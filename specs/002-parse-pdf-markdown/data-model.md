# Data Model: Parse PDF Corpus to Markdown

**Feature**: `002-parse-pdf-markdown`  
**Date**: 2026-10-01  
**Status**: Completed  

---

## 1. Entities & Schemas

### Entity 1: ManifestEntry
Represents an individual document specification read from the YAML manifest file (`manifest.yml`).

| Field | Type | Required | Description | Validation Rule |
|---|---|---|---|---|
| `selection_id` | string | Yes | Unique document slug / identifier | Non-empty, alphanumeric + hyphens/underscores (e.g. `001-constituicao-federal`) |
| `title` | string | Yes | Human-readable document title | Non-empty string |
| `group` | string | Yes | Category or thematic grouping | Non-empty string |
| `source_id` | string | Yes | Canonical source institution identifier | Non-empty string |
| `url` | string | Yes | Source URL where the PDF was acquired | Valid URL string |

---

### Entity 2: InputPdfDocument
Represents the local source PDF document read from the filesystem.

| Property | Type | Description |
|---|---|---|
| `path` | Path | Resolved absolute or relative path: `<corpus_dir>/<selection_id>.pdf` |
| `exists` | boolean | True if file exists on disk |
| `file_size` | integer | Size of the file in bytes (must be > 0) |
| `is_readable` | boolean | True if file can be opened and parsed as a valid PDF by MuPDF |

**Validation Rules**:
- If `exists` is False, the document cannot be parsed; logs an error to `stderr` and marks the item as failed.
- If `file_size == 0` or MuPDF raises a parsing error, logs a diagnostic error to `stderr` and marks the item as failed.

---

### Entity 3: OutputMarkdownDocument
Represents the generated, version-controlled Markdown document written to disk.

| Property | Type | Description |
|---|---|---|
| `path` | Path | Resolved destination path: `<output_dir>/<selection_id>.md` |
| `frontmatter` | mapping | Structured YAML frontmatter enclosed in `---` lines |
| `body` | string | Markdown text extracted from the PDF via `pymupdf4llm` |
| `git_tracked` | boolean | File is actively tracked in Git version control (not ignored by `.gitignore`) |

**Structure Format**:
```markdown
---
selection_id: "{selection_id}"
title: "{title}"
group: "{group}"
source_id: "{source_id}"
url: "{url}"
---

# {title}

{extracted_markdown_body}
```

**Validation Rules**:
- Directory `<output_dir>` must be created automatically if it does not exist.
- If destination file already exists, it is cleanly overwritten (idempotent write).
- File encoding must be UTF-8.

---

### Entity 4: BatchParsingSummary
Summary metrics gathered during execution of the parsing pipeline.

| Attribute | Type | Description |
|---|---|---|
| `total_items` | integer | Total document entries loaded from the manifest |
| `success_count` | integer | Total documents successfully parsed and saved as Markdown |
| `failed_count` | integer | Total documents skipped due to missing or unreadable PDFs |
| `duration_seconds` | float | Elapsed time in seconds for the entire batch run |

---

## 2. Filesystem & Git Mapping

```text
Repository Root
├── manifest.yml               # Manifest (input metadata source, tracked)
├── corpus/                    # Binary PDFs (input directory, ignored except .gitkeep)
│   ├── .gitkeep               # Tracked in Git
│   ├── 001-constituicao-federal.pdf  # Ignored binary
│   └── ...
└── corpus_md/                 # Markdown Corpus (output directory, fully tracked)
    ├── 001-constituicao-federal.md   # Tracked in Git
    ├── 002-codigo-civil.md           # Tracked in Git
    └── ...
```

- **Git Status Guarantee**:
  - `corpus/*` remains ignored via `.gitignore` with `!corpus/.gitkeep`.
  - `corpus_md/` is NOT added to `.gitignore`. All files under `corpus_md/` are tracked by Git.
