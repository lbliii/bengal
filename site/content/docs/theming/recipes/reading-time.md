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

```kida
<span class="reading-time">
  {{ page.reading_time }} min read
</span>
```

### Use the filter on content

```kida
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

```kida
<span>{{ page.content | word_count }} words · {{ page.content | reading_time }} min read</span>
```

Both filters work together seamlessly since they use the same word counting logic.

:::{/tab-item}
:::{tab-item} Custom WPM

```kida
{# 250 words per minute instead of 200 #}
{% let words = page.content | word_count %}
{% let minutes = (words / 250) | round(0, 'ceil') | int %}

<span>{{ minutes }} min read</span>
```

:::{/tab-item}
:::{tab-item} Short Content

```kida
{% let minutes = page.content | reading_time %}

<span class="reading-time">
{% match minutes %}
  {% case m if m < 1 %}
    Quick read
  {% case 1 %}
    1 min read
  {% case m %}
    {{ m }} min read
{% end %}
</span>
```

:::{/tab-item}
:::{tab-item} Frontmatter Override

Allow manual override for complex content:

```kida
{% let minutes = page.metadata.reading_time ?? page.content | reading_time %}
```

Then in frontmatter:

```yaml
---
title: Complex Technical Guide
reading_time: 25  # Override calculated time
---
```

:::{/tab-item}
:::{/tab-set}

:::{seealso}

- [Template Functions](/docs/theming/templating/functions/) — All filters
- [List Recent Posts](/docs/theming/recipes/list-recent-posts/) — Include reading time in post lists

:::
