"""
Template profiling infrastructure for Bengal SSG.

Provides timing instrumentation for template rendering to identify
performance bottlenecks and optimize template code.

Usage:

```bash
# Enable via CLI
bengal build --profile-templates
```

```python
# Access report
report = template_engine.get_template_profile()
```

Architecture:
    TemplateProfiler collects timing data for:
    - Individual template renders (base.html, partials/*.html)
    - Template function calls (get_menu_lang, get_auto_nav, etc.)
    - Include/extends resolution

    Data is thread-safe and aggregated across parallel renders.

See Also:
    - plan/active/rfc-template-performance-optimization.md
    - bengal/rendering/template_engine/core.py
"""

from __future__ import annotations

import threading
import time
from collections import defaultdict
from collections.abc import Callable
from dataclasses import dataclass, field
from functools import wraps
from typing import TYPE_CHECKING, Any, ParamSpec, TypeVar

if TYPE_CHECKING:
    from jinja2 import Template


@dataclass
class TemplateTimings:
    """Timing statistics for a single template."""

    name: str
    render_times: list[float] = field(default_factory=list)

    @property
    def count(self) -> int:
        """Number of times template was rendered."""
        return len(self.render_times)

    @property
    def total_ms(self) -> float:
        """Total render time in milliseconds."""
        return sum(self.render_times) * 1000

    @property
    def avg_ms(self) -> float:
        """Average render time in milliseconds."""
        if not self.render_times:
            return 0.0
        return self.total_ms / len(self.render_times)

    @property
    def min_ms(self) -> float:
        """Minimum render time in milliseconds."""
        if not self.render_times:
            return 0.0
        return min(self.render_times) * 1000

    @property
    def max_ms(self) -> float:
        """Maximum render time in milliseconds."""
        if not self.render_times:
            return 0.0
        return max(self.render_times) * 1000


@dataclass
class FunctionTimings:
    """Timing statistics for a template function."""

    name: str
    call_times: list[float] = field(default_factory=list)

    @property
    def count(self) -> int:
        """Number of times function was called."""
        return len(self.call_times)

    @property
    def total_ms(self) -> float:
        """Total execution time in milliseconds."""
        return sum(self.call_times) * 1000

    @property
    def avg_ms(self) -> float:
        """Average execution time in milliseconds."""
        if not self.call_times:
            return 0.0
        return self.total_ms / len(self.call_times)


