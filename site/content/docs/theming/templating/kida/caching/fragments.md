---
title: Fragment Caching
nav_title: Fragment Caching
description: Manual caching for expensive template operations
weight: 20
type: doc
tags:
- how-to
- kida
- caching
- performance
---

# Fragment Caching

Use Kida's built-in `{% cache %}` directive for manual control over expensive template operations.

## When to Use Fragment Caching

Cache fragments when you have:

- Expensive computations (navigation trees, related posts)
- Complex data processing (statistics, aggregations)
- Repeated calculations across pages

## Basic Caching

### Simple Cache

```kida
{% cache "sidebar-nav" %}
  {{ build_nav_tree(site.pages) }}
{% end %}
```

### Dynamic Cache Keys

Use expressions to create unique cache keys:

```kida
{% cache "related-" ~ post.id %}
  {% let related = site.pages
    |> where('tags', post.tags[0])
    |> take(5) %}
  <aside>
    {% for item in related %}
      <a href="{{ item.url }}">{{ item.title }}</a>
    {% end %}
  </aside>
{% end %}
```

### Cache with TTL

Fragment cache uses a global TTL configured at the environment level. All cached fragments share the same expiration time set in `bengal.yaml`:

```kida
{% cache "stats" %}
  {{ calculate_site_stats() }}
{% end %}
```

