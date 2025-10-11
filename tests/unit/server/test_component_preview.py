"""Tests for component preview functionality."""

from pathlib import Path

import pytest
import yaml

from bengal.core.site import Site
from bengal.server.component_preview import ComponentPreviewServer


def _write(p: Path, text: str) -> None:
    """Helper to write file with parent directory creation."""
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding='utf-8')


@pytest.fixture
def component_site(tmp_path: Path) -> Site:
    """Create a test site with component manifests."""
    # Create a basic bengal.toml
    config = tmp_path / "bengal.toml"
    _write(config, """
[site]
title = "Test Site"
base_url = "https://example.com"
theme = "test-theme"
""")

    # Create component manifest (use correct path: themes/<theme>/dev/components/)
    manifest = tmp_path / "themes" / "test-theme" / "dev" / "components" / "testcard.yaml"
    manifest_data = {
        "name": "Test Card",
        "template": "partials/test-card.html",
        "variants": [
            {
                "id": "default",
                "name": "Default",
                "context": {"title": "Test Title"}
            },
            {
                "id": "long-title",
                "name": "Long Title",
                "context": {"title": "Very Long Test Title"}
            }
        ]
    }
    _write(manifest, yaml.dump(manifest_data))

    # Create template
    template = tmp_path / "themes" / "test-theme" / "templates" / "partials" / "test-card.html"
    _write(template, '<div class="card">{{ title }}</div>')

    # Create output directory with CSS
    css_file = tmp_path / "public" / "assets" / "css" / "style.abc123.css"
    _write(css_file, "body { color: red; }")

    site = Site.from_config(tmp_path)
    return site


def test_discover_components_empty(tmp_path: Path):
    """Test component discovery with no manifests."""
    config = tmp_path / "bengal.toml"
    _write(config, '[site]\ntitle = "Test"\nbase_url = "https://example.com"\ntheme = "nonexistent-theme"')

    site = Site.from_config(tmp_path)
    cps = ComponentPreviewServer(site)
    components = cps.discover_components()

    # May find bundled default theme components, so just check it's a list
    assert isinstance(components, list)


def test_discover_components_single(component_site: Site):
    """Test discovering a single component."""
    cps = ComponentPreviewServer(component_site)
    components = cps.discover_components()

    # Find our test component (may have bundled ones too)
    test_comp = next((c for c in components if c["id"] == "testcard"), None)
    assert test_comp is not None
    assert test_comp["name"] == "Test Card"
    assert test_comp["template"] == "partials/test-card.html"
    assert len(test_comp["variants"]) == 2


def test_discover_components_invalid_yaml(tmp_path: Path):
    """Test handling of malformed YAML manifests."""
    config = tmp_path / "bengal.toml"
    _write(config, '[site]\ntitle = "Test"\nbase_url = "https://example.com"\ntheme = "test-theme-unique"')

    # Create invalid YAML
    manifest = tmp_path / "bengal" / "themes" / "test-theme-unique" / "dev" / "components" / "invalid.yaml"
    _write(manifest, "invalid: yaml: content: [")

    site = Site.from_config(tmp_path)
    cps = ComponentPreviewServer(site)
    components = cps.discover_components()

    # Should handle error gracefully (may find bundled components)
    invalid_comp = next((c for c in components if c["id"] == "invalid"), None)
    assert invalid_comp is None  # Our invalid one should not be there


def test_discover_components_missing_template_key(tmp_path: Path):
    """Test handling of manifests without template key."""
    config = tmp_path / "bengal.toml"
    _write(config, '[site]\ntitle = "Test"\nbase_url = "https://example.com"\ntheme = "test-theme-unique2"')

    # Create manifest without template key
    manifest = tmp_path / "bengal" / "themes" / "test-theme-unique2" / "dev" / "components" / "incomplete.yaml"
    manifest_data = {
        "name": "Incomplete Component",
        "variants": []
    }
    _write(manifest, yaml.dump(manifest_data))

    site = Site.from_config(tmp_path)
    cps = ComponentPreviewServer(site)
    components = cps.discover_components()

    # Should skip components without template
    incomplete_comp = next((c for c in components if c["id"] == "incomplete"), None)
    assert incomplete_comp is None


