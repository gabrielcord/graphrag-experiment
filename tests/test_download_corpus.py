"""Unit tests for the download_corpus module."""

import io
import tempfile
import unittest
import urllib.error
from pathlib import Path
from unittest.mock import MagicMock, call, patch

from src.download_corpus import (
    ManifestEntry,
    ensure_git_ignored,
    format_file_size,
    is_valid_entry,
    parse_args,
    parse_manifest,
    run_pipeline,
)


class TestManifestParsing(unittest.TestCase):
    """Tests for manifest validation and parsing."""

    def test_is_valid_entry_valid(self):
        entry = {
            "selection_id": "doc-001",
            "url": "https://example.com/doc.pdf",
            "title": "Doc 1",
        }
        self.assertTrue(is_valid_entry(entry))

    def test_is_valid_entry_invalid_selection_id(self):
        # Empty selection_id
        self.assertFalse(is_valid_entry({"selection_id": "", "url": "https://example.com/doc.pdf"}))
        # Non-string selection_id
        self.assertFalse(is_valid_entry({"selection_id": 123, "url": "https://example.com/doc.pdf"}))
        # Path traversal characters
        self.assertFalse(is_valid_entry({"selection_id": "../doc", "url": "https://example.com/doc.pdf"}))
        self.assertFalse(is_valid_entry({"selection_id": "dir/doc", "url": "https://example.com/doc.pdf"}))

    def test_is_valid_entry_invalid_url(self):
        # Empty url
        self.assertFalse(is_valid_entry({"selection_id": "doc-001", "url": ""}))
        # Invalid scheme
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
"""
        with tempfile.NamedTemporaryFile("w", suffix=".yml", delete=False) as f:
            f.write(content)
            temp_path = f.name

        try:
            entries, skipped = parse_manifest(temp_path)
            self.assertEqual(len(entries), 2)
            self.assertEqual(skipped, 0)
            self.assertEqual(entries[0].selection_id, "doc-001")
            self.assertEqual(entries[0].url, "https://example.com/doc1.pdf")
            self.assertEqual(entries[0].title, "Document 1")
            self.assertEqual(entries[1].selection_id, "doc-002")
        finally:
            Path(temp_path).unlink()

    def test_parse_manifest_skips_malformed(self):
        content = """
- selection_id: doc-valid
  url: https://example.com/valid.pdf
- missing_url: true
  selection_id: doc-invalid
- selection_id: ""
  url: https://example.com/empty-id.pdf
"""
        with tempfile.NamedTemporaryFile("w", suffix=".yml", delete=False) as f:
            f.write(content)
            temp_path = f.name

        try:
            with patch("sys.stderr", new=io.StringIO()) as mock_stderr:
                entries, skipped = parse_manifest(temp_path)
                self.assertEqual(len(entries), 1)
                self.assertEqual(skipped, 2)
                self.assertEqual(entries[0].selection_id, "doc-valid")
                self.assertIn("[WARN]", mock_stderr.getvalue())
        finally:
            Path(temp_path).unlink()

    def test_parse_manifest_non_list_root(self):
        content = """
items:
  - selection_id: doc-001
    url: https://example.com/doc1.pdf
