import re
import numpy as np
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity

class FoundationGrader:
    def __init__(self):
        print("Loading LaBSE Model into memory... (This may take a moment)")
        # This model projects 109+ languages into a shared 768-dimensional latent space
        self.labse = SentenceTransformer('sentence-transformers/LaBSE')

    def calculate_similarity(self, text_a: str, text_b: str) -> float:
        """Projects texts into the shared latent space and calculates Cosine Similarity."""
        if not text_a.strip() or not text_b.strip():
            return 0.0
            
        embeddings = self.labse.encode([text_a, text_b])
        sim = cosine_similarity([embeddings[0]], [embeddings[1]])[0][0]
        return float(sim)

    def calculate_windowed_similarity(self, generated_text: str, ground_truth_snippet: str) -> float:
        """
        Solves the 'patchy' text problem by finding the best-matching 
        segment in a long generation using a sliding window.
        """
        gen_lines = [l.strip() for l in generated_text.split('\n') if l.strip()]
        truth_lines = [l.strip() for l in ground_truth_snippet.split('\n') if l.strip()]
        
        window_size = len(truth_lines)
        
        # If the generated text is shorter than our ground truth snippet, 
        # fallback to a direct comparison.
        if window_size == 0 or len(gen_lines) < window_size:
            return self.calculate_similarity(generated_text, ground_truth_snippet)

        max_sim = 0.0
        
        # Slide the window across the generated lines to find the best match
        for i in range(len(gen_lines) - window_size + 1):
            window_text = "\n".join(gen_lines[i : i + window_size])
            current_sim = self.calculate_similarity(window_text, ground_truth_snippet)
            if current_sim > max_sim:
                max_sim = current_sim
        
        return max_sim

    def calculate_ttr(self, text: str) -> float:
        """
        Calculates Type-Token Ratio (TTR) to measure morphological diversity.
        Useful for Slavic/Germanic hops to detect 'flattening' of complex grammar.
        """
        tokens = re.findall(r'\w+', text.lower())
        if not tokens:
            return 0.0
        # Ratio of unique words (Types) to total words (Tokens)
        return len(set(tokens)) / len(tokens)

    def calculate_char_density(self, text: str) -> float:
        """
        Calculates character-to-word ratio.
        Useful for Eastern Asian hops to detect hallucinated context or 'fluff'.
        """
        tokens = text.split()
        if not tokens:
            return 0.0
        # Calculate non-space characters per word
        return len(text.replace(" ", "")) / len(tokens)