---
title: Themes
description: Using and creating Bengal themes
weight: 30
draft: false
lang: en
tags: [themes, customization]
keywords: [themes, customization, create, override]
category: guide
---

# Themes

Using existing themes, customizing them, and creating your own.

## Overview

Bengal themes are complete design packages containing:

- **Layouts** — HTML templates
- **Assets** — CSS, JavaScript, images
- **Partials** — Reusable components
- **Configuration** — Theme-specific settings

## Using a Theme

Set your theme in configuration:

```toml
# bengal.toml
[theme]
name = "default"
```

## Theme Resolution

Bengal layers themes, allowing overrides:

```
your-project/layouts/     # Highest priority
your-project/themes/my-theme/layouts/
bengal/themes/default/layouts/  # Lowest priority
```

Any file you create in `layouts/` overrides the theme's version.

## Customizing Without Forking

Override specific files without modifying the theme:

```
your-project/
├── layouts/
│   └── partials/
│       └── header.html    # Overrides theme's header
└── static/
    └── css/
        └── custom.css     # Additional styles
```

## In This Section

- **[Customize](/docs/theming/themes/customize/)** — Override themes without forking
- **[Create](/docs/theming/themes/create/)** — Build a theme from scratch


