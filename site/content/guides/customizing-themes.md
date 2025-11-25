---
title: Customizing Themes
description: Learn how to customize existing themes without breaking updates, override templates, and extend theme functionality
weight: 30
type: doc
draft: false
lang: en
tags: [themes, customization, templates, css, design]
keywords: [themes, customization, templates, css, override, swizzling]
category: guide
---

# Customizing Themes

This guide shows you how to customize Bengal themes without breaking theme updates. Learn theme inheritance, template overrides, and CSS customization techniques.

## When to Use This Guide

```{checklist}
- You want to modify an existing theme's appearance
- You need to override specific templates
- You want to add custom CSS without editing theme files
- You're creating a child theme based on an existing theme
- You need to customize theme behavior
```

## Prerequisites

- [Bengal installed](/getting-started/installation/)
- [Themer Quickstart](/getting-started/themer-quickstart/) completed
- Basic knowledge of HTML, CSS, and Jinja2 templates
- A Bengal site with a theme installed

## Step 1: Understand Theme Resolution

Bengal resolves themes in this order:

```{checklist} Theme Resolution Priority
- **Project themes** - `themes/your-theme/` (highest priority)
- **Installed themes** - Installed via pip/uv
- **Bundled themes** - Built into Bengal (e.g., `default`)
```

### Check Active Theme

```bash
# List available themes
bengal utils theme list

# Get theme info
bengal utils theme info default

# Debug theme resolution
bengal utils theme debug
```

### Theme Debug Output

```bash
$ bengal utils theme debug

Active Theme Chain:
  → my-custom-theme (project)
    → default (bundled)

Template Resolution Paths:
  1. themes/my-custom-theme/templates/
  2. bengal/themes/default/templates/

Template Sources:
  base.html → themes/my-custom-theme/templates/base.html
  page.html → bengal/themes/default/templates/page.html
```

## Step 2: Create a Project Theme

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

### Option 2: Copy and Customize

```bash
# Copy default theme structure
mkdir -p themes/my-custom-theme
cp -r bengal/themes/default/templates themes/my-custom-theme/
cp -r bengal/themes/default/static themes/my-custom-theme/static

# Create theme.yaml
cat > themes/my-custom-theme/theme.yaml << EOF
name: my-custom-theme
version: 1.0.0
description: My custom theme based on default
EOF
```

### Configure Your Theme

Edit `bengal.toml`:

```toml
[theme]
name = "my-custom-theme"
default_appearance = "light"
default_palette = ""
```

## Step 3: Override Templates Selectively

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

## Step 4: Customize CSS

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
    --theme-spacing: 1.5rem;
}
```

### Method 3: Site-Level CSS

Add CSS at the site level (not in theme):

**`assets/css/site.css`:**
```css
/* Site-specific styles */
.site-header {
    border-bottom: 2px solid #3498db;
}
```

Reference in templates or config.

## Step 5: Customize JavaScript

### Add Custom Scripts

**`themes/my-custom-theme/static/js/custom.js`:**
```javascript
// Custom theme functionality
document.addEventListener('DOMContentLoaded', () => {
    // Theme switcher
    const themeToggle = document.getElementById('theme-toggle');
    if (themeToggle) {
        themeToggle.addEventListener('click', () => {
            document.body.classList.toggle('dark-mode');
            localStorage.setItem('theme',
                document.body.classList.contains('dark-mode') ? 'dark' : 'light'
            );
        });
    }

    // Restore saved theme
    const savedTheme = localStorage.getItem('theme');
    if (savedTheme) {
        document.body.classList.add(savedTheme + '-mode');
    }
});
```

Include in template:

```html
{% block extra_scripts %}
<script src="{{ asset_url('js/custom.js') }}"></script>
{% endblock %}
```

## Step 6: Custom Template Functions

### Create Custom Filters

**`themes/my-custom-theme/filters.py`:**
```python
def truncate_words(text, count=50):
    """Truncate text to a word count."""
    words = text.split()
    if len(words) <= count:
        return text
    return ' '.join(words[:count]) + '...'

def format_date_relative(date):
    """Format date as relative time (e.g., '2 days ago')."""
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc)
    if isinstance(date, str):
        date = datetime.fromisoformat(date.replace('Z', '+00:00'))
    delta = now - date
    # Implementation here...
    return f"{delta.days} days ago"

# Bengal auto-discovers FILTERS dict
FILTERS = {
    'truncate_words': truncate_words,
    'relative_date': format_date_relative,
}
```

Use in templates:

```html
<p>{{ page.content | striptags | truncate_words(30) }}</p>
<p>Published {{ page.date | relative_date }}</p>
```

## Step 7: Theme Configuration Options

### Add Theme Parameters

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
show_date = true
sidebar_position = "right"
color_scheme = "dark"
```

## Step 8: Debug Theme Issues

### Common Debugging Commands

```bash
# Check theme resolution
bengal utils theme debug

# Debug specific template
bengal utils theme debug --template page.html

# List all available templates
bengal utils theme discover

# Check asset paths
bengal utils assets list
```

### Template Not Found

If a template isn't loading:

1. **Check template exists:**
   ```bash
   bengal utils theme debug --template your-template.html
   ```

2. **Verify theme is active:**
   ```bash
   bengal utils theme info
   ```

3. **Check template inheritance:**
   ```html
   {# Verify extends path is correct #}
   {% extends "default::base.html" %}
   ```

### Styles Not Applying

1. **Check asset paths:**
   ```html
   {# Use asset_url filter #}
   <link rel="stylesheet" href="{{ asset_url('css/style.css') }}">
   ```

2. **Verify CSS file location:**
   ```bash
   # Should be in themes/your-theme/static/css/
   ls themes/your-theme/static/css/
   ```

3. **Check asset manifest:**
   ```bash
   bengal utils assets list
   ```

4. **Hard refresh browser:**
   - `Cmd+Shift+R` (Mac) or `Ctrl+Shift+R` (Windows)

## Step 9: Best Practices

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

### Organize Custom Assets

```
themes/my-theme/
├── static/
│   ├── css/
│   │   ├── theme.css      # Theme base styles
│   │   └── custom.css     # Your overrides
│   └── js/
│       └── custom.js      # Custom functionality
```

### Version Control

Include your custom theme in git:

```bash
# .gitignore
# Don't ignore your custom theme
!themes/my-custom-theme/
```

## Troubleshooting

### Theme Not Found

**Issue:** `Theme 'my-theme' not found`

**Solutions:**
- Verify theme directory exists: `themes/my-theme/`
- Check `theme.yaml` has correct `name` field
- Run `bengal utils theme list` to see available themes
- Check `bengal.toml` theme name matches directory name

### Template Inheritance Not Working

**Issue:** Changes to parent theme not reflected

**Solutions:**
- Verify `extends` path is correct: `"default::base.html"`
- Check theme chain: `bengal utils theme debug`
- Ensure parent theme is accessible
- Clear cache: `bengal site clean --cache`

### CSS Not Loading

**Issue:** Custom CSS not applying

**Solutions:**
- Use `asset_url()` filter: `{{ asset_url('css/style.css') }}`
- Check file location: `themes/your-theme/static/css/`
- Verify file is included in template
- Check browser console for 404 errors
- Hard refresh: `Cmd+Shift+R`

## Next Steps

- **[Themer Quickstart](/getting-started/themer-quickstart/)** - Learn theme basics
- **[Rendering System](/architecture/rendering/)** - Understand template rendering
- **[Asset Pipeline](/about/concepts/assets/)** - Optimize CSS and JavaScript
