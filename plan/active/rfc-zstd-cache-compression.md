# RFC: Zstandard Cache Compression (Spike)

**Status**: Draft (Spike)
**Created**: 2025-12-05
**Author**: AI-assisted analysis
**Type**: Performance Investigation
**Related**: `bengal/cache/cache_store.py`, `bengal/cache/build_cache.py`

---

## Summary

Investigate using Python 3.14's new `compression.zstd` module (PEP 784) to compress Bengal's cache files. This is a **time-boxed spike** to determine if Zstd provides meaningful benefits for `.bengal/` cache directory size and load/save performance.

**Spike Goal**: Measure compression ratio and I/O speed vs current JSON
**Time Box**: 2-4 hours
**Decision Point**: Adopt if ≥40% size reduction with ≤10% speed penalty

---

## Background

### Current State: Uncompressed JSON

Bengal's cache files use plain JSON:

```python
# bengal/cache/cache_store.py:170-171
with open(self.cache_path, "w", encoding="utf-8") as f:
    json.dump(data, f, indent=indent)
```

For large sites, cache files can grow substantially:
- `page_metadata.json` - PageCore data for every page
- `taxonomy_index.json` - Tag/category indexes
- `asset_dependency_map.json` - Asset relationships
- `build_cache.json` - Hashes, dependencies, parsed content

### Why Zstandard?

PEP 784 adds `compression.zstd` to Python 3.14 stdlib:

| Feature | Benefit for Bengal |
|---------|-------------------|
| 3-5x better compression than gzip | Smaller `.bengal/` directory |
| Fast decompression (~1GB/s) | Fast cache loads |
| Dictionary support | Great for repetitive JSON structures |
| Streaming API | Memory-efficient for large files |
| Adjustable compression level | Trade-off speed vs size |

---

## Spike Objectives

### 1. Measure Current Cache Sizes

```bash
# Benchmark current cache sizes for test-basic root (small)
du -h .bengal/

# Benchmark for docs site (medium: ~770 pages)
cd site && bengal build && du -h .bengal/
```

**Expected Outputs**:
- Total `.bengal/` size
- Individual file sizes (build_cache.json, taxonomy_index.json, etc.)

### 2. Prototype Compressed Cache Store

Create `bengal/cache/cache_store_zstd.py`:

```python
"""
Experimental Zstandard-compressed cache store.

Spike to evaluate compression benefits for cache files.
Uses Python 3.14's new compression.zstd module (PEP 784).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import TypeVar

# Python 3.14+ only
from compression import zstd

from bengal.cache.cacheable import Cacheable
from bengal.utils.logger import get_logger

logger = get_logger(__name__)

T = TypeVar("T", bound=Cacheable)


class ZstdCacheStore:
    """
    Cache store with Zstandard compression.
    
    File format: .json.zst (compressed JSON)
    Compression level: 3 (default, good balance)
    """
    
    COMPRESSION_LEVEL = 3  # 1-22, higher = smaller but slower
    
    def __init__(self, cache_path: Path):
        """
        Initialize compressed cache store.
        
        Args:
            cache_path: Path to cache file (e.g., .bengal/tags.json.zst)
        """
        self.cache_path = cache_path
        
    def save(
        self,
        entries: list[Cacheable],
        version: int = 1,
    ) -> None:
        """Save entries with Zstd compression."""
        data = {
            "version": version,
            "entries": [entry.to_cache_dict() for entry in entries],
        }
        
        # Serialize to JSON bytes
        json_bytes = json.dumps(data, separators=(",", ":")).encode("utf-8")
        
        # Compress with Zstandard
        compressed = zstd.compress(json_bytes, level=self.COMPRESSION_LEVEL)
        
        # Write atomically
        self.cache_path.parent.mkdir(parents=True, exist_ok=True)
        self.cache_path.write_bytes(compressed)
        
        ratio = len(json_bytes) / len(compressed)
        logger.debug(
            f"Saved {len(entries)} entries to {self.cache_path} "
            f"({len(json_bytes)} → {len(compressed)} bytes, {ratio:.1f}x compression)"
        )
    
    def load(
        self,
        entry_type: type[T],
        expected_version: int = 1,
    ) -> list[T]:
        """Load entries with Zstd decompression."""
        if not self.cache_path.exists():
            logger.debug(f"Cache not found: {self.cache_path}")
            return []
        
        try:
            # Read and decompress
            compressed = self.cache_path.read_bytes()
            json_bytes = zstd.decompress(compressed)
            data = json.loads(json_bytes)
            
            # Version check
            if data.get("version") != expected_version:
                logger.warning(f"Cache version mismatch: {self.cache_path}")
                return []
            
            # Deserialize entries
            return [entry_type.from_cache_dict(e) for e in data.get("entries", [])]
            
        except (zstd.ZstdError, json.JSONDecodeError) as e:
            logger.error(f"Failed to load cache {self.cache_path}: {e}")
            return []
```

