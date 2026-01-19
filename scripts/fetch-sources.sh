#!/bin/bash
# Fetch all source data for BSB Bible Data preprocessing
# Downloads only the specific files needed, not full repositories
#
# Usage:
#   bash scripts/fetch-sources.sh           # Download missing files and update changed files (default)
#   bash scripts/fetch-sources.sh --force   # Re-download all files

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
SOURCES_DIR="$PROJECT_DIR/sources"
TIMESTAMP_FILE="$SOURCES_DIR/.last_fetch"

# Parse command line arguments
FORCE=false
while [[ $# -gt 0 ]]; do
    case $1 in
        --force|-f)
            FORCE=true
            shift
            ;;
        --help|-h)
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --force, -f    Force re-download of all files"
            echo "  --help, -h     Show this help message"
            echo ""
            echo "By default, the script downloads missing files and checks for updates."
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

echo "=== BSB Data Source Fetcher ==="
echo "Project directory: $PROJECT_DIR"
echo "Sources directory: $SOURCES_DIR"
if [ "$FORCE" = true ]; then
    echo "Mode: FORCE (re-downloading all files)"
else
    echo "Mode: Default (download missing files and check for updates)"
fi
echo ""
echo "This script downloads only the required files (~305MB total)"
echo "instead of cloning full repositories (~12GB)."
echo ""

# Create sources directory if needed
mkdir -p "$SOURCES_DIR"

# Function to check if we should download a file
# Returns 0 (true) if should download, 1 (false) if should skip
should_download() {
    local file="$1"
    local url="$2"

    # Force mode: always download
    if [ "$FORCE" = true ]; then
        return 0
    fi

    # File doesn't exist: download
    if [ ! -f "$file" ]; then
        return 0
    fi

    # Check remote timestamp to see if file has been updated
    # Use subshell to prevent set -e from exiting on errors
    local remote_date
    remote_date=$(curl -sI "$url" 2>/dev/null | grep -i "last-modified" | cut -d' ' -f2- | tr -d '\r') || true

    if [ -n "$remote_date" ]; then
        # Cross-platform date parsing (works on both macOS and Linux)
        local remote_ts="0"
        local local_ts="0"

        if date --version >/dev/null 2>&1; then
            # GNU date (Linux)
            remote_ts=$(date -d "$remote_date" "+%s" 2>/dev/null) || remote_ts="0"
            local_ts=$(stat -c "%Y" "$file" 2>/dev/null) || local_ts="0"
        else
            # BSD date (macOS)
            remote_ts=$(date -j -f "%a, %d %b %Y %H:%M:%S %Z" "$remote_date" "+%s" 2>/dev/null) || remote_ts="0"
            local_ts=$(stat -f "%m" "$file" 2>/dev/null) || local_ts="0"
        fi

        if [ "$remote_ts" != "0" ] && [ "$local_ts" != "0" ] && [ "$remote_ts" -gt "$local_ts" ]; then
            return 0  # Remote is newer
        fi
    fi

    # File exists and is up to date (or couldn't check): skip
    return 1
}

# Function to download a file with optional update checking
download_file() {
    local url="$1"
    local dest="$2"
    local desc="$3"

    if should_download "$dest" "$url"; then
        echo "  Downloading $desc..."
        curl -sfL "$url" -o "$dest" || { echo "    Warning: Failed to download $desc"; return 1; }
        return 0
    else
        return 1  # Skipped
    fi
}

# Book file patterns: 01-39 OT, 41-67 NT (no 40)
BOOKS=(
    "01GENBSB" "02EXOBSB" "03LEVBSB" "04NUMBSB" "05DEUBSB"
    "06JOSBSB" "07JDGBSB" "08RUTBSB" "091SABSB" "102SABSB"
    "111KIBSB" "122KIBSB" "131CHBSB" "142CHBSB" "15EZRBSB"
    "16NEHBSB" "17ESTBSB" "18JOBBSB" "19PSABSB" "20PROBSB"
    "21ECCBSB" "22SNGBSB" "23ISABSB" "24JERBSB" "25LAMBSB"
    "26EZKBSB" "27DANBSB" "28HOSBSB" "29JOLBSB" "30AMOBSB"
    "31OBABSB" "32JONBSB" "33MICBSB" "34NAMBSB" "35HABBSB"
    "36ZEPBSB" "37HAGBSB" "38ZECBSB" "39MALBSB"
    "41MATBSB" "42MRKBSB" "43LUKBSB" "44JHNBSB" "45ACTBSB"
    "46ROMBSB" "471COBSB" "482COBSB" "49GALBSB" "50EPHBSB"
    "51PHPBSB" "52COLBSB" "531THBSB" "542THBSB" "551TIBSB"
    "562TIBSB" "57TITBSB" "58PHMBSB" "59HEBBSB" "60JASBSB"
    "611PEBSB" "622PEBSB" "631JNBSB" "642JNBSB" "653JNBSB"
    "66JUDBSB" "67REVBSB"
)

