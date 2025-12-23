---
title: Archive Page
description: Create year and month archive pages for blog content
weight: 90
draft: false
lang: en
tags:
- cookbook
- archive
- collections
keywords:
- archive page
- yearly archive
- monthly archive
- blog archive
category: cookbook
---

# Archive Page

Create archive pages that group content by year or month.

:::{note}
**Built into Default Theme**

Bengal's default theme includes archive templates:
- **`archive.html`** — Full archive page grouped by year
- **`archive-year.html`** — Year-specific archive pages
- **`partials/archive-sidebar.html`** — Sidebar widget with year links

This recipe shows how to customize grouping or build your own archive layouts.
:::

## The Pattern

### Yearly Archive

```jinja2
{% set posts = site.pages | where('section', 'blog') | sort_by('date', reverse=true) %}
{% set by_year = posts | group_by_year %}

<div class="archive">
{% for year, year_posts in by_year.items() %}
  <section class="archive-year">
    <h2>{{ year }}</h2>
    <ul>
    {% for post in year_posts %}
      <li>
        <time>{{ post.date | date('%b %d') }}</time>
        <a href="{{ post.href }}">{{ post.title }}</a>
      </li>
    {% endfor %}
    </ul>
  </section>
{% endfor %}
</div>
```

## What's Happening

| Filter | Purpose |
|--------|---------|
| `group_by_year` | Groups pages by publication year |
| `group_by_month` | Groups pages by year-month |
| `archive_years` | Returns list of years with post counts |

## Variations

### Archive Sidebar

Quick navigation showing years with counts:

```jinja2
{% set posts = site.pages | where('section', 'blog') %}
{% set years = posts | archive_years %}

<aside class="archive-nav">
  <h3>Archive</h3>
  <ul>
  {% for item in years %}
    <li>
      <a href="/blog/{{ item.year }}/">{{ item.year }}</a>
      <span class="count">({{ item.count }})</span>
    </li>
  {% endfor %}
  </ul>
</aside>
```

### Monthly Archive

```jinja2
{% set posts = site.pages | where('section', 'blog') | sort_by('date', reverse=true) %}
{% set by_month = posts | group_by_month %}

<div class="archive">
{% for (year, month), month_posts in by_month.items() %}
  <section class="archive-month">
    <h2>{{ month | month_name }} {{ year }}</h2>
    <ul>
    {% for post in month_posts %}
      <li>
        <time>{{ post.date | date('%d') }}</time>
        <a href="{{ post.href }}">{{ post.title }}</a>
      </li>
    {% endfor %}
    </ul>
  </section>
{% endfor %}
</div>
```

### Compact Timeline

```jinja2
{% set posts = site.pages | where('section', 'blog') | sort_by('date', reverse=true) %}
{% set by_year = posts | group_by_year %}

<div class="timeline">
{% for year, year_posts in by_year.items() %}
  <div class="timeline-year">
    <div class="year-marker">{{ year }}</div>
    <div class="year-posts">
      {% for post in year_posts %}
      <a href="{{ post.href }}" class="timeline-post">
        <span class="date">{{ post.date | date('%b %d') }}</span>
        <span class="title">{{ post.title }}</span>
      </a>
      {% endfor %}
    </div>
  </div>
{% endfor %}
</div>
```

### Archive with Categories

```jinja2
{% set posts = site.pages | where('section', 'blog') | sort_by('date', reverse=true) %}
{% set by_year = posts | group_by_year %}

{% for year, year_posts in by_year.items() %}
<section>
  <h2>{{ year }}</h2>

  {% set by_category = year_posts | group_by('category') %}
  {% for category, cat_posts in by_category.items() %}
  <div class="category-group">
    <h3>{{ category | title }}</h3>
    <ul>
    {% for post in cat_posts %}
      <li><a href="{{ post.href }}">{{ post.title }}</a></li>
    {% endfor %}
    </ul>
  </div>
  {% endfor %}
</section>
{% endfor %}
```

### Archive Stats Header

```jinja2
{% set posts = site.pages | where('section', 'blog') %}
{% set years = posts | archive_years %}

<header class="archive-header">
  <h1>Archive</h1>
  <p class="archive-stats">
    {{ posts | length }} posts across {{ years | length }} years
    ({{ years | first | attr('year') }}–{{ years | last | attr('year') }})
  </p>
</header>
```

## Example CSS

```css
.archive-year {
  margin-bottom: 2rem;
}

.archive-year h2 {
  font-size: 1.5rem;
  border-bottom: 2px solid var(--accent);
  padding-bottom: 0.5rem;
  margin-bottom: 1rem;
}

.archive-year ul {
  list-style: none;
  padding: 0;
}

.archive-year li {
  display: flex;
  gap: 1rem;
  padding: 0.5rem 0;
  border-bottom: 1px solid var(--border-color);
}

.archive-year time {
  color: var(--text-muted);
  font-family: monospace;
  min-width: 60px;
}

/* Timeline variant */
.timeline-year {
  display: flex;
  gap: 2rem;
  margin-bottom: 2rem;
}

.year-marker {
  font-size: 1.25rem;
  font-weight: bold;
  color: var(--accent);
  min-width: 60px;
}

.timeline-post {
  display: block;
  padding: 0.25rem 0;
}

.timeline-post .date {
  color: var(--text-muted);
  font-size: 0.875rem;
  margin-right: 0.5rem;
}

/* Sidebar nav */
.archive-nav .count {
  color: var(--text-muted);
  font-size: 0.875rem;
}
```

:::{seealso}
- [Template Functions Reference](/docs/reference/template-functions/#group_by_year) — Grouping filters
- [Group by Category](/docs/theming/recipes/group-by-category/) — Category grouping
:::
