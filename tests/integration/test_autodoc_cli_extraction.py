"""Integration tests that Bengal CLI autodoc generates virtual pages (issue #621)."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from pathlib import Path

    from bengal.core.site import Site


@pytest.fixture
def site_with_bengal_cli_autodoc(tmp_path: Path) -> Site:
    """Minimal site with real Bengal CLI autodoc enabled."""
    from bengal.core.site import Site

    content_dir = tmp_path / "content"
    content_dir.mkdir()
    (content_dir / "_index.md").write_text("---\ntitle: Home\n---\n# Home\n")

    config_dir = tmp_path / "config" / "_default"
    config_dir.mkdir(parents=True)
    (config_dir / "site.yaml").write_text("site:\n  title: CLI Autodoc Test\n  baseurl: ''\n")
    (config_dir / "autodoc.yaml").write_text(
        """
autodoc:
  cli:
    enabled: true
    app_module: bengal.cli:cli
    framework: milo
    output_prefix: cli
  python:
    enabled: false
  openapi:
    enabled: false
"""
    )

    return Site.from_config(tmp_path)


def test_bengal_cli_autodoc_generates_virtual_pages(site_with_bengal_cli_autodoc: Site) -> None:
    """Real Milo CLI autodoc should emit build/theme leaf pages under /cli/."""
    from bengal.autodoc.orchestration import VirtualAutodocOrchestrator
    from bengal.orchestration.content import ContentOrchestrator

    content = ContentOrchestrator(site_with_bengal_cli_autodoc)
    content.discover_content()

    orchestrator = VirtualAutodocOrchestrator(site_with_bengal_cli_autodoc)
    pages, sections, _result = orchestrator.generate()

    page_urls = {page.href for page in pages}
    section_urls = {section.href for section in sections}

    assert "/cli/" in section_urls
    assert "/cli/build/" in page_urls
    assert "/cli/theme/list/" in page_urls
    assert "/cli/bengal/build/" not in page_urls

    build_pages = [page for page in pages if page.href == "/cli/build/"]
    assert build_pages
    assert build_pages[0].title