# Plain USJ files use short book codes
PLAIN_BOOKS=(
    "GEN" "EXO" "LEV" "NUM" "DEU"
    "JOS" "JDG" "RUT" "1SA" "2SA"
    "1KI" "2KI" "1CH" "2CH" "EZR"
    "NEH" "EST" "JOB" "PSA" "PRO"
    "ECC" "SNG" "ISA" "JER" "LAM"
    "EZK" "DAN" "HOS" "JOL" "AMO"
    "OBA" "JON" "MIC" "NAM" "HAB"
    "ZEP" "HAG" "ZEC" "MAL"
    "MAT" "MRK" "LUK" "JHN" "ACT"
    "ROM" "1CO" "2CO" "GAL" "EPH"
    "PHP" "COL" "1TH" "2TH" "1TI"
    "2TI" "TIT" "PHM" "HEB" "JAS"
    "1PE" "2PE" "1JN" "2JN" "3JN"
    "JUD" "REV"
)

# OT books in OSHB naming convention
OSHB_BOOKS=(
    "Gen" "Exod" "Lev" "Num" "Deut"
    "Josh" "Judg" "Ruth" "1Sam" "2Sam"
    "1Kgs" "2Kgs" "1Chr" "2Chr" "Ezra"
    "Neh" "Esth" "Job" "Ps" "Prov"
    "Eccl" "Song" "Isa" "Jer" "Lam"
    "Ezek" "Dan" "Hos" "Joel" "Amos"
    "Obad" "Jonah" "Mic" "Nah" "Hab"
    "Zeph" "Hag" "Zech" "Mal"
)

# ============================================================================
# 1. Fetch BSB-USJ data (CC0)
# ============================================================================
echo "--- Fetching BSB-USJ data (CC0) ---"

# 1a. Download strongs_full USJ files (with Strong's numbers)
USJ_STRONGS_DIR="$SOURCES_DIR/bsb-usj/results_usj/strongs_full"
mkdir -p "$USJ_STRONGS_DIR"

STRONGS_COUNT=0
STRONGS_DOWNLOADED=0
BASE_URL="https://raw.githubusercontent.com/BSB-publishing/bsb2usfm/main/results_usj/strongs_full"

for BOOK in "${BOOKS[@]}"; do
    FILE="${BOOK}_full_strongs.usj"
    if download_file "$BASE_URL/$FILE" "$USJ_STRONGS_DIR/$FILE" "$FILE"; then
        ((STRONGS_DOWNLOADED++))
    fi
    ((STRONGS_COUNT++))
done

