"""
Tests for RebuildManifest.

RFC: rfc-cache-invalidation-architecture
Tests rebuild tracking and observability.
"""

from __future__ import annotations

import json
from pathlib import Path

from bengal.cache.manifest import RebuildEntry, RebuildManifest


class TestRebuildEntry:
    """Tests for RebuildEntry dataclass."""

    def test_entry_creation(self):
        """Can create an entry with required fields."""
        entry = RebuildEntry(
            page_path="content/about.md",
            reason="CONTENT_CHANGED",
            trigger="file_modified",
        )

        assert entry.page_path == "content/about.md"
        assert entry.reason == "CONTENT_CHANGED"
        assert entry.trigger == "file_modified"
        assert entry.duration_ms == 0.0
        assert entry.from_cache is False

    def test_entry_with_duration(self):
        """Can create an entry with duration."""
        entry = RebuildEntry(
            page_path="content/about.md",
            reason="CONTENT_CHANGED",
            trigger="file_modified",
            duration_ms=45.2,
        )

        assert entry.duration_ms == 45.2

    def test_entry_from_cache(self):
        """Can create a cache hit entry."""
        entry = RebuildEntry(
            page_path="content/about.md",
            reason="cache_hit",
            trigger="",
            from_cache=True,
        )

        assert entry.from_cache is True


class TestRebuildManifest:
    """Tests for RebuildManifest class."""

    def test_manifest_creation(self):
        """Can create a manifest with required fields."""
        manifest = RebuildManifest(
            build_id="abc123",
            incremental=True,
        )

        assert manifest.build_id == "abc123"
        assert manifest.incremental is True
        assert manifest.entries == []
        assert manifest.skipped == []
        assert manifest.invalidation_summary == {}

    def test_add_rebuild(self):
        """Can add a rebuild entry."""
        manifest = RebuildManifest(build_id="abc123", incremental=True)

        manifest.add_rebuild(
            page_path=Path("content/about.md"),
            reason="CONTENT_CHANGED",
            trigger="file_modified",
            duration_ms=45.2,
        )

        assert len(manifest.entries) == 1
        assert manifest.entries[0].page_path == "content/about.md"
        assert manifest.entries[0].reason == "CONTENT_CHANGED"
        assert manifest.entries[0].duration_ms == 45.2
        assert manifest.entries[0].from_cache is False

    def test_add_cache_hit(self):
        """Can add a cache hit entry."""
        manifest = RebuildManifest(build_id="abc123", incremental=True)

        manifest.add_cache_hit(
            page_path=Path("content/about.md"),
            duration_ms=0.5,
        )

        assert len(manifest.entries) == 1
        assert manifest.entries[0].from_cache is True
        assert manifest.entries[0].reason == "cache_hit"

    def test_add_skipped(self):
        """Can add a skipped page."""
        manifest = RebuildManifest(build_id="abc123", incremental=True)

        manifest.add_skipped(Path("content/about.md"))

        assert len(manifest.skipped) == 1
        assert manifest.skipped[0] == "content/about.md"

    def test_to_json(self):
        """to_json returns valid JSON."""
        manifest = RebuildManifest(build_id="abc123", incremental=True)
        manifest.add_rebuild(
            page_path=Path("content/about.md"),
            reason="CONTENT_CHANGED",
            trigger="file_modified",
            duration_ms=45.2,
        )
        manifest.add_skipped(Path("content/team.md"))

        result = manifest.to_json()
        data = json.loads(result)

        assert data["build_id"] == "abc123"
        assert data["incremental"] is True
        assert data["rebuilt"] == 1
        assert data["skipped"] == 1
        assert len(data["entries"]) == 1

    def test_to_dict(self):
        """to_dict returns dictionary."""
        manifest = RebuildManifest(build_id="abc123", incremental=True)
        manifest.add_rebuild(
            page_path=Path("content/about.md"),
            reason="CONTENT_CHANGED",
            trigger="file_modified",
        )

        result = manifest.to_dict()

        assert result["build_id"] == "abc123"
        assert result["rebuilt"] == 1
        assert "by_reason" in result

    def test_summary(self):
        """summary returns correct statistics."""
        manifest = RebuildManifest(build_id="abc123", incremental=True)
        manifest.add_rebuild(
            page_path=Path("content/about.md"),
            reason="CONTENT_CHANGED",
            trigger="",
            duration_ms=10.0,
        )
        manifest.add_rebuild(
            page_path=Path("content/team.md"),
            reason="CONTENT_CHANGED",
            trigger="",
            duration_ms=20.0,
        )
        manifest.add_rebuild(
            page_path=Path("content/data.md"),
            reason="DATA_FILE_CHANGED",
            trigger="",
            duration_ms=15.0,
        )
        manifest.add_cache_hit(
            page_path=Path("content/cached.md"),
            duration_ms=0.5,
        )
        manifest.add_skipped(Path("content/skipped.md"))

        summary = manifest.summary()

        assert summary["total_rebuilt"] == 3
        assert summary["total_cache_hits"] == 1
        assert summary["total_skipped"] == 1
        assert summary["by_reason"]["CONTENT_CHANGED"] == 2
        assert summary["by_reason"]["DATA_FILE_CHANGED"] == 1
        assert summary["total_duration_ms"] == 45.5

    def test_merge(self):
        """Can merge two manifests."""
        manifest1 = RebuildManifest(build_id="abc123", incremental=True)
        manifest1.add_rebuild(
            page_path=Path("content/about.md"),
            reason="CONTENT_CHANGED",
            trigger="",
        )
        manifest1.add_skipped(Path("content/skipped1.md"))
        manifest1.invalidation_summary = {"CONTENT_CHANGED": [{"page": "about.md"}]}

        manifest2 = RebuildManifest(build_id="abc123", incremental=True)
        manifest2.add_rebuild(
            page_path=Path("content/team.md"),
            reason="DATA_FILE_CHANGED",
            trigger="",
        )
        manifest2.add_skipped(Path("content/skipped2.md"))
        manifest2.invalidation_summary = {"DATA_FILE_CHANGED": [{"page": "team.md"}]}

        manifest1.merge(manifest2)

        assert len(manifest1.entries) == 2
        assert len(manifest1.skipped) == 2
        assert "CONTENT_CHANGED" in manifest1.invalidation_summary
        assert "DATA_FILE_CHANGED" in manifest1.invalidation_summary

    def test_repr(self):
        """Manifest has useful repr."""
        manifest = RebuildManifest(build_id="abc123", incremental=True)
        manifest.add_rebuild(
            page_path=Path("content/about.md"),
            reason="CONTENT_CHANGED",
            trigger="",
        )
        manifest.add_skipped(Path("content/skipped.md"))

        result = repr(manifest)

        assert "RebuildManifest" in result
        assert "abc123" in result
        assert "rebuilt=1" in result
        assert "skipped=1" in result
