import asyncio
import os
import random
import sqlite3
from datetime import datetime

from chaintest import (
    ClaudeTranslationProvider,
    DeepSeekTranslationProvider,
    GeminiTranslationProvider,
    KimiTranslationProvider,
    OpenAITranslationProvider,
    TranslationResult,
)
from comparison import ComparisonEngine
from foundation_grader import FoundationGrader
from visualizer import PipelineVisualizer

# --- Infrastructure Configuration ---

DB_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "data", "app_data.db")
)


def load_data_from_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute("SELECT Name, Family FROM Languages")
    family_dictionary = {}
    for row in cursor.fetchall():
        fam = row["Family"]
        if fam not in family_dictionary:
            family_dictionary[fam] = []
        family_dictionary[fam].append(row["Name"])

    cursor.execute("SELECT DocumentID, Type, Name FROM Documents")
    documents = cursor.fetchall()

    research_datasets = {}
    doc_id_to_name = {}
    for doc in documents:
        doc_key = f"{doc['Type']} {doc['Name']}"
        doc_id_to_name[doc["DocumentID"]] = doc_key
        research_datasets[doc_key] = {
            "source_text": "",
            "snippets": {},
            "doc_id": doc["DocumentID"],
        }

    cursor.execute("SELECT Name, Document, Language, Text FROM Refrences")
    for ref in cursor.fetchall():
        doc_key = doc_id_to_name[ref["Document"]]
        if ref["Language"] == "English":
            research_datasets[doc_key]["source_text"] = ref["Text"]
            research_datasets[doc_key]["snippets"]["English"] = ref["Text"]
        else:
            research_datasets[doc_key]["snippets"][ref["Language"]] = ref["Text"]

    conn.close()
    return family_dictionary, research_datasets


FAMILY_DICTIONARY, RESEARCH_DATASETS = load_data_from_db()


def get_model_id(provider_name):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT ModelID FROM Model WHERE Name LIKE ?", (f"%{provider_name.lower()}%",)
    )
    row = cursor.fetchone()
    conn.close()
    return row[0] if row else 1


async def run_stochastic_chain(initial_text, family_chain, family_dict, provider):
    """Executes the translation pipeline with Anti-Deadlock and Jitter logic."""
    results_history = []
    current_text = initial_text
    current_source_lang = "English"

    for i in range(len(family_chain) - 1):
        if family_chain[i + 1] not in family_dict:
            continue
        target_lang = random.choice(family_dict[family_chain[i + 1]])
        path_log = f"Hop {i + 1}: {family_chain[i]} ({current_source_lang}) -> {family_chain[i + 1]} ({target_lang})"
        print(f"[{provider.provider_name.upper()}] {path_log}")

        try:
            # ANTI-DEADLOCK: Hard 45-second limit per API call
            result = await asyncio.wait_for(
                provider.translate(current_text, current_source_lang, target_lang),
                timeout=45.0,
            )
        except asyncio.TimeoutError:
            print(
                f"[{provider.provider_name.upper()}] ⏳ DEADLOCK DETECTED! Terminating hop at {path_log}"
            )
            result = TranslationResult(
                source_text=current_text,
                translated_text="",
                provider=provider.provider_name,
                model_id=provider.default_model,
                latency_ms=45000,
                error="API Timeout Deadlock (45s)",
            )

        result.decoding_params["routing_path"] = path_log
        result.decoding_params["target_lang"] = target_lang
        result.decoding_params["source_lang"] = current_source_lang
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
        KimiTranslationProvider(),
    ]
    chain_path = [
        "English",
        "Germanic",
        "Romantic",
        "Slavic",
        "Western Asian",
        "Eastern Asian",
        "English",
    ]

    grader = FoundationGrader()
    auditor = ComparisonEngine()
    viz = PipelineVisualizer()
    global_judge_log = []

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    for dataset_name, dataset in RESEARCH_DATASETS.items():
        print(f"\n{'*' * 50}\nBenchmarking Dataset: {dataset_name}\n{'*' * 50}")
        doc_id = dataset["doc_id"]

        # Fire all 5 models in parallel
        tasks = [
            run_stochastic_chain(
                dataset["source_text"], chain_path, FAMILY_DICTIONARY, p
            )
            for p in providers
        ]
        parallel_results = await asyncio.gather(*tasks)

        dataset_plot_data = {}

        for history in parallel_results:
            if not history:
                continue
            provider_tag = history[0].provider.upper()
            model_id = get_model_id(history[0].provider)

            scores = {"labse": [], "fidelity": [], "bleu": [], "comet": [], "ttr": []}
            prev_translation_id = None

            for res in history:
                if res.error:
                    continue

                target_lang = res.decoding_params["target_lang"]
                ground_truth = dataset["snippets"].get(target_lang, "")

                # Core Metric Extraction
                l_val = grader.calculate_similarity(
                    dataset["source_text"], res.translated_text
                )
                f_val = grader.calculate_windowed_similarity(
                    res.translated_text, ground_truth
                )
                b_val = grader.calculate_bleu(res.translated_text, ground_truth)
                c_val = auditor.calculate_comet_qe(
                    dataset["source_text"], res.translated_text
                )
                t_val = grader.calculate_ttr(res.translated_text)

                scores["labse"].append(l_val)
                scores["fidelity"].append(f_val)
                scores["bleu"].append(b_val)
                scores["comet"].append(c_val)
                scores["ttr"].append(t_val)

                cursor.execute(
                    """
                    INSERT INTO Translations (Name, Document, Translation, Language, PreviousLanguage, Text, Model, LatencyMS)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                    (
                        f"{dataset_name} - {target_lang}",
                        doc_id,
                        prev_translation_id,
                        target_lang,
                        res.decoding_params["source_lang"],
                        res.translated_text,
                        model_id,
                        res.latency_ms,
                    ),
                )

                translation_id = cursor.lastrowid
                prev_translation_id = translation_id

                cursor.execute(
                    """
                    INSERT INTO Metrics (Translation, LaBSE, Fidelity, BLEU, COMET, TTR)
                    VALUES (?, ?, ?, ?, ?, ?)
                """,
                    (translation_id, l_val, f_val, b_val, c_val, t_val),
                )
                conn.commit()

            dataset_plot_data[provider_tag] = scores

            # Final Qualitative Audit
            if history and not history[-1].error:
                eval_result = await auditor.evaluate_semantic_drift(
                    dataset["source_text"], history[-1]
                )
                score_pct = eval_result.score * 100
                global_judge_log.append({"Provider": provider_tag, "Score": score_pct})

        # Dataset-level Pipeline Visualizations
        viz.generate_radar_charts(dataset_name, dataset_plot_data)
        viz.generate_alignment_chart(dataset_name, dataset_plot_data)

    conn.close()

    # Final Cross-Dataset Volatility Analysis
    if global_judge_log:
        viz.generate_judge_box_plot(global_judge_log)

    print("\n📝 Execution Finished. Database updated and PNG visualizations generated.")


# EXPLICIT MAIN DRIVER BLOCK
if __name__ == "__main__":
    asyncio.run(main())
