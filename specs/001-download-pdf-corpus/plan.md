# Implementation Plan: Download PDF Corpus from YAML List

**Branch**: `001-download-pdf-corpus` | **Date**: 2026-09-30 | **Spec**: [spec.md](file:///Users/gabrielcordeiro/Repos/graphrag-experiment/specs/001-download-pdf-corpus/spec.md)

**Input**: Feature specification from [`specs/001-download-pdf-corpus/spec.md`](file:///Users/gabrielcordeiro/Repos/graphrag-experiment/specs/001-download-pdf-corpus/spec.md)

---

## Summary

The goal of this feature is to provide a clean, reliable CLI tool that reads a YAML document manifest (a top-level list of document metadata entries) and downloads all referenced PDF files into a local `corpus/` folder. Files are saved as `corpus/<selection_id>.pdf`. The CLI accepts an optional manifest path parameter with an automatic fallback to the fixed project manifest (`manifest.yml`).

To keep the repository structure consistent across fresh clones, the `corpus/` directory is tracked in Git via a `corpus/.gitkeep` marker file, while `.gitignore` excludes all downloaded PDF binaries (`corpus/*` and `!corpus/.gitkeep`).

To protect target servers from traffic bursts and rate-limiting penalties, downloads execute **strictly in sequence** (one by one, never concurrently) with a configurable **polite pause** (default 1.0s) between successive requests. For transient errors (HTTP 429, 5xx, and connection timeouts), the tool applies an **exponential backoff retry** strategy (up to 3 retries, doubling interval) before recording a failure and continuing the batch.

The tool guarantees idempotent execution by replacing existing files, automatically configures `.gitignore` and `corpus/.gitkeep`, provides real-time progress and summary metrics on `stdout`, reports item errors and retry notices to `stderr`, and exits with code 0 on successful batch completion.

Technical approach: A flat, lightweight Python module using `pyyaml` for manifest deserialization, Python's built-in `urllib.request` for streaming downloads, `time.sleep` for delays and backoff, `argparse` for CLI commands, and atomic file replacement (`os.replace`) to prevent file corruption.

---

## Technical Context

**Language/Version**: Python 3.11+ (running Python 3.14.7)  
**Primary Dependencies**: `pyyaml >= 6.0` (YAML parsing), Python standard library (`urllib.request`, `time`, `argparse`, `pathlib`, `os`, `shutil`)  
**Storage**: Filesystem binary storage at `./corpus/<selection_id>.pdf` with `./corpus/.gitkeep` tracking  
**Default Manifest**: `./manifest.yml` at repository root  
**Testing**: `unittest` (Python built-in standard library)  
**Target Platform**: Cross-platform POSIX / macOS / Linux CLI  
**Project Type**: CLI utility  
**Execution Model**: Strictly sequential processing (no multithreading or asyncio)  
**Polite Delay**: Default 1.0s between consecutive successful downloads (`--delay`)  
**Error Resilience**: Exponential backoff retry for HTTP 429/5xx and timeouts (up to 3 attempts, doubling wait times: 1s, 2s, 4s)  
**Constraints**: Zero unnecessary dependencies, atomic file writes via temporary buffer (`.tmp`), idempotent execution, courteous server access, directory preserved in Git via `.gitkeep`  
**Scale/Scope**: Manifests ranging from individual files up to several hundred documents per run  

---

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Compliance Check | Status | Notes |
|---|---|---|---|
| **I. Python-First** | Code must be 100% Python 3.11+, prioritizing standard library. | **PASS** | Implemented in Python 3.14 using standard library modules (`urllib.request`, `time`, `argparse`, `pathlib`), with only `pyyaml` added for manifest parsing. |
| **II. Código Mínimo (KISS & YAGNI)** | Minimal code to solve the problem; no premature abstractions, interfaces, or class hierarchies. | **PASS** | Sequential `for` loop and procedural retry function (~25 LOC). No third-party concurrency or retry frameworks (`tenacity`, `asyncio`). |
| **III. Sem Casos de Borda Especulativos** | Only concrete, documented edge cases covered; no speculative recovery or complex retries. | **PASS** | Backoff retry specifically targets concrete server protections requested by user (rate limit 429, server 5xx, timeouts), and `.gitkeep` ensures git directory preservation. |
| **IV. Interface Exclusiva via CLI** | System interaction exclusively via CLI; standard `argparse`, stdout for output, stderr for errors. | **PASS** | Configurable via optional positional argument (defaulting to `manifest.yml`), `--manifest`, `--delay`, and `--max-retries` in `argparse`. |

---

## Project Structure

### Documentation (this feature)

```text
specs/001-download-pdf-corpus/
├── spec.md              # Feature specification
├── plan.md              # Implementation plan (this file)
├── research.md          # Technical decisions and dependency justification
├── data-model.md        # Entities, validation rules, and filesystem mappings
├── quickstart.md        # Step-by-step verification and run guide
├── contracts/
│   └── cli-contract.md  # CLI command, argument, and output format contract
└── checklists/
    └── requirements.md  # Quality validation checklist
```

### Source Code (repository root)

```text
manifest.yml              # Default document manifest with 12 institutional documents
corpus/
└── .gitkeep              # Preserves corpus directory in Git

src/
├── __init__.py
└── download_corpus.py    # Main CLI entry point, sequential loop, backoff, and downloader logic

tests/
├── __init__.py
└── test_download_corpus.py # Unit tests for parsing, CLI arguments, backoff retries, and error handling

requirements.txt          # Python dependencies (pyyaml)
.gitignore                # Git exclusions (corpus/* and !corpus/.gitkeep)
```

**Structure Decision**: A flat, direct single-project layout without layers of abstraction, adhering directly to the GraphRAG Experiment Constitution ("Flat is better than nested; Simple is better than complex").

---

## Complexity Tracking

*No constitutional violations or complex patterns introduced. Zero complexity debt.*
