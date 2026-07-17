"""USJ Parser - Convert BSB-USJ format to DisplayVerse format."""

import re
from pathlib import Path
from typing import Any

from .types import DisplayVerse
from .utils import normalize_strongs, read_json

# bsb2usfm's "full Strong's" USJ marks a Strong's-tagged word that has no
# surface form in the English translation (e.g. Hebrew's untranslatable
# direct-object marker, an elided Greek article) with a literal "-" as the
# word's text.
ELISION_PLACEHOLDER = "-"

# Characters that shouldn't have a space before them (closing punctuation).
# Shared between the space-insertion logic and the boundary-whitespace
# cleanup pass in clean_words() below.
NO_SPACE_BEFORE = ',.;:!?)]\'""”’'

# Some words carry a Strong's number for a discontinuous/repeated occurrence
# of an original-language word that's already covered by a nearby English
# word (e.g. Hebrew's "between X and between Y" idiom rendered as a single
# "between"). bsb2usfm marks the second occurrence with a bare all-dots run
# (". . .", "...", etc.) instead of real text - either as its own Strong's
# tagged word, or as untagged literal text between words. A lone "." is
# ordinary terminal punctuation and is NOT part of this pattern.
def _is_ellipsis_artifact(stripped: str) -> bool:
    return bool(stripped) and stripped != "." and set(stripped) <= {".", " "}


# Known upstream data-quality defects: literal placeholder tokens that leaked
# into the public release in place of real English text. Unlike elision/
# ellipsis above, these aren't a documented convention - there's no way to
# recover the intended word, so they're stripped out (whole-word match, so a
# real word like "revved" is untouched) but flagged as a "defect" rather than
# folded silently into "elided".
GARBLED_TOKEN_RE = re.compile(r"(?i)\bvvv\b")


def _strip_garbled_tokens(text: str) -> tuple[str, bool]:
    """Remove known upstream garbage placeholder tokens from text.

    Returns (cleaned_text, found_any). Applies to both Strong's-tagged word
    text and untagged literal text, since the defect shows up in both.
    """
    cleaned, count = GARBLED_TOKEN_RE.subn("", text)
    return cleaned, count > 0


# The ellipsis/hyphen elision placeholders above are usually their own
# complete text span, but bsb2usfm sometimes glues one to adjacent real
# punctuation in the same text node instead (e.g. " . . ., " before an open
# quote, or " - ." before a close quote). These catch the placeholder as a
# substring so it can be stripped while keeping the real punctuation around
# it. A "-" used this way always stands alone (whitespace/string-boundary on
# both sides); a real hyphenated word like "seed-bearing" never has
# whitespace directly against its hyphen.
ELLIPSIS_SUBSTRING_RE = re.compile(r"\.(?:\s?\.){2,}")
ISOLATED_HYPHEN_RE = re.compile(r"(?<!\S)-(?!\S)")


# A stray space glued directly before closing punctuation within a single
# text span is never valid English typesetting - collapsed unconditionally,
# regardless of what put it there. Covers both a literal source typo like
# "Moreover , Shaphan" (one word's raw content, unrelated to any of the
# placeholder patterns above) and a space left behind after stripping a
# bracket/placeholder next to punctuation (e.g. "[the Sea] of Tiberias )").
STRAY_SPACE_BEFORE_PUNCT_RE = re.compile(r"\s+([,.;:!?)\]])")

# Mirror image of the above: a stray space glued directly after *opening*
# punctuation (e.g. "( for" as one word's raw content, same as the
# "Moreover , Shaphan" case above but on the other side). Character class
# matches the "no_space_after" set already used by the space-insertion logic
# below, for consistency.
STRAY_SPACE_AFTER_OPEN_PUNCT_RE = re.compile(r"([\"'(\[“‘])\s+")


def _collapse_stray_space_before_punct(text: str) -> str:
    return STRAY_SPACE_BEFORE_PUNCT_RE.sub(r"\1", text)


def _collapse_stray_space_after_open_punct(text: str) -> str:
    return STRAY_SPACE_AFTER_OPEN_PUNCT_RE.sub(r"\1", text)


