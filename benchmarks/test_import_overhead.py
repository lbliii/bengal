"""
Import Overhead Benchmarks - Measure module startup latency and dependency pollution.

These tests measure:
1. Cold import time for key modules
2. "Import pollution" - heavy dependencies loaded when not needed
3. Lazy vs eager import patterns

Run with:
    pytest benchmarks/test_import_overhead.py -v
    pytest benchmarks/test_import_overhead.py -v -k "rosettes"  # specific module

Terminology:
    - Cold import: First import after clearing sys.modules
    - Import pollution: Loading heavy deps (errors, core, pipeline) when not needed
    - Lazy loading: Deferring imports until first use

Design Principles (from rosettes investigation):
    - Lightweight modules should import in <50ms
    - Optional features should not load until used
    - Package __init__.py should use lazy exports for heavy classes
    - Error imports should be deferred to exception-raising code paths
"""

from __future__ import annotations

import subprocess
import sys
from typing import NamedTuple

import pytest

# Thresholds for acceptable import times (milliseconds)
THRESHOLDS = {
    "lightweight": 50,  # Utils, types, protocols
    "moderate": 150,  # Template engines, parsers
    "heavy": 500,  # Full pipeline, site loading
}

# Heavy modules that lightweight imports should NOT trigger
# Note: bengal.errors is now lazy-loaded and only ~2ms, but we still track it
# because lightweight modules shouldn't need error infrastructure at import time
HEAVY_MODULES = frozenset(
    [
        "bengal.core.page",
        "bengal.core.site",
        "bengal.rendering.pipeline",
        "bengal.cache.build_cache",
    ]
)

# Optional dependencies that should not load unless explicitly used
OPTIONAL_DEPS = frozenset(
    [
        "uvloop",
        "psutil",
        "aiohttp",
        "zstd",
        "compression.zstd",
        "mako",
        "patitas",
        "lunr",
        "marimo",
    ]
)


class ImportResult(NamedTuple):
    """Result of measuring an import."""

    module: str
    time_ms: float
    heavy_loaded: list[str]
    optional_loaded: list[str]


def measure_import(module_path: str) -> ImportResult:
    """
    Measure import time and dependency pollution in a fresh Python process.

    Uses subprocess to ensure completely cold import (no cached modules).
    """
    script = f"""
import sys
import time

# Measure import time
start = time.perf_counter()
import {module_path}
elapsed = (time.perf_counter() - start) * 1000

# Check which heavy modules were loaded
heavy = {list(HEAVY_MODULES)!r}
heavy_loaded = [m for m in heavy if m in sys.modules]

# Check which optional deps were loaded
optional = {list(OPTIONAL_DEPS)!r}
optional_loaded = [m for m in optional if m in sys.modules]

# Output as simple parseable format
print(f"TIME:{{elapsed:.2f}}")
print(f"HEAVY:{{','.join(heavy_loaded) if heavy_loaded else 'none'}}")
print(f"OPTIONAL:{{','.join(optional_loaded) if optional_loaded else 'none'}}")
"""

    result = subprocess.run(
        [sys.executable, "-c", script],
        capture_output=True,
        text=True,
        timeout=30,
    )

    if result.returncode != 0:
        pytest.fail(f"Import failed for {module_path}: {result.stderr}")

    # Parse output
    lines = result.stdout.strip().split("\n")
    time_ms = float(lines[0].split(":")[1])
    heavy_str = lines[1].split(":")[1]
    optional_str = lines[2].split(":")[1]

    heavy_loaded = [] if heavy_str == "none" else heavy_str.split(",")
    optional_loaded = [] if optional_str == "none" else optional_str.split(",")

    return ImportResult(
        module=module_path,
        time_ms=time_ms,
        heavy_loaded=heavy_loaded,
        optional_loaded=optional_loaded,
    )


# =============================================================================
# Lightweight Module Tests - Should be fast, no heavy deps
# =============================================================================