USJ_COUNT=$(ls -1 "$USJ_STRONGS_DIR"/*.usj 2>/dev/null | wc -l | tr -d ' ')
if [ "$STRONGS_DOWNLOADED" -gt 0 ]; then
    echo "Downloaded $STRONGS_DOWNLOADED Strong's USJ files (total: $USJ_COUNT)"
else
    echo "Strong's USJ files up to date ($USJ_COUNT files)"
fi

# 1b. Download plain USJ files (without Strong's numbers - for text extraction)
USJ_PLAIN_DIR="$SOURCES_DIR/bsb-usj/results_usj/plain"
mkdir -p "$USJ_PLAIN_DIR"

PLAIN_COUNT=0
PLAIN_DOWNLOADED=0
BASE_URL="https://raw.githubusercontent.com/BSB-publishing/bsb2usfm/main/results_usj"

for BOOK in "${PLAIN_BOOKS[@]}"; do
    FILE="${BOOK}.usj"
    if download_file "$BASE_URL/$FILE" "$USJ_PLAIN_DIR/$FILE" "$FILE"; then
        ((PLAIN_DOWNLOADED++))
    fi
    ((PLAIN_COUNT++))
done

USJ_PLAIN_COUNT=$(ls -1 "$USJ_PLAIN_DIR"/*.usj 2>/dev/null | wc -l | tr -d ' ')
if [ "$PLAIN_DOWNLOADED" -gt 0 ]; then
    echo "Downloaded $PLAIN_DOWNLOADED plain USJ files (total: $USJ_PLAIN_COUNT)"
else
    echo "Plain USJ files up to date ($USJ_PLAIN_COUNT files)"
fi
echo ""

# ============================================================================
# 2. Fetch cross-references from Scrollmapper Bible Databases
# ============================================================================
echo "--- Fetching Cross-References (Public Domain) ---"
XREF_DIR="$SOURCES_DIR/bible-databases/sources/extras"
mkdir -p "$XREF_DIR"

XREF_DOWNLOADED=0
BASE_URL="https://raw.githubusercontent.com/scrollmapper/bible_databases/master/sources/extras"

for i in 0 1 2 3 4 5 6; do
    FILE="cross_references_$i.json"
    if download_file "$BASE_URL/$FILE" "$XREF_DIR/$FILE" "$FILE"; then
        ((XREF_DOWNLOADED++))
    fi
done

# Also get the text version for reference
download_file "$BASE_URL/cross_references.txt" "$XREF_DIR/cross_references.txt" "cross_references.txt"

XREF_COUNT=$(ls -1 "$XREF_DIR"/cross_references*.json 2>/dev/null | wc -l | tr -d ' ')
if [ "$XREF_DOWNLOADED" -gt 0 ]; then
    echo "Downloaded $XREF_DOWNLOADED cross-reference files (total: $XREF_COUNT)"
else
    echo "Cross-reference files up to date ($XREF_COUNT files)"
fi
echo ""

# ============================================================================
# 3. Fetch OpenScriptures OSHB (CC-BY 4.0)
# ============================================================================
echo "--- Fetching OpenScriptures OSHB (CC-BY 4.0) ---"
OSHB_DIR="$SOURCES_DIR/oshb/wlc"
mkdir -p "$OSHB_DIR"

OSHB_DOWNLOADED=0
BASE_URL="https://raw.githubusercontent.com/openscriptures/morphhb/master/wlc"

for BOOK in "${OSHB_BOOKS[@]}"; do
    FILE="${BOOK}.xml"
    if download_file "$BASE_URL/$FILE" "$OSHB_DIR/$FILE" "$FILE"; then
        ((OSHB_DOWNLOADED++))
    fi
done

OSHB_COUNT=$(ls -1 "$OSHB_DIR"/*.xml 2>/dev/null | wc -l | tr -d ' ')
if [ "$OSHB_DOWNLOADED" -gt 0 ]; then
    echo "Downloaded $OSHB_DOWNLOADED OSHB XML files (total: $OSHB_COUNT)"
else
    echo "OSHB files up to date ($OSHB_COUNT files)"
fi
echo ""

# ============================================================================
# Summary
# ============================================================================

# Update timestamp file
date -u "+%Y-%m-%dT%H:%M:%SZ" > "$TIMESTAMP_FILE"

echo "=== Fetch complete ==="
echo ""
echo "Source data locations:"
echo "  BSB-USJ (Strong's): $USJ_STRONGS_DIR/ ($USJ_COUNT files)"
echo "  BSB-USJ (plain):    $USJ_PLAIN_DIR/ ($USJ_PLAIN_COUNT files)"
echo "  Cross-refs:         $XREF_DIR/ ($XREF_COUNT files)"
echo "  OSHB:               $OSHB_DIR/ ($OSHB_COUNT files)"
echo ""

# Show total size
TOTAL_SIZE=$(du -sh "$SOURCES_DIR" 2>/dev/null | cut -f1)
echo "Total source data size: $TOTAL_SIZE"

# Show last fetch time
if [ -f "$TIMESTAMP_FILE" ]; then
    echo "Last fetch: $(cat "$TIMESTAMP_FILE")"
fi

echo ""
echo "Next steps:"
echo "  source venv/bin/activate"
echo "  python3 -m scripts.build"
