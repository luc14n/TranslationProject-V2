import asyncio
import time
import traceback
import os
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field
from dotenv import load_dotenv
from google import genai
from google.genai import types
from abc import ABC, abstractmethod
from openai import AsyncOpenAI
from anthropic import AsyncAnthropic

# 1. Load environment variables
load_dotenv()

class TranslationResult(BaseModel):
    """Standardized output schema for client-facing analytics."""
    source_text: str
    translated_text: str
    provider: str
    model_id: str
    latency_ms: float
    prompt_tokens: Optional[int] = None
    completion_tokens: Optional[int] = None
    decoding_params: Dict[str, Any] = Field(default_factory=dict)
    error: Optional[str] = None

class BaseTranslationProvider(ABC):
    """Abstract base class ensuring all APIs follow identical translation constraints."""
    def __init__(self, provider_name: str, default_model: str):
        self.provider_name = provider_name
        self.default_model = default_model

    def get_system_prompt(self, target_lang: str) -> str:
        """The 'Amnesiac' directive to force mechanical translation."""
        return f"""You are an offline, mechanical translation engine.
Your strict directive is to provide a literal, structurally exact translation of the input text into {target_lang}.

CRITICAL RULES:
1. Translate exactly what is written, preserving specific syntax and morphology.
2. DO NOT polish or autocorrect the text into standard idioms.
3. Output ONLY the raw translated text. No introductions, notes, or filler."""

    @abstractmethod
    async def translate(self, text: str, source_lang: str, target_lang: str, **kwargs) -> TranslationResult:
        pass

class GeminiTranslationProvider(BaseTranslationProvider):
    """Google Gemini implementation using the 2.5-flash production model."""
    def __init__(self, default_model: str = "gemini-2.5-flash"): 
        super().__init__(provider_name="google_gemini", default_model=default_model)
        # Explicit key injection for Spark Labs environment security
        api_key = os.getenv("GEMINI_API_KEY")
        self.client = genai.Client(api_key=api_key)

    async def translate(self, text: str, source_lang: str, target_lang: str, **kwargs) -> TranslationResult:
        model_id = kwargs.get("model_id", self.default_model)
        temperature = kwargs.get("temperature", 0.0)
        
        config = types.GenerateContentConfig(
            temperature=temperature, 
            system_instruction=self.get_system_prompt(target_lang)
        )
        
        start_time = time.perf_counter()
        try:
            # FIX: Using .aio with gemini-2.5-flash for 2026 SDK compliance
            response = await self.client.aio.models.generate_content(
                model=model_id, 
                contents=text, 
                config=config
            )
            
            latency_ms = (time.perf_counter() - start_time) * 1000
            
            # Extract text carefully to handle safety blocks
            translated_text = ""
            if response.text:
                translated_text = response.text.strip()
            elif response.candidates and response.candidates[0].content.parts:
                translated_text = response.candidates[0].content.parts[0].text.strip()

            return TranslationResult(
                source_text=text,
                translated_text=translated_text,
                provider=self.provider_name,
                model_id=model_id,
                latency_ms=latency_ms,
                prompt_tokens=response.usage_metadata.prompt_token_count if response.usage_metadata else None,
                completion_tokens=response.usage_metadata.candidates_token_count if response.usage_metadata else None,
                decoding_params={"temperature": temperature}
            )
        except Exception as e:
            return TranslationResult(
                source_text=text,
                translated_text="",
                provider=self.provider_name,
                model_id=model_id,
                latency_ms=(time.perf_counter() - start_time) * 1000,
                error=str(e) 
            )

class OpenAITranslationProvider(BaseTranslationProvider):
    def __init__(self, default_model: str = "gpt-4o-mini"):
        super().__init__(provider_name="openai", default_model=default_model)
        self.client = AsyncOpenAI() 

    async def translate(self, text: str, source_lang: str, target_lang: str, **kwargs) -> TranslationResult:
        model_id = kwargs.get("model_id", self.default_model)
        temperature = kwargs.get("temperature", 0.0)
        sys_msg = self.get_system_prompt(target_lang)
        
        start_time = time.perf_counter()
        try:
            response = await self.client.chat.completions.create(
                model=model_id,
                messages=[{"role": "system", "content": sys_msg}, {"role": "user", "content": text}],
                temperature=temperature
            )
            
            latency_ms = (time.perf_counter() - start_time) * 1000
            return TranslationResult(
                source_text=text,
                translated_text=response.choices[0].message.content.strip(),
                provider=self.provider_name,
                model_id=model_id,
                latency_ms=latency_ms,
                prompt_tokens=response.usage.prompt_tokens if response.usage else None,
                completion_tokens=response.usage.completion_tokens if response.usage else None,
                decoding_params={"temperature": temperature}
            )
        except Exception as e:
            return TranslationResult(
                source_text=text,
                translated_text="",
                provider=self.provider_name,
                model_id=model_id,
                latency_ms=(time.perf_counter() - start_time) * 1000,
                error=str(e)
            )

