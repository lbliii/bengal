"""
Benchmark: ContextVar Config Pattern for Parser/Renderer

Validates the slot reduction impact discovered in Patitas RFC.
Tests instantiation speed with current vs reduced slot counts.

Run:
    python benchmarks/test_contextvar_config.py

Or with pytest-benchmark:
    pytest benchmarks/test_contextvar_config.py -v
"""

from __future__ import annotations

import sys
import time
from contextvars import ContextVar
from dataclasses import dataclass
from typing import Any, Callable

# =============================================================================
# CURRENT IMPLEMENTATION (18 slots)
# =============================================================================


class ParserCurrent:
    """Current Parser with 18 slots (config duplicated per instance)."""

    __slots__ = (
        "_source",
        "_tokens",
        "_pos",
        "_current",
        "_source_file",
        "_text_transformer",
        "_tables_enabled",
        "_strikethrough_enabled",
        "_task_lists_enabled",
        "_footnotes_enabled",
        "_math_enabled",
        "_autolinks_enabled",
        "_directive_registry",
        "_directive_stack",
        "_strict_contracts",
        "_link_refs",
        "_containers",
        "_allow_setext_headings",
    )

    def __init__(
        self,
        source: str = "",
        source_file: str | None = None,
        *,
        tables_enabled: bool = False,
        strikethrough_enabled: bool = False,
        task_lists_enabled: bool = False,
        footnotes_enabled: bool = False,
        math_enabled: bool = False,
        autolinks_enabled: bool = False,
        directive_registry: Any = None,
        strict_contracts: bool = False,
        text_transformer: Callable[[str], str] | None = None,
    ) -> None:
        self._source = source
        self._tokens: list = []
        self._pos = 0
        self._current = None
        self._source_file = source_file
        self._text_transformer = text_transformer
        self._tables_enabled = tables_enabled
        self._strikethrough_enabled = strikethrough_enabled
        self._task_lists_enabled = task_lists_enabled
        self._footnotes_enabled = footnotes_enabled
        self._math_enabled = math_enabled
        self._autolinks_enabled = autolinks_enabled
        self._directive_registry = directive_registry
        self._directive_stack: list = []
        self._strict_contracts = strict_contracts
        self._link_refs: dict = {}
        self._containers: list = []
        self._allow_setext_headings = True


# =============================================================================
# PROPOSED: ContextVar Config Pattern (9 slots)
# =============================================================================


@dataclass(frozen=True, slots=True)
class ParseConfig:
    """Immutable parse configuration - set once, read many."""

    tables_enabled: bool = False
    strikethrough_enabled: bool = False
    task_lists_enabled: bool = False
    footnotes_enabled: bool = False
    math_enabled: bool = False
    autolinks_enabled: bool = False
    directive_registry: Any = None
    strict_contracts: bool = False
    text_transformer: Callable[[str], str] | None = None


# Thread-local config
_parse_config: ContextVar[ParseConfig] = ContextVar("parse_config")


class ParserContextVar:
    """Proposed Parser with 9 slots (config via ContextVar)."""

    __slots__ = (
        "_source",
        "_tokens",
        "_pos",
        "_current",
        "_source_file",
        "_directive_stack",
        "_link_refs",
        "_containers",
        "_allow_setext_headings",
    )

    def __init__(
        self,
        source: str = "",
        source_file: str | None = None,
    ) -> None:
        self._source = source
        self._tokens: list = []
        self._pos = 0
        self._current = None
        self._source_file = source_file
        self._directive_stack: list = []
        self._link_refs: dict = {}
        self._containers: list = []
        self._allow_setext_headings = True

    @property
    def _tables_enabled(self) -> bool:
        return _parse_config.get().tables_enabled

    @property
    def _math_enabled(self) -> bool:
        return _parse_config.get().math_enabled

    # ... other config properties delegate to ContextVar


# =============================================================================
# CURRENT HTMLRenderer (14 slots)
# =============================================================================


