---
title: Swizzle and Customize the Default Theme
nav_title: Swizzle Theme
description: Learn to copy and customize theme templates without breaking updates
weight: 20
draft: false
lang: en
tags:
- tutorial
- theming
- templates
- customization
keywords:
- tutorial
- swizzle
- theme
- templates
- customization
- default theme
category: tutorial
---

# Swizzle and Customize the Default Theme

In this tutorial, you'll learn how to **swizzle** (copy) templates from Bengal's default theme into your project, customize them, and keep them updated. By the end, you'll have a personalized site that inherits from the default theme while allowing you to make targeted customizations.

:::{note}
**Who is this for?**
This tutorial is for developers who want to customize Bengal's default theme without forking it entirely. You should have basic familiarity with HTML and Jinja2 templates. No prior experience with swizzling is required.
:::

## Goal

By the end of this tutorial, you will:

1. Understand what swizzling is and why it's useful
2. Discover available templates in the default theme
3. Swizzle specific templates to your project
4. Customize swizzled templates to match your needs
5. Track and update swizzled templates safely
6. Build a working customized site

## Prerequisites

- **Python 3.14+** installed
- **Bengal** installed (`pip install bengal` or `uv add bengal`)
- A Bengal site initialized (run `bengal new site mysite` if you haven't already)
- Basic knowledge of HTML and Jinja2 templates

## What is Swizzling?

**Swizzling** is the process of copying a template from a theme into your project's `templates/` directory. Once swizzled, you can customize the template without modifying the original theme files.

### Why Swizzle?

- **Safe customization**: Modify templates without touching installed theme files
- **Update-friendly**: Track which templates you've customized
- **Selective changes**: Only copy what you need to change
- **Provenance tracking**: Bengal remembers where templates came from

### How It Works

When Bengal renders a page, it looks for templates in this order:

1. **Your project** → `templates/` (highest priority)
2. **Installed themes** → Theme packages
3. **Bundled themes** → Built-in themes like `default`

If you swizzle a template, your version in `templates/` takes precedence. Everything else continues to use the theme's original templates.

:::{steps}
:::{step} Set Up Your Project
:description: Create or use an existing Bengal site as your starting point.
:duration: 2 min
Let's start with a fresh Bengal site. If you already have one, you can use it.

```bash
# Create a new Bengal site
bengal new site my-custom-site
cd my-custom-site
```

You should see this structure:

```tree
my-custom-site/
├── config/           # Configuration directory
│   └── _default/     # Default environment settings
├── content/          # Your markdown files
├── assets/           # CSS, JS, images
├── templates/        # Template overrides (empty initially)
└── .gitignore
```

:::{tip}
**Why `templates/` is empty**
The `templates/` directory starts empty because Bengal uses templates from the default theme. Once you swizzle templates here, they'll override the theme versions.
:::
:::{/step}

:::{step} Discover Swizzlable Templates
:description: Explore the default theme's template structure to plan your customizations.
:duration: 3 min
Before swizzling, let's see what templates are available in the default theme.

```bash
bengal utils theme discover
```

This lists all templates you can swizzle. You'll see output like:

```text
404.html
base.html
page.html
partials/action-bar.html
partials/navigation-components.html
partials/search-modal.html
partials/search.html
...
```

**Understanding Template Structure**

The default theme organizes templates into:

- **Root templates**: `base.html`, `page.html`, `404.html` — Main page templates
- **Partials**: `partials/*.html` — Reusable components (navigation, search, etc.)
- **Content types**: `blog/`, `doc/`, `autodoc/python/` — Type-specific templates

:::{dropdown} What should I swizzle?
:icon: info
**Start small**: Swizzle only what you need to customize. Common starting points:
- `partials/navigation-components.html` — Navigation menus
- `partials/search.html` — Search functionality
- `base.html` — Site-wide layout
- `page.html` — Individual page layout
:::
:::{/step}

:::{step} Swizzle Your First Template
:description: Copy a theme template to your project for customization.
:duration: 2 min
Let's swizzle the navigation components template. This is a good starting point because navigation is often customized.

```bash
bengal utils theme swizzle partials/navigation-components.html
```

You should see:

```text
✓ Swizzled to /path/to/my-custom-site/templates/partials/navigation-components.html
```

**Verify the Swizzle**

Check that the file was created:

```bash
ls -la templates/partials/
```

You should see `navigation-components.html` in your project's `templates/partials/` directory.

**Check Swizzle Registry**

Bengal tracks swizzled templates in `.bengal/themes/sources.json`. Let's see what's tracked:

```bash
bengal utils theme swizzle-list
```

Output:

```text
- partials/navigation-components.html (from default)
```

This confirms Bengal knows where the template came from.
:::{/step}

:::{step} Customize Your Swizzled Template
:description: Make targeted changes to the copied template.
:duration: 5 min
Now let's customize the navigation. Open `templates/partials/navigation-components.html` in your editor.

**Understand the Template Structure**

The file contains Jinja2 macros for navigation components. Let's add a simple customization: change the breadcrumb separator.

Find the breadcrumbs macro (around line 30-50) and look for the separator. It might look like:

```html
{% macro breadcrumbs(page) %}
  <nav class="breadcrumbs">
    {% for item in page.get_breadcrumbs() %}
      {% if not loop.last %}
        <a href="{{ item.url | absolute_url }}">{{ item.title }}</a>
        <span class="separator">/</span>
      {% else %}
        <span class="current">{{ item.title }}</span>
      {% end %}
    {% end %}
  </nav>
{% endmacro %}
```

**Make a Simple Change**

Change the separator from `/` to `→`:

```html
<span class="separator">→</span>
```

Save the file and preview your site:

```bash
bengal serve
```

Navigate to a page with breadcrumbs and verify the separator changed.

:::{tip}
**Live reload**
The dev server watches for file changes. Save your template and refresh the browser to see changes immediately.
:::
:::{/step}

:::{step} Swizzle and Customize Multiple Templates
:description: Apply the same pattern to additional components.
:duration: 5 min
:optional:
Let's swizzle the search modal and customize it.

**Swizzle the Search Modal**

```bash
bengal utils theme swizzle partials/search-modal.html
```

**Customize the Search Modal**

Open `templates/partials/search-modal.html`. You might want to:

- Change the placeholder text
- Modify the styling classes
- Add custom search behavior

For example, change the search placeholder:

```html
<!-- Find the input field -->
<input
  type="search"
  placeholder="Search the site..."
  class="search-input"
>
```

Change it to:

```html
<input
  type="search"
  placeholder="Find anything..."
  class="search-input"
>
```

**Verify Your Changes**

Check your swizzled templates:

```bash
bengal utils theme swizzle-list
```

You should see both templates:

```text
- partials/navigation-components.html (from default)
- partials/search-modal.html (from default)
```
:::{/step}

:::{step} Understand Template Inheritance
:description: Learn a lighter-weight alternative to full swizzling.
:duration: 5 min
:optional:
Swizzling copies the entire template. But you can also use **template inheritance** to override only specific parts.

**Swizzle the Base Template**

```bash
bengal utils theme swizzle base.html
```

**Use Inheritance Instead**

Instead of modifying the entire `base.html`, you can create a minimal override that extends the original:

```html
<!-- templates/base.html -->
{% extends "default::base.html" %}

{# Override only the header block #}
{% block header %}
<header class="custom-header">
  <h1>{{ site.title }}</h1>
  <nav>
    {% for item in menu.main %}
    <a href="{{ item.url }}">{{ item.name }}</a>
    {% end %}
  </nav>
</header>
{% end %}

{# Everything else inherits from default::base.html #}
```

:::{warning}
**Full swizzle vs. inheritance**
- **Full swizzle**: Copy entire template, full control, harder to update
- **Inheritance**: Override blocks only, easier to maintain, less control

Choose based on how much you need to customize.
:::
:::{/step}

:::{step} Track and Update Swizzled Templates
:description: Keep your customizations maintainable as the theme evolves.
:duration: 3 min
Bengal tracks which templates you've swizzled and whether you've modified them. This helps you update templates safely.

**Check Modification Status**

When you swizzle a template, Bengal records a checksum. If you modify the template locally, Bengal detects the change.

The `swizzle-update` command only updates templates you haven't modified:

```bash
bengal utils theme swizzle-update
```

Output:

```text
Updated: 0, Skipped (changed): 2, Missing upstream: 0
```

This means:
- **Updated: 0** — No templates were updated (you've modified them)
- **Skipped (changed): 2** — Two templates were skipped because you changed them
- **Missing upstream: 0** — All source templates still exist

**When Templates Are Updated**

Templates are only updated if:
1. The local file matches the original swizzled checksum (you haven't modified it)
2. The upstream template has changed
3. The source template still exists

This prevents overwriting your customizations.
:::{/step}

:::{step} Build and Test
:description: Generate production files and verify your customizations work.
:duration: 2 min
Let's build your customized site and verify everything works.

**Build for Production**

```bash
bengal build
```

This generates static files in `public/` using your swizzled templates.

**Verify Customizations**

1. **Check navigation**: Breadcrumbs should use `→` instead of `/`
2. **Check search**: Search placeholder should say "Find anything..."
3. **Check structure**: Site should render correctly

**Review Build Output**

```tree
public/
├── index.html
├── static/
│   └── css/
│       └── ...
└── ...
```

Your customizations are baked into the HTML files.
:::{/step}
:::{/steps}

## Best Practices

### 1. Swizzle Only What You Need

Don't swizzle everything at once. Start with one template, customize it, then move to the next.

```bash
# ✅ Good: Swizzle one at a time
bengal utils theme swizzle partials/navigation-components.html
# Customize it
# Then swizzle the next one

# ❌ Avoid: Swizzling everything
# bengal utils theme swizzle base.html
# bengal utils theme swizzle page.html
# bengal utils theme swizzle partials/*.html
# (Too many files to maintain)
```

### 2. Document Your Changes

Add comments in swizzled templates explaining why you changed something:

```html
{# Custom: Changed separator from '/' to '→' for better visual hierarchy #}
<span class="separator">→</span>
```

### 3. Use Template Inheritance When Possible

If you only need to override a block, use inheritance instead of full swizzle:

```html
{# ✅ Good: Override only what's needed #}
{% extends "default::base.html" %}
{% block header %}...{% end %}

{# ❌ Avoid: Copying entire template when you only need one block #}
```

### 4. Keep Swizzled Templates Updated

Periodically run `swizzle-update` to get bug fixes and improvements:

```bash
# Check what would be updated
bengal utils theme swizzle-update

# Review changes, then rebuild
bengal build
```

### 5. Test After Updates

After updating templates, test your site:

```bash
bengal serve
# Navigate through your site
# Verify customizations still work
```

## Troubleshooting

:::{dropdown} Template Not Found
:icon: alert

**Issue**: `FileNotFoundError: Template not found in theme chain`

**Solution**: Verify the template path:
```bash
# List available templates
bengal utils theme discover

# Use the exact path shown
bengal utils theme swizzle partials/navigation-components.html
```
:::

:::{dropdown} Changes Not Appearing
:icon: alert

**Issue**: Customizations don't show up after swizzling

**Solutions**:
- Clear cache: `bengal clean --cache`
- Restart dev server: Stop and restart `bengal serve`
- Check file location: Ensure template is in `templates/` (not `themes/`)
:::

:::{dropdown} Swizzle Update Overwrites Changes
:icon: alert

**Issue**: `swizzle-update` overwrote your customizations

**Solution**: This shouldn't happen if you've modified the file. If it does:
- Check `.bengal/themes/sources.json` for the checksum
- Restore from git if you use version control
- Re-apply your customizations
:::

:::{dropdown} Template Inheritance Not Working
:icon: alert

**Issue**: `{% extends "default::base.html" %}` doesn't work

**Solutions**:
- Verify theme name: Use `bengal utils theme info default` to confirm
- Check syntax: Use `"default::base.html"` format (theme name, double colon, path)
- Clear cache: `bengal clean --cache`
:::

## What You've Learned

In this tutorial, you:

1. ✅ Discovered available templates with `bengal utils theme discover`
2. ✅ Swizzled templates with `bengal utils theme swizzle`
3. ✅ Customized swizzled templates to match your needs
4. ✅ Tracked swizzled templates with `bengal utils theme swizzle-list`
5. ✅ Updated templates safely with `bengal utils theme swizzle-update`
6. ✅ Built a customized site using swizzled templates

## Next Steps

Now that you can swizzle templates, explore further:

- **[Theme Customization Guide](/docs/theming/themes/customize/)** — Deep dive into advanced customization techniques
- **[Template Reference](/docs/theming/templating/)** — Learn about Jinja2 templates and available functions
- **[Variables Reference](/docs/reference/theme-variables/)** — Discover all template variables available
- **[Assets Guide](/docs/theming/assets/)** — Customize CSS and JavaScript

## Summary

Swizzling lets you customize Bengal's default theme safely:

- **Discover** templates with `bengal utils theme discover`
- **Swizzle** templates with `bengal utils theme swizzle <path>`
- **Customize** swizzled templates in `templates/`
- **Track** swizzled templates with `bengal utils theme swizzle-list`
- **Update** safely with `bengal utils theme swizzle-update`

Your customizations are preserved while you can still benefit from theme updates.