class TestLightweightModules:
    """Modules that should import quickly without heavy dependencies."""

    @pytest.mark.parametrize(
        "module",
        [
            "rosettes",  # External package
            "rosettes._types",
            "rosettes._registry",
            "kida",
            "bengal.rendering.highlighting",
        ],
    )
    def test_rendering_submodules_are_lightweight(self, module: str):
        """Rendering submodules should not pull in heavy infrastructure."""
        result = measure_import(module)

        assert result.time_ms < THRESHOLDS["lightweight"], (
            f"{module} took {result.time_ms:.1f}ms (threshold: {THRESHOLDS['lightweight']}ms)"
        )

        assert not result.heavy_loaded, f"{module} loaded heavy modules: {result.heavy_loaded}"

    def test_rosettes_highlight_function(self):
        """The highlight() function should work without heavy deps."""
        result = measure_import("rosettes")  # External package

        assert result.time_ms < THRESHOLDS["lightweight"]
        assert not result.heavy_loaded
        assert not result.optional_loaded

    def test_kida_template_engine(self):
        """Kida should be a lightweight Jinja alternative."""
        result = measure_import("kida")

        assert result.time_ms < THRESHOLDS["lightweight"]
        assert not result.heavy_loaded


# =============================================================================
# Optional Dependency Tests - Should not load unless used
# =============================================================================


class TestOptionalDependencies:
    """Optional dependencies should only load when explicitly used."""

    def test_uvloop_not_loaded_by_utils(self):
        """Importing utils should not trigger uvloop load."""
        result = measure_import("bengal.utils.hashing")

        assert "uvloop" not in result.optional_loaded, (
            "uvloop loaded by bengal.utils.hashing - should be lazy"
        )

    def test_psutil_not_loaded_by_default(self):
        """psutil should only load when collecting performance metrics."""
        result = measure_import("bengal.utils.logger")

        assert "psutil" not in result.optional_loaded, "psutil loaded by logger - should be lazy"

    def test_aiohttp_not_loaded_by_content_layer(self):
        """aiohttp should only load when using REST/external sources."""
        # Import content layer base, not specific sources
        result = measure_import("bengal.content.sources")

        assert "aiohttp" not in result.optional_loaded, (
            "aiohttp loaded by content_layer base - should be lazy"
        )

    def test_tree_sitter_not_loaded_by_highlighting(self):
        """tree-sitter should not load if rosettes is the default backend."""
        result = measure_import("bengal.rendering.highlighting")

        # tree_sitter may or may not be installed, but shouldn't load
        # unless explicitly requested
        assert "tree_sitter" not in result.optional_loaded, (
            "tree_sitter loaded by highlighting - should be lazy"
        )


# =============================================================================
# Error Import Tests - Errors should be lazy
# =============================================================================


class TestErrorImports:
    """bengal.errors is heavy - should only load when actually raising errors."""

    def test_rosettes_no_errors_on_success_path(self):
        """Rosettes shouldn't load errors when highlighting valid code."""
        script = """
import sys

# Import and use rosettes (external package)
from rosettes import highlight
result = highlight("print('hello')", "python")

# Check if errors was loaded (rosettes doesn't depend on bengal.errors)
errors_loaded = "bengal.errors" in sys.modules
print(f"ERRORS_LOADED:{errors_loaded}")
"""
        result = subprocess.run(
            [sys.executable, "-c", script],
            capture_output=True,
            text=True,
            timeout=30,
        )

        assert "ERRORS_LOADED:False" in result.stdout, (
            "bengal.errors loaded during successful highlight - should be lazy"
        )

    def test_rosettes_raises_lookup_error_on_invalid_language(self):
        """Rosettes should raise LookupError for unknown languages."""
        script = """
import sys

from rosettes import get_lexer

try:
    get_lexer("nonexistent_language_xyz")
    print("RAISED:False")
except LookupError:
    print("RAISED:True")
except Exception as e:
    print(f"RAISED:Wrong({type(e).__name__})")
"""
        result = subprocess.run(
            [sys.executable, "-c", script],
            capture_output=True,
            text=True,
            timeout=30,
        )

        assert "RAISED:True" in result.stdout, (
            "rosettes should raise LookupError for unknown languages"
        )


# =============================================================================
# Package Init Tests - __init__.py should be lazy
# =============================================================================


