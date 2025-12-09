---
title: Advanced Filtering
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

This guide shows how to build an advanced filter using Jinja set logic.

## The Logic: Set Intersections

Jinja allows us to treat lists of pages as mathematical sets.

- **Union**: All unique items in A or B.
- **Intersection**: Items that are in BOTH A and B.
- **Difference**: Items in A but not in B.

## Example: Building a "Recipe Finder"

Imagine a documentation site where you want to find "API Guides" for "v2.0".

### 1. Accessing the Data

Bengal exposes `site.taxonomies` which gives us lists of pages for each tag.

```jinja2
{% set api_pages = site.taxonomies.tags["api"].pages %}
{% set v2_pages = site.taxonomies.tags["v2"].pages %}
```

### 2. Finding the Intersection

We can find pages that exist in both lists.

```jinja2
{% set results = [] %}

{% for page in api_pages %}
  {% if page in v2_pages %}
    {% do results.append(page) %}
  {% endif %}
{% endfor %}

<h2>API v2 Guides ({{ results|length }})</h2>
<ul>
  {% for page in results %}
    <li><a href="{{ page.url }}">{{ page.title }}</a></li>
  {% endfor %}
</ul>
```

## Advanced: The "Filter Page" Layout

For a dynamic filter page (e.g., `/search/`), we typically rely on client-side JavaScript because pre-rendering *every combination* of tags is expensive (combinatorial explosion).

However, for specific, high-value combinations, you can create dedicated pages.

### Step 1: Create the Page

`site/content/guides/python-tutorials.md`:
```markdown
---
title: Python Tutorials
layout: filter_page
filter_tags: ["python", "tutorial"]
---
Here are all our Python tutorials.
```

### Step 2: Create the Layout

`templates/filter_page.html`:

```jinja2
{% extends "base.html" %}

{% block content %}
  <h1>{{ page.title }}</h1>

  {# 1. Start with all site pages #}
  {% set matches = site.pages %}

  {# 2. Apply intersection for each required tag #}
  {% for tag in page.filter_tags %}
    {% set tag_pages = site.taxonomies.tags[tag].pages %}
    {# Use a custom filter or loop to intersect #}
    {% set new_matches = [] %}
    {% for m in matches %}
      {% if m in tag_pages %}
        {% do new_matches.append(m) %}
      {% endif %}
    {% endfor %}
    {% set matches = new_matches %}
  {% endfor %}

  {# 3. Render Results #}
  <div class="results">
    {% for page in matches %}
      {% include "partials/card.html" %}
    {% else %}
      <p>No matches found.</p>
    {% endfor %}
  </div>

{% endblock %}
```

## Summary

Use Set Intersections to build powerful "Topic Pages" that aggregate content from multiple dimensions without manually curating lists.

## See Also

- [Content Reuse](/docs/content/reuse/) — DRY content strategies
- [Templating](/docs/theming/templating/) — Jinja2 fundamentals
