---
title: Use Pipeline Operator
nav_title: Pipeline Operator
description: Write readable filter chains with the pipeline operator
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

# Use Pipeline Operator

Learn how to use KIDA's pipeline operator (`|>`) to write readable, left-to-right filter chains.

## Goal

Write cleaner, more readable filter chains using the pipeline operator instead of nested filters.

## Why Pipeline Operator?

The pipeline operator (`|>`) provides:
- **Left-to-right readability**: Read filters in execution order
- **Better debugging**: Easier to see intermediate steps
- **Cleaner syntax**: No deeply nested parentheses

## Basic Usage

### Traditional Filter Chain

**Jinja2 style** (nested, read inside-out):
```kida
{{ items | where('published', true) | sort_by('date') | take(5) }}
```

**KIDA pipeline** (left-to-right):
```kida
{{ items |> where('published', true) |> sort_by('date') |> take(5) }}
```

### Reading Order

**Traditional** (inside-out):
```
1. Start with items
2. Apply where filter
3. Apply sort_by filter
4. Apply take filter
5. Read result
```

**Pipeline** (left-to-right):
```
1. Start with items
2. Filter published items
3. Sort by date
4. Take first 5
5. Done
```

## Common Patterns

### Collection Processing

Process a collection step-by-step:

```kida
{% let recent_posts = site.pages
  |> where('type', 'blog')
  |> where('draft', false)
  |> sort_by('date', reverse=true)
  |> take(10) %}
```

### Data Transformation

Transform data through multiple steps:

```kida
{% let formatted_content = page.content
  |> markdownify
  |> truncate(200)
  |> strip_tags
  |> trim %}
```

### Filtering and Sorting

Combine filtering and sorting:

```kida
{% let featured_posts = site.pages
  |> where('type', 'blog')
  |> where('featured', true)
  |> sort_by('date', reverse=true)
  |> take(5) %}
```

### Grouping and Aggregation

Group and process data:

```kida
{% let posts_by_category = site.pages
  |> where('type', 'blog')
  |> group_by('category')
  |> items() %}
```

## Multi-Line Formatting

Break long chains across multiple lines:

```kida
{% let processed_items = items
  |> where('status', 'active')
  |> where('published', true)
  |> sort_by('date', reverse=true)
  |> take(10)
  |> map('title') %}
```

### With Comments

Add comments to explain each step:

```kida
{% let recent_posts = site.pages
  |> where('type', 'blog')        {# Only blog posts #}
  |> where('draft', false)        {# Exclude drafts #}
  |> sort_by('date', reverse=true) {# Newest first #}
  |> take(10)                      {# Limit to 10 #}
%}
```

## Real-World Examples

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

### Author Statistics

```kida
{% let author_posts = site.pages
  |> where('author', page.author)
  |> where('type', 'blog')
  |> where('draft', false)
  |> sort_by('date', reverse=true) %}

{% let total_posts = author_posts |> length %}
{% let recent_posts = author_posts |> take(5) %}

<div class="author-stats">
  <p>{{ author.name }} has written {{ total_posts }} posts.</p>
  
  <h3>Recent Posts</h3>
  <ul>
    {% for post in recent_posts %}
      <li><a href="{{ post.url }}">{{ post.title }}</a></li>
    {% end %}
  </ul>
</div>
```

## Combining with Other Features

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

### With Functions

```kida
{% def format_posts(posts) %}
  {% let formatted = posts
    |> map('title')
    |> join(', ') %}
  {{ formatted }}
{% end %}

{{ format_posts(site.pages |> where('type', 'blog')) }}
```

## Performance Considerations

Pipeline operations are evaluated lazily when possible, but be mindful of:

- **Early filtering**: Filter early to reduce data processed
- **Limit early**: Use `take()` early if you only need a few items
- **Cache expensive chains**: Cache the result if used multiple times

```kida
{# ✅ Good: Filter early #}
{% let posts = site.pages
  |> where('type', 'blog')      {# Filter first #}
  |> where('draft', false)      {# Then filter drafts #}
  |> sort_by('date')            {# Then sort #}
  |> take(10) %}                {# Finally limit #}

{# ❌ Less efficient: Sort before filtering #}
{% let posts = site.pages
  |> sort_by('date')            {# Sort everything #}
  |> where('type', 'blog')      {# Then filter #}
  |> take(10) %}
```

## Best Practices

1. **Use multi-line format** for chains longer than 3 filters
2. **Add comments** to explain complex transformations
3. **Filter early** to reduce data processed
4. **Cache results** if used multiple times
5. **Use descriptive variable names** for intermediate results

## Complete Example

Here's a complete template using pipeline operators:

```kida
{% extends "baseof.html" %}

{% let recent_posts = site.pages
  |> where('type', 'blog')
  |> where('draft', false)
  |> sort_by('date', reverse=true)
  |> take(10) %}

{% let popular_tags = site.tags
  |> items()
  |> sort_by('count', reverse=true)
  |> take(10) %}

{% block content %}
  <h1>Recent Posts</h1>
  <ul>
    {% for post in recent_posts %}
      <li>
        <a href="{{ post.url }}">{{ post.title }}</a>
        <span>{{ post.date | dateformat('%B %d, %Y') }}</span>
      </li>
    {% end %}
  </ul>
{% endblock %}

{% block sidebar %}
  <h2>Popular Tags</h2>
  <div class="tag-cloud">
    {% for tag in popular_tags %}
      <a href="{{ tag_url(tag.name) }}" class="tag">
        {{ tag.name }} ({{ tag.count }})
      </a>
    {% end %}
  </div>
{% endblock %}
```

## Next Steps

- [Create Custom Template](/docs/theming/templating/kida/create-custom-template/) — Build templates using pipelines
- [Cache Fragments](/docs/theming/templating/kida/cache-fragments/) — Cache pipeline results
- [KIDA Syntax Reference](/docs/reference/kida-syntax/) — Complete syntax documentation

:::{seealso}
- [KIDA Tutorial](/docs/tutorials/getting-started-with-kida/) — Learn KIDA from scratch
- [Template Functions](/docs/theming/templating/functions/) — Available filters
:::

