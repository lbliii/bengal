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

Bengal's build system is orchestrated by the `BuildOrchestrator` and executes in 21 distinct phases.

## Build Phases Overview

The build executes the following phases in sequence:

| Group | Phases | Description |
|-------|--------|-------------|
| **Initialization** | 1-5 | Font processing, template validation, content discovery, caching |
| **Content Setup** | 6-11 | Sections, taxonomies, menus, related posts, indexes |
| **Rendering** | 13-16 | Asset processing, page rendering, dependency tracking |
| **Finalization** | 17-21 | Post-processing, cache save, health checks, cleanup |

## Key Phases

### Initialization (Phases 1-5)

*   **Font Processing**: Download Google Fonts and generate CSS if configured.
*   **Template Validation**: Validate template syntax (optional, strict mode only).
*   **Content Discovery**: Scan `content/` directory, create `Page` objects.
*   **Schema Validation**: If `collections.py` exists, frontmatter is validated against defined schemas.
*   **Cache Integration**: Load previous build cache for incremental builds.

### Content Setup (Phases 6-11)

*   **Section Finalization**: Ensures every folder has a corresponding Section object (creating virtual sections if `_index.md` is missing).
*   **Cascading**: Metadata from section `_index.md` files is applied to all descendant pages.
*   **Taxonomy Collection**: Tags, categories, and other terms are collected from all pages.
*   **Menu Generation**: Navigation menus are built from config and page frontmatter.
*   **Related Posts**: Computes related posts based on tag overlap.

### Rendering (Phases 13-16)

This is the heavy lifting phase.

*   **Asset Processing**: Copy, minify, optimize, and fingerprint assets.
*   **Parallel Rendering**: Pages are rendered in parallel using `ThreadPoolExecutor`.
    *   Bengal supports **Free-Threaded Python (PEP 703)**, allowing true parallelism without the GIL on Python 3.14+.
*   **Jinja2 Context**: Each page is rendered with the `site` and `page` context.
*   **Markdown Parsing**: Markdown content is converted to HTML (cached by file hash).

### Finalization (Phases 17-21)

*   **Sitemap**: `sitemap.xml` is generated.
*   **RSS**: RSS feeds are built.
*   **Output Formats**: JSON and LLM text files are generated.
*   **Health Checks**: Validation runs (if enabled).
*   **Cache Save**: Persist cache for incremental builds.

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
*   **Cached Pages**: ~0 ms (Metadata loaded from JSON).
*   **Rendered Pages**: ~10-50 ms per page (depending on complexity).
*   **Parallelism**: Scales linearly with CPU cores on Python 3.14+ with free-threading enabled.

## Memory Optimization

For large sites (>5,000 pages), Bengal's incremental build system minimizes memory usage by:

*   **Lazy Loading**: Unchanged pages load as lightweight `PageProxy` objects with only metadata.
*   **Dependency Tracking**: Only affected pages are fully loaded and re-rendered.
*   **Section-Level Filtering**: Entire unchanged sections are skipped during change detection.
