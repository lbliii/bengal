---
title: "String Functions"
description: "11 essential string manipulation functions for text processing"
date: 2025-10-04
weight: 1
tags: ["templates", "functions", "strings", "text"]
toc: true
---

# String Functions

Bengal provides **11 essential string functions** for text manipulation in templates. These are the most commonly used functions for processing content, titles, excerpts, and more.

---

## 📚 Function Overview

| Function | Purpose | Example |
|----------|---------|---------|
| `truncatewords` | Truncate to word count | `{{/* text | truncatewords(50) */}}` |
| `truncatewords_html` | Truncate HTML preserving tags | `{{/* html | truncatewords_html(50) */}}` |
| `truncate_chars` | Truncate to character count | `{{/* text | truncate_chars(200) */}}` |
| `slugify` | Create URL-safe slug | `{{/* title | slugify */}}` |
| `markdownify` | Render markdown to HTML | `{{/* md | markdownify | safe */}}` |
| `strip_html` | Remove HTML tags | `{{/* html | strip_html */}}` |
| `replace_regex` | Replace using regex | `{{/* text | replace_regex('\\d+', 'N') */}}` |
| `pluralize` | Singular/plural forms | `{{/* count | pluralize('item') */}}` |
| `reading_time` | Calculate read time | `{{/* content | reading_time */}} min` |
| `excerpt` | Extract smart excerpt | `{{/* text | excerpt(200) */}}` |
| `strip_whitespace` | Normalize whitespace | `{{/* text | strip_whitespace */}}` |

---

## 🔤 truncatewords

Truncate text to a specified number of words.

### Signature

```jinja2
{{/* text | truncatewords(count, suffix="...") */}}
```

### Parameters

- **text** (str): Text to truncate
- **count** (int): Maximum number of words
- **suffix** (str, optional): Suffix to append when truncated. Default: `"..."`

### Returns

String truncated to word count with suffix if truncated.

### Examples

#### Basic Usage

```jinja2
{# Truncate post excerpt to 50 words #}
<div class="excerpt">
  {{/* post.content | truncatewords(50) */}}
</div>
```

**Output:**
```html
<div class="excerpt">
  This is the beginning of the post content. It will be truncated to exactly fifty words and then an ellipsis will be added...
</div>
```

#### Custom Suffix

```jinja2
{# Use custom "Read more" link #}
<p>
  {{/* post.content | truncatewords(30, suffix=" [Read more →]") */}}
</p>
```

**Output:**
```html
<p>
  This is a shorter excerpt that will be truncated to thirty words [Read more →]
</p>
```

#### Blog Card Preview

```jinja2
{% for post in recent_posts %}
  <article class="post-card">
    <h2><a href="{{/* post.url */}}">{{/* post.title */}}</a></h2>
    <div class="preview">
      {{/* post.content | strip_html | truncatewords(40) */}}
    </div>
    <a href="{{/* post.url */}}" class="read-more">Continue reading</a>
  </article>
{% endfor %}
```

### Edge Cases

