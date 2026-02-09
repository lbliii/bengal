"""Tests for RenderingPipeline output_collector integration.

Regression: The pipeline extracted the output collector from BuildContext
using ``not self._output_collector`` which tested *truthiness*.
BuildOutputCollector.__bool__ returns False when empty (always the case
at pipeline init), so every pipeline thought the collector was missing.

The fix changed the check to ``self._output_collector is None``.
These tests verify the collector is correctly extracted and used.
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

    def test_pipeline_no_collector_no_crash(self, tmp_path) -> None:
        """Pipeline with output_collector=None must not raise."""
        pipeline = self._make_pipeline(tmp_path, collector=None)
        assert pipeline._output_collector is None

    def test_pipeline_no_build_context_no_crash(self, tmp_path) -> None:
        """Pipeline with no build_context at all must not raise."""
        site = SimpleNamespace(
            config={},
            root_path=tmp_path,
            output_dir=tmp_path,
        )
        pipeline = RenderingPipeline(site, build_context=None)
        assert pipeline._output_collector is None
