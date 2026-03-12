"""Unit tests for ChangelogGenerator.

Covers:
- First build (no previous changelog)
- Subsequent build with added, modified, removed pages
- page_hashes persistence for next-build diff
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock

from bengal.postprocess.output_formats.changelog_generator import ChangelogGenerator


def _make_site(output_dir: Path, build_time: object = None) -> MagicMock:
    site = MagicMock()
    site.output_dir = output_dir
    site.build_time = build_time
    site.dev_mode = False
    return site


def _make_page(href: str, plain_text: str, output_path: Path | None = None) -> MagicMock:
    page = MagicMock()
    page.href = href
    page.plain_text = plain_text
    page.output_path = output_path or Path(f"public{href}index.html")
    return page


class TestChangelogGenerator:
    def test_first_build_emits_all_added(self, tmp_path: Path) -> None:
        from datetime import datetime

        build_time = datetime(2026, 3, 11, 10, 0, 0)
        site = _make_site(tmp_path, build_time)
        pages = [
            _make_page("/docs/a/", "Content A"),
            _make_page("/docs/b/", "Content B"),
        ]
        gen = ChangelogGenerator(site)
        path = gen.generate(pages)

        assert path is not None
        data = json.loads(path.read_text())
        assert data["build_id"] == "2026-03-11T10:00:00"
        assert data["previous_build_id"] is None
        assert set(data["pages_added"]) == {"/docs/a/", "/docs/b/"}
        assert data["pages_modified"] == []
        assert data["pages_removed"] == []
        assert data["stats"]["total_pages"] == 2
        assert data["stats"]["added"] == 2
        assert "page_hashes" in data
        assert len(data["page_hashes"]) == 2

    def test_second_build_detects_modified_and_removed(self, tmp_path: Path) -> None:
        site = _make_site(tmp_path, "2026-03-11T11:00:00")
        changelog_path = tmp_path / "changelog.json"
        changelog_path.write_text(
            json.dumps(
                {
                    "build_id": "2026-03-11T10:00:00",
                    "previous_build_id": None,
                    "pages_added": ["/docs/a/", "/docs/b/", "/docs/c/"],
                    "pages_modified": [],
                    "pages_removed": [],
                    "page_hashes": {
                        "/docs/a/": "hash_a_old",
                        "/docs/b/": "hash_b",
                        "/docs/c/": "hash_c",
                    },
                    "stats": {"total_pages": 3, "added": 3, "modified": 0, "removed": 0},
                }
            )
        )

        pages = [
            _make_page("/docs/a/", "Content A modified"),
            _make_page("/docs/b/", "Content B"),
            _make_page("/docs/d/", "Content D new"),
        ]
        gen = ChangelogGenerator(site)
        path = gen.generate(pages)

        assert path is not None
        data = json.loads(path.read_text())
        assert data["previous_build_id"] == "2026-03-11T10:00:00"
        assert "/docs/d/" in data["pages_added"]
        assert "/docs/c/" in data["pages_removed"]
        modified_urls = [m["url"] for m in data["pages_modified"]]
        assert "/docs/a/" in modified_urls
        assert data["stats"]["modified"] >= 1
        assert data["stats"]["removed"] == 1
