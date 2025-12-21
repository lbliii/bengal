---
title: Build Pipeline
nav_title: Build
description: How Bengal orchestrates builds, processes content, and performs incremental
  builds
weight: 30
type: doc
draft: false
lang: en
tags:
- build
- pipeline
- orchestration
- incremental
keywords:
- build pipeline
- orchestration
- incremental builds
- performance
category: documentation
---

This guide explains what happens when you run `bengal build`.

Bengal's build system is orchestrated by the `BuildOrchestrator` and executes in distinct phases.

## The Phases

### 1. Initialization
*   **Config Loading**: Bengal loads `bengal.toml` (or `config/` directory) and establishes the environment context.
*   **Cache Loading**: If incremental build is enabled, the previous build cache (`.bengal/cache.json`) is loaded.

### 2. Content Discovery (`ContentOrchestrator`)
*   **Scanning**: The `content/` directory is scanned recursively.
*   **Page Creation**: `Page` objects are created for each markdown file.
*   **Schema Validation**: If `collections.py` exists, frontmatter is validated against defined schemas (see [[docs/content/collections|Content Collections]]).
*   **Lazy Loading**: In incremental builds, unchanged pages are loaded as `PageProxy` objects (lightweight metadata only), saving parsing time.
*   **Section Registry**: A path-based registry is built for O(1) section lookups.

### 3. Structure & Metadata
*   **Section Finalization**: Ensures every folder has a corresponding Section object (creating virtual sections if `_index.md` is missing).
*   **Cascading**: Metadata from section `_index.md` files is applied to all descendant pages (e.g., `cascade: type: doc`).
*   **URL Generation**: Output paths and URLs are computed for all pages.

### 4. Taxonomy & Menus
*   **Taxonomy Collection**: Tags, categories, and other terms are collected from all pages.
*   **Menu Generation**: Navigation menus are built from config and page frontmatter.
*   **Incremental Optimization**: Only changed pages are re-scanned for taxonomy updates.

### 5. Asset Processing (`AssetOrchestrator`)
*   **Discovery**: Assets are found in `assets/` and theme directories.
*   **Processing**: SCSS is compiled, JS is minified, and images are optimized (if pipelines are enabled).
*   **Fingerprinting**: Hashes are generated for cache busting (e.g., `style.a1b2c3.css`).

### 6. Rendering (`RenderOrchestrator`)
This is the heavy lifting phase.

*   **Parallel Execution**: Pages are rendered in parallel using `ThreadPoolExecutor`.
    *   Bengal supports **Free-Threaded Python (3.13t+)**, allowing true parallelism without the GIL.
*   **Jinja2 Context**: Each page is rendered with the `site` and `page` context.
*   **Markdown Parsing**: Markdown content is converted to HTML (cached by file hash).

### 7. Post-Processing
*   **Sitemap**: `sitemap.xml` is generated.
*   **RSS**: RSS feeds are built.
*   **Validation**: Internal links are checked (if `--strict` is enabled).

## Incremental Builds

Bengal's incremental build system relies on **Change Detection** and **Dependency Tracking**.

### How it Works
1.  **Change Detection**: Files are hashed. If `content/post.md` hasn't changed, its hash matches the cache.
2.  **Smart Filtering**: The orchestrator calculates a `pages_to_build` list.
3.  **Dependency Graph**:
    *   **Direct Change**: The file itself changed.
    *   **Navigation Dependency**: If Page A links to Page B, and Page B changes title, Page A must rebuild (to update the link text).
    *   **Template Change**: If `templates/page.html` changes, all pages using that template rebuild.
    *   **Config Change**: If `bengal.toml` changes, a **Full Rebuild** is triggered.

### Performance
*   **Cached Pages**: ~0ms (Metadata loaded from JSON).
*   **Rendered Pages**: ~10-50ms per page (depending on complexity).
*   **Parallelism**: Scales linearly with CPU cores on Python 3.13t+.

## Memory Optimization

For massive sites (>10,000 pages), Bengal offers a `--memory-optimized` flag. This uses a **Streaming Orchestrator** to process pages in batches, keeping memory usage constant rather than linear to site size.

## Reactive Dataflow Pipeline

Bengal also provides a **Reactive Dataflow Pipeline** for declarative, stream-based builds:

```python
from bengal.pipeline import Pipeline

pipeline = (
    Pipeline("build")
    .source("files", discover_files)
    .map("parse", parse_markdown)
    .parallel(workers=4)
    .for_each("write", write_output)
)

result = pipeline.run()
```

Key benefits:

*   **Declarative**: Define what, not how
*   **Automatic Caching**: Version-based cache invalidation
*   **Watch Mode**: Built-in file watching with debouncing
*   **Composable**: Chain operations fluently

See [[docs/reference/architecture/core/pipeline|Reactive Pipeline Architecture]] for details.
