# Data Model: Download PDF Corpus from YAML List

**Feature**: Download PDF Corpus from YAML List  
**Branch**: `001-download-pdf-corpus`  
**Date**: 2026-09-30  

## Overview

This document specifies the conceptual entities, data structures, validation rules, runtime configurations, and filesystem mappings for the PDF corpus downloader CLI tool.

---

## Entities

### 1. `ManifestEntry`

Represents a single document record declared in the input YAML manifest.

#### Fields

| Field Name | Type | Requirement | Description | Validation Rules |
|---|---|---|---|---|
| `selection_id` | String | Mandatory | Unique document identifier used as target filename. | Must be a non-empty string, filesystem-safe (no slashes or path traversal characters). |
| `url` | String | Mandatory | Direct remote URL pointing to the PDF document. | Must be a non-empty string with schema `http://` or `https://`. |
| `title` | String | Optional | Descriptive human-readable title. | Default: `""` if absent. |
| `group` | String | Optional | Functional or category grouping. | Default: `""` if absent. |
| `source_id` | String | Optional | Origin collection identifier. | Default: `""` if absent. |

---

### 2. `CorpusManifest`

Represents the deserialized YAML manifest file containing the sequence of documents.

#### Structure
- Top-level structure in YAML: **Sequence of Mappings** (list of dicts).
- Direct list format (no `items:` wrapper key required):

```yaml
- selection_id: edital-004-2025
  url: https://fapes.es.gov.br/media/Editais/Edital_04-2025.pdf
  title: EDITAL FAPES Nº 04/2025 - UNIVERSAL DE EXTENSÃO III
  group: Editais Encerrados 2025
  source_id: editais-encerrados

- selection_id: resolucao-352-2025
  url: https://fapes.es.gov.br/media/Resolucoes/Resolucao_352.pdf
  title: RESOLUÇÃO Nº 352 - DE 15 DE ABRIL DE 2025
  group: Resoluções CCAF
  source_id: resolucoes
```

#### Validation Rules
- The root document MUST parse into a Python `list`.
- If root is not a list (or empty list), system prints an error to stderr and exits with non-zero code.
- Default path on disk is `./manifest.yml` at the repository root.

---

### 3. `DownloadConfig`

Runtime configuration parameters controlling sequential execution, rate limiting, and backoff retries.

| Parameter | Type | Default | Description |
|---|---|---|---|
| `manifest_path` | Path | `manifest.yml` | Path to YAML document manifest file. |
| `corpus_dir` | Path | `corpus` | Destination directory on disk. |
| `polite_delay` | Float | `1.0` | Pause duration in seconds between consecutive successful downloads. |
| `max_retries` | Integer | `3` | Maximum number of exponential backoff retry attempts for retryable errors. |
| `backoff_base` | Float | `1.0` | Initial backoff wait time in seconds for retries ($wait = base \times 2^{attempt}$). |

---

### 4. `CorpusDirectory` & File Storage

Represents the physical destination directory, Git tracking marker, and binary PDF artifacts.

#### Filesystem Mapping
- **Directory Path**: `./corpus/` (relative to repository root).
- **Directory Keeper**: `./corpus/.gitkeep` (tracked in Git to preserve folder structure across clones).
- **Artifact Path**: `./corpus/<selection_id>.pdf` (binary file, ignored by Git).
- **Atomic Temporary Path**: `./corpus/<selection_id>.pdf.tmp` (temporary write buffer, ignored by Git).

#### Execution Lifecycle & State Transitions
```text
[ Initialize Directory ] ──> [ Ensure corpus/.gitkeep exists ]
                                          │
                                          ▼
                              [ Ensure .gitignore contains ]
                              [ corpus/* and !corpus/.gitkeep ]
                                          │
                                          ▼
                              [ Next Manifest Entry ]
                                          │
                                          ▼
                              [ Download Attempt (attempt = 0..3) ]
                                          │
   Success?
   ├── Yes ──> [ Write to .tmp ] ──> [ os.replace to corpus/<selection_id>.pdf ]
   │                                              │
   │                                              ▼
   │                                   [ Sleep polite_delay (1.0s) ]
   │                                              │
   │                                              ▼
   │                                    [ Proceed to next item ]
   │
   └── No (HTTP 429, 5xx, Timeout)
         │
    attempt < max_retries?
    ├── Yes ──> [ Sleep backoff_base * 2^attempt ] ──> [ Retry attempt + 1 ]
    └── No  ──> [ Cleanup .tmp, Log to stderr, count failed ] ──> [ Next item ]
```

---

### 5. `BatchExecutionSummary`

Transient summary object collected during CLI execution and printed upon completion.

#### Attributes

| Attribute | Type | Description |
|---|---|---|
| `total` | Integer | Total count of entries in the YAML manifest. |
| `downloaded` | Integer | Count of successfully downloaded and replaced files. |
| `failed` | Integer | Count of entries that failed after retries. |
| `skipped` | Integer | Count of malformed entries skipped during parsing. |

---

### 6. Git Ignore Management

- **Target File**: `./.gitignore`
- **Patterns**:
  ```gitignore
  corpus/*
  !corpus/.gitkeep
  ```
- **Rule**: Ignores all downloaded files inside `corpus/` while allowing `corpus/.gitkeep` to be tracked in Git.
