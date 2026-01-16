"""
Tests for canonical protocol imports.

Ensures that backwards-compatible re-exports point to the same objects
as the canonical bengal.protocols definitions. This prevents subtle bugs
where isinstance() checks fail because two different class objects exist.

Background:
    Before consolidation, protocols were defined in multiple places:
    - bengal.cache.cacheable.Cacheable (duplicate)
    - bengal.core.output.collector.OutputCollector (duplicate)
    - bengal.utils.observability.progress.ProgressReporter (duplicate)
    
    These now re-export from bengal.protocols to ensure identity.
"""

from __future__ import annotations

import pytest

from bengal.protocols import Cacheable, OutputCollector, ProgressReporter


class TestCacheableCanonical:
    """Verify Cacheable re-exports are identical to canonical."""

    def test_cacheable_reexport_is_canonical(self) -> None:
        """bengal.cache.cacheable.Cacheable should be identical to bengal.protocols.Cacheable."""
        from bengal.cache.cacheable import Cacheable as CacheableLegacy
        
        assert Cacheable is CacheableLegacy, (
            "Cacheable re-export has diverged from canonical definition!\n"
            "bengal.cache.cacheable.Cacheable must re-export from bengal.protocols."
        )

    def test_cacheable_isinstance_works_across_imports(self) -> None:
        """isinstance() should work regardless of import path."""
        from bengal.cache.cacheable import Cacheable as CacheableLegacy
        from bengal.core.page.page_core import PageCore
        
        # PageCore implements Cacheable
        core = PageCore(
            source_path="content/test.md",
            title="Test",
            slug="test",
        )
        
        # Both import paths should recognize it
        assert isinstance(core, Cacheable)
        assert isinstance(core, CacheableLegacy)


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
    """Verify re-export modules don't cause circular imports."""

    def test_cache_cacheable_import_succeeds(self) -> None:
        """Importing from bengal.cache.cacheable should not raise ImportError."""
        # This would fail if there's a circular import
        from bengal.cache.cacheable import Cacheable
        assert Cacheable is not None

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
