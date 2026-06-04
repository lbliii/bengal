"""
End-to-end rendering tests for advanced OpenAPI schema constructs (#285).

Builds the ``test-openapi-advanced`` root — a spec exercising oneOf/anyOf/allOf
composition, discriminators, nullable/readOnly/writeOnly/deprecated flags,
numeric/string/array constraints, additionalProperties (boolean + typed map),
self-referential schemas, and field-level examples — and asserts the generated
schema detail pages render them as structured documentation rather than raw
JSON dumps.

These render through the real Kida engine, so they also guard against template
syntax regressions in ``autodoc/openapi/_schema.html`` and ``schema.html``.
"""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.autodoc


def _schema_html(site, name: str) -> str:
    """Read a generated schema detail page, failing clearly if it is missing."""
    page = site.output_dir / "api" / "schemas" / name / "index.html"
    assert page.exists(), f"Expected schema page missing: {page}"
    html = page.read_text(encoding="utf-8")
    # Pages must be non-blank, styled shells — not error stubs.
    assert "api-schema" in html, f"{name} page is not a styled schema shell"
    return html


@pytest.mark.bengal(testroot="test-openapi-advanced")
def test_oneof_discriminator_renders_variants_and_mapping(site, build_site) -> None:
    """A polymorphic oneOf schema renders its variants and discriminator mapping."""
    build_site()
    html = _schema_html(site, "PaymentMethod")

    assert 'data-composition="oneOf"' in html
    assert "One of" in html
    # Discriminator + mapping rows (value -> target schema name).
    assert "Discriminated by" in html
    assert "api-schema-composition__discriminator-prop" in html
    assert ">card<" in html
    assert "CardPayment" in html
    assert ">bank<" in html
    assert "BankPayment" in html
    # The composed schema has no direct properties yet still gets a real body.
    assert "api-schema-composition__variant" in html


@pytest.mark.bengal(testroot="test-openapi-advanced")
def test_constraints_and_flags_render_on_account(site, build_site) -> None:
    """Numeric/string/array constraints and field flags render as structured chips."""
    build_site()
    html = _schema_html(site, "Account")

    # Flags.
    assert 'data-badge="readonly"' in html  # id
    assert 'data-badge="nullable"' in html  # nickname
    assert 'data-badge="deprecated"' in html  # legacy_token
    # Constraints.
    for constraint in (
        'data-constraint="format"',
        'data-constraint="min"',
        'data-constraint="max"',
        'data-constraint="multiple of"',
        'data-constraint="min length"',
        'data-constraint="max length"',
        'data-constraint="unique items"',
    ):
        assert constraint in html, f"missing constraint chip: {constraint}"

    # Constraint VALUES are interpolated, not just the labels — exercises the
    # template's `{% if cvalue %}: {{ cvalue }}` branch (balance property).
    assert "min: 0" in html
    assert "max: 1000000" in html
    assert "multiple of: 0.01" in html

    # Property-level composition (primary_method: oneOf) and a typed map
    # (labels: additionalProperties) render inline, not just at the top level.
    assert 'data-composition="oneOf"' in html
    assert "api-schema-viewer__additional" in html


@pytest.mark.bengal(testroot="test-openapi-advanced")
def test_writeonly_and_pattern_render_on_card_payment(site, build_site) -> None:
    """writeOnly fields and regex patterns surface on the variant schema page."""
    build_site()
    html = _schema_html(site, "CardPayment")

    assert 'data-badge="writeonly"' in html  # cvv
    assert 'data-constraint="pattern"' in html  # number


@pytest.mark.bengal(testroot="test-openapi-advanced")
def test_additional_properties_render(site, build_site) -> None:
    """Open maps and typed maps both render an additionalProperties section."""
    build_site()

    settings = _schema_html(site, "Settings")
    assert "api-schema-viewer__additional" in settings
    assert "Allows additional properties" in settings
    assert "&quot;theme&quot;" in settings or '"theme"' in settings  # schema-level example

    metadata = _schema_html(site, "Metadata")
    assert "api-schema-viewer__additional" in metadata
    assert "Additional properties" in metadata


@pytest.mark.bengal(testroot="test-openapi-advanced")
def test_allof_and_anyof_render_as_composition(site, build_site) -> None:
    """allOf inheritance and anyOf unions render as labeled composition blocks."""
    build_site()

    dog = _schema_html(site, "Dog")
    assert 'data-composition="allOf"' in dog
    assert "All of" in dog

    search = _schema_html(site, "SearchValue")
    assert 'data-composition="anyOf"' in search
    assert "Any of" in search


@pytest.mark.bengal(testroot="test-openapi-advanced")
def test_primitive_schema_shows_constraints_and_example(site, build_site) -> None:
    """A primitive schema (no object body) still surfaces its constraints + example."""
    build_site()
    html = _schema_html(site, "CurrencyCode")

    assert "api-schema-shape" in html  # primitive shape section
    assert 'data-constraint="pattern"' in html
    assert 'data-constraint="min length"' in html
    # Primitives render a standalone example section (not via the viewer body).
    assert 'id="example"' in html
    assert "USD" in html


@pytest.mark.bengal(testroot="test-openapi-advanced")
def test_circular_schema_is_bounded_and_readable(site, build_site) -> None:
    """A self-referential schema renders a bounded, readable circular indicator."""
    build_site()
    html = _schema_html(site, "TreeNode")

    assert "circular reference" in html
    assert "api-schema-viewer--ref" in html
    # Bounded: recursion does not explode the page with unbounded nested viewers.
    assert html.count("api-schema-viewer--depth-") < 12


@pytest.mark.bengal(testroot="test-openapi-advanced")
def test_schema_index_tiles_summarize_composition(site, build_site) -> None:
    """The schema catalog index surfaces composition/deprecated tile chips."""
    build_site()
    index = site.output_dir / "api" / "schemas" / "index.html"
    assert index.exists(), f"Schema index missing: {index}"
    html = index.read_text(encoding="utf-8")

    assert "api-schema-catalog__chip" in html
    assert 'data-kind="oneOf"' in html
    assert 'data-kind="discriminator"' in html
