---
title: Add Reading Time
description: Display estimated reading time on your articles
weight: 30
draft: false
lang: en
tags: [recipe, reading-time, ux]
keywords: [reading time, estimate, article, blog]
category: recipe
---

# Add Reading Time

Display estimated reading time based on word count.

## Time Required

⏱️ 5 minutes

## What You'll Build

- Reading time calculation (200 words/minute)
- Display in article header
- Accessible to templates via `page.reading_time`

## Option 1: Use Built-in Filter

Bengal includes a `reading_time` filter. Use it in your templates:

```html
<!-- templates/partials/article-meta.html -->
<div class="article-meta">
  <time datetime="{{ page.date | date('%Y-%m-%d') }}">
    {{ page.date | date('%B %d, %Y') }}
  </time>
  <span class="reading-time">
    {{ page.content | reading_time }} min read
  </span>
</div>
```

## Option 2: Custom Calculation

For more control, calculate in your template:

```html
<!-- templates/partials/article-meta.html -->
{% set words = page.content | striptags | wordcount %}
{% set minutes = (words / 200) | round(0, 'ceil') | int %}

<div class="article-meta">
  <span class="reading-time">
    {% if minutes < 1 %}
      Less than 1 min read
    {% elif minutes == 1 %}
      1 min read
    {% else %}
      {{ minutes }} min read
    {% endif %}
  </span>
</div>
```

## Option 3: Frontmatter Override

Allow manual override in frontmatter:

```html
<!-- templates/partials/article-meta.html -->
{% if page.metadata.reading_time %}
  {% set minutes = page.metadata.reading_time %}
{% else %}
  {% set words = page.content | striptags | wordcount %}
  {% set minutes = (words / 200) | round(0, 'ceil') | int %}
{% endif %}

<span class="reading-time">{{ minutes }} min read</span>
```

Override in frontmatter:

```yaml
---
title: Complex Technical Guide
reading_time: 25  # Override calculated time
---
```

## Styling

Add some style:

```css
.reading-time {
  color: #666;
  font-size: 0.9em;
}

.reading-time::before {
  content: "📖 ";
}
```

## Result

Your articles now show:
- ✅ Estimated reading time
- ✅ Calculated from word count
- ✅ Optional manual override

## See Also

- [Template Functions](/docs/theming/templating/functions/) — Available filters
- [Templating](/docs/theming/templating/) — Template basics

