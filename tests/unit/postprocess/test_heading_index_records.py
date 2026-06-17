"""Tests for per-heading search index record generation."""

from __future__ import annotations

from bengal.postprocess.output_formats.utils import build_heading_index_records


def test_build_heading_index_records_from_toc_and_html() -> None:
    html = """
    <p>Intro paragraph.</p>
    <h2 id="install">Install</h2>
    <p>Install instructions here.</p>
    <h3 id="verify">Verify</h3>
    <p>Verification steps.</p>
    """

    records = build_heading_index_records(
        page_uri="/docs/start/",
        page_url="/docs/start/",
        page_title="Getting Started",
        html_content=html,
        toc_items=[
            {"id": "install", "title": "Install", "level": 2},
            {"id": "verify", "title": "Verify", "level": 3},
        ],
        excerpt_length=50,
    )

    assert len(records) == 2
    assert records[0]["objectID"] == "/docs/start#install"
    assert records[0]["kind"] == "heading"
    assert records[0]["parent_objectID"] == "/docs/start/"
    assert records[0]["breadcrumb"] == "Getting Started › Install"
    assert "Install instructions" in records[0]["content"]
    assert records[1]["anchor"] == "verify"


def test_build_heading_index_records_skips_search_excluded_pages() -> None:
    records = build_heading_index_records(
        page_uri="/docs/hidden/",
        page_url="/docs/hidden/",
        page_title="Hidden",
        html_content="<h2 id='x'>X</h2>",
        toc_items=[{"id": "x", "title": "X", "level": 2}],
        excerpt_length=50,
        search_exclude=True,
    )

    assert records == []
