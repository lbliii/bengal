"""Tests for Atom feed generation."""

from __future__ import annotations

import xml.etree.ElementTree as ET
from datetime import datetime
from typing import TYPE_CHECKING
from unittest.mock import MagicMock

if TYPE_CHECKING:
    from pathlib import Path


def _page(
    title: str = "Test Post",
    date: datetime | None = None,
    in_rss: bool = True,
    output_path: Path | None = None,
) -> MagicMock:
    page = MagicMock()
    page.title = title
    page.date = date or datetime(2024, 1, 15)
    page.in_rss = in_rss
    page.output_path = output_path
    page.slug = "test-post"
    page.metadata = {"description": "Summary"}
    page.lang = "en"
    return page


def _site(tmp_path: Path, pages: list[MagicMock]) -> MagicMock:
    site = MagicMock()
    site.pages = pages
    site.output_dir = tmp_path
    site.title = "Test Site"
    site.baseurl = "https://example.com"
    site.description = "A test site"
    site.config = {"i18n": {}}
    return site


def test_generates_atom_xml_with_pages(tmp_path: Path) -> None:
    from bengal.postprocess.rss import AtomGenerator

    page = _page(output_path=tmp_path / "test-post" / "index.html")
    site = _site(tmp_path, [page])

    AtomGenerator(site).generate()

    atom_path = tmp_path / "atom.xml"
    assert atom_path.exists()
    root = ET.parse(atom_path).getroot()
    assert root.tag.endswith("feed")
    assert root.find("{http://www.w3.org/2005/Atom}entry") is not None


def test_atom_excludes_pages_not_in_rss(tmp_path: Path) -> None:
    from bengal.postprocess.rss import AtomGenerator

    site = _site(tmp_path, [_page(in_rss=False)])

    AtomGenerator(site).generate()

    assert not (tmp_path / "atom.xml").exists()


def test_atom_generates_prefixed_language_feeds(tmp_path: Path) -> None:
    from bengal.postprocess.rss import AtomGenerator

    page = _page(output_path=tmp_path / "fr" / "test-post" / "index.html")
    page.lang = "fr"
    site = _site(tmp_path, [page])
    site.config = {
        "i18n": {
            "strategy": "prefix",
            "default_language": "en",
            "languages": ["en", "fr"],
        }
    }

    AtomGenerator(site).generate()

    assert (tmp_path / "fr" / "atom.xml").exists()
    assert not (tmp_path / "atom.xml").exists()


def test_atom_self_link_matches_non_default_language_path_without_prefix_strategy(
    tmp_path: Path,
) -> None:
    from bengal.postprocess.rss import AtomGenerator

    page = _page(output_path=tmp_path / "fr" / "test-post" / "index.html")
    page.lang = "fr"
    site = _site(tmp_path, [page])
    site.config = {
        "i18n": {
            "strategy": "none",
            "default_language": "en",
            "languages": ["en", "fr"],
        }
    }

    AtomGenerator(site).generate()

    atom_path = tmp_path / "fr" / "atom.xml"
    assert atom_path.exists()
    root = ET.parse(atom_path).getroot()
    ns = {"atom": "http://www.w3.org/2005/Atom"}
    self_link = root.find("atom:link[@rel='self']", ns)
    assert self_link is not None
    assert self_link.attrib["href"] == "https://example.com/fr/atom.xml"
