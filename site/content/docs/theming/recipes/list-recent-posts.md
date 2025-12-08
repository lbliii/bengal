---
title: List Recent Posts
description: Query and display recent content using Bengal's filters
weight: 10
draft: false
lang: en
tags:
- cookbook
- filters
- where
- sort
keywords:
- recent posts
- where filter
- sort_by
- limit
category: cookbook
---

# List Recent Posts

Display the most recent posts from a section using Bengal's query filters.

## The Pattern

```jinja2
{% set posts = site.pages
  | where('section', 'blog')
  | where('draft', false)
  | sort_by('date', reverse=true)
  | limit(5) %}

<ul class="recent-posts">
{% for post in posts %}
  <li>
    <a href="{{ post.url }}">{{ post.title }}</a>
    <time>{{ post.date | date('%B %d, %Y') }}</time>
  </li>
{% endfor %}
</ul>
```

## What's Happening

| Filter | Purpose |
|--------|---------|
| `where('section', 'blog')` | Only pages in the `blog/` directory |
| `where('draft', false)` | Exclude drafts |
| `sort_by('date', reverse=true)` | Newest first |
| `limit(5)` | Take only 5 |

## Variations

### From Any Section

```jinja2
{# All non-draft pages, any section #}
{% set recent = site.pages
  | where('draft', false)
  | sort_by('date', reverse=true)
  | limit(10) %}
```

### With Featured Post

```jinja2
{% set posts = site.pages | where('section', 'blog') | sort_by('date', reverse=true) %}
{% set featured = posts | first %}
{% set rest = posts | offset(1) | limit(4) %}

<div class="featured">
  <h2>{{ featured.title }}</h2>
  <p>{{ featured.description }}</p>
</div>

<ul class="more-posts">
{% for post in rest %}
  <li><a href="{{ post.url }}">{{ post.title }}</a></li>
{% endfor %}
</ul>
```

### Exclude Current Page

```jinja2
{# In a sidebar, show recent posts excluding the current one #}
{% set others = site.pages
  | where('section', 'blog')
  | sort_by('date', reverse=true)
  | limit(6) %}

{% for post in others if post.url != page.url %}
  <a href="{{ post.url }}">{{ post.title }}</a>
{% endfor %}
```

## See Also

- [Template Functions](/docs/theming/templating/functions/) — All filter options
- [Group by Category](/docs/theming/recipes/group-by-category/) — Organize posts by category
