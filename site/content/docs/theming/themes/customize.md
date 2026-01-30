---
title: Customize Themes
description: Customize existing themes without breaking updates
weight: 10
draft: false
lang: en
tags:
- themes
- customization
- templates
- css
keywords:
- themes
- customization
- templates
- css
- override
category: guide
---

# Customize Themes

Customize Bengal themes without breaking theme updates. Use theme inheritance, template overrides, and CSS customization techniques.

## Understand Theme Resolution

Bengal resolves themes in this order:

1. **Project themes** - `themes/your-theme/` (highest priority)
2. **Installed themes** - Installed via pip/uv
3. **Bundled themes** - Built into Bengal (e.g., `default`)

### Check Active Theme

```bash
# List available themes
bengal utils theme list

# Get theme info
bengal utils theme info default

# Debug theme resolution
bengal utils theme debug
```

## Create a Project Theme

### Option 1: Start from Scratch

```bash
bengal new theme my-custom-theme
```

This creates:
```tree
themes/my-custom-theme/
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

### Configure Your Theme

Edit `bengal.toml`:

```toml
[theme]
name = "my-custom-theme"
default_appearance = "light"
```

## Override Templates Selectively

### Template Inheritance

You don't need to copy all templates. Override only what you need:

**`themes/my-custom-theme/templates/base.html`:**
```kida
{# Extend default theme's base template #}
{% extends "default/base.html" %}

{# Override only the header block #}
{% block header %}
<header class="custom-header">
    <h1>{{ site.title }}</h1>
    <nav>
        {% for item in menu.main %}
        <a href="{{ item.href }}">{{ item.name }}</a>
        {% end %}
    </nav>
</header>
{% end %}

{# Everything else inherits from default theme #}
```

### Partial Overrides

Override specific partials:

**`themes/my-custom-theme/templates/partials/footer.html`:**
```kida
<footer class="custom-footer">
    <p>&copy; {{ site.author }} {{ "now" | date("%Y") }}</p>
    <p>Custom footer content</p>
</footer>
```

Bengal will use your partial instead of the theme's default.

## Page Hero Templates

The page hero templates display the header section of content pages including title, breadcrumbs, description, and stats.

### Template Structure

The `page-hero/` directory contains separated hero templates:

```tree
templates/partials/
├── page-hero.html           # Dispatcher (routes by hero_style)
└── page-hero/               # Separated hero templates
    ├── _macros.html         # Shared macros and helpers
    ├── index.html           # Index page hero template
    ├── element.html         # DocElement pages (modules, classes, commands)
    └── section.html         # Section-index pages (packages, CLI groups)
```

The dispatcher (`page-hero.html`) routes to the appropriate template based on page type and `hero_style` configuration.

### Override Page Hero for API Pages

To customize the hero for API documentation pages:

**For element pages (modules, classes, functions, commands):**

Override `partials/page-hero/element.html` to customize the hero for API documentation elements:

```kida
{# themes/my-theme/templates/partials/page-hero/element.html #}
{% from 'partials/page-hero/_macros.html' import hero_element %}

{# Use the macro with custom parameters #}
{{ hero_element(element, params, theme) }}

{# Or create a completely custom hero #}
<div class="page-hero">
  <div class="page-hero__badges">
    {% include 'autodoc/python/partials/badges.html' %}
  </div>
  <h1 class="page-hero__title page-hero__title--code">
    <code>{{ element.qualified_name }}</code>
  </h1>
  {% if element.description %}
  <div class="page-hero__description">
    {{ element.description | markdownify | safe }}
  </div>
  {% end %}
</div>
```

**For section-index pages:**

Override `partials/page-hero/section.html` to customize section index heroes:

```kida
{# themes/my-theme/templates/partials/page-hero/section.html #}
{% from 'partials/page-hero/_macros.html' import hero_section %}

{# Use the macro #}
{{ hero_section(section, params, theme) }}

{# Or create a custom section hero #}
<div class="page-hero">
  <h1 class="page-hero__title">{{ section.title }}</h1>
  {% let desc = section.metadata.description %}
  {% if desc %}
  <div class="page-hero__description">
    {{ desc | markdownify | safe }}
  </div>
  {% end %}
</div>
```

### Using hero_context

For CLI reference sections, pass explicit context to avoid URL sniffing:

```kida
{# In autodoc/cli/section-index.html #}
{% let hero_context = {'is_cli': true} %}
{% include 'partials/page-hero/section.html' %}
```

The `hero_context.is_cli` flag controls whether stats display:
- `true`: "X Groups, Y Commands"
- `false`: "X Packages, Y Modules"

### Template Data Access Patterns

**Element templates** receive a `DocElement` dataclass—use attribute access:
- `element.qualified_name`
- `element.description`
- `element.children`
- `element.source_file`

**Section templates** receive a `Section` object—use attribute access:
- `section.title` (section title)
- `section.metadata.description` (safe access, returns empty string if missing)
- `section.sorted_pages` (sorted child pages)
- `section.sorted_subsections` (sorted child sections)

## Customize CSS

### Method 1: Override Theme CSS

Create your own CSS file that overrides theme styles:

**`themes/my-custom-theme/static/css/custom.css`:**
```css
/* Override theme colors */
:root {
    --color-primary: #3498db;
    --color-text: #2c3e50;
}

/* Custom styles */
.custom-header {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    padding: 2rem;
}
```

Include in your base template:

**`themes/my-custom-theme/templates/base.html`:**
```kida
{% extends "default/base.html" %}

{% block extra_head %}
<link rel="stylesheet" href="{{ asset_url('css/custom.css') }}">
{% end %}
```

### Method 2: Use CSS Variables

Many themes support CSS variables. Override them:

**`themes/my-custom-theme/static/css/overrides.css`:**
```css
:root {
    /* Override default theme variables */
    --theme-primary: #3498db;
    --theme-secondary: #2ecc71;
    --theme-font-sans: 'Inter', sans-serif;
}
```

## Theme Configuration Options

Themes can expose configuration options in two ways:

### Theme-Level Configuration (`theme.yaml`)

Define default configuration in your theme's `theme.yaml` file:

**`themes/my-custom-theme/theme.yaml`:**
```yaml
name: my-custom-theme
version: 1.0.0

# Custom configuration options
show_author: true
show_date: true
sidebar_position: left
color_scheme: light
```

### Site-Level Overrides (`bengal.toml`)

Override theme defaults in your site's `bengal.toml`:

```toml
[theme]
name = "my-custom-theme"

# Override theme config values
show_author = true
sidebar_position = "right"
color_scheme = "dark"
```

### Accessing Configuration in Templates

Access theme configuration using `theme.get()` or direct property access:

```kida
{# Using theme.get() method (recommended) #}
{% if theme.get('show_author', false) %}
<p>By {{ page.author or site.author }}</p>
{% end %}

{# Direct config key access #}
{% if theme.config.show_author %}
<p>By {{ page.author or site.author }}</p>
{% end %}
```

**Note**: All keys in the `[theme]` section are accessible via `theme.get('key')` (with default) or `theme.config.key` (direct access).

## Best Practices

### Don't Modify Installed Themes

❌ **Bad:**
```bash
# Don't edit installed theme directly
vim $(python -m site --user-site)/bengal/themes/default/templates/base.html
```

✅ **Good:**
```bash
# Create project theme that extends default
bengal new theme my-theme
# Override only what you need
```

### Use Theme Inheritance

✅ **Good:**
```kida
{% extends "default/base.html" %}
{% block header %}
  {# Only override header #}
{% end %}
```

❌ **Bad:**
```kida
{# Copying entire base.html #}
<!DOCTYPE html>
<html>
  {# ... hundreds of lines ... #}
</html>
```

## Troubleshooting

:::{dropdown} Theme Not Found
:icon: alert

**Issue:** `Theme 'my-theme' not found`

**Solutions:**
- Verify theme directory exists: `themes/my-theme/`
- Check `theme.toml` has correct `name` field
- Run `bengal utils theme list` to see available themes
:::

:::{dropdown} Template Inheritance Not Working
:icon: alert

**Issue:** Changes to parent theme not reflected

**Solutions:**
- Verify `extends` path is correct: `"default/base.html"`
- Check theme chain: `bengal utils theme debug`
- Clear cache: `bengal clean --cache`
:::

:::{dropdown} CSS Not Loading
:icon: alert

**Issue:** Custom CSS not applying

**Solutions:**
- Use `asset_url()` filter: `{{ asset_url('css/style.css') }}`
- Check file location: `themes/your-theme/static/css/`
- Hard refresh: `Cmd+Shift+R`
:::

## Navigation with NavTree

Bengal provides a pre-computed navigation tree for efficient template rendering. Use `get_nav_tree(page)` to access the navigation structure.

### Basic Usage

```kida
<nav class="sidebar">
  {% for item in get_nav_tree(page) %}
    <a href="{{ item.href }}"
       {% if item.is_current %}class="active"{% end %}
       {% if item.is_in_trail %}class="in-trail"{% end %}>
      {{ item.title }}
    </a>

    {% if item.has_children %}
      <ul>
        {% for child in item.children %}
          <li>
            <a href="{{ child.href }}">{{ child.title }}</a>
          </li>
        {% endfor %}
      </ul>
    {% end %}
  {% endfor %}
</nav>
```

### NavNode Properties

Each navigation node provides:

| Property | Type | Description |
|----------|------|-------------|
| `item.title` | `str` | Display title |
| `item.href` | `str` | Page URL with baseurl applied |
| `item._path` | `str` | Site-relative URL without baseurl |
| `item.icon` | `str \| None` | Icon identifier |
| `item.weight` | `int` | Sort weight |
| `item.children` | `list[NavNode]` | Child navigation items |
| `item.is_current` | `bool` | True if this is the current page |
| `item.is_in_trail` | `bool` | True if in active trail to current page |
| `item.is_expanded` | `bool` | True if node should be expanded |
| `item.has_children` | `bool` | True if node has children |
| `item.depth` | `int` | Nesting level (0 = top level) |

### Scoped Navigation

For section-specific navigation (e.g., docs-only sidebar):

```kida
{% let root = page._section.root if page._section else none %}
{% for item in get_nav_tree(page, root_section=root) %}
  <a href="{{ item.href }}">{{ item.title }}</a>
{% endfor %}
```

### Benefits

- **Performance**: O(1) lookup via cached structure (<1ms render overhead)
- **Simplicity**: Single function call replaces version-filtering boilerplate
- **Consistency**: Pre-computed structure ensures consistent navigation across pages
- **Version-aware**: Automatic version filtering and shared content injection

:::{seealso}
- [Templating](/docs/theming/templating/) — Template basics
- [Assets](/docs/theming/assets/) — Asset pipeline
- [Icon Reference](/docs/reference/icons/) — SVG icons and customization
- [Variables Reference](/docs/reference/theme-variables/) — Available template variables
:::
