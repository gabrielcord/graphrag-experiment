"""CLI tool to sequentially parse PDF files from a YAML manifest into versioned Markdown files."""

import argparse
from dataclasses import dataclass
from pathlib import Path
import sys
import time
from typing import Any

import pymupdf4llm
import yaml

DEFAULT_MANIFEST_PATH = "manifest.yml"
DEFAULT_CORPUS_DIR = "corpus"
DEFAULT_OUTPUT_DIR = "corpus_md"


@dataclass
class ManifestEntry:
    """Represents a validated document manifest item for parsing."""

    selection_id: str
    url: str
    title: str = ""
    group: str = ""
    source_id: str = ""


def is_valid_entry(item: Any) -> bool:
    """Validate that item is a dictionary with valid selection_id and url."""
    if not isinstance(item, dict):
        return False

    selection_id = item.get("selection_id")
    url = item.get("url")

    if not isinstance(selection_id, str) or not selection_id.strip():
        return False

    # Filesystem safe: no directory traversal
    if "/" in selection_id or "\\" in selection_id or ".." in selection_id:
        return False

    if not isinstance(url, str) or not url.strip():
        return False

    url_lower = url.strip().lower()
    if not (url_lower.startswith("http://") or url_lower.startswith("https://")):
        return False

    return True


def parse_manifest(manifest_path: str | Path) -> tuple[list[ManifestEntry], int]:
    """Parse YAML manifest file into validated entries and skipped count.

    Raises:
        FileNotFoundError: If the manifest file does not exist.
        ValueError: If YAML syntax is invalid or root is not a sequence.
    """
    path = Path(manifest_path)
    if not path.is_file():
        raise FileNotFoundError(f"Manifest file not found: {manifest_path}")

    try:
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
    except yaml.YAMLError as exc:
        raise ValueError(f"Invalid YAML syntax in manifest: {exc}") from exc

    if not isinstance(data, list):
        raise ValueError("Invalid manifest format: root element must be a sequence (list) of documents.")

    entries: list[ManifestEntry] = []
    skipped_count = 0

    for item in data:
        if is_valid_entry(item):
            entries.append(
                ManifestEntry(
                    selection_id=str(item["selection_id"]).strip(),
                    url=str(item["url"]).strip(),
                    title=str(item.get("title", "")).strip(),
                    group=str(item.get("group", "")).strip(),
                    source_id=str(item.get("source_id", "")).strip(),
                )
            )
        else:
            skipped_count += 1
            sys.stderr.write(
                f"[WARN] Skipping malformed item (missing required 'selection_id' or 'url'): {item}\n"
            )

    return entries, skipped_count


def parse_args(args: list[str] | None = None) -> argparse.Namespace:
    """Parse CLI arguments with default fallback to manifest.yml."""
    parser = argparse.ArgumentParser(
        prog="parse_corpus",
        description="Sequentially parse PDF files from a YAML manifest into versioned Markdown files.",
    )
    parser.add_argument(
        "manifest",
        nargs="?",
        default=DEFAULT_MANIFEST_PATH,
        help=f"Path to the YAML document manifest file (default: {DEFAULT_MANIFEST_PATH}).",
    )
    parser.add_argument(
        "--manifest",
        "-m",
        dest="manifest_flag",
        default=None,
        help="Alternative flag to specify path to the YAML manifest file (overrides positional argument).",
    )
    parser.add_argument(
        "--corpus-dir",
        "-c",
        default=DEFAULT_CORPUS_DIR,
        help=f"Directory containing downloaded PDF input documents (default: {DEFAULT_CORPUS_DIR}).",
    )
    parser.add_argument(
        "--output-dir",
        "-o",
        default=DEFAULT_OUTPUT_DIR,
        help=f"Directory where parsed Markdown files are saved (default: {DEFAULT_OUTPUT_DIR}).",
    )
    parsed = parser.parse_args(args)
    if parsed.manifest_flag:
        parsed.manifest = parsed.manifest_flag
    return parsed


def extract_pdf_to_markdown(pdf_path: str | Path) -> str:
    """Extract Markdown content from a PDF document using pymupdf4llm."""
    return pymupdf4llm.to_markdown(str(pdf_path))


def check_git_tracking(output_dir: str | Path, gitignore_path: str | Path = ".gitignore") -> bool:
    """Check that output_dir is not ignored by repository .gitignore."""
    gitignore_file = Path(gitignore_path)
    if not gitignore_file.is_file():
        return True

    dir_name = Path(output_dir).name
    try:
        content = gitignore_file.read_text(encoding="utf-8")
        for line in content.splitlines():
            stripped = line.strip()
            if stripped and not stripped.startswith("#"):
                if stripped in {dir_name, f"{dir_name}/", f"{dir_name}/*"}:
                    return False
    except OSError:
        pass

    return True


