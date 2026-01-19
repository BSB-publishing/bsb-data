#!/usr/bin/env python3
"""Build text-only output format using plain USJ files via usfmtc.

Output format: {3 letter bookname}_{three digit chapter number}_BSB.txt
with the text of each verse on a new line (no verse numbers).
"""

import sys
from pathlib import Path

import usfmtc

from .types import BOOK_CODES
from .utils import (
    BASE_DIR,
    USJ_PLAIN_DIR,
    ensure_dir,
    log,
    log_book_progress,
)

# Output directory
TEXT_ONLY_DIR = BASE_DIR / "text-only"

# Plain USJ file mapping (short book codes)
PLAIN_USJ_FILES: dict[str, str] = {code: f"{code}.usj" for code in BOOK_CODES.values()}


def extract_verses_from_usj(usj_path: Path) -> dict[int, dict[int, str]]:
    """Extract verses from a plain USJ file using usfmtc.

    Returns: {chapter_num: {verse_num: text}}
    """
    doc = usfmtc.readFile(str(usj_path))
    root = doc.getroot()

    verses: dict[int, dict[int, str]] = {}
    current_chapter = 0

    for elem in root.iter():
        if elem.tag == "chapter":
            current_chapter = int(elem.get("number", 0))
            if current_chapter not in verses:
                verses[current_chapter] = {}
        elif elem.tag == "verse":
            verse_num_str = elem.get("number", "")
            # Skip verse ranges like "1-2" and end markers
            if "-" in verse_num_str or elem.get("eid"):
                continue
            try:
                verse_num = int(verse_num_str)
            except ValueError:
                continue
            # Get the text that follows the verse marker
            text = elem.tail.strip() if elem.tail else ""
            if current_chapter and verse_num and text:
                if verse_num not in verses.get(current_chapter, {}):
                    verses[current_chapter][verse_num] = text
                else:
                    verses[current_chapter][verse_num] += " " + text

    return verses


def build_text_only() -> None:
    """Build text-only output from plain USJ files."""
    log("Building text-only output...")

    # Check plain USJ sources exist
    if not USJ_PLAIN_DIR.exists():
        log(f"ERROR: Plain USJ files not found at {USJ_PLAIN_DIR}")
        log("Run: bash scripts/fetch-sources.sh")
        sys.exit(1)

    # Ensure output directory exists
    ensure_dir(TEXT_ONLY_DIR)

    total_books = len(BOOK_CODES)
    total_chapters = 0
    total_verses = 0

    for book_num, book_code in BOOK_CODES.items():
        log_book_progress(book_num, total_books, book_code)

        # Get plain USJ file path
        usj_filename = PLAIN_USJ_FILES.get(book_code)
        if not usj_filename:
            log(f"  WARNING: No USJ file mapping for {book_code}")
            continue

        usj_path = USJ_PLAIN_DIR / usj_filename
        if not usj_path.exists():
            log(f"  WARNING: USJ file not found: {usj_path}")
            continue

        # Extract verses using usfmtc
        try:
            chapters = extract_verses_from_usj(usj_path)
        except Exception as e:
            log(f"  ERROR parsing {usj_path}: {e}")
            continue

        # Write each chapter to a file
        book_chapters = 0
        for ch_num in sorted(chapters.keys()):
            ch_verses = chapters[ch_num]

            # Format: {3 letter bookname}_{three digit chapter number}_BSB.txt
            filename = f"{book_code}_{ch_num:03d}_BSB.txt"
            filepath = TEXT_ONLY_DIR / filename

            lines: list[str] = []
            for v_num in sorted(ch_verses.keys()):
                verse_text = ch_verses[v_num]
                lines.append(verse_text)
                total_verses += 1

            filepath.write_text("\n".join(lines) + "\n", encoding="utf-8")
            book_chapters += 1

        total_chapters += book_chapters
        log(f"  Wrote {book_chapters} chapters")

    log("")
    log("=== Text-Only Build Complete ===")
    log(f"Output directory: {TEXT_ONLY_DIR}")
    log(f"Total chapters: {total_chapters}")
    log(f"Total verses: {total_verses}")


def main() -> None:
    """Main entry point."""
    build_text_only()


if __name__ == "__main__":
    main()
