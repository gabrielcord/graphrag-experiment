# Quickstart Validation Guide: Download PDF Corpus

**Feature**: Download PDF Corpus from YAML List  
**Branch**: `001-download-pdf-corpus`  
**Date**: 2026-09-30  

This guide provides step-by-step procedures to validate that the PDF corpus downloader fulfills all user stories, functional requirements, and acceptance criteria, including sequential politeness pauses and exponential backoff retry.

---

## Prerequisites

- Python 3.11+ (verified on Python 3.14.7)
- PyYAML (`pip install pyyaml`)
- Active internet connectivity for remote PDF downloads

---

## 1. Setup Environment

Install required dependencies:

```bash
pip3 install pyyaml
```

Verify Python and PyYAML installation:

```bash
python3 -c "import yaml; print('PyYAML version:', yaml.__version__)"
```

---

## 2. Test Manifest Preparation

Create a temporary test manifest file (`test_manifest.yml`):

```yaml
- selection_id: test-sample-1
  url: https://raw.githubusercontent.com/pdf-association/pdf-corpus/master/sample.pdf
  title: Sample Document 1
  group: Test Group
  source_id: test-source

- selection_id: test-sample-2
  url: https://raw.githubusercontent.com/pdf-association/pdf-corpus/master/sample.pdf
  title: Sample Document 2
  group: Test Group
  source_id: test-source
```

---

## 3. Validation Scenarios

### Scenario 1: Polite Sequential Download & Git Ignore Verification (US1 & US2)

Run the CLI command passing the test manifest with a 0.5s polite delay:

```bash
python3 -m src.download_corpus test_manifest.yml --delay 0.5
```

**Expected Results**:
1. Downloads occur one after the other with an observable 0.5s pause between items.
2. Console shows real-time `[OK]` download indicators and final summary:
   - `Total items: 2`
   - `Downloaded/Updated: 2`
   - `Failed downloads: 0`
3. Directory `corpus/` contains `test-sample-1.pdf` and `test-sample-2.pdf`.
4. Check `.gitignore`:
   ```bash
   grep -F "corpus/" .gitignore
   ```
   Must output `corpus/`.
5. Check Git status:
   ```bash
   git status --porcelain corpus/
   ```
   Must return empty (no untracked files in `corpus/`).

---

### Scenario 2: Idempotent Overwrite Verification (US3 & FR-006)

To verify that existing files are cleanly replaced:

1. Modify one existing local file with test content:
   ```bash
   echo "dummy corrupt content" > corpus/test-sample-1.pdf
   ```
2. Re-run the download command:
   ```bash
   python3 -m src.download_corpus test_manifest.yml --delay 0.1
   ```
3. Inspect `corpus/test-sample-1.pdf`:
   ```bash
   head -c 4 corpus/test-sample-1.pdf
   ```
   **Expected Outcome**: Must output `%PDF` (the valid PDF header), proving the file was re-downloaded and cleanly replaced.

---

### Scenario 3: Exponential Backoff & Resilience (US3, FR-008, FR-012)

Create a manifest containing an invalid domain (permanent failure) and a valid URL:

```yaml
- selection_id: test-fail
  url: https://invalid-domain-does-not-exist.test/missing.pdf
  title: Invalid Entry

- selection_id: test-sample-2
  url: https://raw.githubusercontent.com/pdf-association/pdf-corpus/master/sample.pdf
  title: Valid Entry
```

Run with 2 retries:
```bash
python3 -m src.download_corpus test_fail_manifest.yml --max-retries 2
```

**Expected Results**:
1. Retry warnings with exponential wait times are emitted to `stderr` for `test-fail`.
2. Final error message is emitted to `stderr` once retries are exhausted.
3. Execution proceeds sequentially to `test-sample-2`, which downloads successfully.
4. Summary reports `Downloaded/Updated: 1`, `Failed downloads: 1`.
5. CLI exits with code `0`.

---

## Cleanup

Remove temporary test files:

```bash
rm -f test_manifest.yml test_fail_manifest.yml
```
