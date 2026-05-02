"""Tests for write_output() with RenderedPage parameter.

Sprint 2: Immutable Page Pipeline — verifies that write_output reads
from the RenderedPage record when provided, ignoring mutable Page state.
"""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from bengal.core.output import BuildOutputCollector
from bengal.core.records import RenderedPage
from bengal.rendering.pipeline.output import write_output


def _make_page(**overrides):
    """Create a minimal Page-like object for testing."""
    defaults = {
        "source_path": Path("content/test.md"),
        "output_path": Path("/tmp/old/index.html"),
        "rendered_html": "<p>old</p>",
        "metadata": {},
    }
    defaults.update(overrides)
    return SimpleNamespace(**defaults)


def _make_site(tmp_path, fast_writes=True):
    """Create a minimal Site-like object for testing."""
    return SimpleNamespace(
        config={"build": {"fast_writes": fast_writes}},
        output_dir=tmp_path,
    )


class TestWriteOutputRenderedPage:
    """write_output uses RenderedPage when provided."""

    def test_writes_rendered_page_html(self, tmp_path):
        """rendered_html comes from RenderedPage, not page."""
        out = tmp_path / "page" / "index.html"
        page = _make_page(rendered_html="<p>stale page html</p>", output_path=out)
        site = _make_site(tmp_path)

        rendered_page = RenderedPage(
            source_path=Path("content/test.md"),
            output_path=out,
            rendered_html="<p>fresh rendered page html</p>",
            render_time_ms=1.0,
        )

        write_output(page, site, rendered_page=rendered_page)

        assert out.read_text() == "<p>fresh rendered page html</p>"

    def test_writes_to_rendered_page_output_path(self, tmp_path):
        """output_path comes from RenderedPage, not page."""
        page_out = tmp_path / "old" / "index.html"
        record_out = tmp_path / "new" / "index.html"

        page = _make_page(output_path=page_out, rendered_html="<p>page</p>")
        site = _make_site(tmp_path)

        rendered_page = RenderedPage(
            source_path=Path("content/test.md"),
            output_path=record_out,
            rendered_html="<p>record</p>",
            render_time_ms=1.0,
        )

        write_output(page, site, rendered_page=rendered_page)

        assert record_out.read_text() == "<p>record</p>"
        assert not page_out.exists()

    def test_falls_back_to_page_without_rendered_page(self, tmp_path):
        """Without RenderedPage, write_output reads from page as before."""
        out = tmp_path / "fallback" / "index.html"
        page = _make_page(output_path=out, rendered_html="<p>from page</p>")
        site = _make_site(tmp_path)

        write_output(page, site)

        assert out.read_text() == "<p>from page</p>"

    def test_skips_write_when_rendered_html_empty(self, tmp_path):
        """Empty rendered_html on RenderedPage should skip write."""
        out = tmp_path / "skip" / "index.html"
        page = _make_page(output_path=out)
        site = _make_site(tmp_path)

        rendered_page = RenderedPage(
            source_path=Path("content/test.md"),
            output_path=out,
            rendered_html="",
            render_time_ms=0.0,
        )

        write_output(page, site, rendered_page=rendered_page)

        assert not out.exists()

    def test_skips_write_when_output_path_none(self, tmp_path):
        """None output_path on page (no RenderedPage) should skip write."""
        page = _make_page(output_path=None, rendered_html="<p>html</p>")
        site = _make_site(tmp_path)

        # Should not raise
        write_output(page, site)

    def test_does_not_record_unchanged_html_output(self, tmp_path):
        """Output collector should only receive route-visible byte changes."""
        out = tmp_path / "same" / "index.html"
        out.parent.mkdir(parents=True)
        out.write_text("<p>same</p>", encoding="utf-8")
        page = _make_page(output_path=out, rendered_html="<p>same</p>")
        site = _make_site(tmp_path)
        collector = BuildOutputCollector(output_dir=tmp_path)

        write_output(page, site, collector=collector)

        assert collector.get_outputs() == []
        assert out.read_text(encoding="utf-8") == "<p>same</p>"

    def test_full_rebuild_can_skip_existing_output_compare(self, tmp_path):
        """Full rebuilds can record outputs without reading old HTML first."""
        out = tmp_path / "same" / "index.html"
        out.parent.mkdir(parents=True)
        out.write_text("<p>same</p>", encoding="utf-8")
        page = _make_page(output_path=out, rendered_html="<p>same</p>")
        site = _make_site(tmp_path)
        collector = BuildOutputCollector(output_dir=tmp_path)

        write_output(page, site, collector=collector, compare_existing_output=False)

        outputs = collector.get_outputs()
        assert len(outputs) == 1
        assert str(outputs[0].path) == "same/index.html"
        assert out.read_text(encoding="utf-8") == "<p>same</p>"

    def test_records_changed_html_output(self, tmp_path):
        """Changed HTML bytes should still be written and recorded."""
        out = tmp_path / "changed" / "index.html"
        out.parent.mkdir(parents=True)
        out.write_text("<p>old</p>", encoding="utf-8")
        page = _make_page(output_path=out, rendered_html="<p>new</p>")
        site = _make_site(tmp_path)
        collector = BuildOutputCollector(output_dir=tmp_path)

        write_output(page, site, collector=collector)

        outputs = collector.get_outputs()
        assert len(outputs) == 1
        assert str(outputs[0].path) == "changed/index.html"
        assert out.read_text(encoding="utf-8") == "<p>new</p>"
