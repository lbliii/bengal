"""Integration tests for gettext PO/MO i18n workflow."""

from __future__ import annotations

import pytest

from bengal.core.site import Site
from bengal.i18n import load_catalog
from bengal.i18n.catalog import clear_catalog_cache


@pytest.mark.bengal(testroot="test-i18n-gettext")
def test_load_catalog_from_po(site: Site) -> None:
    """PO files are loaded when .mo does not exist."""
    clear_catalog_cache(site.root_path)
    catalog = load_catalog(site.root_path, "es", "messages")
    assert catalog is not None
    assert catalog.gettext("Home") == "Inicio"
    assert catalog.gettext("About") == "Acerca de"
    assert catalog.gettext("Welcome") == "Bienvenido"


@pytest.mark.bengal(testroot="test-i18n-gettext")
def test_load_catalog_arabic(site: Site) -> None:
    """Arabic PO is loaded correctly."""
    clear_catalog_cache(site.root_path)
    catalog = load_catalog(site.root_path, "ar", "messages")
    assert catalog is not None
    assert catalog.gettext("Home") == "الرئيسية"
    assert catalog.gettext("Welcome") == "مرحبا"


@pytest.mark.bengal(testroot="test-i18n-gettext")
def test_t_function_uses_gettext(site: Site) -> None:
    """t() in templates uses gettext when PO/MO exist."""
    from bengal.rendering.template_functions.i18n import _make_t

    t = _make_t(site)
    # Spanish
    assert t("Home", lang="es") == "Inicio"
    assert t("About", lang="es") == "Acerca de"
    # English (default)
    assert t("Home", lang="en") == "Home"
    # Arabic
    assert t("Welcome", lang="ar") == "مرحبا"


@pytest.mark.bengal(testroot="test-i18n-gettext")
def test_build_produces_locale_outputs(site: Site) -> None:
    """Build produces output for each locale."""
    from bengal.orchestration.build.options import BuildOptions

    site.build(BuildOptions())
    output_dir = site.output_dir
    assert output_dir is not None
    # Find all index.html under output (structure depends on i18n strategy)
    index_files = list(output_dir.rglob("index.html"))
    assert len(index_files) >= 3, (
        f"Expected at least 3 index.html (en, es, ar), found {len(index_files)}: "
        f"{[str(p.relative_to(output_dir)) for p in index_files]}"
    )
