# Implementation Tasks: Parse PDF Corpus to Markdown

**Feature**: Parse PDF Corpus to Markdown  
**Branch**: `002-parse-pdf-markdown`  
**Spec**: [`specs/002-parse-pdf-markdown/spec.md`](file:///Users/gabrielcordeiro/Repos/graphrag-experiment/specs/002-parse-pdf-markdown/spec.md)  
**Plan**: [`specs/002-parse-pdf-markdown/plan.md`](file:///Users/gabrielcordeiro/Repos/graphrag-experiment/specs/002-parse-pdf-markdown/plan.md)  

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Dependency configuration and environment preparation.

- [x] T001 Update `requirements.txt` declaring `pymupdf4llm>=0.0.17` alongside existing `pyyaml>=6.0`
- [x] T002 [P] Install dependencies into virtual environment via `pip install -r requirements.txt`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Manifest loading and CLI interface infrastructure required across all user stories.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete.

- [x] T003 Implement manifest loading helper in `src/parse_corpus.py` to parse YAML manifest (with default fallback to `manifest.yml`), validating that entries contain required string attributes: `selection_id`, `title`, `group`, `source_id`, `url`
- [x] T004 Implement CLI argument parser in `src/parse_corpus.py` using standard library `argparse` accepting optional positional argument `manifest` (default: `manifest.yml`), `--manifest` / `-m` flag, `--corpus-dir` / `-c` (default: `corpus`), and `--output-dir` / `-o` (default: `corpus_md`), adhering to [cli-contract.md](file:///Users/gabrielcordeiro/Repos/graphrag-experiment/specs/002-parse-pdf-markdown/contracts/cli-contract.md)

**Checkpoint**: Foundation ready - manifest deserialization and CLI configuration are complete and ready for user story implementation.

---

## Phase 3: User Story 1 - Sequential PDF Parsing from Manifest (Priority: P1) 🎯 MVP

**Goal**: Sequentially read PDF documents from the input corpus directory matching manifest entries, convert their content into Markdown using `pymupdf4llm`, write them to the destination directory, and print real-time status and a final summary to `stdout`.

**Independent Test**: Execute `python3 src/parse_corpus.py` against a manifest with sample PDF files in `corpus/`; verify that documents are processed one by one in sequence, corresponding `<selection_id>.md` files are created in `corpus_md/`, and real-time progress and summary blocks are emitted to `stdout`.

### Implementation for User Story 1

- [x] T005 [US1] Implement core PDF extraction function in `src/parse_corpus.py` invoking `pymupdf4llm.to_markdown(pdf_path)` to convert input PDF into Markdown text
- [x] T006 [US1] Implement sequential batch loop in `src/parse_corpus.py` that iterates over manifest entries one by one in sequence, converts each `<corpus_dir>/<selection_id>.pdf`, writes the parsed output to `<output_dir>/<selection_id>.md`, and prints real-time `[N/M] Parsing ... [OK]` progress to `stdout`
- [x] T007 [US1] Implement terminal summary reporter in `src/parse_corpus.py` emitting execution statistics (`Total documents in manifest`, `Successfully parsed`, `Failed / Skipped`, `Elapsed time`, `Output directory`) to `stdout` upon batch completion
- [x] T008 [P] [US1] Add unit tests in `tests/test_parse_corpus.py` testing CLI argument defaults, sequential batch loop execution, and Markdown output generation using mocked `pymupdf4llm.to_markdown`

**Checkpoint**: User Story 1 is fully functional as a standalone MVP delivering sequential PDF-to-Markdown conversion.

---

## Phase 4: User Story 2 - Git Versioning for Markdown Corpus (Priority: P2)

**Goal**: Ensure the output Markdown directory (`corpus_md/`) is created and that all generated Markdown files are actively version-controlled in Git and exempt from `.gitignore`.

**Independent Test**: Run the parser and inspect Git tracking status; verify that `corpus_md/` and generated `.md` files appear as trackable files in `git status` and are not matched by repository ignore rules.

### Implementation for User Story 2

- [x] T009 [US2] Implement output directory creation logic in `src/parse_corpus.py` ensuring `<output_dir>` is created if not existing, and verifying that `.gitignore` does not exclude `<output_dir>` or `.md` files
- [x] T010 [P] [US2] Add unit test in `tests/test_parse_corpus.py` verifying that output files created in `corpus_md/` are not excluded by repository `.gitignore` patterns

**Checkpoint**: User Story 2 is complete - Markdown corpus directory is created and verified trackable by Git.

---

## Phase 5: User Story 3 - Fault Resilience & Idempotent Overwrite (Priority: P3)

**Goal**: Handle missing or corrupt PDF files gracefully with diagnostics to `stderr` without aborting the batch, support clean idempotent overwrites, and ensure output files contain strictly pure Markdown.

**Independent Test**: Run parser against a manifest containing an existing file (verified cleanly overwritten), a missing PDF, and a corrupt PDF; verify that valid files contain pure Markdown without frontmatter, diagnostic errors are logged to `stderr`, summary records failures, and the command exits with code 0.

### Implementation for User Story 3

- [x] T011 [US3] Ensure pure Markdown output persistence in `src/parse_corpus.py` saving strictly extracted text without injecting frontmatter or extraneous metadata headers
- [x] T012 [US3] Implement error handling for missing and corrupt PDFs in `src/parse_corpus.py` logging diagnostic error messages to `stderr` with document `selection_id` and continuing processing remaining items in sequence
- [x] T013 [US3] Implement idempotent file writing in `src/parse_corpus.py` ensuring pre-existing `.md` destination files are cleanly overwritten
- [x] T014 [P] [US3] Add unit tests in `tests/test_parse_corpus.py` verifying pure Markdown output without frontmatter, missing PDF handling, corrupt/unreadable PDF error logging to `stderr`, and idempotent overwrite

**Checkpoint**: User Story 3 is complete - batch processing survives missing/corrupt files with pure Markdown output.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: End-to-end validation, complete test coverage, and documentation.

- [x] T015 Execute validation scenarios from `specs/002-parse-pdf-markdown/quickstart.md` against the downloaded corpus documents in `corpus/`
- [x] T016 [P] Run full automated test suite using `python3 -m unittest discover tests` and verify all tests pass with 100% success
- [x] T017 [P] Update `README.md` to document the new `src/parse_corpus.py` CLI command, options, and output Markdown directory

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately.
- **Foundational (Phase 2)**: Depends on Phase 1 completion — BLOCKS all user stories.
- **User Story 1 (Phase 3 - MVP)**: Depends on Phase 2 — Core sequential parsing functionality.
- **User Story 2 (Phase 4)**: Depends on Phase 2 — Output directory creation and Git tracking checks.
- **User Story 3 (Phase 5)**: Depends on Phase 3 (US1) — Frontmatter enrichment, error handling, and idempotency.
- **Polish (Phase 6)**: Depends on Phases 1 through 5 completion.

### User Story Dependencies

- **User Story 1 (P1)**: Core extraction and sequential processing. Delivers the standalone MVP.
- **User Story 2 (P2)**: Directory creation and Git tracking. Can be developed in parallel with or immediately after US1.
- **User Story 3 (P3)**: Builds on top of US1's batch pipeline by adding frontmatter metadata injection and resilient error handling for corrupt/missing files.

---

## Parallel Execution Opportunities

- Phase 1: `T002` can run once `T001` updates `requirements.txt`.
- Phase 3: `T008` (test suite) can run in parallel with implementation `T005-T007`.
- Phase 4: `T010` (test) can run in parallel with `T009`.
- Phase 5: `T014` (test suite) can run in parallel with `T011-T013`.
- Phase 6: `T016` (test suite) and `T017` (documentation) can run in parallel after `T015`.

---

## Implementation Strategy

### MVP First (User Story 1 Only)
1. Complete Phase 1 (Dependencies: `pymupdf4llm`).
2. Complete Phase 2 (Foundational: Manifest parsing & CLI args).
3. Complete Phase 3 (User Story 1: Sequential PDF-to-Markdown batch conversion).
4. **Validate MVP**: Run `python3 src/parse_corpus.py` to confirm that PDFs in `corpus/` are parsed to Markdown in `corpus_md/`.

### Incremental Delivery
1. Add Phase 4 (User Story 2: Git tracking validation for `corpus_md/`).
2. Add Phase 5 (User Story 3: YAML frontmatter metadata enrichment + missing/corrupt PDF resilience).
3. Complete Phase 6 (Polish: Quickstart verification, test suite run, README documentation).
