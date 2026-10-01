# CLI Interface Contract: `download_corpus`

**Feature**: Download PDF Corpus from YAML List  
**Branch**: `001-download-pdf-corpus`  
**Date**: 2026-09-30  

## Overview

This contract formally specifies the Command Line Interface (CLI) input syntax, arguments, flags, output formats (stdout/stderr), rate-limiting defaults, and exit status codes in accordance with Constitution Principle IV (CLI-First).

---

## Command Invocation

```bash
python3 -m src.download_corpus <manifest_path> [--corpus-dir <dir_path>] [--delay <seconds>] [--max-retries <count>]
```

Alternatively:
```bash
python3 src/download_corpus.py <manifest_path> [--delay <seconds>]
```

---

## Arguments & Options

| Parameter | Type | Required | Default | Description |
|---|---|---|---|---|
| `manifest_path` | Positional Argument | Yes | N/A | Path to the YAML file containing the list of documents to download. |
| `--corpus-dir` | Flag / Option | No | `corpus` | Target directory where PDF files are stored. Defaults to `corpus` at repository root. |
| `--delay` | Float Option | No | `1.0` | Polite delay in seconds between consecutive downloads to avoid harming the source website. |
| `--max-retries` | Integer Option | No | `3` | Maximum number of exponential backoff retries when transient errors occur (429, 5xx, timeouts). |
| `-h`, `--help` | Flag | No | N/A | Show auto-generated help message and exit. |

---

## Exit Codes

| Exit Code | Meaning | Condition |
|---|---|---|
| `0` | Success | Manifest successfully read and batch processing finished (even if individual item URLs fail after retries, the batch run succeeded). |
| `1` | Fatal Runtime Error | Manifest file not found, unreadable, invalid YAML syntax, or root element is not a sequence/list. |
| `2` | Usage / Syntax Error | Missing required `manifest_path` positional argument, or unrecognized CLI flags. |

---

## Output Stream Formats

### 1. Standard Output (`stdout`)

Emits real-time progress indicators during download and a final formatted summary block.

#### Item Progress Line
```text
[OK] <selection_id> -> corpus/<selection_id>.pdf (245.3 KB)
```

#### Final Summary Block
```text
========================================
Corpus Download Summary
========================================
Total items:        12
Downloaded/Updated: 11
Failed downloads:   1
Malformed/Skipped:  0
Target directory:   corpus/
Polite delay:       1.0s
========================================
```

### 2. Standard Error (`stderr`)

Emits item-level non-blocking warnings, transient retry notifications, download failures, and fatal errors.

#### Transient Retry Notification (Exponential Backoff)
```text
[WARN] Transient error downloading 'edital-012-2025' (HTTP Error 429: Too Many Requests). Retrying in 1.0s (attempt 1/3)...
```

#### Final Item Download Failure
```text
[ERROR] Failed to download 'edital-012-2025' from 'https://fapes.es.gov.br/...': HTTP Error 404: Not Found
```

#### Malformed Item Warning
```text
[WARN] Skipping malformed item (missing required 'selection_id' or 'url'): {'title': 'Example without URL'}
```

#### Fatal Error
```text
[FATAL] Manifest file not found: non_existent_manifest.yml
```
