#!/usr/bin/env python3
"""Build display output - JSON files per chapter for web rendering."""

import csv
import re
import sys
from collections import defaultdict
from pathlib import Path

from .types import BOOK_CODES, BuildStats
from .utils import (
    BSB_TABLES_FILE,
    DISPLAY_DIR,
    ensure_dir,
    format_file_size,
    log,
    write_json,
)

# Unicode directional control characters to remove
DIRECTIONAL_CHARS = re.compile(
    r"[\u200e\u200f\u202a\u202b\u202c\u202d\u202e\u2066\u2067\u2068\u2069]"
)


def clean_text(text: str) -> str:
    """Remove Unicode directional control characters from text."""
    return DIRECTIONAL_CHARS.sub("", text)


# Mapping from TSV VerseId book names to our 3-letter codes
BOOK_NAME_TO_CODE = {
    "Genesis": "GEN",
    "Exodus": "EXO",
    "Leviticus": "LEV",
    "Numbers": "NUM",
    "Deuteronomy": "DEU",
    "Joshua": "JOS",
    "Judges": "JDG",
    "Ruth": "RUT",
    "1 Samuel": "1SA",
    "2 Samuel": "2SA",
    "1 Kings": "1KI",
    "2 Kings": "2KI",
    "1 Chronicles": "1CH",
    "2 Chronicles": "2CH",
    "Ezra": "EZR",
    "Nehemiah": "NEH",
    "Esther": "EST",
    "Job": "JOB",
    "Psalm": "PSA",
    "Proverbs": "PRO",
    "Ecclesiastes": "ECC",
    "Song of Solomon": "SNG",
    "Isaiah": "ISA",
    "Jeremiah": "JER",
    "Lamentations": "LAM",
    "Ezekiel": "EZK",
    "Daniel": "DAN",
    "Hosea": "HOS",
    "Joel": "JOL",
    "Amos": "AMO",
    "Obadiah": "OBA",
    "Jonah": "JON",
    "Micah": "MIC",
    "Nahum": "NAM",
    "Habakkuk": "HAB",
    "Zephaniah": "ZEP",
    "Haggai": "HAG",
    "Zechariah": "ZEC",
    "Malachi": "MAL",
    "Matthew": "MAT",
    "Mark": "MRK",
    "Luke": "LUK",
    "John": "JHN",
    "Acts": "ACT",
    "Romans": "ROM",
    "1 Corinthians": "1CO",
    "2 Corinthians": "2CO",
    "Galatians": "GAL",
    "Ephesians": "EPH",
    "Philippians": "PHP",
    "Colossians": "COL",
    "1 Thessalonians": "1TH",
    "2 Thessalonians": "2TH",
    "1 Timothy": "1TI",
    "2 Timothy": "2TI",
    "Titus": "TIT",
    "Philemon": "PHM",
    "Hebrews": "HEB",
    "James": "JAS",
    "1 Peter": "1PE",
    "2 Peter": "2PE",
    "1 John": "1JN",
    "2 John": "2JN",
    "3 John": "3JN",
    "Jude": "JUD",
    "Revelation": "REV",
}


def parse_verse_id(verse_id: str) -> tuple[str, int, int] | None:
    """Parse VerseId like 'Genesis 1:1' to (book_code, chapter, verse)."""
    if not verse_id or ":" not in verse_id:
        return None

    parts = verse_id.rsplit(":", 1)
    if len(parts) != 2:
        return None

    book_chapter, verse_str = parts
    last_space = book_chapter.rfind(" ")
    if last_space == -1:
        return None

    book_name = book_chapter[:last_space]
    chapter_str = book_chapter[last_space + 1 :]

    book_code = BOOK_NAME_TO_CODE.get(book_name)
    if not book_code:
        return None

    try:
        chapter = int(chapter_str)
        verse = int(verse_str)
        return (book_code, chapter, verse)
    except ValueError:
        return None


