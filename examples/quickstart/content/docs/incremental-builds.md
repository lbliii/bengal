---
title: "Incremental Builds: Lightning Fast Rebuilds"
date: 2025-10-03
tags: ["performance", "builds", "advanced"]
categories: ["Documentation", "Performance"]
type: "guide"
description: "Bengal's incremental builds provide 18-42x faster rebuilds by only processing changed files"
author: "Bengal Documentation Team"
---

# Incremental Builds

**The Problem**: Rebuilding your entire site on every small change wastes valuable development time.  
**The Solution**: Bengal's incremental builds rebuild only what changed, providing 18-42x faster rebuilds.

## Performance Impact

Real-world performance improvements from our benchmarks:

| Site Size | Full Build | Incremental Build | Speedup |
|-----------|------------|-------------------|---------|
| Small (10 pages) | 0.223s | 0.012s | **18.6x faster** |
| Medium (50 pages) | 0.839s | 0.020s | **41.6x faster** |
| Large (100 pages) | 1.688s | 0.047s | **35.6x faster** |

For very large sites (1000+ pages), we expect **100x+ speedup** for single-file changes.

## How It Works

Bengal's incremental build system uses intelligent caching and dependency tracking:

### 1. File Change Detection

- **SHA256 Hashing**: Every file gets a cryptographic hash
- **Cache Persistence**: Hashes stored in `.bengal-cache.json`
- **Smart Comparison**: Only changed files trigger rebuilds

### 2. Dependency Tracking

Bengal builds a complete dependency graph during rendering:

```
page.md → template.html → partial.html
     ↓
   tag.md (if page has tags)
```

When a template changes, Bengal knows exactly which pages need rebuilding.

### 3. Selective Rebuilding

| Change Type | Bengal's Action |
|------------|-----------------|
| Content file modified | Rebuild that page only |
| Template modified | Rebuild all pages using that template |
| Partial/include modified | Rebuild all pages including it |
| Config file modified | Full rebuild (safest approach) |
| Tag modified | Rebuild affected tag pages only |

### 4. Taxonomy Intelligence

Bengal tracks tag-to-page relationships:

- Adding a tag to a post → Rebuild post + tag page
- Removing a tag → Rebuild post + tag page + tag index
- No tag changes → Skip all tag pages

## Usage

### Basic Incremental Build

```bash
# Enable incremental builds
bengal build --incremental
```

First run creates the cache. Subsequent runs are dramatically faster.

### Verbose Mode (Recommended for Learning)

```bash
# See exactly what changed and why
bengal build --incremental --verbose
```

Output shows:
```
🔍 Checking for changes...
✓ No changes to config file
Changed files (2):
  - content/posts/my-post.md (content)
  - templates/post.html (template)

Affected pages (5):
  - content/posts/my-post.md (modified)
  - content/posts/another-post.md (template dependency)
  - content/posts/third-post.md (template dependency)
  ...

⚡ Incremental build: 5 pages (out of 100 total)
```

### Combined with Parallel Processing

```bash
# Maximum speed: incremental + parallel
bengal build --incremental --parallel
```

For the ultimate development experience, combine incremental builds with parallel processing.

## The Cache File

### Location

`.bengal-cache.json` in your project root

### Contents

```json
{
  "version": "1.0",
  "config_hash": "abc123...",
  "files": {
    "content/posts/my-post.md": {
      "hash": "def456...",
      "last_modified": 1696348800.0
    }
  },
  "dependencies": {
    "content/posts/my-post.md": [
      "templates/post.html",
      "templates/partials/article-card.html"
    ]
  },
  "taxonomies": {
    "tutorial": ["content/posts/my-post.md", "content/posts/another.md"]
  }
}
```

### Cache Management

✅ **Do commit** the cache file to version control for team consistency  
✅ **Do use** `.gitignore` patterns to exclude if preferred  
❌ **Don't** manually edit the cache file  
❌ **Don't** rely on cache for CI/CD (use clean builds)

## What Triggers Full Rebuilds?

Bengal automatically does a full rebuild when:

1. **Config file changed** - Safest to rebuild everything
2. **Cache file missing** - First build or after `clean`
3. **Cache version mismatch** - After Bengal upgrades
4. **`--no-cache` flag used** - Explicit override

## Best Practices

### During Development ✅

```bash
# Use incremental builds for fast iteration
bengal build --incremental --verbose

# Or use the dev server (incremental by default)
bengal serve
```

### For Production Builds ✅

```bash
# Use clean, full builds for deployment
bengal clean
bengal build --parallel
```

**Why?** Ensures no stale cache issues in production.

### In CI/CD Pipelines ✅

```bash
# Always start clean in CI
bengal clean && bengal build --parallel
```

**Why?** Reproducible builds are more important than speed in CI.

## Troubleshooting

### Problem: Pages not rebuilding when expected

**Symptom**: You changed something but the page didn't update.

**Solution**: 
```bash
# Use verbose mode to debug
bengal build --incremental --verbose

# Or force a clean build
bengal clean && bengal build
```

### Problem: Build seems slower than expected

**Symptom**: Incremental build isn't faster.

**Solution**: 
- First build always creates cache (no speedup expected)
- Very small sites may not benefit (overhead cost)
- Check if config file changes (forces full rebuild)

### Problem: Cache out of sync

**Symptom**: Unexpected behavior or missing content.

**Solution**:
```bash
# Delete cache and rebuild
rm .bengal-cache.json
bengal build
```

### Problem: Different results between incremental and full builds

**Symptom**: Inconsistent output.

**Solution**: Report this as a bug! Incremental and full builds should produce identical output.

## Technical Deep Dive

### Dependency Tracking Implementation

Bengal tracks dependencies during the rendering pipeline:

```python
# When a page renders
page.md → parser → template_engine
                        ↓
            tracks: template.html
                    partial.html
                    includes/header.html
```

The `DependencyTracker` class records every template, partial, and include used during rendering.

### Performance Characteristics

| Operation | Complexity | Cost |
|-----------|-----------|------|
| Hash calculation | O(n) | ~0.5ms per file |
| Dependency lookup | O(1) | ~0.001ms |
| Cache save/load | O(n) | ~10ms for 1000 files |
| Rebuild decision | O(1) | ~0.001ms per file |

Where n = file size in bytes.

### Cache File Growth

The cache file grows linearly with site size:

- 10 pages: ~2 KB
- 100 pages: ~15 KB
- 1000 pages: ~150 KB
- 10000 pages: ~1.5 MB

Even for very large sites, cache files remain manageable.

## Configuration Options

### Enable/Disable

```toml
[build]
incremental = true  # Enable incremental builds
```

### Cache Location (Future)

Currently fixed at `.bengal-cache.json`, but future versions may allow:

```toml
[build]
cache_dir = ".bengal-cache"  # Custom cache directory
```

## Comparison with Other Tools

| Tool | Incremental Builds | Dependency Tracking | Performance |
|------|-------------------|---------------------|-------------|
| Bengal | ✅ Full support | ✅ Templates + Content | 18-42x faster |
| Hugo | ✅ Partial support | ⚠️ Limited | Varies |
| Jekyll | ❌ Regeneration only | ❌ No tracking | Slow |
| Gatsby | ✅ Full support | ✅ GraphQL queries | Fast |

## Learn More

- [Parallel Processing](/docs/parallel-processing/) - Combine with incremental for maximum speed
- [Performance Optimization](/guides/performance-optimization/) - Additional performance tips
- [Build Cache Architecture](/docs/architecture/) - Technical implementation details

## Feedback

Found an issue with incremental builds? [Report it on GitHub](https://github.com/bengal-ssg/bengal/issues).

