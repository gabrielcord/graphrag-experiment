# Technical Research: Parse PDF Corpus to Markdown

**Feature**: `002-parse-pdf-markdown`  
**Date**: 2026-10-01  
**Status**: Completed  

---

## 1. Technical Decisions & Trade-Offs

### Decision 1: PDF to Markdown Parsing Library
- **Decision**: Adopt `pymupdf4llm` as the primary PDF extraction and Markdown conversion engine.
- **Rationale**:
  - Specifically requested by the user.
  - Built on PyMuPDF (C-based MuPDF engine), delivering exceptional parsing speed and low memory footprint compared to pure-Python parsers.
  - Tailored specifically for LLM and RAG ingestion pipelines: handles structural element extraction (multi-column text flow, tables formatted as Markdown tables, bulleted lists, and bold/italic markup) without needing bespoke heuristic post-processors.
  - Clean, high-level API: `pymupdf4llm.to_markdown(doc_path)` returns formatted Markdown text directly.
- **Alternatives Considered**:
  - `pdfplumber`: Excellent for manual table bounding box inspection, but slow on large documents, extracts raw text without Markdown heading hierarchies, and requires custom heuristics to recreate formatting.
  - `pypdf`: Extremely lightweight, but limited to flat text extraction without font-weight detection, tables, or Markdown structure.
  - `markitdown` (Microsoft): Capable multi-format tool, but has a larger transitive dependency graph and slower execution times for dedicated PDF workloads.

---

### Decision 2: Document Metadata Format in Output Markdown
- **Decision**: Embed document metadata as YAML Frontmatter at the top of each output `.md` file, enclosed between standard triple-dash delimiters (`---`).
- **Rationale**:
  - Industry-standard pattern across Markdown tooling, static site generators, and RAG ingestion frameworks (such as LangChain, LlamaIndex, and GraphRAG pipelines).
  - Cleanly separates document metadata (`selection_id`, `title`, `group`, `source_id`, `url`) from textual body content, preventing metadata from polluting text chunking and embedding processes while keeping it programmatically deserializable.
  - Formatted example:
    ```markdown
    ---
    selection_id: "001-constituicao-federal"
    title: "Constituição da República Federativa do Brasil"
    group: "Legislação Federal"
    source_id: "planalto-cf88"
    url: "https://www.planalto.gov.br/ccivil_03/constituicao/constituicao.pdf"
    ---

    # Constituição da República Federativa do Brasil

    ...
    ```
- **Alternatives Considered**:
  - Markdown HTML comments (`<!-- metadata: ... -->`): Hidden when rendered, but less standardized across RAG document loaders and harder for human inspection.
  - In-body markdown headers (`# Document Metadata`): Intermingles metadata with actual document text, creating false semantic entities in knowledge graph extraction.

---

### Decision 3: Sequential Execution Model & Progress Feedback
- **Decision**: Execute document parsing strictly one by one in procedural sequence, emitting real-time status for each document to standard output (`stdout`) and diagnostic errors to standard error (`stderr`).
- **Rationale**:
  - Directly fulfills the user requirement: "read the pdf corpus, one by one and parse it to markdown".
  - Strictly adheres to the GraphRAG Experiment Constitution (Principle II: KISS & YAGNI; Principle IV: CLI-First).
  - Eliminates concurrency complexity, race conditions, or uncoordinated terminal logging.
  - Keeps memory usage predictable and bounded to one active document at a time.
- **Alternatives Considered**:
  - Multiprocessing / ThreadPool: Introduces synchronization overhead, multi-core contention, complex error recovery, and violates the explicit "one by one" mandate and Constitution's KISS principle.

---

### Decision 4: Git Tracking & Versioning for Markdown Corpus
- **Decision**: Persist output Markdown files into a dedicated `corpus_md/` directory at the repository root. Ensure that `.gitignore` explicitly does NOT exclude `corpus_md/`.
- **Rationale**:
  - Fulfills the explicit user requirement: "the md corpus will be versioned, so not ignored by git".
  - Clear separation of concerns: `corpus/` stores raw binary PDFs (ignored via `corpus/*` and preserved via `.gitkeep`), whereas `corpus_md/` stores human-readable, lightweight, reviewable text files that are tracked in Git.
  - Enables team members and CI pipelines to perform downstream GraphRAG tasks directly from tracked Markdown without requiring access to external PDF sources or local binary downloads.
- **Alternatives Considered**:
  - Storing `.md` files directly in `corpus/`: Conflicts with the established `.gitignore` rule `corpus/*` from Feature 001 and mixes binary artifacts with versioned source text. A separate directory provides cleaner repository hygiene.

---

## 2. Dependency Assessment

- **`pymupdf4llm`**:
  - PyPI package: `pymupdf4llm` (requires `pymupdf`).
  - Added to `requirements.txt`.
  - Python compatibility: 3.11+.
- **`pyyaml`**:
  - Already in `requirements.txt` from Feature 001. Used for reading `manifest.yml` and serializing frontmatter.
- **Python Standard Library**:
  - `argparse` (CLI parsing)
  - `pathlib` (filesystem paths)
  - `sys` (streams and exit codes)
  - `time` (timing batch execution)

---

## 3. Unknowns & Clarifications Resolution

| Item | Resolution | Source / Rationale |
|---|---|---|
| PDF parsing engine | `pymupdf4llm` | User prompt instruction |
| Concurrency model | Sequential (one-by-one) | User prompt instruction |
| Output directory | `corpus_md/` (configurable via `--output-dir`) | User requirement + sensible default |
| Git versioning | Committed to Git; not in `.gitignore` | User prompt instruction |
| Handling corrupt/missing PDFs | Log error to `stderr`, skip, continue batch | Spec resilience requirements |
| Metadata placement | YAML Frontmatter (`--- ... ---`) | RAG industry standard |
