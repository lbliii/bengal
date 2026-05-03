"""Tests for rendering-owned reference registries."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

from bengal.rendering.reference_registry import (
    InternalReferenceResolver,
    build_link_registry,
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


def test_resolver_checks_url_and_anchor_variants(tmp_path):
    resolver = InternalReferenceResolver(build_link_registry(_mock_site(tmp_path)))

    assert resolver.has_url("/docs")
    assert resolver.has_url("/guide/")
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
