#!/usr/bin/env python3
"""Build paragraph-structure index - extract paragraph/poetry/list break
markers with verse anchors, so consumers can reconstruct BSB's original
paragraph and stanza layout on top of the flat per-verse display/index
output.

Output: paragraphs.jsonl with bidirectional links to verses
"""

import sys
from typing import Any, TypedDict

from .types import BOOK_CODES, USJ_FILES
from .utils import (
    BASE_DIR,
    USJ_DIR,
    check_sources_exist,
    ensure_dir,
    log,
    log_book_progress,
    read_json,
    write_json,
    write_jsonl,
)


class ParagraphBreak(TypedDict):
    id: str  # Unique ID: "GEN.p.12", "GEN.q1.3"
    b: str  # Book code
    c: int  # Chapter where the break appears
    before_v: int  # Verse number that follows this break
    marker: str  # USJ paragraph style: "p", "pmo", "b", "q1", "q2", "li1", ...


# Structural paragraph/poetry/list markers to extract. Headings (s1/s2/r/d/...)
# are handled separately by build_headings.py - this set is everything else
# USJ uses to mark paragraph, stanza, and list breaks.
PARAGRAPH_MARKERS = {
    "p",
    "pmo",
    "m",
    "mi",
    "nb",
    "b",
    "q1",
    "q2",
    "q3",
    "q4",
    "qr",
    "qa",
    "qc",
    "li1",
    "li2",
    "li3",
    "li4",
    "pc",
}


def parse_paragraphs_from_usj(usj: dict[str, Any], book_code: str) -> list[ParagraphBreak]:
    """Parse paragraph/poetry/list break markers from a USJ document."""
    breaks: list[ParagraphBreak] = []
    marker_counts: dict[str, int] = {}

    current_chapter = 0
    pending_markers: list[str] = []  # Markers waiting for the next verse

    def flush_pending(verse_num: int) -> None:
        nonlocal pending_markers
        for marker in pending_markers:
            marker_counts[marker] = marker_counts.get(marker, 0) + 1
            paragraph_break: ParagraphBreak = {
                "id": f"{book_code}.{marker}.{marker_counts[marker]}",
                "b": book_code,
                "c": current_chapter,
                "before_v": verse_num,
                "marker": marker,
            }
            breaks.append(paragraph_break)
        pending_markers = []

    def process_content(content: list[Any]) -> None:
        nonlocal current_chapter, pending_markers

        for item in content:
            if not isinstance(item, dict):
                continue

            item_type = item.get("type")
            marker = item.get("marker", "")

            if item_type == "chapter":
                # A paragraph/poetry element can start mid-verse and run to
                # the end of the chapter with no further verse inside it
                # (e.g. a closing "evening and morning..." refrain in its own
                # paragraph). There's no verse boundary to anchor a break to
                # in that case - our before_v model can't express "mid-verse"
                # - so drop it rather than fabricate a bogus before_v=1.
                pending_markers = []
                current_chapter = int(item.get("number", 0))

            elif item_type == "verse":
                verse_num = int(item.get("number", 0))
                if verse_num > 0 and pending_markers:
                    flush_pending(verse_num)

            elif item_type == "para" and marker in PARAGRAPH_MARKERS:
                # This paragraph/poetry/list element marks a structural break
                pending_markers.append(marker)
                if "content" in item:
                    process_content(item["content"])

            elif item_type == "para" and "content" in item:
                # Other paragraph type (e.g. a heading) - still walk into it
                # to find nested verses, but don't record a break for it.
                process_content(item["content"])

            elif "content" in item:
                process_content(item["content"])

    process_content(usj.get("content", []))

    # Any markers still pending here wrap trailing content at the end of the
    # book's last chapter with no further verse - same "mid-verse, no
    # boundary to anchor to" case as the chapter-transition branch above.
    # Nothing to do; they're simply dropped.

    return breaks


def build_paragraphs() -> dict[str, list[str]]:
    """Build paragraph-structure index and return verse-to-break mapping.

    Returns: dict mapping verse IDs to list of paragraph-break IDs
    """
    log("Building paragraph structure index...")

    # Check sources exist
    exists, missing = check_sources_exist()
    if not exists:
        log("ERROR: Missing source data:")
        for m in missing:
            log(f"  - {m}")
        sys.exit(1)

    # Ensure output directory exists
    ensure_dir(BASE_DIR)

    all_breaks: list[ParagraphBreak] = []
    total_books = len(BOOK_CODES)

    for book_num, book_code in BOOK_CODES.items():
        log_book_progress(book_num, total_books, book_code)

        # Get USJ file path
        usj_filename = USJ_FILES.get(book_code)
        if not usj_filename:
            continue

        usj_path = USJ_DIR / usj_filename
        if not usj_path.exists():
            continue

        # Parse USJ
        usj = read_json(usj_path)
        breaks = parse_paragraphs_from_usj(usj, book_code)
        all_breaks.extend(breaks)

        log(f"  Found {len(breaks)} paragraph breaks")

    # Build verse-to-break mapping for cross-referencing
    verse_to_paragraphs: dict[str, list[str]] = {}
    for pb in all_breaks:
        verse_id = f"{pb['b']}.{pb['c']}.{pb['before_v']}"
        verse_to_paragraphs.setdefault(verse_id, []).append(pb["id"])

    # Write paragraphs index
    output_path = BASE_DIR / "paragraphs.jsonl"
    write_jsonl(output_path, all_breaks)

    # Write stats
    stats = {
        "total_breaks": len(all_breaks),
        "by_marker": {},
        "verses_with_breaks": len(verse_to_paragraphs),
    }
    for pb in all_breaks:
        marker = pb["marker"]
        stats["by_marker"][marker] = stats["by_marker"].get(marker, 0) + 1

    stats_path = BASE_DIR / "paragraphs-stats.json"
    write_json(stats_path, stats)

    log("")
    log("=== Paragraph Structure Build Complete ===")
    log(f"Total breaks: {len(all_breaks)}")
    log(f"Verses with breaks: {len(verse_to_paragraphs)}")
    for marker, count in sorted(stats["by_marker"].items()):
        log(f"  {marker}: {count}")

    return verse_to_paragraphs


def main() -> None:
    """Main entry point."""
    build_paragraphs()


if __name__ == "__main__":
    main()
