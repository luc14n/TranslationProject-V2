import json
import os
import sqlite3
from pathlib import Path


def init_dummy_database(db_name: str = "./data/app_data.db"):
    """Creates a SQLite database using schema.sql and populates sample data."""

    # Optional: remove the existing DB to start fresh with the new schema
    if os.path.exists(db_name):
        os.remove(db_name)
        # return  # Skip re-initialization if the database already exists

    con = sqlite3.connect(db_name)
    cur = con.cursor()

    # Determine the path to schema.sql
    # Assumes app/database.py and data/schema.sql directory structure
    schema_path = Path(__file__).parent.parent / "data" / "schema.sql"

    if schema_path.exists():
        with open(schema_path, "r", encoding="utf-8") as f:
            cur.executescript(f.read())
    else:
        print(f"Warning: Could not find schema.sql at {schema_path}")
        return

    # --- Populate Initial Data ---

    # 1. Languages
    dict_path = (
        Path(__file__).parent.parent / "data" / "init" / "LanguageDictionary.json"
    )
    with open(dict_path, "r", encoding="utf-8") as f:
        language_data = json.load(f)

    languages = []
    for family, langs in language_data.items():
        for lang_name, details in langs.items():
            lang_id, name, region = details
            languages.append((lang_id.upper(), name, family, region))

    cur.executemany(
        "INSERT INTO Languages (LangID, Name, Family, Region) VALUES (?, ?, ?, ?)",
        languages,
    )

    # 2. Models
    dict_path = Path(__file__).parent.parent / "data" / "init" / "Models.json"
    with open(dict_path, "r", encoding="utf-8") as f:
        model_data = json.load(f)

    models = [(name, versions[0]) for name, versions in model_data.items()]

    cur.executemany("INSERT INTO Model (Name, Version) VALUES (?, ?)", models)

    # 3. Settings & Ratings - Uninitialized for now, can be populated as needed

    # 4. Documents
    documents = [
        ("Welcome Guide", "Manual", "EN", "A short introductory manual."),
        ("Product Description", "Marketing", "ES", "Marketing copy for the new tool."),
    ]
    cur.executemany(
        "INSERT INTO Documents (Name, Type, OriginalLanguage, Description) VALUES (?, ?, ?, ?)",
        documents,
    )

    # 5. Refrences (References)
    refrences = [
        ("Intro_Greeting", 1, "EN", "Welcome to our application."),
        (
            "Feature_List",
            1,
            "EN",
            "This application supports translation and data viewing.",
        ),
        ("Promo_Title", 2, "ES", "¡Descubre la nueva herramienta!"),
    ]
    cur.executemany(
        "INSERT INTO Refrences (Name, Document, Language, Text) VALUES (?, ?, ?, ?)",
        refrences,
    )

    # 6. Translations
    translations = [
        (
            "Intro_Greeting_ES",
            1,  # Refrence ID
            None,  # Translation ID (if referencing another translation)
            "ES",  # Language
            "EN",  # PreviousLanguage
            "Bienvenido a nuestra aplicación.",  # Text
            1,  # Model ID
            1,  # Settings ID
            1,  # Ratings ID
        ),
        (
            "Feature_List_FR",
            2,  # Refrence ID
            None,
            "FR",  # Language
            "EN",  # PreviousLanguage
            "Cette application prend en charge la traduction et la visualisation des données.",  # Text
            2,  # Model ID
            1,
            2,
        ),
    ]
    cur.executemany(
        """
        INSERT INTO Translations
        (Name, Refrence, Translation, Language, PreviousLanguage, Text, Model, Settings, Ratings)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """,
        translations,
    )

    con.commit()
    con.close()


if __name__ == "__main__":
    # Test initialization locally
    init_dummy_database()
    print("Database initialized and populated with dummy data based on schema.sql.")