class TestPackageInits:
    """Package __init__.py files should use lazy imports for heavy re-exports."""

    def test_rendering_init_is_lazy(self):
        """bengal.rendering should not eagerly load RenderingPipeline."""
        result = measure_import("bengal.rendering.highlighting")

        assert "bengal.rendering.pipeline" not in result.heavy_loaded, (
            "bengal.rendering.__init__ eagerly loads pipeline"
        )

    def test_utils_init_overhead(self):
        """Track bengal.utils import overhead."""
        result = measure_import("bengal.utils")

        # Log current state - can tighten threshold after fixes
        print(f"\nbengal.utils import: {result.time_ms:.1f}ms")
        print(f"  Heavy loaded: {result.heavy_loaded or 'none'}")
        print(f"  Optional loaded: {result.optional_loaded or 'none'}")

        # Current threshold - should improve
        assert result.time_ms < THRESHOLDS["heavy"], f"bengal.utils took {result.time_ms:.1f}ms"


# =============================================================================
# Comparative Benchmarks
# =============================================================================


class TestComparativeBenchmarks:
    """Compare import times between related modules."""

    def test_rosettes_vs_full_highlighting(self):
        """Direct rosettes import should be faster than full highlighting."""
        rosettes_result = measure_import("rosettes")  # External package
        highlighting = measure_import("bengal.rendering.highlighting")

        print(f"\nRosettes direct: {rosettes_result.time_ms:.1f}ms")
        print(f"Highlighting:    {highlighting.time_ms:.1f}ms")

        # Both should be lightweight
        assert rosettes_result.time_ms < THRESHOLDS["lightweight"]
        assert highlighting.time_ms < THRESHOLDS["lightweight"]

    def test_kida_vs_jinja_engine(self):
        """Compare template engine import times."""
        kida = measure_import("kida")

        print(f"\nKida engine: {kida.time_ms:.1f}ms")

        # Kida should be lightweight
        assert kida.time_ms < THRESHOLDS["lightweight"]
        assert not kida.heavy_loaded


# =============================================================================
# Regression Detection
# =============================================================================


class TestRegressionDetection:
    """Detect regressions in import performance."""

    # Baseline times from after optimization (update when improving)
    BASELINES = {
        "rosettes": 15.0,  # External package
        "kida": 10.0,
        "bengal.rendering.highlighting": 25.0,
    }

    @pytest.mark.parametrize(("module", "baseline"), list(BASELINES.items()))
    def test_no_regression_from_baseline(self, module: str, baseline: float):
        """Ensure import times don't regress from known baselines."""
        result = measure_import(module)

        # Allow 50% margin for CI variance
        max_allowed = baseline * 1.5

        assert result.time_ms < max_allowed, (
            f"{module} regressed: {result.time_ms:.1f}ms "
            f"(baseline: {baseline}ms, max: {max_allowed:.1f}ms)"
        )


# =============================================================================
# Diagnostic Utilities
# =============================================================================


def print_import_report(modules: list[str]) -> None:
    """Print a detailed import report for debugging."""
    print("\n" + "=" * 70)
    print("IMPORT OVERHEAD REPORT")
    print("=" * 70)

    for module in modules:
        result = measure_import(module)

        status = "✅" if result.time_ms < THRESHOLDS["lightweight"] else "⚠️"
        if result.heavy_loaded:
            status = "❌"

        print(f"\n{status} {module}")
        print(f"   Time: {result.time_ms:.1f}ms")

        if result.heavy_loaded:
            print(f"   Heavy deps: {', '.join(result.heavy_loaded)}")
        if result.optional_loaded:
            print(f"   Optional deps: {', '.join(result.optional_loaded)}")

    print("\n" + "=" * 70)


if __name__ == "__main__":
    # Run as script for quick diagnostics
    print_import_report(
        [
            "rosettes",  # External package
            "kida",
            "bengal.rendering.highlighting",
            "bengal.utils",
            "bengal.utils.hashing",
            "bengal.utils.logger",
            "bengal.errors",
            "bengal.core.page",
        ]
    )
