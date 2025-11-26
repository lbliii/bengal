---
title: Create Themes
description: Create and customize themes
weight: 50
type: doc
draft: false
lang: en
tags: [onboarding, theming, quickstart]
keywords: [themes, templates, customization, design]
category: onboarding
---

# Themer Quickstart

Create custom themes, override templates, and build branded experiences. This guide is for designers and developers who want to customize Bengal's appearance.

## Prerequisites

- [Bengal installed](/docs/getting-started/installation/)
- Basic knowledge of HTML/CSS
- Familiarity with Jinja2 templates (helpful but not required)

## 1. Understand the Theme System

Bengal supports three types of themes:

- **Project themes** - Located in your site's `themes/` directory
- **Installed themes** - Installed via pip/uv (e.g., `bengal-theme-mybrand`)
- **Bundled themes** - Built into Bengal (e.g., `default`)

Themes are resolved in this order: project → installed → bundled.

### See Available Themes

```bash
bengal utils theme list
```

### Get Theme Info

```bash
bengal utils theme info default
```

## 2. Create a Test Site

Start with a blank site for theme development:

```bash
bengal new site theme-test
cd theme-test
```

Choose **Blank** from the wizard (no preset content to distract you).

## 3. Explore the Default Theme

Before creating your own, see what templates are available:

```bash
bengal utils theme discover
```

This shows all templates and partials you can override (called "swizzling").

## 4. Create Your Theme

### Option A: Site-Local Theme

Perfect for one-off customizations:

```bash
bengal new theme mybrand
```

This creates `themes/mybrand/` with starter files:

```
themes/mybrand/
├── theme.yaml           # Theme metadata
├── templates/
│   ├── base.html       # Base layout
│   ├── page.html       # Page template
│   ├── post.html       # Post template
│   └── partials/
│       ├── header.html
│       ├── footer.html
│       └── nav.html
├── static/
│   ├── css/
│   │   └── style.css
│   └── js/
│       └── main.js
└── README.md
```

### Option B: Installable Theme Package

For distributing your theme:

```bash
bengal utils theme new mybrand --mode package
```

This creates a complete Python package structure with `pyproject.toml`.

## 5. Configure Your Theme

Edit `bengal.toml`:

```toml
[theme]
name = "mybrand"                  # Your theme name
default_appearance = "light"      # Options: "light", "dark", "system"
default_palette = ""              # Color palette (if your theme supports multiple)
```

## 6. Customize Templates

### Override Base Layout

Edit `themes/mybrand/templates/base.html`:

```html
<!DOCTYPE html>
<html lang="{{ site.language }}">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{% block title %}{{ page.title }} - {{ site.title }}{% endblock %}</title>

    <link rel="stylesheet" href="{{ asset_url('css/style.css') }}">
    {% block extra_head %}{% endblock %}
</head>
<body>
    {% include 'partials/header.html' %}

    <main class="content">
        {% block content %}{% endblock %}
    </main>

    {% include 'partials/footer.html' %}

    <script src="{{ asset_url('js/main.js') }}"></script>
    {% block extra_scripts %}{% endblock %}
</body>
</html>
```

### Create a Custom Page Template

Edit `themes/mybrand/templates/page.html`:

```html
{% extends "base.html" %}

{% block content %}
<article class="page">
    <header class="page-header">
        <h1>{{ page.title }}</h1>
        {% if page.description %}
        <p class="lead">{{ page.description }}</p>
        {% endif %}
    </header>

    <div class="page-content">
        {{ content | safe }}
    </div>

    {% if page.tags %}
    <footer class="page-footer">
        <div class="tags">
            {% for tag in page.tags %}
            <a href="/tags/{{ tag }}/" class="tag">{{ tag }}</a>
            {% endfor %}
        </div>
    </footer>
    {% endif %}
</article>
{% endblock %}
```

## 7. Style Your Theme

Edit `themes/mybrand/static/css/style.css`:

```css
/* Design Tokens */
:root {
    --color-primary: #3498db;
    --color-text: #2c3e50;
    --color-bg: #ffffff;
    --font-sans: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
    --font-mono: 'JetBrains Mono', monospace;
    --spacing: 1.5rem;
}

/* Base Styles */
* {
    box-sizing: border-box;
}

body {
    font-family: var(--font-sans);
    line-height: 1.6;
    color: var(--color-text);
    background: var(--color-bg);
    max-width: 1200px;
    margin: 0 auto;
    padding: var(--spacing);
}

/* Typography */
h1, h2, h3, h4, h5, h6 {
    font-weight: 700;
    line-height: 1.2;
    margin-top: 2rem;
    margin-bottom: 1rem;
}

h1 { font-size: 2.5rem; }
h2 { font-size: 2rem; }
h3 { font-size: 1.5rem; }

/* Links */
a {
    color: var(--color-primary);
    text-decoration: none;
}

a:hover {
    text-decoration: underline;
}

/* Code */
code {
    font-family: var(--font-mono);
    background: #f5f5f5;
    padding: 0.2em 0.4em;
    border-radius: 3px;
    font-size: 0.9em;
}

pre code {
    display: block;
    padding: 1rem;
    overflow-x: auto;
}
```

## 8. Add Interactivity

Edit `themes/mybrand/static/js/main.js`:

```javascript
// Theme switcher
function initThemeSwitcher() {
    const toggle = document.getElementById('theme-toggle');
    if (!toggle) return;

    toggle.addEventListener('click', () => {
        const current = document.body.getAttribute('data-theme') || 'light';
        const next = current === 'light' ? 'dark' : 'light';
        document.body.setAttribute('data-theme', next);
        localStorage.setItem('theme', next);
    });

    // Restore saved theme
    const saved = localStorage.getItem('theme');
    if (saved) {
        document.body.setAttribute('data-theme', saved);
    }
}

// Smooth scroll for anchor links
function initSmoothScroll() {
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function(e) {
            e.preventDefault();
            const target = document.querySelector(this.getAttribute('href'));
            if (target) {
                target.scrollIntoView({ behavior: 'smooth' });
            }
        });
    });
}

// Initialize on load
document.addEventListener('DOMContentLoaded', () => {
    initThemeSwitcher();
    initSmoothScroll();
});
```