def _strip_elision_artifacts(text: str) -> tuple[str, bool]:
    """Remove ellipsis/hyphen elision-placeholder substrings glued to real
    text/punctuation in the same span, tidying up the whitespace left behind.

    Returns (cleaned_text, found_any).
    """
    cleaned, n1 = ELLIPSIS_SUBSTRING_RE.subn("", text)
    cleaned, n2 = ISOLATED_HYPHEN_RE.subn("", cleaned)
    if n1 or n2:
        cleaned = re.sub(r"\s+", " ", cleaned)
    return cleaned, bool(n1 or n2)


# Square/curly brackets mark translator-supplied words (added for English
# grammar/clarity, not literally present in the original language) baked
# directly into the text as literal characters - both inside Strong's-tagged
# words and in untagged literal text between them (e.g. a stray footnote
# marker artifact like "[’’]"). Strip the bracket characters but keep the
# underlying words; on Strong's-tagged words, flag the entry as containing
# supplied text so consumers don't have to pattern-match on punctuation.
SUPPLIED_MARKUP_RE = re.compile(r"[\[\]{}]")


def _classify_placeholder(stripped: str) -> tuple[bool, str | None]:
    """Classify a Strong's-tagged word's text as a known placeholder that
    should be emptied rather than rendered literally.

    Returns (is_elided, reason). reason is None for the base elision case
    (matches the originally-shipped {"elided": true} schema exactly), and a
    short string for the newer sub-cases so consumers can distinguish them.
    """
    if stripped == ELISION_PLACEHOLDER:
        return True, None
    if _is_ellipsis_artifact(stripped):
        return True, "ellipsis"
    return False, None


def parse_usj_file(file_path: Path) -> list[DisplayVerse]:
    """Parse a USJ file and extract verses with Strong's numbers."""
    usj = read_json(file_path)
    return parse_usj_document(usj)


