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
```
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
```html
{# Extend default theme's base template #}
{% extends "default::base.html" %}

{# Override only the header block #}
{% block header %}
<header class="custom-header">
    <h1>{{ site.title }}</h1>
    <nav>
        {% for item in menu.main %}
        <a href="{{ item.url }}">{{ item.name }}</a>
        {% endfor %}
    </nav>
</header>
{% endblock %}

{# Everything else inherits from default theme #}
```

### Partial Overrides

Override specific partials:

**`themes/my-custom-theme/templates/partials/footer.html`:**
```html
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

```
templates/partials/
├── page-hero.html           # Dispatcher (routes by hero_style)
├── page-hero-api.html       # Legacy API hero (deprecated)
├── page-hero-editorial.html # Editorial-style hero
├── page-hero-overview.html  # Section overview hero
└── page-hero/               # Separated API hero templates
    ├── _share-dropdown.html # AI share dropdown component
    ├── _wrapper.html        # Shared wrapper (breadcrumbs + share)
    ├── _element-stats.html  # Element children stats
    ├── element.html         # DocElement pages (modules, classes, commands)
    └── section.html         # Section-index pages (packages, CLI groups)
```

### Override Page Hero for API Pages

To customize the hero for API documentation pages:

**For element pages (modules, classes, functions, commands):**

```html
{# themes/my-theme/templates/partials/page-hero/element.html #}
{% include 'partials/page-hero/_wrapper.html' %}

  {# Your custom badges #}
  <div class="page-hero__badges">
    {% include 'autodoc/python/partials/badges.html' %}
  </div>

  {# Custom title with code formatting #}
  <h1 class="page-hero__title page-hero__title--code">
    <code>{{ element.qualified_name }}</code>
  </h1>

  {# Your custom content here #}

</div>
```

**For section-index pages:**

```html
{# themes/my-theme/templates/partials/page-hero/section.html #}
{% set is_cli = (hero_context.is_cli if (hero_context is defined and hero_context and hero_context.is_cli is defined) else false) %}

{% include 'partials/page-hero/_wrapper.html' %}

  <h1 class="page-hero__title">{{ section.title }}</h1>

  {# Section description from metadata (dict access) #}
  {% set desc = section.metadata.get('description', '') %}
  {% if desc %}
  <div class="page-hero__description">
    {{ desc | markdownify | safe }}
  </div>
  {% endif %}

</div>
```

### Using hero_context

For CLI reference sections, pass explicit context to avoid URL sniffing:

```html
{# In autodoc/cli/section-index.html #}
{% set hero_context = {'is_cli': true} %}
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

**Section templates** receive a `Section` object—use dict-style access for metadata:
- `section.title` (attribute)
- `section.metadata.get('description', '')` (dict access)
- `section.sorted_pages` (attribute)
- `section.sorted_subsections` (attribute)

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
```html
{% extends "default::base.html" %}

{% block extra_head %}
<link rel="stylesheet" href="{{ asset_url('css/custom.css') }}">
{% endblock %}
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

Themes can expose configuration options:

**`themes/my-custom-theme/theme.yaml`:**
```yaml
name: my-custom-theme
version: 1.0.0
description: Customizable theme

params:
  show_author: true
  show_date: true
  sidebar_position: left
  color_scheme: light
```

Access in templates:

```html
{% if theme.config.params.show_author %}
<p>By {{ page.author or site.author }}</p>
{% endif %}
```

Configure in `bengal.toml`:

```toml
[theme]
name = "my-custom-theme"

[theme.params]
show_author = true
sidebar_position = "right"
color_scheme = "dark"
```

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
```html
{% extends "default::base.html" %}
{% block header %}
  {# Only override header #}
{% endblock %}
```

❌ **Bad:**
```html
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
- Check `theme.yaml` has correct `name` field
- Run `bengal utils theme list` to see available themes
:::

:::{dropdown} Template Inheritance Not Working
:icon: alert

**Issue:** Changes to parent theme not reflected

**Solutions:**
- Verify `extends` path is correct: `"default::base.html"`
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

:::{seealso}
- [Templating](/docs/theming/templating/) — Template basics
- [Assets](/docs/theming/assets/) — Asset pipeline
- [Icon Reference](/docs/reference/icons/) — SVG icons and customization
- [Variables Reference](/docs/theming/variables/) — Available template variables
:::
