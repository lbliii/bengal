"""Tests for legacy link resolution compatibility wrappers."""

from __future__ import annotations

from bengal.utils.paths.link_resolution import resolved_path_url_variants


def test_resolved_path_url_variants_returns_legacy_list():
    variants = resolved_path_url_variants("/docs/")

    assert variants == ["/docs/", "/docs", "/docs/"]
    variants.append("/extra")
    assert variants[-1] == "/extra"
