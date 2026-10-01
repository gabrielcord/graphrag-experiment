# Feature Specification: Parse PDF Corpus to Markdown

**Feature Branch**: `002-parse-pdf-markdown`

**Created**: 2026-09-30

**Status**: Draft

**Input**: Sequentially parse the local PDF document corpus into standardized Markdown files driven by the document manifest (`manifest.yml`), storing output documents into a dedicated Markdown corpus folder that is actively tracked under Git version control (exempt from `.gitignore`).

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Sequential PDF Parsing from Manifest (Priority: P1)

As an ingestion pipeline operator or researcher, I want the system to read the document entries from the manifest one by one, locate each corresponding PDF file in the local corpus directory, and parse its contents into a standard Markdown document stored in a designated output directory, so that unstructured document contents are converted into a readable, standardized text format.

**Why this priority**: Core value of the feature. Without converting unstructured binary PDF files into Markdown documents, subsequent text processing, chunking, and knowledge graph construction cannot function.

**Independent Test**: Provide an input corpus directory containing sample PDF files matching entries in a manifest file. Execute the parsing command and verify that for each entry, a corresponding `.md` file is generated in the output directory containing the extracted text content.

**Acceptance Scenarios**:

1. **Given** a valid YAML manifest and an input corpus directory containing the referenced PDF files, **When** the parsing command is executed, **Then** the system processes each document strictly one at a time in sequence, generating a corresponding `<selection_id>.md` file in the output directory.
2. **Given** a manifest containing multiple entries, **When** the parsing command runs, **Then** real-time progress for each document and a final summary showing total parsed and total failed documents are displayed on standard output.

---

### User Story 2 - Git Versioning for Markdown Corpus (Priority: P2)

As a repository collaborator, I want the generated Markdown corpus directory and all produced Markdown files to be version-controlled in Git (explicitly not ignored by `.gitignore`), so that all team members and automated environments have immediate access to the parsed text corpus without having to re-download or re-parse binary files.

**Why this priority**: Ensures persistence, reproducibility, and team collaboration on the text corpus while differentiating the lightweight, reviewable Markdown corpus from the transient, ignored binary PDF files.

**Independent Test**: Run `git status` after generating Markdown files into the default Markdown corpus directory, and verify that the directory and its `.md` files are recognized as trackable/staged by Git, confirming they are not excluded by repository ignore rules.

**Acceptance Scenarios**:

1. **Given** the output Markdown corpus directory is created and populated with `.md` files, **When** repository ignore rules are checked, **Then** the Markdown directory and all `.md` files within it are NOT excluded by `.gitignore`.
2. **Given** newly generated `.md` files in the Markdown corpus directory, **When** `git status` is executed, **Then** the files are reported as untracked or modified and can be staged and committed to version control.

---

### User Story 3 - Fault Resilience & Idempotent Overwrite (Priority: P3)

As an operator running the parsing pipeline, I want the system to handle missing, corrupt, or unreadable PDF files gracefully by reporting errors to standard error without crashing the overall batch, and to support clean idempotent overwrites, so that errors on individual files do not abort the processing of the remaining corpus.

**Why this priority**: Guarantees pipeline robustness and batch resilience, ensuring that individual bad or missing files do not halt batch operations.

**Independent Test**: Run the parsing command with a manifest that contains a missing PDF file and a corrupted PDF file alongside valid PDF files. Verify that valid files are successfully parsed into clean Markdown without extraneous frontmatter, errors for invalid files are reported to standard error, and the batch completes successfully.

**Acceptance Scenarios**:

1. **Given** a valid PDF in the corpus directory, **When** it is parsed, **Then** the resulting Markdown file contains strictly the extracted document content without injecting extraneous metadata.
2. **Given** a document listed in the manifest whose corresponding PDF file is missing from the input corpus directory, **When** parsing executes, **Then** an error message is written to standard error with the document identifier, the item is recorded as failed, and parsing continues with the next item.
3. **Given** a corrupted or unreadable PDF file in the corpus directory, **When** parsing executes, **Then** an error message is written to standard error, the failure is recorded in the summary, and the batch continues without crashing.
4. **Given** a Markdown file that already exists in the output directory, **When** the parsing command runs again, **Then** the file is cleanly and idempotently overwritten with the latest parsed content.

