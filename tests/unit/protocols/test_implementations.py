"""
Tests for protocol implementation compliance.

Verifies that concrete classes correctly implement their protocols.
Uses isinstance() checks (enabled by @runtime_checkable) and method
signature verification.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from bengal.protocols import (
    Cacheable,
    HighlightService,
    OutputCollector,
    ProgressReporter,
)


class TestProgressReporterImplementations:
    """Verify ProgressReporter implementations."""

    def test_noop_reporter_satisfies_protocol(self) -> None:
        """NoopReporter must satisfy ProgressReporter protocol."""
        from bengal.utils.observability.progress import NoopReporter
        
        reporter = NoopReporter()
        
        # Runtime protocol check
        assert isinstance(reporter, ProgressReporter), (
            "NoopReporter does not satisfy ProgressReporter protocol"
        )

    def test_noop_reporter_methods_are_callable(self) -> None:
        """NoopReporter methods should be callable without error."""
        from bengal.utils.observability.progress import NoopReporter
        
        reporter = NoopReporter()
        
        # All methods should be callable (no-ops, but shouldn't raise)
        reporter.add_phase("test", "Test Phase", total=10)
        reporter.start_phase("test")
        reporter.update_phase("test", current=5, current_item="item.md")
        reporter.complete_phase("test", elapsed_ms=100.0)
        reporter.log("Test message")

    def test_live_progress_adapter_satisfies_protocol(self) -> None:
        """LiveProgressReporterAdapter must satisfy ProgressReporter protocol."""
        from bengal.utils.observability.progress import LiveProgressReporterAdapter
        
        # Create a mock progress manager
        class MockProgressManager:
            def add_phase(self, phase_id, label, total=None): pass
            def start_phase(self, phase_id): pass
            def update_phase(self, phase_id, **kwargs): pass
            def complete_phase(self, phase_id, elapsed_ms=None): pass
        
        adapter = LiveProgressReporterAdapter(MockProgressManager())
        
        # Runtime protocol check
        assert isinstance(adapter, ProgressReporter), (
            "LiveProgressReporterAdapter does not satisfy ProgressReporter protocol"
        )


class TestOutputCollectorImplementations:
    """Verify OutputCollector implementations."""

    def test_build_output_collector_satisfies_protocol(self) -> None:
        """BuildOutputCollector must satisfy OutputCollector protocol."""
        from bengal.core.output.collector import BuildOutputCollector
        
        collector = BuildOutputCollector()
        
        # Runtime protocol check
        assert isinstance(collector, OutputCollector), (
            "BuildOutputCollector does not satisfy OutputCollector protocol"
        )

    def test_build_output_collector_methods_work(self) -> None:
        """BuildOutputCollector methods should work correctly."""
        from bengal.core.output.collector import BuildOutputCollector
        from bengal.core.output.types import OutputType
        
        collector = BuildOutputCollector()
        
        # Record some outputs
        collector.record(Path("test.html"), OutputType.HTML, "render")
        collector.record(Path("style.css"), OutputType.CSS, "asset")
        
        # Verify retrieval
        outputs = collector.get_outputs()
        assert len(outputs) == 2
        
        # Verify filtering
        html_outputs = collector.get_outputs(OutputType.HTML)
        assert len(html_outputs) == 1
        
        # Verify css_only
        assert not collector.css_only()
        
        # Verify clear
        collector.clear()
        assert len(collector.get_outputs()) == 0


class TestCacheableImplementations:
    """Verify Cacheable implementations."""

    def test_page_core_satisfies_cacheable(self) -> None:
        """PageCore must satisfy Cacheable protocol."""
        from bengal.core.page.page_core import PageCore
        
        core = PageCore(
            source_path="content/test.md",
            title="Test",
            slug="test",
        )
        
        # Runtime protocol check
        assert isinstance(core, Cacheable), (
            "PageCore does not satisfy Cacheable protocol"
        )

    def test_page_core_roundtrip(self) -> None:
        """PageCore should serialize and deserialize correctly."""
        from datetime import datetime, UTC
        from bengal.core.page.page_core import PageCore
        
        original = PageCore(
            source_path="content/blog/test.md",
            title="Test Post",
            slug="test-post",
            date=datetime(2024, 1, 15, 12, 0, 0, tzinfo=UTC),
            weight=10,
            tags=["python", "testing"],
        )
        
        # Serialize
        data = original.to_cache_dict()
        assert isinstance(data, dict)
        
        # Deserialize
        restored = PageCore.from_cache_dict(data)
        
        # Verify equality
        assert restored.source_path == original.source_path
        assert restored.title == original.title
        assert restored.slug == original.slug
        assert restored.date == original.date
        assert restored.weight == original.weight
        assert restored.tags == original.tags


class TestHighlightServiceImplementations:
    """Verify HighlightService implementations."""

    def test_rosettes_backend_satisfies_protocol(self) -> None:
        """RosettesBackend must satisfy HighlightService protocol."""
        from bengal.rendering.highlighting.rosettes import RosettesBackend
        
        backend = RosettesBackend()
        
        # Runtime protocol check
        assert isinstance(backend, HighlightService), (
            "RosettesBackend does not satisfy HighlightService protocol"
        )

    def test_rosettes_backend_properties(self) -> None:
        """RosettesBackend should have correct name property."""
        from bengal.rendering.highlighting.rosettes import RosettesBackend
        
        backend = RosettesBackend()
        assert backend.name == "rosettes"

    def test_rosettes_backend_highlight_works(self) -> None:
        """RosettesBackend.highlight should return HTML."""
        from bengal.rendering.highlighting.rosettes import RosettesBackend
        
        backend = RosettesBackend()
        result = backend.highlight("print('hello')", "python")
        
        assert isinstance(result, str)
        assert len(result) > 0
        # Should contain some HTML markup
        assert "<" in result

    def test_rosettes_backend_supports_language(self) -> None:
        """RosettesBackend.supports_language should work."""
        from bengal.rendering.highlighting.rosettes import RosettesBackend
        
        backend = RosettesBackend()
        
        # Common languages should be supported
        assert backend.supports_language("python")
        assert backend.supports_language("javascript")
        assert backend.supports_language("rust")
        
        # Made-up language should not be supported
        assert not backend.supports_language("notareallanguage123")


class TestProtocolMethodSignatures:
    """Verify implementations have correct method signatures."""

    def test_progress_reporter_method_accepts_optional_args(self) -> None:
        """ProgressReporter methods should accept optional arguments."""
        from bengal.utils.observability.progress import NoopReporter
        
        reporter = NoopReporter()
        
        # add_phase: total is optional
        reporter.add_phase("phase1", "Phase 1")
        reporter.add_phase("phase2", "Phase 2", total=100)
        
        # update_phase: current and current_item are optional
        reporter.update_phase("phase1")
        reporter.update_phase("phase1", current=5)
        reporter.update_phase("phase1", current_item="file.md")
        reporter.update_phase("phase1", current=5, current_item="file.md")
        
        # complete_phase: elapsed_ms is optional
        reporter.complete_phase("phase1")
        reporter.complete_phase("phase2", elapsed_ms=1234.5)

    def test_output_collector_record_accepts_optional_args(self) -> None:
        """OutputCollector.record should accept optional arguments."""
        from bengal.core.output.collector import BuildOutputCollector
        from bengal.core.output.types import OutputType
        
        collector = BuildOutputCollector()
        
        # output_type is optional (auto-detected from extension)
        collector.record(Path("test.html"))
        
        # phase has a default value
        collector.record(Path("test.css"), OutputType.CSS)
        
        # All args provided
        collector.record(Path("test.js"), OutputType.JS, "asset")
