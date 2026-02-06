"""Unit tests for BuildOutputCollector.

Tests cover:
- Basic recording and retrieval
- CSS-only detection for hot reload
- Thread safety for parallel builds
- Type filtering
- Path relativization
- Validation warnings
"""

from __future__ import annotations

import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest

from bengal.core.output import BuildOutputCollector, OutputRecord, OutputType


class TestOutputRecord:
    """Tests for OutputRecord dataclass."""

    def test_from_path_html(self) -> None:
        """Auto-detect HTML from .html extension."""
        record = OutputRecord.from_path(Path("posts/hello.html"), phase="render")
        assert record.output_type == OutputType.HTML
        assert record.phase == "render"
        assert record.path == Path("posts/hello.html")

    def test_from_path_css(self) -> None:
        """Auto-detect CSS from .css extension."""
        record = OutputRecord.from_path(Path("assets/style.css"), phase="asset")
        assert record.output_type == OutputType.CSS
        assert record.phase == "asset"

    def test_from_path_js(self) -> None:
        """Auto-detect JS from .js and .mjs extensions."""
        record_js = OutputRecord.from_path(Path("scripts/app.js"), phase="asset")
        record_mjs = OutputRecord.from_path(Path("scripts/module.mjs"), phase="asset")
        assert record_js.output_type == OutputType.JS
        assert record_mjs.output_type == OutputType.JS

    def test_from_path_image(self) -> None:
        """Auto-detect IMAGE from image extensions."""
        for ext in [".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp", ".ico"]:
            record = OutputRecord.from_path(Path(f"images/photo{ext}"), phase="asset")
            assert record.output_type == OutputType.IMAGE

    def test_from_path_font(self) -> None:
        """Auto-detect FONT from font extensions."""
        for ext in [".woff", ".woff2", ".ttf", ".otf", ".eot"]:
            record = OutputRecord.from_path(Path(f"fonts/font{ext}"), phase="asset")
            assert record.output_type == OutputType.FONT

    def test_from_path_xml(self) -> None:
        """Auto-detect XML from .xml extension."""
        record = OutputRecord.from_path(Path("sitemap.xml"), phase="postprocess")
        assert record.output_type == OutputType.XML

    def test_from_path_json(self) -> None:
        """Auto-detect JSON from .json extension."""
        record = OutputRecord.from_path(Path("search-index.json"), phase="postprocess")
        assert record.output_type == OutputType.JSON

    def test_from_path_manifest(self) -> None:
        """Auto-detect MANIFEST from .webmanifest extension."""
        record = OutputRecord.from_path(Path("manifest.webmanifest"), phase="postprocess")
        assert record.output_type == OutputType.MANIFEST

    def test_from_path_unknown_defaults_to_asset(self) -> None:
        """Unknown extensions default to ASSET type."""
        record = OutputRecord.from_path(Path("data.bin"), phase="asset")
        assert record.output_type == OutputType.ASSET

    def test_str_representation(self) -> None:
        """String representation includes type and path."""
        record = OutputRecord(Path("style.css"), OutputType.CSS, "asset")
        assert str(record) == "css:style.css"

    def test_immutable(self) -> None:
        """OutputRecord is immutable (frozen)."""
        record = OutputRecord(Path("style.css"), OutputType.CSS, "asset")
        with pytest.raises(AttributeError):
            record.path = Path("other.css")  # type: ignore[misc]


