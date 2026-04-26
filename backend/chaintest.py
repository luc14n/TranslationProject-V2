import asyncio
import time
import random
import traceback
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field
from dotenv import load_dotenv
from google import genai
from google.genai import types
from abc import ABC, abstractmethod
from typing import Optional, Any, List, Dict

# 1. Load the hidden API key
load_dotenv()

# 2. Schemas & Interfaces
class TranslationResult(BaseModel):
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
    def __init__(self, provider_name: str, default_model: str):
        self.provider_name = provider_name
        self.default_model = default_model

    @abstractmethod
    async def translate(self, text: str, source_lang: str, target_lang: str, **kwargs) -> TranslationResult:
        pass

# 3. The Gemini Provider (With Fixes 1 & 3 applied)
class GeminiTranslationProvider(BaseTranslationProvider):
    def __init__(self, default_model: str = "gemini-2.5-pro"): # Fix 1: Standardized model ID
        super().__init__(provider_name="google_gemini", default_model=default_model)
        self.client = genai.Client() # Automatically uses GEMINI_API_KEY from .env

    async def translate(self, text: str, source_lang: str, target_lang: str, **kwargs) -> TranslationResult:
        prompt = f"Translate the following text from {source_lang} to {target_lang}. Return only the translated text.\n\n{text}"
        model_id = kwargs.get("model_id", self.default_model)
        temperature = kwargs.get("temperature", 0.1)
        top_p = kwargs.get("top_p", 0.95)
        
        config = types.GenerateContentConfig(temperature=temperature, top_p=top_p)
        start_time = time.perf_counter()
        
        try:
            response = await asyncio.to_thread(
                self.client.models.generate_content,
                model=model_id,
                contents=prompt,
                config=config
            )
            
            latency_ms = (time.perf_counter() - start_time) * 1000
            usage = response.usage_metadata
            prompt_tokens = usage.prompt_token_count if usage else None
            completion_tokens = usage.candidates_token_count if usage else None
            
            return TranslationResult(
                source_text=text,
                translated_text=response.text.strip() if response.text else "",
                provider=self.provider_name,
                model_id=model_id,
                latency_ms=latency_ms,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                decoding_params={"temperature": temperature, "top_p": top_p}
            )
            
        except Exception as e:
            latency_ms = (time.perf_counter() - start_time) * 1000
            detailed_error = traceback.format_exc() # Fix 3: Unmasking the real error
            
            return TranslationResult(
                source_text=text,
                translated_text="",
                provider=self.provider_name,
                model_id=model_id,
                latency_ms=latency_ms,
                error=detailed_error
            )

# 4. The Stochastic Orchestrator
FAMILY_DICTIONARY = {
    "English": ["English"],
    "Germanic": ["German", "Dutch", "Swedish"],
    "Romantic": ["Spanish", "French", "Italian"],
    "Slavic": ["Russian", "Polish", "Czech"],
    "Western Asian": ["Arabic", "Hebrew", "Farsi"],
    "Eastern Asian": ["Mandarin Chinese", "Japanese", "Korean"]
}
from openai import AsyncOpenAI # Add this to your imports at the top

