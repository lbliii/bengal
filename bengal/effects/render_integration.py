"""
Effect recording integration for the rendering pipeline.

RFC: Snapshot-Enabled v2 Opportunities (Opportunity 1)

Provides integration between the Effect system and the existing
RenderingPipeline. Uses a context manager pattern for clean
integration without major refactoring.

This is opt-in via config:
    build:
      effect_tracing: true  # Enable effect recording
"""

import threading
from contextvars import ContextVar
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any

from bengal.effects.effect import Effect
from bengal.effects.tracer import EffectTracer
from bengal.effects.utils import frozenset_or_none

if TYPE_CHECKING:
    from bengal.core.page import Page


# Thread-local storage for effect context
_current_effect_context: ContextVar[EffectContext | None] = ContextVar(
    "current_effect_context",
    default=None,
)


@dataclass
class EffectContext:
    """
    Context for recording effects during page rendering.

    Tracks dependencies as they're accessed during rendering,
    then creates an Effect at the end.
    """

    # Page being rendered
    source_path: Path
    output_path: Path
    page_href: str
    template_name: str

    # Dependencies accumulated during render
    template_includes: set[str] = field(default_factory=set)
    data_files: set[Path] = field(default_factory=set)
    cascade_sources: set[Path] = field(default_factory=set)

    # Additional dependencies discovered during render
    extra_deps: set[Path | str] = field(default_factory=set)


def get_current_effect_context() -> EffectContext | None:
    """Get the current effect context (if any)."""
    return _current_effect_context.get()


def record_template_include(template_name: str) -> None:
    """
    Record a template include/extend during rendering.

    Call this from template engine when a template is included.
    """
    ctx = _current_effect_context.get()
    if ctx:
        ctx.template_includes.add(template_name)


def record_data_file_access(data_path: Path) -> None:
    """
    Record data file access during rendering.

    Call this from data loading code when a file is accessed.
    """
    ctx = _current_effect_context.get()
    if ctx:
        ctx.data_files.add(data_path)


def record_cascade_source(cascade_path: Path) -> None:
    """
    Record a cascade source (_index.md that cascades to this page).

    Call this from cascade processing code.
    """
    ctx = _current_effect_context.get()
    if ctx:
        ctx.cascade_sources.add(cascade_path)


def record_extra_dependency(dep: Path | str) -> None:
    """
    Record an additional dependency during rendering.

    Generic hook for any dependency type.
    """
    ctx = _current_effect_context.get()
    if ctx:
        ctx.extra_deps.add(dep)


class RenderEffectRecorder:
    """
    Context manager for recording effects during page rendering.

    Usage:
        >>> tracer = EffectTracer()
        >>> with RenderEffectRecorder(tracer, page) as recorder:
        ...     # Render page
        ...     html = render(page)
        >>> # Effect automatically recorded to tracer
    """

    def __init__(
        self,
        tracer: EffectTracer,
        page: Page,
        template_name: str,
    ) -> None:
        """
        Initialize recorder.

        Args:
            tracer: EffectTracer to record to
            page: Page being rendered
            template_name: Template used for rendering
        """
        self._tracer = tracer
        self._page = page
        self._template_name = template_name
        self._context: EffectContext | None = None
        self._token: Any = None

    def __enter__(self) -> RenderEffectRecorder:
        """Start recording effects."""
        self._context = EffectContext(
            source_path=self._page.source_path,
            output_path=self._page.output_path or Path(f"unknown_{self._page.title}"),
            page_href=self._page.href or "/",
            template_name=self._template_name,
        )
        self._token = _current_effect_context.set(self._context)
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> bool:
        """Stop recording and create effect."""
        if self._token is not None:
            _current_effect_context.reset(self._token)

        # Only record if no exception
        if exc_type is None and self._context is not None:
            effect = Effect.for_page_render(
                source_path=self._context.source_path,
                output_path=self._context.output_path,
                template_name=self._context.template_name,
                template_includes=frozenset(self._context.template_includes),
                page_href=self._context.page_href,
                cascade_sources=frozenset_or_none(self._context.cascade_sources),
                data_files=frozenset_or_none(self._context.data_files),
            )

            # Add extra deps
            if self._context.extra_deps:
                effect = Effect(
                    outputs=effect.outputs,
                    depends_on=effect.depends_on | frozenset(self._context.extra_deps),
                    invalidates=effect.invalidates,
                    operation=effect.operation,
                    metadata=effect.metadata,
                )

            self._tracer.record(effect)

        return False  # Don't suppress exceptions


class BuildEffectTracer:
    """
    Global effect tracer for a build.

    Singleton-ish per build. Stores effects for post-build analysis
    and incremental build planning.

    Thread-safe: Uses lock for effect storage.
    """

    _instance: BuildEffectTracer | None = None
    _lock = threading.Lock()

    def __init__(self) -> None:
        """Initialize tracer."""
        self._tracer = EffectTracer()
        self._enabled = False

    @classmethod
    def get_instance(cls) -> BuildEffectTracer:
        """Get or create the singleton instance."""
        with cls._lock:
            if cls._instance is None:
                cls._instance = cls()
            return cls._instance

    @classmethod
    def reset(cls) -> None:
        """Reset singleton (for testing)."""
        with cls._lock:
            cls._instance = None

    @property
    def tracer(self) -> EffectTracer:
        """Get the underlying tracer."""
        return self._tracer

    @property
    def enabled(self) -> bool:
        """Check if effect tracing is enabled."""
        return self._enabled

    def enable(self) -> None:
        """Enable effect tracing."""
        self._enabled = True

    def disable(self) -> None:
        """Disable effect tracing."""
        self._enabled = False

    def record_page_render(self, page: Page, template_name: str) -> RenderEffectRecorder | None:
        """
        Get recorder for page rendering (if enabled).

        Args:
            page: Page being rendered
            template_name: Template name

        Returns:
            RenderEffectRecorder if enabled, None otherwise
        """
        if not self._enabled:
            return None
        return RenderEffectRecorder(self._tracer, page, template_name)

    def get_effects(self) -> list[Effect]:
        """Get all recorded effects."""
        return self._tracer.effects

    def get_statistics(self) -> dict[str, Any]:
        """Get effect statistics."""
        return self._tracer.get_statistics()

    def clear(self) -> None:
        """Clear all effects."""
        self._tracer.clear()


def enable_effect_tracing_from_config(config: dict[str, Any]) -> bool:
    """
    Enable effect tracing based on config.

    Args:
        config: Site config dict

    Returns:
        True if effect tracing was enabled
    """
    build_config = config.get("build", {})
    if isinstance(build_config, dict) and build_config.get("effect_tracing"):
        BuildEffectTracer.get_instance().enable()
        return True
    return False
