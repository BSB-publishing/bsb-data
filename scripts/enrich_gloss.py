"""Add Strong's glosses/definitions to verse data."""

from pathlib import Path
from typing import Any

from .utils import BIBLE_DB_DIR, extract_strongs_from_words, log, read_json


def load_strongs_lexicon() -> dict[str, str]:
    """
    Load Strong's lexicon data.
    Returns a dict mapping Strong's numbers to short glosses.
    """
    # Try different possible paths for Strong's data
    possible_paths = [
        BIBLE_DB_DIR / "json" / "strongs.json",
        BIBLE_DB_DIR / "json" / "strongs_dictionary.json",
        BIBLE_DB_DIR / "json" / "hebrew_strongs.json",
        BIBLE_DB_DIR / "json" / "greek_strongs.json",
    ]

    lexicon: dict[str, str] = {}

    for path in possible_paths:
        if path.exists():
            log(f"Loading Strong's data from {path}")
            data = read_json(path)

            if isinstance(data, dict):
                for key, value in data.items():
                    # Normalize the Strong's number
                    strongs_num = key.upper()
                    if not strongs_num.startswith(("H", "G")):
                        # Try to infer from filename
                        if "hebrew" in path.name.lower():
                            strongs_num = f"H{key}"
                        elif "greek" in path.name.lower():
                            strongs_num = f"G{key}"

                    # Extract gloss from value
                    if isinstance(value, str):
                        gloss = value
                    elif isinstance(value, dict):
                        gloss = (
                            value.get("gloss")
                            or value.get("short_definition")
                            or value.get("definition", "")[:100]
                            or value.get("strongs_def", "")[:100]
                        )
                    else:
                        continue

                    if gloss and strongs_num not in lexicon:
                        lexicon[strongs_num] = gloss

            elif isinstance(data, list):
                for entry in data:
                    if isinstance(entry, dict):
                        strongs_num = (
                            entry.get("strongs") or entry.get("number") or entry.get("id", "")
                        )
                        if strongs_num:
                            strongs_num = strongs_num.upper()
                            gloss = (
                                entry.get("gloss")
                                or entry.get("short_definition")
                                or entry.get("definition", "")[:100]
                            )
                            if gloss and strongs_num not in lexicon:
                                lexicon[strongs_num] = gloss

    if lexicon:
        log(f"Loaded {len(lexicon)} Strong's definitions")
    else:
        log("WARNING: Could not load Strong's lexicon data")
        log("  Checked paths:")
        for path in possible_paths:
            log(f"    - {path} (exists: {path.exists()})")

    return lexicon


def enrich_with_glosses(
    verses: list[dict[str, Any]], lexicon: dict[str, str]
) -> list[dict[str, Any]]:
    """Add Strong's glosses to verse data."""
    enriched = []

    for verse in verses:
        # Get Strong's numbers from this verse
        words = verse.get("w", [])
        strongs_nums = extract_strongs_from_words(words)

        # Build glosses dict for this verse
        glosses: dict[str, str] = {}
        for s in strongs_nums:
            if s in lexicon:
                glosses[s] = lexicon[s]

        enriched_verse = {**verse, "g": glosses}
        enriched.append(enriched_verse)

    return enriched
