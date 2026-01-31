---
title: Content Filters
description: HTML and content manipulation filters
weight: 80
tags:
- reference
- filters
- html
- content
category: reference
---

# Content Filters

Functions for HTML and content manipulation.

## html_escape

Escape HTML entities for safe display.

```kida
{{ user_input | html_escape }}
{# "<script>" becomes "&lt;script&gt;" #}
```

## html_unescape

Convert HTML entities back to characters.

```kida
{{ escaped_text | html_unescape }}
{# "&lt;Hello&gt;" becomes "<Hello>" #}
```

## nl2br

Convert newlines to HTML `<br>` tags.

```kida
{{ text | nl2br | safe }}
{# "Line 1\nLine 2" becomes "Line 1<br>\nLine 2" #}
```

## smartquotes

Convert straight quotes to smart (curly) quotes.

```kida
{{ text | smartquotes }}
{# "Hello" becomes "Hello" #}
{# -- becomes – (en-dash) #}
{# --- becomes — (em-dash) #}
```

## emojify

Convert emoji shortcodes to Unicode emoji.

```kida
{{ text | emojify }}
{# "Hello :smile:" becomes "Hello 😊" #}
{# "I :heart: Python" becomes "I ❤️ Python" #}
```

**Supported shortcodes:** `:smile:`, `:grin:`, `:joy:`, `:heart:`, `:star:`, `:fire:`, `:rocket:`, `:check:`, `:x:`, `:warning:`, `:tada:`, `:thumbsup:`, `:thumbsdown:`, `:eyes:`, `:bulb:`, `:sparkles:`, `:zap:`, `:wave:`, `:clap:`, `:raised_hands:`, `:100:`

## extract_content

Extract main content from full rendered HTML page. Useful for embedding page content.

```kida
{{ page.rendered_html | extract_content | safe }}
```

## demote_headings

Demote HTML headings by specified levels (h1→h2, h2→h3, etc.).

```kida
{{ page.content | demote_headings | safe }}
{# <h1>Title</h1> becomes <h2>Title</h2> #}

{{ page.content | demote_headings(2) | safe }}
{# <h1>Title</h1> becomes <h3>Title</h3> #}
```

## prefix_heading_ids

Prefix heading IDs to ensure uniqueness when embedding multiple pages.

```kida
{{ page.content | prefix_heading_ids("s1-") | safe }}
{# <h2 id="quick-start"> becomes <h2 id="s1-quick-start"> #}
{# <a href="#quick-start"> becomes <a href="#s1-quick-start"> #}
```

## urlize

Convert plain URLs in text to clickable HTML links.

```kida
{{ "Check out https://example.com for more info" | urlize }}
{# "Check out <a href="https://example.com">https://example.com</a>..." #}

{{ text | urlize(target='_blank', rel='noopener') }}
{# Opens links in new tab with security attributes #}

{{ text | urlize(shorten=true, shorten_length=30) }}
{# Shortens long URLs in display text #}
```
