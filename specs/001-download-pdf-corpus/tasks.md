# Implementation Tasks: Download PDF Corpus from YAML List

**Feature**: Download PDF Corpus from YAML List  
**Branch**: `001-download-pdf-corpus`  
**Spec**: [`specs/001-download-pdf-corpus/spec.md`](file:///Users/gabrielcordeiro/Repos/graphrag-experiment/specs/001-download-pdf-corpus/spec.md)  
**Plan**: [`specs/001-download-pdf-corpus/plan.md`](file:///Users/gabrielcordeiro/Repos/graphrag-experiment/specs/001-download-pdf-corpus/plan.md)  

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization, directory structure, default manifest, and dependency configuration.

- [x] T001 Create project source and test directories with package markers in `src/__init__.py` and `tests/__init__.py`
- [x] T002 [P] Create `requirements.txt` declaring `pyyaml>=6.0` dependency
- [x] T003 [P] Create default `manifest.yml` at repository root with institutional documents
- [x] T004 [P] Ensure base `.gitignore` exists at repository root with Python artifact exclusions (`__pycache__/`, `*.pyc`, `.venv/`)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core parsing and CLI infrastructure required before implementing specific user stories.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete.

- [x] T005 Implement YAML manifest parser function in `src/download_corpus.py` to validate and extract top-level sequence of entries enforcing constraints: `selection_id` as "non-empty string, filesystem-safe (no slashes or path traversal characters)" and `url` as "non-empty string with schema http:// or https://", skipping malformed entries with a warning to `stderr`
- [x] T006 Implement CLI argument parsing in `src/download_corpus.py` using standard library `argparse` accepting optional positional argument `manifest_path` (default: `manifest.yml`), alternative `--manifest` flag, `--corpus-dir` (default: `corpus`), `--delay` (default: `1.0`), and `--max-retries` (default: `3`), adhering to [cli-contract.md](file:///Users/gabrielcordeiro/Repos/graphrag-experiment/specs/001-download-pdf-corpus/contracts/cli-contract.md)

**Checkpoint**: Foundation ready - manifest deserialization and CLI arguments with delay/retry flags and default manifest fallback are functional.

---

## Phase 3: User Story 1 - Download PDF Files to Corpus Directory (Priority: P1) 🎯 MVP

**Goal**: Read a YAML manifest, download each referenced PDF sequentially via streaming HTTP into `corpus/<selection_id>.pdf`, and output real-time progress and summary to stdout.

**Independent Test**: Run the CLI command against a sample YAML manifest with valid URLs; verify each corresponding `<selection_id>.pdf` is saved in `corpus/` with non-zero size, and real-time `[OK]` status and summary block are emitted to `stdout`.

### Implementation for User Story 1

- [x] T007 [US1] Implement streaming HTTP downloader function in `src/download_corpus.py` using standard library `urllib.request.urlopen` downloading binary chunks to a temporary file (`corpus/<selection_id>.pdf.tmp`)
- [x] T008 [US1] Implement atomic file movement in `src/download_corpus.py` using `os.replace` to promote completed `.tmp` files to `corpus/<selection_id>.pdf`
- [x] T009 [US1] Implement terminal output formatting in `src/download_corpus.py` printing `[OK]` progress lines and the final summary block (`Total items`, `Downloaded/Updated`, `Failed downloads`, `Malformed/Skipped`, `Polite delay`) to `stdout` matching the contract
- [x] T010 [US1] Implement `main()` sequential batch loop in `src/download_corpus.py` enforcing sequential execution (no concurrency) and a polite pause (`time.sleep(args.delay)`) between consecutive successful downloads
- [x] T011 [P] [US1] Add unit tests for manifest parsing and CLI execution in `tests/test_download_corpus.py`

**Checkpoint**: User Story 1 is fully functional as a standalone MVP with sequential execution and polite delay.

---

## Phase 4: User Story 2 - Maintain Corpus Directory in Git via .gitkeep with Ignored Contents (Priority: P2)

**Goal**: Automatically ensure `corpus/.gitkeep` is created and preserved in Git while excluding all downloaded PDF binary files and temporary buffers via `.gitignore`.

**Independent Test**: Run the downloader and check `corpus/.gitkeep`; verify that `corpus/*` and `!corpus/.gitkeep` are present in `.gitignore`, and `git status -u` reports only `.gitkeep` without untracked PDF binaries.

### Implementation for User Story 2

- [x] T012 [US2] Ensure `corpus/.gitkeep` creation in `src/download_corpus.py` during directory initialization if not already present
- [x] T013 [US2] Implement `ensure_git_ignored()` helper in `src/download_corpus.py` using `pathlib.Path` to append `corpus/*` and `!corpus/.gitkeep` to `.gitignore` without duplicating existing rules
- [x] T014 [P] [US2] Add unit test in `tests/test_download_corpus.py` verifying that `ensure_git_ignored()` writes `corpus/*` and `!corpus/.gitkeep` to `.gitignore` and does not duplicate entries

**Checkpoint**: User Story 2 is fully integrated and independently verified.

---

## Phase 5: User Story 3 - Polite Sequential Downloads, Exponential Backoff & Idempotency (Priority: P3)

**Goal**: Idempotently replace existing destination files with newly downloaded files, apply exponential backoff retry on transient errors (HTTP 429, 5xx, timeouts), and continue processing remaining items when non-retryable errors occur.

**Independent Test**: Run against a manifest containing an existing local file (verified cleanly replaced) and an endpoint returning HTTP 429/timeout (verified backoff retry warnings emitted to `stderr`, followed by graceful skip or recovery); verify process exits with code 0.

### Implementation for User Story 3

- [x] T015 [US3] Implement exponential backoff retry loop in `src/download_corpus.py` for transient HTTP codes (429, 500, 502, 503, 504) and timeouts, waiting `args.delay * (2 ** attempt)` seconds with warning messages to `stderr` before exhausting retries and cleaning up dangling `.tmp` files
- [x] T016 [US3] Implement idempotent overwrite logic in `src/download_corpus.py` ensuring existing `<selection_id>.pdf` files are cleanly replaced via `os.replace` and counted in the downloaded/updated summary
- [x] T017 [P] [US3] Add unit tests in `tests/test_download_corpus.py` verifying exponential backoff retries, rate-limiting delays, and idempotent overwrite behavior using mock responses

**Checkpoint**: User Story 3 is complete and all server-protection resilience requirements are verified.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: End-to-end verification across all user stories and test suite execution.

- [x] T018 Execute all validation scenarios specified in `specs/001-download-pdf-corpus/quickstart.md`
- [x] T019 [P] Run automated test suite with `python3 -m unittest discover tests` and verify 100% pass rate

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately.
- **Foundational (Phase 2)**: Depends on Phase 1 — BLOCKS all user stories.
- **User Story 1 (Phase 3 - MVP)**: Depends on Phase 2 — Core functionality.
- **User Story 2 (Phase 4)**: Depends on Phase 2 — Directory initialization and `.gitkeep`.
- **User Story 3 (Phase 5)**: Depends on Phase 3 — Extends download loop with exponential backoff and overwrite tracking.
- **Polish (Phase 6)**: Depends on Phases 1–5 being complete.

### User Story Dependencies

- **User Story 1 (P1)**: Independent of US2 and US3. Delivers the complete MVP with sequential downloads and polite delay.
- **User Story 2 (P2)**: Integrates with directory initialization in US1, testable on `corpus/.gitkeep` and `.gitignore`.
- **User Story 3 (P3)**: Builds on US1 download loop to add exponential backoff retry on transient errors and idempotent overwrite.

### Parallel Opportunities

- **Phase 1**: T002, T003, and T004 can be executed in parallel.
- **Phase 3**: T011 (tests) can be created in parallel with T010.
- **Phase 4**: T014 (git ignore tests) can run in parallel.
- **Phase 5**: T017 (resilience tests) can run in parallel.
- **Phase 6**: T019 can run in parallel with manual scenario checks.

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (`src/`, `tests/`, `requirements.txt`, `manifest.yml`).
2. Complete Phase 2: Foundational (manifest parser + CLI args with default fallback).
3. Complete Phase 3: User Story 1 (sequential streaming download + polite delay + atomic replace + stdout summary).
4. **VALIDATE MVP**: Run download against default or custom manifest and verify files are saved sequentially to `corpus/<selection_id>.pdf`.

### Incremental Delivery

1. Setup + Foundation ready.
2. Deliver US1 (MVP) -> Test independently -> Working sequential downloader with polite delay.
3. Deliver US2 -> Test independently -> `corpus/.gitkeep` tracked and `corpus/*` ignored in `.gitignore`.
4. Deliver US3 -> Test independently -> Exponential backoff on transient errors and idempotent overwrite.
5. Polish -> Run quickstart validation and unit test suite.
