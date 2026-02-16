---
title: Advanced Filtering
nav_title: Filtering
description: Build dynamic pages that filter content by multiple tags or criteria
weight: 30
draft: false
lang: en
tags:
- filtering
- taxonomy
- jinja
keywords:
- filtering
- taxonomy
- tags
- intersection
- dynamic
category: guide
---

# Advanced Content Filtering

Standard tag pages list content for *one* tag (e.g., `/tags/python/`). But sometimes users want to find content that matches **multiple** criteria, like "Tutorials" AND "Python" AND "Beginner".

This guide shows how to build an advanced filter using [[ext:kida:|Kida]] template set logic.

## The Logic: Set Intersections

Kida (and Jinja2) allows us to treat lists of pages as mathematical sets.

- **Union**: All unique items in A or B.
- **Intersection**: Items that are in BOTH A and B.
- **Difference**: Items in A but not in B.

## Example: Building a "Recipe Finder"

Imagine a documentation site where you want to find "API Guides" for "v2.0".

:::{steps}
:::{step} Access the data

Bengal exposes `site.taxonomies` which gives us lists of pages for each tag.

```kida
{% let api_pages = site.taxonomies.tags["api"].pages %}
{% let v2_pages = site.taxonomies.tags["v2"].pages %}
```

:::{/step}
:::{step} Find the intersection

Use the `|> intersect()` filter to find pages in both lists:

```kida
{% let results = api_pages |> intersect(v2_pages) %}

<h2>API v2 Guides ({{ results | length }})</h2>
<ul>
  {% for page in results %}
    <li><a href="{{ page.href }}">{{ page.title }}</a></li>
  {% end %}
</ul>
```

:::{/step}
:::{/steps}

:::{tip}
For more complex filtering, use `|> where()` with operators:
```kida
{% let results = site.pages
  |> where('tags', 'api', 'in')
  |> where('tags', 'v2', 'in') %}
```
:::

## Advanced: The "Filter Page" Layout

For a dynamic filter page (e.g., `/search/`), we typically rely on client-side JavaScript because pre-rendering *every combination* of tags is expensive (combinatorial explosion).

However, for specific, high-value combinations, you can create dedicated pages.

:::{steps}
:::{step} Create the Page

`site/content/guides/python-tutorials.md`:
```markdown
---
title: Python Tutorials
variant: filter_page
filter_tags: ["python", "tutorial"]
---
Here are all our Python tutorials.
```

:::{/step}
:::{step} Create the Layout

`templates/filter_page.html`:

```kida
{% extends "base.html" %}

{% block content %}
  <h1>{{ page.title }}</h1>

  {# Start with all pages, then filter by each required tag #}
  {% let matches = site.pages %}

  {% for tag in page.metadata.filter_tags %}
    {% let tag_pages = site.pages |> where('tags', tag, 'in') %}
    {% let matches = matches |> intersect(tag_pages) %}
  {% end %}

  {# Render Results #}
  <div class="results">
    {% for post in matches %}
      {% include "partials/card.html" %}
    {% else %}
      <p>No matches found.</p>
    {% end %}
  </div>

{% end %}
```

:::{/step}
:::{/steps}

## Summary

Use Set Intersections to build powerful "Topic Pages" that aggregate content from multiple dimensions without manually curating lists.

:::{seealso}
- [Filter by Multiple Tags](/docs/theming/recipes/filter-by-tags/) — Complete cookbook recipe
- [Content Reuse](/docs/content/reuse/) — DRY content strategies
- [Templating](/docs/theming/templating/) — Template fundamentals
:::
