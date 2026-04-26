import random
import asyncio
import os
from datetime import datetime
from chaintest import (
    OpenAITranslationProvider, 
    GeminiTranslationProvider, 
    ClaudeTranslationProvider, 
    DeepSeekTranslationProvider, 
    KimiTranslationProvider,
    TranslationResult
)
from comparison import ComparisonEngine
from foundation_grader import FoundationGrader
from visualizer import PipelineVisualizer

# --- Infrastructure Configuration ---

FAMILY_DICTIONARY = {
    "English": ["English"], 
    "Germanic": ["German", "Dutch", "Swedish"],
    "Romantic": ["Spanish", "French", "Italian"],
    "Slavic": ["Russian", "Polish", "Czech"],
    "Western Asian": ["Arabic", "Hebrew", "Farsi"],
    "Eastern Asian": ["Mandarin Chinese", "Japanese", "Korean"]
}

RESEARCH_DATASETS = {
    "Technical Document": {
        "source_text": "All human beings are born free and equal in dignity and rights. They are endowed with reason and conscience and should act towards one another in a spirit of brotherhood.",
        "snippets": {
            "English": "All human beings are born free and equal in dignity and rights. They are endowed with reason and conscience and should act towards one another in a spirit of brotherhood.",
            "German": "Alle Menschen sind frei und gleich an Würde und Rechten geboren. Sie sind mit Vernunft und Gewissen begabt und sollen einander im Geist der Brüderlichkeit begegnen.",
            "Dutch": "Alle menselijke wezens worden vrij en gelijk in waardigheid en rechten geboren. Zij zijn begiftigd met verstand en geweten, en behoren zich jegens elkander in een geest van broederschap te gedragen.",
            "Swedish": "Alla människor är födda fria och lika i värde och rättigheter. De har utrustats med förnuft och samvete och bör handla gentemot varandra i en anda av gemenskap.",
            "Spanish": "Todos los seres humanos nacen libres e iguales en dignidad y derechos y, dotados como están de razón y conciencia, deben comportarse fraternalmente los unos con los otros.",
            "French": "Tous les êtres humains naissent libres et égaux en dignité et en droits. Ils sont doués de raison et de conscience et doivent agir les uns envers les autres dans un esprit de fraternité.",
            "Italian": "Tutti gli esseri umani nascono liberi ed eguali in dignità e diritti. Essi sono dotati di ragione e di coscienza e devono agire gli uni verso gli altri in spirito di fratellanza.",
            "Russian": "Все люди рождаются свободными и равными в своем достоинстве и правах. Они наделены разумом и совестью и должны поступать в отношении друг друга в духе братства.",
            "Polish": "Wszyscy ludzie rodzą się wolni i równi pod względem swej godności i swych praw. Są oni obdarzeni rozumem i sumieniem i powinni postępować wobec innych в духе братства.",
            "Czech": "Všichni lidé se rodí svobodní a sobě rovní co do důstojnosti a práv. Jsou nadáni rozumem a svědomím a mají spolu jednat v duchu bratrství.",
            "Arabic": "يولد جميع الناس أحرارًا متساوين في الكرامة والحقوق. وقد وهبوا عقلاً وضميرًا وعليهم أن يعامل بعضهم بعضًا بروح الإخاء.",
            "Hebrew": "כל בני האדם נולדו בני חורין ושווים בערכם ובזכויותيهם. כולם חוננו בתבונה ובמצפון, לפיכך חובה עליהם לנהוג איש ברעהו ברוح של אחווה.",
            "Farsi": "تمام افراد بشر آزاد به دنیا می‌آیند و از لحاظ حیثیت و حقوق با هم برابرند. همه دارای عقل و وجدان می‌باشند و باید نسبت به یکدیگر با روح برادری رفتار کنند.",
            "Mandarin Chinese": "人人生而自由，在尊严和权利上一律平等。他们赋有理性和良心，并应以兄弟关系的精神相对待。",
            "Japanese": "すべての人間は、生れながらにして自由であり、かつ、尊厳と権利とについて平等である。人間は、理性と良心とを授けられており、互いに同胞の精神をもって行動しなければならない。",
            "Korean": "모든 인간은 태어날 때부터 자유로우며 그 존엄과 권리에 있어 동등하다. 인간은 천부적으로 이성과 양심을 부여받았으며 서로 형제애의 정신으로 행동하여야 한다."
        }
    },
    "Metaphorical Poem": {
        "source_text": "The ocean speaks in whispers to the shore, A salty breath that rustles through the sand. It holds the ancient secrets of the deep, A world untouched by any human hand.",
        "snippets": {} # Zero-Shot experiment (no ground truth exists)
    }
}

