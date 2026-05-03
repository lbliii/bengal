"""Tests for rendering-owned reference registries."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

from bengal.cache.build_cache import BuildCache
from bengal.rendering.reference_registry import (
    InternalReferenceResolver,
    build_link_registry,
    build_link_registry_from_artifacts,
    build_reference_resolver,
)


def _mock_site(tmp_path):
    site = MagicMock()
    site.root_path = tmp_path
    site.config = {"output_formats": {"enabled": True, "per_page": ["llm_txt"]}}

    content_dir = tmp_path / "content"
    content_dir.mkdir(exist_ok=True)
    (content_dir / "docs.md").touch()

    page = MagicMock()
    page.href = "/docs/"
    page._path = "/docs/"
    page.permalink = "/guide/"
    page.source_path = Path("content/docs.md")
    page.toc_items = [{"id": "intro"}, {"id": "install"}]

    site.pages = [page]
    return site


def test_registry_indexes_rendered_urls_anchors_and_auxiliary_outputs(tmp_path):
    registry = build_link_registry(_mock_site(tmp_path))

    assert "/docs" in registry.page_urls
    assert "/guide/" in registry.page_urls
    assert "intro" in registry.anchors_by_url["/docs/"]
    assert "/docs/index.txt" in registry.auxiliary_urls
    assert "/llms.txt" in registry.auxiliary_urls
    assert "/index.json" in registry.auxiliary_urls


def test_resolver_checks_url_and_anchor_variants(tmp_path):
    resolver = InternalReferenceResolver(build_link_registry(_mock_site(tmp_path)))

    assert resolver.has_url("/docs")
    assert resolver.has_url("/guide/")
    assert resolver.has_url("/llms.txt")
    assert resolver.has_anchor("/docs", "install")
    assert not resolver.has_anchor("/docs/", "missing")


def test_build_reference_resolver_uses_existing_site_registry(tmp_path):
    site = _mock_site(tmp_path)
    registry = build_link_registry(site)
    site.link_registry = registry

    resolver = build_reference_resolver(site)

    assert resolver.registry is registry


def test_resolver_precomputes_combined_url_index(tmp_path):
    resolver = InternalReferenceResolver(build_link_registry(_mock_site(tmp_path)))

    assert resolver.all_urls == resolver.registry.page_urls | resolver.registry.auxiliary_urls
    assert "/docs/index.txt" in resolver.all_urls


def test_registry_fingerprint_is_stable_for_same_link_targets(tmp_path):
    registry_a = build_link_registry(_mock_site(tmp_path))
    registry_b = build_link_registry(_mock_site(tmp_path))

    assert registry_a.fingerprint == registry_b.fingerprint


def test_registry_fingerprint_changes_when_url_truth_changes(tmp_path):
    site = _mock_site(tmp_path)
    registry_a = build_link_registry(site)
    site.pages[0].href = "/renamed/"
    registry_b = build_link_registry(site)

    assert registry_a.fingerprint != registry_b.fingerprint


def test_registry_fingerprint_changes_when_anchor_truth_changes(tmp_path):
    site = _mock_site(tmp_path)
    registry_a = build_link_registry(site)
    site.pages[0].toc_items = [{"id": "intro"}, {"id": "changed"}]
    registry_b = build_link_registry(site)

    assert registry_a.fingerprint != registry_b.fingerprint


def test_registry_fingerprint_changes_when_auxiliary_outputs_change(tmp_path):
    site = _mock_site(tmp_path)
    registry_a = build_link_registry(site)
    site.config = {"output_formats": {"enabled": False}}
    registry_b = build_link_registry(site)

    assert registry_a.fingerprint != registry_b.fingerprint


def test_site_wide_auxiliary_outputs_respect_explicit_config(tmp_path):
    site = _mock_site(tmp_path)
    site.config = {
        "output_formats": {
            "enabled": True,
            "per_page": ["llm_txt"],
            "site_wide": ["llms_txt"],
        }
    }

    registry = build_link_registry(site)

    assert "/llms.txt" in registry.auxiliary_urls
    assert "/index.json" not in registry.auxiliary_urls
    assert "/changelog.json" not in registry.auxiliary_urls


def test_site_wide_auxiliary_outputs_include_baseurl_variants(tmp_path):
    site = _mock_site(tmp_path)
    site.baseurl = "/bengal"

    registry = build_link_registry(site)

    assert "/llms.txt" in registry.auxiliary_urls
    assert "/bengal/llms.txt" in registry.auxiliary_urls


def test_build_link_registry_from_artifacts_uses_cached_url_and_anchor_truth(tmp_path):
    site = _mock_site(tmp_path)
    cache = BuildCache(site_root=tmp_path)
    cache.page_artifacts["content/docs.md"] = {
        "source_path": "content/docs.md",
        "uri": "/docs/",
        "anchors": ["intro", "install"],
    }
    build_context = SimpleNamespace(cache=cache)

    registry = build_link_registry_from_artifacts(site, build_context)

    assert registry is not None
    assert "/docs" in registry.page_urls
    assert "install" in registry.anchors_by_url["/docs/"]
    assert "/docs/index.txt" in registry.auxiliary_urls
    assert "/llms.txt" in registry.auxiliary_urls


def test_build_link_registry_from_artifacts_falls_back_without_anchor_inventory(tmp_path):
    site = _mock_site(tmp_path)
    cache = BuildCache(site_root=tmp_path)
    cache.page_artifacts["content/docs.md"] = {
        "source_path": "content/docs.md",
        "uri": "/docs/",
    }
    build_context = SimpleNamespace(cache=cache)

    assert build_link_registry_from_artifacts(site, build_context) is None
