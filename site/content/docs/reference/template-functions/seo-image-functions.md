---
title: SEO, Image & Theme Functions
description: SEO meta tags, image manipulation, icons, and theme features
weight: 100
tags:
- reference
- functions
- filters
- seo
- images
- icons
category: reference
---

# SEO Functions

Functions for generating SEO-friendly meta tags.

## meta_description

Generate meta description from text. Strips HTML, truncates to length, ends at sentence boundary.

```kida
<meta name="description" content="{{ page.content | meta_description }}">
<meta name="description" content="{{ page.content | meta_description(200) }}">
```

## meta_keywords

Generate meta keywords from tags list.

```kida
<meta name="keywords" content="{{ page.tags | meta_keywords }}">
<meta name="keywords" content="{{ page.tags | meta_keywords(5) }}">  {# Max 5 #}
```

## canonical_url

Generate canonical URL. For versioned docs, always points to latest version.

```kida
<link rel="canonical" href="{{ canonical_url(page.href, page=page) }}">
```

## og_image

Generate Open Graph image URL. Supports manual image, auto-generated social cards, or fallback.

```kida
<meta property="og:image" content="{{ og_image(page.metadata.get('image', ''), page) }}">
```

## get_social_card_url

Get URL to generated social card for a page (if social cards are enabled).

```kida
{% let card = get_social_card_url(page) %}
{% if card %}
  <meta property="og:image" content="{{ card }}">
{% end %}
```

---

# Image Functions

Functions for working with images in templates.

## image_url

Generate image URL with optional sizing parameters.

```kida
{{ image_url('photos/hero.jpg') }}
{{ image_url('photos/hero.jpg', width=800) }}
{{ image_url('photos/hero.jpg', width=800, height=600, quality=85) }}
```

## image_dimensions

Get image dimensions (requires Pillow).

```kida
{% let dims = image_dimensions('photo.jpg') %}
{% if dims %}
  {% let width, height = dims %}
  <img width="{{ width }}" height="{{ height }}" src="..." alt="...">
{% end %}
```

## image_srcset

Generate srcset attribute for responsive images.

```kida
<img srcset="{{ 'hero.jpg' | image_srcset([400, 800, 1200]) }}" />
{# hero.jpg?w=400 400w, hero.jpg?w=800 800w, hero.jpg?w=1200 1200w #}
```

## image_srcset_gen

Generate srcset with default sizes (400, 800, 1200, 1600).

```kida
<img srcset="{{ image_srcset_gen('hero.jpg') }}" />
```

## image_alt

Generate alt text from filename.

```kida
{{ 'mountain-sunset.jpg' | image_alt }}
{# "Mountain Sunset" #}
```

## image_data_uri

Convert image to data URI for inline embedding.

```kida
<img src="{{ image_data_uri('icons/logo.svg') }}" alt="Logo">
```

---

# Icon Function

Render SVG icons in templates.

## icon

Render an SVG icon. Uses theme-aware icon resolution with caching.

```kida
{{ icon("search") }}
{{ icon("search", size=20) }}
{{ icon("menu", size=24, css_class="nav-icon") }}
{{ icon("arrow-up", size=18, aria_label="Back to top") }}
```

**Parameters:**
- `name`: Icon name (e.g., "search", "menu", "close", "arrow-up")
- `size`: Icon size in pixels (default: 24)
- `css_class`: Additional CSS classes
- `aria_label`: Accessibility label (if empty, uses aria-hidden)

**Alias:** `render_icon` is an alias for `icon`.

---

# Theme Functions

Functions for accessing theme configuration.

## feature_enabled

Check if a theme feature is enabled.

```kida
{% if 'navigation.toc' | feature_enabled %}
  {# Render table of contents #}
{% end %}

{% if feature_enabled('search.enabled') %}
  {# Render search box #}
{% end %}
```
