# Feature Specification: Download PDF Corpus from YAML List

**Feature Branch**: `001-download-pdf-corpus`

**Created**: 2026-09-30

**Status**: Draft

**Input**: User description: "Download PDF files sequentially from a YAML manifest containing document URLs and metadata into a local 'corpus/' directory preserved in Git via .gitkeep but whose downloaded files are ignored, naming files after their selection_id, replacing existing files idempotently, with polite delays between requests and exponential backoff retry on errors to protect source servers."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Download PDF Files to Corpus Directory (Priority: P1)

As a researcher or developer running the ingestion pipeline, I want to provide a YAML file containing a list of document entries with URLs and metadata, so that all referenced PDF documents are automatically downloaded into a local `corpus/` folder with filenames derived from `selection_id`.

**Why this priority**: Core capability of the feature. Without downloaded PDF documents in the corpus directory, subsequent indexing, chunking, and GraphRAG operations cannot take place.

**Independent Test**: Provide a sample YAML file containing a list of document entries with valid PDF URLs and distinct `selection_id` values. Execute the download command and verify that each corresponding `<selection_id>.pdf` file exists in the `corpus/` directory with non-zero size.

**Acceptance Scenarios**:

1. **Given** a valid YAML file containing document entries with `selection_id` and `url`, **When** the download command is executed with the file path, **Then** all referenced PDF files are downloaded and saved to `corpus/<selection_id>.pdf`.
2. **Given** a valid YAML file with document entries, **When** the download command executes, **Then** real-time progress and a final completion summary (total downloaded/replaced and failed) are emitted to standard output.

---

### User Story 2 - Maintain Corpus Directory in Git via .gitkeep with Ignored Contents (Priority: P2)

As a repository collaborator, I want the `corpus/` folder structure to be tracked and preserved in version control via a `.gitkeep` placeholder file, while ensuring all downloaded PDF files and temporary artifacts are ignored by Git, so that the repository contains the necessary folder on clone without tracking large binary downloads.

**Why this priority**: Preserves repository structure across clones while preventing repository bloat from committing large binary artifacts or transient datasets to git history.

**Independent Test**: Inspect `corpus/` to verify that `corpus/.gitkeep` exists and is trackable by Git, and verify that `.gitignore` excludes contents of `corpus/` while allowing `!corpus/.gitkeep` so that downloaded PDF files never appear as untracked files in `git status`.

**Acceptance Scenarios**:

1. **Given** the corpus directory is initialized, **When** the directory is created or verified, **Then** `corpus/.gitkeep` is created if not already present.
2. **Given** a repository with a `.gitignore` file, **When** the corpus directory is configured, **Then** `.gitignore` excludes `corpus/*` while un-ignoring `!corpus/.gitkeep`.
3. **Given** files exist within `corpus/`, **When** `git status` is executed, **Then** `corpus/.gitkeep` is recognized by Git and no downloaded PDF files appear as untracked files.

---

### User Story 3 - Polite Sequential Downloads, Exponential Backoff & Idempotency (Priority: P3)

As an operator downloading from public institutions or rate-limited web servers, I want downloads to occur strictly in sequence with a polite delay between each request and exponential backoff on errors, so that the remote server is not overwhelmed or harmed, while ensuring idempotent replacement and overall batch resilience.

**Why this priority**: Guarantees ethical scraping and server respect, prevents rate-limiting IP bans, and ensures fault-tolerant and idempotent batch processing over public networks.

**Independent Test**: Execute the command on a manifest with multiple items, an existing file (verified overwritten), and a server that temporarily returns a retryable error or rate limit. Verify that downloads occur sequentially with pauses between requests, exponential backoff retries resolve transient errors or gracefully log failures to stderr, and execution completes with exit code 0.

**Acceptance Scenarios**:

1. **Given** multiple entries in a YAML manifest, **When** the download runs, **Then** each item is processed strictly one at a time (sequential) with a polite delay (default 1.0s) between successive requests.
2. **Given** `corpus/<selection_id>.pdf` already exists locally, **When** the download command runs, **Then** the system downloads the file and cleanly replaces the existing local file.
3. **Given** an entry encounters a transient HTTP error (e.g. 429, 500, 502, 503, 504) or connection timeout, **When** the error occurs, **Then** the system waits using exponential backoff before retrying (up to 3 retries) before declaring failure.
4. **Given** an entry whose URL permanently fails after retries, **When** the retries are exhausted, **Then** the failure is reported to standard error with item details, and the batch proceeds to the next document.

---

### Edge Cases