### 3. Benchmark Script

Create `scripts/benchmark_zstd_cache.py`:

```python
#!/usr/bin/env python3
"""
Benchmark Zstd cache compression vs plain JSON.

Usage:
    python scripts/benchmark_zstd_cache.py [--site-root SITE_ROOT]
    
Example:
    python scripts/benchmark_zstd_cache.py --site-root site
"""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

# Python 3.14+
from compression import zstd


def benchmark_file(json_path: Path) -> dict:
    """Benchmark a single JSON cache file."""
    if not json_path.exists():
        return {"error": f"File not found: {json_path}"}
    
    # Read original
    original_bytes = json_path.read_bytes()
    original_size = len(original_bytes)
    
    # Parse JSON (to ensure it's valid)
    data = json.loads(original_bytes)
    
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
        # Compression
        start = time.perf_counter()
        compressed = zstd.compress(compact_bytes, level=level)
        compress_time = time.perf_counter() - start
        
        # Decompression
        start = time.perf_counter()
        _ = zstd.decompress(compressed)
        decompress_time = time.perf_counter() - start
        
        results["levels"][level] = {
            "compressed_size": len(compressed),
            "ratio": compact_size / len(compressed),
            "compress_ms": compress_time * 1000,
            "decompress_ms": decompress_time * 1000,
        }
    
    return results


def main():
    parser = argparse.ArgumentParser(description="Benchmark Zstd cache compression")
    parser.add_argument("--site-root", default=".", help="Site root directory")
    args = parser.parse_args()
    
    cache_dir = Path(args.site_root) / ".bengal"
    
    if not cache_dir.exists():
        print(f"Cache directory not found: {cache_dir}")
        print("Run 'bengal build' first to generate cache files.")
        return
    
    # Find all JSON cache files
    json_files = list(cache_dir.glob("*.json"))
    
    if not json_files:
        print(f"No JSON files found in {cache_dir}")
        return
    
    print(f"Benchmarking {len(json_files)} cache files in {cache_dir}\n")
    print("=" * 80)
    
    total_original = 0
    total_compressed = 0
    
    for json_path in sorted(json_files):
        result = benchmark_file(json_path)
        
        if "error" in result:
            print(f"  {result['error']}")
            continue
        
        print(f"\n📁 {result['file']}")
        print(f"   Original:    {result['original_size']:,} bytes")
        print(f"   Compact:     {result['compact_size']:,} bytes")
        
        # Use level 3 (default) for totals
        level_3 = result["levels"][3]
        total_original += result["compact_size"]
        total_compressed += level_3["compressed_size"]
        
        print(f"\n   Compression levels:")
        for level, stats in result["levels"].items():
            print(
                f"     Level {level}: {stats['compressed_size']:,} bytes "
                f"({stats['ratio']:.1f}x) "
                f"[compress: {stats['compress_ms']:.2f}ms, "
                f"decompress: {stats['decompress_ms']:.2f}ms]"
            )
    
    print("\n" + "=" * 80)
    print(f"\n📊 TOTALS (at level 3):")
    print(f"   Original:   {total_original:,} bytes ({total_original / 1024:.1f} KB)")
    print(f"   Compressed: {total_compressed:,} bytes ({total_compressed / 1024:.1f} KB)")
    print(f"   Ratio:      {total_original / total_compressed:.1f}x")
    print(f"   Savings:    {(1 - total_compressed / total_original) * 100:.1f}%")


if __name__ == "__main__":
    main()
```

