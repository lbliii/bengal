"""
Regression: auto-discovered menus must render the home page.

When no manual ``menu.main`` is configured, MenuOrchestrator builds the main
menu from sections. Templates must use ``get_menu_lang('main')`` — not a
separate ``get_auto_nav()`` fallback — so index.html is always emitted.
"""

from __future__ import annotations

from bengal.orchestration.build.options import BuildOptions


def test_auto_menu_site_renders_index_html(site_factory) -> None:
    """Sites without manual menu.main must produce index.html with nav."""
    site = site_factory("test-product")
    site.build(BuildOptions(quiet=True, force_sequential=True))

    index_path = site.output_dir / "index.html"
    assert index_path.is_file(), "index.html missing — home page render likely failed"

    main_menu = site.menu.get("main", [])
    assert main_menu, "MenuOrchestrator should populate site.menu['main'] in auto mode"

    html = index_path.read_text(encoding="utf-8")
    first_item = main_menu[0]
    assert first_item.name in html, "Orchestrated main menu should appear in rendered nav"


def test_home_template_renders_without_get_auto_nav(site_factory) -> None:
    """home.html splash defaults must work from orchestrated main menu only."""
    site = site_factory("test-product")
    (site.root_path / "content" / "_index.md").write_text(
        """---
title: Splash Home
template: home.html
---
""",
        encoding="utf-8",
    )
    site.discover_content()
    site.build(BuildOptions(quiet=True, force_sequential=True))

    assert (site.output_dir / "index.html").is_file()
