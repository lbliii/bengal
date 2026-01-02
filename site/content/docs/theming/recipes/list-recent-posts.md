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

```kida
{% let posts = site.pages
  |> where('section', 'blog')
  |> where('draft', false)
  |> sort_by('date', reverse=true)
  |> limit(5) %}

<ul class="recent-posts">
{% for post in posts %}
  <li>
    <a href="{{ post.href }}">{{ post.title }}</a>
    <time>{{ post.date | date('%B %d, %Y') }}</time>
  </li>
{% end %}
</ul>
```

## What's Happening

| Filter | Purpose |
|--------|---------|
| `where('section', 'blog')` | Only pages in the `blog/` directory |
| `where('draft', false)` | Exclude drafts |
| `sort_by('date', reverse=true)` | Newest first |
| `limit(5)` | Take only 5 |
| `date('%B %d, %Y')` | Format date (alias for `dateformat`) |

## Variations

:::{tab-set}
:::{tab-item} Any Section

```kida
{# All non-draft pages, any section #}
{% let recent = site.pages
  |> where('draft', false)
  |> sort_by('date', reverse=true)
  |> limit(10) %}
```

:::{/tab-item}
:::{tab-item} With Featured

```kida
{% let posts = site.pages |> where('section', 'blog') |> sort_by('date', reverse=true) %}
{% let featured = posts |> first %}
{% let rest = posts |> offset(1) |> limit(4) %}

<div class="featured">
  <h2>{{ featured.title }}</h2>
  <p>{{ featured.description }}</p>
</div>

<ul class="more-posts">
{% for post in rest %}
  <li><a href="{{ post.href }}">{{ post.title }}</a></li>
{% end %}
</ul>
```

:::{/tab-item}
:::{tab-item} Exclude Current

```kida
{# In a sidebar, show recent posts excluding the current one #}
{% let others = site.pages
  |> where('section', 'blog')
  |> sort_by('date', reverse=true)
  |> limit(6) %}

{% for post in others if post._path != page._path %}
  <a href="{{ post.href }}">{{ post.title }}</a>
{% end %}
```

:::{/tab-item}
:::{/tab-set}

:::{seealso}
- [Template Functions](/docs/theming/templating/functions/) — All filter options
- [Group by Category](/docs/theming/recipes/group-by-category/) — Organize posts by category
:::