---

### Edge Cases

- **Missing input PDF file**: When a document defined in the manifest does not exist in the input corpus directory, the system logs a diagnostic message to standard error with the `selection_id` and proceeds to the next document in sequence without halting.
- **Corrupt or unreadable PDF**: When a PDF file cannot be opened or parsed due to malformed data or encryption, the system logs the failure to standard error, marks the item as failed in the batch summary, and continues processing subsequent documents.
- **Pre-existing output Markdown file**: When a target `.md` file already exists in the destination folder, the system overwrites the existing file cleanly and idempotently.
- **Missing or invalid manifest file**: When the manifest file does not exist at the specified path or contains invalid YAML syntax, the system outputs a clear error message to standard error and terminates with a non-zero exit code.
- **Empty manifest**: When the manifest file contains no document entries, the system reports that zero documents were found to parse and exits cleanly with exit code 0.
- **Missing output directory**: When the destination directory does not yet exist on disk, the system automatically creates it before writing any parsed Markdown files.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST accept an optional command-line argument for the manifest YAML file path, defaulting to a fixed `manifest.yml` in the project root if omitted.
- **FR-002**: System MUST process documents strictly one by one in sequence according to the entries listed in the manifest.
- **FR-003**: System MUST resolve the input PDF path for each manifest entry as `<corpus-dir>/<selection_id>.pdf`, where `--corpus-dir` defaults to `corpus/` and can be overridden via command-line argument.
- **FR-004**: System MUST parse the textual content and structural elements of each PDF document and convert them into standard Markdown representation.
- **FR-005**: System MUST persist each converted document as `<output-dir>/<selection_id>.md`, where `--output-dir` defaults to `corpus_md/` and can be overridden via command-line argument.
- **FR-006**: System MUST ensure that the output Markdown directory and all generated `.md` files are version-controlled in Git and explicitly NOT excluded by `.gitignore`.
- **FR-007**: System MUST persist strictly the extracted document Markdown content to `<output-dir>/<selection_id>.md` without injecting frontmatter or extraneous metadata headers into the document body.
- **FR-008**: System MUST handle missing or unparseable PDF files gracefully by logging descriptive error details to standard error and continuing sequential execution for all remaining entries.
- **FR-009**: System MUST overwrite existing Markdown files idempotently when executed multiple times.
- **FR-010**: System MUST emit real-time status for each document processed to standard output, followed by a final completion summary indicating total documents processed, successfully parsed, and failed.

### Key Entities

- **Manifest Entry**: A single document record defined in the YAML manifest, containing identification and lineage attributes (`selection_id`, `title`, `group`, `source_id`, `url`).
- **Input Corpus Document**: A binary PDF file located on disk at `<corpus-dir>/<selection_id>.pdf` representing the source material to be parsed.
- **Parsed Markdown Document**: A version-controlled text file located on disk at `<output-dir>/<selection_id>.md` containing structured document metadata and extracted Markdown text.
- **Batch Parsing Summary**: Execution statistics reporting total items discovered in the manifest, count of successfully parsed documents, and count of failed or skipped documents.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of readable PDF documents in the corpus directory corresponding to manifest entries are successfully parsed into valid Markdown files in the output directory.
- **SC-002**: All generated Markdown files in the output directory are recognized by Git as version-controlled files without being filtered out by `.gitignore`.
- **SC-003**: The parsing tool executes completely via the command-line interface, providing real-time item status and a summary report upon completion.
- **SC-004**: The system demonstrates fault resilience by successfully processing all valid documents in a batch even when encountering missing or corrupt PDF files.
- **SC-005**: Re-running the parsing command over an existing output directory produces identical, cleanly overwritten Markdown files with exit code 0.

## Assumptions

- Input PDF documents have been downloaded to the input corpus directory (e.g. `corpus/`) prior to running the parsing command.
- The default output directory for versioned Markdown documents is `corpus_md/` at the repository root.
- In accordance with the project constitution, interaction is CLI-first and standard streams (`stdout` for informational output, `stderr` for errors/diagnostics) are used.
- Source PDF documents primarily contain text and headings that can be translated into standard Markdown formatting.