```{warning} Empty or Short Text
If text is empty or shorter than the count, it returns unchanged (no suffix added).

```jinja2
{{/* "Short text" | truncatewords(100) */}}
{# Returns: "Short text" (no ellipsis) #}
```
```

### Best Practices

```{tip} Combine with strip_html
Always strip HTML before truncating to avoid cutting in the middle of tags:

```jinja2
{# Good #}
{{/* post.content | strip_html | truncatewords(50) */}}

{# Bad - might cut HTML tags #}
{{/* post.content | truncatewords(50) */}}
```
```

---

## 🏷️ truncatewords_html

Truncate HTML text to word count, preserving HTML tags.

### Signature

```jinja2
{{/* html | truncatewords_html(count, suffix="...") */}}
```

### Parameters

- **html** (str): HTML text to truncate
- **count** (int): Maximum number of words
- **suffix** (str, optional): Suffix to append. Default: `"..."`

### Returns

Truncated HTML with properly closed tags (simplified implementation).

### Examples

#### Preserve Formatting

```jinja2
{# Truncate while keeping bold, italic, links #}
{{/* post.html_content | truncatewords_html(50) */}}
```

**Input:**
```html
<p>This is <strong>bold text</strong> and <em>italic text</em> with a <a href="/link">link</a>...</p>
```

**Output:**
```html
This is bold text and italic text with a link...
```

#### Blog Content Preview

```jinja2
<div class="post-preview">
  {{/* post.rendered_content | truncatewords_html(100) */}}
</div>
```

### Implementation Note

```{note} Simplified Implementation
The current implementation strips HTML for word counting but doesn't fully preserve tag structure. For complex HTML, consider using `strip_html` + `truncatewords` instead:

```jinja2
{{/* html | strip_html | truncatewords(50) */}}
```

A more sophisticated HTML-preserving version may be added in future versions.
```

---

## ✂️ truncate_chars

Truncate text to a specific character length.

### Signature

```jinja2
{{ text | truncate_chars(length, suffix="...") }}
```

### Parameters

- **text** (str): Text to truncate
- **length** (int): Maximum character length
- **suffix** (str, optional): Suffix to append. Default: `"..."`

### Returns

String truncated to character length with suffix if truncated.

### Examples

#### Meta Description

```jinja2
{# Ensure meta description is under 160 characters #}
<meta name="description" content="{{ page.description | truncate_chars(160) }}">
```

#### Tweet-Length Preview

```jinja2
{# Twitter has 280 character limit #}
<div class="tweet-preview">
  {{ post.excerpt | truncate_chars(260) }}
  <a href="{{ post.url }}">Read more</a>
</div>
```

#### Truncate File Names

```jinja2
{# Show shortened file names in lists #}
{% for file in files %}
  <li>{{ file.name | truncate_chars(40) }}</li>
{% endfor %}
```

### Comparison with truncatewords

```{tabs}
:id: truncate-comparison

### Tab: truncate_chars

**Character-based:**
```jinja2
{{ "The quick brown fox jumps" | truncate_chars(15) }}
```

**Output:** `"The quick brow..."`

**Good for:**
- Fixed-width displays
- Character limits (tweets, meta tags)
- Exact length requirements

### Tab: truncatewords

**Word-based:**
```jinja2
{{/* "The quick brown fox jumps" | truncatewords(3) */}}
```

**Output:** `"The quick brown..."`

**Good for:**
- Reading excerpts
- Natural text breaks
- Content previews
```

---

## 🔗 slugify

Convert text to URL-safe slug.

### Signature

```jinja2
{{ text | slugify }}
```

### Parameters

- **text** (str): Text to convert

### Returns

URL-safe lowercase slug with hyphens.

### Examples

#### Create Page URLs

```jinja2
{# Generate URL from title #}
{% set slug = post.title | slugify %}
<a href="/posts/{{ slug }}/">{{ post.title }}</a>
```

**Examples:**
- `"Hello World!"` → `"hello-world"`
- `"What's New in 2025?"` → `"whats-new-in-2025"`
- `"C++ Programming"` → `"c-programming"`

#### Generate IDs

```jinja2
{# Create HTML IDs from headings #}
{% for heading in headings %}
  <h2 id="{{ heading | slugify }}">{{ heading }}</h2>
{% endfor %}
```

#### File Names

```jinja2
{# Generate safe file names #}
{% set filename = post.title | slugify ~ ".html" %}
```

### Rules

```{example} Slugification Rules

1. **Convert to lowercase:** `"Hello"` → `"hello"`
2. **Replace spaces with hyphens:** `"hello world"` → `"hello-world"`
3. **Remove special characters:** `"what's up?"` → `"whats-up"`
4. **Collapse multiple hyphens:** `"hello  world"` → `"hello-world"`
5. **Strip leading/trailing hyphens:** `"-hello-"` → `"hello"`

**Examples:**
```jinja2
{{ "Hello, World!" | slugify }}  {# "hello-world" #}
{{ "2025 Annual Report" | slugify }}  {# "2025-annual-report" #}
{{ "C++ & Python" | slugify }}  {# "c-python" #}
```
```

### Best Practices

```{tip} Use for Navigation Anchors
Perfect for creating table of contents anchors:

```jinja2
{% for heading in page.toc %}
  <a href="#{{ heading.title | slugify }}">{{ heading.title }}</a>
{% endfor %}
```
```

---

## 📝 markdownify

Render Markdown text to HTML.

### Signature

```jinja2
{{ text | markdownify | safe }}
```

### Parameters

- **text** (str): Markdown text to render

### Returns

Rendered HTML string.

### Examples

#### Render Custom Markdown Field

```jinja2
{# Render markdown from custom field #}
<div class="bio">
  {{ author.bio_markdown | markdownify | safe }}
</div>
```

#### Dynamic Content

```jinja2
{# Render markdown from data file #}
{% set features = get_data('features.yaml') %}
{% for feature in features %}
  <div class="feature">
    <h3>{{ feature.name }}</h3>
    <div class="description">
      {{ feature.description_md | markdownify | safe }}
    </div>
  </div>
{% endfor %}
```

#### Inline Markdown

```jinja2
{# Render small markdown snippets #}
<p class="note">
  {{ note_text | markdownify | safe }}
</p>
```

### Important Notes

```{warning} Always Use | safe
Markdown renders to HTML. You **must** use `| safe` to prevent HTML escaping:

```jinja2
{# Good #}
{{ text | markdownify | safe }}

{# Bad - HTML will be escaped #}
{{ text | markdownify }}
```

Otherwise, you'll see `&lt;p&gt;` instead of actual HTML tags.
```

```{note} Extensions Supported
The markdown renderer includes:
- **extra** - Tables, fenced code, etc.
- **codehilite** - Syntax highlighting
- **tables** - GFM tables
- **fenced_code** - ``` code blocks

If markdown library is not installed, returns text unchanged.
```

---

## 🧹 strip_html

Remove all HTML tags from text.

### Signature

```jinja2
{{ text | strip_html }}
```

### Parameters

- **text** (str): HTML text to clean

### Returns

Plain text with all HTML tags removed.

### Examples

#### Clean Content for Excerpts

```jinja2
{# Remove HTML before truncating #}
<div class="excerpt">
  {{/* post.html_content | strip_html | truncatewords(50) */}}
</div>
```

#### Search Index

```jinja2
{# Create clean text for search #}
{
  "title": "{{/* post.title */}}",
  "content": "{{/* post.content | strip_html | truncatewords(200) */}}"
}
```

#### Plain Text Email

```jinja2
{# Generate plain text version #}
Dear {{ user.name }},

{{ email_body_html | strip_html }}

Best regards
```

### What It Removes

```{example} HTML Stripping Examples

```jinja2
{{ "<p>Hello <strong>world</strong>!</p>" | strip_html }}
{# Output: "Hello world!" #}

{{ "<div class='content'>Text <a href='url'>link</a></div>" | strip_html }}
{# Output: "Text link" #}

{{ "Plain text" | strip_html }}
{# Output: "Plain text" (unchanged) #}
```

Also decodes HTML entities:
```jinja2
{{ "Hello &amp; goodbye" | strip_html }}
{# Output: "Hello & goodbye" #}
```
```

### Common Use Cases

```{tabs}
:id: strip-html-uses

### Tab: Content Preview

```jinja2
{# Clean preview without formatting #}
<div class="preview">
  {{/* post.content | strip_html | truncatewords(40) */}}
</div>
```

### Tab: Meta Tags

```jinja2
{# Meta description can't have HTML #}
<meta name="description" content="{{ page.content | strip_html | truncate_chars(160) }}">
```

### Tab: Reading Time

```jinja2
{# Calculate based on text only #}
{{ post.content | strip_html | reading_time }} min read
```

### Tab: Search Indexing

```jinja2
{# Index clean text only #}
{
  "content": "{{ page.content | strip_html }}"
}
```
```

---

## 🔄 replace_regex

Replace text using regular expressions.

### Signature

```jinja2
{{ text | replace_regex(pattern, replacement) }}
```

### Parameters

- **text** (str): Text to search in
- **pattern** (str): Regular expression pattern
- **replacement** (str): Replacement text

### Returns

Text with replacements made.

### Examples

#### Remove Numbers

```jinja2
{# Replace all numbers with 'N' #}
{{ "Order 12345 from 2025" | replace_regex('\\d+', 'N') }}
{# Output: "Order N from N" #}
```

#### Sanitize Usernames

```jinja2
{# Remove special characters #}
{% set clean_username = username | replace_regex('[^a-zA-Z0-9_]', '') %}
```

#### Format Phone Numbers

```jinja2
{# Add dashes to phone numbers #}
{{ phone | replace_regex('(\d{3})(\d{3})(\d{4})', '\1-\2-\3') }}
{# "5551234567" → "555-123-4567" #}
```

#### Remove Extra Spaces

```jinja2
{# Collapse multiple spaces #}
{{ text | replace_regex('\s+', ' ') }}
```

### Advanced Examples

```{example} Complex Patterns

**Remove HTML comments:**
```jinja2
{{ html | replace_regex('<!--.*?-->', '') }}
```

**Extract domain from email:**
```jinja2
{{ email | replace_regex('.*@', '') }}
{# "user@example.com" → "example.com" #}
```

**Mask credit card:**
```jinja2
{{ cc | replace_regex('\d(?=\d{4})', '*') }}
{# "1234567890123456" → "************3456" #}
```
```

### Error Handling

```{warning} Invalid Regex
If the regex pattern is invalid, the filter returns the original text unchanged:

```jinja2
{{ text | replace_regex('[invalid(', 'x') }}
{# Returns original text if regex error #}
```

Test your patterns carefully!
```

---

## 🔢 pluralize

Return singular or plural form based on count.

### Signature

```jinja2
{{ count | pluralize(singular, plural=None) }}
```

### Parameters

- **count** (int): Number to check
- **singular** (str): Singular form
- **plural** (str, optional): Plural form. Default: `singular + 's'`

### Returns

Appropriate form based on count.

### Examples

#### Auto-Pluralization

```jinja2
{# Automatic 's' suffix #}
{{ posts|length }} {{ posts|length | pluralize('post') }}
{# 1 → "1 post" #}
{# 5 → "5 posts" #}
```

#### Custom Plural

```jinja2
{# Irregular plurals #}
{{ count | pluralize('person', 'people') }}
{{ count | pluralize('child', 'children') }}
{{ count | pluralize('category', 'categories') }}
```

#### In Sentences

```jinja2
<p>
  Found {{ results|length }} 
  {{ results|length | pluralize('result') }}
  in {{ categories|length }}
  {{ categories|length | pluralize('category', 'categories') }}.
</p>
```

**Output examples:**
- "Found 1 result in 1 category."
- "Found 15 results in 3 categories."

### Common Plurals

```{example} Irregular Plurals

```jinja2
{# Regular (add 's') #}
{{ n | pluralize('page') }}  {# pages #}
{{ n | pluralize('item') }}  {# items #}

{# Irregular #}
{{ n | pluralize('person', 'people') }}
{{ n | pluralize('child', 'children') }}
{{ n | pluralize('mouse', 'mice') }}
{{ n | pluralize('foot', 'feet') }}
{{ n | pluralize('category', 'categories') }}
{{ n | pluralize('entry', 'entries') }}
```
```

---

## ⏱️ reading_time

Calculate reading time in minutes.

### Signature

```jinja2
{{ text | reading_time(wpm=200) }}
```

### Parameters

- **text** (str): Text to analyze
- **wpm** (int, optional): Words per minute reading speed. Default: `200`

### Returns

Reading time in minutes (minimum 1).

### Examples

#### Basic Usage

```jinja2
{# Show reading time #}
<div class="meta">
  {{ post.content | reading_time }} min read
</div>
```

#### Custom Reading Speed

```jinja2
{# Faster reader (250 wpm) #}
{{ post.content | reading_time(250) }} min read

{# Technical content (slower, 150 wpm) #}
{{ technical_doc | reading_time(150) }} min read
```

#### Complete Meta Info

```jinja2
<div class="post-meta">
  <span class="date">{{ post.date | format_date('%B %d, %Y') }}</span>
  <span class="reading-time">{{ post.content | reading_time }} min read</span>
  <span class="word-count">{{ post.content | strip_html | wordcount }} words</span>
</div>
```

### How It Works

```{note} Calculation Method

1. **Strip HTML** if present
2. **Count words** (split by whitespace)
3. **Calculate:** `minutes = words / wpm`
4. **Round** to nearest integer
5. **Minimum** of 1 minute

**Example:**
- Content: 850 words
- Speed: 200 wpm
- Calculation: 850 / 200 = 4.25
- Result: **4 minutes**
```

### Reading Speed Guide

```{tabs}
:id: reading-speeds

### Tab: Standard (200 wpm)

**Default speed for:**
- General articles
- Blog posts
- News content

```jinja2
{{ content | reading_time }}
```

### Tab: Fast (250-300 wpm)

**For:**
- Casual reading
- Fiction
- Familiar topics

```jinja2
{{ content | reading_time(250) }}
```

### Tab: Slow (150 wpm)

**For:**
- Technical documentation
- Academic papers
- Complex topics
- Non-native readers

```jinja2
{{ content | reading_time(150) }}
```
```

---

## 📄 excerpt

Extract excerpt from text with smart handling.

### Signature

```jinja2
{{ text | excerpt(length=200, respect_word_boundaries=True) }}
```

### Parameters

- **text** (str): Text to excerpt from
- **length** (int, optional): Maximum length in characters. Default: `200`
- **respect_word_boundaries** (bool, optional): Don't cut words in half. Default: `True`

### Returns

Excerpt with ellipsis if truncated.

### Examples

#### Basic Excerpt

```jinja2
{# Extract 200 character excerpt #}
<p class="excerpt">
  {{ post.content | excerpt(200) }}
</p>
```

#### Custom Length

```jinja2
{# Short excerpt for cards #}
<div class="card">
  <h3>{{ post.title }}</h3>
  <p>{{ post.content | excerpt(150) }}</p>
</div>
```

#### Allow Word Splitting

```jinja2
{# Exact 100 characters, even if mid-word #}
{{ text | excerpt(100, false) }}
```

### Comparison with truncatewords

```{tabs}
:id: excerpt-vs-truncatewords

### Tab: excerpt (Character-Based)

**Fixed length:**
```jinja2
{{ text | excerpt(200) }}
```

- Truncates to ~200 characters
- Respects word boundaries
- Strips HTML first
- Adds "..." if truncated

**Good for:**
- Meta descriptions
- Consistent preview sizes
- Fixed-width displays

### Tab: truncatewords (Word-Based)

**Fixed word count:**
```jinja2
{{/* text | truncatewords(50) */}}
```

- Truncates to exactly 50 words
- Variable character length
- Can keep or strip HTML
- Adds "..." if truncated

**Good for:**
- Content previews
- Reading excerpts
- Natural text breaks
```

### Smart Word Boundaries

```{example} Word Boundary Behavior

**With respect_word_boundaries=True (default):**
```jinja2
{{ "The quick brown fox jumps over the lazy dog" | excerpt(20) }}
```
**Output:** `"The quick brown..."`
(Stops at last complete word before 20 chars)

**With respect_word_boundaries=False:**
```jinja2
{{ "The quick brown fox jumps over the lazy dog" | excerpt(20, false) }}
```
**Output:** `"The quick brown fo..."`
(Cuts at exactly 20 chars)
```

---

## 🧽 strip_whitespace

Remove extra whitespace from text.

### Signature

```jinja2
{{ text | strip_whitespace }}
```

### Parameters

- **text** (str): Text to clean

### Returns

Text with normalized whitespace.

### Examples

#### Clean User Input

```jinja2
{# Normalize form input #}
{% set clean_name = form.name | strip_whitespace %}
```

#### Clean Markdown Output

```jinja2
{# Remove extra spacing from rendered markdown #}
<div class="content">
  {{ markdown_text | markdownify | strip_html | strip_whitespace }}
</div>
```

#### Compact Display

```jinja2
{# Remove newlines and extra spaces #}
<span class="compact">
  {{ multiline_text | strip_whitespace }}
</span>
```

### What It Does

```{example} Whitespace Normalization

**Multiple spaces → single space:**
```jinja2
{{ "Hello    world" | strip_whitespace }}
{# Output: "Hello world" #}
```

**Newlines → spaces:**
```jinja2
{{ "Line 1\nLine 2\n\nLine 3" | strip_whitespace }}
{# Output: "Line 1 Line 2 Line 3" #}
```

**Tabs → spaces:**
```jinja2
{{ "Tab\there\t\tthere" | strip_whitespace }}
{# Output: "Tab here there" #}
```

**Trim edges:**
```jinja2
{{ "  spaced out  " | strip_whitespace }}
{# Output: "spaced out" #}
```
```

---

## 🎯 Common Patterns

### Blog Post Preview

```jinja2
{% for post in recent_posts %}
  <article class="post-preview">
    <h2><a href="{{ post.url }}">{{ post.title }}</a></h2>
    
    <div class="meta">
      {{ post.date | format_date('%B %d, %Y') }} · 
      {{ post.content | reading_time }} min read
    </div>
    
    <div class="excerpt">
      {{/* post.content | strip_html | truncatewords(50) */}}
    </div>
    
    <a href="{{ post.url }}" class="read-more">
      Read more →
    </a>
  </article>
{% endfor %}
```

### SEO Meta Tags

```jinja2
{# Page title (60 chars) #}
<title>{{ page.title | truncate_chars(60, suffix='') }}</title>

{# Meta description (160 chars) #}
<meta name="description" 
      content="{{ page.content | strip_html | excerpt(160) }}">

{# URL-safe slug #}
<link rel="canonical" 
      href="{{ site.baseurl }}/{{ page.title | slugify }}/">
```

### Clean Content Pipeline

```jinja2
{# Complete cleaning pipeline #}
{% set clean_content = 
    post.content 
    | strip_html 
    | strip_whitespace 
    | truncatewords(100) 
%}

<div class="preview">{{ clean_content }}</div>
```

---

## 📚 Related Functions

- **[Advanced String Functions](advanced-strings.md)** - camelize, underscore, titleize
- **[SEO Functions](seo.md)** - meta_description, meta_keywords
- **[Content Functions](content.md)** - safe_html, nl2br, wordwrap

---

## 💡 Best Practices

```{tip} Function Chaining
String functions work great in chains:

```jinja2
{# Strip → Truncate → Clean #}
{{/* post.content | strip_html | truncatewords(50) | strip_whitespace */}}
```

Order matters! Process in logical sequence.
```

```{success} Performance
String functions are **fast**:
- `strip_html`: < 1ms
- `truncatewords`: < 1ms
- `slugify`: < 1ms
- `reading_time`: < 1ms

Chain multiple functions without performance concerns!
```

```{warning} HTML Safety
When rendering HTML:
- Use `| safe` after `markdownify`
- Use `| escape` for user input
- Use `strip_html` before truncating

**Never** `| safe` user-provided content!
```

---

**Module:** `bengal.rendering.template_functions.strings`  
**Functions:** 11  
**Last Updated:** October 4, 2025

