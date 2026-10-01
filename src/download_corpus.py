"""CLI tool to sequentially download PDF files from a YAML manifest into a local corpus directory."""

import argparse
import os
import shutil
import sys
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

RETRYABLE_HTTP_CODES = {429, 500, 502, 503, 504}


@dataclass
class ManifestEntry:
    """Represents a validated document manifest item."""

    selection_id: str
    url: str
    title: str = ""
    group: str = ""
    source_id: str = ""


def is_valid_entry(item: Any) -> bool:
    """Check if an item matches ManifestEntry constraints."""
    if not isinstance(item, dict):
        return False

    selection_id = item.get("selection_id")
    url = item.get("url")

    if not isinstance(selection_id, str) or not selection_id.strip():
        return False

    # Filesystem safe: no slashes or directory traversal
    if "/" in selection_id or "\\" in selection_id or ".." in selection_id:
        return False

    if not isinstance(url, str) or not url.strip():
        return False

    # Valid schema
    url_lower = url.strip().lower()
    if not (url_lower.startswith("http://") or url_lower.startswith("https://")):
        return False

    return True


def parse_manifest(manifest_path: str | Path) -> tuple[list[ManifestEntry], int]:
    """Parse YAML manifest into validated entries and skipped count.

    Raises:
        FileNotFoundError: If the manifest file does not exist.
        ValueError: If YAML syntax is invalid or root is not a list.
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
                    title=str(item.get("title", "")),
                    group=str(item.get("group", "")),
                    source_id=str(item.get("source_id", "")),
                )
            )
        else:
            skipped_count += 1
            sys.stderr.write(
                f"[WARN] Skipping malformed item (missing required 'selection_id' or 'url'): {item}\n"
            )

    return entries, skipped_count


DEFAULT_MANIFEST_PATH = "manifest.yml"


def parse_args(args: list[str] | None = None) -> argparse.Namespace:
    """Parse CLI arguments with default fallback to manifest.yml."""
    parser = argparse.ArgumentParser(
        prog="download_corpus",
        description="Sequentially download PDF files from a YAML manifest into a corpus folder.",
    )
    parser.add_argument(
        "manifest_path",
        nargs="?",
        default=DEFAULT_MANIFEST_PATH,
        help=f"Path to the YAML file containing the list of documents to download (default: {DEFAULT_MANIFEST_PATH}).",
    )
    parser.add_argument(
        "--manifest",
        dest="manifest_flag",
        default=None,
        help="Alternative flag to specify path to the YAML manifest file (overrides positional argument).",
    )
    parser.add_argument(
        "--corpus-dir",
        default="corpus",
        help="Target directory where PDF files are stored (default: corpus).",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=1.0,
        help="Polite delay in seconds between consecutive downloads (default: 1.0).",
    )
    parser.add_argument(
        "--max-retries",
        type=int,
        default=3,
        help="Maximum exponential backoff retries on transient errors (default: 3).",
    )
    parsed = parser.parse_args(args)
    if parsed.manifest_flag:
        parsed.manifest_path = parsed.manifest_flag
    return parsed


def ensure_git_ignored(corpus_dir: str | Path, gitignore_path: str | Path = ".gitignore") -> None:
    """Ensure that the corpus files are excluded in .gitignore while preserving .gitkeep."""
    dir_name = Path(corpus_dir).name
    wildcard_pattern = f"{dir_name}/*"
    gitkeep_pattern = f"!{dir_name}/.gitkeep"
    legacy_pattern = f"{dir_name}/"
    gitignore_file = Path(gitignore_path)

    content = ""
    existing_lines: list[str] = []
    if gitignore_file.is_file():
        try:
            content = gitignore_file.read_text(encoding="utf-8")
            existing_lines = [line.strip() for line in content.splitlines()]
        except OSError:
            content = ""
            existing_lines = []

    # If legacy_pattern ('corpus/') was present, replace it with 'corpus/*' and '!corpus/.gitkeep'
    if legacy_pattern in existing_lines and wildcard_pattern not in existing_lines:
        lines: list[str] = []
        for line in content.splitlines():
            if line.strip() == legacy_pattern:
                lines.append(wildcard_pattern)
                lines.append(gitkeep_pattern)
            else:
                lines.append(line)
        try:
            gitignore_file.write_text("\n".join(lines) + "\n", encoding="utf-8")
        except OSError as exc:
            sys.stderr.write(f"[WARN] Could not update {gitignore_path}: {exc}\n")
        return

    to_add: list[str] = []
    if wildcard_pattern not in existing_lines:
        to_add.append(wildcard_pattern)
    if gitkeep_pattern not in existing_lines:
        to_add.append(gitkeep_pattern)

    if not to_add:
        return

    prefix = "\n" if content and not content.endswith("\n") else ""
    try:
        with open(gitignore_file, "a", encoding="utf-8") as f:
            for pat in to_add:
                f.write(f"{prefix}{pat}\n")
                prefix = ""
    except OSError as exc:
        sys.stderr.write(f"[WARN] Could not update {gitignore_path}: {exc}\n")


def format_file_size(size_bytes: int) -> str:
    """Format bytes into human-readable string."""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    else:
        return f"{size_bytes / (1024 * 1024):.1f} MB"


def download_single_file(
    entry: ManifestEntry,
    corpus_dir: Path,
    delay: float = 1.0,
    max_retries: int = 3,
    timeout: float = 30.0,
) -> bool:
    """Download a single PDF file with exponential backoff retries and atomic persistence.

    Returns:
        True if the file was successfully downloaded and saved, False otherwise.
    """
    dest_path = corpus_dir / f"{entry.selection_id}.pdf"
    tmp_path = corpus_dir / f"{entry.selection_id}.pdf.tmp"

    request = urllib.request.Request(
        entry.url,
        headers={"User-Agent": "GraphRAG-CorpusDownloader/1.0 (Ethical Scraper)"},
    )

    attempt = 0
    while attempt <= max_retries:
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                with open(tmp_path, "wb") as out_file:
                    shutil.copyfileobj(response, out_file)

            # Atomic replace to guarantee idempotent overwrite and prevent file corruption
            os.replace(tmp_path, dest_path)
            file_size = dest_path.stat().st_size
            sys.stdout.write(
                f"[OK] {entry.selection_id} -> {dest_path} ({format_file_size(file_size)})\n"
            )
            sys.stdout.flush()
            return True

        except urllib.error.HTTPError as exc:
            if tmp_path.exists():
                try:
                    tmp_path.unlink()
                except OSError:
                    pass

            if exc.code in RETRYABLE_HTTP_CODES and attempt < max_retries:
                wait_time = delay * (2**attempt)
                sys.stderr.write(
                    f"[WARN] Transient error downloading '{entry.selection_id}' "
                    f"(HTTP Error {exc.code}: {exc.reason}). Retrying in {wait_time:.1f}s "
                    f"(attempt {attempt + 1}/{max_retries})...\n"
                )
                sys.stderr.flush()
                time.sleep(wait_time)
                attempt += 1
                continue
            else:
                sys.stderr.write(
                    f"[ERROR] Failed to download '{entry.selection_id}' from '{entry.url}': "
                    f"HTTP Error {exc.code}: {exc.reason}\n"
                )
                sys.stderr.flush()
                return False

        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            if tmp_path.exists():
                try:
                    tmp_path.unlink()
                except OSError:
                    pass

            if attempt < max_retries:
                wait_time = delay * (2**attempt)
                sys.stderr.write(
                    f"[WARN] Network error downloading '{entry.selection_id}' ({exc}). "
                    f"Retrying in {wait_time:.1f}s (attempt {attempt + 1}/{max_retries})...\n"
                )
                sys.stderr.flush()
                time.sleep(wait_time)
                attempt += 1
                continue
            else:
                sys.stderr.write(
                    f"[ERROR] Failed to download '{entry.selection_id}' from '{entry.url}': {exc}\n"
                )
                sys.stderr.flush()
                return False

    return False


def run_pipeline(
    manifest_path: str,
    corpus_dir: str = "corpus",
    delay: float = 1.0,
    max_retries: int = 3,
) -> int:
    """Execute the end-to-end download pipeline."""
    target_dir = Path(corpus_dir)
    target_dir.mkdir(parents=True, exist_ok=True)
    gitkeep = target_dir / ".gitkeep"
    if not gitkeep.exists():
        gitkeep.touch()

    # Automatically exclude corpus files while preserving .gitkeep
    ensure_git_ignored(corpus_dir=corpus_dir)

    try:
        entries, skipped_count = parse_manifest(manifest_path)
    except (FileNotFoundError, ValueError) as exc:
        sys.stderr.write(f"[FATAL] {exc}\n")
        return 1

    total_items = len(entries) + skipped_count
    downloaded_count = 0
    failed_count = 0

    total_entries = len(entries)
    for idx, entry in enumerate(entries):
        success = download_single_file(
            entry=entry,
            corpus_dir=target_dir,
            delay=delay,
            max_retries=max_retries,
        )
        if success:
            downloaded_count += 1
            # Polite pause between consecutive successful requests
            if idx < total_entries - 1 and delay > 0:
                time.sleep(delay)
        else:
            failed_count += 1

    # Output final summary block
    summary = (
        "========================================\n"
        "Corpus Download Summary\n"
        "========================================\n"
        f"Total items:        {total_items}\n"
        f"Downloaded/Updated: {downloaded_count}\n"
        f"Failed downloads:   {failed_count}\n"
        f"Malformed/Skipped:  {skipped_count}\n"
        f"Target directory:   {target_dir.as_posix()}/\n"
        f"Polite delay:       {delay:.1f}s\n"
        "========================================\n"
    )
    sys.stdout.write(summary)
    sys.stdout.flush()

    return 0


def main(argv: list[str] | None = None) -> None:
    """CLI entry point."""
    args = parse_args(argv)
    code = run_pipeline(
        manifest_path=args.manifest_path,
        corpus_dir=args.corpus_dir,
        delay=args.delay,
        max_retries=args.max_retries,
    )
    sys.exit(code)


if __name__ == "__main__":
    main()
