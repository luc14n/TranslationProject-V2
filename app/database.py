import json
import os
import sqlite3
from pathlib import Path


def init_dummy_database(
    db_name: str = str(Path(__file__).parent.parent / "data" / "app_data.db"),
):
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
            name, region = details
            languages.append((name, family, region))

    cur.executemany(
        "INSERT INTO Languages (Name, Family, Region) VALUES (?, ?, ?)",
        languages,
    )

    # 2. Models
    dict_path = Path(__file__).parent.parent / "data" / "init" / "Models.json"
    with open(dict_path, "r", encoding="utf-8") as f:
        model_data = json.load(f)

    models = [(name, versions[0]) for name, versions in model_data.items()]

    cur.executemany("INSERT INTO Model (Name, Version) VALUES (?, ?)", models)

    # 3. Settings & Ratings - Uninitialized for now, can be populated as needed
    for _ in range(3):
        cur.execute("INSERT INTO Settings DEFAULT VALUES")
        cur.execute("INSERT INTO Ratings DEFAULT VALUES")

    # 4. Documents, References, and Translations
    documents_dir = Path(__file__).parent.parent / "data" / "init" / "documents"

    if documents_dir.exists():
        for doc_file in documents_dir.glob("*.json"):
            if doc_file.name == ".template.json":
                continue
            with open(doc_file, "r", encoding="utf-8") as f:
                doc_data = json.load(f)

            name = doc_data.get("name")
            doc_type = doc_data.get("type")
            original_language = doc_data.get("original_language")
            source_text = doc_data.get("source_text")
            translations = doc_data.get("translations", {})

            # Insert Document
            cur.execute(
                "INSERT INTO Documents (Name, Type, OriginalLanguage, Description) VALUES (?, ?, ?, ?)",
                (name, doc_type, original_language, ""),
            )
            document_id = cur.lastrowid

            # Insert Reference
            ref_name = f"{name}_Source"
            cur.execute(
                "INSERT INTO Refrences (Name, Document, Language, Text) VALUES (?, ?, ?, ?)",
                (ref_name, document_id, original_language, source_text),
            )

            # Insert Vetted Translations as References
            for lang, text in translations.items():
                trans_name = f"{name}_{lang}"
                cur.execute(
                    "INSERT INTO Refrences (Name, Document, Language, Text) VALUES (?, ?, ?, ?)",
                    (trans_name, document_id, lang, text),
                )

    con.commit()
    con.close()


if __name__ == "__main__":
    # Test initialization locally
    init_dummy_database()
    print("Database initialized and populated with dummy data based on schema.sql.")
