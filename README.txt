Multilingual Semantic Drift Evaluation Pipeline
This repository contains a stochastic, multi-agent NLP evaluation pipeline designed to mathematically validate semantic retention, historical fidelity, and morphological drift across diverse language families.

Rather than relying purely on text-based string matching (which tokenizers and varying grammar structures often break), this pipeline projects text into a shared, high-dimensional latent space to provide quantitative proof of semantic degradation.

 What We Are Analyzing
This pipeline measures how Large Language Models (LLMs) degrade, flatten, or hallucinate context when forced to translate through a stochastic chain of distinct language families (Germanic, Romantic, Slavic, Western Asian, Eastern Asian).

It tracks four distinct dimensions of data at every "hop" in the chain:

Global Semantic Retention (Vector Space Analysis): Calculates the cosine similarity between the original English source and the current translation hop to measure how much core meaning has survived.

Historical Fidelity (Sliding Window Alignment): Measures the generated output against verified, human-authored ground truth texts (e.g., historical literary translations) using a sliding window algorithm to account for length discrepancies and "patchy" generation.

Morphological Diagnostics: * Type-Token Ratio (TTR): Detects grammatical "flattening" in highly inflected languages (Slavic/Germanic).

Character-to-Meaning Density: Detects hallucinated context or overly formal fluff in logographic/syllabic scripts (Eastern Asian).

Qualitative Degradation (LLM-as-a-Judge): Analyzes tone shifts, lost idioms, and specific entity omissions via an independent LLM auditor.

 Tools & Architecture
LaBSE (Language-agnostic BERT Sentence Embedding): Used via sentence-transformers to project 109+ languages into a shared 768-dimensional latent space for 1:1 tensor comparisons.

COMET-QE (Crosslingual Optimized Metric for Evaluation of Translation): Provides state-of-the-art, reference-free quality estimation (predicting human-quality scores by evaluating the Source vs. Target simultaneously).

OpenAI API (GPT-4o-mini): Powers the translation provider interface and the strict, Pydantic-enforced ComparisonEngine auditor.

Python (Scikit-learn, NumPy, Regex): Drives the stochastic routing engine, sliding window logic, and mathematical morphological heuristics.

 Setup and Installation
1. Clone the repository and set up a virtual environment:

Bash
git clone [YOUR_REPO_LINK_HERE]
cd [YOUR_REPO_DIRECTORY]
python -m venv venv
source venv/bin/activate  # On Windows use `venv\Scripts\activate`
2. Install the required dependencies:

Bash
pip install sentence-transformers scikit-learn openai pydantic numpy python-dotenv
3. Install Optional Diagnostics (COMET & spaCy):
(Note: COMET requires PyTorch and may take a moment to download its weights on the first run).

Bash
pip install unbabel-comet spacy
python -m spacy download en_core_web_sm
4. Environment Variables:
Create a .env file in the root directory and add your API keys:

Code snippet
OPENAI_API_KEY=your_api_key_here
 Usage
To execute the pipeline, simply run the orchestrator script. Ensure you have a stable internet connection for the API calls and enough local memory to load the LaBSE tensor weights (~1.8GB) on the first initialization.

Bash
python "Stochastic Chain.py"
Outputs
The program generates a comprehensive translation_report.txt containing:

The stochastic path log for the experiment.

Intermediate text outputs for every language hop.

Real-time metrics (LaBSE, TTR, Character Density, COMET-QE) for each node.

A final qualitative LLM-Judge analysis of the back-translated English result.