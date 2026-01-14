---
title: Image Processing
nav_title: Images
description: Resize, crop, and optimize images in templates
weight: 35
category: how-to
icon: image
tags:
- images
- assets
- responsive
---
# Image Processing

Bengal provides image processing functions for resizing, cropping, format conversion, and responsive image generation.

## Quick Start

```kida
{# Get an image resource #}
{% let hero = page.resources.get("hero.jpg") %}

{# Resize and crop to exact dimensions #}
{% let processed = hero.fill("800x600 webp q80") %}
<img src="{{ processed.rel_permalink }}" 
     width="{{ processed.width }}" 
     height="{{ processed.height }}">
```

## Image Resources

Access images through page resources or the site's asset system:

```kida
{# From page bundle (co-located with content) #}
{% let img = page.resources.get("diagram.png") %}

{# From assets directory #}
{% let logo = site.resources.get("images/logo.png") %}
```

## Processing Methods

### fill — Crop to Exact Dimensions

Resizes and crops to fill the exact dimensions, maintaining aspect ratio:

```kida
{% let cropped = image.fill("800x600") %}
{% let cropped_webp = image.fill("800x600 webp q80 center") %}
```

**Spec format:** `WIDTHxHEIGHT [format] [quality] [anchor]`

### fit — Fit Within Dimensions

Resizes to fit within the box without cropping:

```kida
{% let thumb = image.fit("400x400") %}
{% let thumb_avif = image.fit("400x400 avif q85") %}
```

### resize — Resize by Width or Height

Resize by one dimension, auto-calculating the other:

```kida
{# Width only - height calculated automatically #}
{% let wide = image.resize("800x") %}

{# Height only - width calculated automatically #}
{% let tall = image.resize("x600") %}
```

## Spec String Options

| Component | Example | Description |
|-----------|---------|-------------|
| Dimensions | `800x600`, `800x`, `x600` | Width×Height (either can be omitted) |
| Format | `webp`, `avif`, `jpeg`, `png` | Output format |
| Quality | `q80`, `q95` | JPEG/WebP quality (0-100) |
| Anchor | `center`, `top`, `smart` | Crop anchor point |

### Anchor Points

For `fill` operations, the anchor determines which part of the image to keep:

| Anchor | Description |
|--------|-------------|
| `center` | Center of image (default) |
| `top`, `bottom`, `left`, `right` | Edge anchors |
| `topleft`, `topright`, `bottomleft`, `bottomright` | Corner anchors |
| `smart` | Face detection (requires smartcrop) |

## Responsive Images

### srcset Generation

Generate `srcset` attributes for responsive images:

```kida
<img src="{{ image_url('hero.jpg', width=800) }}"
     srcset="{{ 'hero.jpg' | image_srcset([400, 800, 1200, 1600]) }}"
     sizes="(max-width: 640px) 400px, (max-width: 1024px) 800px, 1200px"
     alt="Hero image">
```

### Default Sizes

Use `image_srcset_gen` for common breakpoints:

```kida
{# Uses default sizes: 400, 800, 1200, 1600 #}
<img srcset="{{ image_srcset_gen('hero.jpg') }}" 
     sizes="100vw">
```

### Responsive Image Macro

The default theme includes a responsive image macro:

```kida
{{ responsive_image(
    'hero.jpg', 
    alt='Hero image',
    sizes='(max-width: 768px) 100vw, 50vw',
    widths=[320, 640, 1024, 1280],
    loading='lazy'
) }}
```

## Format Conversion

Convert images to modern formats for smaller file sizes:

```kida
{# Convert to WebP (typically 25-35% smaller than JPEG) #}
{% let webp = image.fill("800x600 webp q80") %}

{# Convert to AVIF (typically 50% smaller than JPEG) #}
{% let avif = image.fill("800x600 avif q80") %}
```

:::{note}
AVIF support requires `pillow-avif-plugin`. Install with: `pip install pillow-avif-plugin`
:::

## Caching

Processed images are cached in `.bengal/image-cache/`. The cache key includes:
- Source file path and modification time
- Processing operation and parameters

Subsequent builds skip processing for unchanged images.

## Template Functions Reference

| Function | Description | Example |
|----------|-------------|---------|
| `image_url(path, width, height, quality)` | Generate image URL with params | `{{ image_url('logo.png', width=200) }}` |
| `image_srcset(path, sizes)` | Generate srcset attribute | `{{ 'hero.jpg' \| image_srcset([400, 800]) }}` |
| `image_srcset_gen(path)` | srcset with default sizes | `{{ image_srcset_gen('hero.jpg') }}` |
| `image_dimensions(path)` | Get (width, height) tuple | `{% let dims = image_dimensions('photo.jpg') %}` |
| `image_alt(filename)` | Generate alt text from filename | `{{ 'my-photo.jpg' \| image_alt }}` → "My photo" |
| `image_data_uri(path)` | Inline image as data URI | `{{ image_data_uri('icon.svg') }}` |

## Complete Example

```kida
{# Article card with responsive hero image #}
{% let hero = page.resources.get("hero.jpg") %}
{% if hero %}
  {% let processed = hero.fill("1200x630 webp q85") %}
  <article class="card">
    <img 
      src="{{ processed.rel_permalink }}"
      srcset="{{ hero.source_path | image_srcset([400, 800, 1200]) }}"
      sizes="(max-width: 640px) 100vw, (max-width: 1024px) 50vw, 1200px"
      width="{{ processed.width }}"
      height="{{ processed.height }}"
      alt="{{ page.title }}"
      loading="lazy"
    >
    <h2>{{ page.title }}</h2>
  </article>
{% end %}
```

## Requirements

Image processing requires Pillow:

```bash
pip install bengal[images]
# Or: pip install Pillow
```

Optional dependencies:
- `smartcrop-py`: Smart cropping with face detection
- `pillow-avif-plugin`: AVIF format support

:::{seealso}
- [[docs/content/authoring/images-media|Images & Media]] — Markdown syntax for images
- [[docs/reference/template-functions/images|Image Functions Reference]] — Complete function reference
:::
