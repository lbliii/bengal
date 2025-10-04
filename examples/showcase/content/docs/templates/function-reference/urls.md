---
title: "URL Functions"
description: "3 URL manipulation functions for encoding, decoding, and absolute URLs"
date: 2025-10-04
weight: 5
tags: ["templates", "functions", "urls", "encoding", "links"]
toc: true
---

# URL Functions

Bengal provides **3 URL manipulation functions** for working with links, encoding parameters, and generating absolute URLs. Essential for navigation, forms, and API integrations.

---

## 📚 Function Overview

| Function | Purpose | Example |
|----------|---------|---------|
| `absolute_url` | Convert to absolute URL | `{{/* url | absolute_url */}}` |
| `url_encode` | Percent-encode for URLs | `{{ text | url_encode }}` |
| `url_decode` | Decode percent-encoding | `{{ encoded | url_decode }}` |

---

## 🌐 absolute_url

Convert relative URL to absolute URL with site base URL.

### Signature

```jinja2
{{/* url | absolute_url */}}
```

### Parameters

- **url** (str): Relative or absolute URL

### Returns

Absolute URL with site base URL prepended.

### Examples

#### Basic Usage

```jinja2
{# Convert relative URL to absolute #}
<link rel="canonical" href="{{/* page.url | absolute_url */}}">
```

**Input:** `/blog/my-post/`
**Output:** `https://example.com/blog/my-post/`

#### Open Graph URLs

```jinja2
{# Absolute URLs required for Open Graph #}
<meta property="og:url" content="{{/* page.url | absolute_url */}}">
<meta property="og:image" content="{{/* page.image | absolute_url */}}">
```

#### RSS Feed Links

```jinja2
{# RSS feeds require absolute URLs #}
<rss version="2.0">
  <channel>
    {% for post in recent_posts %}
      <item>
        <link>{{/* post.url | absolute_url */}}</link>
        <guid>{{/* post.url | absolute_url */}}</guid>
      </item>
    {% endfor %}
  </channel>
</rss>
```

#### Sitemap Generation

```jinja2
{# Sitemaps require absolute URLs #}
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  {% for page in pages %}
    <url>
      <loc>{{/* page.url | absolute_url */}}</loc>
    </url>
  {% endfor %}
</urlset>
```

### When to Use Absolute URLs

````{tabs}
:id: absolute-url-uses

### Tab: Required

**Must use absolute URLs:**

✅ **Open Graph / Twitter Cards**
```jinja2
<meta property="og:url" content="{{/* page.url | absolute_url */}}">
```

✅ **RSS / Atom feeds**
```jinja2
<link>{{/* post.url | absolute_url */}}</link>
```

✅ **Canonical URLs**
```jinja2
<link rel="canonical" href="{{/* page.url | absolute_url */}}">
```

✅ **Sitemaps**
```jinja2
<loc>{{/* page.url | absolute_url */}}</loc>
```

✅ **Email content**
```jinja2
<a href="{{/* article.url | absolute_url */}}">Read more</a>
```

### Tab: Optional

**Can use relative URLs:**

⚠️ **Internal navigation**
```jinja2
<a href="{{ page.url }}">Link</a>  {# Relative is fine #}
```

⚠️ **Images (usually)**
```jinja2
<img src="{{ image.path }}">  {# Relative works #}
```

⚠️ **Stylesheets/Scripts**
```jinja2
<link rel="stylesheet" href="/css/style.css">  {# Relative OK #}
```

### Tab: Best Practice

**Use absolute when:**
- Content might be viewed outside your site
- Sharing on social media
- RSS/email distribution
- External APIs/webhooks
- Cross-domain references

**Use relative when:**
- Internal site navigation
- Better for site migrations
- Smaller HTML file size
- Simpler maintenance
````

### Configuration

```{note} Base URL Required
The `absolute_url` function uses your site's base URL from config:

```toml
# bengal.toml
[site]
baseurl = "https://example.com"
```

Without `baseurl`, it returns the relative URL unchanged.
```

---

## 🔐 url_encode

URL-encode string (percent encoding) for safe use in URLs.

### Signature

```jinja2
{{ text | url_encode }}
```

### Parameters

- **text** (str): Text to encode

### Returns

URL-encoded text with special characters as `%XX` codes.

### Examples

#### Search Query Parameters

```jinja2
{# Encode search query #}
<form action="/search">
  <input type="text" name="q" value="{{ query }}">
</form>

{# In search results URL #}
<a href="/search?q={{ search_term | url_encode }}">Search</a>
```

