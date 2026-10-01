# Implementation Plan: Parse PDF Corpus to Markdown

**Branch**: `002-parse-pdf-markdown` | **Date**: 2026-10-01 | **Spec**: [spec.md](file:///Users/gabrielcordeiro/Repos/graphrag-experiment/specs/002-parse-pdf-markdown/spec.md)

**Input**: Feature specification from [`specs/002-parse-pdf-markdown/spec.md`](file:///Users/gabrielcordeiro/Repos/graphrag-experiment/specs/002-parse-pdf-markdown/spec.md)

---

## Summary

The objective of this feature is to provide a dedicated, reliable CLI tool (`src/parse_corpus.py`) that reads the document entries defined in the YAML manifest (`manifest.yml`), locates the corresponding downloaded PDF files in `corpus/`, and sequentially converts each PDF into a standardized Markdown file persisted into `corpus_md/`.

Unlike the binary PDF `corpus/` folder (which is ignored by Git with `.gitkeep`), the generated Markdown corpus folder (`corpus_md/`) will be **actively version-controlled in Git** (exempt from `.gitignore`), allowing team members and downstream GraphRAG indexing pipelines to directly consume high-fidelity Markdown representations of the legal documents without re-downloading or re-parsing binary PDFs.

Per the user's explicit design choice, the conversion engine will utilize **`pymupdf4llm`**, which leverages MuPDF to deliver fast, LLM-optimized Markdown conversions with faithful extraction of headings, lists, bold/italics, and tables. Each generated Markdown document is enriched with structured YAML frontmatter containing metadata attributes (`selection_id`, `title`, `group`, `source_id`, `url`) from the manifest.

Processing occurs strictly one by one in sequence. The tool provides real-time progress and summary statistics to `stdout`, logs missing or corrupted PDF errors to `stderr` without crashing the batch, supports idempotent re-runs, and exits with code 0 on batch completion.

---

## Technical Context

**Language/Version**: Python 3.11+ (running Python 3.12.14 / 3.14.7 compatible)  
**Primary Dependencies**: `pymupdf4llm >= 0.0.17` (PDF to Markdown conversion), `pyyaml >= 6.0` (manifest and frontmatter handling), Python standard library (`argparse`, `pathlib`, `sys`, `time`)  
**Storage**: Filesystem Markdown storage at `./corpus_md/<selection_id>.md` (tracked in Git version control)  
**Input Source**: PDF files at `./corpus/<selection_id>.pdf` mapped via `./manifest.yml`  
**Testing**: `unittest` (Python built-in standard library)  
**Target Platform**: Cross-platform POSIX / macOS / Linux CLI  
**Project Type**: CLI utility  
**Execution Model**: Strictly sequential processing (one by one, no concurrency)  
**Constraints**: Minimal code (KISS & YAGNI), CLI-first, standard streams separation, versioned Markdown directory (`corpus_md/` NOT in `.gitignore`)  
**Scale/Scope**: Manifest containing 12 institutional legal documents (scalable to hundreds)  

---

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Compliance Check | Status | Notes |
|---|---|---|---|
| **I. Python-First** | Code must be 100% Python 3.11+, prioritizing standard library and standard conventions. | **PASS** | Implemented entirely in Python using standard library (`argparse`, `pathlib`, `sys`, `time`) and essential domain libraries (`pymupdf4llm`, `pyyaml`). |
| **II. Código Mínimo (KISS & YAGNI)** | Minimal code to solve the specified problem; no premature abstractions, base classes, or unused helper layers. | **PASS** | Single flat script `src/parse_corpus.py` with direct procedural functions: read manifest, parse PDF via `pymupdf4llm.to_markdown()`, prepend YAML frontmatter, write file. |
| **III. Sem Casos de Borda Especulativos** | Only concrete, documented edge cases covered; no speculative recovery or complex retries. | **PASS** | Handles only concrete scenarios: missing input PDF file, unreadable/corrupt PDF, missing manifest, directory creation, and idempotent overwrite. |
| **IV. Interface Exclusiva via CLI** | System interaction exclusively via CLI; standard `argparse`, stdout for output, stderr for errors. | **PASS** | CLI entry point with optional manifest path, `--manifest`, `--corpus-dir`, and `--output-dir`. Clean stdout progress and stderr diagnostics. |

---

## Project Structure

### Documentation (this feature)

```text
specs/002-parse-pdf-markdown/
├── spec.md              # Feature specification
├── plan.md              # Implementation plan (this file)
├── research.md          # Phase 0: Technical decisions and library evaluation
├── data-model.md        # Phase 1: Entity schemas and filesystem mapping
├── quickstart.md        # Phase 1: Verification guide and runnable scenarios
├── contracts/
│   └── cli-contract.md  # Phase 1: CLI arguments, options, and streams contract
└── checklists/
    └── requirements.md  # Specification quality checklist
```

### Source Code (repository root)

```text
manifest.yml              # Canonical document manifest
corpus/                   # Input binary PDF documents (ignored by Git except .gitkeep)
└── .gitkeep
corpus_md/                # Output Markdown documents (versioned & tracked in Git)
├── 001-constituicao-federal.md
├── ...
└── 012-marco-civil-internet.md

src/
├── __init__.py
├── download_corpus.py    # Feature 001 CLI
└── parse_corpus.py       # Feature 002 CLI entry point: sequential PDF -> Markdown parser

tests/
├── __init__.py
├── test_download_corpus.py # Feature 001 tests
└── test_parse_corpus.py    # Feature 002 unit tests: CLI args, frontmatter, parsing, missing/corrupt handling

requirements.txt          # Python dependencies (pyyaml, pymupdf4llm)
.gitignore                # Git exclusions (corpus/* preserved; corpus_md explicitly tracked)
```

**Structure Decision**: A flat, direct single-project layout without layers of abstraction, adhering directly to the GraphRAG Experiment Constitution ("Flat is better than nested; Simple is better than complex").

---

## Complexity Tracking

*No constitutional violations or complex patterns introduced. Zero complexity debt.*
