---
title: Series Navigation
description: Add prev/next navigation for multi-part tutorials and series
weight: 60
draft: false
lang: en
tags:
- cookbook
- series
- navigation
keywords:
- tutorial series
- multi-part content
- prev next
- series navigation
category: cookbook
---

# Series Navigation

Add navigation for multi-part content like tutorial series, allowing readers to move between parts.

:::{note}
**Built into Default Theme**

Bengal's default theme includes navigation components:
- **Prev/Next navigation** via `{{ page_navigation(page) }}` macro
- **Section-scoped** for docs/tutorials (respects `weight` order)
- **Track navigation** for learning paths with progress bars
- Enable with `navigation.prev_next` feature flag

This recipe shows how to use `page.series` frontmatter for explicit multi-part series with progress tracking.
:::

## The Pattern

### Frontmatter Setup

Each page in the series needs series metadata:

```yaml
---
title: "Part 2: Building Components"
series:
  name: "React from Scratch"
  part: 2
  total: 5
---
```

### Template Code

```jinja2
{% if page.series %}
<nav class="series-nav">
  <div class="series-header">
    <span class="series-name">{{ page.series.name }}</span>
    <span class="series-progress">Part {{ page.series.part }} of {{ page.series.total }}</span>
  </div>

  <div class="series-links">
    {% if page.prev_in_series %}
    <a href="{{ page.prev_in_series.href }}" class="prev">
      ← {{ page.prev_in_series.title }}
    </a>
    {% endif %}

    {% if page.next_in_series %}
    <a href="{{ page.next_in_series.href }}" class="next">
      {{ page.next_in_series.title }} →
    </a>
    {% endif %}
  </div>
</nav>
{% endif %}
```

## What's Happening

| Component | Purpose |
|-----------|---------|
| `page.series` | Series object with `name`, `part`, `total` |
| `page.prev_in_series` | Previous Page object (or None if first) |
| `page.next_in_series` | Next Page object (or None if last) |

## Variations

### Progress Bar

```jinja2
{% if page.series %}
<div class="series-progress-bar">
  <div class="progress" style="width: {{ (page.series.part / page.series.total * 100) | round }}%"></div>
</div>
<span>{{ page.series.part }} / {{ page.series.total }}</span>
{% endif %}
```

### Series Table of Contents

Show all parts with current highlighted:

```jinja2
{% if page.series %}
<aside class="series-toc">
  <h4>{{ page.series.name }}</h4>
  <ol>
    {% for part_page in page.series.pages %}
    <li {% if part_page.eq(page) %}class="current"{% endif %}>
      <a href="{{ part_page.href }}">{{ part_page.title }}</a>
    </li>
    {% endfor %}
  </ol>
</aside>
{% endif %}
```

### Compact Footer Navigation

```jinja2
{% if page.series %}
<footer class="series-footer">
  {% if page.prev_in_series %}
  <a href="{{ page.prev_in_series.href }}">← Previous</a>
  {% else %}
  <span></span>
  {% endif %}

  <span>{{ page.series.part }}/{{ page.series.total }}</span>

  {% if page.next_in_series %}
  <a href="{{ page.next_in_series.href }}">Next →</a>
  {% else %}
  <span></span>
  {% endif %}
</footer>
{% endif %}
```

### With Completion Message

```jinja2
{% if page.series %}
  {% if not page.next_in_series %}
  <div class="series-complete">
    🎉 You've completed "{{ page.series.name }}"!
  </div>
  {% endif %}
{% endif %}
```

## Example CSS

```css
.series-nav {
  border: 1px solid var(--border-color);
  border-radius: 8px;
  padding: 1rem;
  margin: 2rem 0;
}

.series-header {
  display: flex;
  justify-content: space-between;
  margin-bottom: 1rem;
  font-size: 0.875rem;
  color: var(--text-muted);
}

.series-links {
  display: flex;
  justify-content: space-between;
  gap: 1rem;
}

.series-links a {
  flex: 1;
  padding: 0.75rem;
  background: var(--bg-secondary);
  border-radius: 4px;
  text-decoration: none;
}

.series-links .prev { text-align: left; }
.series-links .next { text-align: right; }
```

:::{seealso}
- [Template Functions Reference](/docs/reference/template-functions/#series-properties) — Series properties
- [Build a Tutorial Series](/docs/tutorials/create-a-tutorial-series/) — Full tutorial
:::
