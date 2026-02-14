"""
Unit tests for render_integration module.
"""

from dataclasses import dataclass
from pathlib import Path

import pytest

from bengal.effects.render_integration import (
    BuildEffectTracer,
    EffectContext,
    RenderEffectRecorder,
    enable_effect_tracing_from_config,
    get_current_effect_context,
    record_cascade_source,
    record_data_file_access,
    record_extra_dependency,
    record_template_include,
)
from bengal.effects.tracer import EffectTracer


@dataclass
class MockPage:
    """Mock Page for testing."""

    source_path: Path
    output_path: Path | None
    href: str | None
    title: str


class TestEffectContext:
    """Tests for EffectContext dataclass."""

    def test_create_context(self) -> None:
        """EffectContext can be created with required fields."""
        ctx = EffectContext(
            source_path=Path("content/page.md"),
            output_path=Path("public/page/index.html"),
            page_href="/page/",
            template_name="page.html",
        )
        assert ctx.source_path == Path("content/page.md")
        assert ctx.output_path == Path("public/page/index.html")
        assert ctx.page_href == "/page/"
        assert ctx.template_name == "page.html"

    def test_default_collections_empty(self) -> None:
        """Default collections are empty sets."""
        ctx = EffectContext(
            source_path=Path("a.md"),
            output_path=Path("a.html"),
            page_href="/a/",
            template_name="t.html",
        )
        assert ctx.template_includes == set()
        assert ctx.data_files == set()
        assert ctx.cascade_sources == set()
        assert ctx.extra_deps == set()


class TestRecordFunctions:
    """Tests for record_* helper functions."""

    def test_record_template_include_no_context(self) -> None:
        """record_template_include does nothing without context."""
        # Should not raise
        record_template_include("base.html")

    def test_record_data_file_access_no_context(self) -> None:
        """record_data_file_access does nothing without context."""
        # Should not raise
        record_data_file_access(Path("data/site.yaml"))

    def test_record_cascade_source_no_context(self) -> None:
        """record_cascade_source does nothing without context."""
        # Should not raise
        record_cascade_source(Path("content/_index.md"))

    def test_record_extra_dependency_no_context(self) -> None:
        """record_extra_dependency does nothing without context."""
        # Should not raise
        record_extra_dependency(Path("extra.md"))
        record_extra_dependency("string_dep")


class TestRenderEffectRecorder:
    """Tests for RenderEffectRecorder context manager."""

    def test_context_manager_basic(self) -> None:
        """RenderEffectRecorder works as context manager."""
        tracer = EffectTracer()
        page = MockPage(
            source_path=Path("content/page.md"),
            output_path=Path("public/page/index.html"),
            href="/page/",
            title="Test Page",
        )

        with RenderEffectRecorder(tracer, page, "page.html") as recorder:  # type: ignore[arg-type]
            assert recorder is not None

        # Effect should be recorded
        assert len(tracer.effects) == 1
        effect = tracer.effects[0]
        assert Path("public/page/index.html") in effect.outputs
        assert Path("content/page.md") in effect.depends_on

    def test_context_sets_and_resets(self) -> None:
        """Context is set during recording and reset after."""
        tracer = EffectTracer()
        page = MockPage(
            source_path=Path("content/page.md"),
            output_path=Path("public/page/index.html"),
            href="/page/",
            title="Test",
        )

        assert get_current_effect_context() is None

        with RenderEffectRecorder(tracer, page, "page.html"):  # type: ignore[arg-type]
            ctx = get_current_effect_context()
            assert ctx is not None
            assert ctx.source_path == Path("content/page.md")

        assert get_current_effect_context() is None

    def test_record_functions_work_in_context(self) -> None:
        """record_* functions accumulate dependencies in context."""
        tracer = EffectTracer()
        page = MockPage(
            source_path=Path("content/page.md"),
            output_path=Path("public/page/index.html"),
            href="/page/",
            title="Test",
        )

        with RenderEffectRecorder(tracer, page, "page.html"):  # type: ignore[arg-type]
            record_template_include("base.html")
            record_template_include("partials/nav.html")
            record_data_file_access(Path("data/site.yaml"))
            record_cascade_source(Path("content/_index.md"))
            record_extra_dependency("custom_dep")

        effect = tracer.effects[0]
        assert "base.html" in effect.depends_on
        assert "partials/nav.html" in effect.depends_on
        # Note: data_files and cascade_sources are converted to frozenset_or_none
        # which returns None if empty after the context manager processes them

    def test_exception_does_not_record_effect(self) -> None:
        """Exception during rendering prevents effect recording."""
        tracer = EffectTracer()
        page = MockPage(
            source_path=Path("content/page.md"),
            output_path=Path("public/page/index.html"),
            href="/page/",
            title="Test",
        )

        with (
            pytest.raises(ValueError, match="Render failed"),
            RenderEffectRecorder(
                tracer,
                page,
                "page.html",  # type: ignore[arg-type]
            ),
        ):
            raise ValueError("Render failed")

        # No effect should be recorded
        assert len(tracer.effects) == 0

    def test_handles_missing_output_path(self) -> None:
        """Recorder handles page with no output_path."""
        tracer = EffectTracer()
        page = MockPage(
            source_path=Path("content/page.md"),
            output_path=None,
            href="/page/",
            title="Test",
        )

        with RenderEffectRecorder(tracer, page, "page.html"):  # type: ignore[arg-type]
            pass

        # Should still record, with fallback output path
        assert len(tracer.effects) == 1

    def test_handles_missing_href(self) -> None:
        """Recorder handles page with no href."""
        tracer = EffectTracer()
        page = MockPage(
            source_path=Path("content/page.md"),
            output_path=Path("public/page/index.html"),
            href=None,
            title="Test",
        )

        with RenderEffectRecorder(tracer, page, "page.html"):  # type: ignore[arg-type]
            pass

        assert len(tracer.effects) == 1
        effect = tracer.effects[0]
        assert "page:/" in effect.invalidates  # Falls back to "/"