async def run_stochastic_chain(initial_text, family_chain, family_dict, provider):
    """Executes the translation pipeline with Anti-Deadlock and Jitter logic."""
    results_history = []
    current_text = initial_text
    current_source_lang = "English"

    for i in range(len(family_chain) - 1):
        target_lang = random.choice(family_dict[family_chain[i+1]])
        path_log = f"Hop {i+1}: {family_chain[i]} ({current_source_lang}) -> {family_chain[i+1]} ({target_lang})"
        print(f"[{provider.provider_name.upper()}] {path_log}")
        
        try:
            # ANTI-DEADLOCK: Hard 45-second limit per API call
            result = await asyncio.wait_for(
                provider.translate(current_text, current_source_lang, target_lang),
                timeout=45.0
            )
        except asyncio.TimeoutError:
            print(f"[{provider.provider_name.upper()}] ⏳ DEADLOCK DETECTED! Terminating hop at {path_log}")
            result = TranslationResult(
                source_text=current_text,
                translated_text="",
                provider=provider.provider_name,
                model_id=provider.default_model,
                latency_ms=45000,
                error="API Timeout Deadlock (45s)"
            )
            
        result.decoding_params["routing_path"] = path_log
        result.decoding_params["target_lang"] = target_lang
        results_history.append(result)
        
        if result.error or not result.translated_text:
            print(f"[{provider.provider_name.upper()}] ❌ Chain broken: {result.error}")
            break
            
        current_text, current_source_lang = result.translated_text, target_lang
        
        # RATE LIMIT JITTER: 2.5s pause between sequential hops per model
        await asyncio.sleep(2.5)
        
    return results_history

async def main():
    # Initializing all 5 Agents
    providers = [
        OpenAITranslationProvider(), 
        GeminiTranslationProvider(),
        ClaudeTranslationProvider(),
        DeepSeekTranslationProvider(),
        KimiTranslationProvider()
    ]
    chain_path = ["English", "Germanic", "Romantic", "Slavic", "Western Asian", "Eastern Asian", "English"]
    
    grader = FoundationGrader()
    auditor = ComparisonEngine()
    viz = PipelineVisualizer()
    global_judge_log = [] # Accrues qualitative data for final Box Plot visualization

    with open("translation_report.txt", "w", encoding="utf-8") as file:
        file.write("=== MULTILINGUAL SEMANTIC DRIFT REPORT ===\n")
        file.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        
        for dataset_name, dataset in RESEARCH_DATASETS.items():
            print(f"\n{'*'*50}\nBenchmarking Dataset: {dataset_name}\n{'*'*50}")
            file.write(f"\n{'#'*50}\nDATASET: {dataset_name.upper()}\n{'#'*50}\n\n")
            file.write(f"[ORIGINAL SOURCE TEXT]\n{dataset['source_text']}\n\n")
            
            # Fire all 5 models in parallel
            tasks = [run_stochastic_chain(dataset["source_text"], chain_path, FAMILY_DICTIONARY, p) for p in providers]
            parallel_results = await asyncio.gather(*tasks)
            
            meta_labse = []
            dataset_plot_data = {} 
            
            for history in parallel_results:
                if not history: continue
                provider_tag = history[0].provider.upper()
                file.write(f"{'='*40}\n  PROVIDER: {provider_tag}\n{'='*40}\n\n")
                
                scores = {"labse": [], "fidelity": [], "bleu": [], "comet": [], "ttr": []}
                
                for res in history:
                    if res.error:
                        file.write(f">> {res.decoding_params.get('routing_path', 'Unknown Hop')}\n")
                        file.write(f"❌ API CRUSH / ERROR: {res.error}\n")
                        file.write("-" * 30 + "\n")
                        continue

                    ground_truth = dataset["snippets"].get(res.decoding_params["target_lang"], "")
                    
                    # Core Metric Extraction
                    l_val = grader.calculate_similarity(dataset["source_text"], res.translated_text)
                    f_val = grader.calculate_windowed_similarity(res.translated_text, ground_truth)
                    b_val = grader.calculate_bleu(res.translated_text, ground_truth)
                    c_val = auditor.calculate_comet_qe(dataset["source_text"], res.translated_text)
                    t_val = grader.calculate_ttr(res.translated_text)
                    
                    scores["labse"].append(l_val); scores["fidelity"].append(f_val)
                    scores["bleu"].append(b_val); scores["comet"].append(c_val)
                    scores["ttr"].append(t_val)
                    
                    meta_labse.append(l_val)
                    
                    file.write(f">> {res.decoding_params['routing_path']}\n")
                    file.write(f"LaBSE: {l_val:.4f} | Fidelity: {f_val:.4f} | BLEU: {b_val:.2f} | COMET: {c_val:.4f} | TTR: {t_val:.4f}\n")
                    file.write("-" * 30 + "\n")
                
                dataset_plot_data[provider_tag] = scores
                
                if scores["labse"]:
                    avg_l = sum(scores["labse"]) / len(scores["labse"])
                    file.write(f"\n[MODEL CHAIN AVERAGES]\nAvg LaBSE: {avg_l:.4f} | Avg COMET: {sum(scores['comet'])/len(scores['comet']):.4f}\n\n")
                
                # Final Qualitative Audit
                if history and not history[-1].error:
                    eval_result = await auditor.evaluate_semantic_drift(dataset["source_text"], history[-1])
                    score_pct = eval_result.score * 100
                    file.write(f"=== FINAL AUDIT ===\nJudge Score: {score_pct}%\nAnalysis: {eval_result.analysis}\n\n")
                    
                    # Capture for Box Plot
                    global_judge_log.append({'Provider': provider_tag, 'Score': score_pct})

            # Dataset-level Pipeline Visualizations
            viz.generate_radar_charts(dataset_name, dataset_plot_data)
            viz.generate_alignment_chart(dataset_name, dataset_plot_data)

    # Final Cross-Dataset Volatility Analysis
    if global_judge_log:
        viz.generate_judge_box_plot(global_judge_log)

    print("\n📝 Execution Finished. Report and PNG visualizations generated.")

# EXPLICIT MAIN DRIVER BLOCK
if __name__ == "__main__":
    asyncio.run(main())