class TemplateProfiler:
    """
    Collects and reports template rendering performance data.

    Thread-safe implementation supports parallel builds.

    Example:
        profiler = TemplateProfiler()
        profiler.start_template("base.html")
        # ... render ...
        profiler.end_template("base.html")

        report = profiler.get_report()
    """

    def __init__(self) -> None:
        """Initialize the profiler."""
        self._templates: dict[str, TemplateTimings] = defaultdict(lambda: TemplateTimings(name=""))
        self._functions: dict[str, FunctionTimings] = defaultdict(lambda: FunctionTimings(name=""))
        self._lock = threading.Lock()
        self._active_renders: dict[
            int, dict[str, float]
        ] = {}  # thread_id -> {template: start_time}
        self._enabled = True

    def enable(self) -> None:
        """Enable profiling."""
        self._enabled = True

    def disable(self) -> None:
        """Disable profiling."""
        self._enabled = False

    def is_enabled(self) -> bool:
        """Check if profiling is enabled."""
        return self._enabled

    def start_template(self, template_name: str) -> None:
        """
        Mark start of template render.

        Args:
            template_name: Name of template being rendered
        """
        if not self._enabled:
            return

        thread_id = threading.get_ident()
        with self._lock:
            if thread_id not in self._active_renders:
                self._active_renders[thread_id] = {}
            self._active_renders[thread_id][template_name] = time.perf_counter()

    def end_template(self, template_name: str) -> None:
        """
        Mark end of template render and record timing.

        Args:
            template_name: Name of template that finished rendering
        """
        if not self._enabled:
            return

        end_time = time.perf_counter()
        thread_id = threading.get_ident()

        with self._lock:
            if thread_id in self._active_renders:
                start_time = self._active_renders[thread_id].pop(template_name, None)
                if start_time is not None:
                    duration = end_time - start_time
                    if self._templates[template_name].name == "":
                        self._templates[template_name].name = template_name
                    self._templates[template_name].render_times.append(duration)

    def record_function_call(self, func_name: str, duration: float) -> None:
        """
        Record a template function call timing.

        Args:
            func_name: Name of the function
            duration: Execution time in seconds
        """
        if not self._enabled:
            return

        with self._lock:
            if self._functions[func_name].name == "":
                self._functions[func_name].name = func_name
            self._functions[func_name].call_times.append(duration)

    def get_report(self) -> dict[str, Any]:
        """
        Generate profiling report.

        Returns:
            Dictionary with template and function timing statistics
        """
        with self._lock:
            templates = {}
            for name, timings in self._templates.items():
                if timings.count > 0:
                    templates[name] = {
                        "count": timings.count,
                        "total_ms": round(timings.total_ms, 2),
                        "avg_ms": round(timings.avg_ms, 3),
                        "min_ms": round(timings.min_ms, 3),
                        "max_ms": round(timings.max_ms, 3),
                    }

            functions = {}
            for name, func_timings in self._functions.items():
                if func_timings.count > 0:
                    functions[name] = {
                        "count": func_timings.count,
                        "total_ms": round(func_timings.total_ms, 2),
                        "avg_ms": round(func_timings.avg_ms, 3),
                    }

            # Sort by total time (descending)
            sorted_templates = dict(
                sorted(templates.items(), key=lambda x: x[1]["total_ms"], reverse=True)
            )
            sorted_functions = dict(
                sorted(functions.items(), key=lambda x: x[1]["total_ms"], reverse=True)
            )

            # Calculate totals
            total_template_time = sum(t["total_ms"] for t in templates.values())
            total_function_time = sum(f["total_ms"] for f in functions.values())

            return {
                "templates": sorted_templates,
                "functions": sorted_functions,
                "summary": {
                    "total_template_time_ms": round(total_template_time, 2),
                    "total_function_time_ms": round(total_function_time, 2),
                    "template_count": len(sorted_templates),
                    "function_count": len(sorted_functions),
                    "total_renders": sum(t["count"] for t in templates.values()),
                    "total_calls": sum(f["count"] for f in functions.values()),
                },
            }

    def reset(self) -> None:
        """Clear all collected timing data."""
        with self._lock:
            self._templates.clear()
            self._functions.clear()
            self._active_renders.clear()


P = ParamSpec("P")
R = TypeVar("R")


def profile_function(
    profiler: TemplateProfiler, func_name: str
) -> Callable[[Callable[P, R]], Callable[P, R]]:
    """
    Decorator factory for profiling template functions.

    Args:
        profiler: TemplateProfiler instance
        func_name: Name to record for this function

    Returns:
        Decorator that wraps function with timing

    Example:
        @profile_function(profiler, "get_menu_lang")
        def get_menu_lang(menu_name, lang):
            ...
    """

    def decorator(func: Callable[P, R]) -> Callable[P, R]:
        @wraps(func)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            if not profiler.is_enabled():
                return func(*args, **kwargs)

            start = time.perf_counter()
            try:
                return func(*args, **kwargs)
            finally:
                duration = time.perf_counter() - start
                profiler.record_function_call(func_name, duration)

        return wrapper

    return decorator