- What happens when a file already exists in `corpus/` with the same name? The system overwrites the file with the newly downloaded content, ensuring idempotency.
- What happens when `corpus/.gitkeep` is present during download? The downloader operates solely on `<selection_id>.pdf` and leaves `.gitkeep` intact.
- What happens when the remote server returns HTTP 429 Too Many Requests or 5xx Server Error? The system pauses with exponential backoff (e.g. 1s, 2s, 4s) and retries up to a maximum limit (default 3 retries).
- What happens when the specified YAML file path does not exist or contains invalid YAML syntax? The system halts execution immediately, prints an error message to standard error, and exits with a non-zero status code.
- What happens when an entry in the YAML manifest is missing `url` or `selection_id`? The system emits a warning to standard error for the malformed entry, skips it, and continues processing the remaining entries.
- What happens when the `corpus/` directory does not exist on disk? The system creates the directory automatically before attempting to write files and ensures `corpus/.gitkeep` is created.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST provide a command-line interface accepting a file path parameter pointing to the input YAML manifest, defaulting to `manifest.yml` if omitted.
- **FR-002**: System MUST parse the input YAML file as a direct sequence (list) of document entries containing `selection_id` and `url`, and supporting optional metadata attributes (`title`, `group`, `source_id`) without requiring an `items` wrapper key.
- **FR-003**: System MUST create the destination directory `corpus/` at the repository root if it does not already exist, and create `corpus/.gitkeep` if absent so the directory is preserved in version control.
- **FR-004**: System MUST ensure that `.gitignore` ignores all downloaded files and temporary artifacts in `corpus/` while allowing `corpus/.gitkeep` to be tracked (e.g. `corpus/*` and `!corpus/.gitkeep`).
- **FR-005**: System MUST download the remote PDF for each valid entry in the list and save it as `corpus/<selection_id>.pdf`.
- **FR-006**: System MUST overwrite and replace any existing destination file (`corpus/<selection_id>.pdf`) with the newly downloaded file, ensuring idempotent execution across multiple runs.
- **FR-007**: System MUST output human-readable progress information during execution and a final summary showing count of downloaded (including replaced) and failed files.
- **FR-008**: System MUST emit item-level download failures to standard error and continue downloading subsequent entries in the batch.
- **FR-009**: System MUST return an exit code of 0 when all valid entries are processed (downloaded/replaced), and a non-zero exit code if fatal configuration or input errors occur.
- **FR-010**: System MUST process document downloads strictly sequentially (one at a time, never in parallel).
- **FR-011**: System MUST enforce a polite delay between consecutive downloads (default: 1.0 second, configurable via CLI argument `--delay`) to avoid overwhelming the source website.
- **FR-012**: System MUST apply exponential backoff retry logic (up to 3 retries with doubling wait intervals: e.g. 1s, 2s, 4s) when encountering retryable HTTP status codes (429, 500, 502, 503, 504) or network timeouts before logging an item failure.

### Key Entities *(include if feature involves data)*

- **Document Manifest Entry**: Represents a single document entry within the top-level YAML list:

| Field | Type | Requirement | Description |
|---|---|---|---|
| `selection_id` | String | Mandatory | Unique document identifier used as the target filename (`<selection_id>.pdf`). |
| `url` | String | Mandatory | Remote web URL pointing directly to the PDF file. |
| `title` | String | Optional | Descriptive human-readable title of the document. |
| `group` | String | Optional | Functional or thematic classification (e.g., `Editais Encerrados 2025`, `Resoluções CCAF`). |
| `source_id` | String | Optional | Origin collection identifier (e.g., `editais-encerrados`, `resolucoes`). |

- **Corpus Directory**: The local storage directory (`corpus/`) at the repository root containing `corpus/.gitkeep` to preserve the folder structure in Git, while its binary PDF artifacts are ignored.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of accessible URLs in a provided YAML manifest are downloaded into `corpus/` with corresponding `<selection_id>.pdf` filenames.
- **SC-002**: Executing the download command repeatedly against the same manifest results in an idempotent state where all existing destination files are cleanly replaced with the latest remote content without file corruption or duplication.
- **SC-003**: The `corpus/` directory structure is preserved in Git via `corpus/.gitkeep`, while `git status` reports zero untracked PDF files in `corpus/`.
- **SC-004**: An unreachable URL in a batch does not abort execution of remaining URLs in the input manifest.
- **SC-005**: Output summary accurately reflects the count of downloaded/replaced and failed documents upon command completion.
- **SC-006**: Successive HTTP requests adhere to the configured politeness interval (default 1.0s) and are never executed concurrently.
- **SC-007**: Transient network timeouts and HTTP 429/5xx errors trigger automatic exponential backoff retries up to the maximum retry count before failing.

## Assumptions

- The input manifest is a YAML file containing a top-level list of document entries (no top-level `items:` key required).
- The repository tracks `corpus/.gitkeep` so the `corpus/` folder exists immediately upon checkout/clone.
- Downloads are executed strictly sequentially to protect source servers from load spikes.
- A default polite delay of 1.0 second between downloads is appropriate for typical public servers and can be overridden via CLI if needed.
- Up to 3 retries with exponential backoff (e.g., 1.0s, 2.0s, 4.0s) provide an optimal balance between resilience and execution time.
- The destination directory name is strictly `corpus/` located at the root of the project.
- Destination filenames are standardized as `<selection_id>.pdf` to ensure determinism and avoid invalid filesystem characters.
- In compliance with the project constitution, implementation will be minimal, written in Python 3.11+, and operated exclusively via CLI.