def parse_single_document(
    entry: ManifestEntry,
    corpus_dir: Path,
    output_dir: Path,
) -> bool:
    """Parse a single PDF document into Markdown with frontmatter.

    Returns:
        True if successfully parsed and saved, False otherwise.
    """
    pdf_path = corpus_dir / f"{entry.selection_id}.pdf"
    dest_path = output_dir / f"{entry.selection_id}.md"

    if not pdf_path.is_file():
        sys.stderr.write(f"[ERROR] ({entry.selection_id}): PDF not found at '{pdf_path}'\n")
        sys.stderr.flush()
        return False

    if pdf_path.stat().st_size == 0:
        sys.stderr.write(f"[ERROR] ({entry.selection_id}): PDF file is empty: '{pdf_path}'\n")
        sys.stderr.flush()
        return False

    try:
        markdown_body = extract_pdf_to_markdown(pdf_path)
    except Exception as exc:
        sys.stderr.write(
            f"[ERROR] ({entry.selection_id}): Failed to parse PDF '{pdf_path}': {exc}\n"
        )
        sys.stderr.flush()
        return False

    full_content = markdown_body
    if not full_content.endswith("\n"):
        full_content += "\n"

    try:
        # Idempotently write UTF-8 markdown file
        dest_path.write_text(full_content, encoding="utf-8")
    except OSError as exc:
        sys.stderr.write(
            f"[ERROR] ({entry.selection_id}): Failed to write output file '{dest_path}': {exc}\n"
        )
        sys.stderr.flush()
        return False

    return True


def run_pipeline(
    manifest_path: str = DEFAULT_MANIFEST_PATH,
    corpus_dir: str = DEFAULT_CORPUS_DIR,
    output_dir: str = DEFAULT_OUTPUT_DIR,
) -> int:
    """Execute the end-to-end PDF to Markdown parsing pipeline."""
    target_corpus = Path(corpus_dir)
    target_output = Path(output_dir)

    try:
        entries, skipped_count = parse_manifest(manifest_path)
    except (FileNotFoundError, ValueError) as exc:
        sys.stderr.write(f"[FATAL] {exc}\n")
        sys.stderr.flush()
        return 1

    target_output.mkdir(parents=True, exist_ok=True)

    is_tracked = check_git_tracking(target_output)
    tracking_notice = "tracked in Git" if is_tracked else "WARNING: ignored by .gitignore"

    total_items = len(entries)
    sys.stdout.write(f"Loaded {total_items} document entries from '{manifest_path}'.\n")
    sys.stdout.write(
        f"Reading PDFs from '{target_corpus.as_posix()}' -> writing Markdown to '{target_output.as_posix()}'.\n\n"
    )
    sys.stdout.flush()

    start_time = time.time()
    success_count = 0
    failed_count = 0

    for idx, entry in enumerate(entries, start=1):
        pdf_name = f"{entry.selection_id}.pdf"
        md_name = f"{entry.selection_id}.md"

        success = parse_single_document(
            entry=entry,
            corpus_dir=target_corpus,
            output_dir=target_output,
        )

        if success:
            success_count += 1
            sys.stdout.write(f"[{idx}/{total_items}] Parsing {pdf_name} -> {md_name}... [OK]\n")
        else:
            failed_count += 1
            sys.stdout.write(f"[{idx}/{total_items}] Parsing {pdf_name} -> {md_name}... [FAILED]\n")
        sys.stdout.flush()

    duration = time.time() - start_time

    summary = (
        "\n"
        "==================================================\n"
        f"Batch Parsing Completed in {duration:.2f}s:\n"
        f"  Total documents in manifest: {total_items}\n"
        f"  Successfully parsed:        {success_count}\n"
        f"  Failed / Skipped:            {failed_count + skipped_count}\n"
        f"  Output directory:           {target_output.as_posix()} ({tracking_notice})\n"
        "==================================================\n"
    )
    sys.stdout.write(summary)
    sys.stdout.flush()

    return 0


def main(argv: list[str] | None = None) -> None:
    """CLI entry point."""
    args = parse_args(argv)
    code = run_pipeline(
        manifest_path=args.manifest,
        corpus_dir=args.corpus_dir,
        output_dir=args.output_dir,
    )
    sys.exit(code)


if __name__ == "__main__":
    main()
