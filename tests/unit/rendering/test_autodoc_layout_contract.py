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
    # Endpoint cards link directly to the endpoint page URL. The previous
    # `{{ tag_href }}{{ ep.href }}` concatenation double-prefixed the URL and
    # produced broken links; cards must use the resolved `ep.href` alone.
    assert 'href="{{ ep.href }}"' in home
    assert 'href="{{ tag_href }}{{ ep.href }}"' not in home
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
    # Primitive/enum schemas (no viewer body) render a standalone example section;
    # body schemas render examples inside the viewer instead (no duplication).
    assert "{% if example_val is not none and not has_body %}" in schema_template
    assert 'id="example"' in schema_template
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


def test_autodoc_css_has_no_legacy_rest_layout_selectors() -> None:
    """Legacy OpenAPI layout CSS must not creep back into ``autodoc.css``.

    The bespoke catalog/app-shell (``.api-catalog-app`` / ``.openapi-app``) now
    owns every rendered REST page (verified: zero occurrences of these legacy
    classes across the generated ``bengal-demo-commerce`` site). The pre-shell
    eras left behind several dead selector layers — the Mintlify explorer, the
    three-column ``.api-explorer`` grid, the single-column ``.api-reference``
    layout, the standalone ``.api-home`` landing page, and the ``.api-playground``
    bar. This guard fails if any of them returns.
    """
    css = Path("bengal/themes/default/assets/css/components/autodoc.css").read_text(
        encoding="utf-8"
    )

    # Each token below is a *base class* unique to a removed legacy layer. None
    # is a substring of a live class — note the live shell keeps `.api-param-row`,
    # `.api-responses`, `.api-code-samples`, so we assert the specific dead names
    # (`.api-param-field`, `.api-response-header`, `.api-code-group`) instead.
    legacy_selectors = [
        ".docs-layout--api-explorer",
        ".api-explorer",
        ".api-reference",
        ".api-home",
        ".api-playground",
        ".api-param-field",
        ".api-param-name",
        ".api-param-badge",
        ".api-response-header",
        ".api-response-status",
        ".api-code-group",
        ".api-code-header",
        ".api-code-title",
        ".web-endpoint-block",
        ".web-grid-huge-navs",
        ".web-side-nav",
        ".rest-explorer",
        ".rest-endpoint",
        ".api-deprecated-banner",
    ]
    present = [sel for sel in legacy_selectors if sel in css]
    assert not present, f"legacy REST layout selectors reappeared in autodoc.css: {present}"

    # Discriminating positive guard: this test must fail if the file is gutted,
    # not just when the legacy classes are absent. The live shell selectors below
    # are emitted by the active templates and must remain styled.
    for live in (
        ".api-catalog-app",
        ".openapi-app",
        ".api-operation",
        ".api-schema-viewer",
        ".api-method",
        ".api-sidebar-nav",
    ):
        assert live in css, f"live REST shell selector missing from autodoc.css: {live}"


def test_openapi_schema_viewer_renders_advanced_constructs() -> None:
    """The schema viewer macro must render composition, constraints, flags, and
    a bounded circular-reference indicator (#285).

    File-content contract — the viewer is recursive and depends on the full
    rendering graph, so we assert the rendering hooks are wired rather than
    rendering ``base.html`` in a unit test.
    """
    viewer = Path("bengal/themes/default/templates/autodoc/openapi/_schema.html").read_text(
        encoding="utf-8"
    )

    # Composition (oneOf/anyOf/allOf) + discriminator.
    assert "schema | schema_composition" in viewer
    assert 'class="api-schema-composition"' in viewer
    assert 'data-composition="{{ composition.kind }}"' in viewer
    assert "Discriminated by" in viewer
    assert "api-schema-composition__mapping" in viewer

    # Per-property validation constraints + flag badges.
    assert "prop_schema | schema_constraints" in viewer
    assert 'class="api-schema-viewer__constraints"' in viewer
    assert 'data-constraint="{{ clabel }}"' in viewer
    assert 'data-badge="readonly"' in viewer
    assert 'data-badge="writeonly"' in viewer
    assert 'data-badge="nullable"' in viewer

    # Open / typed maps (additionalProperties).
    assert "schema | schema_additional_properties" in viewer
    assert 'class="api-schema-viewer__additional"' in viewer

    # Bounded circular references render a readable indicator, not an empty box.
    assert "schema | schema_ref" in viewer
    assert "api-schema-viewer__truncated" in viewer
    assert "circular reference" in viewer


def test_openapi_schema_detail_page_surfaces_composition() -> None:
    """Composed/polymorphic schemas (no direct properties) still get a body and
    surface composition metadata in the side panel.
    """
    schema_template = Path("bengal/themes/default/templates/autodoc/openapi/schema.html").read_text(
        encoding="utf-8"
    )

    # A composed schema with no properties must still render a body section.
    assert "schema?.display_schema | schema_composition" in schema_template
    assert "has_body" in schema_template
    # Side panel exposes composition kind + discriminator for polymorphic models.
    assert "{{ composition.kind }}" in schema_template
    assert "composition.discriminator.property_name" in schema_template
    # Deprecated schemas get a header badge.
    assert 'data-badge="deprecated"' in schema_template


