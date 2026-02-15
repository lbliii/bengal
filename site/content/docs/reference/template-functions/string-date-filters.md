---
title: String & Date Filters
description: Text transformation and date calculation filters
weight: 50
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

## reading_time

Estimate reading time in minutes.

```kida
{{ page.content | reading_time }} min read
```

## slugify

Convert text to URL-safe slug.

```kida
{{ "Hello World!" | slugify }}  {# → "hello-world" #}
{{ page.title | slugify }}
```

## markdownify

Render Markdown text to HTML.

```kida
{{ "**Bold** and *italic*" | markdownify | safe }}
{# → "<strong>Bold</strong> and <em>italic</em>" #}
```

## strip_html

Remove all HTML tags from text.

```kida
{{ "<p>Hello <b>world</b></p>" | strip_html }}  {# → "Hello world" #}
```

Also available as `plainify` (Hugo compatibility alias).

## excerpt

Extract an excerpt from content (first paragraph or sentence).

```kida
{{ page.content | excerpt }}
{{ page.content | excerpt(200) }}  {# Limit to 200 characters #}
```

## excerpt_for_card

Strip leading content that duplicates the title or description. Use for card/tile previews so the excerpt does not repeat information already shown in the title.

```kida
{{ p.excerpt | excerpt_for_card(p.title, p.description) }}
{{ item.description | excerpt_for_card(item.title) }}  {# Tiles, docs list #}
```

Works with HTML (strips to plain text) or plain text. Case-insensitive.

**Use cases:** post cards, related cards, tiles, tutorial cards, autodoc element cards, changelog summaries.

## card_excerpt

Excerpt for card previews: strip title/description duplicates, then truncate by word count. Combines `excerpt_for_card` and `truncatewords`.

```kida
{{ p.excerpt | card_excerpt(30, p.title, p.description) | safe }}
{{ item.description | card_excerpt(25, item.title) | safe }}
```

Use for post cards, related cards, tiles, and any preview that should not duplicate the title. Default: 30 words.

**Site strategy examples:**

```kida
{# Blog post cards #}
{{ p.excerpt | card_excerpt(30, p.title, p.description) | safe }}

{# Tutorial cards #}
{{ tut_desc | excerpt_for_card(tut_title) | excerpt(150) }}

{# Autodoc API cards #}
{{ child_desc | excerpt_for_card(child_name) | excerpt(100) }}

{# Changelog release summary #}
{{ rel.summary | excerpt_for_card(rel.version, rel.name) | excerpt(160) }}
```

## first_sentence

Extract the first sentence from text.

```kida
{{ page.excerpt | first_sentence }}
```

## truncate_chars

Truncate text to a character limit.

```kida
{{ page.title | truncate_chars(50) }}
{{ page.title | truncate_chars(50, "…") }}  {# Custom suffix #}
```

## replace_regex

Replace text using regular expressions.

```kida
{{ text | replace_regex("[0-9]+", "#") }}
```

## pluralize

Pluralize based on count.

```kida
{{ count }} {{ "item" | pluralize(count) }}  {# → "1 item" or "3 items" #}
{{ count }} {{ "category" | pluralize(count, "categories") }}  {# Custom plural #}
```

## split

Split string into list.

```kida
{{ "1.2.3" | split(".") }}  {# → ["1", "2", "3"] #}
{{ tags_string | split(",") }}
```

## filesize

Format number as human-readable file size.

```kida
{{ 1024 | filesize }}       {# → "1.0 KB" #}
{{ 1048576 | filesize }}    {# → "1.0 MB" #}
```

## strip_whitespace

Collapse and trim whitespace.

```kida
{{ "  hello   world  " | strip_whitespace }}  {# → "hello world" #}
```

## get

Safe dictionary/object access with default.

```kida
{{ params | get("missing_key", "default") }}
{{ page.meta | get("author", "Anonymous") }}
```

## base64_encode / base64_decode

Encode/decode Base64 strings.

```kida
{{ "Hello" | base64_encode }}  {# → "SGVsbG8=" #}
{{ "SGVsbG8=" | base64_decode }}  {# → "Hello" #}
```

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
