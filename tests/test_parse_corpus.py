"""Unit tests for the parse_corpus module."""

import io
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from src.parse_corpus import (
    DEFAULT_CORPUS_DIR,
    DEFAULT_MANIFEST_PATH,
    DEFAULT_OUTPUT_DIR,
    ManifestEntry,
    check_git_tracking,
    extract_pdf_to_markdown,
    is_valid_entry,
    parse_args,
    parse_manifest,
    parse_single_document,
    run_pipeline,
)


class TestManifestParsing(unittest.TestCase):
    """Tests for manifest loading and validation in parse_corpus."""

    def test_is_valid_entry_valid(self):
        entry = {
            "selection_id": "doc-001",
            "url": "https://example.com/doc.pdf",
            "title": "Doc 1",
            "group": "Group A",
            "source_id": "src-1",
        }
        self.assertTrue(is_valid_entry(entry))

    def test_is_valid_entry_invalid_selection_id(self):
        self.assertFalse(is_valid_entry({"selection_id": "", "url": "https://example.com/doc.pdf"}))
        self.assertFalse(is_valid_entry({"selection_id": 123, "url": "https://example.com/doc.pdf"}))
        self.assertFalse(is_valid_entry({"selection_id": "../doc", "url": "https://example.com/doc.pdf"}))
        self.assertFalse(is_valid_entry({"selection_id": "dir/doc", "url": "https://example.com/doc.pdf"}))

    def test_is_valid_entry_invalid_url(self):
        self.assertFalse(is_valid_entry({"selection_id": "doc-001", "url": ""}))
        self.assertFalse(is_valid_entry({"selection_id": "doc-001", "url": "ftp://example.com/doc.pdf"}))
        self.assertFalse(is_valid_entry({"selection_id": "doc-001", "url": "file:///tmp/doc.pdf"}))

    def test_parse_manifest_success(self):
        content = """
- selection_id: doc-001
  url: https://example.com/doc1.pdf
  title: Document 1
  group: Group A
  source_id: src-1
- selection_id: doc-002
  url: http://example.com/doc2.pdf
  title: Document 2
"""
        with tempfile.NamedTemporaryFile("w", suffix=".yml", delete=False) as f:
            f.write(content)
            temp_path = f.name

        try:
            entries, skipped = parse_manifest(temp_path)
            self.assertEqual(len(entries), 2)
            self.assertEqual(skipped, 0)
            self.assertEqual(entries[0].selection_id, "doc-001")
            self.assertEqual(entries[0].title, "Document 1")
            self.assertEqual(entries[1].selection_id, "doc-002")
        finally:
            Path(temp_path).unlink(missing_ok=True)

    def test_parse_manifest_file_not_found(self):
        with self.assertRaises(FileNotFoundError):
            parse_manifest("non_existent_manifest.yml")

    def test_parse_manifest_invalid_yaml(self):
        with tempfile.NamedTemporaryFile("w", suffix=".yml", delete=False) as f:
            f.write("invalid: [yaml: unclosed")
            temp_path = f.name

        try:
            with self.assertRaises(ValueError):
                parse_manifest(temp_path)
        finally:
            Path(temp_path).unlink(missing_ok=True)

    def test_parse_manifest_not_a_list(self):
        with tempfile.NamedTemporaryFile("w", suffix=".yml", delete=False) as f:
            f.write("key: value\n")
            temp_path = f.name

        try:
            with self.assertRaises(ValueError):
                parse_manifest(temp_path)
        finally:
            Path(temp_path).unlink(missing_ok=True)

    def test_parse_manifest_skips_malformed_entries(self):
        content = """
- selection_id: valid-01
  url: https://example.com/doc.pdf
- selection_id: ""
  url: https://example.com/bad.pdf
- not_even_dict
"""
        with tempfile.NamedTemporaryFile("w", suffix=".yml", delete=False) as f:
            f.write(content)
            temp_path = f.name

        try:
            with patch("sys.stderr", new_callable=io.StringIO):
                entries, skipped = parse_manifest(temp_path)
            self.assertEqual(len(entries), 1)
            self.assertEqual(skipped, 2)
            self.assertEqual(entries[0].selection_id, "valid-01")
        finally:
            Path(temp_path).unlink(missing_ok=True)


class TestCliArgs(unittest.TestCase):
    """Tests for CLI arguments handling in parse_corpus."""

    def test_defaults(self):
        args = parse_args([])
        self.assertEqual(args.manifest, DEFAULT_MANIFEST_PATH)
        self.assertEqual(args.corpus_dir, DEFAULT_CORPUS_DIR)
        self.assertEqual(args.output_dir, DEFAULT_OUTPUT_DIR)

    def test_positional_manifest(self):
        args = parse_args(["custom_manifest.yml"])
        self.assertEqual(args.manifest, "custom_manifest.yml")

    def test_flag_manifest_overrides_positional(self):
        args = parse_args(["pos_manifest.yml", "--manifest", "flag_manifest.yml"])
        self.assertEqual(args.manifest, "flag_manifest.yml")

    def test_custom_corpus_and_output_dirs(self):
        args = parse_args(["-c", "my_corpus", "-o", "my_output"])
        self.assertEqual(args.corpus_dir, "my_corpus")
        self.assertEqual(args.output_dir, "my_output")


