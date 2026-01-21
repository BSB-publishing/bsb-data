# BSB Bible Data Preprocessing Pipeline

Convert BSB-USJ source data into optimized formats for web display and vector DB indexing.

## Output Repository

**Generated data is published to a separate repository for easy downstream use:**

👉 **[bsb-data-output](https://github.com/USER/bsb-data-output)** *(update USER to your GitHub username)*

This repository contains only the build scripts. The output data is automatically
rebuilt and published when source data changes.

## Output Formats

### Display Format (`base/display/`)
- **License:** CC0 (Public Domain)
- **Format:** JSONL files per chapter, organized by book
- **Purpose:** Compact format for web rendering with Strong's numbers and original language text

Structure: `display/{BOOK}/{BOOK}{chapter}.jsonl` (e.g., `display/GEN/GEN1.jsonl`)

Each line is a single verse with both English and original language (Hebrew/Greek):
```json
{"eng":{1:[["In the beginning","H7225"],["God","H430"],["created","H1254"],...]},"heb":{1:[["בְּרֵאשִׁ֖ית","H7225"],["בָּרָ֣א","H1254"],["אֱלֹהִ֑ים","H430"],...]}}}
```

For NT books, `grk` is used instead of `heb`:
```json
{"eng":{1:[["[This is the] record","G976"],["of [the] genealogy","G1078"],...]},"grk":{1:[["Βίβλος","G976"],["γενέσεως","G1078"],...]}}}
```

### Index Format - PD (`vector-db/index-pd/`)
- **License:** CC0 (Public Domain)
- **Format:** Single JSONL file with all verses
- **Purpose:** Vector DB indexing with cross-references, topics, and glosses

```json
{"id":"GEN.1.1","b":"GEN","c":1,"v":1,"t":"In the beginning...","s":["H7225","H430"],"x":["JHN.1.1"],"tp":["Creation"],"g":{"H7225":"beginning"}}
```

### Index Format - CC-BY (`vector-db/index-cc-by/`)
- **License:** CC-BY 4.0 (includes OSHB morphology)
- **Format:** Single JSONL file with all verses
- **Purpose:** Vector DB indexing with full morphological data

Includes all PD fields plus morphology:
```json
{"m":[{"s":"H7225","m":"HR/Ncfsa","p":"noun","l":"רֵאשִׁית"},...]}
```

### Index Format - CC-BY Split (`base/index-cc-by/`)
- **License:** CC-BY 4.0 (includes OSHB morphology)
- **Format:** JSONL files per chapter, organized by book
- **Purpose:** Same as vector-db/index-cc-by but split for easier chapter-by-chapter access

Structure: `index-cc-by/{BOOK}/{BOOK}{chapter}.jsonl` (e.g., `index-cc-by/GEN/GEN1.jsonl`)

### Concordance Index (`base/concordance/`)
- **License:** CC0 (Public Domain)
- **Format:** JSON and JSONL mapping Strong's numbers to verse references
- **Purpose:** Pre-built concordance for lookups by Strong's number

```json
{"H1": ["GEN.1.1", "GEN.2.4", ...], "H2": ["GEN.4.1", ...], "G1": ["MAT.1.1", ...]}
```

Also available as JSONL for streaming:
```json
{"strongs": "H1", "verses": ["GEN.1.1", "GEN.2.4", ...]}
```

### HelloAO Format (`base/helloao/`)
- **License:** CC0 (Public Domain)
- **Format:** JSON files organized by book/chapter
- **Purpose:** Compatible with [bible.helloao.org](https://bible.helloao.org/docs/) API format

Structure: `helloao/{BOOK}/{chapter}.json` plus `helloao/books.json`
```json
{
  "translation": {"id": "BSB", "name": "Berean Standard Bible", ...},
  "book": {"id": "GEN", "name": "Genesis", "number": 1},
  "chapter": {"number": 1, "content": [{"type": "verse", "number": 1, "content": [...]}], "footnotes": []}
}
```

### Text-Only Format (`base/text-only/`)
- **License:** CC0 (Public Domain)
- **Format:** Plain text files, one per chapter
- **Purpose:** Simple text extraction for processing, search indexing, or reading

Filename pattern: `{BOOK}_{CCC}_BSB.txt` (e.g., `GEN_001_BSB.txt`)
Each verse on its own line.

### Headings Index (`base/headings.jsonl`)
- **License:** CC0 (Public Domain)
- **Format:** Single JSONL file with all section headings
- **Purpose:** Section headings with cross-references to verses

```json
{"id":"GEN.s1.1","b":"GEN","c":1,"before_v":1,"level":"s1","text":"The Creation"}
{"id":"GEN.s1.2","b":"GEN","c":1,"before_v":3,"level":"s1","text":"The First Day"}
```

Headings are cross-linked with verses via the `h` field in index files.

## For Downstream Projects

The data repository is designed to be extended. Projects can:

1. **Fork** the data repo and add custom enrichments
2. **Submodule** it into your project: `git submodule add https://github.com/.../bsb-data-output.git data/bsb`
3. **Clone** and extend with your own data

All schemas use `additionalProperties: true` to allow adding custom fields.

See the [data repository](https://github.com/USER/bsb-data-output) for full documentation.

## Local Development

### Requirements

- Python 3.10+
- Git
- No external Python dependencies (uses only standard library)

### Quick Start

```bash
# 1. Clone this repo
git clone https://github.com/USER/bsb-data.git
cd bsb-data

# 2. Fetch source data
bash scripts/fetch-sources.sh

# 3. Build all outputs
python3 -m scripts.build

# 4. Or build specific outputs
python3 -m scripts.build --display
python3 -m scripts.build --index-pd
python3 -m scripts.build --index-cc-by
python3 -m scripts.build --index-cc-by-split
python3 -m scripts.build --concordance
python3 -m scripts.build --helloao
python3 -m scripts.build --text-only

# 5. Validate outputs
python3 -m scripts.validate
```

### Output Location

After building, output is in:
```
output/
├── base/
│   ├── display/          # Per-chapter JSONL files with eng + heb/grk
│   ├── index-cc-by/      # CC-BY index split by chapter
│   ├── concordance/      # Strong's to verse mapping
│   ├── helloao/          # HelloAO-compatible JSON by book/chapter
│   ├── text-only/        # Plain text files per chapter
│   └── headings.jsonl    # Section headings index
├── vector-db/
│   ├── index-pd/         # Public Domain index with headings
│   └── index-cc-by/      # CC-BY index with morphology
├── schema/               # JSON schemas
├── VERSION.json          # Source versions
└── README.md             # Generated readme for data repo
```

## Automated Publishing

A GitHub Actions workflow automatically:

1. Runs weekly (or on manual trigger)
2. Checks if source repositories have changed
3. Rebuilds all outputs if needed
4. Publishes to the data repository with version tags

### Setup for Your Fork

1. Create a data repository (e.g., `bsb-data-output`)
2. Create a Personal Access Token with `repo` scope
3. Add secrets/variables to this repository:
   - **Secret:** `DATA_REPO_TOKEN` - your PAT
   - **Variable:** `DATA_REPO` - data repo name (default: `bsb-data-output`)
   - **Variable:** `DATA_REPO_OWNER` - owner (default: same as this repo)

## Data Sources

| Source | License | Content |
|--------|---------|---------|
| [BSB-USJ](https://github.com/BSB-publishing/bsb2usfm) | CC0 | Berean Standard Bible text with Strong's numbers |
| [Scrollmapper Bible DBs](https://github.com/scrollmapper/bible_databases) | Public Domain | TSK cross-references, Nave's topics, Strong's lexicon |
| [OpenScriptures OSHB](https://github.com/openscriptures/morphhb) | CC-BY 4.0 | Hebrew morphology data |

## Repository Structure

```
bsb-data/
├── .github/
│   └── workflows/
│       └── build-publish.yml  # Automated build & publish
├── scripts/
│   ├── build.py               # Main build script
│   ├── build_display.py       # Build display output
│   ├── build_index_pd.py      # Build PD index
│   ├── build_index_cc_by.py   # Build CC-BY index
│   ├── build_index_cc_by_split.py  # Build CC-BY index split by chapter
│   ├── build_concordance.py   # Build Strong's concordance
│   ├── build_helloao.py       # Build HelloAO-compatible output
│   ├── build_text_only.py     # Build text-only output
│   ├── build_headings.py      # Extract section headings
│   ├── convert_usj.py         # USJ parser
│   ├── enrich_*.py            # Enrichment modules
│   ├── fetch-sources.sh       # Download source data
│   ├── generate_metadata.py   # Generate schemas & VERSION.json
│   ├── schemas.py             # JSON schema definitions
│   ├── validate.py            # Output validation
│   ├── types.py               # Type definitions
│   └── utils.py               # Shared utilities
├── sources/                    # Downloaded source data (gitignored)
├── output/                     # Build output (gitignored, published separately)
├── README.md
├── LICENSE-CC0.md
├── LICENSE-CC-BY.md
└── ATTRIBUTION.md
```

## License

- **Code in this repo:** CC0 (Public Domain)
- **Output data:** See individual directories (CC0 or CC-BY 4.0)

See [LICENSE-CC0.md](LICENSE-CC0.md) and [LICENSE-CC-BY.md](LICENSE-CC-BY.md) for full license texts.
