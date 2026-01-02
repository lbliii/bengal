---
title: Caching
description: Automatic and manual template caching
weight: 20
icon: zap
---

# Caching

Kida provides two levels of template caching: automatic block caching for site-wide content and manual fragment caching for expensive operations.

## Automatic Block Caching

Kida analyzes templates at compile time and automatically caches blocks that only depend on site-wide data. Blocks that only reference site-wide variables (like `site.*`, `config.*`) are rendered **once per build** and reused across all pages. For example, on a 500-page site, a site-scoped footer block renders once instead of 500 times.

## Fragment Caching

Use `{% cache %}` for manual control over expensive operations like navigation trees, related posts, and statistics.

```kida
{% cache "related-posts-" ~ post.id %}
  {% let related = site.pages
    |> where('type', 'blog')
    |> where('tags', post.tags[0])
    |> take(5) %}
  <ul>
    {% for item in related %}
      <li><a href="{{ item.url }}">{{ item.title }}</a></li>
    {% end %}
  </ul>
{% end %}
```

## Performance Impact

Automatic block caching provides significant performance improvements for site-scoped blocks. The following table illustrates theoretical savings assuming a 200-line footer block that depends only on site-wide data:

| Site Size | Lines Rendered (Before) | Lines Rendered (After) | Savings |
|-----------|------------------------|------------------------|---------|
| 100 pages | 20,000 | 200 | 99% |
| 500 pages | 100,000 | 200 | 99.8% |
| 1000 pages | 200,000 | 200 | 99.9% |

**Note:** These percentages are illustrative examples based on theoretical calculations. Actual savings depend on:
- Number of site-scoped blocks in your templates
- Size of each cached block
- Site structure and template complexity

To verify actual performance improvements, build your site with `--verbose` to see block cache statistics, or compare build times with and without caching enabled.

## Topics

:::{child-cards}
:columns: 2
:::
