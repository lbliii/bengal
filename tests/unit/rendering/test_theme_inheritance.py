from __future__ import annotations

from typing import TYPE_CHECKING

from bengal.core.theme import Theme
from bengal.rendering.engines.kida import KidaTemplateEngine

if TYPE_CHECKING:
    from pathlib import Path


class DummySite:
    def __init__(self, root_path: Path, theme: str = "default") -> None:
        self.root_path = root_path
        self.theme = theme
        self.config = {}
        self.output_dir = root_path / "public"  # Required by TemplateEngine for bytecode cache
        # Required Site attributes for template engine
        self.dev_mode = False
        self.versioning_enabled = False
        self.versions: list[str] = []
        self._bengal_template_dirs_cache = None
        self._bengal_theme_chain_cache = None

    @property
    def baseurl(self) -> str:
        """Return baseurl from config."""
        site_section = self.config.get("site", {})
        if isinstance(site_section, dict) and site_section.get("baseurl"):
            return site_section.get("baseurl", "")
        return self.config.get("baseurl", "")

    @property
    def theme_config(self) -> Theme:
        """Return a default Theme for testing."""
        return Theme(name=self.theme)


def write_theme(root: Path, name: str, extends: str | None, with_template: bool = False) -> None:
    tdir = root / "themes" / name
    (tdir / "templates").mkdir(parents=True, exist_ok=True)
    if extends is not None:
        (tdir / "theme.toml").write_text(
            f'name = "{name}"\nextends = "{extends}"\n', encoding="utf-8"
        )
    if with_template:
        (tdir / "templates" / "marker.html").write_text(f"{name}", encoding="utf-8")


def test_theme_chain_child_overrides_parent(tmp_path: Path):
    # Arrange: parent theme defines a template; child extends parent and defines its own
    write_theme(tmp_path, "parent", extends=None, with_template=True)
    write_theme(tmp_path, "child", extends="parent", with_template=True)

    site = DummySite(tmp_path, theme="child")
    engine = KidaTemplateEngine(site)

    # Act: resolve template dirs (child first, then parent, default fallback)
    dirs = [str(d) for d in engine.template_dirs]

    # Assert: child templates dir appears before parent
    child_dir = str(tmp_path / "themes" / "child" / "templates")
    parent_dir = str(tmp_path / "themes" / "parent" / "templates")
    assert child_dir in dirs
    assert parent_dir in dirs
    assert dirs.index(child_dir) < dirs.index(parent_dir)


def test_cross_theme_extends_fallback_to_priority(tmp_path: Path):
    """Test that normal extends (without prefix) still works via priority resolution."""
    # Arrange: child theme that extends via normal resolution (no prefix)
    child_dir = tmp_path / "themes" / "child" / "templates"
    child_dir.mkdir(parents=True)
    (child_dir / "page.html").write_text(
        """{% extends "base.html" %}
{% block body %}PAGE CONTENT{% endblock %}""",
        encoding="utf-8",
    )
    (tmp_path / "themes" / "child" / "theme.toml").write_text('name = "child"\n', encoding="utf-8")

    # Act: the child theme uses default's base.html via normal priority resolution
    site = DummySite(tmp_path, theme="child")
    engine = KidaTemplateEngine(site)

    # The default theme should be in the search path
    # (may not render perfectly without full site context, but template should load)
    template = engine.env.get_template("page.html")
    # If this doesn't raise TemplateNotFound, the fallback works
    assert template is not None
