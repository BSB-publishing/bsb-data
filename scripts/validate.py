#!/usr/bin/env python3
"""Validate output data integrity."""

import re
import sys
from pathlib import Path

from .types import BOOK_CODES
from .utils import (
    DISPLAY_DIR,
    INDEX_CC_BY_DIR,
    INDEX_PD_DIR,
    format_file_size,
    is_valid_strongs,
    log,
    read_json,
    read_jsonl,
)

# Expected verse counts (approximate, for validation)
# Note: BSB follows modern critical text, so counts differ from KJV/traditional (31102)
# Index outputs (from USJ): ~30969 verses
# Display output (from TSV): ~30819 verses (TSV excludes some section headings/markers)
EXPECTED_INDEX_VERSES_MIN = 30900
EXPECTED_INDEX_VERSES_MAX = 31102
EXPECTED_DISPLAY_VERSES_MIN = 30700
EXPECTED_DISPLAY_VERSES_MAX = 31102


def validate_display_output() -> tuple[bool, list[str]]:
    """Validate display output files (folder structure: {BOOK}/{BOOK}{Chapter}.json)."""
    errors: list[str] = []
    total_verses = 0
    total_chapters = 0

    log("Validating display output...")

    if not DISPLAY_DIR.exists():
        errors.append(f"Display directory not found: {DISPLAY_DIR}")
        return False, errors

    # Check each book folder exists and has valid chapter files
    for book_code in BOOK_CODES.values():
        book_dir = DISPLAY_DIR / book_code

        if not book_dir.exists():
            errors.append(f"Missing book directory: {book_dir}")
            continue

        # Find all chapter files for this book
        chapter_files = sorted(book_dir.glob(f"{book_code}*.json"))
        if not chapter_files:
            errors.append(f"No chapter files found in {book_dir}")
            continue

        for chapter_file in chapter_files:
            total_chapters += 1
            try:
                data = read_json(chapter_file)

                # New structure: {"eng": {...}, "heb": {...}} or {"eng": {...}, "grk": {...}}
                if "eng" not in data:
                    errors.append(f"{chapter_file.name}: Missing 'eng' section")
                    continue

                eng_data = data["eng"]
                if not isinstance(eng_data, dict):
                    errors.append(f"{chapter_file.name}: 'eng' is not a dict")
                    continue

                # Count verses (keys are verse numbers)
                verse_count = len(eng_data)
                total_verses += verse_count

                # Validate verse structure (spot check first verse)
                for verse_num, words in list(eng_data.items())[:1]:
                    if not isinstance(words, list):
                        errors.append(f"{chapter_file.name}:v{verse_num}: words not a list")
                        continue
                    for i, word_pair in enumerate(words):
                        if not isinstance(word_pair, list) or len(word_pair) != 2:
                            errors.append(
                                f"{chapter_file.name}:v{verse_num}:w{i}: Invalid word pair"
                            )
                            continue
                        text, strongs = word_pair
                        if strongs and not is_valid_strongs(strongs):
                            errors.append(
                                f"{chapter_file.name}:v{verse_num}:w{i}: Invalid Strong's: {strongs}"
                            )

                # Check for Hebrew/Greek section
                if "heb" not in data and "grk" not in data:
                    errors.append(f"{chapter_file.name}: Missing 'heb' or 'grk' section")

            except Exception as e:
                errors.append(f"Error reading {chapter_file}: {e}")

    # Check verse count
    if total_verses == 0:
        errors.append("No verses found in display output")
    else:
        log(f"  Total chapters: {total_chapters}")
        log(f"  Total verses: {total_verses}")
        if total_verses < EXPECTED_DISPLAY_VERSES_MIN or total_verses > EXPECTED_DISPLAY_VERSES_MAX:
            errors.append(
                f"Unexpected verse count: {total_verses} (expected {EXPECTED_DISPLAY_VERSES_MIN}-{EXPECTED_DISPLAY_VERSES_MAX})"
            )

    return len(errors) == 0, errors


