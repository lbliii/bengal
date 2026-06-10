#!/usr/bin/env python3
"""
Benchmark: theme-library provider resolution cache (#365).

resolve_theme_providers() is called on two independent build paths with no
shared state — asset discovery (orchestration/content.py) and Kida engine
loader/filter setup (rendering/engines/kida.py) — and, under the #350
shard-parallel render backend, once per worker-thread pipeline. Each
uncached call does importlib.import_module + convention-hook probing
(get_library_contract / get_loader / static_path / register_filters) for
every declared library, so the contract is rebuilt strictly more than twice
per build.

This benchmark builds a library-backed theme.toml in a temp dir and measures:

  1. cold     — first resolution per process (cache miss, real import work)
  2. warm     — repeated resolution of the SAME (site_root, chain) key
                (cache hit; this is what every extra caller/shard now pays)
  3. uncached — bypassing the cache via the private _resolve_*_uncached
                (what every extra caller paid BEFORE this change)

The headline number is warm-vs-uncached: how much each *extra* resolution
costs after the first. Wall times are tiny and noisy; we report medians over
many rounds and the ratio, and acknowledge measurement noise.

Usage:
    uv run python -m benchmarks.theme_provider_cache_benchmark
"""

from __future__ import annotations

import statistics
import sys
import tempfile
import time
import types
from pathlib import Path
from unittest.mock import patch

from bengal.core.theme import providers as P

# A library module with the full convention-hook surface so resolution does
# the maximum probing work (get_library_contract → get_loader → static_path →
# register_filters), mirroring a real Kida UI library.
_FAKE_ASSET_ROOT = Path(tempfile.mkdtemp(prefix="theme_lib_assets_"))
(_FAKE_ASSET_ROOT / "ui.css").write_text(".ui{}", encoding="utf-8")
(_FAKE_ASSET_ROOT / "ui.js").write_text("window.ui=true", encoding="utf-8")


def _make_lib(name: str) -> types.ModuleType:
    mod = types.ModuleType(name)
    mod.get_loader = lambda: f"loader::{name}"  # type: ignore[attr-defined]
    mod.static_path = lambda: _FAKE_ASSET_ROOT  # type: ignore[attr-defined]
    mod.register_filters = lambda app: None  # type: ignore[attr-defined]
    mod.get_library_contract = lambda: {  # type: ignore[attr-defined]
        "asset_root": _FAKE_ASSET_ROOT,
        "assets": [
            {"path": "ui.css", "mode": "link", "type": "css"},
            {"path": "ui.js", "mode": "link", "type": "javascript"},
        ],
        "runtime": ["alpine"],
    }
    return mod


def _build_site_root(num_libs: int) -> tuple[Path, list[str]]:
    """Create a temp site with a library-backed theme; return (root, chain)."""
    root = Path(tempfile.mkdtemp(prefix="theme_provider_bench_"))
    libs = [f"bench_lib_{i}" for i in range(num_libs)]
    theme_dir = root / "themes" / "benchtheme"
    theme_dir.mkdir(parents=True, exist_ok=True)
    libs_toml = ", ".join(f'"{lib}"' for lib in libs)
    (theme_dir / "theme.toml").write_text(
        f'name = "benchtheme"\nlibraries = [{libs_toml}]\n', encoding="utf-8"
    )
    return root, ["benchtheme"]


def _time_median(fn, *, rounds: int) -> float:
    """Return the median wall time (seconds) of fn over `rounds` calls."""
    samples: list[float] = []
    for _ in range(rounds):
        start = time.perf_counter()
        fn()
        samples.append(time.perf_counter() - start)
    return statistics.median(samples)


def run(num_libs: int = 3, warm_rounds: int = 2000) -> dict[str, float]:
    root, chain = _build_site_root(num_libs)
    libs = {f"bench_lib_{i}": _make_lib(f"bench_lib_{i}") for i in range(num_libs)}

    def fake_import(name: str):
        # Real importlib.import_module would do disk + sys.modules work here;
        # we keep it cheap so the benchmark isolates Bengal's resolution cost,
        # not import-system caching. The relative cold/warm gap is the signal.
        return libs[name]

    with patch(
        "bengal.core.theme.providers.importlib.import_module",
        side_effect=fake_import,
    ):
        # Cold: clear, then time the single first resolution (cache miss).
        P.clear_theme_provider_cache()
        cold = _time_median(
            lambda: (P.clear_theme_provider_cache(), P.resolve_theme_providers(root, chain))[1],
            rounds=max(50, warm_rounds // 20),
        )

        # Warm: cache populated; every subsequent caller/shard pays this.
        P.clear_theme_provider_cache()
        P.resolve_theme_providers(root, chain)  # populate
        warm = _time_median(
            lambda: P.resolve_theme_providers(root, chain),
            rounds=warm_rounds,
        )

        # Uncached: what each extra resolution cost BEFORE this change.
        uncached = _time_median(
            lambda: P._resolve_theme_providers_uncached(root, chain),
            rounds=max(50, warm_rounds // 20),
        )

    return {
        "num_libs": num_libs,
        "cold_us": cold * 1e6,
        "warm_us": warm * 1e6,
        "uncached_us": uncached * 1e6,
        "speedup_warm_vs_uncached": (uncached / warm) if warm > 0 else float("inf"),
    }


def main() -> int:
    print("=" * 72)
    print("Theme-library provider resolution cache benchmark (#365)")
    print("=" * 72)
    print()
    print("NOTE: wall times are sub-millisecond and noisy. The signal is the")
    print("warm (cache-hit) vs uncached ratio: how much each EXTRA resolution")
    print("(second build path + each #350 shard worker) costs before/after.")
    print()

    for num_libs in (1, 3, 6):
        r = run(num_libs=num_libs)
        print(f"libraries declared: {r['num_libs']}")
        print(f"  cold (first/miss)      : {r['cold_us']:8.2f} us")
        print(f"  uncached (per old call): {r['uncached_us']:8.2f} us")
        print(f"  warm (cache hit)       : {r['warm_us']:8.2f} us")
        print(f"  warm speedup vs uncached: {r['speedup_warm_vs_uncached']:6.1f}x")
        print()

    print("Interpretation: every caller/shard after the first now pays the warm")
    print("(hit) cost instead of the uncached cost. With a real importlib.import_module")
    print("and disk-backed theme.toml + library packages, the uncached cost is")
    print("substantially higher than shown here, so the real-build win is larger.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
