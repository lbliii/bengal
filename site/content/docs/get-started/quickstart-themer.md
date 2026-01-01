---
title: Themer Quickstart
nav_title: Themers
description: Customize themes and create your own designs
draft: false
weight: 30
lang: en
type: doc
tags:
- onboarding
- theming
- quickstart
keywords:
- theming
- templates
- css
- design
category: onboarding
id: themer-qs
icon: palette
---

# Themer Quickstart

Learn to customize Bengal themes and create your own designs.

## Prerequisites

:::{checklist}
:show-progress:
- [ ] [[docs/get-started/installation|Bengal installed]]
- [ ] Basic knowledge of HTML
- [ ] Familiarity with CSS
- [ ] Basic template syntax (Bengal uses Kida, similar to Jinja2 but with `{% end %}` closers)
:::{/checklist}

## Understand Theme Resolution

Bengal looks for templates in this order:

1. **Your project** — `templates/` (overrides everything)
2. **Your theme** — `themes/your-theme/templates/`
3. **Installed themes** — Via pip or uv
4. **Default theme** — Built into Bengal

You only need to override what you want to change.

## Create a Custom Theme

```bash
bengal new theme my-theme
```

This creates:

```tree
themes/my-theme/
├── templates/
│   ├── base.html
│   ├── home.html
│   ├── page.html
│   └── partials/
│       ├── header.html
│       └── footer.html
└── assets/
    ├── css/
    │   └── style.css
    ├── js/
    │   └── main.js
    └── images/
```

## Configure Your Theme

Update `bengal.toml`:

```toml
[theme]
name = "my-theme"
```

Or use `config/_default/theme.yaml` for split configuration:

```yaml
theme:
  name: "my-theme"
```

## Override Templates Selectively

You do not need to copy all templates. Extend the default:

```html
{# themes/my-theme/templates/base.html #}
{% extends "base.html" %}

{% block header %}
<header class="custom-header">
    <h1>{{ site.title }}</h1>
    {% for item in menus.main %}
    <a href="{{ item.href }}">{{ item.name }}</a>
    {% end %}
</header>
{% end %}
```

Everything not overridden inherits from the default theme or parent theme.

## Add Custom CSS

Create `themes/my-theme/assets/css/custom.css`:

```css
:root {
    --color-primary: #3498db;
    --color-text: #2c3e50;
}

.custom-header {
    background: var(--color-primary);
    padding: 2rem;
}
```

Include in your template:

```html
{% block extra_head %}
<link rel="stylesheet" href="{{ asset_url('css/custom.css') }}">
{% end %}
```

## Template Variables

Key variables available in templates (all support safe dot-notation access):

| Variable | Description |
|----------|-------------|
| `site.title` | Site title from configuration |
| `site.description` | Site description |
| `site.baseurl` | Site base URL |
| `site.pages` | All pages in the site |
| `menus.main` | Main navigation menu (safe access) |
| `page.title` | Current page title |
| `page.content` | Rendered HTML content (use with `\| safe`) |
| `page.href` | Page URL with baseurl applied |
| `page.date` | Publication date |
| `page.tags` | List of tags |
| `page.description` | Page description |
| `params` | Page frontmatter (cascades page → section → site) |
| `theme` | Theme configuration (safe dot-notation access) |
| `bengal` | Engine metadata |

Bengal provides 80+ template functions. Common ones:

- `asset_url('path')` — Generate asset URLs
- `url_for('path')` — Generate page URLs
- `get_menu('name')` — Get a navigation menu
- `time_ago` / `date_iso` — Format dates (`{{ page.date | time_ago }}`)
- `truncate_chars(text, length)` — Truncate text

## Debug Theme Issues

```bash
# List available themes
bengal utils theme list

# Get theme info
bengal utils theme info default

# Debug theme resolution
bengal utils theme debug

# Discover installed themes
bengal utils theme discover

# Swizzle a template for customization
bengal utils theme swizzle partials/header.html
```

## Next Steps

- **[[docs/theming/themes/customize|Theme Customization]]** — Deep dive into overrides
- **[[docs/theming/templating/functions|Template Functions]]** — All available filters and functions
- **[[docs/reference/theme-variables|Variables Reference]]** — Complete template variables
- **[[docs/theming/assets|Assets]]** — CSS, JS, and image handling
