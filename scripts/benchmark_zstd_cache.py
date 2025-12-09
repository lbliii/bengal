#!/usr/bin/env python3
"""
Benchmark Zstd cache compression vs plain JSON.

Spike for RFC: Zstandard Cache Compression
Tests Python 3.14's new compression.zstd module (PEP 784).

Usage:
    python scripts/benchmark_zstd_cache.py [--site-root SITE_ROOT]

Example:
    python scripts/benchmark_zstd_cache.py --site-root site
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

# Check Python version and zstd availability
try:
    from compression import zstd

    ZSTD_AVAILABLE = True
except ImportError:
    ZSTD_AVAILABLE = False
    # Try third-party zstandard as fallback
    try:
        import zstandard as zstd_fallback

        ZSTD_AVAILABLE = True

        # Create compatible interface
        class zstd:
            @staticmethod
            def compress(data: bytes, level: int = 3) -> bytes:
                cctx = zstd_fallback.ZstdCompressor(level=level)
                return cctx.compress(data)

            @staticmethod
            def decompress(data: bytes) -> bytes:
                dctx = zstd_fallback.ZstdDecompressor()
                return dctx.decompress(data)

    except ImportError:
        pass


def format_size(size_bytes: int) -> str:
    """Format bytes as human-readable size."""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    else:
        return f"{size_bytes / (1024 * 1024):.2f} MB"


def benchmark_file(json_path: Path) -> dict:
    """Benchmark a single JSON cache file."""
    if not json_path.exists():
        return {"error": f"File not found: {json_path}"}

    # Read original
    original_bytes = json_path.read_bytes()
    original_size = len(original_bytes)

    # Parse JSON (to ensure it's valid)
    try:
        data = json.loads(original_bytes)
    except json.JSONDecodeError as e:
        return {"error": f"Invalid JSON: {e}"}

    # Re-serialize without indentation (compact)
    compact_bytes = json.dumps(data, separators=(",", ":")).encode("utf-8")
    compact_size = len(compact_bytes)

    # Benchmark compression at different levels
    results = {
        "file": str(json_path.name),
        "original_size": original_size,
        "compact_size": compact_size,
        "levels": {},
    }

    for level in [1, 3, 6, 9]:
        # Compression - run multiple times for stable timing
        iterations = 10
        start = time.perf_counter()
        for _ in range(iterations):
            compressed = zstd.compress(compact_bytes, level=level)
        compress_time = (time.perf_counter() - start) / iterations

        # Decompression
        start = time.perf_counter()
        for _ in range(iterations):
            _ = zstd.decompress(compressed)
        decompress_time = (time.perf_counter() - start) / iterations

        results["levels"][level] = {
            "compressed_size": len(compressed),
            "ratio": compact_size / len(compressed) if len(compressed) > 0 else 0,
            "compress_ms": compress_time * 1000,
            "decompress_ms": decompress_time * 1000,
        }

    return results


def main():
    parser = argparse.ArgumentParser(description="Benchmark Zstd cache compression")
    parser.add_argument("--site-root", default=".", help="Site root directory")
    args = parser.parse_args()

    print("=" * 80)
    print("🔬 Zstd Cache Compression Benchmark (RFC Spike)")
    print("=" * 80)

    # Check zstd availability
    if not ZSTD_AVAILABLE:
        print("\n❌ Zstd not available!")
        print("   Python 3.14's compression.zstd module not found.")
        print("   Fallback zstandard package also not installed.")
        print("\n   To run this benchmark, install the fallback:")
        print("   pip install zstandard")
        sys.exit(1)

    print(
        f"\n✅ Zstd available (using {'stdlib' if 'compression' in sys.modules else 'zstandard fallback'})"
    )

    cache_dir = Path(args.site_root) / ".bengal"

    if not cache_dir.exists():
        print(f"\n❌ Cache directory not found: {cache_dir}")
        print("   Run 'bengal build' first to generate cache files.")
        sys.exit(1)

    # Find all JSON cache files
    json_files = list(cache_dir.glob("*.json"))

    if not json_files:
        print(f"\n❌ No JSON files found in {cache_dir}")
        sys.exit(1)

    print(f"\n📁 Found {len(json_files)} cache files in {cache_dir}\n")

    total_original = 0
    total_compact = 0
    total_compressed = {1: 0, 3: 0, 6: 0, 9: 0}
    total_compress_time = {1: 0, 3: 0, 6: 0, 9: 0}
    total_decompress_time = {1: 0, 3: 0, 6: 0, 9: 0}

    for json_path in sorted(json_files):
        result = benchmark_file(json_path)

        if "error" in result:
            print(f"  ⚠️  {result['error']}")
            continue

        total_original += result["original_size"]
        total_compact += result["compact_size"]

        print(f"📄 {result['file']}")
        print(
            f"   Size: {format_size(result['original_size'])} → {format_size(result['compact_size'])} (compact JSON)"
        )

        # Find best level for this file
        best_level = min(result["levels"].items(), key=lambda x: x[1]["compressed_size"])
        print(
            f"   Best: Level {best_level[0]} → {format_size(best_level[1]['compressed_size'])} ({best_level[1]['ratio']:.1f}x)"
        )

        for level, stats in result["levels"].items():
            total_compressed[level] += stats["compressed_size"]
            total_compress_time[level] += stats["compress_ms"]
            total_decompress_time[level] += stats["decompress_ms"]

        print()

    # Summary
    print("=" * 80)
    print("📊 SUMMARY")
    print("=" * 80)

    print("\n📦 Total Cache Size:")
    print(f"   Original (indented):  {format_size(total_original)}")
    print(f"   Compact JSON:         {format_size(total_compact)}")

    print("\n🗜️  Compression Results by Level:")
    print(
        f"   {'Level':<8} {'Size':<12} {'Ratio':<8} {'Savings':<10} {'Compress':<12} {'Decompress':<12}"
    )
    print(f"   {'-' * 8} {'-' * 12} {'-' * 8} {'-' * 10} {'-' * 12} {'-' * 12}")

    for level in [1, 3, 6, 9]:
        size = total_compressed[level]
        ratio = total_compact / size if size > 0 else 0
        savings = (1 - size / total_compact) * 100 if total_compact > 0 else 0
        compress_ms = total_compress_time[level]
        decompress_ms = total_decompress_time[level]

        print(
            f"   {level:<8} {format_size(size):<12} {ratio:.1f}x{'':<5} {savings:.0f}%{'':<7} "
            f"{compress_ms:.2f}ms{'':<6} {decompress_ms:.2f}ms"
        )

    # Recommendation
    print("\n" + "=" * 80)
    print("🎯 RECOMMENDATION (Level 3 - Default)")
    print("=" * 80)

    level_3_size = total_compressed[3]
    level_3_ratio = total_compact / level_3_size if level_3_size > 0 else 0
    level_3_savings = (1 - level_3_size / total_compact) * 100 if total_compact > 0 else 0

    print(f"\n   Compressed size: {format_size(level_3_size)}")
    print(f"   Compression ratio: {level_3_ratio:.1f}x")
    print(f"   Space savings: {level_3_savings:.0f}%")
    print(f"   Compress time: {total_compress_time[3]:.2f}ms")
    print(f"   Decompress time: {total_decompress_time[3]:.2f}ms")

    # Decision
    print("\n" + "-" * 80)
    if level_3_savings >= 40:
        print("✅ PASS: ≥40% savings achieved - proceed to implementation RFC")
    elif level_3_savings >= 20:
        print("🟡 MODERATE: 20-40% savings - consider opt-in for large sites")
    else:
        print("❌ FAIL: <20% savings - not worth the complexity")

    if total_compress_time[3] > 500:
        print("⚠️  WARNING: Compress time >500ms - may impact build performance")
    if total_decompress_time[3] > 100:
        print("⚠️  WARNING: Decompress time >100ms - may impact cache load")

    print()


if __name__ == "__main__":
    main()
