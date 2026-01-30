---
title: Large Site Optimization
nav_title: Large Sites
description: Build and render 5K-100K+ pages efficiently with streaming, parallel processing, and query indexes
weight: 10
type: doc
icon: server
tags:
- performance
- large-sites
- streaming
- query-indexes
keywords:
- large site
- streaming build
- memory optimization
- query indexes
- parallel builds
- performance
- scale
category: how-to
---
# Large Site Optimization

Bengal is designed for sites with thousands of pages. This guide covers strategies for sites beyond 5,000 pages.

## Quick Start

For sites with 5K+ pages:

```bash
# Memory-optimized build
bengal build --memory-optimized --fast

# Full incremental + parallel + fast
bengal build --incremental --fast
```

---

## Strategy Overview

| Site Size | Recommended Strategy | Build Time |
|-----------|---------------------|------------|
| <500 pages | Default (no changes needed) | 1-3s |
| 500-5K pages | Default (parallel + incremental enabled) | 3-15s |
| 5K-20K pages | `--memory-optimized` | 15-60s |
| 20K+ pages | Full optimization stack | 1-5min |

---

## 1. Memory-Optimized Builds (Streaming Mode)

For sites with 5K+ pages, enable streaming mode:

```bash
bengal build --memory-optimized
```

### How It Works

1. **Builds knowledge graph** to understand page connectivity
2. **Renders hubs first** (highly connected pages) and keeps them in memory
3. **Streams leaves** in batches and releases memory immediately
4. **Result**: 80-90% memory reduction

### When to Use

- Sites with 5K+ pages
- CI runners with limited memory
- Docker containers with memory limits
- Local machines with limited RAM

