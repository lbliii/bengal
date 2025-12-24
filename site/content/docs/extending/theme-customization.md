---
title: Theme Customization
description: Override templates and customize CSS styling
weight: 20
---

Bengal themes are fully customizable through template overrides, CSS customization, and design token configuration. You can modify the default theme or create your own.

## Template Overrides

Override any theme template by placing a file with the same name in your project's `templates/` directory.

### Project Structure

```
your-project/
├── templates/
│   ├── page.html          # Overrides theme's page.html
│   ├── partials/
│   │   └── header.html    # Overrides theme's header partial
│   └── layouts/
│       └── blog.html      # Overrides blog layout
├── content/
└── bengal.toml
```

### Override Priority

Bengal searches for templates in this order:

1. Project `templates/` directory (highest priority)
2. Theme `templates/` directory
3. Built-in fallback templates

### Common Overrides

#### Custom Page Layout

Create `templates/page.html`:

```jinja
{% extends "layouts/base.html" %}

{% block content %}
<article class="custom-page">
    <header>
        <h1>{{ page.title }}</h1>
        {% if page.date %}
        <time datetime="{{ page.date | isodate }}">
            {{ page.date | date("%B %d, %Y") }}
        </time>
        {% endif %}
    </header>

    <div class="prose">
        {{ page.content | safe }}
    </div>
</article>
{% endblock %}
```

#### Custom Header

Create `templates/partials/header.html`:

```jinja
<header class="site-header">
    <nav>
        <a href="/" class="logo">{{ site.title }}</a>
        <ul class="nav-links">
            {% for item in site.menus.main %}
            <li><a href="{{ item.url }}">{{ item.name }}</a></li>
            {% endfor %}
        </ul>
    </nav>
</header>
```

#### Custom 404 Page

Create `templates/404.html`:

```jinja
{% extends "layouts/base.html" %}

{% block content %}
<div class="error-page">
    <h1>Page Not Found</h1>
    <p>The page you're looking for doesn't exist.</p>
    <a href="/">Return home</a>
</div>
{% endblock %}
```

## CSS Customization

### Method 1: Custom Stylesheet

Create a custom CSS file and reference it in your templates:

```css
/* assets/css/custom.css */
:root {
    --color-primary: #3b82f6;
    --color-text: #1f2937;
    --font-family-body: 'Inter', sans-serif;
}

.site-header {
    background: var(--color-primary);
}
```

Include it in your base template or `head.html` partial:

```jinja
<link rel="stylesheet" href="{{ 'assets/css/custom.css' | asset_url }}">
```

### Method 2: Override Design Tokens

Bengal's default theme uses CSS custom properties (design tokens). Override them in your custom CSS:

```css
/* Override semantic tokens */
:root {
    /* Colors */
    --color-primary: #3b82f6;
    --color-primary-hover: #2563eb;
    --color-text-primary: #1f2937;
    --color-bg-primary: #ffffff;

    /* Typography */
    --font-family-body: 'Inter', system-ui, sans-serif;
    --font-family-heading: 'Cal Sans', sans-serif;
    --font-family-mono: 'JetBrains Mono', monospace;

    /* Spacing */
    --space-4: 1rem;
    --space-8: 2rem;
}

/* Dark mode overrides */
[data-theme="dark"] {
    --color-text-primary: #f3f4f6;
    --color-bg-primary: #1a1a1a;
}
```

### Method 3: Import and Extend

Import the theme's styles and add your own:

```css
/* assets/css/main.css */

/* Import theme base styles */
@import '../themes/default/assets/css/style.css';

/* Your customizations */
.my-custom-component {
    padding: var(--space-4);
    background: var(--color-bg-secondary);
}
```

## Theme Configuration

Configure theme features in `bengal.toml`:

```toml
[theme]
name = "default"

[theme.appearance]
default_mode = "system"  # light, dark, or system
palette = "default"      # Color palette variant

[theme.features]
navigation.toc = true           # Table of contents
navigation.breadcrumbs = true   # Breadcrumb trail
navigation.footer_nav = true    # Previous/next links
content.code_copy = true        # Copy button on code blocks
content.heading_anchors = true  # Anchor links on headings
```

### Feature Flags

Toggle theme features without template overrides:

```toml
[theme.features]
# Navigation
navigation.toc = true
navigation.breadcrumbs = true
navigation.sidebar = true
navigation.footer_nav = true

# Content
content.code_copy = true
content.heading_anchors = true
content.reading_time = true

# Search
search.enabled = true
search.keyboard_shortcut = true
```

## Creating a Custom Theme

For extensive customization, create your own theme:

### Theme Structure

