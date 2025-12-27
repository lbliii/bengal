---
title: Use Pattern Matching
nav_title: Pattern Matching
description: Replace long if/elif chains with clean pattern matching
weight: 30
type: doc
draft: false
lang: en
tags:
- how-to
- templates
- kida
keywords:
- pattern matching
- match case
- kida pattern matching
category: guide
---

# Use Pattern Matching

Learn how to use Kida's pattern matching feature to replace long `if/elif` chains with cleaner, more readable code.

## Goal

Replace conditional logic with pattern matching for better readability and maintainability.

## When to Use Pattern Matching

Use pattern matching when you have:
- Multiple conditions checking the same variable
- Long `if/elif/else` chains
- Type-based or value-based branching
- Default fallback cases

## Basic Pattern Matching

### Simple Value Matching

Replace this:

```kida
{% if page.type == "blog" %}
  <article class="blog-post">{{ page.content | safe }}</article>
{% elif page.type == "doc" %}
  <article class="doc-page">{{ page.content | safe }}</article>
{% elif page.type == "tutorial" %}
  <article class="tutorial">{{ page.content | safe }}</article>
{% else %}
  <article>{{ page.content | safe }}</article>
{% end %}
```

With this:

```kida
{% match page.type %}
  {% case "blog" %}
    <article class="blog-post">{{ page.content | safe }}</article>
  {% case "doc" %}
    <article class="doc-page">{{ page.content | safe }}</article>
  {% case "tutorial" %}
    <article class="tutorial">{{ page.content | safe }}</article>
  {% case _ %}
    <article>{{ page.content | safe }}</article>
{% end %}
```

### Default Case

The `{% case _ %}` pattern matches anything (default fallback):

```kida
{% match page.status %}
  {% case "published" %}
    <span class="status-published">Published</span>
  {% case "draft" %}
    <span class="status-draft">Draft</span>
  {% case "scheduled" %}
    <span class="status-scheduled">Scheduled</span>
  {% case _ %}
    <span class="status-unknown">Unknown</span>
{% end %}
```

## Common Patterns

### Status-Based Rendering

```kida
{% match post.status %}
  {% case "published" %}
    <article class="post">
      <h1>{{ post.title }}</h1>
      {{ post.content | safe }}
    </article>
  {% case "draft" %}
    <div class="draft-notice">
      <p>This post is a draft and not yet published.</p>
    </div>
  {% case "archived" %}
    <article class="archived-post">
      <p class="archive-notice">This post has been archived.</p>
      <h1>{{ post.title }}</h1>
      {{ post.content | safe }}
    </article>
  {% case _ %}
    <p>Post status unknown.</p>
{% end %}
```

### Icon Selection

```kida
{% match page.type %}
  {% case "blog" %}
    <i class="icon-pen"></i>
  {% case "doc" %}
    <i class="icon-book"></i>
  {% case "tutorial" %}
    <i class="icon-graduation-cap"></i>
  {% case "video" %}
    <i class="icon-video"></i>
  {% case "podcast" %}
    <i class="icon-microphone"></i>
  {% case _ %}
    <i class="icon-file"></i>
{% end %}
```

### Layout Selection

```kida
{% match page.layout %}
  {% case "wide" %}
    <div class="layout-wide">
      {{ page.content | safe }}
    </div>
  {% case "narrow" %}
    <div class="layout-narrow">
      {{ page.content | safe }}
    </div>
  {% case "sidebar" %}
    <div class="layout-sidebar">
      <main>{{ page.content | safe }}</main>
      <aside>{{ page.sidebar | safe }}</aside>
    </div>
  {% case _ %}
    <div class="layout-default">
      {{ page.content | safe }}
    </div>
{% end %}
```

### Category-Based Styling

```kida
{% match post.category %}
  {% case "news" %}
    <article class="post post-news">
      <span class="badge badge-news">News</span>
      <h1>{{ post.title }}</h1>
      {{ post.content | safe }}
    </article>
  {% case "tutorial" %}
    <article class="post post-tutorial">
      <span class="badge badge-tutorial">Tutorial</span>
      <h1>{{ post.title }}</h1>
      {{ post.content | safe }}
    </article>
  {% case "announcement" %}
    <article class="post post-announcement">
      <span class="badge badge-announcement">Announcement</span>
      <h1>{{ post.title }}</h1>
      {{ post.content | safe }}
    </article>
  {% case _ %}
    <article class="post">
      <h1>{{ post.title }}</h1>
      {{ post.content | safe }}
    </article>
{% end %}
```

