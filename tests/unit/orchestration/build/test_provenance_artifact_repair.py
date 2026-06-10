"""Tests for artifact-repair coverage in incremental postprocess filtering.

Regression coverage for the latent bug where a warm no-op build repaired
sitemap/robots/output-format artifacts but NOT rss.xml or the prebuilt
search-index.json. These assertions fail if the artifact list (and its
config/availability guards) regresses.
"""

from __future__ import annotations

import importlib.util
from types import SimpleNamespace
from typing import TYPE_CHECKING

import pytest

from bengal.orchestration.build.provenance_filter import (
    _missing_postprocess_artifacts,
    _search_index_repairable,
)

if TYPE_CHECKING:
    from pathlib import Path

LUNR_AVAILABLE = importlib.util.find_spec("lunr") is not None


def _site(output_dir: Path, config: dict) -> SimpleNamespace:
    return SimpleNamespace(output_dir=output_dir, config=config)


# ---------------------------------------------------------------------------
# rss.xml
# ---------------------------------------------------------------------------


def test_rss_included_when_generate_rss_enabled_and_missing(tmp_path: Path) -> None:
    output_dir = tmp_path / "public"
    output_dir.mkdir()
    site = _site(output_dir, {"generate_rss": True, "output_formats": {"enabled": False}})

    missing = _missing_postprocess_artifacts(site)

    assert output_dir / "rss.xml" in missing


def test_rss_excluded_when_already_present(tmp_path: Path) -> None:
    output_dir = tmp_path / "public"
    output_dir.mkdir()
    (output_dir / "rss.xml").write_text("<rss />", encoding="utf-8")
    site = _site(output_dir, {"generate_rss": True, "output_formats": {"enabled": False}})

    missing = _missing_postprocess_artifacts(site)

    assert output_dir / "rss.xml" not in missing


def test_rss_excluded_when_generate_rss_disabled(tmp_path: Path) -> None:
    output_dir = tmp_path / "public"
    output_dir.mkdir()
    site = _site(output_dir, {"generate_rss": False, "output_formats": {"enabled": False}})

    missing = _missing_postprocess_artifacts(site)

    assert output_dir / "rss.xml" not in missing


def test_rss_i18n_prefix_path_placement(tmp_path: Path) -> None:
    """Under prefix strategy for a non-default language, rss.xml lives under <lang>/."""
    output_dir = tmp_path / "public"
    output_dir.mkdir()
    site = SimpleNamespace(
        output_dir=output_dir,
        current_language="fr",
        config={
            "generate_rss": True,
            "output_formats": {"enabled": False},
            "i18n": {"strategy": "prefix", "default_language": "en"},
        },
    )

    missing = _missing_postprocess_artifacts(site)

    assert output_dir / "fr" / "rss.xml" in missing
    assert output_dir / "rss.xml" not in missing


# ---------------------------------------------------------------------------
# search-index.json
# ---------------------------------------------------------------------------


def _search_site(output_dir: Path, *, search: object, index_json: bool = True) -> SimpleNamespace:
    site_wide = ["index_json"] if index_json else []
    return _site(
        output_dir,
        {
            "generate_rss": False,
            "search": search,
            "output_formats": {"enabled": True, "site_wide": site_wide},
        },
    )


@pytest.mark.skipif(not LUNR_AVAILABLE, reason="lunr package not installed")
def test_search_index_included_when_enabled_prebuilt_and_lunr(tmp_path: Path) -> None:
    output_dir = tmp_path / "public"
    output_dir.mkdir()
    site = _search_site(output_dir, search={"enabled": True, "lunr": {"prebuilt": True}})

    assert _search_index_repairable(site) is True
    assert output_dir / "search-index.json" in _missing_postprocess_artifacts(site)


@pytest.mark.skipif(LUNR_AVAILABLE, reason="requires lunr to be absent")
def test_search_index_excluded_when_lunr_unavailable(tmp_path: Path) -> None:
    """Without lunr installed, the file can never be created, so it must not be
    reported missing — otherwise a warm build would loop reporting a phantom."""
    output_dir = tmp_path / "public"
    output_dir.mkdir()
    site = _search_site(output_dir, search={"enabled": True, "lunr": {"prebuilt": True}})

    assert _search_index_repairable(site) is False
    assert output_dir / "search-index.json" not in _missing_postprocess_artifacts(site)


def test_search_index_excluded_when_search_disabled(tmp_path: Path) -> None:
    output_dir = tmp_path / "public"
    output_dir.mkdir()
    site = _search_site(output_dir, search={"enabled": False})

    assert _search_index_repairable(site) is False
    assert output_dir / "search-index.json" not in _missing_postprocess_artifacts(site)


def test_search_index_excluded_when_prebuilt_disabled(tmp_path: Path) -> None:
    output_dir = tmp_path / "public"
    output_dir.mkdir()
    site = _search_site(output_dir, search={"enabled": True, "lunr": {"prebuilt": False}})

    assert _search_index_repairable(site) is False
    assert output_dir / "search-index.json" not in _missing_postprocess_artifacts(site)


def test_search_index_excluded_when_index_json_not_configured(tmp_path: Path) -> None:
    output_dir = tmp_path / "public"
    output_dir.mkdir()
    site = _search_site(
        output_dir, search={"enabled": True, "lunr": {"prebuilt": True}}, index_json=False
    )

    assert _search_index_repairable(site) is False
    assert output_dir / "search-index.json" not in _missing_postprocess_artifacts(site)
