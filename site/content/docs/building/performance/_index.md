---
title: Performance
description: Optimize Bengal build performance
weight: 30
draft: false
lang: en
tags: [performance, optimization, speed]
keywords: [performance, speed, incremental, parallel, cache]
category: guide
---

# Performance

Speed up your Bengal builds with incremental building, parallel processing, and caching.

## Overview

Bengal is designed for performance:

- **Incremental builds** — Only rebuild changed content
- **Parallel processing** — Multi-core rendering
- **Smart caching** — Skip redundant work
- **Lazy loading** — Load content on demand

## Quick Wins

```toml
# bengal.toml
[build]
parallel = true
incremental = true
cache = true
```

## Incremental Builds

Only rebuild pages affected by changes:

```bash
# First build (full)
bengal build

# Subsequent builds (incremental)
bengal build  # Automatically detects changes
```

## Parallel Processing

Use multiple CPU cores:

```toml
[build]
parallel = true
workers = 4  # Or "auto" for CPU count
```

## Caching

Bengal caches:

- **Content parsing** — Markdown processing results
- **Template compilation** — Compiled Jinja2 templates
- **Asset processing** — Fingerprints and transformations

Clear cache if needed:

```bash
bengal clean --cache
```

## In This Section

- **[Incremental Builds](/docs/building/performance/incremental/)** — How incremental builds work
- **[Parallel Processing](/docs/building/performance/parallel/)** — Multi-core configuration
- **[Caching](/docs/building/performance/caching/)** — Cache system details


