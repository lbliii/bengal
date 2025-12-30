---
title: Group by Category
description: Organize content into groups using Bengal's group_by filter
weight: 20
draft: false
lang: en
tags:
- cookbook
- filters
- group_by
keywords:
- group by
- category
- organize
- taxonomy
category: cookbook
---

# Group by Category

Display content organized by category, tag, or any frontmatter field.

## The Pattern

```kida
{% let by_category = site.pages
  |> where('section', 'docs')
  |> group_by('category') %}

{% for category, pages in by_category.items() |> sort %}
<section>
  <h2>{{ category | title }}</h2>
  <ul>
  {% for page in pages |> sort_by('weight') %}
    <li><a href="{{ page.href }}">{{ page.title }}</a></li>
  {% end %}
  </ul>
</section>
{% end %}
```

## What's Happening

| Step | Purpose |
|------|---------|
| `group_by('category')` | Creates a dict: `{category: [pages]}` |
| `.items()` | Iterate key-value pairs |
| `\| sort` | Alphabetize categories |
| `sort_by('weight')` | Order pages within each category |

## Variations

:::{tab-set}
:::{tab-item} By Year

```kida
{# Group blog posts by publication year #}
{% let posts = site.pages |> where('section', 'blog') |> sort_by('date', reverse=true) %}

{% let current_year = none %}
{% for post in posts %}
  {% let post_year = post.date.year %}
  {% if post_year != current_year %}
    {% let current_year = post_year %}
    <h2>{{ post_year }}</h2>
  {% end %}
  <li><a href="{{ post.href }}">{{ post.title }}</a></li>
{% end %}
```

:::{/tab-item}
:::{tab-item} By Tag (Taxonomy)

```kida
{# Show all tags with their post counts #}
{% for tag, data in site.taxonomies.tags.items() |> sort %}
<div class="tag">
  <a href="{{ data.href }}">{{ tag }}</a>
  <span class="count">{{ data.pages | length }}</span>
</div>
{% end %}
```

:::{/tab-item}
:::{tab-item} Nested Groups

```kida
{# Group by category, then by author #}
{% let by_category = site.pages |> group_by('category') %}

{% for category, cat_pages in by_category.items() %}
  <h2>{{ category }}</h2>

  {% let by_author = cat_pages |> group_by('author') %}
  {% for author, author_pages in by_author.items() %}
    <h3>{{ author }}</h3>
    {% for page in author_pages %}
      <li>{{ page.title }}</li>
    {% end %}
  {% end %}
{% end %}
```

:::{/tab-item}
:::{/tab-set}

## Handle Missing Values

Pages without the grouped field go into a `None` group:

```kida
{% let by_category = pages |> group_by('category') %}

{% for category, pages in by_category.items() %}
  {% if category %}
    <h2>{{ category }}</h2>
  {% else %}
    <h2>Uncategorized</h2>
  {% end %}
  {# ... #}
{% end %}
```

:::{seealso}
- [Template Functions](/docs/theming/templating/functions/) — All filter options
- [Filter by Tags](/docs/theming/recipes/filter-by-tags/) — Multi-criteria filtering
:::
