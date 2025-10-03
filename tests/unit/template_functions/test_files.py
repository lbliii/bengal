"""Tests for file system template functions."""

import pytest
import tempfile
from pathlib import Path
from bengal.rendering.template_functions.files import (
    read_file,
    file_exists,
    file_size,
)


class TestReadFile:
    """Tests for read_file function."""
    
    def test_read_existing_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = Path(tmpdir) / "test.txt"
            content = "Hello, World!"
            file_path.write_text(content)
            
            result = read_file("test.txt", Path(tmpdir))
            assert result == content
    
    def test_read_nonexistent_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            result = read_file("missing.txt", Path(tmpdir))
            assert result == ""
    
    def test_empty_path(self):
        result = read_file("", Path("/tmp"))
        assert result == ""


class TestFileExists:
    """Tests for file_exists function."""
    
    def test_existing_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = Path(tmpdir) / "test.txt"
            file_path.write_text("content")
            
            result = file_exists("test.txt", Path(tmpdir))
            assert result is True
    
    def test_nonexistent_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            result = file_exists("missing.txt", Path(tmpdir))
            assert result is False
    
    def test_directory_not_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            subdir = Path(tmpdir) / "subdir"
            subdir.mkdir()
            
            result = file_exists("subdir", Path(tmpdir))
            assert result is False  # It's a directory, not a file
    
    def test_empty_path(self):
        result = file_exists("", Path("/tmp"))
        assert result is False


class TestFileSize:
    """Tests for file_size function."""
    
    def test_small_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = Path(tmpdir) / "small.txt"
            file_path.write_text("Hello")
            
            result = file_size("small.txt", Path(tmpdir))
            assert "B" in result
    
    def test_larger_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = Path(tmpdir) / "large.txt"
            file_path.write_text("X" * 2048)  # 2 KB
            
            result = file_size("large.txt", Path(tmpdir))
            assert "KB" in result
    
    def test_nonexistent_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            result = file_size("missing.txt", Path(tmpdir))
            assert result == "0 B"
    
    def test_empty_path(self):
        result = file_size("", Path("/tmp"))
        assert result == "0 B"