```
themes/my-theme/
├── theme.yaml           # Theme configuration
├── templates/
│   ├── layouts/
│   │   └── base.html
│   ├── page.html
│   ├── section.html
│   └── partials/
│       ├── header.html
│       ├── footer.html
│       └── nav.html
└── assets/
    ├── css/
    │   └── style.css
    ├── js/
    │   └── main.js
    └── icons/           # Custom icons
        ├── logo.svg
        └── custom.svg
```

### Theme Configuration

Create `theme.toml`:

```toml
name = "my-theme"
extends = "default"  # Optional: inherit from another theme
```

### Cross-Theme Template Extends

When your theme extends another theme (like `default`), you can explicitly reference the parent theme's templates using the `theme_name/template.html` syntax:

```jinja
{# templates/layouts/base.html #}
{% extends "default/base.html" %}

{% block head %}
{{ super() }}
<link rel="stylesheet" href="{{ 'css/my-theme.css' | asset_url }}">
{% endblock %}

{% block content %}
<div class="my-theme-wrapper">
    {{ super() }}
</div>
{% endblock %}
```

This explicit syntax is useful when:

- **Building distributable themes** - Reference parent templates by name for clarity
- **Avoiding ambiguity** - Specify exactly which theme's template to extend
- **Debugging** - Make inheritance chain visible in templates

**Without the prefix**, templates use priority-based resolution (project > child theme > parent theme > default):

```jinja
{# Uses whichever base.html is found first in the chain #}
{% extends "layouts/base.html" %}
```

**With the prefix**, templates explicitly target a specific theme:

```jinja
{# Always extends default theme's base.html #}
{% extends "default/layouts/base.html" %}
```

### Using Your Theme

Reference it in `bengal.toml`:

```toml
[theme]
name = "my-theme"
path = "themes/my-theme"  # Path to theme directory
```

## Template Variables

### Site Variables

```jinja
{{ site.title }}          # Site title
{{ site.baseurl }}        # Base URL
{{ site.config }}         # Full site config
{{ site.menus.main }}     # Navigation menus
{{ site.pages }}          # All pages
```

### Page Variables

```jinja
{{ page.title }}          # Page title
{{ page.content }}        # Rendered HTML content
{{ page.url }}            # Page URL
{{ page.date }}           # Publication date
{{ page.metadata }}       # All frontmatter
{{ page.section }}        # Parent section
{{ page.toc }}            # Table of contents
```

### Template Functions

Bengal provides 80+ template functions:

```jinja
{# String functions #}
{{ title | slugify }}
{{ content | truncatewords(50) }}

{# Date functions #}
{{ page.date | date("%B %d, %Y") }}
{{ page.date | isodate }}

{# URL functions #}
{{ "/about/" | absolute_url }}
{{ "image.png" | asset_url }}

{# Content functions #}
{{ page.content | reading_time }}
{{ pages | sort_by("date", reverse=True) }}
```

## Best Practices

### 1. Start Small

Override only what you need:

```
templates/
└── partials/
    └── header.html  # Just the header
```

### 2. Use Design Tokens

Prefer token overrides over hard-coded values:

```css
/* ✅ Good: Uses tokens */
.button {
    background: var(--color-primary);
    padding: var(--space-2) var(--space-4);
}

/* ❌ Avoid: Hard-coded values */
.button {
    background: #3b82f6;
    padding: 0.5rem 1rem;
}
```

### 3. Extend, Don't Replace

Use Jinja's `{% block %}` and `{% extends %}`:

```jinja
{% extends "layouts/base.html" %}

{% block head %}
{{ super() }}  {# Keep parent content #}
<link rel="stylesheet" href="{{ 'custom.css' | asset_url }}">
{% endblock %}
```

### 4. Test Dark Mode

Ensure customizations work in both modes:

```css
.custom-component {
    background: var(--color-bg-primary);
    color: var(--color-text-primary);
}

/* Automatically works in dark mode via tokens */
```

## Icon Customization

Add custom icons or override defaults by placing SVG files in your theme's `assets/icons/` directory:

```
themes/my-theme/assets/icons/
├── company-logo.svg   # New icon
└── warning.svg        # Overrides default
```

Icons are resolved in priority order: site theme → theme → parent theme → Bengal defaults.

See [Icon Reference](/docs/reference/icons/#custom-icons) for SVG format requirements and configuration options.

## Related

- [Icon Reference](/docs/reference/icons/) for custom icons and icon library
- [Build Hooks](/docs/extending/build-hooks/) for CSS preprocessing
- [Configuration](/docs/building/configuration/) for theme settings
- [Template Functions](/docs/reference/template-functions/) for template syntax
