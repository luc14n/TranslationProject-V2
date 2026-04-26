import random
import asyncio
import json
from typing import List, Dict
from datetime import datetime
from dotenv import load_dotenv

from chaintest import BaseTranslationProvider, TranslationResult, OpenAITranslationProvider
from comparison import ComparisonEngine
from foundation_grader import FoundationGrader

load_dotenv() 

FAMILY_DICTIONARY = {
    "English": ["English"], 
    "Germanic": ["German", "Dutch", "Swedish"],
    "Romantic": ["Spanish", "French", "Italian"],
    "Slavic": ["Russian", "Polish", "Czech"],
    "Western Asian": ["Arabic", "Hebrew", "Farsi"],
    "Eastern Asian": ["Mandarin Chinese", "Japanese", "Korean"]
}

VERIFIED_SNIPPETS = {
    "French": "Si tu peux voir détruit l'ouvrage de ta vie\nEt sans dire un seul mot te mettre à rebâtir,\nOu perdre en un seul coup le gain de cent parties\nSans un geste et sans un soupir ;",
    "Spanish": "Si puedes mantener la cabeza en su sitio cuando todos a tu alrededor\nla pierden y te culpan por ello;\nSi puedes confiar en ti mismo cuando todos dudan de ti,\npero admites también sus dudas;",
    "Russian": "О, если ты покоен, не растерян,\nКогда теряют головы вокруг,\nИ если ты себе остался верен,\nКогда в тебя не верит лучший друг,",
    "Czech": "Když bezhlavost svým okem klidně měříš,\nač tupen, sám že nejsi bezhlavý,\nkdyž, podezříván, pevně v sebe věříš,\nvšak neviníš svých soků z bezpráví,",
    "Dutch": "Indien gij uw kalmte kunt bewaren, als ieder rondom u\nDie verliest en u daarvan de schuld geeft;\nIndien gij op u zelf kunt vertrouwen, als ieder aan u twijfelt,\nMaar ook hun twijfel in rekening brengt;",
    "Arabic": "إذا قدرت أن تحفظ رأسك حين يفقده كل من حولك\nويلومونك على ذلك؛\nإذا قدرت أن تثق بنفسك حين يشك فيك كل الرجال،\nولكن تسمح لهم بشكهم أيضاً؛"
}

async def run_stochastic_chain(
    initial_text: str, 
    family_chain: List[str], 
    family_dict: Dict[str, List[str]],
    provider: BaseTranslationProvider
) -> List[TranslationResult]:
    
    results_history = []
    current_text = initial_text
    current_source_lang = family_dict[family_chain[0]][0] 
    
    for i in range(len(family_chain) - 1):
        target_family = family_chain[i+1]
        target_lang = random.choice(family_dict[target_family])
        
        path_log = f"Hop {i+1}: {family_chain[i]} ({current_source_lang}) -> {target_family} ({target_lang})"
        print(f"Executing {path_log}...")
        
        result = await provider.translate(
            text=current_text, 
            source_lang=current_source_lang, 
            target_lang=target_lang
        )
        
        result.decoding_params["routing_path"] = path_log 
        result.decoding_params["target_lang"] = target_lang
        results_history.append(result)
        
        if result.error or not result.translated_text:
            print(f" Chain broken at {path_log}. Error: {result.error}")
            break
            
        current_text = result.translated_text
        current_source_lang = target_lang 
        
    return results_history

async def main():
    print("Initializing Engines...")
    openai_provider = OpenAITranslationProvider()
    comparison_engine = ComparisonEngine() 
    foundation_grader = FoundationGrader() 
    
    # Optional: If you have installed unbabel-comet, uncomment the line below:
    # comparison_engine.init_comet_model()
    
    test_text = """If you can keep your head when all about you
    Are losing theirs and blaming it on you,
If you can trust yourself when all men doubt you,
    But make allowance for their doubting too;"""
    
    chain_path = ["English", "Germanic", "Romantic", "Slavic", "Western Asian", "Eastern Asian", "English"]
    
    print("\nStarting Translation Chain...")
    history = await run_stochastic_chain(test_text, chain_path, FAMILY_DICTIONARY, openai_provider)
    
    if history and not history[-1].error:
        final_text = history[-1].translated_text
        print("\n✅ Chain Completed Successfully!")
        
        evaluation = await comparison_engine.evaluate_semantic_drift(test_text, history[-1])
        
        print("\nWriting detailed multi-metric report...")
        with open("translation_report.txt", "w", encoding="utf-8") as file:
            file.write("=== MULTILINGUAL SEMANTIC DRIFT REPORT ===\n")
            file.write(f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            file.write(f"[ORIGINAL SOURCE TEXT]\n{test_text}\n\n")
            
            file.write("=== INTERMEDIATE HOPS & DIAGNOSTIC METRICS ===\n\n")
            for result in history:
                hop = result.decoding_params.get("routing_path", "Unknown Hop")
                lang = result.decoding_params.get("target_lang", "Unknown")
                
                file.write(f">> {hop}\n")
                file.write(f"Text: {result.translated_text[:100]}...\n")
                
                # 1. Base Vectors (LaBSE & Window Logic)
                labse_score = foundation_grader.calculate_similarity(test_text, result.translated_text)
                file.write(f"LaBSE Global Retention: {labse_score:.4f}\n")
                
                ground_truth = VERIFIED_SNIPPETS.get(lang)
                if ground_truth:
                    fidelity = foundation_grader.calculate_windowed_similarity(result.translated_text, ground_truth)
                    file.write(f"Verified Historical Fidelity: {fidelity:.4f}\n")
                else:
                    file.write("Verified Historical Fidelity: [N/A]\n")

                # 2. Morphological Diagnostics (TTR & Density)
                ttr = foundation_grader.calculate_ttr(result.translated_text)
                file.write(f"Type-Token Ratio (Morphology): {ttr:.4f}\n")
                
                if lang in ["Mandarin Chinese", "Japanese", "Korean"]:
                    density = foundation_grader.calculate_char_density(result.translated_text)
                    file.write(f"Character-to-Meaning Density: {density:.4f}\n")

                # 3. Quality Estimation (COMET-QE)
                qe_score = comparison_engine.calculate_comet_qe(test_text, result.translated_text)
                if qe_score != 0.0:
                    file.write(f"COMET-QE Score: {qe_score:.4f}\n")
                
                file.write("-" * 40 + "\n\n")
                
            file.write("=== FINAL BACK-TRANSLATION (ENGLISH) ===\n")
            file.write(f"{final_text}\n\n")
            
            file.write("=== LLM JUDGE EVALUATION ===\n")
            file.write(f"Retention Score: {evaluation.score * 100}%\n")
            file.write(f"Analysis: {evaluation.analysis}\n")
            file.write(f"Omissions: {', '.join(evaluation.omissions) if evaluation.omissions else 'None'}\n")
            
        print("📝 Report successfully saved to 'translation_report.txt'")

if __name__ == "__main__":
    asyncio.run(main())