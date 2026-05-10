"""Tests for sharded page artifact persistence."""

from __future__ import annotations

from bengal.cache.page_artifact_store import PageArtifactStore


def test_page_artifact_store_round_trips_records(tmp_path):
    """Records are persisted across deterministic shard files."""
    store = PageArtifactStore(tmp_path / "page-artifacts")
    records = {
        "content/a.md": {"uri": "/a/"},
        "content/b.md": {"uri": "/b/"},
    }

    store.save(records)

    assert store.load() == records


def test_page_artifact_store_prunes_stale_shards(tmp_path):
    """Saving a smaller record set removes shards no longer in use."""
    store = PageArtifactStore(tmp_path / "page-artifacts")
    store.save({"content/a.md": {"uri": "/a/"}})
    assert list((tmp_path / "page-artifacts").glob("*.json"))

    store.save({})

    assert list((tmp_path / "page-artifacts").glob("*.json")) == []
