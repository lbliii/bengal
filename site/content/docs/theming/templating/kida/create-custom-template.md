---
title: Create a Custom Template
nav_title: Custom Template
description: Build a custom template from scratch using Kida syntax
weight: 10
draft: false
lang: en
tags:
- how-to
- templates
- kida
keywords:
- custom template
- kida template
- template creation
category: guide
---

# Create a Custom Template

Learn how to create a custom template using Kida syntax. This guide walks through building a blog post template from scratch.

## Goal

Create a custom blog post template that:

- Extends the base layout
- Displays post metadata (title, date, author)
- Shows tags and categories
- Includes a reading time estimate

## Prerequisites

- Bengal site initialized
- Kida enabled in `bengal.toml`:

  ```yaml
  site:
    template_engine: kida
  ```

## Steps

### Step 1: Create Template Directory

Create the template file in your project:

```bash
mkdir -p templates/blog
touch templates/blog/single.html
```

Bengal searches templates in this order:

1. `templates/` (your project's custom templates)
2. Theme templates (for each theme in the theme chain):
   - Site-level themes (`themes/{theme}/templates`)
   - Installed themes (via package entry points)
   - Bundled themes (`bengal/themes/{theme}/templates`)
3. Default theme templates (ultimate fallback)

### Step 2: Extend Base Layout

Start by extending the base layout:

```kida
{# templates/blog/single.html #}
{% extends "baseof.html" %}
```

### Step 3: Define Template Variables

Use `{% let %}` for template-wide variables:

```kida
{% extends "baseof.html" %}

{% let post = page %}
{% let reading_time = post.content | reading_time %}
{% let author = site.authors[post.author] ?? {} %}
```

### Step 4: Override Content Block

Override the `content` block to display your post:

```kida
{% extends "baseof.html" %}

{% let post = page %}
{% let reading_time = post.content | reading_time %}
{% let author = site.authors[post.author] ?? {} %}

{% block content %}
  <article class="blog-post">
    <header>
      <h1>{{ post.title }}</h1>

      <div class="post-meta">
        <time datetime="{{ post.date | dateformat('%Y-%m-%d') }}">
          {{ post.date | dateformat('%B %d, %Y') }}
        </time>

        {% if author.name %}
          <span class="author">By {{ author.name }}</span>
        {% end %}

        <span class="reading-time">{{ reading_time }} min read</span>
      </div>
    </header>

    <div class="post-content">
      {{ post.content | safe }}
    </div>

    {% if post.tags %}
      <footer class="post-footer">
        <div class="tags">
          {% for tag in post.tags %}
            <a href="{{ tag_url(tag) }}" class="tag">{{ tag }}</a>
          {% end %}
        </div>
      </footer>
    {% end %}
  </article>
{% end %}
```

### Step 5: Add Pattern Matching for Post Types

Use pattern matching to handle different post types:

```kida
{% block content %}
  {% match post.type %}
    {% case "blog" %}
      <article class="blog-post">
        {# Blog post template #}
        <h1>{{ post.title }}</h1>
        {{ post.content | safe }}
      </article>
    {% case "tutorial" %}
      <article class="tutorial">
        {# Tutorial template #}
        <h1>{{ post.title }}</h1>
        <div class="tutorial-content">{{ post.content | safe }}</div>
      </article>
    {% case _ %}
      <article>
        {# Default template #}
        <h1>{{ post.title }}</h1>
        {{ post.content | safe }}
      </article>
  {% end %}
{% end %}
```

### Step 6: Use Pipeline Operator for Data Processing

Process collections with the pipeline operator:

```kida
{% let recent_posts = site.pages
  |> where('type', 'blog')
  |> where('draft', false)
  |> sort_by('date', reverse=true)
  |> take(5) %}

{% block content %}
  <article class="blog-post">
    {# Post content #}
  </article>

  {% if recent_posts %}
    <aside class="related-posts">
      <h2>Related Posts</h2>
      <ul>
        {% for related in recent_posts %}
          <li><a href="{{ related.href }}">{{ related.title }}</a></li>
        {% end %}
      </ul>
    </aside>
  {% end %}
{% end %}
```

### Step 7: Add Fragment Caching

Cache expensive operations:

```kida
{% block content %}
  <article class="blog-post">
    {# Post content #}
  </article>

  {% cache "related-posts-" ~ post.id %}
    {% let related = site.pages
      |> where('type', 'blog')
      |> where('tags', post.tags[0])
      |> where('id', '!=', post.id)
      |> take(3) %}

    {% if related %}
      <aside class="related-posts">
        <h2>Related Posts</h2>
        <ul>
          {% for item in related %}
            <li><a href="{{ item.href }}">{{ item.title }}</a></li>
          {% end %}
        </ul>
      </aside>
    {% end %}
  {% end %}
{% end %}
```

## Complete Example

Here's a complete blog post template:

```kida
{# templates/blog/single.html #}
{% extends "baseof.html" %}

{% let post = page %}
{% let reading_time = post.content | reading_time %}
{% let author = site.authors[post.author] ?? {} %}
{% let related_posts = site.pages
  |> where('type', 'blog')
  |> where('tags', post.tags[0] ?? '')
  |> where('id', '!=', post.id)
  |> sort_by('date', reverse=true)
  |> take(3) %}

{% block content %}
  <article class="blog-post">
    <header>
      <h1>{{ post.title }}</h1>

      <div class="post-meta">
        <time datetime="{{ post.date | dateformat('%Y-%m-%d') }}">
          {{ post.date | dateformat('%B %d, %Y') }}
        </time>

        {% if author.name %}
          <span class="author">By {{ author.name }}</span>
        {% end %}

        <span class="reading-time">{{ reading_time }} min read</span>
      </div>
    </header>

    <div class="post-content">
      {{ post.content | safe }}
    </div>

    {% if post.tags %}
      <footer class="post-footer">
        <div class="tags">
          {% for tag in post.tags %}
            <a href="{{ tag_url(tag) }}" class="tag">{{ tag }}</a>
          {% end %}
        </div>
      </footer>
    {% end %}
  </article>

  {% cache "related-posts-" ~ post.id %}
    {% if related_posts %}
      <aside class="related-posts">
        <h2>Related Posts</h2>
        <ul>
          {% for related in related_posts %}
            <li>
              <a href="{{ related.href }}">{{ related.title }}</a>
              <span>{{ related.date | days_ago }} days ago</span>
            </li>
          {% end %}
        </ul>
      </aside>
    {% end %}
  {% end %}
{% end %}
```

## Testing

Test your template:

```bash
# Build the site
bengal build

# Or run dev server
bengal serve
```

Visit a blog post page to see your custom template in action.

## Next Steps

- [Add Custom Filters](/docs/theming/templating/kida/add-custom-filter.md) — Extend Kida with your own filters
- [Use Pattern Matching](/docs/theming/templating/kida/syntax/operators/#pattern-matching) — Clean up conditional logic
- [Cache Fragments](/docs/theming/templating/kida/caching/fragments/) — Improve performance

:::{seealso}

- [Kida Syntax Reference](/docs/reference/kida-syntax/) — Complete syntax documentation
- [Template Functions](/docs/theming/templating/functions/) — Available filters and functions
:::