**Note:** Per-key TTL (e.g., `ttl="1h"`) is not currently supported. All fragments use the environment-level `fragment_ttl` setting. See [Configuration](#configuration) to set the global TTL.

## Common Use Cases

### Related Posts

```kida
{% cache "related-posts-" ~ page.id %}
  {% let related = site.pages
    |> where('type', 'blog')
    |> where('tags', page.tags[0] ?? '')
    |> where('id', '!=', page.id)
    |> sort_by('date', reverse=true)
    |> take(5) %}

  {% if related %}
    <aside class="related-posts">
      <h2>Related Posts</h2>
      <ul>
        {% for item in related %}
          <li>
            <a href="{{ item.url }}">{{ item.title }}</a>
            <span>{{ item.date | days_ago }} days ago</span>
          </li>
        {% end %}
      </ul>
    </aside>
  {% end %}
{% end %}
```

### Navigation Tree

```kida
{% cache "nav-tree-" ~ site.nav_version %}
  {% let nav = get_nav_tree(page) %}
  <nav>
    {% for item in nav %}
      <a href="{{ item.url }}">{{ item.title }}</a>
    {% end %}
  </nav>
{% end %}
```

### Site Statistics

```kida
{% cache "site-stats" %}
  {% let total_posts = site.pages |> where('type', 'blog') |> length %}
  {% let total_docs = site.pages |> where('type', 'doc') |> length %}
  {% let total_tags = site.tags |> length %}

  <div class="stats">
    <div class="stat">
      <span class="value">{{ total_posts }}</span>
      <span class="label">Posts</span>
    </div>
    <div class="stat">
      <span class="value">{{ total_docs }}</span>
      <span class="label">Docs</span>
    </div>
    <div class="stat">
      <span class="value">{{ total_tags }}</span>
      <span class="label">Tags</span>
    </div>
  </div>
{% end %}
```

### Tag Cloud

```kida
{% cache "tag-cloud" %}
  {% let tags = site.tags
    |> items()
    |> sort_by('count', reverse=true)
    |> take(20) %}

  <div class="tag-cloud">
    {% for tag in tags %}
      <a href="{{ tag_url(tag.name) }}" class="tag tag-{{ tag.count }}">
        {{ tag.name }}
      </a>
    {% end %}
  </div>
{% end %}
```

## Cache Invalidation

### Version-Based

```kida
{% cache "sidebar-" ~ site.nav_version %}
  {# Cache invalidates when nav_version changes #}
  {{ build_sidebar() }}
{% end %}
```

### Content-Based

```kida
{% cache "post-meta-" ~ post.id ~ "-" ~ post.updated_at %}
  {# Cache invalidates when post is updated #}
  <div class="post-meta">
    <time>{{ post.date | dateformat('%B %d, %Y') }}</time>
  </div>
{% end %}
```

### Manual Invalidation

Fragment cache is stored in memory and persists only during the build process. To clear it:

**During build:**

- Fragment cache is automatically cleared when you restart the build process
- Use `bengal clean --cache` to clear all caches (including bytecode cache)

**Note:** The fragment cache is separate from the bytecode cache:

- **Fragment cache**: In-memory LRU cache for `{% cache %}` block outputs (cleared on process restart)
- **Bytecode cache**: Disk cache at `.bengal/cache/kida/` for compiled template bytecode (persists across builds)

```bash
# Clear all caches (output + bytecode cache)
bengal clean --cache

# Clear only bytecode cache (fragment cache is in-memory)
rm -rf .bengal/cache/kida/
```

## Best Practices

### Cache Expensive Operations

```kida
{# ✅ Expensive: Cache it #}
{% cache "expensive-calculation" %}
  {% let result = expensive_function(site.pages) %}
  {{ result }}
{% end %}

{# ❌ Cheap: Don't cache #}
{{ page.title }}
```

### Configure TTL Appropriately

Set the global TTL in `bengal.yaml` based on your content update frequency:

```yaml
kida:
  fragment_ttl: 300.0  # 5 minutes - good for frequently changing content
  # fragment_ttl: 3600.0  # 1 hour - good for rarely changing content
```

```kida
{# All fragments use the same TTL from configuration #}
{% cache "recent-posts" %}
  {{ get_recent_posts() }}
{% end %}

{% cache "site-stats" %}
  {{ calculate_stats() }}
{% end %}
```

### Don't Over-Cache

```kida
{# ❌ Don't cache simple variables #}
{% cache "title" %}
  {{ page.title }}
{% end %}

{# ✅ Cache expensive operations #}
{% cache "related-posts" %}
  {{ calculate_related_posts(page) }}
{% end %}
```

## Configuration

Configure cache settings in `bengal.yaml`:

```yaml
kida:
  fragment_cache_size: 1000  # Max cached fragments (LRU eviction)
  fragment_ttl: 300.0         # Global TTL in seconds for all fragments (5 min)
```

**Cache behavior:**

- `fragment_cache_size`: Maximum number of cached fragments. When exceeded, least recently used entries are evicted.
- `fragment_ttl`: Time-to-live in seconds applied to all cached fragments. Fragments expire after this duration regardless of access.
- Fragment cache is in-memory only and cleared when the build process ends.

## Debugging

**Fragment cache statistics:**

Fragment cache statistics are available programmatically via the Kida environment's `cache_info()` method. The fragment cache is in-memory and cleared on each build.

**Bytecode cache:**

The bytecode cache (compiled template bytecode) is stored on disk:

```bash
# Check bytecode cache directory
ls -la .bengal/cache/kida/

# Build with verbose output
bengal build --verbose
```

**Note:** Fragment cache (for `{% cache %}` blocks) and bytecode cache (for compiled templates) are separate systems with different storage locations and purposes.

## Complete Example

```kida
{% extends "baseof.html" %}

{% let post = page %}

{% block content %}
  <article class="blog-post">
    <header>
      <h1>{{ post.title }}</h1>

      {% cache "post-meta-" ~ post.id %}
        <div class="post-meta">
          <time>{{ post.date | dateformat('%B %d, %Y') }}</time>
          <span>{{ post.reading_time }} min read</span>
        </div>
      {% end %}
    </header>

    <div class="content">
      {{ post.content | safe }}
    </div>

    {% cache "related-posts-" ~ post.id %}
      {% let related = site.pages
        |> where('type', 'blog')
        |> where('tags', post.tags[0] | default(''))
        |> where('id', '!=', post.id)
        |> sort_by('date', reverse=true)
        |> take(5) %}

      {% if related %}
        <aside class="related-posts">
          <h2>Related Posts</h2>
          <ul>
            {% for item in related %}
              <li><a href="{{ item.url }}">{{ item.title }}</a></li>
            {% end %}
          </ul>
        </aside>
      {% end %}
    {% end %}
  </article>
{% endblock %}

{% block sidebar %}
  {% cache "sidebar-nav-" ~ site.nav_version %}
    {{ build_sidebar_nav(site.pages) }}
  {% end %}

  {% cache "tag-cloud" %}
    {{ build_tag_cloud(site.tags) }}
  {% end %}
{% endblock %}
```