"""
        with tempfile.NamedTemporaryFile("w", suffix=".yml", delete=False) as f:
            f.write(content)
            temp_path = f.name

        try:
            with self.assertRaises(ValueError) as ctx:
                parse_manifest(temp_path)
            self.assertIn("root element must be a sequence", str(ctx.exception))
        finally:
            Path(temp_path).unlink()

    def test_parse_manifest_file_not_found(self):
        with self.assertRaises(FileNotFoundError):
            parse_manifest("non_existent_file_xyz.yml")


class TestCLIArgs(unittest.TestCase):
    """Tests for argparse configuration."""

    def test_parse_args_defaults_no_args(self):
        args = parse_args([])
        self.assertEqual(args.manifest_path, "manifest.yml")
        self.assertEqual(args.corpus_dir, "corpus")
        self.assertEqual(args.delay, 1.0)
        self.assertEqual(args.max_retries, 3)

    def test_parse_args_positional(self):
        args = parse_args(["custom_manifest.yml"])
        self.assertEqual(args.manifest_path, "custom_manifest.yml")

    def test_parse_args_flag_override(self):
        args = parse_args(["--manifest", "flag_manifest.yml"])
        self.assertEqual(args.manifest_path, "flag_manifest.yml")

    def test_parse_args_custom_values(self):
        args = parse_args(["my_manifest.yml", "--corpus-dir", "custom_corpus", "--delay", "0.5", "--max-retries", "5"])
        self.assertEqual(args.manifest_path, "my_manifest.yml")
        self.assertEqual(args.corpus_dir, "custom_corpus")
        self.assertEqual(args.delay, 0.5)
        self.assertEqual(args.max_retries, 5)


class TestGitIgnore(unittest.TestCase):
    """Tests for ensure_git_ignored."""

    def test_ensure_git_ignored_creates_new(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            gitignore = Path(tmp_dir) / ".gitignore"
            ensure_git_ignored("corpus", gitignore_path=gitignore)
            self.assertTrue(gitignore.is_file())
            content = gitignore.read_text(encoding="utf-8")
            self.assertIn("corpus/*\n", content)
            self.assertIn("!corpus/.gitkeep\n", content)

    def test_ensure_git_ignored_appends_without_duplication(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            gitignore = Path(tmp_dir) / ".gitignore"
            gitignore.write_text("node_modules/\n", encoding="utf-8")

            ensure_git_ignored("corpus", gitignore_path=gitignore)
            content = gitignore.read_text(encoding="utf-8")
            self.assertEqual(content, "node_modules/\ncorpus/*\n!corpus/.gitkeep\n")

            # Calling again should not duplicate
            ensure_git_ignored("corpus", gitignore_path=gitignore)
            content_second = gitignore.read_text(encoding="utf-8")
            self.assertEqual(content_second, "node_modules/\ncorpus/*\n!corpus/.gitkeep\n")


class TestPipelineAndResilience(unittest.TestCase):
    """Tests for download pipeline, sequential pause, exponential backoff, and idempotent overwrite."""

    @patch("urllib.request.urlopen")
    @patch("time.sleep")
    def test_download_success_and_polite_delay(self, mock_sleep, mock_urlopen):
        def fake_urlopen(req, timeout=30.0):
            mock_resp = MagicMock()
            bio = io.BytesIO(b"%PDF-1.4 dummy binary content")
            mock_resp.read = bio.read
            mock_resp.__enter__.return_value = mock_resp
            return mock_resp

        mock_urlopen.side_effect = fake_urlopen

        with tempfile.TemporaryDirectory() as tmp_dir:
            corpus_path = Path(tmp_dir) / "test_corpus"
            manifest = Path(tmp_dir) / "manifest.yml"
            manifest.write_text(
                "- selection_id: doc-1\n  url: https://example.com/1.pdf\n"
                "- selection_id: doc-2\n  url: https://example.com/2.pdf\n",
                encoding="utf-8",
            )

            out_buffer = io.StringIO()
            with patch("sys.stdout", out_buffer):
                code = run_pipeline(str(manifest), corpus_dir=str(corpus_path), delay=0.5, max_retries=2)

            self.assertEqual(code, 0)
            self.assertTrue((corpus_path / "doc-1.pdf").is_file())
            self.assertTrue((corpus_path / "doc-2.pdf").is_file())
            # Delay between doc-1 and doc-2
            mock_sleep.assert_called_with(0.5)

            out_text = out_buffer.getvalue()
            self.assertIn("Total items:        2", out_text)
            self.assertIn("Downloaded/Updated: 2", out_text)
            self.assertIn("Failed downloads:   0", out_text)

    @patch("urllib.request.urlopen")
    def test_idempotent_overwrite(self, mock_urlopen):
        # Existing file has old content
        with tempfile.TemporaryDirectory() as tmp_dir:
            corpus_path = Path(tmp_dir) / "test_corpus"
            corpus_path.mkdir()
            target_file = corpus_path / "doc-replace.pdf"
            target_file.write_text("old corrupted content", encoding="utf-8")

            # Mock new content
            new_content = b"%PDF-new-version"
            mock_response = MagicMock()
            mock_response.read.side_effect = [new_content, b""]
            mock_response.__enter__.return_value = mock_response
            mock_urlopen.return_value = mock_response

            manifest = Path(tmp_dir) / "manifest.yml"
            manifest.write_text("- selection_id: doc-replace\n  url: https://example.com/r.pdf\n", encoding="utf-8")

            with patch("sys.stdout", new=io.StringIO()):
                code = run_pipeline(str(manifest), corpus_dir=str(corpus_path), delay=0.0)

            self.assertEqual(code, 0)
            self.assertEqual(target_file.read_bytes(), new_content)

    @patch("urllib.request.urlopen")
    @patch("time.sleep")
    def test_exponential_backoff_retry_recovery(self, mock_sleep, mock_urlopen):
        # First call fails with 429, second succeeds
        err_429 = urllib.error.HTTPError(
            url="https://example.com/retry.pdf",
            code=429,
            msg="Too Many Requests",
            hdrs={},
            fp=None,
        )

        mock_ok = MagicMock()
        mock_ok.read.side_effect = [b"%PDF-recovered", b""]
        mock_ok.__enter__.return_value = mock_ok

        mock_urlopen.side_effect = [err_429, mock_ok]

        with tempfile.TemporaryDirectory() as tmp_dir:
            corpus_path = Path(tmp_dir) / "test_corpus"
            manifest = Path(tmp_dir) / "manifest.yml"
            manifest.write_text("- selection_id: doc-retry\n  url: https://example.com/retry.pdf\n", encoding="utf-8")

            with patch("sys.stdout", new=io.StringIO()), patch("sys.stderr", new=io.StringIO()) as mock_err:
                code = run_pipeline(str(manifest), corpus_dir=str(corpus_path), delay=1.0, max_retries=3)

            self.assertEqual(code, 0)
            self.assertTrue((corpus_path / "doc-retry.pdf").is_file())
            self.assertIn("Retrying in 1.0s", mock_err.getvalue())
            mock_sleep.assert_called_with(1.0)

    @patch("urllib.request.urlopen")
    @patch("time.sleep")
    def test_permanent_error_exhausts_retries(self, mock_sleep, mock_urlopen):
        err_500 = urllib.error.HTTPError(
            url="https://example.com/error.pdf",
            code=500,
            msg="Internal Server Error",
            hdrs={},
            fp=None,
        )
        mock_urlopen.side_effect = err_500

        with tempfile.TemporaryDirectory() as tmp_dir:
            corpus_path = Path(tmp_dir) / "test_corpus"
            manifest = Path(tmp_dir) / "manifest.yml"
            manifest.write_text("- selection_id: doc-fail\n  url: https://example.com/error.pdf\n", encoding="utf-8")

            out_buf = io.StringIO()
            err_buf = io.StringIO()
            with patch("sys.stdout", out_buf), patch("sys.stderr", err_buf):
                code = run_pipeline(str(manifest), corpus_dir=str(corpus_path), delay=1.0, max_retries=2)

            self.assertEqual(code, 0)
            self.assertFalse((corpus_path / "doc-fail.pdf").exists())
            self.assertIn("[ERROR] Failed to download 'doc-fail'", err_buf.getvalue())
            self.assertIn("Failed downloads:   1", out_buf.getvalue())
            # Retried attempt 0 (wait 1.0s) and attempt 1 (wait 2.0s)
            mock_sleep.assert_has_calls([call(1.0), call(2.0)])


if __name__ == "__main__":
    unittest.main()
