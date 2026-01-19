"""Add Nave's Topical Bible tags to verse data."""

from pathlib import Path
from typing import Any

from .types import BOOK_CODES
from .utils import BIBLE_DB_DIR, book_number_to_code, log, read_json, verse_id


def load_topics() -> dict[str, list[str]]:
    """
    Load Nave's Topical Bible data from scrollmapper bible_databases.
    Returns a dict mapping verse IDs to lists of topic names.
    """
    # Try different possible paths for topic data
    possible_paths = [
        BIBLE_DB_DIR / "json" / "topics.json",
        BIBLE_DB_DIR / "json" / "topic_verses.json",
        BIBLE_DB_DIR / "json" / "naves_topics.json",
    ]

    topics_path = None
    for path in possible_paths:
        if path.exists():
            topics_path = path
            break

    if not topics_path:
        log("WARNING: No topics file found in bible-databases")
        log("  Checked paths:")
        for path in possible_paths:
            log(f"    - {path}")
        return {}

    log(f"Loading topics from {topics_path}")
    data = read_json(topics_path)

    # The structure depends on which file we found
    # Build mapping from verse ID to list of topics
    topics: dict[str, list[str]] = {}

    # Handle different possible data structures
    if isinstance(data, list):
        # List of topic entries
        for entry in data:
            if isinstance(entry, dict):
                topic_name = entry.get("topic") or entry.get("name") or entry.get("title")
                verses = entry.get("verses") or entry.get("references") or []

                if topic_name and verses:
                    for verse_ref in verses:
                        if isinstance(verse_ref, dict):
                            try:
                                book = book_number_to_code(verse_ref.get("book", 0))
                                chapter = verse_ref.get("chapter", 0)
                                verse_num = verse_ref.get("verse", 0)
                                vid = verse_id(book, chapter, verse_num)

                                if vid not in topics:
                                    topics[vid] = []
                                if topic_name not in topics[vid]:
                                    topics[vid].append(topic_name)
                            except (ValueError, KeyError):
                                continue
                        elif isinstance(verse_ref, str):
                            # Parse string reference like "GEN.1.1"
                            if verse_ref not in topics:
                                topics[verse_ref] = []
                            if topic_name not in topics[verse_ref]:
                                topics[verse_ref].append(topic_name)

    elif isinstance(data, dict):
        # Dict keyed by topic name or verse ID
        for key, value in data.items():
            if isinstance(value, list):
                # Key is topic name, value is list of verse references
                topic_name = key
                for verse_ref in value:
                    if isinstance(verse_ref, str):
                        if verse_ref not in topics:
                            topics[verse_ref] = []
                        if topic_name not in topics[verse_ref]:
                            topics[verse_ref].append(topic_name)
            elif isinstance(value, dict):
                # Key is verse ID, value has topic info
                vid = key
                topic_list = value.get("topics") or value.get("names") or []
                if vid not in topics:
                    topics[vid] = []
                topics[vid].extend(t for t in topic_list if t not in topics[vid])

    if topics:
        log(f"Loaded {len(topics)} verses with topics")
        total_topics = sum(len(t) for t in topics.values())
        log(f"Total topic assignments: {total_topics}")
    else:
        log("WARNING: Could not parse topics from file")

    return topics


def enrich_with_topics(
    verses: list[dict[str, Any]], topics: dict[str, list[str]]
) -> list[dict[str, Any]]:
    """Add topics to verse data."""
    enriched = []

    for verse in verses:
        vid = verse_id(verse["b"], verse["c"], verse["v"])
        verse_topics = topics.get(vid, [])

        enriched_verse = {**verse, "tp": verse_topics}
        enriched.append(enriched_verse)

    return enriched
