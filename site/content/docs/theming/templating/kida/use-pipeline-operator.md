---
title: Use Pipeline Operator
nav_title: Pipeline Operator
description: Alternative syntax for filter chains in Kida templates
weight: 60
type: doc
draft: false
lang: en
tags:
- how-to
- templates
- kida
keywords:
- pipeline operator
- filter chains
- kida pipeline
category: guide
---

# Pipeline Operator

Kida supports two syntaxes for filter chains: the traditional pipe (`|`) and the pipeline operator (`|>`). Both compile to identical code—choose based on your style preference.

## Quick Comparison

```kida
{# These are functionally identical #}
{{ items | where('published', true) | sort_by('date') | take(5) }}
{{ items |> where('published', true) |> sort_by('date') |> take(5) }}
```

Both operators:
- Read left-to-right
- Compile to the same nested function calls
- Have identical performance
- Support the same filters

## When to Use Each

| Syntax | Convention |
|--------|------------|
| `\|` | Inline expressions, Jinja2 familiarity |
| `\|>` | Multiline pipelines, functional programming style |

:::{note}
You cannot mix `|` and `|>` in the same expression. Pick one style per chain.
:::

## Multiline Pipelines

The pipeline operator works well for multiline formatting:

```kida
{% let recent_posts = site.pages
  |> where('type', 'blog')
  |> where('draft', false)
  |> sort_by('date', reverse=true)
  |> take(10) %}
```

The same works with the traditional pipe:

```kida
{% let recent_posts = site.pages
  | where('type', 'blog')
  | where('draft', false)
  | sort_by('date', reverse=true)
  | take(10) %}
```

### With Comments

Add inline comments to explain each step:

```kida
{% let recent_posts = site.pages
  |> where('type', 'blog')        {# Only blog posts #}
  |> where('draft', false)        {# Exclude drafts #}
  |> sort_by('date', reverse=true) {# Newest first #}
  |> take(10) %}                   {# Limit to 10 #}
```

## Examples

### Blog Post List

```kida
{% let blog_posts = site.pages
  |> where('type', 'blog')
  |> where('draft', false)
  |> sort_by('date', reverse=true)
  |> take(10) %}

<ul>
  {% for post in blog_posts %}
    <li>
      <a href="{{ post.url }}">{{ post.title }}</a>
      <span>{{ post.date | dateformat('%B %d, %Y') }}</span>
    </li>
  {% end %}
</ul>
```

### Related Posts

```kida
{% let related_posts = site.pages
  |> where('type', 'blog')
  |> where('tags', page.tags[0])
  |> where('id', '!=', page.id)
  |> sort_by('date', reverse=true)
  |> take(5) %}

{% if related_posts %}
  <aside class="related-posts">
    <h2>Related Posts</h2>
    <ul>
      {% for post in related_posts %}
        <li><a href="{{ post.url }}">{{ post.title }}</a></li>
      {% end %}
    </ul>
  </aside>
{% end %}
```

### Tag Cloud

```kida
{% let popular_tags = site.tags
  |> items()
  |> sort_by('count', reverse=true)
  |> take(20) %}

<div class="tag-cloud">
  {% for tag in popular_tags %}
    <a href="{{ tag_url(tag.name) }}" class="tag">
      {{ tag.name }} ({{ tag.count }})
    </a>
  {% end %}
</div>
```

### With Pattern Matching

```kida
{% let posts = site.pages
  |> where('type', 'blog')
  |> sort_by('date', reverse=true) %}

{% match posts |> length %}
  {% case 0 %}
    <p>No posts yet.</p>
  {% case _ %}
    <ul>
      {% for post in posts %}
        <li>{{ post.title }}</li>
      {% end %}
    </ul>
{% end %}
```

### With Fragment Caching

```kida
{% cache "recent-posts" %}
  {% let recent = site.pages
    |> where('type', 'blog')
    |> where('draft', false)
    |> sort_by('date', reverse=true)
    |> take(10) %}

  <ul>
    {% for post in recent %}
      <li><a href="{{ post.url }}">{{ post.title }}</a></li>
    {% end %}
  </ul>
{% end %}
```

## Filter Chain Best Practices

These apply to both `|` and `|>`:

1. **Filter early** — Reduce data before sorting or mapping
2. **Limit early** — Use `take()` if you only need a few items
3. **Cache expensive chains** — Use `{% cache %}` for repeated computations
4. **Use multiline format** — For chains longer than 3 filters
5. **Add comments** — Explain non-obvious transformations

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

## Technical Details

Both operators compile to nested filter calls:

```python
# Template: items |> where('type', 'blog') |> take(5)
# Compiles to: _filters['take'](_filters['where'](items, 'type', 'blog'), 5)

# Template: items | where('type', 'blog') | take(5)
# Compiles to: _filters['take'](_filters['where'](items, 'type', 'blog'), 5)
```

The `|>` operator exists for developers who prefer its visual style, particularly those familiar with functional programming languages like F#, Elixir, or OCaml where `|>` is the standard pipeline operator.

## Next Steps

- [Create Custom Template](/docs/theming/templating/kida/create-custom-template/) — Build templates using pipelines
- [Cache Fragments](/docs/theming/templating/kida/cache-fragments/) — Cache pipeline results
- [Kida Syntax Reference](/docs/reference/kida-syntax/) — Complete syntax documentation

:::{seealso}
- [Kida Tutorial](/docs/tutorials/getting-started-with-kida/) — Learn Kida from scratch
- [Template Functions](/docs/theming/templating/functions/) — Available filters
:::