**Example:**
- Input: `"hello world"`
- Output: `"hello%20world"`
- URL: `/search?q=hello%20world`

#### Multiple Parameters

```jinja2
{# Build query string #}
<a href="/filter?category={{ cat | url_encode }}&tag={{ tag | url_encode }}">
  Filter
</a>
```

**Example:**
- `category = "Arts & Crafts"`
- `tag = "DIY Projects"`
- URL: `/filter?category=Arts%20%26%20Crafts&tag=DIY%20Projects`

#### Social Sharing Links

```jinja2
{# Twitter share link #}
{% set tweet_text = post.title ~ " - " ~ post.description %}
<a href="https://twitter.com/intent/tweet?text={{ tweet_text | url_encode }}&url={{/* page.url | absolute_url | url_encode */}}">
  Share on Twitter
</a>
```

#### Email Links

```jinja2
{# Mailto link with subject and body #}
{% set subject = "Check out " ~ post.title %}
{% set body = "I thought you might like this: " ~ post.url | absolute_url %}

<a href="mailto:?subject={{ subject | url_encode }}&body={{ body | url_encode }}">
  Email this article
</a>
```

### What Gets Encoded

```{example} URL Encoding Examples

**Space → %20 or +:**
```jinja2
{{ "hello world" | url_encode }}  {# "hello%20world" #}
```

**Special characters:**
```jinja2
{{ "user@example.com" | url_encode }}     {# "user%40example.com" #}
{{ "50% off!" | url_encode }}              {# "50%25%20off%21" #}
{{ "C++ programming" | url_encode }}       {# "C%2B%2B%20programming" #}
{{ "quotes: 'hello'" | url_encode }}       {# "quotes%3A%20%27hello%27" #}
```

**Unicode:**
```jinja2
{{ "café" | url_encode }}    {# "caf%C3%A9" #}
{{ "日本語" | url_encode }}   {# "%E6%97%A5%E6%9C%AC%E8%AA%9E" #}
```

**Already safe characters (not encoded):**
- Letters: `A-Z`, `a-z`
- Digits: `0-9`
- Safe: `-`, `_`, `.`, `~`
```

### Complete Social Sharing

```{example} Social Share Buttons

```jinja2
{# Reusable social share buttons #}
{% set share_url = page.url | absolute_url %}
{% set share_title = page.title %}
{% set share_desc = page.content | meta_description(200) %}

<div class="share-buttons">
  {# Twitter #}
  <a href="https://twitter.com/intent/tweet?text={{ share_title | url_encode }}&url={{ share_url | url_encode }}" 
     target="_blank" rel="noopener">
    Share on Twitter
  </a>
  
  {# Facebook #}
  <a href="https://www.facebook.com/sharer/sharer.php?u={{ share_url | url_encode }}" 
     target="_blank" rel="noopener">
    Share on Facebook
  </a>
  
  {# LinkedIn #}
  <a href="https://www.linkedin.com/sharing/share-offsite/?url={{ share_url | url_encode }}" 
     target="_blank" rel="noopener">
    Share on LinkedIn
  </a>
  
  {# Email #}
  <a href="mailto:?subject={{ share_title | url_encode }}&body={{ share_desc | url_encode }}%0A%0A{{ share_url | url_encode }}">
    Share via Email
  </a>
  
  {# Reddit #}
  <a href="https://reddit.com/submit?url={{ share_url | url_encode }}&title={{ share_title | url_encode }}" 
     target="_blank" rel="noopener">
    Share on Reddit
  </a>
</div>
```
```

---

## 🔓 url_decode

Decode URL-encoded string (decode percent encoding).

### Signature

```jinja2
{{ text | url_decode }}
```

### Parameters

- **text** (str): URL-encoded text to decode

### Returns

Decoded text with `%XX` codes converted back to characters.

### Examples

#### Decode Query Parameters

```jinja2
{# Decode parameter from URL #}
{% set query = request.args.get('q', '') %}
<h1>Search Results for: {{ query | url_decode }}</h1>
```

**URL:** `/search?q=hello%20world`
**Output:** `"Search Results for: hello world"`

#### Display Encoded URLs

```jinja2
{# Make encoded URL human-readable #}
<div class="debug">
  Encoded: {{ url }}
  Decoded: {{ url | url_decode }}
</div>
```

#### Parse Referrer URLs

```jinja2
{# Extract readable info from referrer #}
{% set referrer = request.referrer | url_decode %}
<p>You came from: {{ referrer }}</p>
```

### Decode Examples

```{example} Decoding Examples

**Spaces:**
```jinja2
{{ "hello%20world" | url_decode }}    {# "hello world" #}
{{ "hello+world" | url_decode }}      {# "hello world" #}
```

**Special characters:**
```jinja2
{{ "user%40example.com" | url_decode }}          {# "user@example.com" #}
{{ "50%25%20off%21" | url_decode }}              {# "50% off!" #}
{{ "C%2B%2B%20programming" | url_decode }}       {# "C++ programming" #}
```

**Unicode:**
```jinja2
{{ "caf%C3%A9" | url_decode }}                   {# "café" #}
{{ "%E6%97%A5%E6%9C%AC%E8%AA%9E" | url_decode }} {# "日本語" #}
```
```

### When to Use url_decode

```{warning} Rare Use Case
You typically **don't need** `url_decode` because:

- Browsers decode URLs automatically
- Template variables are already decoded
- Query parameters are decoded by framework

**Use only when:**
- Displaying raw encoded URLs to users
- Debugging URL issues
- Processing manually encoded strings
- Working with external encoded data

**Example - when you DO need it:**
```jinja2
{# Show user what search they performed from URL #}
URL: /search?q=hello%20world
Display: "Searching for: {{ request.args.q | url_decode }}"
```

**Most of the time, you don't need url_decode!**
```

---

## 🎯 Common Patterns

### Navigation with Parameters

```jinja2
{# Filter links with preserved parameters #}
<nav class="filters">
  <a href="?category={{ 'tech' | url_encode }}&sort=date">Tech</a>
  <a href="?category={{ 'design' | url_encode }}&sort=date">Design</a>
  <a href="?category={{ 'business' | url_encode }}&sort=date">Business</a>
</nav>
```

### Search Form and Results

```jinja2
{# Search form #}
<form action="/search" method="get">
  <input type="text" name="q" value="{{ query }}" placeholder="Search...">
  <button type="submit">Search</button>
</form>

{# Search results with encoded "show more" link #}
{% if results %}
  <h2>Results for "{{ query }}"</h2>
  
  {% for result in results %}
    <div class="result">
      <h3><a href="{{ result.url }}">{{ result.title }}</a></h3>
      <p>{{ result.excerpt }}</p>
    </div>
  {% endfor %}
  
  {# Pagination with encoded query #}
  {% if has_more %}
    <a href="/search?q={{ query | url_encode }}&page={{ page + 1 }}">
      Show more results
    </a>
  {% endif %}
{% endif %}
```

### Tag Filtering

```jinja2
{# Tag cloud with encoded tag names #}
<div class="tag-cloud">
  {% for tag in all_tags | uniq | sort %}
    <a href="/tags/?tag={{ tag | url_encode }}" 
       class="tag tag-{{ tag | slugify }}">
      {{ tag }}
    </a>
  {% endfor %}
</div>

{# Tagged posts page #}
{% if current_tag %}
  <h1>Posts tagged: {{ current_tag | url_decode }}</h1>
  
  {% for post in posts | where('tags', current_tag) %}
    <article>{{ post.title }}</article>
  {% endfor %}
{% endif %}
```

### Complete Meta Tags

```jinja2
{# Complete meta tags using URL functions #}
<head>
  {# Canonical URL (absolute) #}
  <link rel="canonical" href="{{/* page.url | absolute_url */}}">
  
  {# Open Graph #}
  <meta property="og:url" content="{{/* page.url | absolute_url */}}">
  <meta property="og:image" content="{{/* page.image | absolute_url */}}">
  
  {# Sharing links in head #}
  <link rel="alternate" type="application/rss+xml" 
        href="{{/* '/rss.xml' | absolute_url */}}">
  
  {# Prefetch next page #}
  {% if next_page %}
    <link rel="next" href="{{/* next_page.url | absolute_url */}}">
  {% endif %}
</head>
```

---

## 📚 URL Encoding Reference

### When to Encode

````{tabs}
:id: when-to-encode

### Tab: Always Encode

**Must encode these:**

✅ **Query parameters:**
```jinja2
?q={{ search | url_encode }}
```

✅ **Form data in URLs:**
```jinja2
?name={{ name | url_encode }}&email={{ email | url_encode }}
```

✅ **Share buttons:**
```jinja2
https://twitter.com/...?text={{ text | url_encode }}
```

✅ **User input in URLs:**
```jinja2
/search/{{ user_query | url_encode }}
```

### Tab: Never Encode

**Don't encode these:**

❌ **URL path segments** (use slugify instead):
```jinja2
/posts/{{ title | slugify }}/  {# NOT url_encode #}
```

❌ **Already-encoded URLs:**
```jinja2
{{ encoded_url }}  {# Already encoded! #}
```

❌ **HTML content:**
```jinja2
{{ html_content }}  {# Use |safe, not |url_encode #}
```

### Tab: Double-Encoding

**Avoid double-encoding:**

```jinja2
{# Bad - double encoded! #}
{{ text | url_encode | url_encode }}

{# Good - encode once #}
{{ text | url_encode }}
```

**Check if already encoded:**
```jinja2
{% if '%' in text %}
  {# Probably already encoded #}
  {{ text }}
{% else %}
  {{ text | url_encode }}
{% endif %}
```
````

---

## 🔗 Building Query Strings

```{example} Dynamic Query Strings

```jinja2
{# Build query string from dict #}
{% set params = {
  'category': 'tech',
  'sort': 'date',
  'order': 'desc',
  'page': 1
} %}

{% set query_parts = [] %}
{% for key, value in params.items() %}
  {% set _ = query_parts.append(key ~ '=' ~ (value | url_encode)) %}
{% endfor %}

<a href="/search?{{ query_parts | join('&') }}">
  Filtered Results
</a>
```

**Output:**
```html
<a href="/search?category=tech&sort=date&order=desc&page=1">
  Filtered Results
</a>
```
```

---

## 📚 Related Functions

- **[String Functions](strings.md)** - slugify (for URL paths)
- **[SEO Functions](seo.md)** - canonical_url, og_image
- **[Content Functions](content.md)** - safe_html, escape_html

---

## 💡 Best Practices

```{success} URL Path vs Query Parameters

**For URL paths:** Use `slugify`
```jinja2
/blog/{{ title | slugify }}/  {# URL-safe slug #}
```

**For query parameters:** Use `url_encode`
```jinja2
?q={{ query | url_encode }}  {# Percent encoding #}
```

Different purposes, different functions!
```

```{tip} Always Encode User Input

```jinja2
{# Good - safe from injection #}
<a href="/search?q={{ user_query | url_encode }}">Search</a>

{# Bad - potential XSS/injection #}
<a href="/search?q={{ user_query }}">Search</a>
```

User input in URLs must always be encoded!
```

```{warning} Encode, Don't Escape
For URLs, use `url_encode`, not HTML escape:

```jinja2
{# Good #}
?query={{ text | url_encode }}

{# Wrong - HTML escape, not URL encode #}
?query={{ text | escape }}
```

Different contexts need different encoding!
```

```{note} Relative vs Absolute
**Relative URLs** (default):
- Smaller HTML
- Easier migrations
- Better for internal links

**Absolute URLs** (with `| absolute_url`):
- Required for Open Graph
- Required for RSS/Email
- Better for external sharing

Choose based on use case!
```

---

## 🎓 Complete Example

Here's a complete page using all URL functions:

```jinja2
{# search.html - Complete search page #}
<!DOCTYPE html>
<html>
<head>
  {# Absolute URLs for SEO #}
  <link rel="canonical" href="{{/* page.url | absolute_url */}}">
  <meta property="og:url" content="{{/* page.url | absolute_url */}}">
  
  {# RSS feed #}
  <link rel="alternate" type="application/rss+xml" 
        href="{{/* '/rss.xml' | absolute_url */}}">
</head>
<body>
  {# Search form #}
  <form action="/search" method="get">
    <input type="text" 
           name="q" 
           value="{{ query }}" 
           placeholder="Search...">
    <button type="submit">Search</button>
  </form>
  
  {% if query %}
    <h1>Results for "{{ query }}"</h1>
    
    {# Search results #}
    {% for result in results %}
      <article>
        <h2><a href="{{ result.url }}">{{ result.title }}</a></h2>
        <p>{{ result.excerpt }}</p>
      </article>
    {% endfor %}
    
    {# Pagination with encoded query #}
    <nav class="pagination">
      {% if page > 1 %}
        <a href="?q={{ query | url_encode }}&page={{ page - 1 }}">Previous</a>
      {% endif %}
      
      {% if has_more %}
        <a href="?q={{ query | url_encode }}&page={{ page + 1 }}">Next</a>
      {% endif %}
    </nav>
    
    {# Share search results #}
    {% set share_url = page.url | absolute_url %}
    {% set share_text = "Search results for: " ~ query %}
    
    <div class="share">
      <a href="https://twitter.com/intent/tweet?text={{ share_text | url_encode }}&url={{ share_url | url_encode }}">
        Share on Twitter
      </a>
    </div>
  {% endif %}
</body>
</html>
```

---

**Module:** `bengal.rendering.template_functions.urls`  
**Functions:** 3  
**Last Updated:** October 4, 2025

