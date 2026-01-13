from __future__ import annotations

from pathlib import Path

from bengal.core.theme import Theme
from bengal.rendering.engines.jinja import JinjaTemplateEngine


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
        self._bengal_theme_chain_cache = None
        self._bengal_template_metadata_cache = None
        self._asset_manifest_fallbacks_global: set[str] = set()
        self._asset_manifest_fallbacks_lock = None

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
    engine = JinjaTemplateEngine(site)

    # Act: resolve template dirs (child first, then parent, default fallback)
    dirs = [str(d) for d in engine.template_dirs]

    # Assert: child templates dir appears before parent
    child_dir = str(tmp_path / "themes" / "child" / "templates")
    parent_dir = str(tmp_path / "themes" / "parent" / "templates")
    assert child_dir in dirs and parent_dir in dirs
    assert dirs.index(child_dir) < dirs.index(parent_dir)


def test_cross_theme_extends_with_prefix_loader(tmp_path: Path):
    """Test that templates can explicitly extend from a named theme using prefix syntax.
    
    This enables the pattern:
        {% extends "parent/base.html" %}
    
    Which allows child themes to extend specific parent themes without relying on
    priority-based resolution.
    
    Note: This is a Jinja2-specific feature using PrefixLoader.
        
    """
    # Arrange: parent theme with a base template
    parent_dir = tmp_path / "themes" / "parent" / "templates"
    parent_dir.mkdir(parents=True)
    (parent_dir / "base.html").write_text(
        """<!DOCTYPE html>
<html>
<head>{% block head %}{% endblock %}</head>
<body>{% block body %}PARENT BODY{% endblock %}</body>
</html>""",
        encoding="utf-8",
    )
    (tmp_path / "themes" / "parent" / "theme.toml").write_text(
        'name = "parent"\n', encoding="utf-8"
    )

    # Arrange: child theme that extends parent explicitly via prefix syntax
    child_dir = tmp_path / "themes" / "child" / "templates"
    child_dir.mkdir(parents=True)
    (child_dir / "base.html").write_text(
        """{# Cross-theme extends: explicitly reference parent theme #}
{% extends "parent/base.html" %}

{% block body %}CHILD BODY{% endblock %}""",
        encoding="utf-8",
    )
    (tmp_path / "themes" / "child" / "theme.toml").write_text(
        'name = "child"\nextends = "parent"\n', encoding="utf-8"
    )

    # Act: render the child template using JinjaTemplateEngine (prefix loader is Jinja-specific)
    site = DummySite(tmp_path, theme="child")
    engine = JinjaTemplateEngine(site)
    template = engine.env.get_template("base.html")
    rendered = template.render()

    # Assert: child body is rendered, but within parent structure
    assert "CHILD BODY" in rendered
    assert "PARENT BODY" not in rendered  # Block was overridden
    assert "<!DOCTYPE html>" in rendered  # Parent structure preserved
    assert "<head>" in rendered


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
    engine = JinjaTemplateEngine(site)

    # The default theme should be in the search path
    # (may not render perfectly without full site context, but template should load)
    template = engine.env.get_template("page.html")
    # If this doesn't raise TemplateNotFound, the fallback works
    assert template is not None


def test_prefix_loader_enables_direct_theme_access(tmp_path: Path):
    """Test that PrefixLoader allows direct access to any theme's templates.
    
    Note: This is a Jinja2-specific feature using PrefixLoader.
        
    """
    # Arrange: create a theme with a unique template
    theme_dir = tmp_path / "themes" / "my-theme" / "templates"
    theme_dir.mkdir(parents=True)
    (theme_dir / "unique.html").write_text("UNIQUE CONTENT", encoding="utf-8")
    (tmp_path / "themes" / "my-theme" / "theme.toml").write_text(
        'name = "my-theme"\n', encoding="utf-8"
    )

    # Act: load template using prefix syntax (Jinja-specific feature)
    site = DummySite(tmp_path, theme="my-theme")
    engine = JinjaTemplateEngine(site)

    # Direct access via prefix
    template = engine.env.get_template("my-theme/unique.html")
    rendered = template.render()

    assert "UNIQUE CONTENT" in rendered
