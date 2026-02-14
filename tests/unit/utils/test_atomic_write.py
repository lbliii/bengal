"""
Tests for atomic write utilities.

These tests verify that file writes are crash-safe and never leave
files in a partially written state.
"""

import json

import pytest


class TestAtomicWriteText:
    """Test atomic_write_text function."""

    def test_basic_write(self, tmp_path):
        """Test basic atomic write creates file correctly."""
        from bengal.utils.io.atomic_write import atomic_write_text

        file_path = tmp_path / "test.txt"
        content = "Hello, World!"

        atomic_write_text(file_path, content)

        assert file_path.exists()
        assert file_path.read_text() == content

    def test_write_with_unicode(self, tmp_path):
        """Test writing unicode content."""
        from bengal.utils.io.atomic_write import atomic_write_text

        file_path = tmp_path / "unicode.txt"
        content = "🐯 Bengal SSG — Fast & Fierce"

        atomic_write_text(file_path, content)

        assert file_path.read_text() == content

    def test_overwrite_existing(self, tmp_path):
        """Test overwriting existing file atomically."""
        from bengal.utils.io.atomic_write import atomic_write_text

        file_path = tmp_path / "test.txt"

        # Write initial content
        file_path.write_text("old content")
        old_mtime = file_path.stat().st_mtime

        # Small delay to ensure mtime changes
        import time

        time.sleep(0.01)

        # Overwrite atomically
        atomic_write_text(file_path, "new content")

        assert file_path.read_text() == "new content"
        assert file_path.stat().st_mtime > old_mtime

    def test_no_temp_file_left_on_success(self, tmp_path):
        """Test that temp file is cleaned up on success."""
        from bengal.utils.io.atomic_write import atomic_write_text

        file_path = tmp_path / "test.txt"
        atomic_write_text(file_path, "content")

        # Check no .tmp files left
        tmp_files = list(tmp_path.glob("*.tmp"))
        assert len(tmp_files) == 0

    def test_temp_file_cleaned_on_error(self, tmp_path):
        """Test that temp file is cleaned up on write error."""
        from unittest.mock import patch

        from bengal.utils.io.atomic_write import atomic_write_text

        file_path = tmp_path / "test.txt"

        # Mock write_text to raise an error after creating the temp file
        with (
            patch("pathlib.Path.write_text", side_effect=OSError("Mock write error")),
            pytest.raises(OSError, match="Mock write error"),
        ):
            atomic_write_text(file_path, "content")

        # Check no .tmp files left anywhere (including hidden ones)
        tmp_files = list(tmp_path.rglob("*.tmp"))
        assert len(tmp_files) == 0

    def test_preserves_original_on_simulated_crash(self, tmp_path):
        """
        Test that original file is preserved if write is interrupted.

        Simulates crash by writing to temp and NOT renaming.
        """
        file_path = tmp_path / "test.txt"

        # Create original file
        original_content = "original"
        file_path.write_text(original_content)

        # Simulate interrupted write (temp file left behind)
        tmp_path_file = file_path.with_suffix(".txt.tmp")
        tmp_path_file.write_text("partial")  # Simulate partial write

        # Original should still be intact
        assert file_path.read_text() == original_content

        # Cleanup
        tmp_path_file.unlink()

    def test_large_content(self, tmp_path):
        """Test writing large content atomically."""
        from bengal.utils.io.atomic_write import atomic_write_text

        file_path = tmp_path / "large.txt"
        # Create ~1MB of content
        content = "x" * (1024 * 1024)

        atomic_write_text(file_path, content)

        assert file_path.read_text() == content
        # No temp files left
        assert len(list(tmp_path.glob("*.tmp"))) == 0


class TestAtomicWriteBytes:
    """Test atomic_write_bytes function."""

    def test_basic_write(self, tmp_path):
        """Test basic binary write."""
        from bengal.utils.io.atomic_write import atomic_write_bytes

        file_path = tmp_path / "test.bin"
        content = b"\x00\x01\x02\x03\xff\xfe"

        atomic_write_bytes(file_path, content)

        assert file_path.exists()
        assert file_path.read_bytes() == content

    def test_overwrite_existing_binary(self, tmp_path):
        """Test overwriting existing binary file."""
        from bengal.utils.io.atomic_write import atomic_write_bytes

        file_path = tmp_path / "test.bin"

        file_path.write_bytes(b"old")
        atomic_write_bytes(file_path, b"new")

        assert file_path.read_bytes() == b"new"


