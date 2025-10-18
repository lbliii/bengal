# Bengal SSG - Quick Start Guide

## Installation

```bash
# Install from source
git clone <repository-url>
cd bengal
pip install -e .

# Or with uv
uv pip install -e .
```

## Create Your First Site

```bash
# Create a new site
bengal new site myblog
cd myblog

# Directory structure created:
# myblog/
# ├── bengal.toml          # Configuration
# ├── content/             # Your content
# │   └── index.md
# ├── assets/              # Static files
# │   ├── css/
# │   ├── js/
# │   └── images/
# └── templates/           # Custom templates (optional)
```

## Build and Serve

```bash
# Build the site
bengal site build

# Start development server with hot reload
bengal site serve

# Visit http://localhost:5173 (or the URL printed in the console)
```

## Add Content

### Create a New Page

```bash
# Create a page in the root
bengal new page about

# Create a page in a section
bengal new page --section blog first-post
```

### Manual Page Creation

Create `content/blog/hello-world.md`:

```markdown
---
title: Hello World
date: 2025-10-02
tags: [tutorial, first-post]
type: post
---

# Hello World

This is my first blog post!

## Features

- Easy Markdown editing
- Fast builds
- Hot reload development
```

## Configuration

Edit `bengal.toml`:

```toml
[site]
title = "My Awesome Blog"
baseurl = "https://myblog.com"
description = "A blog about awesome things"

[build]
output_dir = "public"
parallel = true        # Use parallel processing
pretty_urls = true     # /about/index.html instead of /about.html

[assets]
minify = true         # Minify CSS/JS
optimize = true       # Optimize images
fingerprint = true    # Add content hash to filenames
```

## Customize Templates

Bengal uses Jinja2 templates. Override the default templates by creating your own:

`templates/page.html`:
```html
{% extends "base.html" %}

{% block content %}
<article>
    <h1>{{ page.title }}</h1>
    <div class="content">
        {{ content | safe }}
    </div>
</article>
{% endblock %}
```

## Add Assets

Place files in the `assets/` directory:

```
assets/
├── css/
│   └── style.css
├── js/
│   └── main.js
└── images/
    └── logo.png
```

Reference them in templates:
```html
<link rel="stylesheet" href="{{ asset_url('css/style.css') }}">
<img src="{{ asset_url('images/logo.png') }}" alt="Logo">
```

## Deploy

After building, deploy the `public/` directory to your hosting provider:

```bash
# Build for production
bengal site build

# The public/ directory contains your complete site
# Upload it to:
# - Netlify
# - Vercel
# - GitHub Pages
# - Any static hosting provider
```

### Deploy to GitHub Pages

```bash
# Build site
bengal site build

# Deploy to gh-pages branch
git subtree push --prefix public origin gh-pages
```

## Advanced Features

### Frontmatter Options

```yaml
---
title: Page Title              # Page title
date: 2025-10-02              # Publication date
type: post                     # Template type (page, post, index)
tags: [python, tutorial]      # Tags
description: Short summary    # Meta description
template: custom.html         # Custom template
---
```

### Available CLI Commands

```bash
bengal site build              # Build the site
bengal site serve              # Start dev server
bengal site clean              # Clean output directory
bengal new site <name>    # Create new site
bengal new page <name>    # Create new page
bengal --version          # Show version
bengal --help             # Show help
```

### Development Server Options

```bash
# Custom host and port
bengal site serve --host 0.0.0.0 --port 3000

# Disable file watching
bengal site serve --no-watch

# Show detailed server activity
bengal site serve --verbose

# Show debug output (port checks, file changes, etc.)
bengal site serve --debug

# Use custom config file
bengal site serve --config custom-config.toml
```

## Example Sites

Check out example sites in the `examples/` directory:

```bash
cd examples/quickstart
bengal site serve
```

## Next Steps

- Read the [Architecture Documentation](ARCHITECTURE.md)
- Explore [Contributing Guidelines](CONTRIBUTING.md)
- Check out the full [README](README.md)
- Create your own custom theme
- Add plugins (coming soon!)

## Troubleshooting

### Build Errors

```bash
# Clean and rebuild
bengal site clean
bengal site build
```

### Template Not Found

Make sure your templates are in:
1. `templates/` (custom templates)
2. `themes/<theme>/templates/` (theme templates)
3. Bengal's built-in default templates

### Import Errors

Make sure all dependencies are installed:
```bash
pip install -r requirements.txt
```

## Getting Help

- Check [ARCHITECTURE.md](ARCHITECTURE.md) for technical details
- See [CONTRIBUTING.md](CONTRIBUTING.md) for development guidelines
- Review example sites in the `examples/` directory
