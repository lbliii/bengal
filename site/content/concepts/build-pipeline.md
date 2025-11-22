---
title: The Build Pipeline
description: A deep dive into Bengal's build orchestration, phases, and incremental build system.
weight: 30
---

For those who need to understand exactly what happens when they run `bengal build`, this guide breaks down the **Build Pipeline**.

Bengal's build system is orchestrated by the `BuildOrchestrator` and executes in distinct phases.

## The Phases

### 1. Initialization
*   **Config Loading**: Bengal loads `bengal.toml` (or `config/` directory) and establishes the environment context.
*   **Cache Loading**: If incremental build is enabled, the previous build cache (`.bengal/cache.json`) is loaded.

### 2. Content Discovery (`ContentOrchestrator`)
*   **Scanning**: The `content/` directory is scanned recursively.
*   **Page Creation**: `Page` objects are created for each markdown file.
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
    *   **Template Change**: If `layouts/_default/single.html` changes, all pages using that template rebuild.
    *   **Config Change**: If `bengal.toml` changes, a **Full Rebuild** is triggered.

### Performance
*   **Cached Pages**: ~0ms (Metadata loaded from JSON).
*   **Rendered Pages**: ~10-50ms per page (depending on complexity).
*   **Parallelism**: Scales linearly with CPU cores on Python 3.13t+.

## Memory Optimization

For massive sites (>10,000 pages), Bengal offers a `--memory-optimized` flag. This uses a **Streaming Orchestrator** to process pages in batches, keeping memory usage constant rather than linear to site size.