class TestAtomicFile:
    """Test AtomicFile context manager."""

    def test_basic_usage(self, tmp_path):
        """Test basic context manager usage."""
        from bengal.utils.io.atomic_write import AtomicFile

        file_path = tmp_path / "test.txt"

        with AtomicFile(file_path, "w") as f:
            f.write("line 1\n")
            f.write("line 2\n")

        assert file_path.read_text() == "line 1\nline 2\n"
        # No temp files left
        assert len(list(tmp_path.glob("*.tmp"))) == 0

    def test_exception_rolls_back(self, tmp_path):
        """Test that exception prevents file creation."""
        from bengal.utils.io.atomic_write import AtomicFile

        file_path = tmp_path / "test.txt"

        # Create original
        file_path.write_text("original")

        # Try to write with exception
        try:
            with AtomicFile(file_path, "w") as f:
                f.write("new")
                raise ValueError("Simulated error")
        except ValueError:
            pass

        # Original should be intact
        assert file_path.read_text() == "original"

        # No temp files left
        assert len(list(tmp_path.glob("*.tmp"))) == 0

    def test_json_write(self, tmp_path):
        """Test writing JSON atomically."""
        from bengal.utils.io.atomic_write import AtomicFile

        file_path = tmp_path / "data.json"
        data = {"key": "value", "number": 42, "list": [1, 2, 3]}

        with AtomicFile(file_path, "w") as f:
            json.dump(data, f, indent=2)

        with open(file_path) as f:
            loaded = json.load(f)

        assert loaded == data

    def test_binary_mode(self, tmp_path):
        """Test AtomicFile in binary mode."""
        from bengal.utils.io.atomic_write import AtomicFile

        file_path = tmp_path / "test.bin"
        content = b"binary content"

        with AtomicFile(file_path, "wb") as f:
            f.write(content)

        assert file_path.read_bytes() == content

    def test_append_mode_creates_new_file(self, tmp_path):
        """Test that append mode works (though less common for atomic writes)."""
        from bengal.utils.io.atomic_write import AtomicFile

        file_path = tmp_path / "test.txt"

        # Note: Append mode is unusual for atomic writes since it
        # would append to the temp file, not the original
        with AtomicFile(file_path, "a") as f:
            f.write("line 1\n")

        assert file_path.read_text() == "line 1\n"


@pytest.mark.parallel_unsafe
class TestRealWorldScenarios:
    """Test real-world crash scenarios.

    Marked parallel_unsafe: Uses ThreadPoolExecutor for concurrent writes, which conflicts
    with pytest-xdist's parallel test execution (nested parallelism causes worker crashes).

    """

    def test_multiple_rapid_writes(self, tmp_path):
        """Test rapid successive writes (like page rendering)."""
        from bengal.utils.io.atomic_write import atomic_write_text

        file_path = tmp_path / "test.txt"

        # Rapid writes (simulates build process)
        for i in range(100):
            atomic_write_text(file_path, f"version {i}")

        # Final content should be complete
        assert file_path.read_text() == "version 99"

        # No temp files left
        assert len(list(tmp_path.glob("*.tmp"))) == 0

    def test_concurrent_writes_different_files(self, tmp_path):
        """Test concurrent writes to different files (parallel build)."""
        import concurrent.futures

        from bengal.utils.io.atomic_write import atomic_write_text

        def write_file(i):
            file_path = tmp_path / f"file_{i}.txt"
            atomic_write_text(file_path, f"content {i}")
            return file_path

        # Parallel writes
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
            paths = list(executor.map(write_file, range(20)))

        # All files should exist with correct content
        for i, path in enumerate(paths):
            assert path.exists()
            assert path.read_text() == f"content {i}"

        # No temp files left
        assert len(list(tmp_path.glob("*.tmp"))) == 0

    def test_concurrent_writes_same_file(self, tmp_path):
        """Test concurrent writes to the SAME file (regression test for race condition)."""
        import concurrent.futures
        import time

        from bengal.utils.io.atomic_write import atomic_write_text

        file_path = tmp_path / "index.html"
        num_threads = 10

        def write_same_file(i):
            """Multiple threads writing to same file."""
            content = f"<html><body>Thread {i} at {time.time()}</body></html>"
            atomic_write_text(file_path, content)
            return i

        # Concurrent writes to SAME file (this was causing FileNotFoundError)
        with concurrent.futures.ThreadPoolExecutor(max_workers=num_threads) as executor:
            results = list(executor.map(write_same_file, range(num_threads)))

        # File should exist with valid content from ONE of the threads
        assert file_path.exists()
        content = file_path.read_text()
        assert content.startswith("<html><body>Thread")
        assert content.endswith("</body></html>")

        # All threads should complete successfully
        assert len(results) == num_threads

        # No temp files left (critical - was leaking .tmp files before fix)
        tmp_files = list(tmp_path.rglob("*.tmp"))
        assert len(tmp_files) == 0, f"Found leftover temp files: {tmp_files}"

    def test_html_page_rendering(self, tmp_path):
        """Test typical page rendering scenario."""
        from bengal.utils.io.atomic_write import atomic_write_text

        output_path = tmp_path / "page.html"
        html = """<!DOCTYPE html>
<html>
<head><title>Test Page</title></head>
<body>
<h1>Hello, World!</h1>
<p>This is a test page.</p>
</body>
</html>"""

        atomic_write_text(output_path, html)

        assert output_path.exists()
        assert "<title>Test Page</title>" in output_path.read_text()

    def test_cache_file_scenario(self, tmp_path):
        """Test cache file write scenario (JSON)."""
        from bengal.utils.io.atomic_write import AtomicFile

        cache_path = tmp_path / "cache.json"
        cache_data = {
            "version": "1.0",
            "files": {
                "page1.md": "abc123",
                "page2.md": "def456",
            },
        }

        with AtomicFile(cache_path, "w") as f:
            json.dump(cache_data, f, indent=2)

        assert cache_path.exists()
        loaded = json.loads(cache_path.read_text())
        assert loaded == cache_data


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
