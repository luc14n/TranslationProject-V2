import random
import asyncio
from typing import Optional, Any, List, Dict
from dotenv import load_dotenv
from chaintest import BaseTranslationProvider, TranslationResult

# This loads the variables from .env into your system's environment
load_dotenv() 

# Now when you initialize the client, it will automatically find GEMINI_API_KEY
from google import genai
client = genai.Client()
# The dynamic dictionary: Families mapped to lists of representative languages
FAMILY_DICTIONARY = {
    "English": ["English"], # Starting point remains fixed
    "Germanic": ["German", "Dutch", "Swedish"],
    "Romantic": ["Spanish", "French", "Italian"],
    "Slavic": ["Russian", "Polish", "Czech"],
    "Western Asian": ["Arabic", "Hebrew", "Farsi"],
    "Eastern Asian": ["Mandarin Chinese", "Japanese", "Korean"]
}

async def run_stochastic_chain(
    initial_text: str, 
    family_chain: List[str], 
    family_dict: Dict[str, List[str]],
    provider: BaseTranslationProvider
) -> List[TranslationResult]:
    
    results_history = []
    current_text = initial_text
    
    for i in range(len(family_chain) - 1):
        source_family = family_chain[i]
        target_family = family_chain[i+1]
        
        # Randomly select a concrete language for this specific run
        source_lang = random.choice(family_dict[source_family])
        target_lang = random.choice(family_dict[target_family])
        
        # LOGGING IS CRITICAL HERE: We print/store exactly what was chosen
        path_log = f"Hop {i+1}: {source_family} ({source_lang}) -> {target_family} ({target_lang})"
        print(f"Executing {path_log}...")
        
        result = await provider.translate(
            text=current_text, 
            source_lang=source_lang, 
            target_lang=target_lang
        )
        
        # We can attach our custom path log to the result object for the DB later
        result.decoding_params["routing_path"] = path_log 
        
        results_history.append(result)
        
        if result.error or not result.translated_text:
            print(f"Chain broken at {path_log}. Error: {result.error}")
            break
            
        current_text = result.translated_text
        
    return results_history