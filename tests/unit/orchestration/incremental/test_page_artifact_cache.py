"""Tests for cached post-render page artifacts."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from types import SimpleNamespace

from bengal.cache import BengalPaths
from bengal.cache.build_cache import BuildCache
from bengal.cache.page_artifact_store import PageArtifactStore
from bengal.orchestration.build_context import AccumulatedPageData
from bengal.orchestration.incremental.cache_manager import CacheManager


def test_cache_manager_persists_accumulated_page_artifacts(tmp_path: Path) -> None:
    """Rendered page artifacts are stored under canonical cache keys."""
    source_path = Path("content/docs.md")
    site = SimpleNamespace(
        root_path=tmp_path,
        pages=[SimpleNamespace(source_path=source_path, toc_items=[{"id": "intro"}])],
    )
    manager = CacheManager(site)
    manager.cache = BuildCache(site_root=tmp_path)
    artifact = _artifact(source_path)
    build_context = SimpleNamespace(get_accumulated_page_data=lambda: [artifact])

    manager._store_page_artifacts(build_context)

    cached = manager.cache.page_artifacts["content/docs.md"]
    assert cached["uri"] == "/docs/"
    assert cached["anchors"] == ["intro"]
    assert cached["full_json_data"] == {"url": "/docs/", "title": "Docs"}
    assert cached["json_output_path"] == "public/docs/index.json"


def test_cache_manager_prunes_deleted_page_artifacts(tmp_path: Path) -> None:
    """Artifact cache drops records for pages no longer present in the site."""
    source_path = Path("content/docs.md")
    site = SimpleNamespace(root_path=tmp_path, pages=[SimpleNamespace(source_path=source_path)])
    manager = CacheManager(site)
    manager.cache = BuildCache(site_root=tmp_path)
    manager.cache.page_artifacts = {"content/deleted.md": {"uri": "/deleted/"}}
    build_context = SimpleNamespace(get_accumulated_page_data=lambda: [_artifact(source_path)])

    manager._store_page_artifacts(build_context)

    assert set(manager.cache.page_artifacts) == {"content/docs.md"}
    assert manager._deleted_page_artifact_keys == {"content/deleted.md"}


def test_cache_manager_tracks_dirty_page_artifact_keys(tmp_path: Path) -> None:
    """CacheManager exposes dirty artifact keys for shard-limited persistence."""
    source_path = Path("content/docs.md")
    site = SimpleNamespace(root_path=tmp_path, pages=[SimpleNamespace(source_path=source_path)])
    manager = CacheManager(site)
    manager.cache = BuildCache(site_root=tmp_path)
    manager.cache.page_artifacts = {"content/docs.md": {"uri": "/old/"}}
    build_context = SimpleNamespace(
        get_accumulated_page_data=lambda: [_artifact(source_path)],
        pages_to_build=[SimpleNamespace(source_path=source_path)],
    )

    manager._store_page_artifacts(build_context)

    assert manager._dirty_page_artifact_keys == {"content/docs.md"}


def test_cache_manager_sanitizes_page_artifact_metadata(tmp_path: Path) -> None:
    """Cached page artifacts remain serializable when metadata has Python objects."""
    source_path = Path("content/docs.md")
    site = SimpleNamespace(
        root_path=tmp_path,
        pages=[SimpleNamespace(source_path=source_path, toc_items=[])],
    )
    manager = CacheManager(site)
    manager.cache = BuildCache(site_root=tmp_path)
    artifact = _artifact(source_path)
    artifact.raw_metadata["path"] = tmp_path / "source.md"
    artifact.enhanced_metadata["updated"] = datetime(2026, 5, 3, 12, 0, 0)
    artifact.full_json_data = {"url": "/docs/", "source": tmp_path / "source.md"}
    build_context = SimpleNamespace(get_accumulated_page_data=lambda: [artifact])

    manager._store_page_artifacts(build_context)

    cached = manager.cache.page_artifacts["content/docs.md"]
    assert cached["raw_metadata"]["path"] == str(tmp_path / "source.md")
    assert cached["enhanced_metadata"]["updated"] == "2026-05-03T12:00:00"
    assert cached["full_json_data"]["source"] == str(tmp_path / "source.md")


def test_cache_manager_saves_page_artifacts_to_shards(tmp_path: Path) -> None:
    """CacheManager stores bulky page artifacts outside the monolithic cache."""
    source_path = Path("content/docs.md")
    site = SimpleNamespace(
        root_path=tmp_path,
        pages=[SimpleNamespace(source_path=source_path, toc_items=[])],
        assets=[],
        theme=None,
        config_service=SimpleNamespace(paths=BengalPaths(tmp_path)),
        url_registry=None,
    )
    manager = CacheManager(site)
    manager.cache = BuildCache(site_root=tmp_path)
    manager.cache.page_artifacts = {
        "content/docs.md": _artifact(source_path).full_json_data | {"uri": "/docs/"}
    }

    assert manager.save([], []) is True

    store = PageArtifactStore(site.config_service.paths.state_dir / "page-artifacts")
    assert store.load()["content/docs.md"]["uri"] == "/docs/"
    assert manager.cache.page_artifacts["content/docs.md"]["uri"] == "/docs/"


def _artifact(source_path: Path) -> AccumulatedPageData:
    return AccumulatedPageData(
        source_path=source_path,
        url="/docs/",
        uri="/docs/",
        title="Docs",
        description="Docs page",
        date=None,
        date_iso=None,
        plain_text="Docs body",
        excerpt="Docs",
        content_preview="Docs body",
        word_count=2,
        reading_time=1,
        section="Docs",
        tags=["guide"],
        dir="/docs/",
        enhanced_metadata={"type": "guide"},
        is_autodoc=False,
        full_json_data={"url": "/docs/", "title": "Docs"},
        json_output_path=Path("public/docs/index.json"),
        raw_metadata={"description": "Docs page"},
    )
