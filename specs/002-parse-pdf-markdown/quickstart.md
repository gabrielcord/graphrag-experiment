# Quickstart & Verification Guide: Parse PDF Corpus to Markdown

**Feature**: `002-parse-pdf-markdown`  
**Date**: 2026-10-01  
**Status**: Ready for Implementation  

---

## 1. Prerequisites & Setup

Ensure the Python 3.11+ virtual environment is active and dependencies are installed:

```bash
source .venv/bin/activate
pip install -r requirements.txt
```

Verify that `manifest.yml` and the input PDF corpus in `corpus/` are present (from Feature 001):

```bash
ls -l corpus/*.pdf
```

---

## 2. Validation Scenarios

### Scenario 1: Standard Batch Parsing (End-to-End)
Verify that all 12 documents in `manifest.yml` are converted to Markdown in `corpus_md/`:

```bash
python3 src/parse_corpus.py
```

**Expected Outcome**:
- Script prints sequential progress `[1/12] Parsing ... [OK]` through `[12/12]`.
- Batch summary displays 12 total, 12 successfully parsed, 0 failed.
- Files `corpus_md/001-constituicao-federal.md` through `corpus_md/012-marco-civil-internet.md` exist on disk.
- Each generated Markdown file contains YAML frontmatter (`selection_id`, `title`, `group`, `source_id`, `url`) followed by extracted text content.

---

### Scenario 2: Git Tracking Verification
Verify that the output `corpus_md/` directory and its files are recognized by Git and NOT excluded by `.gitignore`:

```bash
git status
```

**Expected Outcome**:
- `corpus_md/` appears under untracked / modified files in `git status`.
- Running `git check-ignore -v corpus_md/001-constituicao-federal.md` returns non-zero (file is NOT ignored).

---

### Scenario 3: Idempotent Execution
Re-run the parsing command against the populated `corpus_md/` directory:

```bash
python3 src/parse_corpus.py
```

**Expected Outcome**:
- All Markdown files are cleanly overwritten without error.
- Script exits with status code 0.

---

### Scenario 4: Missing & Corrupt PDF Resilience
Run the parser pointing to a test manifest with missing or invalid files:

```bash
python3 -m unittest discover tests
```

**Expected Outcome**:
- Unit test suite verifies that missing or corrupt PDF files log errors to `stderr` without halting the process, and remaining files are parsed successfully.
- All unit tests pass with exit code 0.
