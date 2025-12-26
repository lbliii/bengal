---
title: Cache Template Fragments
nav_title: Cache Fragments
description: Improve performance with built-in fragment caching
weight: 40
type: doc
draft: false
lang: en
tags:
- how-to
- templates
- kida
- performance
keywords:
- fragment caching
- cache directive
- performance
category: guide
---

# Cache Template Fragments

Learn how to use KIDA's built-in fragment caching to improve template rendering performance.

## Goal

Cache expensive template fragments to reduce build time and improve performance.

## When to Use Fragment Caching

Cache fragments when you have:
- Expensive computations (navigation trees, related posts)
- External API calls (weather, social feeds)
- Complex data processing (statistics, aggregations)
- Static content that changes infrequently

## Basic Caching

### Simple Cache

Cache a fragment with a static key:

```kida
{% cache "sidebar-nav" %}
  {{ build_nav_tree(site.pages) }}
{% end %}
```

### Dynamic Cache Keys

Use expressions to create dynamic cache keys:

```kida
{% cache "post-" ~ post.id %}
  <article>
    <h1>{{ post.title }}</h1>
    {{ post.content | safe }}
  </article>
{% end %}

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

Set a time-to-live (TTL) for cache expiration:

```kida
{% cache "weather", ttl="5m" %}
  {{ fetch_weather() }}
{% end %}

{% cache "social-feed", ttl="1h" %}
  {{ fetch_social_feed() }}
{% end %}

{% cache "stats-" ~ site.nav_version, ttl="30s" %}
  {{ calculate_site_stats() }}
{% end %}
```

**TTL formats**:
- `"5m"` - 5 minutes
- `"1h"` - 1 hour
- `"30s"` - 30 seconds
- `"2d"` - 2 days

## Common Use Cases

### Navigation Tree

Cache expensive navigation tree building:

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

### Related Posts

Cache related post calculations:

```kida
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

### Site Statistics

Cache expensive statistics calculations:

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

### Author Information

Cache author data processing:

```kida
{% cache "author-" ~ page.author %}
  {% let author = site.authors[page.author] | default({}) %}
  {% let author_posts = site.pages
    |> where('author', page.author)
    |> where('type', 'blog')
    |> length %}
  
  <div class="author-card">
    {% if author.name %}
      <h3>{{ author.name }}</h3>
    {% end %}
    {% if author.bio %}
      <p>{{ author.bio }}</p>
    {% end %}
    <p>{{ author_posts }} posts</p>
  </div>
{% end %}
```

### Tag Cloud

Cache tag cloud generation:

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

### Version-Based Invalidation

Use site version for cache invalidation:

```kida
{% cache "sidebar-" ~ site.nav_version %}
  {# Cache invalidates when nav_version changes #}
  {{ build_sidebar() }}
{% end %}
```

### Content-Based Invalidation

Invalidate based on content changes:

```kida
{% cache "post-meta-" ~ post.id ~ "-" ~ post.updated_at %}
  {# Cache invalidates when post is updated #}
  <div class="post-meta">
    <time>{{ post.date | dateformat('%B %d, %Y') }}</time>
    <span>{{ post.reading_time }} min read</span>
  </div>
{% end %}
```

### Manual Invalidation

Clear cache manually:

```bash
# Clear all caches
bengal clean --cache

# Or delete cache directory
rm -rf .bengal/cache/kida/
```

## Performance Tips

### Cache Expensive Operations

```kida
{# Expensive: Cache it #}
{% cache "expensive-calculation" %}
  {% let result = expensive_function(site.pages) %}
  {{ result }}
{% end %}

{# Cheap: Don't cache #}
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

### Avoid Over-Caching

Don't cache everything:

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

Here's a complete template using fragment caching:

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

## Next Steps

- [Create Custom Template](/docs/theming/templating/kida/create-custom-template/) — Build templates with caching
- [KIDA Syntax Reference](/docs/reference/kida-syntax/) — Complete syntax documentation
- [Performance Guide](/docs/building/performance/) — More performance tips

:::{seealso}
- [KIDA Tutorial](/docs/tutorials/getting-started-with-kida/) — Learn KIDA from scratch
- [Template Functions](/docs/theming/templating/functions/) — Available filters and functions
:::