class TestDocumentParsing(unittest.TestCase):
    """Tests for document parsing, filesystem persistence, and resilience."""

    def test_parse_single_document_success(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            corpus_dir = Path(tmp_dir) / "corpus"
            output_dir = Path(tmp_dir) / "corpus_md"
            corpus_dir.mkdir()
            output_dir.mkdir()

            pdf_file = corpus_dir / "doc-1.pdf"
            pdf_file.write_bytes(b"%PDF-1.4 dummy content")

            entry = ManifestEntry(
                selection_id="doc-1",
                url="https://example.com/doc1.pdf",
                title="Doc One",
                group="Group A",
                source_id="src-1",
            )

            with patch("src.parse_corpus.extract_pdf_to_markdown", return_value="# Body Content\n\nSome text"):
                success = parse_single_document(entry, corpus_dir, output_dir)

            self.assertTrue(success)
            dest_file = output_dir / "doc-1.md"
            self.assertTrue(dest_file.is_file())
            content = dest_file.read_text(encoding="utf-8")
            self.assertEqual(content, "# Body Content\n\nSome text\n")
            self.assertNotIn("---", content)
            self.assertNotIn("selection_id:", content)

    def test_parse_single_document_idempotent_overwrite(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            corpus_dir = Path(tmp_dir) / "corpus"
            output_dir = Path(tmp_dir) / "corpus_md"
            corpus_dir.mkdir()
            output_dir.mkdir()

            pdf_file = corpus_dir / "doc-1.pdf"
            pdf_file.write_bytes(b"%PDF-1.4 dummy content")

            dest_file = output_dir / "doc-1.md"
            dest_file.write_text("old content", encoding="utf-8")

            entry = ManifestEntry(
                selection_id="doc-1",
                url="https://example.com/doc1.pdf",
                title="Doc One",
            )

            with patch("src.parse_corpus.extract_pdf_to_markdown", return_value="new content"):
                success = parse_single_document(entry, corpus_dir, output_dir)

            self.assertTrue(success)
            content = dest_file.read_text(encoding="utf-8")
            self.assertIn("new content", content)
            self.assertNotIn("old content", content)

    def test_parse_single_document_missing_pdf(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            corpus_dir = Path(tmp_dir) / "corpus"
            output_dir = Path(tmp_dir) / "corpus_md"
            corpus_dir.mkdir()
            output_dir.mkdir()

            entry = ManifestEntry(
                selection_id="missing-doc",
                url="https://example.com/missing.pdf",
            )

            with patch("sys.stderr", new_callable=io.StringIO) as mock_stderr:
                success = parse_single_document(entry, corpus_dir, output_dir)

            self.assertFalse(success)
            self.assertIn("PDF not found", mock_stderr.getvalue())

    def test_parse_single_document_empty_pdf(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            corpus_dir = Path(tmp_dir) / "corpus"
            output_dir = Path(tmp_dir) / "corpus_md"
            corpus_dir.mkdir()
            output_dir.mkdir()

            pdf_file = corpus_dir / "empty.pdf"
            pdf_file.write_bytes(b"")

            entry = ManifestEntry(
                selection_id="empty",
                url="https://example.com/empty.pdf",
            )

            with patch("sys.stderr", new_callable=io.StringIO) as mock_stderr:
                success = parse_single_document(entry, corpus_dir, output_dir)

            self.assertFalse(success)
            self.assertIn("PDF file is empty", mock_stderr.getvalue())

    def test_parse_single_document_corrupt_pdf(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            corpus_dir = Path(tmp_dir) / "corpus"
            output_dir = Path(tmp_dir) / "corpus_md"
            corpus_dir.mkdir()
            output_dir.mkdir()

            pdf_file = corpus_dir / "corrupt.pdf"
            pdf_file.write_bytes(b"garbage")

            entry = ManifestEntry(
                selection_id="corrupt",
                url="https://example.com/corrupt.pdf",
            )

            with patch(
                "src.parse_corpus.extract_pdf_to_markdown",
                side_effect=RuntimeError("MuPDF error: invalid object"),
            ):
                with patch("sys.stderr", new_callable=io.StringIO) as mock_stderr:
                    success = parse_single_document(entry, corpus_dir, output_dir)

            self.assertFalse(success)
            self.assertIn("Failed to parse PDF", mock_stderr.getvalue())


class TestGitTracking(unittest.TestCase):
    """Tests for Git tracking validation for corpus_md."""

    def test_check_git_tracking_not_ignored(self):
        with tempfile.NamedTemporaryFile("w", suffix=".gitignore", delete=False) as f:
            f.write("corpus/*\n!corpus/.gitkeep\n__pycache__/\n")
            gitignore_path = f.name

        try:
            self.assertTrue(check_git_tracking("corpus_md", gitignore_path=gitignore_path))
        finally:
            Path(gitignore_path).unlink(missing_ok=True)

    def test_check_git_tracking_ignored_warning(self):
        with tempfile.NamedTemporaryFile("w", suffix=".gitignore", delete=False) as f:
            f.write("corpus_md/\n")
            gitignore_path = f.name

        try:
            self.assertFalse(check_git_tracking("corpus_md", gitignore_path=gitignore_path))
        finally:
            Path(gitignore_path).unlink(missing_ok=True)


class TestPipelineExecution(unittest.TestCase):
    """Tests for end-to-end run_pipeline execution."""

    def test_run_pipeline_success(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            corpus_dir = Path(tmp_dir) / "corpus"
            output_dir = Path(tmp_dir) / "corpus_md"
            corpus_dir.mkdir()

            pdf1 = corpus_dir / "doc-1.pdf"
            pdf1.write_bytes(b"%PDF content 1")
            pdf2 = corpus_dir / "doc-2.pdf"
            pdf2.write_bytes(b"%PDF content 2")

            manifest_content = """
- selection_id: doc-1
  url: https://example.com/doc1.pdf
  title: Title 1
- selection_id: doc-2
  url: https://example.com/doc2.pdf
  title: Title 2
"""
            manifest_file = Path(tmp_dir) / "manifest.yml"
            manifest_file.write_text(manifest_content, encoding="utf-8")

            with patch("src.parse_corpus.extract_pdf_to_markdown", return_value="Extracted content"):
                with patch("sys.stdout", new_callable=io.StringIO) as mock_stdout:
                    code = run_pipeline(
                        manifest_path=str(manifest_file),
                        corpus_dir=str(corpus_dir),
                        output_dir=str(output_dir),
                    )

            self.assertEqual(code, 0)
            output = mock_stdout.getvalue()
            self.assertIn("Loaded 2 document entries", output)
            self.assertIn("[1/2] Parsing doc-1.pdf -> doc-1.md... [OK]", output)
            self.assertIn("[2/2] Parsing doc-2.pdf -> doc-2.md... [OK]", output)
            self.assertIn("Successfully parsed:        2", output)
            self.assertTrue((output_dir / "doc-1.md").is_file())
            self.assertTrue((output_dir / "doc-2.md").is_file())

    def test_run_pipeline_partial_failures(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            corpus_dir = Path(tmp_dir) / "corpus"
            output_dir = Path(tmp_dir) / "corpus_md"
            corpus_dir.mkdir()

            pdf1 = corpus_dir / "valid-doc.pdf"
            pdf1.write_bytes(b"%PDF valid")

            manifest_content = """
- selection_id: valid-doc
  url: https://example.com/valid.pdf
- selection_id: missing-doc
  url: https://example.com/missing.pdf
"""
            manifest_file = Path(tmp_dir) / "manifest.yml"
            manifest_file.write_text(manifest_content, encoding="utf-8")

            with patch("src.parse_corpus.extract_pdf_to_markdown", return_value="Valid text"):
                with patch("sys.stdout", new_callable=io.StringIO) as mock_stdout:
                    with patch("sys.stderr", new_callable=io.StringIO) as mock_stderr:
                        code = run_pipeline(
                            manifest_path=str(manifest_file),
                            corpus_dir=str(corpus_dir),
                            output_dir=str(output_dir),
                        )

            self.assertEqual(code, 0)
            self.assertIn("[1/2] Parsing valid-doc.pdf -> valid-doc.md... [OK]", mock_stdout.getvalue())
            self.assertIn("[2/2] Parsing missing-doc.pdf -> missing-doc.md... [FAILED]", mock_stdout.getvalue())
            self.assertIn("PDF not found", mock_stderr.getvalue())
            self.assertIn("Successfully parsed:        1", mock_stdout.getvalue())
            self.assertIn("Failed / Skipped:            1", mock_stdout.getvalue())

    def test_run_pipeline_missing_manifest(self):
        with patch("sys.stderr", new_callable=io.StringIO) as mock_stderr:
            code = run_pipeline(manifest_path="does_not_exist.yml")
        self.assertEqual(code, 1)
        self.assertIn("[FATAL]", mock_stderr.getvalue())


if __name__ == "__main__":
    unittest.main()