class RendererCurrent:
    """Current HTMLRenderer with 14 slots."""

    __slots__ = (
        "_source",
        "_highlight",
        "_highlight_style",
        "_rosettes_available",
        "_directive_registry",
        "_directive_cache",
        "_role_registry",
        "_text_transformer",
        "_delegate",
        "_headings",
        "_slugify",
        "_seen_slugs",
        "_page_context",
        "_current_page",
    )

    def __init__(
        self,
        source: str = "",
        *,
        highlight: bool = False,
        highlight_style: str = "semantic",
        directive_registry: Any = None,
        role_registry: Any = None,
        text_transformer: Callable[[str], str] | None = None,
        slugify: Callable[[str], str] | None = None,
        page_context: Any = None,
    ) -> None:
        self._source = source
        self._highlight = highlight
        self._highlight_style = highlight_style
        self._rosettes_available = False
        self._directive_registry = directive_registry
        self._directive_cache = None
        self._role_registry = role_registry
        self._text_transformer = text_transformer
        self._delegate = None
        self._headings: list = []
        self._slugify = slugify
        self._seen_slugs: set = set()
        self._page_context = page_context
        self._current_page = page_context


# =============================================================================
# PROPOSED HTMLRenderer (8 slots)
# =============================================================================


@dataclass(frozen=True, slots=True)
class RenderConfig:
    """Immutable render configuration."""

    highlight: bool = False
    highlight_style: str = "semantic"
    directive_registry: Any = None
    role_registry: Any = None
    text_transformer: Callable[[str], str] | None = None
    slugify: Callable[[str], str] | None = None


_render_config: ContextVar[RenderConfig] = ContextVar("render_config")


class RendererContextVar:
    """Proposed HTMLRenderer with 8 slots (config via ContextVar)."""

    __slots__ = (
        "_source",
        "_delegate",
        "_headings",
        "_seen_slugs",
        "_page_context",
        "_current_page",
        "_directive_cache",
        "_rosettes_available",
    )

    def __init__(
        self,
        source: str = "",
        *,
        page_context: Any = None,
    ) -> None:
        self._source = source
        self._delegate = None
        self._headings: list = []
        self._seen_slugs: set = set()
        self._page_context = page_context
        self._current_page = page_context
        self._directive_cache = None
        self._rosettes_available = False

    @property
    def _highlight(self) -> bool:
        return _render_config.get().highlight

    @property
    def _highlight_style(self) -> str:
        return _render_config.get().highlight_style


# =============================================================================
# BENCHMARKS
# =============================================================================


def benchmark_instantiation(cls, iterations: int = 100_000, **kwargs) -> float:
    """Benchmark class instantiation time."""
    start = time.perf_counter()
    for _ in range(iterations):
        cls(**kwargs)
    elapsed = time.perf_counter() - start
    return elapsed * 1000  # ms


