"""Tests for sharded page artifact persistence."""

from __future__ import annotations

import time

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


def test_page_artifact_store_dirty_save_rewrites_only_affected_shard(tmp_path):
    """Dirty saves touch only shards for changed keys."""
    store = PageArtifactStore(tmp_path / "page-artifacts")
    changed_key = "content/a.md"
    stable_key = _key_in_different_shard(store, changed_key)
    records = {
        changed_key: {"uri": "/a/"},
        stable_key: {"uri": "/stable/"},
    }
    store.save(records)
    changed_path = store.root / f"{store._shard_name(changed_key)}.json"
    stable_path = store.root / f"{store._shard_name(stable_key)}.json"
    changed_mtime = changed_path.stat().st_mtime_ns
    stable_mtime = stable_path.stat().st_mtime_ns
    time.sleep(0.01)

    records[changed_key] = {"uri": "/a-updated/"}
    store.save(records, dirty_keys={changed_key}, deleted_keys=set())

    assert changed_path.stat().st_mtime_ns > changed_mtime
    assert stable_path.stat().st_mtime_ns == stable_mtime
    assert store.load()[changed_key]["uri"] == "/a-updated/"


def test_page_artifact_store_dirty_save_deletes_empty_shard(tmp_path):
    """Dirty deletion removes a shard when no records remain in it."""
    store = PageArtifactStore(tmp_path / "page-artifacts")
    records = {"content/a.md": {"uri": "/a/"}}
    store.save(records)
    shard_path = store.root / f"{store._shard_name('content/a.md')}.json"
    assert shard_path.exists()

    store.save({}, dirty_keys=set(), deleted_keys={"content/a.md"})

    assert not shard_path.exists()


def _key_in_different_shard(store: PageArtifactStore, key: str) -> str:
    source_shard = store._shard_name(key)
    for index in range(1000):
        candidate = f"content/stable-{index}.md"
        if store._shard_name(candidate) != source_shard:
            return candidate
    raise AssertionError("could not find test key in different shard")
