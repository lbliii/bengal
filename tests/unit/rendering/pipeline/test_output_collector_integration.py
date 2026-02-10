"""Tests for RenderingPipeline output_collector integration.

Verifies that the pipeline correctly extracts the output collector from
BuildContext and falls back to NULL_COLLECTOR (no-op sentinel) when one
is not provided. This eliminates None-guards in all downstream consumers.

Key invariant: ``pipeline._output_collector`` is *never* None.
It is either the real BuildOutputCollector or the NULL_COLLECTOR sentinel.
"""

from __future__ import annotations

from types import SimpleNamespace

from bengal.core.output import BuildOutputCollector
from bengal.rendering.pipeline import RenderingPipeline


# ---------------------------------------------------------------------------
# Lightweight stubs (same pattern as test_pipeline_injection.py)
# ---------------------------------------------------------------------------

class _DummyParser:
    def __init__(self) -> None:
        self.enabled: dict[str, bool] = {}

    def enable_cross_references(self, xref_index: object) -> None:
        self.enabled["xref"] = True

    def parse(self, content: str, metadata: dict) -> str:  # noqa: ARG002
        return content


class _DummyTemplateEngine:
    def __init__(self, site: object) -> None:
        self.site = site
        self.env = SimpleNamespace()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestPipelineOutputCollector:
    """Verify RenderingPipeline correctly extracts and uses output_collector."""

    def _make_pipeline(
        self,
        tmp_path: object,
        collector: BuildOutputCollector | None = None,
    ) -> RenderingPipeline:
        """Create a minimal pipeline with an optional collector."""
        site = SimpleNamespace(
            config={},
            root_path=tmp_path,
            output_dir=tmp_path,
        )
        ctx = SimpleNamespace(
            markdown_parser=_DummyParser(),
            template_engine=_DummyTemplateEngine(site),
            output_collector=collector,
        )
        return RenderingPipeline(site, build_context=ctx)

    def test_pipeline_extracts_collector_from_build_context(self, tmp_path) -> None:
        """Empty collector must be detected (is not None), not discarded."""
        collector = BuildOutputCollector()
        # Sanity: the collector is falsy when empty
        assert not collector

        pipeline = self._make_pipeline(tmp_path, collector=collector)

        # The pipeline must retain the actual collector object
        assert pipeline._output_collector is not None
        assert pipeline._output_collector is collector

    def test_pipeline_no_collector_falls_back_to_null(self, tmp_path) -> None:
        """Pipeline with output_collector=None must use NULL_COLLECTOR sentinel."""
        from bengal.core.output.collector import NullOutputCollector

        pipeline = self._make_pipeline(tmp_path, collector=None)
        assert isinstance(pipeline._output_collector, NullOutputCollector)

    def test_pipeline_no_build_context_falls_back_to_null(self, tmp_path) -> None:
        """Pipeline with no build_context at all must use NULL_COLLECTOR sentinel."""
        from bengal.core.output.collector import NullOutputCollector

        # Construct pipeline with build_context=None to exercise the fallback
        site = SimpleNamespace(
            config={},
            root_path=tmp_path,
            output_dir=tmp_path,
        )
        pipeline = RenderingPipeline(site, build_context=None)
        assert isinstance(pipeline._output_collector, NullOutputCollector)
