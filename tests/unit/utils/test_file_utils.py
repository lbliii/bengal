"""
Tests for bengal/utils/file_utils.py.

Covers:
- hash_file function
- SHA256 hashing
- Chunked file reading
- Error handling for non-existent files
"""

from __future__ import annotations

import hashlib
from pathlib import Path

import pytest


class TestHashFileBasics:
    """Test basic hash_file functionality."""

    def test_hashes_file_content(self, tmp_path: Path) -> None:
        """Test that hash_file returns SHA256 hash of content."""
        from bengal.utils.file_utils import hash_file

        test_file = tmp_path / "test.txt"
        content = b"hello world"
        test_file.write_bytes(content)

        result = hash_file(test_file)

        # Compute expected hash
        expected = hashlib.sha256(content).hexdigest()

        assert result == expected

    def test_returns_hexdigest(self, tmp_path: Path) -> None:
        """Test that hash_file returns hexdigest string."""
        from bengal.utils.file_utils import hash_file

        test_file = tmp_path / "test.txt"
        test_file.write_bytes(b"content")

        result = hash_file(test_file)

        # Should be 64-character hex string
        assert len(result) == 64
        assert all(c in "0123456789abcdef" for c in result)


class TestHashFileNonExistent:
    """Test hash_file with non-existent files."""

    def test_raises_file_not_found(self, tmp_path: Path) -> None:
        """Test that non-existent file raises FileNotFoundError."""
        from bengal.utils.file_utils import hash_file

        nonexistent = tmp_path / "nonexistent.txt"

        with pytest.raises(FileNotFoundError, match="File not found"):
            hash_file(nonexistent)


class TestHashFileDeterminism:
    """Test that hash_file is deterministic."""

    def test_same_content_same_hash(self, tmp_path: Path) -> None:
        """Test that same content produces same hash."""
        from bengal.utils.file_utils import hash_file

        file1 = tmp_path / "file1.txt"
        file2 = tmp_path / "file2.txt"

        content = b"identical content"
        file1.write_bytes(content)
        file2.write_bytes(content)

        hash1 = hash_file(file1)
        hash2 = hash_file(file2)

        assert hash1 == hash2

    def test_different_content_different_hash(self, tmp_path: Path) -> None:
        """Test that different content produces different hash."""
        from bengal.utils.file_utils import hash_file

        file1 = tmp_path / "file1.txt"
        file2 = tmp_path / "file2.txt"

        file1.write_bytes(b"content one")
        file2.write_bytes(b"content two")

        hash1 = hash_file(file1)
        hash2 = hash_file(file2)

        assert hash1 != hash2

    def test_multiple_reads_same_hash(self, tmp_path: Path) -> None:
        """Test that multiple reads produce same hash."""
        from bengal.utils.file_utils import hash_file

        test_file = tmp_path / "test.txt"
        test_file.write_bytes(b"test content")

        hash1 = hash_file(test_file)
        hash2 = hash_file(test_file)
        hash3 = hash_file(test_file)

        assert hash1 == hash2 == hash3


class TestHashFileChunkedReading:
    """Test chunked file reading."""

    def test_small_file_hashed_correctly(self, tmp_path: Path) -> None:
        """Test that small files (< chunk size) are hashed correctly."""
        from bengal.utils.file_utils import hash_file

        test_file = tmp_path / "small.txt"
        content = b"small"  # Much smaller than default chunk size
        test_file.write_bytes(content)

        result = hash_file(test_file)
        expected = hashlib.sha256(content).hexdigest()

        assert result == expected

    def test_large_file_hashed_correctly(self, tmp_path: Path) -> None:
        """Test that large files are hashed correctly."""
        from bengal.utils.file_utils import hash_file

        test_file = tmp_path / "large.txt"
        # Create content larger than default chunk size (8192)
        content = b"x" * 50000
        test_file.write_bytes(content)

        result = hash_file(test_file)
        expected = hashlib.sha256(content).hexdigest()

        assert result == expected

    def test_custom_chunk_size(self, tmp_path: Path) -> None:
        """Test with custom chunk size."""
        from bengal.utils.file_utils import hash_file

        test_file = tmp_path / "test.txt"
        content = b"test content"
        test_file.write_bytes(content)

        # Use very small chunk size
        result = hash_file(test_file, chunk_size=1)
        expected = hashlib.sha256(content).hexdigest()

        assert result == expected

    def test_chunk_size_larger_than_file(self, tmp_path: Path) -> None:
        """Test with chunk size larger than file."""
        from bengal.utils.file_utils import hash_file

        test_file = tmp_path / "test.txt"
        content = b"small"
        test_file.write_bytes(content)

        # Use very large chunk size
        result = hash_file(test_file, chunk_size=1000000)
        expected = hashlib.sha256(content).hexdigest()

        assert result == expected


class TestHashFileEdgeCases:
    """Test edge cases for hash_file."""

    def test_empty_file(self, tmp_path: Path) -> None:
        """Test hashing empty file."""
        from bengal.utils.file_utils import hash_file

        test_file = tmp_path / "empty.txt"
        test_file.write_bytes(b"")

        result = hash_file(test_file)
        expected = hashlib.sha256(b"").hexdigest()

        assert result == expected

    def test_binary_file(self, tmp_path: Path) -> None:
        """Test hashing binary file."""
        from bengal.utils.file_utils import hash_file

        test_file = tmp_path / "binary.bin"
        content = bytes(range(256))  # All byte values
        test_file.write_bytes(content)

        result = hash_file(test_file)
        expected = hashlib.sha256(content).hexdigest()

        assert result == expected

    def test_file_with_null_bytes(self, tmp_path: Path) -> None:
        """Test hashing file with null bytes."""
        from bengal.utils.file_utils import hash_file

        test_file = tmp_path / "nulls.bin"
        content = b"\x00\x00\x00hello\x00\x00\x00"
        test_file.write_bytes(content)

        result = hash_file(test_file)
        expected = hashlib.sha256(content).hexdigest()

        assert result == expected


class TestHashFilePath:
    """Test hash_file with different path types."""

    def test_accepts_path_object(self, tmp_path: Path) -> None:
        """Test that Path objects are accepted."""
        from bengal.utils.file_utils import hash_file

        test_file = tmp_path / "test.txt"
        test_file.write_bytes(b"content")

        # Should work with Path object
        result = hash_file(test_file)
        assert isinstance(result, str)

    def test_accepts_pathlib_path(self, tmp_path: Path) -> None:
        """Test with pathlib.Path explicitly."""
        from bengal.utils.file_utils import hash_file

        test_file = Path(tmp_path) / "test.txt"
        test_file.write_bytes(b"content")

        result = hash_file(test_file)
        assert len(result) == 64


class TestHashFileSpecificHashes:
    """Test specific known hash values."""

    def test_known_hash_hello(self, tmp_path: Path) -> None:
        """Test known hash for 'hello'."""
        from bengal.utils.file_utils import hash_file

        test_file = tmp_path / "hello.txt"
        test_file.write_bytes(b"hello")

        result = hash_file(test_file)

        # Known SHA256 hash of "hello"
        expected = "2cf24dba5fb0a30e26e83b2ac5b9e29e1b161e5c1fa7425e73043362938b9824"
        assert result == expected

    def test_known_hash_empty(self, tmp_path: Path) -> None:
        """Test known hash for empty file."""
        from bengal.utils.file_utils import hash_file

        test_file = tmp_path / "empty.txt"
        test_file.write_bytes(b"")

        result = hash_file(test_file)

        # Known SHA256 hash of empty string
        expected = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
        assert result == expected