class TestBuildEffectTracer:
    """Tests for BuildEffectTracer singleton."""

    def setup_method(self) -> None:
        """Reset singleton before each test."""
        BuildEffectTracer.reset()

    def teardown_method(self) -> None:
        """Reset singleton after each test."""
        BuildEffectTracer.reset()

    def test_get_instance_returns_same_instance(self) -> None:
        """get_instance returns the same singleton."""
        instance1 = BuildEffectTracer.get_instance()
        instance2 = BuildEffectTracer.get_instance()
        assert instance1 is instance2

    def test_reset_clears_singleton(self) -> None:
        """reset() creates new singleton on next call."""
        instance1 = BuildEffectTracer.get_instance()
        BuildEffectTracer.reset()
        instance2 = BuildEffectTracer.get_instance()
        assert instance1 is not instance2

    def test_disabled_by_default(self) -> None:
        """Tracing is disabled by default."""
        tracer = BuildEffectTracer.get_instance()
        assert tracer.enabled is False

    def test_enable_disable(self) -> None:
        """enable() and disable() work correctly."""
        tracer = BuildEffectTracer.get_instance()
        assert tracer.enabled is False

        tracer.enable()
        assert tracer.enabled is True

        tracer.disable()
        assert tracer.enabled is False

    def test_record_page_render_returns_none_when_disabled(self) -> None:
        """record_page_render returns None when disabled."""
        tracer = BuildEffectTracer.get_instance()
        page = MockPage(
            source_path=Path("a.md"),
            output_path=Path("a.html"),
            href="/a/",
            title="A",
        )

        result = tracer.record_page_render(page, "page.html")  # type: ignore[arg-type]
        assert result is None

    def test_record_page_render_returns_recorder_when_enabled(self) -> None:
        """record_page_render returns recorder when enabled."""
        tracer = BuildEffectTracer.get_instance()
        tracer.enable()
        page = MockPage(
            source_path=Path("a.md"),
            output_path=Path("a.html"),
            href="/a/",
            title="A",
        )

        result = tracer.record_page_render(page, "page.html")  # type: ignore[arg-type]
        assert result is not None
        assert isinstance(result, RenderEffectRecorder)

    def test_get_effects_returns_list(self) -> None:
        """get_effects returns list of recorded effects."""
        tracer = BuildEffectTracer.get_instance()
        assert tracer.get_effects() == []

    def test_get_statistics_returns_dict(self) -> None:
        """get_statistics returns statistics dict."""
        tracer = BuildEffectTracer.get_instance()
        stats = tracer.get_statistics()
        assert isinstance(stats, dict)
        assert "total_effects" in stats

    def test_clear_removes_effects(self) -> None:
        """clear() removes all recorded effects."""
        tracer = BuildEffectTracer.get_instance()
        tracer.enable()

        page = MockPage(
            source_path=Path("a.md"),
            output_path=Path("a.html"),
            href="/a/",
            title="A",
        )

        recorder = tracer.record_page_render(page, "page.html")  # type: ignore[arg-type]
        if recorder:
            with recorder:
                pass

        assert len(tracer.get_effects()) == 1

        tracer.clear()
        assert len(tracer.get_effects()) == 0


class TestEnableEffectTracingFromConfig:
    """Tests for enable_effect_tracing_from_config function."""

    def setup_method(self) -> None:
        """Reset singleton before each test."""
        BuildEffectTracer.reset()

    def teardown_method(self) -> None:
        """Reset singleton after each test."""
        BuildEffectTracer.reset()

    def test_enables_when_config_true(self) -> None:
        """Enables tracing when build.effect_tracing is true."""
        config = {"build": {"effect_tracing": True}}
        result = enable_effect_tracing_from_config(config)

        assert result is True
        assert BuildEffectTracer.get_instance().enabled is True

    def test_does_not_enable_when_config_false(self) -> None:
        """Does not enable tracing when build.effect_tracing is false."""
        config = {"build": {"effect_tracing": False}}
        result = enable_effect_tracing_from_config(config)

        assert result is False
        assert BuildEffectTracer.get_instance().enabled is False

    def test_does_not_enable_when_missing(self) -> None:
        """Does not enable tracing when config key is missing."""
        config = {"build": {}}
        result = enable_effect_tracing_from_config(config)

        assert result is False
        assert BuildEffectTracer.get_instance().enabled is False

    def test_handles_empty_config(self) -> None:
        """Handles empty config gracefully."""
        config: dict = {}
        result = enable_effect_tracing_from_config(config)

        assert result is False

    def test_handles_non_dict_build(self) -> None:
        """Handles non-dict build config gracefully."""
        config = {"build": "not a dict"}
        result = enable_effect_tracing_from_config(config)

        assert result is False
