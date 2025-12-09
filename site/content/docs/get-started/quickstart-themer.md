---
title: Themer Quickstart
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

- [Bengal installed](/docs/get-started/installation/)
- Basic knowledge of HTML, CSS, and Jinja2

## Understand Theme Resolution

Bengal looks for templates in this order:

1. **Your project** — `templates/` (overrides everything)
2. **Your theme** — `themes/your-theme/templates/`
3. **Installed themes** — Via pip/uv
4. **Default theme** — Built into Bengal

You only need to override what you want to change.

## Create a Custom Theme

```bash
bengal new theme my-theme
```

This creates:

```
themes/my-theme/
├── theme.yaml
├── templates/
│   ├── base.html
│   ├── page.html
│   └── partials/
│       ├── header.html
│       └── footer.html
└── static/
    ├── css/
    │   └── style.css
    └── js/
        └── main.js
```

## Configure Your Theme

Edit `config/_default/theme.yaml`:

```yaml
theme:
  name: "my-theme"
```

## Override Templates Selectively

You don't need to copy all templates. Extend the default:

```html
{# themes/my-theme/templates/base.html #}
{# Extend the base template if you want to reuse structure #}
{% extends "base.html" %}

{% block header %}
<header class="custom-header">
    <h1>{{ site.title }}</h1>
    {% for item in menu.main %}
    <a href="{{ item.url }}">{{ item.name }}</a>
    {% endfor %}
</header>
{% endblock %}
```

Everything not overridden inherits from the default theme (or parent theme).

## Add Custom CSS

Create `themes/my-theme/static/css/custom.css`:

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
{% endblock %}
```

## Template Variables

Key variables available in templates:

| Variable | Description |
|----------|-------------|
| `site.title` | Site title |
| `site.pages` | All pages |
| `page.title` | Current page title |
| `page.content` | Raw content |
| `page.rendered_html` | Rendered HTML |
| `page.url` | Page URL |
| `menu.main` | Main navigation menu |

## Debug Theme Issues

```bash
# Check theme resolution
bengal utils theme debug

# List available themes
bengal utils theme list

# Get theme info
bengal utils theme info default
```

## Next Steps

- **[Theme Customization](/docs/theming/themes/customize/)** — Deep dive into overrides
- **[Template Functions](/docs/theming/templating/functions/)** — Available filters
- **[Variables Reference](/docs/theming/variables/)** — All template variables
- **[Assets](/docs/theming/assets/)** — CSS, JS, and image handling
