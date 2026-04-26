import re
import numpy as np
import sacrebleu
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity

class FoundationGrader:
    def __init__(self):
        print("Loading LaBSE Model (Semantic Vector Engine)...")
        self.labse = SentenceTransformer('sentence-transformers/LaBSE')

    def calculate_similarity(self, text_a: str, text_b: str) -> float:
        if not text_a.strip() or not text_b.strip():
            return 0.0
        embeddings = self.labse.encode([text_a, text_b])
        return float(cosine_similarity([embeddings[0]], [embeddings[1]])[0][0])

    def calculate_windowed_similarity(self, generated_text: str, ground_truth: str) -> float:
        gen_lines = [l.strip() for l in generated_text.split('\n') if l.strip()]
        truth_lines = [l.strip() for l in ground_truth.split('\n') if l.strip()]
        window_size = len(truth_lines)
        if window_size == 0 or len(gen_lines) < window_size:
            return self.calculate_similarity(generated_text, ground_truth)
        max_sim = 0.0
        for i in range(len(gen_lines) - window_size + 1):
            window_text = "\n".join(gen_lines[i : i + window_size])
            current_sim = self.calculate_similarity(window_text, ground_truth)
            if current_sim > max_sim: max_sim = current_sim
        return max_sim

    def calculate_bleu(self, generated_text: str, ground_truth: str) -> float:
        """Calculates n-gram precision against a validated historical snippet."""
        if not ground_truth or not generated_text:
            return 0.0
        # SacreBLEU expects lists of strings
        bleu = sacrebleu.corpus_bleu([generated_text], [[ground_truth]])
        return float(bleu.score)

    def calculate_ttr(self, text: str) -> float:
        tokens = re.findall(r'\w+', text.lower())
        if not tokens: return 0.0
        return len(set(tokens)) / len(tokens)

    def calculate_char_density(self, text: str) -> int:
        return len(text.replace(" ", "").replace("\n", ""))