class TestBuildOutputCollector:
    """Tests for BuildOutputCollector implementation."""

    def test_record_and_retrieve(self) -> None:
        """Basic recording and retrieval."""
        collector = BuildOutputCollector()
        collector.record(Path("index.html"), OutputType.HTML, phase="render")
        collector.record(Path("style.css"), OutputType.CSS, phase="asset")

        outputs = collector.get_outputs()
        assert len(outputs) == 2
        assert outputs[0].output_type == OutputType.HTML
        assert outputs[1].output_type == OutputType.CSS

    def test_record_auto_detect_type(self) -> None:
        """Record auto-detects type from extension when not specified."""
        collector = BuildOutputCollector()
        collector.record(Path("main.css"), phase="asset")

        outputs = collector.get_outputs()
        assert len(outputs) == 1
        assert outputs[0].output_type == OutputType.CSS

    def test_css_only_true(self) -> None:
        """css_only() returns True when only CSS files recorded."""
        collector = BuildOutputCollector()
        collector.record(Path("style.css"), OutputType.CSS, phase="asset")
        collector.record(Path("theme.css"), OutputType.CSS, phase="asset")

        assert collector.css_only() is True

    def test_css_only_false_with_mixed(self) -> None:
        """css_only() returns False when mixed types recorded."""
        collector = BuildOutputCollector()
        collector.record(Path("style.css"), OutputType.CSS, phase="asset")
        collector.record(Path("index.html"), OutputType.HTML, phase="render")

        assert collector.css_only() is False

    def test_css_only_false_when_empty(self) -> None:
        """css_only() returns False when no outputs recorded."""
        collector = BuildOutputCollector()
        assert collector.css_only() is False

    def test_filter_by_type(self) -> None:
        """get_outputs() filters by output type."""
        collector = BuildOutputCollector()
        collector.record(Path("index.html"), OutputType.HTML, phase="render")
        collector.record(Path("about.html"), OutputType.HTML, phase="render")
        collector.record(Path("style.css"), OutputType.CSS, phase="asset")

        html_outputs = collector.get_outputs(OutputType.HTML)
        css_outputs = collector.get_outputs(OutputType.CSS)

        assert len(html_outputs) == 2
        assert len(css_outputs) == 1
        assert all(o.output_type == OutputType.HTML for o in html_outputs)
        assert all(o.output_type == OutputType.CSS for o in css_outputs)

    def test_get_relative_paths(self) -> None:
        """get_relative_paths() returns path strings."""
        collector = BuildOutputCollector()
        collector.record(Path("posts/hello.html"), OutputType.HTML, phase="render")
        collector.record(Path("style.css"), OutputType.CSS, phase="asset")

        paths = collector.get_relative_paths()
        assert paths == ["posts/hello.html", "style.css"]

    def test_get_relative_paths_filtered(self) -> None:
        """get_relative_paths() filters by type."""
        collector = BuildOutputCollector()
        collector.record(Path("index.html"), OutputType.HTML, phase="render")
        collector.record(Path("style.css"), OutputType.CSS, phase="asset")

        css_paths = collector.get_relative_paths(OutputType.CSS)
        assert css_paths == ["style.css"]

    def test_relative_path_conversion(self) -> None:
        """Absolute paths are converted to relative when output_dir provided."""
        output_dir = Path("/site/public")
        collector = BuildOutputCollector(output_dir)
        collector.record(Path("/site/public/posts/hello.html"), OutputType.HTML, phase="render")

        outputs = collector.get_outputs()
        assert outputs[0].path == Path("posts/hello.html")

    def test_absolute_path_outside_output_dir_kept(self) -> None:
        """Absolute paths outside output_dir are kept as-is."""
        output_dir = Path("/site/public")
        collector = BuildOutputCollector(output_dir)
        collector.record(Path("/other/path/file.html"), OutputType.HTML, phase="render")

        outputs = collector.get_outputs()
        assert outputs[0].path == Path("/other/path/file.html")

    def test_clear(self) -> None:
        """clear() removes all recorded outputs."""
        collector = BuildOutputCollector()
        collector.record(Path("index.html"), OutputType.HTML, phase="render")
        collector.record(Path("style.css"), OutputType.CSS, phase="asset")

        collector.clear()
        assert len(collector) == 0
        assert collector.get_outputs() == []

    def test_len(self) -> None:
        """__len__ returns count of recorded outputs."""
        collector = BuildOutputCollector()
        assert len(collector) == 0

        collector.record(Path("index.html"), OutputType.HTML, phase="render")
        assert len(collector) == 1

        collector.record(Path("style.css"), OutputType.CSS, phase="asset")
        assert len(collector) == 2

    def test_bool(self) -> None:
        """__bool__ returns True when outputs recorded."""
        collector = BuildOutputCollector()
        assert not collector

        collector.record(Path("index.html"), OutputType.HTML, phase="render")
        assert collector

    def test_thread_safety(self) -> None:
        """Concurrent recording from multiple threads is safe."""
        collector = BuildOutputCollector()
        num_threads = 10
        records_per_thread = 100

        def record_outputs(thread_id: int) -> None:
            for i in range(records_per_thread):
                collector.record(
                    Path(f"thread{thread_id}/page{i}.html"),
                    OutputType.HTML,
                    phase="render",
                )

        with ThreadPoolExecutor(max_workers=num_threads) as executor:
            futures = [executor.submit(record_outputs, i) for i in range(num_threads)]
            for future in futures:
                future.result()

        assert len(collector) == num_threads * records_per_thread

    def test_thread_safety_mixed_operations(self) -> None:
        """Concurrent mixed operations (record, get_outputs, css_only) are safe."""
        collector = BuildOutputCollector()
        errors: list[Exception] = []
        barrier = threading.Barrier(3)

        def writer() -> None:
            barrier.wait()
            try:
                for i in range(50):
                    collector.record(Path(f"page{i}.html"), OutputType.HTML, phase="render")
                    collector.record(Path(f"style{i}.css"), OutputType.CSS, phase="asset")
            except Exception as e:
                errors.append(e)

        def reader() -> None:
            barrier.wait()
            try:
                for _ in range(50):
                    _ = collector.get_outputs()
                    _ = collector.css_only()
                    _ = len(collector)
            except Exception as e:
                errors.append(e)

        threads = [
            threading.Thread(target=writer),
            threading.Thread(target=reader),
            threading.Thread(target=reader),
        ]

        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=10)

        assert not errors, f"Errors during concurrent access: {errors}"

    def test_validate_warns_on_empty(self) -> None:
        """validate() emits warning when sources changed but no outputs recorded."""
        from bengal.core.diagnostics import DiagnosticsCollector

        collector = BuildOutputCollector()
        diagnostics = DiagnosticsCollector()
        collector._diagnostics = diagnostics
        collector.validate(changed_sources=["content/post.md"])

        events = diagnostics.drain()
        assert len(events) == 1
        assert events[0].code == "output_tracking_empty"
        assert events[0].level == "warning"

    def test_validate_no_warn_when_outputs_exist(self) -> None:
        """validate() does not warn when outputs recorded."""
        from bengal.core.diagnostics import DiagnosticsCollector

        collector = BuildOutputCollector()
        diagnostics = DiagnosticsCollector()
        collector._diagnostics = diagnostics
        collector.record(Path("index.html"), OutputType.HTML, phase="render")
        collector.validate(changed_sources=["content/post.md"])

        events = diagnostics.drain()
        assert len(events) == 0

    def test_validate_no_warn_when_no_sources(self) -> None:
        """validate() does not warn when no sources changed."""
        from bengal.core.diagnostics import DiagnosticsCollector

        collector = BuildOutputCollector()
        diagnostics = DiagnosticsCollector()
        collector._diagnostics = diagnostics
        collector.validate(changed_sources=None)
        collector.validate(changed_sources=[])

        events = diagnostics.drain()
        assert len(events) == 0


class TestOutputCollectorProtocol:
    """Tests for OutputCollector protocol conformance."""

    def test_build_output_collector_implements_protocol(self) -> None:
        """BuildOutputCollector implements OutputCollector protocol."""
        from bengal.core.output import OutputCollector

        collector = BuildOutputCollector()
        assert isinstance(collector, OutputCollector)