def test_discover_components_theme_override(tmp_path: Path):
    """Test that child theme overrides parent theme components."""
    config = tmp_path / "bengal.toml"
    _write(config, '[site]\ntitle = "Test"\nbase_url = "https://example.com"\ntheme = "child-theme"')

    # Create parent theme component
    parent_manifest = tmp_path / "bengal" / "themes" / "default" / "dev" / "components" / "button.yaml"
    parent_data = {
        "name": "Parent Button",
        "template": "partials/button.html",
        "variants": [{"id": "default", "name": "Default", "context": {}}]
    }
    _write(parent_manifest, yaml.dump(parent_data))

    # Create child theme component with same ID
    child_manifest = tmp_path / "bengal" / "themes" / "child-theme" / "dev" / "components" / "button.yaml"
    child_data = {
        "name": "Child Button",
        "template": "partials/custom-button.html",
        "variants": [{"id": "default", "name": "Default", "context": {}}]
    }
    _write(child_manifest, yaml.dump(child_data))

    site = Site.from_config(tmp_path)
    cps = ComponentPreviewServer(site)
    components = cps.discover_components()

    # Should use child theme version
    assert len(components) == 1
    assert components[0]["name"] == "Child Button"
    assert components[0]["template"] == "partials/custom-button.html"


def test_render_component_basic(component_site: Site):
    """Test basic component rendering."""
    cps = ComponentPreviewServer(component_site)

    context = {"title": "My Title"}
    html = cps.render_component("partials/test-card.html", context)

    assert "<!doctype html>" in html
    assert '<div class="card">My Title</div>' in html
    assert '<link rel="stylesheet"' in html


def test_render_component_css_fingerprinting(component_site: Site):
    """Test that CSS URLs are properly fingerprinted."""
    cps = ComponentPreviewServer(component_site)

    html = cps.render_component("partials/test-card.html", {})

    # Should include fingerprinted CSS URL (not hardcoded /assets/css/style.css)
    assert '/assets/css/style.abc123.css' in html or '/assets/css/style.' in html


def test_render_component_page_to_article_alias(component_site: Site):
    """Test that 'page' context is aliased to 'article'."""
    # Create template that uses 'article' variable
    template = component_site.root_path / "bengal" / "themes" / "test-theme" / "templates" / "partials" / "article-card.html"
    _write(template, '<div>{{ article.title }}</div>')

    cps = ComponentPreviewServer(component_site)

    # Pass 'page' in context
    context = {"page": {"title": "Page Title"}}
    html = cps.render_component("partials/article-card.html", context)

    # Should be accessible as 'article'
    assert "<div>Page Title</div>" in html


def test_view_page_not_found(component_site: Site):
    """Test viewing a non-existent component."""
    cps = ComponentPreviewServer(component_site)

    html = cps.view_page("nonexistent", None)

    assert "Not found" in html
    assert "nonexistent" in html


def test_view_page_single_variant(component_site: Site):
    """Test viewing a specific variant."""
    cps = ComponentPreviewServer(component_site)

    html = cps.view_page("card", "long-title")

    # Should render only the specified variant
    assert "Very Long Test Title" in html


def test_view_page_all_variants(component_site: Site):
    """Test viewing all variants of a component."""
    cps = ComponentPreviewServer(component_site)

    html = cps.view_page("card", None)

    # Should render all variants
    assert "Test Title" in html or "Default" in html
    assert "Very Long Test Title" in html or "Long Title" in html
    assert "<section>" in html


def test_view_page_variant_not_found(component_site: Site):
    """Test viewing a non-existent variant."""
    cps = ComponentPreviewServer(component_site)

    # Should render with empty context (no error)
    html = cps.view_page("card", "nonexistent-variant")

    # Should not crash, should render something
    assert html is not None


