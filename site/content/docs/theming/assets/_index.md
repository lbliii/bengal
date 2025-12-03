---
title: Assets
description: CSS, JavaScript, images, and fonts
weight: 20
category: guide
icon: image
card_color: green
---

# Asset Pipeline

Bengal processes your CSS, JavaScript, images, and fonts with optional minification and fingerprinting.

## How Assets Flow

```mermaid
flowchart LR
    subgraph Sources
        A[static/]
        B[assets/]
        C[Theme assets]
        D[Page bundles]
    end
    
    subgraph Processing
        E[Collect]
        F[Minify]
        G[Fingerprint]
    end
    
    subgraph Output
        H[public/]
    end
    
    A --> E
    B --> E
    C --> E
    D --> E
    E --> F --> G --> H
```

## Asset Locations

| Location | Copied To | Processing | Use For |
|----------|-----------|------------|---------|
| `static/` | `public/` | None | Files that don't need processing |
| `assets/` | `public/` | Full pipeline | CSS/JS needing minification |
| Theme's `static/` | `public/` | None | Theme's static files |
| Page bundles | `public/` | Scope-limited | Page-specific images/data |

## Quick Reference

::::{tab-set}
:::{tab-item} Configuration
```toml
# bengal.toml
[build.assets]
minify_css = true
minify_js = true
fingerprint = true   # main.css → main.a1b2c3.css
```
:::

:::{tab-item} Template Usage
```jinja
{# Basic asset URL #}
<link rel="stylesheet" href="{{ 'css/main.css' | asset_url }}">

{# With fingerprint for cache-busting #}
<link rel="stylesheet" href="{{ 'css/main.css' | fingerprint }}">

{# Images #}
<img src="{{ 'images/logo.png' | asset_url }}" alt="Logo">
```
:::

:::{tab-item} Page Bundle Assets
```jinja
{# Access assets co-located with current page #}
{% for image in page.resources.match("*.jpg") %}
  <img src="{{ image.url }}" alt="{{ image.title }}">
{% endfor %}
```
:::
::::

:::{tip}
**Fingerprinting** adds a hash to filenames (`main.a1b2c3.css`) for cache-busting. Enable it in production for optimal caching.
:::
