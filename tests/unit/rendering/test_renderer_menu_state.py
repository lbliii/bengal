"""Regression tests for render-time menu state handling."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from bengal.rendering import renderer as renderer_module
from bengal.rendering.renderer import Renderer


class _SiteWithExplodingMenuMutation:
    def __init__(self) -> None:
        self.config: dict[str, Any] = {"build": {}}
        self.taxonomies: dict[str, Any] = {}

    def mark_active_menu_items(self, page: Any) -> None:
        raise AssertionError("rendering must not mutate shared menu active state")


class _TemplateEngine:
    def __init__(self, site: _SiteWithExplodingMenuMutation) -> None:
        self.site = site

    def render(self, template_name: str, context: dict[str, Any]) -> str:
        return f"{template_name}:{context['content']}"


class _Page:
    def __init__(self) -> None:
        self.title = "Page"
        self.html_content = "<p>body</p>"
        self.metadata: dict[str, Any] = {}
        self.type = None
        self.source_path = Path("/site/content/page.md")
        self._section = None


def test_renderer_does_not_mark_shared_menu_items(monkeypatch) -> None:
    """Rendering must leave menu active state immutable across parallel pages."""

    def fake_build_page_context(**kwargs: Any) -> dict[str, Any]:
        return {"content": kwargs["content"], "page": kwargs["page"]}

    monkeypatch.setattr(renderer_module, "build_page_context", fake_build_page_context)

    renderer = Renderer(_TemplateEngine(_SiteWithExplodingMenuMutation()))

    assert renderer.render_page(_Page()) == "page.html:<p>body</p>"