def test_openapi_schema_index_tiles_show_composition_chips() -> None:
    """Schema catalog tiles expose composition/deprecated summary metadata (#285)."""
    section_template = Path(
        "bengal/themes/default/templates/autodoc/openapi/section-index.html"
    ).read_text(encoding="utf-8")

    assert "schema.display_schema | schema_composition" in section_template
    assert 'class="api-schema-catalog__chip"' in section_template
    assert 'data-kind="discriminator"' in section_template
    # Must not regress the existing tile contract.
    assert "schema.properties |> items |> take(4)" in section_template
    assert "api-schema-catalog__preview" in section_template


def test_autodoc_css_styles_advanced_schema_constructs() -> None:
    """The new advanced-schema markup must be styled in autodoc.css (#285)."""
    css = Path("bengal/themes/default/assets/css/components/autodoc.css").read_text(
        encoding="utf-8"
    )

    for selector in (
        ".api-schema-composition",
        '.api-schema-composition[data-composition="oneOf"]',
        ".api-schema-viewer__constraint",
        ".api-schema-viewer__additional",
        ".api-schema-viewer__truncated",
        ".api-schema-catalog__chip",
        '.autodoc-badge[data-badge="readonly"]',
        '.autodoc-badge[data-badge="writeonly"]',
    ):
        assert selector in css, f"advanced-schema selector missing from autodoc.css: {selector}"


# =============================================================================
# Catalog navigation interactions (#287)
# =============================================================================


def _read_openapi_template(name: str) -> str:
    return Path(f"bengal/themes/default/templates/autodoc/openapi/{name}").read_text(
        encoding="utf-8"
    )


def test_openapi_catalog_landing_has_filter_and_rail_hooks() -> None:
    """The catalog landing must expose filter + scroll-spy + group hooks (#287)."""
    home = _read_openapi_template("home.html")

    assert 'data-bengal="api-catalog"' in home
    assert "data-api-rail" in home  # left-rail scroll-spy
    assert "data-api-filter-input" in home
    assert "data-api-filter-empty" in home
    assert "data-api-filter-group" in home
    # Endpoint cards are filterable and carry structured method/path for search.
    assert "data-api-filter-item" in home
    assert 'data-method="{{ ep.method }}"' in home
    assert 'data-path="{{ ep.path }}"' in home


def test_openapi_explorer_shell_and_rails_enable_scroll_spy() -> None:
    """The shared app shell activates the enhancement; in-page navs are rails."""
    explorer = _read_openapi_template("layouts/explorer.html")
    assert 'data-bengal="api-catalog"' in explorer

    for name in ("list.html", "endpoint.html", "schema.html"):
        template = _read_openapi_template(name)
        assert 'class="openapi-nav"' in template
        assert "data-api-rail" in template, f"{name} openapi-nav missing data-api-rail"


def test_openapi_schema_index_is_filterable() -> None:
    """The schema catalog index exposes a filter and filterable tiles (#287)."""
    section = _read_openapi_template("section-index.html")
    assert "data-api-filter-input" in section
    assert "data-api-filter-item" in section
    assert 'data-schema-name="{{ schema.name }}"' in section
    assert "data-api-filter-empty" in section


def test_openapi_path_copy_buttons_present() -> None:
    """Operation paths get a copy button riding the global [data-copy] handler."""
    list_template = _read_openapi_template("list.html")
    endpoint = _read_openapi_template("endpoint.html")

    assert 'class="api-copy-btn"' in list_template
    assert 'data-copy="{{ ep.path }}"' in list_template
    assert 'class="api-copy-btn"' in endpoint
    assert 'data-copy="{{ endpoint_path }}"' in endpoint


def test_base_template_registers_api_catalog_enhancement() -> None:
    """The enhancement loader must be able to resolve the api-catalog module."""
    base = Path("bengal/themes/default/templates/base.html").read_text(encoding="utf-8")
    assert "'api-catalog': '{{ asset_url(\"js/enhancements/api-catalog.js\") }}'" in base


def test_api_catalog_enhancement_module_exists_and_registers() -> None:
    """The vanilla-JS module exists and self-registers (no npm dependency)."""
    module = Path("bengal/themes/default/assets/js/enhancements/api-catalog.js").read_text(
        encoding="utf-8"
    )
    assert "Bengal.enhance.register('api-catalog'" in module
    # Reduced-motion is honored (the toc.js scroll-spy gap this module closes).
    assert "prefers-reduced-motion" in module
    # Deep links must survive filtering: the module reveals filtered-out targets.
    assert "hashchange" in module


def test_autodoc_css_styles_catalog_navigation() -> None:
    """The #287 markup (filter, rail active-state, copy button) must be styled."""
    css = Path("bengal/themes/default/assets/css/components/autodoc.css").read_text(
        encoding="utf-8"
    )
    for selector in (
        ".api-catalog-filter__input",
        ".api-catalog-filter__empty",
        "[data-api-filter-item][hidden]",
        ".api-rail__link--active",
        ".api-copy-btn",
    ):
        assert selector in css, f"catalog-nav selector missing from autodoc.css: {selector}"