class ClaudeTranslationProvider(BaseTranslationProvider):
    """Anthropic Claude implementation."""
    # FIX: Updated to the strict Anthropic release tag
    def __init__(self, default_model: str = "claude-sonnet-4-6"):
        super().__init__(provider_name="anthropic_claude", default_model=default_model)
       
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            print("[CRITICAL] ANTHROPIC_API_KEY not found in .env file!")
        self.client = AsyncAnthropic(api_key=api_key)

    async def translate(self, text: str, source_lang: str, target_lang: str, **kwargs) -> TranslationResult:
        model_id = kwargs.get("model_id", self.default_model)
        temperature = kwargs.get("temperature", 0.0)
        sys_msg = self.get_system_prompt(target_lang)
        
        start_time = time.perf_counter()
        try:
            # Anthropic uses a specific top-level 'system' parameter
            response = await self.client.messages.create(
                model=model_id,
                system=sys_msg,
                messages=[{"role": "user", "content": text}],
                temperature=temperature,
                max_tokens=1024 # Anthropic requires max_tokens to be explicitly set
            )
            
            latency_ms = (time.perf_counter() - start_time) * 1000
            
            return TranslationResult(
                source_text=text,
                translated_text=response.content[0].text.strip(),
                provider=self.provider_name,
                model_id=model_id,
                latency_ms=latency_ms,
                prompt_tokens=response.usage.input_tokens if response.usage else None,
                completion_tokens=response.usage.output_tokens if response.usage else None,
                decoding_params={"temperature": temperature}
            )
        except Exception as e:
            return TranslationResult(
                source_text=text, translated_text="", provider=self.provider_name,
                model_id=model_id, latency_ms=(time.perf_counter() - start_time) * 1000, error=f"API Error: {str(e)}"
            )

class DeepSeekTranslationProvider(BaseTranslationProvider):
    """DeepSeek implementation via OpenAI SDK compatibility layer."""
    def __init__(self, default_model: str = "deepseek-chat"):
        super().__init__(provider_name="deepseek", default_model=default_model)
        api_key = os.getenv("DEEPSEEK_API_KEY")
        if not api_key:
            print("[CRITICAL] DEEPSEEK_API_KEY not found in .env file!")
        # Override the base URL to point to DeepSeek's servers
        self.client = AsyncOpenAI(api_key=api_key, base_url="https://api.deepseek.com")

    async def translate(self, text: str, source_lang: str, target_lang: str, **kwargs) -> TranslationResult:
        model_id = kwargs.get("model_id", self.default_model)
        temperature = kwargs.get("temperature", 0.0)
        sys_msg = self.get_system_prompt(target_lang)
        
        start_time = time.perf_counter()
        try:
            response = await self.client.chat.completions.create(
                model=model_id,
                messages=[{"role": "system", "content": sys_msg}, {"role": "user", "content": text}],
                temperature=temperature
            )
            
            latency_ms = (time.perf_counter() - start_time) * 1000
            return TranslationResult(
                source_text=text,
                translated_text=response.choices[0].message.content.strip(),
                provider=self.provider_name,
                model_id=model_id,
                latency_ms=latency_ms,
                prompt_tokens=response.usage.prompt_tokens if response.usage else None,
                completion_tokens=response.usage.completion_tokens if response.usage else None,
                decoding_params={"temperature": temperature}
            )
        except Exception as e:
            return TranslationResult(
                source_text=text, translated_text="", provider=self.provider_name,
                model_id=model_id, latency_ms=(time.perf_counter() - start_time) * 1000, error=f"API Error: {str(e)}"
            )

class KimiTranslationProvider(BaseTranslationProvider):
    """Moonshot/Kimi implementation via OpenAI SDK compatibility layer."""
    def __init__(self, default_model: str = "moonshot-v1-8k"):
        super().__init__(provider_name="moonshot_kimi", default_model=default_model)
        api_key = os.getenv("KIMI_API_KEY")
        if not api_key:
            print("[CRITICAL] KIMI_API_KEY not found in .env file!")
        # Override the base URL to point to Moonshot's servers
        self.client = AsyncOpenAI(api_key=api_key, base_url="https://api.moonshot.ai/v1")

    async def translate(self, text: str, source_lang: str, target_lang: str, **kwargs) -> TranslationResult:
        model_id = kwargs.get("model_id", self.default_model)
        temperature = kwargs.get("temperature", 0.0)
        sys_msg = self.get_system_prompt(target_lang)
        
        start_time = time.perf_counter()
        try:
            response = await self.client.chat.completions.create(
                model=model_id,
                messages=[{"role": "system", "content": sys_msg}, {"role": "user", "content": text}],
                temperature=temperature
            )
            
            latency_ms = (time.perf_counter() - start_time) * 1000
            return TranslationResult(
                source_text=text,
                translated_text=response.choices[0].message.content.strip(),
                provider=self.provider_name,
                model_id=model_id,
                latency_ms=latency_ms,
                prompt_tokens=response.usage.prompt_tokens if response.usage else None,
                completion_tokens=response.usage.completion_tokens if response.usage else None,
                decoding_params={"temperature": temperature}
            )
        except Exception as e:
            return TranslationResult(
                source_text=text, translated_text="", provider=self.provider_name,
                model_id=model_id, latency_ms=(time.perf_counter() - start_time) * 1000, error=f"API Error: {str(e)}"
            )