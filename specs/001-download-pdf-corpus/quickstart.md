# Quickstart Validation Guide: Download PDF Corpus

**Feature**: Download PDF Corpus from YAML List  
**Branch**: `001-download-pdf-corpus`  
**Date**: 2026-09-30  

This guide provides step-by-step procedures to validate that the PDF corpus downloader fulfills all user stories, functional requirements, and acceptance criteria, including sequential politeness pauses, exponential backoff retry, and directory preservation via `.gitkeep`.

---

## Prerequisites

- Python 3.11+ (verified on Python 3.12.14 / 3.14.7)
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

## 2. Validation Scenarios

### Scenario 1: Default Manifest Execution & Directory Preservation (US1 & US2)

Run the CLI command without arguments (defaults to project `manifest.yml`):

```bash
python3 -m src.download_corpus
```

**Expected Results**:
1. Downloads proceed sequentially using `manifest.yml`.
2. Console shows real-time `[OK]` download indicators and final summary:
   - `Total items: 12`
   - `Downloaded/Updated: 12`
   - `Failed downloads: 0`
   - `Target directory: corpus/`
3. Directory `corpus/` contains `corpus/.gitkeep` and all 12 downloaded PDF documents.
4. Check `.gitignore`:
   ```bash
   grep -F "corpus/*" .gitignore
   grep -F "!corpus/.gitkeep" .gitignore
   ```
   Both patterns must be present.
5. Check Git status:
   ```bash
   git status -u
   ```
   **Expected Outcome**: Only `corpus/.gitkeep` appears as tracked/untracked for commit; zero PDF files from `corpus/` appear in git status.

---

### Scenario 2: Custom Manifest Parameter & Idempotent Overwrite (US3 & FR-006)

To verify that existing files are cleanly replaced when specifying an alternative manifest:

1. Create a small custom manifest (`custom_test.yml`):
   ```yaml
   - selection_id: test-edital-004
     url: https://fapes.es.gov.br/media/Editais/Edital_04-2025_-_Universal_Extens%C3%A3o-1.pdf
     title: Custom Test Document
   ```
2. Corrupt the local file:
   ```bash
   echo "dummy corrupt content" > corpus/test-edital-004.pdf
   ```
3. Run the download command passing the custom manifest:
   ```bash
   python3 -m src.download_corpus custom_test.yml --delay 0.1
   ```
4. Inspect `corpus/test-edital-004.pdf`:
   ```bash
   head -c 4 corpus/test-edital-004.pdf
   ```
   **Expected Outcome**: Must output `%PDF` (the valid PDF header), proving the file was re-downloaded and cleanly replaced.
5. Cleanup:
   ```bash
   rm -f custom_test.yml corpus/test-edital-004.pdf
   ```

---

### Scenario 3: Exponential Backoff & Resilience (US3, FR-008, FR-012)

Create a manifest containing an invalid domain (permanent failure) and a valid URL:

```yaml
- selection_id: test-fail
  url: https://invalid-domain-does-not-exist.test/missing.pdf
  title: Invalid Entry

- selection_id: test-sample-2
  url: https://fapes.es.gov.br/media/Resolu%C3%A7%C3%B5es/Resolu%C3%A7%C3%A3o_CCAF_n%C2%BA_352-2025_-_Reajuste_de_Bolsas.pdf
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
6. Cleanup:
   ```bash
   rm -f test_fail_manifest.yml
   ```
