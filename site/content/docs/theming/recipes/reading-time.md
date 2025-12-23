---
title: Show Reading Time
description: Display estimated reading time using Bengal's reading_time filter
weight: 40
draft: false
lang: en
tags:
- cookbook
- filters
- reading-time
keywords:
- reading time
- word count
- estimate
category: cookbook
---

# Show Reading Time

Display estimated reading time using Bengal's `reading_time` property or filter.

## The Pattern

### Use the page property (recommended)

```jinja2
<span class="reading-time">
  {{ page.reading_time }} min read
</span>
```

### Use the filter on content

```jinja2
<span class="reading-time">
  {{ page.content | reading_time }} min read
</span>
```

Both approaches calculate reading time at 200 words per minute by default.

## What's Happening

| Component | Purpose |
|-----------|---------|
| `page.reading_time` | Property: returns reading time in minutes (cached) |
| `reading_time` | Filter: counts words, divides by 200 |

## Variations

:::{tab-set}
:::{tab-item} With Word Count

Bengal provides a `word_count` filter that strips HTML and counts words:

```jinja2
<span>{{ page.content | word_count }} words · {{ page.content | reading_time }} min read</span>
```

Both filters work together seamlessly since they use the same word counting logic.

:::
:::{tab-item} Custom WPM

```jinja2
{# 250 words per minute instead of 200 #}
{% set words = page.content | word_count %}
{% set minutes = (words / 250) | round(0, 'ceil') | int %}

<span>{{ minutes }} min read</span>
```

:::
:::{tab-item} Short Content

```jinja2
{% set minutes = page.content | reading_time %}

<span class="reading-time">
{% if minutes < 1 %}
  Quick read
{% elif minutes == 1 %}
  1 min read
{% else %}
  {{ minutes }} min read
{% endif %}
</span>
```

:::
:::{tab-item} Frontmatter Override

Allow manual override for complex content:

```jinja2
{% if page.metadata.reading_time %}
  {% set minutes = page.metadata.reading_time %}
{% else %}
  {% set minutes = page.content | reading_time %}
{% endif %}
```

Then in frontmatter:

```yaml
---
title: Complex Technical Guide
reading_time: 25  # Override calculated time
---
```

:::
:::

:::{seealso}

- [Template Functions](/docs/theming/templating/functions/) — All filters
- [List Recent Posts](/docs/theming/recipes/list-recent-posts/) — Include reading time in post lists

:::
