---
title: Assets
description: CSS, JavaScript, images, and fonts
weight: 20
draft: false
lang: en
tags: [assets, css, javascript, images]
keywords: [assets, css, javascript, images, fonts, pipeline]
category: guide
---

# Assets

The asset pipeline — handling stylesheets, JavaScript, images, and fonts.

## Overview

Bengal's asset pipeline provides:

- **Multiple sources** — Project assets, theme assets, and page bundles
- **Processing** — Minification, fingerprinting, optimization
- **Template access** — Easy asset URLs in templates

## Asset Locations

| Location | Purpose |
|----------|---------|
| `static/` | Project-wide static files |
| `assets/` | Processed assets (CSS, JS) |
| Theme's `static/` | Theme static files |
| Page bundles | Page-specific assets |

## Asset Processing

```toml
# bengal.toml
[build.assets]
minify_css = true
minify_js = true
fingerprint = true
```

## Using Assets in Templates

```jinja
{# Static assets #}
<link rel="stylesheet" href="{{ 'css/main.css' | asset_url }}">
<script src="{{ 'js/app.js' | asset_url }}"></script>

{# With fingerprinting #}
<link rel="stylesheet" href="{{ 'css/main.css' | fingerprint }}">
```

## In This Section

- **[Stylesheets](/docs/theming/assets/stylesheets/)** — CSS handling and processing
- **[JavaScript](/docs/theming/assets/javascript/)** — JS bundling and optimization
- **[Images](/docs/theming/assets/images/)** — Image optimization and responsive images
- **[Fonts](/docs/theming/assets/fonts/)** — Custom font integration