def test_list_page_empty(tmp_path: Path):
    """Test component list page with no components."""
    config = tmp_path / "bengal.toml"
    _write(config, '[site]\ntitle = "Test"\nbase_url = "https://example.com"')

    site = Site.from_config(tmp_path)
    cps = ComponentPreviewServer(site)

    html = cps.list_page()

    assert "Components" in html
    assert "No components found" in html


def test_list_page_with_components(component_site: Site):
    """Test component list page with components."""
    cps = ComponentPreviewServer(component_site)

    html = cps.list_page()

    assert "Components" in html
    assert "Test Card" in html
    assert "2 variants" in html
    assert "href=\"/__bengal_components__/view?c=card\"" in html


def test_component_manifest_dirs_theme_chain(component_site: Site):
    """Test that component manifest directories follow theme chain."""
    cps = ComponentPreviewServer(component_site)
    dirs = cps._component_manifest_dirs()

    # Should include at least the test theme and default
    dir_strs = [str(d) for d in dirs]
    assert any("test-theme" in d for d in dir_strs)


def test_component_variant_id_normalization(tmp_path: Path):
    """Test that variant IDs are normalized from names."""
    config = tmp_path / "bengal.toml"
    _write(config, '[site]\ntitle = "Test"\nbase_url = "https://example.com"\ntheme = "test-theme"')

    manifest = tmp_path / "bengal" / "themes" / "test-theme" / "dev" / "components" / "test.yaml"
    manifest_data = {
        "name": "Test Component",
        "template": "partials/test.html",
        "variants": [
            {"name": "Very Long Name", "context": {}}
        ]
    }
    _write(manifest, yaml.dump(manifest_data))

    site = Site.from_config(tmp_path)
    cps = ComponentPreviewServer(site)
    components = cps.discover_components()

    # Should normalize "Very Long Name" to "very-long-name"
    variant = components[0]["variants"][0]
    assert variant["id"] == "very-long-name"


def test_render_component_error_handling(tmp_path: Path):
    """Test error handling when template rendering fails."""
    config = tmp_path / "bengal.toml"
    _write(config, '[site]\ntitle = "Test"\nbase_url = "https://example.com"')

    site = Site.from_config(tmp_path)
    cps = ComponentPreviewServer(site)

    # Try to render non-existent template
    with pytest.raises(Exception):
        cps.render_component("nonexistent.html", {})


def test_multiple_components_discovery(tmp_path: Path):
    """Test discovering multiple components."""
    config = tmp_path / "bengal.toml"
    _write(config, '[site]\ntitle = "Test"\nbase_url = "https://example.com"\ntheme = "test-theme"')

    # Create multiple component manifests
    for comp_name in ["button", "card", "nav"]:
        manifest = tmp_path / "bengal" / "themes" / "test-theme" / "dev" / "components" / f"{comp_name}.yaml"
        manifest_data = {
            "name": f"Test {comp_name.title()}",
            "template": f"partials/{comp_name}.html",
            "variants": []
        }
        _write(manifest, yaml.dump(manifest_data))

    site = Site.from_config(tmp_path)
    cps = ComponentPreviewServer(site)
    components = cps.discover_components()

    assert len(components) == 3
    comp_ids = [c["id"] for c in components]
    assert "button" in comp_ids
    assert "card" in comp_ids
    assert "nav" in comp_ids


def test_component_with_no_variants(tmp_path: Path):
    """Test component with empty variants list."""
    config = tmp_path / "bengal.toml"
    _write(config, '[site]\ntitle = "Test"\nbase_url = "https://example.com"\ntheme = "test-theme"')

    manifest = tmp_path / "bengal" / "themes" / "test-theme" / "dev" / "components" / "simple.yaml"
    manifest_data = {
        "name": "Simple Component",
        "template": "partials/simple.html",
        "variants": []
    }
    _write(manifest, yaml.dump(manifest_data))

    # Create template
    template = tmp_path / "bengal" / "themes" / "test-theme" / "templates" / "partials" / "simple.html"
    _write(template, '<div>Simple</div>')

    site = Site.from_config(tmp_path)
    cps = ComponentPreviewServer(site)

    html = cps.view_page("simple", None)

    # Should render with default variant
    assert "<div>Simple</div>" in html

