#!/usr/bin/env python3
"""Build display output - JSONL files for web rendering."""

import sys
from pathlib import Path

from .convert_usj import parse_usj_file
from .types import BOOK_CODES, USJ_FILES, BuildStats
from .utils import (
    DISPLAY_DIR,
    USJ_DIR,
    check_sources_exist,
    ensure_dir,
    extract_strongs_from_words,
    format_file_size,
    log,
    log_book_progress,
    write_json,
    write_jsonl,
)


def build_display() -> BuildStats:
    """Build display output files."""
    log("Building display output...")

    # Check sources exist
    exists, missing = check_sources_exist()
    if not exists:
        log("ERROR: Missing source data:")
        for m in missing:
            log(f"  - {m}")
        sys.exit(1)

    # Ensure output directory exists
    ensure_dir(DISPLAY_DIR)

    stats = BuildStats()
    total_books = len(BOOK_CODES)

    for book_num, book_code in BOOK_CODES.items():
        log_book_progress(book_num, total_books, book_code)

        # Get USJ file path
        usj_filename = USJ_FILES.get(book_code)
        if not usj_filename:
            log(f"  WARNING: No USJ file mapping for {book_code}")
            continue

        usj_path = USJ_DIR / usj_filename
        if not usj_path.exists():
            log(f"  WARNING: USJ file not found: {usj_path}")
            continue

        # Parse USJ file
        verses = parse_usj_file(usj_path)

        # Update stats
        stats.books_processed += 1
        stats.total_verses += len(verses)

        for verse in verses:
            words = verse["w"]
            stats.total_words += len(words)
            for text, strongs in words:
                if strongs:
                    stats.words_with_strongs += 1
                    stats.unique_strongs.add(strongs)

        # Write JSONL file for this book
        output_path = DISPLAY_DIR / f"{book_code}.jsonl"
        write_jsonl(output_path, verses)

        log(f"  Wrote {len(verses)} verses to {output_path.name}")

    # Write stats
    stats_path = DISPLAY_DIR / "stats.json"
    write_json(stats_path, stats.to_dict())

    # Log summary
    log("")
    log("=== Display Build Complete ===")
    log(f"Books processed: {stats.books_processed}")
    log(f"Total verses: {stats.total_verses}")
    log(f"Total words: {stats.total_words}")
    log(f"Words with Strong's: {stats.words_with_strongs}")
    log(f"Unique Strong's numbers: {len(stats.unique_strongs)}")

    # Calculate total output size
    total_size = sum(f.stat().st_size for f in DISPLAY_DIR.glob("*.jsonl"))
    log(f"Total output size: {format_file_size(total_size)}")

    return stats


def main() -> None:
    """Main entry point."""
    build_display()


if __name__ == "__main__":
    main()
