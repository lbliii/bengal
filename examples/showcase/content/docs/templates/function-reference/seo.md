---
title: "SEO Functions"
description: "4 SEO optimization functions for meta tags, canonical URLs, and Open Graph"
date: 2025-10-04
weight: 11
tags: ["templates", "functions", "seo", "meta-tags", "optimization"]
toc: true
---

# SEO Functions

Bengal provides **4 SEO helper functions** for generating search-engine-friendly meta tags, canonical URLs, and Open Graph data. These functions help your site rank better and look great when shared on social media.

---

## 📚 Function Overview

| Function | Purpose | Example |
|----------|---------|---------|
| `meta_description` | Generate meta description | `{{/* content | meta_description(160) */}}` |
| `meta_keywords` | Generate meta keywords | `{{ tags | meta_keywords }}` |
| `canonical_url` | Create canonical URL | `{{ canonical_url(page.url) }}` |
| `og_image` | Open Graph image URL | `{{ og_image('hero.jpg') }}` |

---

## 📝 meta_description

Generate SEO-friendly meta description from text.

### Signature

```jinja2
{{/* text | meta_description(length=160) */}}
```

### Parameters

- **text** (str): Source text (can include HTML)
- **length** (int, optional): Maximum character length. Default: `160`

### Returns

Clean, truncated text suitable for meta description tag.

### What It Does

1. **Strips HTML tags** - Removes all markup
2. **Normalizes whitespace** - Collapses spaces/newlines
3. **Truncates intelligently** - Tries to end at sentence boundary
4. **Adds ellipsis** - When truncated mid-sentence

### Examples

#### Basic Usage

```jinja2
{# Generate meta description from page content #}
<meta name="description" content="{{/* page.content | meta_description */}}">
```

**Input:** Long HTML content
**Output:** Clean 160-character description with ellipsis if truncated

#### Custom Length

```jinja2
{# Shorter description for mobile #}
<meta name="description" content="{{/* page.content | meta_description(120) */}}">
```

#### Use Existing Description Field

```jinja2
{# Prefer manual description, fall back to auto-generated #}
{% if page.metadata.description %}
  <meta name="description" content="{{ page.metadata.description }}">
{% else %}
  <meta name="description" content="{{/* page.content | meta_description */}}">
{% endif %}
```

### Smart Truncation

```{example} Sentence-Aware Truncation

**Input text (200 chars):**
```
This is the first sentence. This is the second sentence that might get cut off. This is a third sentence that definitely won't fit.
```

**With meta_description(160):**
```
This is the first sentence. This is the second sentence that might get cut off…
```

**Behavior:**
- Truncates at ~160 characters
- Tries to end at sentence boundary (. ! ?)
- Falls back to word boundary if no sentence break found
- Adds "…" if truncated
```

### Complete Head Section

```jinja2
<head>
  {# Title #}
  <title>{{ page.title }} | {{ site.title }}</title>
  
  {# Meta description #}
  {% set description = page.metadata.description or (page.content | meta_description(160)) %}
  <meta name="description" content="{{ description }}">
  
  {# Open Graph #}
  <meta property="og:title" content="{{ page.title }}">
  <meta property="og:description" content="{{ description }}">
  <meta property="og:url" content="{{ canonical_url(page.url) }}">
  
  {# Twitter Card #}
  <meta name="twitter:title" content="{{ page.title }}">
  <meta name="twitter:description" content="{{ description }}">
</head>
```

### SEO Best Practices