def run_benchmarks():
    """Run all benchmarks and report results."""
    iterations = 100_000

    print("=" * 70)
    print("ContextVar Config Pattern Benchmark")
    print("=" * 70)
    print(f"Python: {sys.version}")
    print(f"Iterations: {iterations:,}")
    print()

    # Set up ContextVar configs (simulates build start)
    _parse_config.set(ParseConfig(tables_enabled=True, math_enabled=True))
    _render_config.set(RenderConfig(highlight=True))

    # Parser benchmarks
    print("PARSER INSTANTIATION")
    print("-" * 70)

    parser_current_ms = benchmark_instantiation(
        ParserCurrent,
        iterations,
        source="# Hello",
        tables_enabled=True,
        math_enabled=True,
    )

    parser_contextvar_ms = benchmark_instantiation(
        ParserContextVar,
        iterations,
        source="# Hello",
    )

    parser_speedup = parser_current_ms / parser_contextvar_ms
    parser_reduction = (18 - 9) / 18 * 100

    print(f"  Current (18 slots):     {parser_current_ms:>8.2f}ms")
    print(f"  ContextVar (9 slots):   {parser_contextvar_ms:>8.2f}ms")
    print(f"  Speedup:                {parser_speedup:>8.2f}x")
    print(f"  Slot reduction:         {parser_reduction:>8.0f}%")
    print()

    # Renderer benchmarks
    print("RENDERER INSTANTIATION")
    print("-" * 70)

    renderer_current_ms = benchmark_instantiation(
        RendererCurrent,
        iterations,
        source="<p>Hello</p>",
        highlight=True,
    )

    renderer_contextvar_ms = benchmark_instantiation(
        RendererContextVar,
        iterations,
        source="<p>Hello</p>",
    )

    renderer_speedup = renderer_current_ms / renderer_contextvar_ms
    renderer_reduction = (14 - 8) / 14 * 100

    print(f"  Current (14 slots):     {renderer_current_ms:>8.2f}ms")
    print(f"  ContextVar (8 slots):   {renderer_contextvar_ms:>8.2f}ms")
    print(f"  Speedup:                {renderer_speedup:>8.2f}x")
    print(f"  Slot reduction:         {renderer_reduction:>8.0f}%")
    print()

    # Combined impact
    print("COMBINED IMPACT (1,000 page build)")
    print("-" * 70)

    pages = 1000
    current_total = (parser_current_ms + renderer_current_ms) * pages / iterations
    contextvar_total = (parser_contextvar_ms + renderer_contextvar_ms) * pages / iterations
    saved = current_total - contextvar_total

    print(f"  Current:                {current_total:>8.2f}ms")
    print(f"  ContextVar:             {contextvar_total:>8.2f}ms")
    print(f"  Saved:                  {saved:>8.2f}ms")
    print()

    # ContextVar lookup overhead test
    print("CONTEXTVAR LOOKUP OVERHEAD")
    print("-" * 70)

    start = time.perf_counter()
    for _ in range(iterations):
        _ = _parse_config.get().tables_enabled
    lookup_ms = (time.perf_counter() - start) * 1000
    ops_per_sec = iterations / (lookup_ms / 1000)

    print(f"  {iterations:,} lookups:        {lookup_ms:>8.2f}ms")
    print(f"  Throughput:             {ops_per_sec / 1_000_000:>8.2f}M ops/sec")
    print()

    # Summary
    print("=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(
        f"  Parser:   {parser_speedup:.2f}x faster ({18} → {9} slots, {parser_reduction:.0f}% reduction)"
    )
    print(
        f"  Renderer: {renderer_speedup:.2f}x faster ({14} → {8} slots, {renderer_reduction:.0f}% reduction)"
    )
    print(f"  ContextVar lookup: {ops_per_sec / 1_000_000:.1f}M ops/sec (negligible overhead)")
    print()

    if parser_speedup > 1.5 and renderer_speedup > 1.3:
        print("✅ RECOMMENDATION: Implement ContextVar config pattern")
    else:
        print("⚠️  Results inconclusive - review data")

    return {
        "parser": {"speedup": parser_speedup, "slots_before": 18, "slots_after": 9},
        "renderer": {"speedup": renderer_speedup, "slots_before": 14, "slots_after": 8},
        "lookup_ops_per_sec": ops_per_sec,
    }


# =============================================================================
# PYTEST-BENCHMARK SUPPORT
# =============================================================================


def test_parser_current(benchmark):
    """Benchmark current Parser instantiation."""
    benchmark(
        ParserCurrent,
        source="# Hello",
        tables_enabled=True,
        math_enabled=True,
    )


def test_parser_contextvar(benchmark):
    """Benchmark ContextVar Parser instantiation."""
    _parse_config.set(ParseConfig(tables_enabled=True, math_enabled=True))
    benchmark(ParserContextVar, source="# Hello")


def test_renderer_current(benchmark):
    """Benchmark current HTMLRenderer instantiation."""
    benchmark(RendererCurrent, source="<p>Hello</p>", highlight=True)


def test_renderer_contextvar(benchmark):
    """Benchmark ContextVar HTMLRenderer instantiation."""
    _render_config.set(RenderConfig(highlight=True))
    benchmark(RendererContextVar, source="<p>Hello</p>")


def test_contextvar_lookup(benchmark):
    """Benchmark ContextVar lookup overhead."""
    _parse_config.set(ParseConfig(tables_enabled=True))

    def lookup():
        return _parse_config.get().tables_enabled

    benchmark(lookup)


# =============================================================================
# MAIN
# =============================================================================

if __name__ == "__main__":
    run_benchmarks()