def validate_index_output(
    index_dir: Path, name: str, check_morphology: bool = False
) -> tuple[bool, list[str]]:
    """Validate index output file."""
    errors: list[str] = []

    log(f"Validating {name} index output...")

    if not index_dir.exists():
        errors.append(f"Index directory not found: {index_dir}")
        return False, errors

    index_file = index_dir / "bible-index.jsonl"
    if not index_file.exists():
        errors.append(f"Index file not found: {index_file}")
        return False, errors

    try:
        verses = read_jsonl(index_file)
        log(f"  Total verses: {len(verses)}")

        if len(verses) == 0:
            errors.append("No verses found in index output")
            return False, errors

        # Validate verse structure
        seen_ids: set[str] = set()
        strongs_set: set[str] = set()

        for i, verse in enumerate(verses):
            # Check required fields
            required_fields = ["id", "b", "c", "v", "t", "s", "x", "tp", "g"]
            if check_morphology:
                required_fields.append("m")

            for field in required_fields:
                if field not in verse:
                    errors.append(f"Verse {i}: Missing '{field}' field")

            # Check ID uniqueness
            vid = verse.get("id", "")
            if vid in seen_ids:
                errors.append(f"Duplicate verse ID: {vid}")
            seen_ids.add(vid)

            # Validate ID format
            if not re.match(r"^[A-Z0-9]{3}\.\d+\.\d+$", vid):
                errors.append(f"Invalid verse ID format: {vid}")

            # Validate Strong's numbers
            strongs_list = verse.get("s", [])
            for s in strongs_list:
                if not is_valid_strongs(s):
                    errors.append(f"Verse {vid}: Invalid Strong's number: {s}")
                strongs_set.add(s)

            # Validate cross-references format
            xrefs = verse.get("x", [])
            for xref in xrefs:
                if not re.match(r"^[A-Z0-9]{3}\.\d+\.\d+$", xref):
                    errors.append(f"Verse {vid}: Invalid cross-reference format: {xref}")

            # Validate glosses match Strong's numbers
            glosses = verse.get("g", {})
            for gs in glosses.keys():
                if not is_valid_strongs(gs):
                    errors.append(f"Verse {vid}: Invalid Strong's in gloss: {gs}")

            # Validate morphology if present
            if check_morphology:
                morph_entries = verse.get("m", [])
                for entry in morph_entries:
                    if not isinstance(entry, dict):
                        errors.append(f"Verse {vid}: Invalid morphology entry")
                        continue
                    if "s" not in entry or "m" not in entry:
                        errors.append(f"Verse {vid}: Incomplete morphology entry")

        log(f"  Unique Strong's numbers: {len(strongs_set)}")
        log(f"  File size: {format_file_size(index_file.stat().st_size)}")

        # Check verse count
        if len(verses) < EXPECTED_INDEX_VERSES_MIN or len(verses) > EXPECTED_INDEX_VERSES_MAX:
            errors.append(
                f"Unexpected verse count: {len(verses)} (expected {EXPECTED_INDEX_VERSES_MIN}-{EXPECTED_INDEX_VERSES_MAX})"
            )

    except Exception as e:
        errors.append(f"Error reading index file: {e}")

    return len(errors) == 0, errors


def validate_no_cc_by_in_pd() -> tuple[bool, list[str]]:
    """Verify PD output does not contain CC-BY content (morphology)."""
    errors: list[str] = []

    log("Checking PD output for CC-BY content...")

    index_file = INDEX_PD_DIR / "bible-index.jsonl"
    if not index_file.exists():
        log("  Skipping (PD index not built)")
        return True, errors

    try:
        verses = read_jsonl(index_file)

        for verse in verses:
            if "m" in verse and verse["m"]:
                errors.append(
                    f"CC-BY content (morphology) found in PD output: {verse.get('id', 'unknown')}"
                )
                break  # One error is enough

        if not errors:
            log("  OK - No CC-BY content in PD output")

    except Exception as e:
        errors.append(f"Error checking PD output: {e}")

    return len(errors) == 0, errors


def main() -> int:
    """Main validation entry point."""
    log("=== BSB Data Validation ===")
    log("")

    all_valid = True
    all_errors: list[str] = []

    # Validate display output
    valid, errors = validate_display_output()
    if not valid:
        all_valid = False
        all_errors.extend(errors)
    log("")

    # Validate PD index
    valid, errors = validate_index_output(INDEX_PD_DIR, "PD", check_morphology=False)
    if not valid:
        all_valid = False
        all_errors.extend(errors)
    log("")

    # Validate CC-BY index
    valid, errors = validate_index_output(INDEX_CC_BY_DIR, "CC-BY", check_morphology=True)
    if not valid:
        all_valid = False
        all_errors.extend(errors)
    log("")

    # Check for license compliance
    valid, errors = validate_no_cc_by_in_pd()
    if not valid:
        all_valid = False
        all_errors.extend(errors)
    log("")

    # Summary
    log("=== Validation Summary ===")
    if all_valid:
        log("All validations passed!")
        return 0
    else:
        log(f"Validation failed with {len(all_errors)} error(s):")
        for error in all_errors[:20]:  # Show first 20 errors
            log(f"  - {error}")
        if len(all_errors) > 20:
            log(f"  ... and {len(all_errors) - 20} more errors")
        return 1


if __name__ == "__main__":
    sys.exit(main())