## 9. Test Your Theme

Start the dev server:

```bash
bengal site serve
```

Make changes to templates or CSS - the site rebuilds automatically!

### Create Test Content

```bash
bengal new page test-page
bengal new page blog-post --section blog
```

Add varied content to test different template layouts.

## 10. Advanced Features

### Multiple Color Palettes

In `themes/mybrand/theme.yaml`:

```yaml
name: mybrand
version: 1.0.0
description: My custom theme

palettes:
  default:
    primary: "#3498db"
    secondary: "#2ecc71"
  ocean:
    primary: "#1e90ff"
    secondary: "#00ced1"
  sunset:
    primary: "#ff6b6b"
    secondary: "#feca57"
```

Users can switch palettes in their `bengal.toml`:

```toml
[theme]
name = "mybrand"
default_palette = "ocean"
```

### Template Inheritance

Extend default templates selectively:

```html
{# Override just the header, keep everything else #}
{% extends "default::base.html" %}

{% block header %}
<header class="custom-header">
    <!-- Your custom header -->
</header>
{% endblock %}
```

### Custom Jinja Filters

Create `themes/mybrand/filters.py`:

```python
def truncate_words(text, count=50):
    """Truncate text to a word count."""
    words = text.split()
    if len(words) <= count:
        return text
    return ' '.join(words[:count]) + '...'

# Bengal auto-discovers filters from FILTERS dict
FILTERS = {
    'truncate_words': truncate_words,
}
```

Use in templates:

```html
<p>{{ page.content | striptags | truncate_words(30) }}</p>
```

Bengal automatically discovers filters from the `FILTERS` dictionary.

## 11. Package and Distribute

### For PyPI Distribution

```bash
cd themes/mybrand
python -m build
python -m twine upload dist/*
```

Users install with:

```bash
pip install bengal-theme-mybrand
```

### For GitHub Distribution

Push to GitHub and users can install directly:

```bash
pip install git+https://github.com/yourusername/bengal-theme-mybrand.git
```

## Template Reference

### Available Variables

**Site-wide:**
- `site.title` - Site title
- `site.description` - Site description
- `site.baseurl` - Base URL
- `site.language` - Language code
- `site.author` - Author name

**Page-specific:**
- `page.title` - Page title
- `page.content` - Rendered HTML content
- `page.description` - Page description
- `page.date` - Publication date
- `page.tags` - List of tags
- `page.categories` - List of categories
- `page.url` - Page URL
- `page.section` - Parent section

**Navigation:**
- `menu.main` - Main menu items
- `breadcrumbs` - Breadcrumb trail

### Available Filters

- `dateformat(format)` - Format dates
- `striptags` - Remove HTML tags
- `markdown` - Render markdown
- `asset_url(path)` - Get asset URL with fingerprinting

## Troubleshooting

### Debug Theme Resolution

If templates aren't loading or you're unsure where a template comes from, use the debug command:

```bash
bengal utils theme debug
```

This shows:
- **Active theme chain** - Inheritance order (child → parent → default)
- **Template resolution paths** - Priority order of template directories
- **Template sources** - Where each template file comes from
- **Theme validation** - Circular inheritance detection, missing themes

**Debug a specific template:**

```bash
bengal utils theme debug --template page.html
```

This shows exactly where `page.html` is resolved from and all locations that were checked.

### Common Issues

**Template not found:**
```bash
# Check if template exists in theme chain
bengal utils theme debug --template your-template.html

# Verify theme is active
bengal utils theme info your-theme
```

**Theme inheritance not working:**
```bash
# Check for circular inheritance
bengal utils theme debug

# Look for warnings about missing themes or circular dependencies
```

**Styles not applying:**
- Verify asset paths in templates: `{{ asset_url('css/style.css') }}`
- Check asset manifest: `bengal utils assets list`
- Ensure CSS files are in `themes/your-theme/assets/css/`
- Check browser console for 404 errors on asset files

**Theme not discovered:**
- Site themes: Must be in `themes/<slug>/templates/`
- Installed themes: Must have entry point `bengal.themes` in `pyproject.toml`
- Check: `bengal utils theme list` shows all available themes

**Template syntax errors:**
- Check Jinja2 syntax: `{% block %}` not `{%block%}`
- Verify template inheritance: `{% extends "base.html" %}`
- Check for missing closing tags: `{% endblock %}`, `{% endfor %}`
- Run dev server with `--verbose` to see template errors

**CSS not updating:**
- Hard refresh browser: `Cmd+Shift+R` (Mac) or `Ctrl+Shift+R` (Windows)
- Check if CSS file is being watched: `bengal site serve --verbose`
- Verify CSS file is in correct location: `themes/your-theme/static/css/`

## Next Steps

**Learn More:**
- **[Theme Commands](/api/cli/utils/)** - Full CLI reference
- **[Rendering System](/docs/reference/architecture/rendering/)** - Advanced templating and rendering
- **[Asset Pipeline](/api/assets/)** - CSS/JS optimization and asset management

**Get Inspired:**
- Browse bundled themes: `bengal utils theme list`
- Check example themes on [GitHub](https://github.com/lbliii/bengal)
- Explore the default theme structure: `bengal/themes/default/`

**Distribute:**
- Publish to PyPI
- Share on GitHub
- Create a showcase site

Happy theming! 🎨
