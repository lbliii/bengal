---
title: Caching
description: Automatic and manual template caching
weight: 20
icon: zap
---

# Caching

Kida provides two levels of template caching: automatic block caching for site-wide content and manual fragment caching for expensive operations.

## Automatic Block Caching

Kida analyzes templates at compile time and automatically caches blocks that only depend on site-wide data. For a 500-page site, your footer renders once instead of 500 times.

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

| Site Size | Lines Rendered (Before) | Lines Rendered (After) | Savings |
|-----------|------------------------|------------------------|---------|
| 100 pages | 20,000 | 200 | 99% |
| 500 pages | 100,000 | 200 | 99.8% |
| 1000 pages | 200,000 | 200 | 99.9% |

## Topics

:::{child-cards}
:columns: 2
:::