class OpenAITranslationProvider(BaseTranslationProvider):
    def __init__(self, default_model: str = "gpt-4o-mini"):
        super().__init__(provider_name="openai", default_model=default_model)
        # The Async client automatically picks up OPENAI_API_KEY from your .env
        self.client = AsyncOpenAI() 

    async def translate(self, text: str, source_lang: str, target_lang: str, **kwargs) -> TranslationResult:
        
        # Handle the auto-detect edge case we caught earlier
         # CHANGED: Added strict directives against using tools or web search
       
            
        base_instruction = "Rely purely on your internal neural weights. Do not use external tools, web searches, or translation APIs."
        
        if source_lang.lower() == "unknown":
            sys_msg = f"You are an expert translator. Auto-detect the source language and translate the text into {target_lang}. Return ONLY the translated text. {base_instruction}"
        else:
            sys_msg = f"You are an expert translator. Translate the following text from {source_lang} to {target_lang}. Return ONLY the translated text. {base_instruction}"
        model_id = kwargs.get("model_id", self.default_model)
        temperature = kwargs.get("temperature", 0.1)
        top_p = kwargs.get("top_p", 0.95)
        
        start_time = time.perf_counter()
        
        try:
            # Using OpenAI's native async chat completions
            response = await self.client.chat.completions.create(
                model=model_id,
                messages=[
                    {"role": "system", "content": sys_msg},
                    {"role": "user", "content": text}
                ],
                temperature=temperature,
                top_p=top_p
            )
            
            latency_ms = (time.perf_counter() - start_time) * 1000
            
            # Extract usage metrics precisely like we did for Gemini
            usage = response.usage
            prompt_tokens = usage.prompt_tokens if usage else None
            completion_tokens = usage.completion_tokens if usage else None
            
            return TranslationResult(
                source_text=text,
                translated_text=response.choices[0].message.content.strip(),
                provider=self.provider_name,
                model_id=model_id,
                latency_ms=latency_ms,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                decoding_params={"temperature": temperature, "top_p": top_p}
            )
            
        except Exception as e:
            latency_ms = (time.perf_counter() - start_time) * 1000
            detailed_error = traceback.format_exc()
            
            return TranslationResult(
                source_text=text,
                translated_text="",
                provider=self.provider_name,
                model_id=model_id,
                latency_ms=latency_ms,
                error=detailed_error
            )

async def run_stochastic_chain(
    initial_text: str, 
    family_chain: list[str], 
    family_dict: dict[str, list[str]],
    provider: BaseTranslationProvider
) -> list[TranslationResult]:
    
    results_history = []
    current_text = initial_text
    
    for i in range(len(family_chain) - 1):
        source_family = family_chain[i]
        target_family = family_chain[i+1]
        
        source_lang = random.choice(family_dict[source_family])
        target_lang = random.choice(family_dict[target_family])
        
        path_log = f"Hop {i+1}: {source_family} ({source_lang}) -> {target_family} ({target_lang})"
        print(f"Executing {path_log}...")
        
        result = await provider.translate(text=current_text, source_lang=source_lang, target_lang=target_lang)
        result.decoding_params["routing_path"] = path_log 
        results_history.append(result)
        
        if result.error or not result.translated_text:
            print(f"\n❌ Chain broken at {path_log}!")
            print(f"Error Details:\n{result.error}")
            break
            
        current_text = result.translated_text
        
    return results_history

# 5. Execution Block
async def main():
    
    print("Initializing OpenAI Provider...")
    openai_provider = OpenAITranslationProvider()
    
    test_text = "The new software update is a double-edged sword; it fixes the bugs but completely throws a wrench in our current workflow."
    
    # CHANGED: Added "English" to the very end of the list for back-translation
    chain_path = ["English", "Germanic", "Romantic", "Slavic", "Western Asian", "Eastern Asian", "English"]
    
    print("\nStarting Translation Chain...")
    history = await run_stochastic_chain(test_text, chain_path, FAMILY_DICTIONARY, openai_provider)
    
    if history and not history[-1].error:
        final_text = history[-1].translated_text
        print("\n✅ Chain Completed Successfully!")
        print(f"Final output: {final_text}")
        
        # CHANGED: Write the entire journey and final result to a text file
        # utf-8 encoding is mandatory here to prevent crashes on non-English characters
        with open("translation_report.txt", "w", encoding="utf-8") as file:
            file.write("--- TRANSLATION DRIFT REPORT ---\n\n")
            file.write(f"ORIGINAL TEXT:\n{test_text}\n\n")
            
            file.write("ROUTING PATH TAKEN:\n")
            for result in history:
                hop = result.decoding_params.get("routing_path", "Unknown Hop")
                file.write(f" - {hop}\n")
                
            file.write(f"\nFINAL BACK-TRANSLATION (ENGLISH):\n{final_text}\n")
            
        print("\n📝 Report successfully saved to 'translation_report.txt'")

if __name__ == "__main__":
    asyncio.run(main())