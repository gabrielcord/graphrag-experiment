# Technical Research: Download PDF Corpus from YAML List

**Feature**: Download PDF Corpus from YAML List  
**Branch**: `001-download-pdf-corpus`  
**Date**: 2026-09-30  

## Overview

This document resolves all technical decisions and dependency choices for implementing the PDF corpus downloader CLI tool in strict compliance with the [GraphRAG Experiment Constitution](file:///Users/gabrielcordeiro/Repos/graphrag-experiment/.specify/memory/constitution.md).

---

## Technical Decisions

### 1. YAML Parsing Library

- **Decision**: Use `pyyaml` (`PyYAML >= 6.0`) for parsing the document manifest file.
- **Rationale**:
  - Python standard library does not provide a YAML parser.
  - PyYAML is the industry standard for Python, mature, lightweight, and supports standard YAML sequences of dictionaries (`safe_load`).
  - It cleanly extracts the top-level list of documents without requiring any wrapper key like `items:`.
- **Alternatives Considered**:
  - *Custom regex/string parser*: Rejected because YAML specification involves indentation, quoting rules, and escaping; writing a custom parser violates Principle II (KISS & YAGNI) and introduces bugs.
  - *`ruamel.yaml`*: Rejected because it is primarily intended for round-trip YAML editing with comment preservation, adding unnecessary complexity and weight.

### 2. HTTP Downloader & Rate-Limiting Strategy

- **Decision**: Use Python standard library `urllib.request` with streaming chunks and a standard User-Agent header.
- **Sequential Execution**:
  - Downloads are executed strictly sequentially using a simple procedural `for` loop over manifest entries.
  - No concurrency (no threads, multiprocessing, or asyncio), ensuring predictable and gentle access to the target host.
- **Polite Inter-Request Delay**:
  - A pause using standard library `time.sleep(delay)` (default: 1.0s, configurable via `--delay`) is executed between successive downloads.
  - Rationale: Protects remote institutional servers from burst traffic and prevents IP throttling.
- **Exponential Backoff on Transient Errors**:
  - When encountering transient errors (HTTP 429 Too Many Requests, HTTP 500/502/503/504 Server Errors, or network `TimeoutError`/`URLError`), the system executes exponential backoff retries:
    $$\text{wait\_time} = \text{base\_delay} \times (2^{\text{attempt}})$$
    (e.g., attempt 1: 1.0s, attempt 2: 2.0s, attempt 3: 4.0s).
  - Maximum retries: 3 attempts.
  - If retries are exhausted or if an error is non-retryable (e.g., HTTP 404 Not Found), the error is logged to `stderr` and the batch advances to the next document.
  - Implemented entirely with Python's built-in `time.sleep` and `urllib.error` without external libraries (e.g., `tenacity` or `backoff`), strictly conforming to Principle II (Minimal Code).
- **Alternatives Considered**:
  - *Third-party retry libraries (`tenacity`, `retry`)*: Rejected because standard Python logic requires only ~15 lines and avoids unnecessary external package bloat.
  - *Parallel / asynchronous downloads*: Explicitly rejected per user requirement and server courtesy principles.

### 3. CLI Argument Parsing

- **Decision**: Use Python standard library `argparse`.
- **Rationale**:
  - Mandated by Constitution Principle IV: *"A biblioteca padrão `argparse` DEVE (MUST) ser priorizada para tratamento de argumentos de linha de comando."*
  - Provides native help (`--help`), positional/optional argument parsing, type conversion, and standardized exit codes with zero dependencies.
- **Alternatives Considered**:
  - *`click` / `typer`*: Rejected to avoid third-party dependencies and adhere directly to the project constitution.

### 4. Idempotent & Atomic File Persistence

- **Decision**: Download remote content to a temporary file (`corpus/<selection_id>.pdf.tmp`) and atomically replace the destination file (`os.replace`) upon complete download.
- **Rationale**:
  - Requirement FR-006 specifies that existing destination files must be overwritten and replaced idempotently.
  - Downloading directly to the target file could corrupt or leave zero-byte/truncated files if a network interruption occurs mid-download.
  - `os.replace` is atomic on POSIX filesystems and standard in Python, ensuring that either the fresh, complete file exists or the previous state is preserved.
- **Alternatives Considered**:
  - *Direct in-place open(path, 'wb')*: If download fails midway, corrupts destination file.

### 5. Git Ignore Automation

- **Decision**: Read repository root `.gitignore` via `pathlib.Path`. Check whether `corpus/` or `corpus` appears as an exact line (ignoring whitespace). If not present, append `corpus/\n` to `.gitignore`. If `.gitignore` does not exist, create it containing `corpus/\n`.
- **Rationale**:
  - Clean, idempotent, minimal code using `pathlib.Path`.
  - Satisfies FR-003, FR-004, and User Story 2 without subprocess invocations or external git libraries.

---

## Summary of Dependencies

| Component | Choice | Source | License |
|---|---|---|---|
| Language Runtime | Python 3.11+ (running 3.14.7) | Built-in | PSF |
| Manifest Parser | `pyyaml` | PyPI | MIT |
| HTTP Transfer | `urllib.request` | Standard Library | PSF |
| Delays & Backoff | `time.sleep` | Standard Library | PSF |
| CLI Interface | `argparse` | Standard Library | PSF |
| Filesystem / Paths | `pathlib`, `os`, `shutil` | Standard Library | PSF |
| Automated Tests | `unittest` (standard library) | Standard Library | PSF |
