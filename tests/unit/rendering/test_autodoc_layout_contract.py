"""
Contract tests for autodoc layout rendering in the default theme.

These tests are intentionally "static" (file-content based) to avoid the heavy
runtime dependency graph of rendering `base.html` in unit tests.

The goal is to prevent regressions where autodoc pages look "broken" because:
- The default docs layout constrains `.prose` to `--prose-width` (75ch) and centers it.
- Autodoc API/CLI reference pages are app-like UIs (card grids) and must not be constrained.
- `base.html` must not emit `data-variant="None"` when no variant is set.
"""

from __future__ import annotations

import re
from pathlib import Path


def test_default_theme_css_does_not_constrain_api_reference_prose() -> None:
    """Ensure autodoc reference pages have prose constraints for readable content.

    The CSS system uses data-type selectors on body with autodoc type names:
    - autodoc-python: Python API documentation
    - autodoc-cli: CLI command documentation
    - autodoc-rest: REST/OpenAPI documentation

    All autodoc pages constrain their content to prose-width for readability.

    """
    css_path = Path("bengal/themes/default/assets/css/composition/layouts.css")
    css = css_path.read_text(encoding="utf-8")

    # All autodoc reference pages should have prose-width constraints
    assert 'body[data-type="autodoc-python"]' in css
    assert 'body[data-type="autodoc-cli"]' in css
    assert 'body[data-type="autodoc-rest"]' in css

    # These pages should have max-width constraints on .docs-main children
    assert 'body[data-type="autodoc-python"] .docs-main>*' in css
    assert 'body[data-type="autodoc-cli"] .docs-main>*' in css
    assert 'body[data-type="autodoc-rest"] .docs-main>*' in css


def test_base_template_does_not_render_none_variant_attribute() -> None:
    """
    Ensure `base.html` does not emit `data-variant="None"` when page.variant is None.

    This is a contract check on the template expression itself; rendering base.html in a
    unit test requires a large mock surface because it includes many partials.

    """
    base_path = Path("bengal/themes/default/templates/base.html")
    base = base_path.read_text(encoding="utf-8")

    # Require a guard that emits an empty string when variant is None/absent.
    # Kida 0.7.0 strict_undefined requires `page?.variant ?? ''` for safe access;
    # the trailing `or ''` further coerces a stored None to an empty string.
    assert re.search(
        r"data-variant=\"\{\{\s*\(\s*page\?\.variant\s*\?\?\s*''\s*\)\s+or\s+''\s*\}\}\"",
        base,
    )


def test_openapi_consolidated_list_renders_full_operation_reference() -> None:
    """Consolidated OpenAPI tag pages should render endpoint details, not only cards."""
    list_path = Path("bengal/themes/default/templates/autodoc/openapi/list.html")
    template = list_path.read_text(encoding="utf-8")

    assert 'class="api-operations autodoc-section"' in template
    assert 'class="api-operation' in template
    assert "partials/request-body.html" in template
    assert "partials/responses.html" in template
    assert "partials/code-samples.html" in template
    assert "api-list__cards" not in template


def test_openapi_home_uses_full_viewport_catalog_shell() -> None:
    """The OpenAPI landing page should be a bespoke catalog, not a docs column."""
    home_path = Path("bengal/themes/default/templates/autodoc/openapi/home.html")
    home = home_path.read_text(encoding="utf-8")
    css_path = Path("bengal/themes/default/assets/css/components/autodoc.css")
    css = css_path.read_text(encoding="utf-8")

    assert "{% extends 'base.html' %}" in home
    assert "{% block site_footer %}{% end %}" in home
    assert 'class="api-catalog-app"' in home
    assert "api-catalog-app__left-rail" in home
    assert "api-catalog-app__right-rail" in home
    assert 'href="{{ tag_href }}{{ ep.href }}"' in home
    assert "autodoc/openapi/layouts/reference.html" not in home

    assert 'body[data-type="autodoc-rest"] .api-catalog-app' in css
    assert "grid-template-columns: minmax(16rem, 18vw) minmax(0, 1fr) minmax(22rem, 24vw);" in css
    assert 'body[data-type="autodoc-rest"] .openapi-app' in css
    assert "grid-template-columns: minmax(16rem, 18vw) minmax(0, 1fr) minmax(24rem, 28vw);" in css


def test_openapi_templates_use_bespoke_app_shell_not_legacy_reference_layout() -> None:
    """REST API pages should own their layout below the global top bar."""
    explorer_path = Path("bengal/themes/default/templates/autodoc/openapi/layouts/explorer.html")
    explorer = explorer_path.read_text(encoding="utf-8")
    list_template = Path("bengal/themes/default/templates/autodoc/openapi/list.html").read_text(
        encoding="utf-8"
    )
    endpoint_template = Path(
        "bengal/themes/default/templates/autodoc/openapi/endpoint.html"
    ).read_text(encoding="utf-8")
    schema_template = Path("bengal/themes/default/templates/autodoc/openapi/schema.html").read_text(
        encoding="utf-8"
    )

    assert '{% extends "base.html" %}' in explorer
    assert "{% block site_footer %}{% end %}" in explorer
    assert 'class="openapi-app"' in explorer
    assert "breadcrumbs(" not in explorer
    assert "page_navigation(" not in explorer

    assert "{% block api_left %}" in list_template
    assert "{% block api_header %}" in list_template
    assert "{% block api_main %}" in list_template
    assert "{% block api_right %}" in list_template
    assert "{% block api_left %}" in endpoint_template
    assert "{% block api_right %}" in endpoint_template
    assert "{% block api_left %}" in schema_template


def test_openapi_schema_index_uses_catalog_tiles() -> None:
    """Schema landing pages should use REST catalog tiles, not generic cards."""
    section_template = Path(
        "bengal/themes/default/templates/autodoc/openapi/section-index.html"
    ).read_text(encoding="utf-8")

    assert "{% let schema_items = section | schemas %}" in section_template
    assert 'class="api-schema-catalog"' in section_template
    assert 'class="api-schema-catalog__tile"' in section_template
    assert "schema.properties | length" in section_template
    assert "api-schema-catalog__preview" in section_template
    assert "schema.properties |> items |> take(4)" in section_template


def test_openapi_schema_pages_render_primitive_and_enum_shapes() -> None:
    """Schema detail pages should not look empty for primitive or enum models."""
    schema_template = Path("bengal/themes/default/templates/autodoc/openapi/schema.html").read_text(
        encoding="utf-8"
    )

    assert "api-schema-shape" in schema_template
    assert "schema?.raw_schema?.format" in schema_template
    assert "{% if example_val is not none %}" in schema_template
    assert "<div><dt>Required</dt><dd>{{ required_props | length }}</dd></div>" in schema_template


def test_openapi_code_sample_ids_are_scoped_by_method_and_path() -> None:
    """Inline operation examples need unique tab/copy targets on consolidated pages."""
    partial_path = Path(
        "bengal/themes/default/templates/autodoc/openapi/partials/code-samples.html"
    )
    partial = partial_path.read_text(encoding="utf-8")

    assert "{% let sample_id = (method_upper ~ '-' ~ path) | slugify %}" in partial
    assert "code-panel-{{ sample_id }}-curl" in partial
    assert 'data-copy-target="code-{{ sample_id }}-curl"' in partial