class ProfiledTemplate:
    """
    Wrapper around Jinja2 Template that adds render timing.

    Delegates all attribute access to the wrapped template while
    intercepting render() calls for profiling.
    """

    def __init__(self, template: Template, profiler: TemplateProfiler) -> None:
        """
        Initialize the profiled template.

        Args:
            template: Jinja2 Template to wrap
            profiler: TemplateProfiler for recording timings
        """
        self._template = template
        self._profiler = profiler

    def __getattr__(self, name: str) -> Any:
        """Delegate attribute access to wrapped template."""
        return getattr(self._template, name)

    def render(self, *args: Any, **kwargs: Any) -> str:
        """
        Render template with timing instrumentation.

        Args:
            *args: Positional arguments for template.render()
            **kwargs: Keyword arguments for template.render()

        Returns:
            Rendered template string
        """
        template_name = getattr(self._template, "name", "unknown")

        self._profiler.start_template(template_name)
        try:
            return self._template.render(*args, **kwargs)
        finally:
            self._profiler.end_template(template_name)


def format_profile_report(report: dict[str, Any], top_n: int = 20) -> str:
    """
    Format profiling report for CLI output.

    Args:
        report: Profiling report from TemplateProfiler.get_report()
        top_n: Number of top items to show per category

    Returns:
        Formatted report string for display
    """
    lines = []
    summary = report.get("summary", {})

    lines.append("=" * 60)
    lines.append("📊 Template Profiling Report")
    lines.append("=" * 60)
    lines.append("")

    # Summary
    lines.append("Summary:")
    lines.append(f"  Total template time: {summary.get('total_template_time_ms', 0):.2f}ms")
    lines.append(f"  Total function time: {summary.get('total_function_time_ms', 0):.2f}ms")
    lines.append(f"  Templates profiled: {summary.get('template_count', 0)}")
    lines.append(f"  Total renders: {summary.get('total_renders', 0)}")
    lines.append(f"  Functions profiled: {summary.get('function_count', 0)}")
    lines.append(f"  Total function calls: {summary.get('total_calls', 0)}")
    lines.append("")

    # Templates
    templates = report.get("templates", {})
    if templates:
        lines.append("-" * 60)
        lines.append(f"Top {min(top_n, len(templates))} Templates (by total time):")
        lines.append("-" * 60)
        lines.append(f"{'Template':<40} {'Count':>8} {'Total':>10} {'Avg':>8}")
        lines.append(f"{'':<40} {'':>8} {'(ms)':>10} {'(ms)':>8}")
        lines.append("-" * 60)

        for i, (name, stats) in enumerate(templates.items()):
            if i >= top_n:
                break
            # Truncate long names
            display_name = name if len(name) <= 38 else f"...{name[-35:]}"
            lines.append(
                f"{display_name:<40} {stats['count']:>8} "
                f"{stats['total_ms']:>10.2f} {stats['avg_ms']:>8.3f}"
            )
        lines.append("")

    # Functions
    functions = report.get("functions", {})
    if functions:
        lines.append("-" * 60)
        lines.append(f"Top {min(top_n, len(functions))} Template Functions (by total time):")
        lines.append("-" * 60)
        lines.append(f"{'Function':<40} {'Calls':>8} {'Total':>10} {'Avg':>8}")
        lines.append(f"{'':<40} {'':>8} {'(ms)':>10} {'(ms)':>8}")
        lines.append("-" * 60)

        for i, (name, stats) in enumerate(functions.items()):
            if i >= top_n:
                break
            display_name = name if len(name) <= 38 else f"...{name[-35:]}"
            lines.append(
                f"{display_name:<40} {stats['count']:>8} "
                f"{stats['total_ms']:>10.2f} {stats['avg_ms']:>8.3f}"
            )
        lines.append("")

    lines.append("=" * 60)

    return "\n".join(lines)


# Global profiler instance (disabled by default)
_global_profiler: TemplateProfiler | None = None


def get_profiler() -> TemplateProfiler | None:
    """Get the global template profiler instance."""
    return _global_profiler


def enable_profiling() -> TemplateProfiler:
    """
    Enable template profiling globally.

    Returns:
        The global TemplateProfiler instance
    """
    global _global_profiler
    if _global_profiler is None:
        _global_profiler = TemplateProfiler()
    _global_profiler.enable()
    return _global_profiler


def disable_profiling() -> None:
    """Disable template profiling globally."""
    global _global_profiler
    if _global_profiler is not None:
        _global_profiler.disable()
