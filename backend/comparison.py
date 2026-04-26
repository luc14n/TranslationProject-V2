import functools
from pydantic import BaseModel, Field
from typing import List
from openai import AsyncOpenAI
import logging

# --- PYTHON 3.14 COMPATIBILITY MONKEYPATCH ---
if not hasattr(functools, '_HashedSeq'):
    class _HashedSeq(list):
        __slots__ = 'hashvalue'
        def __init__(self, tup, hash=hash):
            self[:] = tup
            self.hashvalue = hash(tup)
        def __hash__(self):
            return self.hashvalue
    functools._HashedSeq = _HashedSeq

from comet import download_model, load_from_checkpoint
logging.getLogger("pytorch_lightning").setLevel(logging.WARNING)

class LLMEvaluation(BaseModel):
    score: float = Field(description="Numerical retention score from 0.0 to 1.0.")
    analysis: str = Field(description="Detailed explanation of what changed during the chain.")
    omissions: List[str] = Field(description="Specific keywords or technical nuances lost in translation.")

class ComparisonEngine:
    def __init__(self):
        self.client = AsyncOpenAI()
        self.judge_model = "gpt-4o-mini"
        
        print("Loading Open COMET-QE Model into VRAM...")
        # Switched to the ungated WMT20 model to bypass Hugging Face authentication requirements
        model_path = download_model("Unbabel/wmt20-comet-qe-da")
        self.comet_model = load_from_checkpoint(model_path)
        self.comet_model.eval()

    def calculate_comet_qe(self, source: str, translation: str) -> float:
        if not source or not translation:
            return 0.0
            
        data = [{"src": source, "mt": translation}]
        model_output = self.comet_model.predict(data, batch_size=8, gpus=1)
        return float(model_output.scores[0])

    async def evaluate_semantic_drift(self, original_text: str, final_result) -> LLMEvaluation:
        sys_msg = (
            "You are a linguistic auditor. Compare the ORIGINAL source text to the "
            "final BACK-TRANSLATED version. Identify semantic drift, loss of nuance, "
            "and tone shifts. Be critical and objective."
        )
        user_msg = f"ORIGINAL SOURCE:\n{original_text}\n\nFINAL BACK-TRANSLATION:\n{final_result.translated_text}"

        try:
            response = await self.client.beta.chat.completions.parse(
                model=self.judge_model,
                messages=[{"role": "system", "content": sys_msg}, {"role": "user", "content": user_msg}],
                response_format=LLMEvaluation,
                temperature=0.0
            )
            return response.choices[0].message.parsed
        except Exception as e:
            return LLMEvaluation(score=0.0, analysis=f"Auditor Error: {str(e)}", omissions=["Processing Error"])