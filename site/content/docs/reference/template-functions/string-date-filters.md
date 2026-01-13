---
title: String & Date Filters
description: Text transformation and date calculation filters
weight: 50
type: doc
tags:
- reference
- filters
- strings
- dates
category: reference
---

# String Filters

## word_count

Count words in text, stripping HTML first. Uses same logic as `reading_time`.

```kida
{{ page.content | word_count }} words

{# Combined with reading time #}
<span>{{ page.content | word_count }} words · {{ page.content | reading_time }} min read</span>
```

Also available as `wordcount` (Jinja naming convention).

---

# Date Filters

These filters help calculate and display content age and date information.

## days_ago

Calculate days since a date. Useful for freshness indicators.

```kida
{# Days since publication #}
{{ page.date | days_ago }} days old

{# Conditional styling #}
{% if page.date | days_ago < 7 %}
<span class="badge badge-new">New</span>
{% end %}
```

## months_ago

Calculate calendar months since a date.

```kida
{% if page.date | months_ago > 6 %}
<div class="notice">This content may be outdated.</div>
{% end %}
```

## month_name

Get month name from number (1-12).

```kida
{{ 3 | month_name }}         {# → "March" #}
{{ 3 | month_name(true) }}   {# → "Mar" (abbreviated) #}

{# With date #}
{{ page.date.month | month_name }}
```

## humanize_days

Convert day count to human-readable relative time.

```kida
{{ page.date | days_ago | humanize_days }}
{# → "today", "yesterday", "3 days ago", "2 weeks ago", etc. #}
```