def load_tsv_data() -> dict:
    """Load and parse the BSB tables TSV file.

    Returns a nested dict structure for building display files.
    """
    log("Loading BSB tables TSV...")

    if not BSB_TABLES_FILE.exists():
        log(f"ERROR: BSB tables file not found: {BSB_TABLES_FILE}")
        log("  Run: bash scripts/fetch-sources.sh")
        sys.exit(1)

    # Track current verse context for rows without VerseId
    current_book = None
    current_chapter = None
    current_verse = None

    # Structure: {book: {chapter: {verse: {"eng": {sort: [text, strongs]}, "orig": {sort: [text, strongs]}, "lang": "heb"|"grk"}}}}
    data: dict = defaultdict(
        lambda: defaultdict(lambda: defaultdict(lambda: {"eng": {}, "orig": {}, "lang": "heb"}))
    )

    with open(BSB_TABLES_FILE, encoding="utf-8") as f:
        reader = csv.reader(f, delimiter="\t")
        next(reader)  # Skip header

        for row in reader:
            if len(row) < 19:
                continue

            heb_sort = row[0]
            grk_sort = row[1]
            bsb_sort = row[2]
            language = row[4]
            orig_text = row[5]  # Hebrew or Greek text
            strongs_heb = row[10] if len(row) > 10 else ""
            strongs_grk = row[11] if len(row) > 11 else ""
            verse_id_col = row[12] if len(row) > 12 else ""
            eng_text = row[18] if len(row) > 18 else ""

            # Parse verse reference if present
            if verse_id_col and ":" in verse_id_col:
                parsed = parse_verse_id(verse_id_col)
                if parsed:
                    current_book, current_chapter, current_verse = parsed

            # Skip if we don't have a current verse context
            if not current_book or not current_chapter or not current_verse:
                continue

            # Skip non-Hebrew/Greek rows
            if language not in ("Hebrew", "Greek"):
                continue

            # Skip empty content rows
            if not orig_text.strip() and not eng_text.strip():
                continue

            # Determine Strong's number and sort order
            if language == "Hebrew":
                strongs_raw = strongs_heb.strip()
                strongs = f"H{strongs_raw}" if strongs_raw and strongs_raw != "-" else None
                orig_sort = int(heb_sort) if heb_sort.isdigit() else 999999
            else:  # Greek
                strongs_raw = strongs_grk.strip()
                strongs = f"G{strongs_raw}" if strongs_raw else None
                orig_sort = int(grk_sort) if grk_sort.isdigit() else 999999

            # Clean up strongs
            if strongs:
                strongs = strongs.split()[0].rstrip("-").rstrip()
                if strongs in ("H", "G", "H-", "G-"):
                    strongs = None

            bsb_sort_num = int(bsb_sort) if bsb_sort.isdigit() else 999999

            verse_data = data[current_book][current_chapter][current_verse]
            verse_data["lang"] = "heb" if language == "Hebrew" else "grk"

            # Store English text with BSB sort order
            if eng_text.strip():
                verse_data["eng"][bsb_sort_num] = [clean_text(eng_text.strip()), strongs]

            # Store original text (Hebrew/Greek) with original sort order
            if orig_text.strip():
                cleaned_orig = clean_text(orig_text.strip())
                verse_data["orig"][orig_sort] = [cleaned_orig, strongs]

    log(f"  Loaded data for {len(data)} books")
    return data


def build_display() -> BuildStats:
    """Build display output files."""
    log("Building display output...")

    # Load TSV data
    tsv_data = load_tsv_data()

    if not tsv_data:
        log("ERROR: No data loaded from TSV")
        sys.exit(1)

    # Ensure output directory exists
    ensure_dir(DISPLAY_DIR)

    stats = BuildStats()
    total_books = len(BOOK_CODES)
    files_written = 0

    for book_num, book_code in BOOK_CODES.items():
        log(f"Processing {book_code} ({book_num}/{total_books})")

        if book_code not in tsv_data:
            log(f"  WARNING: No data for {book_code}")
            continue

        book_data = tsv_data[book_code]
        stats.books_processed += 1

        # Create book directory
        book_dir = DISPLAY_DIR / book_code
        ensure_dir(book_dir)

        for chapter in sorted(book_data.keys()):
            chapter_data = book_data[chapter]

            # Build chapter output structure
            eng_output = {}
            orig_output = {}
            lang_key = "heb"  # Default, will be overwritten

            for verse in sorted(chapter_data.keys()):
                verse_data = chapter_data[verse]
                lang_key = verse_data["lang"]

                # Build English word list (sorted by BSB order)
                eng_words = []
                for sort_key in sorted(verse_data["eng"].keys()):
                    eng_words.append(verse_data["eng"][sort_key])

                # Build original language word list (sorted by sort order)
                orig_words = []
                for sort_key in sorted(verse_data["orig"].keys()):
                    orig_words.append(verse_data["orig"][sort_key])

                if eng_words:
                    eng_output[str(verse)] = eng_words
                    stats.total_verses += 1
                    stats.total_words += len(eng_words)
                    for text, strongs in eng_words:
                        if strongs:
                            stats.words_with_strongs += 1
                            stats.unique_strongs.add(strongs)

                if orig_words:
                    orig_output[str(verse)] = orig_words

            if eng_output:
                # Build final chapter JSON
                chapter_output = {
                    "eng": eng_output,
                    lang_key: orig_output,
                }

                # Write chapter file as compact JSON
                output_path = book_dir / f"{book_code}{chapter}.json"
                write_json(output_path, chapter_output, compact=True)
                files_written += 1

        log(f"  Wrote {len(book_data)} chapters")

    # Write stats
    stats_dict = stats.to_dict()
    stats_dict["files_written"] = files_written
    stats_path = DISPLAY_DIR / "stats.json"
    write_json(stats_path, stats_dict)

    # Log summary
    log("")
    log("=== Display Build Complete ===")
    log(f"Books processed: {stats.books_processed}")
    log(f"Total verses: {stats.total_verses}")
    log(f"Total words: {stats.total_words}")
    log(f"Words with Strong's: {stats.words_with_strongs}")
    log(f"Unique Strong's numbers: {len(stats.unique_strongs)}")
    log(f"Chapter files written: {files_written}")

    # Calculate total output size
    total_size = sum(f.stat().st_size for f in DISPLAY_DIR.rglob("*.json"))
    log(f"Total output size: {format_file_size(total_size)}")

    return stats


def main() -> None:
    """Main entry point."""
    build_display()


if __name__ == "__main__":
    main()
