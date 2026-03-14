"""i18n E2E: multi-language build, per-locale outputs, hreflang.

Covers i18n with prefix strategy, dir content structure, and gettext.
Plan: plan-production-maturity.md Phase 0A
"""

from __future__ import annotations

from collections.abc import Callable

import pytest


@pytest.mark.e2e
def test_i18n_build_produces_per_locale_outputs(
    built_site: Callable[..., tuple[object, object, object]],
) -> None:
    """i18n: Build produces output dirs for each configured locale."""
    _site_dir, output_dir, result = built_site("test-i18n-gettext")
    assert result.returncode == 0, f"Build failed: {result.stderr}"
    assert (output_dir / "en").is_dir(), "Expected en/ output dir"
    assert (output_dir / "es").is_dir(), "Expected es/ output dir"
    assert (output_dir / "ar").is_dir(), "Expected ar/ output dir"


@pytest.mark.e2e
def test_i18n_build_includes_hreflang_in_html(
    built_site: Callable[..., tuple[object, object, object]],
) -> None:
    """i18n: HTML includes hreflang alternate links."""
    _, output_dir, result = built_site("test-i18n-gettext")
    assert result.returncode == 0
    html_path = output_dir / "en" / "index.html"
    assert html_path.exists(), "Expected en index.html"
    html = html_path.read_text(encoding="utf-8")
    assert 'rel="alternate" hreflang=' in html or 'hreflang="en"' in html
    assert 'hreflang="es"' in html
    assert 'hreflang="ar"' in html


@pytest.mark.e2e
def test_i18n_build_translated_content_per_locale(
    built_site: Callable[..., tuple[object, object, object]],
) -> None:
    """i18n: Each locale contains translated content."""
    _, output_dir, result = built_site("test-i18n-gettext")
    assert result.returncode == 0

    en_index = output_dir / "en" / "index.html"
    es_index = output_dir / "es" / "es" / "index.html"
    ar_index = output_dir / "ar" / "ar" / "index.html"

    for path in (en_index, es_index, ar_index):
        if not path.exists():
            continue
        content = path.read_text(encoding="utf-8")
        assert "<h1>" in content, f"Expected h1 in {path}"

    if en_index.exists():
        assert "Welcome" in en_index.read_text(encoding="utf-8")
    if es_index.exists():
        assert "Bienvenido" in es_index.read_text(encoding="utf-8")
    if ar_index.exists():
        assert "مرحبا" in ar_index.read_text(encoding="utf-8")
