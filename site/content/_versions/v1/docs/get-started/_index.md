---
title: Get Started (v1)
description: Install Bengal v1.0 and create your first site
weight: 10
type: doc
icon: arrow-clockwise
cascade:
  type: doc
---

# Get Started with Bengal v1.0

:::{deprecated} v2.0
This installation guide is for Bengal v1.0. The v2.0 installation process has changed—see the [latest get started guide](/docs/get-started/).
:::

## Install

```bash
pip install bengal==1.0.0
```

Requires Python 3.11+.

## Create a Site

```bash
bengal init mysite
cd mysite
bengal serve
```

Your site runs at `localhost:8000`.

## Basic Structure

```
mysite/
├── bengal.yaml      # Site configuration
├── content/         # Markdown content
│   └── _index.md
├── templates/       # Jinja2 templates
└── static/          # Static assets
```

## Next Steps

- Read the [content guide](../content/) for writing pages
- Check out [theming](../theming/) for customization