:::{warning}
`--memory-optimized` and `--perf-profile` cannot be used together (profiler doesn't work with batched rendering).
:::

---

## 2. Query Indexes (O(1) Lookups)

Replace O(n) page filtering with O(1) index lookups in templates.

### The Problem

```kida
{# O(n) - scans ALL pages on every request #}
{% let blog_posts = site.pages | where('section', 'blog') %}
```

On a 10K page site, this filter runs 10,000 comparisons.

### The Solution

```kida
{# O(1) - instant hash lookup #}
{% let blog_posts = site.indexes.section.get('blog') | resolve_pages %}
```

### Built-in Indexes

| Index | Key Type | Example |
|-------|----------|---------|
| `section` | Section name | `site.indexes.section.get('blog')` |
| `author` | Author name | `site.indexes.author.get('Jane')` |
| `category` | Category | `site.indexes.category.get('tutorial')` |
| `date_range` | Year or Year-Month | `site.indexes.date_range.get('2024')` |

### Usage Examples

**Section-based listing:**

```kida
{% let blog_posts = site.indexes.section.get('blog') | resolve_pages %}
{% for post in blog_posts | sort_by('date', reverse=true) %}
  <h2>{{ post.title }}</h2>
{% end %}
```

**Author archive:**

```kida
{% let author_posts = site.indexes.author.get('Jane Smith') | resolve_pages %}
<p>{{ author_posts | length }} posts by Jane</p>
```

**Monthly archives:**

```kida
{% let jan_posts = site.indexes.date_range.get('2024-01') | resolve_pages %}
{% for post in jan_posts %}
  {{ post.title }}
{% end %}
```

### Performance Impact

| Pages | O(n) Filter | Query Index |
|-------|-------------|-------------|
| 1K | 2ms | <0.1ms |
| 10K | 20ms | <0.1ms |
| 100K | 200ms | <0.1ms |

---

## 3. Parallel Processing

Parallel processing is **auto-detected** based on page count and workload. Adjust worker count if needed:

```toml
# bengal.toml
[build]
max_workers = 8           # Optional: adjust based on CPU cores (auto-detected if omitted)
```

To force sequential processing (useful for debugging):

```bash
bengal build --no-parallel
```

### Free-Threaded Python

Bengal automatically detects Python 3.14t+ (free-threaded):

```bash
# 1.5-2x faster rendering
# Install free-threaded Python:
pyenv install 3.14t
python3.14t -m pip install bengal
```

When running on free-threaded Python:
- ThreadPoolExecutor gets true parallelism (no GIL contention)
- ~1.78x faster rendering on multi-core machines
- No code changes needed

---

## 4. Incremental Builds

Incremental builds are **automatic** — no configuration needed. First build is full, subsequent builds only rebuild changed content. Force a full rebuild if needed:

```bash
# Force full rebuild (skip cache)
bengal build --no-incremental
```

### What Gets Cached

- **Content parsing** — Markdown AST cached per file
- **Template rendering** — Output cached by content hash
- **Asset hashing** — Fingerprints cached
- **Query indexes** — Updated incrementally
- **Autodoc AST parsing** — Python modules cached to skip AST parsing (30-40% speedup for autodoc-heavy sites)
- **Asset dependencies** — Tracked during render-time (no HTML parsing needed)

### Cache Location

```tree
.bengal/
├── cache.json.zst          # Main build cache (compressed)
├── page_metadata.json.zst  # Page discovery cache
├── taxonomy_index.json.zst # Taxonomy index
├── indexes/                # Query indexes (section, author, etc.)
├── templates/              # Template bytecode cache
└── logs/                   # Build logs
```

### Clear Cache

```bash
# Clear all caches (forces cold rebuild)
bengal clean --cache

# Clear output and cache
bengal clean --all
```

---

## 5. Fast Mode

Combine all optimizations for maximum speed:

```bash
bengal build --fast
```

`--fast` enables:
- Quiet output (minimal console I/O)
- Suppresses verbose logging
- Parallelism auto-detected as normal
- **Skips HTML formatting** (raw HTML output, ~10-15% faster)

:::{note}
Fast mode skips HTML pretty-printing and minification. Output is still valid HTML but not formatted. Use for development and CI builds where formatting doesn't matter.
:::

---

## 6. Build Profiling

Identify bottlenecks:

```bash
# Generate performance profile
bengal build --perf-profile

# View results
python -m pstats .bengal/profiles/profile.stats
```

### Template Profiling

Find slow templates:

```bash
bengal build --profile-templates
```

**Output:**

```text
Template Rendering Times:
  layouts/blog.html: 1.2s (340 pages, 3.5ms avg)
  layouts/docs.html: 0.8s (890 pages, 0.9ms avg)
  partials/nav.html: 0.3s (included 1230 times)
```

---

## 7. Content Organization

### Split Large Sections

If one section has 5K+ pages, consider splitting:

```tree
content/
├── blog/
│   ├── 2024/     # 500 pages
│   ├── 2023/     # 800 pages
│   └── archive/  # 3000+ pages (separate pagination)
```

### Use Pagination

Don't render 1000 items on one page:

```yaml
# Paginate blog listing
pagination:
  enabled: true
  per_page: 20
```

### Lazy-Load Heavy Content

Move rarely-accessed content to separate pages:

```kida
{# Don't: render full changelog inline #}
{{ include('changelog.html') }}

{# Do: link to separate page #}
<a href="/changelog/">View full changelog</a>
```

---

## 8. CI/CD Optimization

### GitHub Actions Example

```yaml
jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Cache Bengal
        uses: actions/cache@v4
        with:
          path: .bengal
          key: bengal-${{ hashFiles('content/**/*.md') }}

      - name: Build
        run: bengal build --fast --environment production
```

### Docker Memory Limits

```dockerfile
# Use memory-optimized for container builds
CMD ["bengal", "build", "--memory-optimized", "--fast"]
```

---

## 9. Monitoring Build Health

Track build performance over time:

```bash
# Detailed build stats
bengal build --verbose
```

**Output:**

```text
Build Summary:
  Total Pages: 15,432
  Rendered: 342 (incremental)
  Skipped: 15,090 (cached)
  Duration: 12.3s
  Memory Peak: 245MB
  Pages/sec: 1,254
```

---

## Quick Reference

```bash
# Memory-efficient large site build
bengal build --memory-optimized --fast

# Profile to find bottlenecks
bengal build --perf-profile --profile-templates

# Force full rebuild
bengal build --no-incremental

# Clear all caches
bengal clean --cache

# Clear output and cache
bengal clean --all
```

---

## Troubleshooting

### Build runs out of memory

1. Enable streaming: `--memory-optimized`
2. Use `bengal build --dev --verbose` to see memory usage
3. Increase swap space

### Build is slow despite caching

1. Check what's invalidating cache: `bengal build --verbose`
2. Profile templates: `--profile-templates`
3. Check for O(n) filters in templates (use query indexes)

### Incremental not working

1. Ensure `.bengal/` is not gitignored for local dev
2. Run `bengal clean --cache` to reset
3. Check for template changes that invalidate all pages

---

:::{seealso}
- [[docs/building/performance|Performance Overview]]
- [[docs/reference/cheatsheet|CLI Cheatsheet]]
:::
