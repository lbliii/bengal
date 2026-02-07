"""
Tests for canonical protocol imports.

Ensures that protocols are importable from the canonical bengal.protocols
location and that isinstance() checks work correctly.

Background:
    Protocols are defined canonically in bengal.protocols:
    - bengal.protocols.Cacheable
    - bengal.protocols.OutputCollector
    - bengal.protocols.ProgressReporter

    Some modules re-export from bengal.protocols for convenience.
"""

from __future__ import annotations

from bengal.protocols import Cacheable, OutputCollector, ProgressReporter


class TestCacheableCanonical:
    """Verify Cacheable protocol works correctly."""

    def test_cacheable_isinstance_works(self) -> None:
        """isinstance() should work for Cacheable protocol."""
        from bengal.core.page.page_core import PageCore

        # PageCore implements Cacheable
        core = PageCore(
            source_path="content/test.md",
            title="Test",
            slug="test",
        )

        assert isinstance(core, Cacheable)

    def test_cacheable_from_bengal_cache_module(self) -> None:
        """bengal.cache.Cacheable should be identical to bengal.protocols.Cacheable."""
        from bengal.cache import Cacheable as CacheFromModule

        assert Cacheable is CacheFromModule, (
            "bengal.cache.Cacheable should re-export from bengal.protocols"
        )


class TestOutputCollectorCanonical:
    """Verify OutputCollector re-exports are identical to canonical."""

    def test_output_collector_reexport_is_canonical(self) -> None:
        """bengal.core.output.collector.OutputCollector should be identical to protocols."""
        from bengal.core.output.collector import OutputCollector as OCLegacy

        assert OutputCollector is OCLegacy, (
            "OutputCollector re-export has diverged from canonical definition!\n"
            "bengal.core.output.collector.OutputCollector must re-export from bengal.protocols."
        )

    def test_output_collector_isinstance_works_across_imports(self) -> None:
        """isinstance() should work regardless of import path."""
        from bengal.core.output.collector import (
            BuildOutputCollector,
        )
        from bengal.core.output.collector import (
            OutputCollector as OCLegacy,
        )

        collector = BuildOutputCollector()

        # Both import paths should recognize it
        assert isinstance(collector, OutputCollector)
        assert isinstance(collector, OCLegacy)


class TestProgressReporterCanonical:
    """Verify ProgressReporter re-exports are identical to canonical."""

    def test_progress_reporter_reexport_is_canonical(self) -> None:
        """bengal.utils.observability.progress.ProgressReporter should be identical to protocols."""
        from bengal.utils.observability.progress import ProgressReporter as PRLegacy

        assert ProgressReporter is PRLegacy, (
            "ProgressReporter re-export has diverged from canonical definition!\n"
            "bengal.utils.observability.progress.ProgressReporter must re-export from bengal.protocols."
        )

    def test_progress_reporter_isinstance_works_across_imports(self) -> None:
        """isinstance() should work regardless of import path."""
        from bengal.utils.observability.progress import (
            NoopReporter,
        )
        from bengal.utils.observability.progress import (
            ProgressReporter as PRLegacy,
        )

        reporter = NoopReporter()

        # Both import paths should recognize it
        assert isinstance(reporter, ProgressReporter)
        assert isinstance(reporter, PRLegacy)

    def test_observability_init_reexport_is_canonical(self) -> None:
        """bengal.utils.observability.ProgressReporter should also be identical."""
        from bengal.utils.observability import ProgressReporter as PRObservability

        assert ProgressReporter is PRObservability, (
            "ProgressReporter re-export from observability.__init__ has diverged!"
        )


class TestNoCircularImports:
    """Verify protocol imports don't cause circular imports."""

    def test_output_collector_import_succeeds(self) -> None:
        """Importing from bengal.core.output.collector should not raise ImportError."""
        from bengal.core.output.collector import OutputCollector

        assert OutputCollector is not None

    def test_progress_import_succeeds(self) -> None:
        """Importing from bengal.utils.observability.progress should not raise ImportError."""
        from bengal.utils.observability.progress import ProgressReporter

        assert ProgressReporter is not None

    def test_protocols_import_succeeds(self) -> None:
        """Importing from bengal.protocols should not raise ImportError."""
        from bengal.protocols import Cacheable, OutputCollector, ProgressReporter

        assert all([Cacheable, OutputCollector, ProgressReporter])
