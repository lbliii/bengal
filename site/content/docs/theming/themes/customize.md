---
title: Customize Themes
description: Customize existing themes without breaking updates
weight: 10
draft: false
lang: en
tags: [themes, customization, templates, css]
keywords: [themes, customization, templates, css, override]
category: guide
aliases:
  - /docs/guides/customizing-themes/
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

### Theme Not Found

**Issue:** `Theme 'my-theme' not found`

**Solutions:**
- Verify theme directory exists: `themes/my-theme/`
- Check `theme.yaml` has correct `name` field
- Run `bengal utils theme list` to see available themes

### Template Inheritance Not Working

**Issue:** Changes to parent theme not reflected

**Solutions:**
- Verify `extends` path is correct: `"default::base.html"`
- Check theme chain: `bengal utils theme debug`
- Clear cache: `bengal site clean --cache`

### CSS Not Loading

**Issue:** Custom CSS not applying

**Solutions:**
- Use `asset_url()` filter: `{{ asset_url('css/style.css') }}`
- Check file location: `themes/your-theme/static/css/`
- Hard refresh: `Cmd+Shift+R`

## See Also

- [Templating](/docs/theming/templating/) — Template basics
- [Assets](/docs/theming/assets/) — Asset pipeline
- [Variables Reference](/docs/theming/variables/) — Available template variables



