"""
End-to-end tests for REST autodoc catalog navigation interactions (#287).

Builds the ``test-openapi-catalog`` root (multi-tag, multi-endpoint) and asserts
the generated HTML carries the filter / scroll-spy / copy hooks that the
client-side ``api-catalog`` enhancement consumes. Asserting on OUTPUT (not just
template source) proves the rendered path actually emits the hooks, and that the
JS module is discovered + fingerprinted by the asset pipeline.

Anchors and filter inputs are plain HTML, so these pages work with JS disabled;
the enhancement only layers behavior on top.
"""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.autodoc


@pytest.mark.bengal(testroot="test-openapi-catalog")
def test_landing_catalog_emits_filter_and_rail_hooks(site, build_site) -> None:
    """The /api/ landing catalog renders filter + scroll-spy + group hooks."""
    build_site()
    index = site.output_dir / "api" / "index.html"
    assert index.exists(), f"Catalog landing missing: {index}"
    html = index.read_text(encoding="utf-8")

    assert 'data-bengal="api-catalog"' in html
    assert "data-api-rail" in html
    assert "data-api-filter-input" in html
    assert "data-api-filter-empty" in html
    # 6 endpoints -> multiple filterable items + 2 tag groups.
    assert html.count("data-api-filter-item") >= 6
    assert html.count("data-api-filter-group") >= 2


@pytest.mark.bengal(testroot="test-openapi-catalog")
def test_endpoint_and_tag_pages_have_rail_and_path_copy(site, build_site) -> None:
    """Resource shells enable scroll-spy and expose an operation-path copy button."""
    build_site()

    endpoint = site.output_dir / "api" / "tags" / "Orders" / "get-orders" / "index.html"
    assert endpoint.exists(), f"Endpoint page missing: {endpoint}"
    ep_html = endpoint.read_text(encoding="utf-8")
    assert 'data-bengal="api-catalog"' in ep_html
    assert "data-api-rail" in ep_html
    assert 'class="api-copy-btn"' in ep_html
    assert "data-copy=" in ep_html

    tag_page = site.output_dir / "api" / "tags" / "Orders" / "index.html"
    assert tag_page.exists(), f"Tag page missing: {tag_page}"
    tag_html = tag_page.read_text(encoding="utf-8")
    assert "data-api-rail" in tag_html
    # Consolidated tag page lists operations, each with a path copy button.
    assert tag_html.count('class="api-copy-btn"') >= 1


@pytest.mark.bengal(testroot="test-openapi-catalog")
def test_schema_index_filterable_in_output(site, build_site) -> None:
    """The schema catalog index renders a filter and filterable tiles."""
    build_site()
    index = site.output_dir / "api" / "schemas" / "index.html"
    assert index.exists(), f"Schema index missing: {index}"
    html = index.read_text(encoding="utf-8")

    assert "data-api-filter-input" in html
    assert html.count("data-api-filter-item") >= 5  # 5 schemas


@pytest.mark.bengal(testroot="test-openapi-catalog")
def test_api_catalog_module_is_fingerprinted(site, build_site) -> None:
    """The vanilla-JS enhancement is discovered + fingerprinted (no npm)."""
    build_site()
    enh_dir = site.output_dir / "assets" / "js" / "enhancements"
    modules = list(enh_dir.glob("api-catalog*.js")) if enh_dir.exists() else []
    assert modules, "api-catalog.js was not emitted/fingerprinted into the build"
