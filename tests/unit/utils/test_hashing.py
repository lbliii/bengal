"""
Tests for bengal.utils.hashing module.

Verifies hashing utilities for file fingerprinting, cache keys, and
content-addressable storage.
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from bengal.utils.hashing import (
    hash_bytes,
    hash_dict,
    hash_file,
    hash_file_with_stat,
    hash_str,
)


class TestHashStr:
    """Tests for hash_str function."""

    def test_basic_hashing(self) -> None:
        """Test basic string hashing produces consistent output."""
        result = hash_str("hello")
        # SHA256 of "hello"
        assert result == "2cf24dba5fb0a30e26e83b2ac5b9e29e1b161e5c1fa7425e73043362938b9824"

    def test_deterministic(self) -> None:
        """Test same input produces same hash."""
        assert hash_str("test") == hash_str("test")

    def test_different_inputs_different_hashes(self) -> None:
        """Test different inputs produce different hashes."""
        assert hash_str("hello") != hash_str("world")

    def test_truncation(self) -> None:
        """Test hash truncation."""
        full_hash = hash_str("hello")
        truncated = hash_str("hello", truncate=16)
        assert truncated == full_hash[:16]
        assert len(truncated) == 16

    def test_md5_algorithm(self) -> None:
        """Test MD5 algorithm option."""
        result = hash_str("hello", algorithm="md5")
        # MD5 of "hello"
        assert result == "5d41402abc4b2a76b9719d911017c592"

    def test_empty_string(self) -> None:
        """Test hashing empty string."""
        result = hash_str("")
        assert len(result) == 64  # SHA256 produces 64 hex chars


class TestHashBytes:
    """Tests for hash_bytes function."""

    def test_basic_hashing(self) -> None:
        """Test basic bytes hashing."""
        result = hash_bytes(b"hello")
        assert result == hash_str("hello")

    def test_truncation(self) -> None:
        """Test hash truncation."""
        truncated = hash_bytes(b"hello", truncate=8)
        assert len(truncated) == 8

    def test_binary_data(self) -> None:
        """Test hashing binary data."""
        binary_data = bytes([0, 1, 2, 255, 254, 253])
        result = hash_bytes(binary_data)
        assert len(result) == 64


class TestHashDict:
    """Tests for hash_dict function."""

    def test_basic_hashing(self) -> None:
        """Test basic dict hashing."""
        result = hash_dict({"key": "value"})
        assert len(result) == 16  # Default truncation

    def test_deterministic_key_order(self) -> None:
        """Test that key order doesn't affect hash (deterministic)."""
        hash1 = hash_dict({"b": 2, "a": 1})
        hash2 = hash_dict({"a": 1, "b": 2})
        assert hash1 == hash2

    def test_different_dicts_different_hashes(self) -> None:
        """Test different dicts produce different hashes."""
        hash1 = hash_dict({"a": 1})
        hash2 = hash_dict({"a": 2})
        assert hash1 != hash2

    def test_nested_dict(self) -> None:
        """Test hashing nested dictionaries."""
        result = hash_dict({"outer": {"inner": "value"}})
        assert len(result) == 16

    def test_list_values(self) -> None:
        """Test hashing dicts with list values."""
        result = hash_dict({"items": [1, 2, 3]})
        assert len(result) == 16

    def test_custom_truncation(self) -> None:
        """Test custom truncation length."""
        result = hash_dict({"key": "value"}, truncate=32)
        assert len(result) == 32

    def test_no_truncation(self) -> None:
        """Test no truncation."""
        result = hash_dict({"key": "value"}, truncate=None)
        assert len(result) == 64

    def test_non_json_types(self) -> None:
        """Test handling of non-JSON types via default=str."""
        from datetime import datetime

        result = hash_dict({"date": datetime(2025, 1, 1)})
        assert len(result) == 16


class TestHashFile:
    """Tests for hash_file function."""

    def test_basic_file_hashing(self, tmp_path: Path) -> None:
        """Test basic file hashing."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("hello")

        result = hash_file(test_file)
        assert result == hash_str("hello")

    def test_truncation(self, tmp_path: Path) -> None:
        """Test file hash truncation."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("hello")

        result = hash_file(test_file, truncate=8)
        assert len(result) == 8

    def test_large_file_streaming(self, tmp_path: Path) -> None:
        """Test large file is hashed via streaming."""
        test_file = tmp_path / "large.txt"
        # Create file larger than chunk size (8192)
        content = "x" * 10000
        test_file.write_text(content)

        result = hash_file(test_file)
        assert result == hash_str(content)

    def test_binary_file(self, tmp_path: Path) -> None:
        """Test hashing binary files."""
        test_file = tmp_path / "binary.bin"
        binary_data = bytes([0, 1, 2, 255, 254, 253])
        test_file.write_bytes(binary_data)

        result = hash_file(test_file)
        assert result == hash_bytes(binary_data)

    def test_file_not_found(self, tmp_path: Path) -> None:
        """Test FileNotFoundError for missing files."""
        with pytest.raises(FileNotFoundError):
            hash_file(tmp_path / "nonexistent.txt")


class TestHashFileWithStat:
    """Tests for hash_file_with_stat function."""

    def test_basic_fingerprinting(self, tmp_path: Path) -> None:
        """Test basic file fingerprinting."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("hello")

        result = hash_file_with_stat(test_file)
        assert len(result) == 8  # Default truncation

    def test_changes_with_mtime(self, tmp_path: Path) -> None:
        """Test fingerprint changes when mtime changes."""
        import os
        import time

        test_file = tmp_path / "test.txt"
        test_file.write_text("hello")

        hash1 = hash_file_with_stat(test_file)

        # Change mtime
        time.sleep(0.1)
        os.utime(test_file, None)

        hash2 = hash_file_with_stat(test_file)

        # Hash should change even though content is same
        assert hash1 != hash2

    def test_deterministic_same_stat(self, tmp_path: Path) -> None:
        """Test fingerprint is deterministic for same file state."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("hello")

        hash1 = hash_file_with_stat(test_file)
        hash2 = hash_file_with_stat(test_file)

        assert hash1 == hash2


class TestEdgeCases:
    """Edge case tests for hashing utilities."""

    def test_unicode_content(self) -> None:
        """Test hashing unicode content."""
        result = hash_str("こんにちは")  # Japanese "hello"
        assert len(result) == 64

    def test_emoji_content(self) -> None:
        """Test hashing emoji content."""
        result = hash_str("Hello 👋 World 🌍")
        assert len(result) == 64

    def test_newlines(self) -> None:
        """Test different newline styles produce different hashes."""
        unix = hash_str("line1\nline2")
        windows = hash_str("line1\r\nline2")
        assert unix != windows

    def test_whitespace(self) -> None:
        """Test whitespace affects hash."""
        with_space = hash_str("hello ")
        without_space = hash_str("hello")
        assert with_space != without_space