### 4. Success Metrics

| Metric | Target | Pass Condition |
|--------|--------|----------------|
| Compression ratio | ≥3x | Cache files 3x smaller on average |
| Size reduction | ≥40% | At least 40% total size savings |
| Compress speed | ≤50ms | For typical cache file (100KB) |
| Decompress speed | ≤10ms | For typical cache file (100KB) |
| Memory overhead | ≤10MB | Peak memory during compression |

---

## Expected Results

Based on JSON's characteristics and Zstd's performance profile:

### Optimistic (JSON highly compressible)

```
📊 TOTALS (at level 3):
   Original:   512 KB
   Compressed: 85 KB
   Ratio:      6.0x
   Savings:    83%
```

### Conservative (Moderate compression)

```
📊 TOTALS (at level 3):
   Original:   512 KB
   Compressed: 171 KB
   Ratio:      3.0x
   Savings:    67%
```

### Pessimistic (Poor compression)

```
📊 TOTALS (at level 3):
   Original:   512 KB
   Compressed: 307 KB
   Ratio:      1.7x
   Savings:    40%
```

---

## Decision Matrix

After spike completes, evaluate:

| Outcome | Decision |
|---------|----------|
| ≥40% savings, fast I/O | ✅ Proceed to implementation RFC |
| 20-40% savings | 🟡 Consider for large sites only (opt-in) |
| <20% savings | ❌ Not worth the complexity |
| Speed penalty >50% | ❌ Reject (cache speed is critical) |

---

## Implementation Path (If Spike Succeeds)

### Phase 1: Add Compression Module

1. Create `bengal/cache/compression.py` with Zstd wrappers
2. Update `CacheStore` to accept compression option
3. Default: compressed for new caches, transparent read of old

### Phase 2: Migrate Existing Caches

```python
# Auto-detect format by extension
def load(self, path: Path) -> dict:
    if path.suffix == ".zst":
        return self._load_compressed(path)
    return self._load_json(path)
```

### Phase 3: Configuration

```yaml
# bengal.yaml
build:
  cache:
    compression: true  # Default for 3.14+
    level: 3          # 1-22
```

---

## Risks and Mitigations

| Risk | Mitigation |
|------|------------|
| Python <3.14 compatibility | Feature-gate behind version check |
| Corrupted cache | Tolerant loading (rebuild on error) |
| Debugging difficulty | Add `bengal cache inspect` command |
| CI/CD compatibility | Cache compression is optional |

---

## Out of Scope

- Compressing build outputs (HTML, CSS, JS) - different use case
- Dictionary training - complexity not worth it for cache sizes
- Streaming compression - cache files are small enough

---

## Spike Checklist

- [ ] Build site to generate cache files
- [ ] Run benchmark script
- [ ] Record compression ratios for each file type
- [ ] Measure I/O speed (compress + decompress)
- [ ] Test on small site (test-basic)
- [ ] Test on medium site (docs site, ~770 pages)
- [ ] Document findings in this RFC
- [ ] Make go/no-go decision

---

## References

- [PEP 784 – Adding Zstandard to the Standard Library](https://peps.python.org/pep-0784/)
- [Zstandard compression algorithm](https://facebook.github.io/zstd/)
- [Python 3.14 Release Notes](https://docs.python.org/3.14/whatsnew/3.14.html)
- Related: `bengal/cache/cache_store.py` - Current JSON implementation
- Related: `bengal/cache/build_cache.py` - BuildCache (largest cache file)