def parse_usj_document(usj: dict[str, Any]) -> list[DisplayVerse]:
    """Parse a USJ document and extract all verses."""
    verses: list[DisplayVerse] = []
    current_book = ""
    current_chapter = 0
    current_verse = 0
    current_words: list[tuple[str, str | None, dict]] = []
    current_citations: list[str] = []

    def add_text(text: str) -> None:
        """Add text to current verse."""
        nonlocal current_words
        if current_verse > 0:
            # Check if we can merge with previous word that has no strongs
            if current_words and current_words[-1][1] is None:
                current_words[-1] = (current_words[-1][0] + text, None, {})
            else:
                current_words.append((text, None, {}))

    def extract_text(content: list[Any]) -> str:
        """Extract plain text from content array."""
        text = ""
        for item in content:
            if isinstance(item, str):
                text += item
            elif isinstance(item, dict) and "content" in item:
                text += extract_text(item["content"])
        return text

    def extract_citations_from_note(note: dict[str, Any]) -> list[str]:
        """Extract citation references from a footnote."""
        citations = []
        content = note.get("content", [])
        for item in content:
            if isinstance(item, dict):
                if item.get("type") == "ref":
                    # Extract the location (e.g., "2CO 4:6")
                    loc = item.get("loc", "")
                    if loc:
                        citations.append(loc)
                elif "content" in item:
                    # Recurse into nested content
                    citations.extend(extract_citations_from_note(item))
        return citations

    def process_char(char: dict[str, Any]) -> None:
        """Process a char element (may contain Strong's number or nested content)."""
        nonlocal current_words

        marker = char.get("marker")
        content = char.get("content", [])

        if marker == "w" and char.get("strong"):
            # Word with Strong's number - only process if we're in a verse
            if current_verse > 0:
                text = extract_text(content)
                strongs = normalize_strongs(char["strong"])

                meta: dict = {}
                elided, reason = _classify_placeholder(text.strip())
                if elided:
                    text = ""
                    meta["elided"] = True
                    if reason:
                        meta["reason"] = reason
                else:
                    text, had_defect = _strip_garbled_tokens(text)
                    if SUPPLIED_MARKUP_RE.search(text):
                        meta["supplied"] = True
                        # Some source text wraps whitespace *inside* the
                        # brackets (e.g. "[ their prayers ]"), so strip
                        # leading/trailing space left behind by removing just
                        # the bracket characters - word entries never carry
                        # their own boundary whitespace; clean_words() below
                        # inserts separator spaces between entries itself.
                        text = SUPPLIED_MARKUP_RE.sub("", text).strip()
                    # Defensive: an elision placeholder glued to real
                    # punctuation within a single word's own content (not just
                    # untagged text between words) - strips the same way.
                    text, _ = _strip_elision_artifacts(text)
                    if had_defect:
                        if text.strip():
                            # Garbage token removed but real text remains
                            # (e.g. "vvv him" -> "him") - flag without emptying.
                            meta["defect"] = True
                        else:
                            # Garbage token was the entry's only content -
                            # same outcome as any other elided word.
                            text = ""
                            meta["elided"] = True
                            meta["reason"] = "defect"
                    text = _collapse_stray_space_before_punct(text)
                    text = _collapse_stray_space_after_open_punct(text)

                current_words.append((text, strongs, meta))
        else:
            # Other char types (wj, add, etc.) - may contain nested verses/words
            # Process content recursively to find verses and words inside
            process_content(content)

    def clean_words(
        words: list[tuple[str, str | None, dict]],
    ) -> list[tuple[str, str | None, dict]]:
        """Clean and normalize word array with proper spacing."""
        result: list[tuple[str, str | None, dict]] = []

        for text, strongs, meta in words:
            # Skip empty text (but keep elided placeholders - they carry a strongs code)
            if not text and not strongs:
                continue

            # Normalize whitespace in text
            text = re.sub(r"\s+", " ", text)

            # Merge with previous if both have no strongs
            if strongs is None and result and result[-1][1] is None:
                result[-1] = (result[-1][0] + text, None, {})
            else:
                # Add space before this word if needed. An elided word has empty
                # text, so look back past any such entries for the nearest
                # visible text to base the spacing decision on - and skip the
                # decision entirely when this word is itself elided (there's
                # nothing to visibly separate).
                if result and strongs is not None and text:
                    prev_text = ""
                    for pt, _, _ in reversed(result):
                        if pt:
                            prev_text = pt
                            break
                    # Check if we need a space between words
                    needs_space = False
                    if prev_text:
                        last_char = prev_text[-1]
                        first_char = text[0]
                        # Characters that shouldn't have space after them
                        no_space_after = ' "\'(["“‘'
                        # Don't add space after opening punctuation
                        if last_char in no_space_after:
                            needs_space = False
                        # Don't add space before closing punctuation
                        elif first_char in NO_SPACE_BEFORE:
                            needs_space = False
                        # Add space between words
                        else:
                            needs_space = True
                    if needs_space:
                        result.append((" ", None, {}))
                result.append((text, strongs, meta))

        # Merge adjacent non-strongs entries
        merged: list[tuple[str, str | None, dict]] = []
        for text, strongs, meta in result:
            if strongs is None and merged and merged[-1][1] is None:
                merged[-1] = (merged[-1][0] + text, None, {})
            else:
                merged.append((text, strongs, meta))

        # Collapse doubled boundary whitespace left behind when an elided
        # (empty-text) entry sits between two plain-text spans that each
        # independently carry their own boundary space (e.g. ", " + <elided>
        # + " "" -> ", ""), by looking back past empty entries the same way
        # the space-insertion pass above does.
        deduped: list[tuple[str, str | None, dict]] = []
        for text, strongs, meta in merged:
            if text.startswith(" "):
                prev_text = ""
                for pt, _, _ in reversed(deduped):
                    if pt:
                        prev_text = pt
                        break
                if prev_text.endswith(" "):
                    text = text.lstrip(" ")
            deduped.append((text, strongs, meta))

        # A boundary space can also be left with nothing to separate on its
        # *right*: an elision-artifact span (e.g. " - ") that stripped down to
        # a bare space, immediately followed - after skipping empty elided
        # entries - by closing punctuation that shouldn't have space before
        # it (e.g. "kind" + <elided> + " " + <elided> + <elided> + ".""
        # should read "kind."", not "kind ."").
        for i, (text, strongs, meta) in enumerate(deduped):
            if text.endswith(" "):
                next_text = ""
                for nt, _, _ in deduped[i + 1 :]:
                    if nt:
                        next_text = nt
                        break
                if next_text and next_text[0] in NO_SPACE_BEFORE:
                    deduped[i] = (text.rstrip(" "), strongs, meta)

        # Trim leading/trailing whitespace from first and last entries
        if deduped:
            deduped[0] = (deduped[0][0].lstrip(), deduped[0][1], deduped[0][2])
            deduped[-1] = (deduped[-1][0].rstrip(), deduped[-1][1], deduped[-1][2])

        return deduped

    def save_current_verse() -> None:
        """Save the current verse if valid."""
        nonlocal current_words, current_citations
        if current_book and current_chapter > 0 and current_verse > 0 and current_words:
            # Clean up words - merge adjacent null-strongs entries and add spacing
            cleaned_words = clean_words(current_words)

            # Convert to list format for JSON serialization. Words with metadata
            # (elided, supplied, ...) get a third element so display-safe
            # consumers can concatenate `w[0]` directly without ever seeing a
            # placeholder token or raw bracket markup.
            w_list: list[tuple[str, str | None] | tuple[str, str | None, dict]] = [
                (t, s, meta) if meta else (t, s) for t, s, meta in cleaned_words
            ]

            verse_data: DisplayVerse = {
                "b": current_book,
                "c": current_chapter,
                "v": current_verse,
                "w": w_list,
            }

            # Add citations if present
            if current_citations:
                verse_data["citations"] = current_citations.copy()  # type: ignore

            verses.append(verse_data)
        current_words = []
        current_citations = []

    def process_content(content: list[Any]) -> None:
        """Recursive function to process content."""
        nonlocal current_book, current_chapter, current_verse, current_words, current_citations

        for item in content:
            if isinstance(item, str):
                # Plain text (punctuation, spaces, etc.)
                stripped = item.strip()
                if stripped or item == " ":
                    # Untagged text can carry the same garbage-token,
                    # bracket/brace, and ellipsis/hyphen elision-placeholder
                    # artifacts as Strong's-tagged words - including glued to
                    # real punctuation in the same span (e.g. " . . ., " or
                    # " - ."). There's no per-word Strong's alignment on plain
                    # text, so just clean it silently rather than flag it.
                    cleaned, _ = _strip_garbled_tokens(item)
                    cleaned = SUPPLIED_MARKUP_RE.sub("", cleaned)
                    cleaned, _ = _strip_elision_artifacts(cleaned)
                    cleaned = _collapse_stray_space_before_punct(cleaned)
                    cleaned = _collapse_stray_space_after_open_punct(cleaned)
                    add_text(cleaned)
            elif isinstance(item, dict):
                item_type = item.get("type")

                if item_type == "book":
                    # Extract book code
                    current_book = item.get("code", "")
                elif item_type == "chapter":
                    # Save previous verse if exists
                    save_current_verse()
                    current_chapter = int(item.get("number", 0))
                    current_verse = 0
                elif item_type == "verse":
                    # Save previous verse if exists
                    save_current_verse()
                    current_verse = int(item.get("number", 0))
                    current_words = []
                    current_citations = []
                elif item_type == "para":
                    # Skip section headers (s1, s2, etc.) and references (r)
                    marker = item.get("marker", "")
                    if marker in ("s1", "s2", "s3", "s4", "s5", "r", "sr", "mr", "d"):
                        # Don't include section headers or references in verse text
                        continue
                    # Process paragraph content
                    if "content" in item:
                        process_content(item["content"])
                elif item_type == "char":
                    # Character style - may contain Strong's number
                    process_char(item)
                elif item_type == "note":
                    # Footnote - extract citations but don't include note text
                    citations = extract_citations_from_note(item)
                    if citations:
                        current_citations.extend(citations)
                    # Don't process note content as verse text
                elif "content" in item:
                    # Other elements with content - recurse
                    process_content(item["content"])

    # Process the document
    process_content(usj.get("content", []))

    # Save final verse
    save_current_verse()

    return verses


def get_book_code_from_filename(filename: str) -> str:
    """
    Get book code from USJ filename.
    Format: "01GENBSB_full_strongs.usj" -> "GEN"
    """
    match = re.match(r"^\d{2}([A-Z0-9]+)BSB", filename)
    if not match:
        raise ValueError(f"Cannot extract book code from filename: {filename}")
    return match.group(1)
