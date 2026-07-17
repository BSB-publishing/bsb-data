#!/usr/bin/env python3
"""Main build script - builds all outputs."""

import argparse
import sys

from .build_concordance import build_concordance
from .build_display import build_display, build_display_msb
from .build_english_concordance import build_english_concordance
from .build_geography import build_geography
from .build_greek_tsv import build_greek_tsv
from .build_hebrew_tsv import build_hebrew_tsv
from .build_lexicon import build_lexicon
from .build_proper_names import build_proper_names
from .build_versification import build_versification
from .build_helloao import build_helloao
from .build_index_cc_by import build_index_cc_by, build_index_cc_by_msb
from .build_index_cc_by_split import build_index_cc_by_split, build_index_cc_by_split_msb
from .build_index_pd import build_index_pd, build_index_pd_msb
from .build_text_only import build_text_only
from .generate_metadata import main as generate_metadata
from .utils import log
from .validate import main as validate_main


def main() -> int:
    """Main build entry point."""
    parser = argparse.ArgumentParser(description="BSB Data Build Pipeline")
    parser.add_argument("--display", action="store_true", help="Build display output only")
    parser.add_argument("--index-pd", action="store_true", help="Build PD index output only")
    parser.add_argument("--index-cc-by", action="store_true", help="Build CC-BY index output only")
    parser.add_argument(
        "--index-cc-by-split", action="store_true", help="Build split CC-BY index (per-chapter)"
    )
    parser.add_argument("--helloao", action="store_true", help="Build helloao output only")
    parser.add_argument("--text-only", action="store_true", help="Build text-only output only")
    parser.add_argument("--concordance", action="store_true", help="Build concordance index")
    parser.add_argument(
        "--english-concordance", action="store_true", help="Build English concordance index"
    )
    parser.add_argument("--geography", action="store_true", help="Build geography data")
    parser.add_argument(
        "--greek-tsv", action="store_true", help="Build Greek-only slim TSV export"
    )
    parser.add_argument(
        "--hebrew-tsv", action="store_true", help="Build Hebrew-only slim TSV export"
    )
    parser.add_argument("--proper-names", action="store_true", help="Build proper names data")
    parser.add_argument("--versification", action="store_true", help="Build versification mappings")
    parser.add_argument("--lexicon", action="store_true", help="Build extended Strong's lexicon")
    parser.add_argument("--validate", action="store_true", help="Validate outputs after building")
    parser.add_argument(
        "--all", action="store_true", help="Build all outputs (default if no options specified)"
    )
    parser.add_argument(
        "--display-msb", action="store_true", help="Build MSB display output (NT books only)"
    )
    parser.add_argument(
        "--index-pd-msb", action="store_true", help="Build MSB PD index output (NT books only)"
    )
    parser.add_argument(
        "--index-cc-by-msb",
        action="store_true",
        help="Build MSB CC-BY index output (NT books only)",
    )
    parser.add_argument(
        "--index-cc-by-split-msb",
        action="store_true",
        help="Build split MSB CC-BY index (NT books only)",
    )
    parser.add_argument(
        "--msb",
        action="store_true",
        help="Build all MSB outputs (display, index-pd, index-cc-by, index-cc-by-split)",
    )

    args = parser.parse_args()

    # Default to building all (BSB) outputs if no specific options given.
    # MSB flags are opt-in only and never trigger (or are triggered by) --all,
    # since MSB is a separate edition tree consumers request explicitly.
    build_all = args.all or not (
        args.display
        or args.index_pd
        or args.index_cc_by
        or args.index_cc_by_split
        or args.helloao
        or args.text_only
        or args.concordance
        or args.english_concordance
        or args.geography
        or args.greek_tsv
        or args.hebrew_tsv
        or args.proper_names
        or args.versification
        or args.lexicon
        or args.display_msb
        or args.index_pd_msb
        or args.index_cc_by_msb
        or args.index_cc_by_split_msb
        or args.msb
    )

    log("=== BSB Data Build Pipeline ===")
    log("")

    try:
        if args.display or build_all:
            build_display()
            log("")

        if args.index_pd or build_all:
            build_index_pd()
            log("")

        if args.index_cc_by or build_all:
            build_index_cc_by()
            log("")

        if args.index_cc_by_split or build_all:
            build_index_cc_by_split()
            log("")

        if args.helloao or build_all:
            build_helloao()
            log("")

        if args.text_only or build_all:
            build_text_only()
            log("")

        if args.concordance or build_all:
            build_concordance()
            log("")

        if args.english_concordance or build_all:
            build_english_concordance()
            log("")

        if args.geography or build_all:
            build_geography()
            log("")

        if args.greek_tsv or build_all:
            build_greek_tsv()
            log("")

        if args.hebrew_tsv or build_all:
            build_hebrew_tsv()
            log("")

        if args.proper_names or build_all:
            build_proper_names()
            log("")

        if args.versification or build_all:
            build_versification()
            log("")

        if args.lexicon or build_all:
            build_lexicon()
            log("")

        if args.display_msb or args.msb:
            build_display_msb()
            log("")

        if args.index_pd_msb or args.msb:
            build_index_pd_msb()
            log("")

        if args.index_cc_by_msb or args.msb:
            build_index_cc_by_msb()
            log("")

        if args.index_cc_by_split_msb or args.msb:
            build_index_cc_by_split_msb()
            log("")

        # Always generate metadata when building all
        if build_all:
            generate_metadata()
            log("")

        if args.validate or build_all:
            log("Running validation...")
            log("")
            return validate_main()

        log("Build complete!")
        return 0

    except KeyboardInterrupt:
        log("\nBuild interrupted by user")
        return 130
    except Exception as e:
        log(f"ERROR: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
