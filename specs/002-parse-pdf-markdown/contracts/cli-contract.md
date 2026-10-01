# CLI Contract: Parse PDF Corpus to Markdown

**Feature**: `002-parse-pdf-markdown`  
**Date**: 2026-10-01  
**Status**: Completed  

---

## 1. Command Syntax

```bash
python3 src/parse_corpus.py [MANIFEST] [OPTIONS]
```

Or with flags:

```bash
python3 src/parse_corpus.py [--manifest MANIFEST] [--corpus-dir CORPUS_DIR] [--output-dir OUTPUT_DIR]
```

---

## 2. Command-Line Arguments & Options

| Parameter | Type | Default | Description |
|---|---|---|---|
| `manifest` | Positional / Optional | `manifest.yml` | Path to the YAML document manifest file. |
| `--manifest`, `-m` | Optional Flag | `manifest.yml` | Explicit flag specifying manifest file path (takes precedence over positional if both supplied). |
| `--corpus-dir`, `-c` | Optional Flag | `corpus` | Directory containing downloaded PDF input documents. |
| `--output-dir`, `-o` | Optional Flag | `corpus_md` | Directory where parsed `.md` documents are saved. Created if not existing. |

---

## 3. Standard Streams Contract

### Standard Output (`stdout`)
Informational progress, per-document status, and final batch summary:

```text
Loaded 12 document entries from 'manifest.yml'.
Reading PDFs from 'corpus' -> writing Markdown to 'corpus_md'.

[1/12] Parsing 001-constituicao-federal.pdf -> 001-constituicao-federal.md... [OK]
[2/12] Parsing 002-codigo-civil.pdf -> 002-codigo-civil.md... [OK]
...
[12/12] Parsing 012-marco-civil-internet.pdf -> 012-marco-civil-internet.md... [OK]

==================================================
Batch Parsing Completed in 4.21s:
  Total documents in manifest: 12
  Successfully parsed:        12
  Failed / Skipped:            0
  Output directory:           corpus_md (tracked in Git)
==================================================
```

### Standard Error (`stderr`)
Diagnostic failure notices when a PDF is missing or unparseable:

```text
[ERROR] (005-document-slug): PDF not found at 'corpus/005-document-slug.pdf'
[ERROR] (007-corrupted-file): Failed to parse PDF 'corpus/007-corrupted-file.pdf': MuPDF error: ...
```

---

## 4. Exit Codes

| Exit Code | Condition | Description |
|---|---|---|
| `0` | Success / Completed Batch | Manifest was parsed and batch completed (including partial runs where missing/corrupted files were reported to `stderr`). |
| `1` | Fatal Configuration Error | Manifest file not found on disk, invalid YAML format, or invalid command-line argument. |

---

## 5. Usage Examples

### Default Run (Uses fixed `manifest.yml`, `corpus/` input, `corpus_md/` output)
```bash
python3 src/parse_corpus.py
```

### Explicit Custom Directories
```bash
python3 src/parse_corpus.py --manifest custom_manifest.yml --corpus-dir custom_corpus --output-dir custom_md
```
