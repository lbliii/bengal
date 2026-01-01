---
title: Post-Processing
nav_title: Post-Process
description: Site-wide operations after rendering - sitemap, RSS, and link validation
weight: 50
category: rendering
tags:
- rendering
- postprocess
- sitemap
- rss
- link-validation
- seo
keywords:
- post-processing
- sitemap
- RSS
- link validation
- SEO
- site generation
---

# Post-Processing

Post-processing runs after all pages are rendered and performs site-wide operations like sitemap generation, RSS feeds, and link validation.

## Sitemap Generator (`bengal/postprocess/sitemap.py`)

### Purpose
Generates XML sitemap for SEO

### Features
- Generates XML sitemap for SEO
- Includes all pages with metadata (respects `visibility.sitemap`)
- Version-aware priority (latest: 0.8, older: 0.3, default: 0.5)
- i18n support with `hreflang` alternate links
- Validates URL structure
- Follows sitemap.xml protocol

### Configuration

```toml
# Enable/disable sitemap generation (default: true)
generate_sitemap = true
```

Sitemap behavior is automatic:
- **Change frequency**: Always `weekly`
- **Priority**: Computed from version status (latest versions get higher priority)
- **Exclusions**: Pages with `hidden: true` or `visibility.sitemap: false` are excluded

### Output Format

```xml
<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url>
    <loc>https://example.com/</loc>
    <lastmod>2025-10-19</lastmod>
    <changefreq>weekly</changefreq>
    <priority>1.0</priority>
  </url>
  <url>
    <loc>https://example.com/blog/post/</loc>
    <lastmod>2025-10-18</lastmod>
    <changefreq>weekly</changefreq>
    <priority>0.8</priority>
  </url>
</urlset>
```

## RSS Generator (`bengal/postprocess/rss.py`)

### Purpose
Generates RSS feed for blog posts

### Features
- Generates RSS 2.0 feed
- Includes 20 most recent posts with dates
- Uses page description or excerpt (first 200 chars)
- Sorted by date (newest first)
- Respects `visibility.rss` and draft status
- i18n support (per-locale feeds when enabled)

### Configuration

```toml
# Enable/disable RSS generation (default: true)
generate_rss = true
```

RSS behavior is automatic:
- **Item limit**: 20 most recent pages with dates
- **Content**: Page description from frontmatter, or excerpt from content
- **Exclusions**: Drafts and pages with `visibility.rss: false` are excluded

### Output Format

```xml
<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom">
  <channel>
    <title>My Site</title>
    <link>https://example.com/</link>
    <description>A Bengal SSG site</description>
    <language>en</language>
    <lastBuildDate>Sat, 19 Oct 2025 00:00:00 +0000</lastBuildDate>
    <atom:link href="https://example.com/rss.xml" rel="self" type="application/rss+xml"/>

    <item>
      <title>My Blog Post</title>
      <link>https://example.com/blog/my-post/</link>
      <guid>https://example.com/blog/my-post/</guid>
      <pubDate>Fri, 18 Oct 2025 00:00:00 +0000</pubDate>
      <description>Post description or excerpt</description>
    </item>
  </channel>
</rss>
```

## Link Validator (`bengal/health/validators/links.py`)

### Purpose
Validates internal and external links

### Features
- Validates internal links resolve to existing pages
- Handles relative paths and fragments
- Supports trailing slash variations
- Caches validation results for performance
- Integrates with health check system
- External link checking handled separately via `bengal health linkcheck` command

### Configuration

```toml
# Enable/disable internal link validation during build (default: true)
validate_links = true
```

### Validation Process

**Internal links** (validated during build):
1. Extract links from rendered pages
2. Resolve relative paths against page URL
3. Check if target page exists in site
4. Report broken links with source context

**External links** (separate command):
```bash
bengal health linkcheck --external
```

**Automatically skipped**:
- External URLs (`http://`, `https://`)
- Special protocols (`mailto:`, `tel:`, `data:`)
- Template syntax (`{{`, `${`)
- Source file references (`.py` files from autodoc)

### Output Example

Build-time validation reports internal broken links:

```text
Found 2 broken internal links:
  content/blog/post.md: /docs/missing-page/
  content/index.md: /guide/old-section/
```

External link checking (via `bengal health linkcheck`):

```text
Checking 156 external links...
✓ 153 links valid
✗ 3 broken:
  - https://example.com/404 (in /links.html)
  - https://old-api.example.com (in /docs/api.html)
```

## Special Page Generation

### 404 Page
Generated automatically if `templates/404.html` exists

### Search Index
JSON index for client-side search (if enabled)

### Archive Pages
Chronological page listings by year/month

## Parallel Post-Processing

Post-processing tasks run in parallel when multiple tasks are enabled:

```python
# Actual implementation in bengal/orchestration/postprocess.py
with ThreadPoolExecutor(max_workers=len(tasks)) as executor:
    futures = {executor.submit(task_fn): name for name, task_fn in tasks}
    for future in as_completed(futures):
        future.result()  # Raises on error
```

**Tasks that run in parallel**:
- Sitemap generation
- RSS feed generation
- Output formats (JSON, TXT, LLM)
- Special pages (404, search)
- Redirect pages
- Social cards (if enabled)

**Incremental builds**: Skip expensive tasks (sitemap, RSS, social cards) for faster dev server response. Output formats always regenerate to keep search index current.
