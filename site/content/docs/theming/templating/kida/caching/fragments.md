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

Set time-to-live for cache expiration:

```kida
{% cache "stats", ttl="1h" %}
  {{ calculate_site_stats() }}
{% end %}
```

**TTL formats:**
- `"30s"` — 30 seconds
- `"5m"` — 5 minutes
- `"1h"` — 1 hour
- `"2d"` — 2 days

## Common Use Cases

### Related Posts

```kida
{% cache "related-posts-" ~ page.id %}
  {% let related = site.pages
    |> where('type', 'blog')
    |> where('tags', page.tags[0] | default(''))
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
{% cache "site-stats", ttl="1h" %}
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
{% cache "tag-cloud", ttl="1h" %}
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

```bash
# Clear all caches
bengal clean --cache

# Or delete cache directory
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

### Use Appropriate TTLs

```kida
{# Changes frequently: Short TTL #}
{% cache "recent-posts", ttl="5m" %}
  {{ get_recent_posts() }}
{% end %}

{# Changes rarely: Long TTL #}
{% cache "site-stats", ttl="24h" %}
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
  fragment_cache_size: 1000  # Max cached fragments
  fragment_ttl: 300.0         # Default TTL in seconds (5 min)
```

## Debugging

Check cache hit/miss rates:

```bash
# Build with verbose output
bengal build --verbose

# Check cache directory
ls -la .bengal/cache/kida/
```

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

  {% cache "tag-cloud", ttl="1h" %}
    {{ build_tag_cloud(site.tags) }}
  {% end %}
{% endblock %}
```
