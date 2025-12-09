---
title: Post-Processing
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
- Includes all pages with metadata
- Configurable priority and change frequency
- Validates URL structure
- Follows sitemap.xml protocol

### Configuration

```toml
[sitemap]
enabled = true
changefreq = "weekly"  # always, hourly, daily, weekly, monthly, yearly, never
priority = 0.5  # 0.0 to 1.0
```

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
- Includes recent posts
- Supports custom descriptions
- Configurable item count
- Full content or excerpts

### Configuration

```toml
[rss]
enabled = true
limit = 20  # Number of items in feed
full_content = false  # true for full HTML, false for excerpts
```

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

## Link Validator (`bengal/rendering/link_validator.py`)

### Purpose
Validates internal and external links

### Features
- Validates internal and external links
- Reports broken links
- Can be extended for comprehensive validation
- Configurable checking depth
- Supports link ignoring patterns

### Configuration

```toml
[validation]
check_internal_links = true
check_external_links = false  # Can be slow
ignore_patterns = ["^#", "^mailto:", "^tel:"]
```

### Validation Process
1. Extract all links from rendered HTML
2. Categorize as internal or external
3. For internal links:
   - Check if target page exists
   - Verify anchor IDs exist
4. For external links (optional):
   - Make HEAD request
   - Check response status
5. Report broken links with context

### Output Example

```
Link Validation Results:
✓ 245 internal links valid
✗ 3 broken links found:
  - /docs/missing-page/ (referenced in /blog/post.html)
  - /guide/#invalid-anchor (referenced in /index.html)
  - https://example.com/404 (referenced in /links.html)
```

## Special Page Generation

### 404 Page
Generated automatically if `templates/404.html` exists

### Search Index
JSON index for client-side search (if enabled)

### Archive Pages
Chronological page listings by year/month

## Parallel Post-Processing

Post-processing tasks can run in parallel for better performance:

```python
# tasks run concurrently
with ThreadPoolExecutor() as executor:
    futures = [
        executor.submit(generate_sitemap),
        executor.submit(generate_rss),
        executor.submit(validate_links),
        executor.submit(generate_search_index),
    ]
    wait(futures)
```

**Impact**: 2x speedup measured on typical sites
