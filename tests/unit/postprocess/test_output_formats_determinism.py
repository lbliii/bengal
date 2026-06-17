"""Determinism regression tests for per-page JSON output.

The per-page ``index.json`` sidecar must be byte-reproducible across builds of
the same tree (the warm==cold parity contract). A page's ``metadata`` dict is
assembled from frontmatter + cascade merges whose key order can vary run-to-run
under PYTHONHASHSEED, so the serializer must emit metadata keys in a stable
(sorted) order. This was a real bug: sidecars differed across rebuilds purely
because of metadata key ordering (not timestamps, as was long assumed).
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import Mock

from bengal.postprocess.output_formats.json_generator import PageJSONGenerator
from tests._testing.page_records import seed_parsed_page_state


def _mock_site(output_dir: Path) -> Mock:
    site = Mock()
    site.output_dir = output_dir
    site.dev_mode = False
    site.versioning_enabled = False
    site.build_time = None
    site.config = {"title": "T", "baseurl": ""}
    site.title = "T"
    site.baseurl = ""
    site.description = ""
    site.pages = []
    site.git_lastmod_by_source = {}
    return site


def _mock_page(output_dir: Path, metadata: dict) -> Mock:
    page = Mock()
    page.title = "Page"
    page.href = "/page/"
    page._path = "/page/"
    page.content = "Body"
    page.plain_text = "Body"
    seed_parsed_page_state(page, html_content="Body", plain_text="Body")
    page.output_path = output_dir / "page/index.html"
    page.tags = []
    page.date = None
    page.metadata = metadata
    page.source_path = Path("content/page.md")
    page.version = None
    page._section = None
    return page


def _generate_metadata(tmp_path: Path, metadata: dict) -> dict:
    output_dir = tmp_path / "public"
    output_dir.mkdir(parents=True)
    site = _mock_site(output_dir)
    page = _mock_page(output_dir, metadata)
    PageJSONGenerator(site, graph_data=None).generate([page])
    data = json.loads((output_dir / "page/index.json").read_text())
    return data.get("metadata", {})


class TestMetadataKeyOrderDeterminism:
    def test_metadata_keys_are_emitted_sorted(self, tmp_path: Path) -> None:
        # Insertion order deliberately NOT alphabetical.
        meta = {"zeta": 1, "alpha": 2, "mike": 3, "bravo": 4}
        emitted = _generate_metadata(tmp_path, meta)
        assert list(emitted.keys()) == sorted(emitted.keys())

    def test_serialized_metadata_is_identical_regardless_of_insertion_order(
        self, tmp_path: Path
    ) -> None:
        meta_a = {"zeta": 1, "alpha": 2, "mike": 3}
        meta_b = {"mike": 3, "zeta": 1, "alpha": 2}  # same content, different order
        a = _generate_metadata(tmp_path / "a", meta_a)
        b = _generate_metadata(tmp_path / "b", meta_b)
        assert json.dumps(a) == json.dumps(b)
