"""
Tests for ContentHashRegistry.

RFC: Output Cache Architecture - Tests central registry for content hashes
with versioning and corruption recovery.
"""

from __future__ import annotations

import json
from pathlib import Path

from bengal.cache.content_hash_registry import (
    REGISTRY_FORMAT_VERSION,
    ContentHashRegistry,
)


class TestContentHashRegistry:
    """Tests for ContentHashRegistry class."""

    def test_update_source_stores_hash(self, tmp_path: Path) -> None:
        """update_source stores hash for source file."""
        registry = ContentHashRegistry()

        registry.update_source(Path("content/post.md"), "abc123")

        assert registry.get_source_hash(Path("content/post.md")) == "abc123"

    def test_update_output_stores_hash_and_type(self, tmp_path: Path) -> None:
        """update_output stores hash and output type."""
        registry = ContentHashRegistry()

        registry.update_output(Path("public/index.html"), "def456", "CONTENT_PAGE")

        assert registry.get_output_hash(Path("public/index.html")) == "def456"
        assert registry.output_types["public/index.html"] == "CONTENT_PAGE"

    def test_update_generated_deps(self, tmp_path: Path) -> None:
        """update_generated_deps tracks dependencies."""
        registry = ContentHashRegistry()

        registry.update_source(Path("a.md"), "hash1")
        registry.update_source(Path("b.md"), "hash2")
        registry.update_generated_deps(
            Path("tags/python/index.html"),
            [Path("a.md"), Path("b.md")],
        )

        deps = registry.get_member_hashes(Path("tags/python/index.html"))

        assert deps["a.md"] == "hash1"
        assert deps["b.md"] == "hash2"

    def test_compute_generated_hash_deterministic(self, tmp_path: Path) -> None:
        """Generated hash is deterministic."""
        registry = ContentHashRegistry()

        registry.update_source(Path("a.md"), "hash1")
        registry.update_source(Path("b.md"), "hash2")
        registry.update_generated_deps(
            Path("tags/python/index.html"),
            [Path("a.md"), Path("b.md")],
        )

        hash1 = registry.compute_generated_hash(Path("tags/python/index.html"))
        hash2 = registry.compute_generated_hash(Path("tags/python/index.html"))

        assert hash1 == hash2

    def test_has_changed_true_for_new(self, tmp_path: Path) -> None:
        """has_changed returns True for unregistered output."""
        registry = ContentHashRegistry()

        result = registry.has_changed(Path("new.html"), "abc123")

        assert result is True

    def test_has_changed_false_for_same(self, tmp_path: Path) -> None:
        """has_changed returns False for same hash."""
        registry = ContentHashRegistry()

        registry.update_output(Path("index.html"), "abc123", "CONTENT_PAGE")

        result = registry.has_changed(Path("index.html"), "abc123")

        assert result is False

    def test_has_changed_true_for_different(self, tmp_path: Path) -> None:
        """has_changed returns True for different hash."""
        registry = ContentHashRegistry()

        registry.update_output(Path("index.html"), "abc123", "CONTENT_PAGE")

        result = registry.has_changed(Path("index.html"), "def456")

        assert result is True

    def test_clear_removes_all_data(self, tmp_path: Path) -> None:
        """clear removes all registry data."""
        registry = ContentHashRegistry()

        registry.update_source(Path("a.md"), "hash1")
        registry.update_output(Path("a.html"), "hash2", "CONTENT_PAGE")

        registry.clear()

        assert len(registry.source_hashes) == 0
        assert len(registry.output_hashes) == 0

    def test_get_stats(self, tmp_path: Path) -> None:
        """get_stats returns useful statistics."""
        registry = ContentHashRegistry()

        registry.update_source(Path("a.md"), "hash1")
        registry.update_source(Path("b.md"), "hash2")
        registry.update_output(Path("a.html"), "hash3", "CONTENT_PAGE")
        registry.update_output(Path("b.html"), "hash4", "GENERATED_PAGE")

        stats = registry.get_stats()

        assert stats["source_count"] == 2
        assert stats["output_count"] == 2
        assert stats["output_types"]["CONTENT_PAGE"] == 1
        assert stats["output_types"]["GENERATED_PAGE"] == 1


class TestContentHashRegistryPersistence:
    """Tests for registry persistence."""

    def test_load_returns_empty_for_missing(self, tmp_path: Path) -> None:
        """load returns empty registry for missing file."""
        registry = ContentHashRegistry.load(tmp_path / "nonexistent.json")

        assert len(registry.source_hashes) == 0
        assert len(registry.output_hashes) == 0

    def test_load_handles_corrupted_json(self, tmp_path: Path) -> None:
        """load returns empty registry for corrupted JSON."""
        path = tmp_path / "corrupted.json"
        path.write_text("{ invalid json }")

        registry = ContentHashRegistry.load(path)

        # Should not raise, returns empty
        assert len(registry.source_hashes) == 0

    def test_load_handles_version_mismatch(self, tmp_path: Path) -> None:
        """load returns empty registry for old version."""
        path = tmp_path / "old_version.json"
        path.write_text(
            json.dumps(
                {
                    "version": 0,  # Old version
                    "source_hashes": {"a.md": "hash1"},
                }
            )
        )

        registry = ContentHashRegistry.load(path)

        # Should start fresh
        assert len(registry.source_hashes) == 0


class TestContentHashRegistryValidation:
    """Tests for registry validation."""

    def test_validate_missing_file(self, tmp_path: Path) -> None:
        """validate returns True for missing file."""
        is_valid, message = ContentHashRegistry.validate(tmp_path / "missing.json")

        assert is_valid is True
        assert "will be created" in message

    def test_validate_corrupted_file(self, tmp_path: Path) -> None:
        """validate returns False for corrupted file."""
        path = tmp_path / "corrupted.json"
        path.write_text("{ invalid json }")

        is_valid, message = ContentHashRegistry.validate(path)

        assert is_valid is False
        assert "JSON parse error" in message

    def test_validate_version_mismatch(self, tmp_path: Path) -> None:
        """validate returns False for version mismatch."""
        path = tmp_path / "old.json"
        path.write_text(
            json.dumps(
                {
                    "version": 999,  # Future version
                    "source_hashes": {},
                    "output_hashes": {},
                }
            )
        )

        is_valid, message = ContentHashRegistry.validate(path)

        assert is_valid is False
        assert "Version mismatch" in message

    def test_validate_missing_required_fields(self, tmp_path: Path) -> None:
        """validate returns False for missing required fields."""
        path = tmp_path / "incomplete.json"
        path.write_text(
            json.dumps(
                {
                    "version": REGISTRY_FORMAT_VERSION,
                    # Missing source_hashes and output_hashes
                }
            )
        )

        is_valid, message = ContentHashRegistry.validate(path)

        assert is_valid is False
        assert "Missing fields" in message

    def test_validate_valid_file(self, tmp_path: Path) -> None:
        """validate returns True for valid file."""
        path = tmp_path / "valid.json"
        path.write_text(
            json.dumps(
                {
                    "version": REGISTRY_FORMAT_VERSION,
                    "source_hashes": {"a.md": "hash1"},
                    "output_hashes": {"a.html": "hash2"},
                }
            )
        )

        is_valid, message = ContentHashRegistry.validate(path)

        assert is_valid is True
        assert "Valid" in message
