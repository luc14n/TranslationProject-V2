import json
from pydantic import BaseModel, Field
from typing import List
from openai import AsyncOpenAI
from chaintest import TranslationResult

# 1. The Strict Output Schema for the Judge
class LLMEvaluation(BaseModel):
    score: float = Field(description="A score from 0.0 to 1.0 representing how much semantic meaning was retained.")
    analysis: str = Field(description="A concise 1-2 sentence explanation of what context was lost, altered, or retained perfectly.")
    omissions: List[str] = Field(description="A list of specific entities, idioms, or core details that were completely dropped. Return an empty list if none.")

class ComparisonEngine:
    def __init__(self):
        self.client = AsyncOpenAI() 
        self.judge_model = "gpt-4o-mini" 
        self.comet_model = None

    def init_comet_model(self):
        """
        Loads the COMET-QE model into memory. 
        Run `pip install unbabel-comet` before calling this.
        """
        if self.comet_model is None:
            print("Downloading/Loading COMET-QE model... (This will take a moment)")
            try:
                from comet import download_model, load_from_checkpoint
                model_path = download_model("Unbabel/wmt22-cometkiwi-da")
                self.comet_model = load_from_checkpoint(model_path)
            except ImportError:
                print("❌ Warning: 'unbabel-comet' is not installed. Run pip install unbabel-comet.")

    def calculate_comet_qe(self, source: str, translation: str) -> float:
        """Reference-free quality estimation evaluating Source vs Target."""
        if self.comet_model is None:
            return 0.0 # Returns 0.0 if the model hasn't been initialized
            
        data = [{"src": source, "mt": translation}]
        # Disable GPU strictly for the test run if you aren't on a CUDA machine
        model_output = self.comet_model.predict(data, batch_size=8, gpus=0)
        return float(model_output.scores[0])

    async def evaluate_semantic_drift(self, original_text: str, final_result: TranslationResult) -> LLMEvaluation:
        """Uses OpenAI to grade the back-translated text against the original source."""
        back_translated_text = final_result.translated_text
        
        sys_msg = """
        You are an expert linguistic auditor. Compare the ORIGINAL text to the BACK-TRANSLATED text.
        The text has gone through a multi-language translation chain. 
        Analyze the degradation, focusing on semantic drift, tone shifts, and omitted details.
        """
        
        user_msg = f"ORIGINAL:\n{original_text}\n\nBACK-TRANSLATED:\n{back_translated_text}"
        
        try:
            print("Grading final semantic drift...")
            response = await self.client.beta.chat.completions.parse(
                model=self.judge_model,
                messages=[
                    {"role": "system", "content": sys_msg},
                    {"role": "user", "content": user_msg}
                ],
                response_format=LLMEvaluation,
                temperature=0.0 
            )
            return response.choices[0].message.parsed
            
        except Exception as e:
            print(f" Evaluation Failed: {e}")
            return LLMEvaluation(score=0.0, analysis=f"Error during evaluation: {e}", omissions=["Error"])