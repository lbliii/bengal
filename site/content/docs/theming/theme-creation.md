---
title: Create a Theme
description: Build a custom Bengal theme from scaffold to deployment
weight: 50
icon: palette
tags:
- theming
- customization
- themes
keywords:
- bengal theme
- create theme
- custom theme
- theme development
---

# Create a Theme

Bengal's theme system supports inheritance, so you can build on the default theme and override only what you need. This guide walks through creating, customizing, and testing a theme.

## Scaffold a Theme

```bash
# Create a site-local theme (lives in your project)
bengal theme new --slug my-theme

# Create an installable package (publishable to PyPI)
bengal theme new --slug my-theme --mode package

# Extend a specific parent theme
bengal theme new --slug my-theme --extends default
```

Site mode creates this structure:

```
themes/my-theme/
├── theme.toml              # Name and inheritance
├── README.md
├── templates/
│   ├── base.html
│   ├── home.html
│   ├── page.html
│   └── partials/
├── assets/
│   └── css/
│       └── style.css       # Your styles (directive base CSS is automatic)
```

## Configure Your Site

Point your site config at the new theme:

```toml
# bengal.toml
[build]
theme = "my-theme"
```

Bengal resolves templates in priority order: your theme first, then its parent (via `extends`), then the default theme. You only need to override the templates you want to change.

## Override Templates

Copy a template from the active theme to customize it:

```bash
# See what's available
bengal theme discover

# Copy a specific template
bengal theme swizzle --template-path partials/header.html
```

Swizzled templates are tracked with checksums. When the parent theme updates, `bengal theme swizzle-update` refreshes unchanged templates while preserving your modifications.

### Template Inheritance

Your templates can extend parent templates:

```html
{# templates/page.html #}
{% extends "page.html" %}

{% block content %}
<article class="my-theme-content">
  {{ content | safe }}
</article>
{% endblock %}
```

Bengal resolves the `extends` to the parent theme's `page.html` automatically.

## Add Styles

Your `assets/css/style.css` is loaded after the parent theme's CSS, so your styles override naturally via the cascade.

Bengal automatically includes base CSS for all directives (tabs, dropdowns, admonitions, steps, cards, code blocks). Your theme only needs to provide aesthetic styles — functional show/hide, accessibility, and prose contamination fixes are handled.

```css
/* assets/css/style.css */

/* Override the primary color */
:root {
  --color-primary: #2563eb;
  --color-primary-light: #3b82f6;
}

/* Custom typography */
body {
  font-family: "Inter", system-ui, sans-serif;
  line-height: 1.7;
}

/* Style code blocks */
pre code {
  border-radius: 0.5rem;
  font-size: 0.875rem;
}
```

## Test Your Theme

```bash
# Start dev server with live reload
bengal serve

# Start theme-focused preview with active theme preflight
bengal theme preview

# Validate theme structure
bengal theme validate --theme-path themes/my-theme

# Debug template resolution
bengal theme debug
bengal theme debug --template page.html
```

`bengal theme preview` resolves the active theme, shows whether it came from
the site, Bengal's bundled themes, or an installed package, validates its
metadata and required templates, then starts the live-reload server. It also
prints the content, template, and theme paths the preview workflow watches.

## Theme Configuration

Your `theme.toml` declares theme metadata:

```toml
name = "my-theme"
version = "1.0.0"
description = "Documentation theme for the project"
author = "Docs Team"
license = "MIT"
extends = "default"
libraries = ["chirp_ui"]
```

Supported metadata fields:

| Field | Type | Purpose |
|---|---|---|
| `name` | string | Display name for `bengal theme list` and `bengal theme info` |
| `version` | string | Theme version shown by theme tooling |
| `description` | string | Human-readable package or project description |
| `author` | string | Theme author or owning team |
| `license` | string | Theme license identifier |
| `extends` | string | Parent theme slug |
| `parent` | string | Legacy parent theme slug, used when `extends` is absent |
| `libraries` | list of strings | Python theme libraries to load, such as `chirp_ui` |

`bengal theme validate --theme-path themes/my-theme` checks this metadata before
checking templates and assets, so malformed fields fail with direct messages.

For richer configuration (feature flags, appearance, icons), use `theme.yaml`:

```yaml
name: my-theme
version: "1.0.0"
parent: default

features:
  navigation:
    breadcrumbs: true
    toc: true
  content:
    code.copy: true
    lightbox: true
  search:
    suggest: true

appearance:
  default_mode: system
  default_palette: snow-lynx
```

## Publish as a Package

If you scaffolded with `--mode package`, your theme is a pip-installable Python package:

```bash
cd bengal-theme-my-theme
pip install -e .    # Install locally for testing
```

The `pyproject.toml` registers your theme via entry points:

```toml
[project.entry-points.'bengal.themes']
my-theme = "bengal_themes.my_theme"
```

Once installed, any Bengal site can use it:

```toml
# bengal.toml
[build]
theme = "my-theme"
```

Publish to PyPI with `uv publish` or `python -m build && twine upload dist/*`.

## Useful Commands

| Command | Purpose |
|---------|---------|
| `bengal theme new --slug <slug>` | Scaffold a new theme |
| `bengal theme validate --theme-path <path>` | Check required files and structure |
| `bengal theme list` | Show available themes |
| `bengal theme info --slug <slug>` | Theme details and paths |
| `bengal theme discover` | List swizzlable templates |
| `bengal theme swizzle --template-path <template>` | Copy template for customization |
| `bengal theme swizzle-list` | List swizzled templates |
| `bengal theme swizzle-update` | Update unchanged swizzled templates |
| `bengal theme preview` | Start a theme-focused live preview server |
| `bengal theme debug` | Debug theme resolution chain |

:::{seealso}
- [Theming Overview](/docs/theming/) — theme features and appearance config
- [The Bengal Ecosystem](/docs/about/ecosystem/) — how Kida templates work
:::
