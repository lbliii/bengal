---
title: Operators
nav_title: Operators
description: Pipeline, optional chaining, and null coalescing operators
weight: 30
type: doc
tags:
- reference
- kida
- syntax
---

# Operators

Kida adds modern operators for data transformation and null-safe access.

## Pipeline Operator (`|>`)

The pipeline operator chains filters left-to-right:

```kida
{% let recent_posts = site.pages
  |> where('type', 'blog')
  |> where('draft', false)
  |> sort_by('date', reverse=true)
  |> take(10) %}
```

### Pipeline vs Pipe

Both `|` and `|>` compile to identical code:

```kida
{# These are functionally identical #}
{{ items |> where('published', true) |> sort_by('date') |> take(5) }}
{{ items |> where('published', true) |> sort_by('date') |> take(5) }}
```

| Syntax | Convention |
|--------|------------|
| `\|` | Inline expressions, Jinja2 familiarity |
| `\|>` | Multiline pipelines, functional style |

:::{note}
You cannot mix `|` and `|>` in the same expression. Pick one per chain.
:::

### Multiline Pipelines

Add inline comments to explain each step:

```kida
{% let recent_posts = site.pages
  |> where('type', 'blog')        {# Only blog posts #}
  |> where('draft', false)        {# Exclude drafts #}
  |> sort_by('date', reverse=true) {# Newest first #}
  |> take(10) %}                   {# Limit to 10 #}
```

### Filter Name Mapping

| Jinja2 Filter | Kida Filter | Description |
|--------------|-------------|-------------|
| `selectattr('key')` | `where('key', true)` | Boolean filter |
| `selectattr('key', 'eq', val)` | `where('key', val)` | Equality filter |
| `rejectattr('key')` | `where_not('key', true)` | Inverse boolean |
| `sort(attribute='key')` | `sort_by('key')` | Sort by attribute |
| `batch(n) \| first` | `take(n)` | Get first n items |
| `groupby('key')` | `group_by('key')` | Group by attribute |

## Optional Chaining (`?.`)

Safe navigation through potentially null values:

```kida
{{ user?.profile?.name ?? 'Anonymous' }}
{{ page?.metadata?.author?.avatar }}
{{ config?.social?.twitter?.handle }}
```

Compare to Jinja2's defensive coding:

```kida
{{ user.profile.name if user and user.profile and user.profile.name else 'Anonymous' }}
```

## Null Coalescing (`??`)

Concise fallback for null/undefined values:

```kida
{{ page.subtitle ?? page.title }}
{{ user.nickname ?? user.name ?? 'Guest' }}
{{ config.theme ?? 'default' }}
```

### Precedence Gotcha

The `??` operator has lower precedence than `|`, so filters bind to the fallback:

```kida
{# ❌ Parses as: items ?? ([] | length) — returns list, not length! #}
{{ items ?? [] | length }}

{# ✅ Correct: use | default() for filter chains #}
{{ items | default([]) | length }}
```

**Rule**: Use `??` for simple direct output. Use `| default()` when applying filters after the fallback.

### Combined Usage

```kida
{{ page?.metadata?.image ?? site?.config?.default_image ?? '/images/placeholder.png' }}
```

## Best Practices

### Filter Early, Limit Early

```kida
{# ✅ Good: Filter before sorting #}
{% let posts = site.pages
  |> where('type', 'blog')
  |> where('draft', false)
  |> sort_by('date')
  |> take(10) %}

{# ❌ Less efficient: Sort everything first #}
{% let posts = site.pages
  |> sort_by('date')
  |> where('type', 'blog')
  |> take(10) %}
```

### Use Multiline for Complex Chains

```kida
{# 3+ filters: use multiline #}
{% let posts = site.pages
  |> where('type', 'blog')
  |> sort_by('date', reverse=true)
  |> take(5) %}

{# Simple chains: inline is fine #}
{{ items |> take(3) }}
```

## Complete Example

```kida
{% extends "baseof.html" %}

{% let post = page %}
{% let author = post?.metadata?.author ?? site?.config?.default_author ?? 'Anonymous' %}
{% let post_image = post?.metadata?.image ?? post?.metadata?.cover %}
{% let related_posts = site.pages
  |> where('type', 'blog')
  |> where('tags', post.tags | first)
  |> where_not('_path', post._path)
  |> sort_by('date', reverse=true)
  |> take(3) %}

{% block content %}
<article class="blog-post">
  {% if post_image %}
    <img src="{{ post_image }}" alt="{{ post.title }}">
  {% end %}

  <header>
    <h1>{{ post.title }}</h1>
    <span>By {{ author }}</span>
  </header>

  {{ post.content | safe }}

  {% if related_posts | length > 0 %}
    <aside class="related">
      <h2>Related Posts</h2>
      {% for item in related_posts %}
        <a href="{{ item.url }}">{{ item.title }}</a>
      {% end %}
    </aside>
  {% end %}
</article>
{% endblock %}
```