```{tip} Optimal Length
**Google displays:**
- Desktop: ~155-160 characters
- Mobile: ~120-130 characters

**Recommendations:**
- Use 150-160 chars for best results
- Front-load important keywords
- Make it compelling (users click on it!)
- Unique for every page

```jinja2
{# Good length #}
{{/* page.content | meta_description(155) */}}
```
```

```{warning} Avoid These Mistakes

**❌ Too short:**
```jinja2
{{/* page.content | meta_description(50) */}}  {# Not enough info #}
```

**❌ Too long:**
```jinja2
{{/* page.content | meta_description(300) */}}  {# Gets truncated by Google #}
```

**❌ Duplicate descriptions:**
```jinja2
{# Don't use same description for all pages! #}
<meta name="description" content="{{ site.description }}">
```

**✅ Just right:**
```jinja2
<meta name="description" content="{{/* page.content | meta_description(160) */}}">
```
```

---

## 🏷️ meta_keywords

Generate meta keywords from tags list.

### Signature

```jinja2
{{ tags | meta_keywords(max_count=10) }}
```

### Parameters

- **tags** (list): List of keywords/tags
- **max_count** (int, optional): Maximum number of keywords. Default: `10`

### Returns

Comma-separated keywords string.

### Examples

#### Basic Usage

```jinja2
{# Generate keywords from page tags #}
<meta name="keywords" content="{{ page.tags | meta_keywords }}">
```

**Input:** `['python', 'django', 'web', 'tutorial', 'beginner']`
**Output:** `"python, django, web, tutorial, beginner"`

#### Limit Keywords

```jinja2
{# Only top 5 keywords #}
<meta name="keywords" content="{{ page.tags | meta_keywords(5) }}">
```

#### Combine Multiple Sources

```jinja2
{# Combine tags and categories #}
{% set all_keywords = page.tags + page.categories %}
<meta name="keywords" content="{{ all_keywords | meta_keywords(10) }}">
```

### Modern SEO Note

```{note} Limited SEO Value
Meta keywords have **minimal SEO impact** in modern search engines:

- ❌ Google **ignores** meta keywords (since 2009)
- ⚠️ Bing gives them **very low** weight
- ✅ Might help with **internal site search**

**Still useful for:**
- Internal site search indexing
- Content management
- Categorization
- Legacy systems

**Focus instead on:**
- Quality content
- Meta descriptions
- Heading structure (H1, H2, H3)
- Alt text for images
```

### Alternatives to Meta Keywords

```{tabs}
:id: keyword-alternatives

### Tab: Schema.org

**Use structured data instead:**
```jinja2
<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "Article",
  "keywords": "{{ page.tags | join(', ') }}"
}
</script>
```

Better for search engines!

### Tab: Hidden Content

**In-content keywords:**
```jinja2
<div class="hidden-seo" aria-hidden="true" style="display:none;">
  Keywords: {{ page.tags | join(', ') }}
</div>
```

⚠️ **Not recommended** - can be seen as spam

### Tab: Natural Usage

**Best approach - use naturally:**
```jinja2
<footer class="article-meta">
  <span>Tagged with:</span>
  {% for tag in page.tags %}
    <a href="/tags/{{ tag | slugify }}/" rel="tag">{{ tag }}</a>
  {% endfor %}
</footer>
```

Natural, visible tags are better for SEO!
```

---

## 🔗 canonical_url

Generate canonical URL for a page.

### Signature

```jinja2
{{ canonical_url(path) }}
```

### Parameters

- **path** (str): Page path (relative or absolute)

### Returns

Full canonical URL with site base URL.

### Examples

#### Basic Usage

```jinja2
{# Generate canonical URL #}
<link rel="canonical" href="{{ canonical_url(page.url) }}">
```

**Input:** `"/blog/my-post/"`
**Output:** `"https://example.com/blog/my-post/"`

#### In Head Section

```jinja2
<head>
  <title>{{ page.title }}</title>
  
  {# Canonical URL #}
  <link rel="canonical" href="{{ canonical_url(page.url) }}">
  
  {# Open Graph URL #}
  <meta property="og:url" content="{{ canonical_url(page.url) }}">
</head>
```

#### For Paginated Content

```jinja2
{% if page_num == 1 %}
  {# First page gets main URL #}
  <link rel="canonical" href="{{ canonical_url('/blog/') }}">
{% else %}
  {# Subsequent pages get their own URL #}
  <link rel="canonical" href="{{ canonical_url('/blog/page/' ~ page_num ~ '/') }}">
{% endif %}
```

### Why Canonical URLs Matter

```{success} SEO Benefits

**Prevents duplicate content issues:**
```
https://example.com/post/
https://example.com/post/index.html
https://www.example.com/post/
http://example.com/post/
```

All these URLs show the same content! Search engines might see them as duplicates and split ranking power.

**Solution:** Canonical URL tells search engines which URL is the "main" one:
```jinja2
<link rel="canonical" href="{{ canonical_url('/post/') }}">
```

Now all variations point to one canonical version!
```

### Common Scenarios

```{example} Canonical URL Use Cases

**1. HTTPS vs HTTP:**
```jinja2
{# Always use HTTPS in canonical #}
<link rel="canonical" href="{{ canonical_url(page.url) }}">
```

**2. WWW vs non-WWW:**
```jinja2
{# Config determines which is canonical #}
[site]
baseurl = "https://example.com"  # No www
```

**3. Pagination:**
```jinja2
{# Page 2+ points to page 1 OR to itself #}
{% if page_num > 1 %}
  <link rel="canonical" href="{{ canonical_url(base_path) }}">  {# To page 1 #}
  {# OR #}
  <link rel="canonical" href="{{ canonical_url(current_path) }}">  {# To self #}
{% endif %}
```

**4. AMP pages:**
```jinja2
{# AMP version points to canonical non-AMP #}
<link rel="canonical" href="{{ canonical_url(page.url) }}">
```

**5. Cross-posted content:**
```jinja2
{# Syndicated content points to original #}
<link rel="canonical" href="https://original-site.com/post/">
```
```

### Best Practices

```{tip} Canonical URL Rules

1. **Always use absolute URLs:**
   ```jinja2
   ✅ https://example.com/post/
   ❌ /post/
   ```

2. **Use your preferred domain:**
   ```jinja2
   ✅ https://example.com (if that's your preference)
   ❌ https://www.example.com (mixing both)
   ```

3. **Include trailing slash** (if your site uses them):
   ```jinja2
   ✅ /post/
   ❌ /post
   ```

4. **Match your actual URL structure:**
   ```jinja2
   ✅ {{ canonical_url(page.url) }}
   ❌ {{ canonical_url('/different-url/') }}
   ```

5. **Every page should have one:**
   ```jinja2
   {# In base template #}
   <link rel="canonical" href="{{ canonical_url(page.url) }}">
   ```
```

---

## 🖼️ og_image

Generate Open Graph image URL for social media sharing.

### Signature

```jinja2
{{ og_image(image_path) }}
```

### Parameters

- **image_path** (str): Relative path to image (from assets directory)

### Returns

Full absolute URL to image for Open Graph tags.

### Examples

#### Basic Usage

```jinja2
{# Use page hero image #}
{% if page.metadata.image %}
  <meta property="og:image" content="{{ og_image(page.metadata.image) }}">
{% endif %}
```

#### Complete Open Graph Tags

```jinja2
<head>
  {# Open Graph / Facebook #}
  <meta property="og:type" content="article">
  <meta property="og:title" content="{{ page.title }}">
  <meta property="og:description" content="{{/* page.content | meta_description */}}">
  <meta property="og:url" content="{{ canonical_url(page.url) }}">
  <meta property="og:image" content="{{ og_image(page.metadata.image or 'images/default-og.jpg') }}">
  <meta property="og:image:width" content="1200">
  <meta property="og:image:height" content="630">
  
  {# Twitter Card #}
  <meta name="twitter:card" content="summary_large_image">
  <meta name="twitter:title" content="{{ page.title }}">
  <meta name="twitter:description" content="{{/* page.content | meta_description */}}">
  <meta name="twitter:image" content="{{ og_image(page.metadata.image or 'images/default-og.jpg') }}">
</head>
```

#### Fallback to Default Image

```jinja2
{% set social_image = page.metadata.image or 'images/site-og-image.jpg' %}

<meta property="og:image" content="{{ og_image(social_image) }}">
<meta name="twitter:image" content="{{ og_image(social_image) }}">
```

### Image Requirements

```{note} Open Graph Image Specs

**Recommended:**
- **Size:** 1200 x 630 pixels (1.91:1 ratio)
- **Min:** 600 x 315 pixels
- **Max:** 5 MB file size
- **Format:** JPG or PNG

**Facebook:**
- Optimal: 1200 x 630 px
- Minimum: 200 x 200 px
- Shows at: ~500 x 261 px in feed

**Twitter:**
- Large card: 1200 x 628 px (1.91:1)
- Summary: 120 x 120 px (1:1) minimum

```jinja2
{# Specify dimensions #}
<meta property="og:image" content="{{ og_image('hero.jpg') }}">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta property="og:image:alt" content="{{ page.title }}">
```
```

### Social Media Preview

```{example} Complete Social Sharing Setup

```jinja2
{# _base.html template #}
<head>
  {# Basic meta #}
  <title>{{ page.title }} | {{ site.title }}</title>
  <meta name="description" content="{{/* page.content | meta_description */}}">
  <link rel="canonical" href="{{ canonical_url(page.url) }}">
  
  {# Open Graph (Facebook, LinkedIn) #}
  <meta property="og:site_name" content="{{ site.title }}">
  <meta property="og:type" content="article">
  <meta property="og:title" content="{{ page.title }}">
  <meta property="og:description" content="{{/* page.content | meta_description */}}">
  <meta property="og:url" content="{{ canonical_url(page.url) }}">
  
  {% set og_img = page.metadata.image or 'images/default-share.jpg' %}
  <meta property="og:image" content="{{ og_image(og_img) }}">
  <meta property="og:image:width" content="1200">
  <meta property="og:image:height" content="630">
  <meta property="og:image:alt" content="{{ page.title }}">
  
  {% if page.date %}
    <meta property="article:published_time" content="{{ page.date | iso_date }}">
  {% endif %}
  {% if page.metadata.author %}
    <meta property="article:author" content="{{ page.metadata.author }}">
  {% endif %}
  
  {# Twitter Card #}
  <meta name="twitter:card" content="summary_large_image">
  <meta name="twitter:site" content="@{{ site.twitter }}">
  <meta name="twitter:title" content="{{ page.title }}">
  <meta name="twitter:description" content="{{/* page.content | meta_description(200) */}}">
  <meta name="twitter:image" content="{{ og_image(og_img) }}">
  <meta name="twitter:image:alt" content="{{ page.title }}">
</head>
```

**Result:** Beautiful previews when shared on Facebook, Twitter, LinkedIn, Slack, Discord, etc.!
```

### Testing Social Tags

```{tip} Test Your Social Tags

**Facebook Sharing Debugger:**
https://developers.facebook.com/tools/debug/

**Twitter Card Validator:**
https://cards-dev.twitter.com/validator

**LinkedIn Post Inspector:**
https://www.linkedin.com/post-inspector/

**Test your URLs to see how they'll appear when shared!**

Common issues:
- Image not loading (check absolute URL)
- Image too small (< 200x200)
- Missing required tags (title, description, image)
- Cache issues (may take time to update)
```

---

## 🎯 Complete SEO Template

Here's a complete head section using all SEO functions:

```jinja2
{# templates/_head.html #}
<head>
  {# Character encoding #}
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  
  {# Title #}
  <title>{{ page.title }} | {{ site.title }}</title>
  
  {# Meta description #}
  {% set description = page.metadata.description or (page.content | meta_description(160)) %}
  <meta name="description" content="{{ description }}">
  
  {# Meta keywords (optional) #}
  {% if page.tags %}
    <meta name="keywords" content="{{ page.tags | meta_keywords(10) }}">
  {% endif %}
  
  {# Canonical URL #}
  <link rel="canonical" href="{{ canonical_url(page.url) }}">
  
  {# Open Graph #}
  <meta property="og:site_name" content="{{ site.title }}">
  <meta property="og:type" content="website">
  <meta property="og:title" content="{{ page.title }}">
  <meta property="og:description" content="{{ description }}">
  <meta property="og:url" content="{{ canonical_url(page.url) }}">
  
  {% set og_img = page.metadata.image or 'images/og-default.jpg' %}
  <meta property="og:image" content="{{ og_image(og_img) }}">
  <meta property="og:image:width" content="1200">
  <meta property="og:image:height" content="630">
  
  {# Twitter Card #}
  <meta name="twitter:card" content="summary_large_image">
  <meta name="twitter:title" content="{{ page.title }}">
  <meta name="twitter:description" content="{{ description }}">
  <meta name="twitter:image" content="{{ og_image(og_img) }}">
  
  {# Additional SEO #}
  <meta name="robots" content="index, follow">
  <link rel="alternate" type="application/rss+xml" title="{{ site.title }}" href="/rss.xml">
</head>
```

---

## 📊 SEO Checklist

Use this checklist to ensure every page is SEO-optimized:

```{tabs}
:id: seo-checklist

### Tab: Essential Meta Tags

- [ ] **Title tag** (50-60 characters)
  ```jinja2
  <title>{{ page.title | truncate_chars(60, '') }}</title>
  ```

- [ ] **Meta description** (150-160 characters)
  ```jinja2
  <meta name="description" content="{{/* page.content | meta_description(160) */}}">
  ```

- [ ] **Canonical URL**
  ```jinja2
  <link rel="canonical" href="{{ canonical_url(page.url) }}">
  ```

- [ ] **Viewport meta**
  ```jinja2
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  ```

### Tab: Social Sharing

- [ ] **Open Graph title**
  ```jinja2
  <meta property="og:title" content="{{ page.title }}">
  ```

- [ ] **Open Graph description**
  ```jinja2
  <meta property="og:description" content="{{/* page.content | meta_description */}}">
  ```

- [ ] **Open Graph image** (1200x630)
  ```jinja2
  <meta property="og:image" content="{{ og_image(page.image) }}">
  ```

- [ ] **Open Graph URL**
  ```jinja2
  <meta property="og:url" content="{{ canonical_url(page.url) }}">
  ```

- [ ] **Twitter Card tags**
  ```jinja2
  <meta name="twitter:card" content="summary_large_image">
  ```

### Tab: Content SEO

- [ ] **Unique H1 tag** (only one per page)
  ```jinja2
  <h1>{{ page.title }}</h1>
  ```

- [ ] **Structured headings** (H1 → H2 → H3)
- [ ] **Alt text for images**
  ```jinja2
  <img src="..." alt="{{ image.description }}">
  ```

- [ ] **Internal links**
- [ ] **External links** (with rel="nofollow" if needed)
- [ ] **Readable URLs** (use slugify)
  ```jinja2
  /blog/{{ page.title | slugify }}/
  ```

### Tab: Technical SEO

- [ ] **Sitemap.xml** (auto-generated by Bengal)
- [ ] **RSS feed** (auto-generated)
- [ ] **Robots.txt**
- [ ] **404 page**
- [ ] **Fast load time** (< 3 seconds)
- [ ] **Mobile responsive**
- [ ] **HTTPS**
- [ ] **No broken links** (use health checks!)
```

---

## 📚 Related Functions

- **[String Functions](strings.md)** - truncate_chars, slugify
- **[Content Functions](content.md)** - strip_html, safe_html
- **[URL Functions](urls.md)** - absolute_url, url_encode

---

## 💡 Best Practices

```{success} Quick SEO Wins

**1. Use descriptive titles:**
```jinja2
✅ <title>How to Build a Blog with Bengal SSG</title>
❌ <title>Blog Post</title>
```

**2. Write compelling descriptions:**
```jinja2
✅ Learn how to build a lightning-fast blog with Bengal SSG in under 10 minutes.
❌ This is a blog post about Bengal.
```

**3. Use high-quality images:**
```jinja2
✅ 1200x630 custom OG image
❌ Generic default image or no image
```

**4. Every page gets unique meta:**
```jinja2
✅ {{/* page.content | meta_description */}}  {# Unique per page #}
❌ {{ site.description }}  {# Same for all pages #}
```

**5. Test your changes:**
- Use Google Search Console
- Test with Facebook/Twitter validators
- Check mobile preview
- Monitor page speed
```

```{warning} Common SEO Mistakes

**❌ Don't:**
- Duplicate meta descriptions across pages
- Use same title for every page
- Forget image alt text
- Ignore mobile users
- Stuff keywords unnaturally
- Use automatic "Read more..." in descriptions

**✅ Do:**
- Unique content for every page
- Descriptive, keyword-rich titles
- Compelling meta descriptions
- High-quality images
- Fast, responsive design
- Natural, readable content
```

---

**Module:** `bengal.rendering.template_functions.seo`  
**Functions:** 4  
**Last Updated:** October 4, 2025  
**SEO Impact:** High - These functions directly affect search rankings and social sharing