## Nested Pattern Matching

You can nest pattern matching:

```kida
{% match page.type %}
  {% case "blog" %}
    {% match page.format %}
      {% case "standard" %}
        <article class="blog-standard">{{ page.content | safe }}</article>
      {% case "longform" %}
        <article class="blog-longform">{{ page.content | safe }}</article>
      {% case _ %}
        <article class="blog-default">{{ page.content | safe }}</article>
    {% end %}
  {% case "doc" %}
    <article class="doc">{{ page.content | safe }}</article>
  {% case _ %}
    <article>{{ page.content | safe }}</article>
{% end %}
```

## Combining with Other Logic

Pattern matching works well with other Kida features:

```kida
{% let post_type = page.type %}
{% let is_featured = page.featured | default(false) %}

{% match post_type %}
  {% case "blog" %}
    <article class="blog-post {% if is_featured %}featured{% end %}">
      {% if is_featured %}
        <span class="featured-badge">Featured</span>
      {% end %}
      <h1>{{ page.title }}</h1>
      {{ page.content | safe }}
    </article>
  {% case "tutorial" %}
    <article class="tutorial">
      <h1>{{ page.title }}</h1>
      {{ page.content | safe }}
    </article>
  {% case _ %}
    <article>{{ page.content | safe }}</article>
{% end %}
```

## Performance Considerations

Pattern matching is compiled efficiently and performs similarly to `if/elif` chains. Use pattern matching for:
- ✅ Readability when you have 3+ cases
- ✅ Clear intent when matching specific values
- ✅ Easier maintenance when cases change frequently

Use `if/elif` for:
- ✅ Complex boolean expressions
- ✅ Range checks (`if x > 10`)
- ✅ Multiple variable conditions

## Complete Example

Here's a complete example using pattern matching in a blog template:

```kida
{% extends "baseof.html" %}

{% let post = page %}

{% block content %}
  {% match post.type %}
    {% case "blog" %}
      <article class="blog-post">
        <header>
          <h1>{{ post.title }}</h1>
          <div class="meta">
            <time>{{ post.date | dateformat('%B %d, %Y') }}</time>
            {% match post.status %}
              {% case "published" %}
                <span class="status">Published</span>
              {% case "draft" %}
                <span class="status draft">Draft</span>
              {% case "scheduled" %}
                <span class="status scheduled">Scheduled</span>
              {% case _ %}
                <span class="status unknown">Unknown</span>
            {% end %}
          </div>
        </header>
        <div class="content">
          {{ post.content | safe }}
        </div>
        {% if post.tags %}
          <footer>
            {% for tag in post.tags %}
              <a href="{{ tag_url(tag) }}" class="tag">{{ tag }}</a>
            {% end %}
          </footer>
        {% end %}
      </article>
    {% case "tutorial" %}
      <article class="tutorial">
        <h1>{{ post.title }}</h1>
        <div class="tutorial-content">{{ post.content | safe }}</div>
      </article>
    {% case _ %}
      <article>
        <h1>{{ post.title }}</h1>
        {{ post.content | safe }}
      </article>
  {% end %}
{% endblock %}
```

## Migration Tips

When migrating from `if/elif`:

1. **Identify the variable** being checked
2. **List all cases** explicitly
3. **Add default case** with `{% case _ %}`
4. **Test each case** to ensure correct behavior

## Next Steps

- [Create Custom Template](/docs/theming/templating/kida/create-custom-template/) — Build templates using pattern matching
- [Kida Syntax Reference](/docs/reference/kida-syntax/) — Complete syntax documentation
- [Use Pipeline Operator](/docs/theming/templating/kida/use-pipeline-operator/) — Combine with other Kida features

:::{seealso}
- [Kida Tutorial](/docs/tutorials/getting-started-with-kida/) — Learn Kida from scratch
- [Template Functions](/docs/theming/templating/functions/) — Available filters and functions
:::
