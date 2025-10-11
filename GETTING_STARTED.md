# Getting Started with Bengal SSG

## Optional Asset Pipeline (Node v22 LTS)

Bengal stays Python-only by default. If you want modern CSS/JS tooling (SCSS → CSS, PostCSS, bundling JS/TS with source maps), you can opt in to a Node-based pipeline.

Prerequisite: Install Node.js v22 LTS and add devDependencies in your project:

```json
{
  "devDependencies": {
    "sass": "^1.77.0",
    "postcss": "^8.4.35",
    "postcss-cli": "^11.0.0",
    "autoprefixer": "^10.4.19",
    "esbuild": "^0.23.0"
  }
}
```

Then enable the pipeline in `bengal.toml`:

```toml
[assets]
pipeline = true          # Enable Node-based pipeline
scss = true              # Compile SCSS → CSS
postcss = true           # Run PostCSS (requires postcss.config.cjs)
postcss_config = "postcss.config.cjs"
bundle_js = true         # Bundle/minify JS/TS with esbuild
esbuild_target = "es2018"
sourcemaps = true        # Emit source maps
```

You can also toggle at build time:

```bash
bengal build --assets-pipeline
# or
bengal build --no-assets-pipeline
```

Conventions and outputs:
- Place SCSS under `assets/scss/*.scss`; outputs appear at `public/assets/scss/*.css` (fingerprinted).
- Place JS/TS entry files under `assets/js/*.{js,ts}`; outputs appear at `public/assets/js/*.js` (fingerprinted).
- Use `asset_url('scss/main.css')` or `asset_url('js/main.js')` in templates; Bengal will resolve fingerprinted filenames automatically.

Example PostCSS config (`postcss.config.cjs`):

```js
module.exports = {
  plugins: [require('autoprefixer')]
};
```

Welcome to Bengal SSG! This guide will help you get up and running.

## Prerequisites

- Python 3.9 or higher
- pip (Python package manager)
- Basic knowledge of Markdown

## Installation

### Option 1: Install from Source (Current)

```bash
cd /Users/llane/Documents/github/python/bengal
pip install -e .
```

### Option 2: Install from PyPI (Future)

```bash
pip install bengal-ssg
```

## Verify Installation

```bash
# Check version
python -m bengal.cli --version
# Output: Bengal SSG, version 0.1.0

# Or if installed globally
bengal --version
```

## Create Your First Site

### Step 1: Create a New Site

```bash
# Create a new site
python -m bengal.cli new site myblog

# Navigate to the site directory
cd myblog
```

This creates the following structure:
```
myblog/
├── bengal.toml          # Site configuration
├── content/             # Your Markdown content
│   └── index.md         # Homepage
├── assets/              # Static assets
│   ├── css/
│   ├── js/
│   └── images/
└── templates/           # Custom templates (optional)
```

### Step 2: Review the Configuration

Open `bengal.toml`:

```toml
[site]
title = "myblog"
baseurl = ""
theme = "default"

[build]
output_dir = "public"
parallel = true

[assets]
minify = true
fingerprint = true
```

Customize it to your needs:
- `title`: Your site name
- `baseurl`: Your site URL (for production)
- `output_dir`: Where to generate the site
- `parallel`: Enable parallel processing for faster builds

### Step 3: Build Your Site

```bash
# Build the site
python -m bengal.cli build

# Output:
# Building site at /path/to/myblog...
# Processing 1 assets...
# Running post-processing...
#   ✓ Generated sitemap.xml
#   ✓ Generated rss.xml
# ✓ Site built successfully in public
# ✅ Build complete!
```

Your site is now built in the `public/` directory!

### Step 4: Start Development Server

```bash
# Start the dev server with hot reload
python -m bengal.cli serve

# Output:
# Building site before starting server...
# 👀 Watching for file changes...
#
# 🚀 Bengal dev server running at http://localhost:8000/
# 📁 Serving from: /path/to/myblog/public
# Press Ctrl+C to stop
```

Open http://localhost:8000 in your browser to see your site!

## Add Content

### Create a New Page

```bash
# Create a page in the root
python -m bengal.cli new page about

# Create a page in a section
python -m bengal.cli new page first-post --section blog
```

### Manual Page Creation

Create `content/blog/my-first-post.md`:

```markdown
---
title: My First Blog Post
type: post
date: 2025-10-02
tags: [blogging, tutorial]
description: Getting started with Bengal SSG
---

# My First Blog Post

Welcome to my blog! This is my first post using Bengal SSG.

## Why Bengal?

Bengal is:
- **Fast**: Parallel processing for quick builds
- **Simple**: Easy Markdown-based content
- **Flexible**: Powerful Jinja2 templates
- **Modern**: Asset optimization built-in

## Code Example

```python
from bengal import Site

site = Site.from_config(Path("."))
site.build()
```

## What's Next?

Stay tuned for more posts!
```

The dev server will automatically detect the change and rebuild!

## Customize Templates

### Using Default Templates

Bengal includes default templates:
- `base.html` - Base layout
- `page.html` - Regular pages
- `post.html` - Blog posts
- `index.html` - Homepage

### Creating Custom Templates

Create `templates/custom.html`:

```html
{% extends "base.html" %}

{% block content %}
<article class="custom-page">
    <header>
        <h1 class="fancy-title">{{ page.title }}</h1>
        {% if page.date %}
        <time>{{ page.date | dateformat('%B %d, %Y') }}</time>
        {% endif %}
    </header>
    
    <div class="content">
        {{ content | safe }}
    </div>
    
    <footer>
        <p>Tags: {{ page.tags | join(', ') }}</p>
    </footer>
</article>
{% endblock %}
```

Use it in your content:

```markdown
---
title: Custom Styled Page
template: custom.html
---

This page uses a custom template!
```

## Add Assets

### CSS Styling

Create `assets/css/style.css`:

```css
body {
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
    line-height: 1.6;
    max-width: 800px;
    margin: 0 auto;
    padding: 20px;
    color: #333;
}

h1 {
    color: #2c3e50;
    border-bottom: 3px solid #3498db;
    padding-bottom: 10px;
}

.tag {
    background: #3498db;
    color: white;
    padding: 3px 10px;
    border-radius: 3px;
    margin-right: 5px;
}
```

Reference it in `templates/base.html`:

```html
<link rel="stylesheet" href="{{ asset_url('css/style.css') }}">
```

### JavaScript

Create `assets/js/main.js`:

```javascript
// Add your JavaScript here
console.log('Bengal SSG loaded!');

// Example: Add smooth scrolling
document.querySelectorAll('a[href^="#"]').forEach(anchor => {
    anchor.addEventListener('click', function (e) {
        e.preventDefault();
        const target = document.querySelector(this.getAttribute('href'));
        target.scrollIntoView({ behavior: 'smooth' });
    });
});
```

Reference it:

```html
<script src="{{ asset_url('js/main.js') }}"></script>
```

## Build for Production

```bash
# Clean previous build
python -m bengal.cli clean

# Build for production
python -m bengal.cli build

# The public/ directory is ready to deploy!
```

## Deploy Your Site

The `public/` directory contains your complete static site. Deploy it to:

### Netlify

1. Push your code to GitHub
2. Connect to Netlify
3. Build command: `bengal build` or `python -m bengal.cli build`
4. Publish directory: `public`

### GitHub Pages

```bash
# Build site
python -m bengal.cli build

# Deploy to gh-pages branch
git subtree push --prefix public origin gh-pages
```

### Vercel, Cloudflare Pages, etc.

Similar to Netlify - just point to the `public/` directory.

## Advanced Features

### Frontmatter Options

```yaml
---
title: Page Title              # Required: Page title
type: page                     # Template type (page, post, index)
date: 2025-10-02              # Publication date
tags: [python, tutorial]      # Tags for organization
description: SEO description  # Meta description
template: custom.html         # Custom template override
slug: custom-url              # Custom URL slug
---
```

### Configuration Options

```toml
[site]
title = "My Site"
baseurl = "https://mysite.com"
description = "My awesome site"
theme = "default"

[build]
output_dir = "public"
parallel = true              # Use parallel processing
incremental = false          # Incremental builds (future)
max_workers = 4              # Number of parallel workers
pretty_urls = true           # /about/ instead of /about.html

[assets]
minify = true               # Minify CSS/JS
optimize = true             # Optimize images
fingerprint = true          # Add content hash to filenames

[features]
generate_sitemap = true     # Generate sitemap.xml
generate_rss = true         # Generate RSS feed
validate_links = true       # Check for broken links
```

## Custom Output Formats

Bengal can generate multiple output formats for your content, enabling search functionality, AI discovery, and programmatic access.

### Available Formats

**Per-Page Outputs:**
- **JSON** (`.json`) - Structured data for each page
- **LLM Text** (`.txt`) - AI-friendly plain text format

**Site-Wide Outputs:**
- **index.json** - Searchable index of all pages
- **llm-full.txt** - Complete site content for AI consumption

### Configuration

Add to your `bengal.toml`:

```toml
[output_formats]
enabled = true
per_page = ["json", "llm_txt"]        # Per-page formats
site_wide = ["index_json", "llm_full"] # Site-wide formats

[output_formats.options]
include_html_content = true    # Include HTML in JSON
include_plain_text = true      # Include plain text in JSON
excerpt_length = 200           # Excerpt length for index
exclude_sections = []          # Sections to exclude
exclude_patterns = ["404.html", "search.html"]
json_indent = 2                # Pretty-print JSON (use null for compact)
llm_separator_width = 80       # Separator line width
```

### Generated Files

**Per-Page JSON** (`docs/intro/index.json`):
```json
{
  "url": "/docs/intro/",
  "title": "Introduction",
  "description": "Getting started guide",
  "content": "<p>Full HTML content...</p>",
  "plain_text": "Full plain text...",
  "excerpt": "Getting started guide...",
  "metadata": {...},
  "section": "docs",
  "tags": ["docs", "intro"],
  "word_count": 1234,
  "reading_time": 5
}
```

**Per-Page LLM Text** (`docs/intro/index.txt`):
```
# Introduction

URL: /docs/intro/
Section: docs
Tags: docs, intro

--------------------------------------------------------------------------------

[Full plain text content without HTML tags]

--------------------------------------------------------------------------------

Metadata:
- Word Count: 1234
- Reading Time: 5 minutes
```

**Site Index** (`index.json`):
```json
{
  "site": {
    "title": "My Site",
    "baseurl": "https://example.com",
    "build_time": "2025-10-04T12:00:00Z"
  },
  "pages": [
    {
      "url": "/docs/intro/",
      "title": "Introduction",
      "excerpt": "Getting started...",
      "section": "docs",
      "tags": ["docs"],
      "word_count": 1234,
      "reading_time": 5
    }
  ],
  "sections": [
    {"name": "docs", "count": 15}
  ],
  "tags": [
    {"name": "tutorial", "count": 8}
  ]
}
```

### Use Cases

**1. Client-Side Search:**
```javascript
// Fetch and search the index
fetch('/index.json')
  .then(r => r.json())
  .then(data => {
    const results = data.pages.filter(p => 
      p.title.includes(searchTerm) || 
      p.excerpt.includes(searchTerm)
    );
  });
```

**2. AI/LLM Discovery:**
```bash
# Full site content for AI
curl https://mysite.com/llm-full.txt

# Per-page AI-friendly text
curl https://mysite.com/docs/intro.txt
```

**3. Static API:**
```python
# Programmatic access
import requests
data = requests.get('https://mysite.com/index.json').json()
pages = data['pages']
```

**4. Search Tools:**
- Use with [Pagefind](https://pagefind.app/)
- Build custom search with [Lunr.js](https://lunrjs.com/)
- Feed to [Fuse.js](https://fusejs.io/) for fuzzy search

## Troubleshooting

### Build Fails

```bash
# Clean and rebuild
python -m bengal.cli clean
python -m bengal.cli build
```

### Template Not Found

Make sure templates are in the correct location:
1. `templates/` in your site directory
2. `themes/<theme>/templates/`
3. Bengal's built-in templates

### Module Not Found

```bash
# Reinstall dependencies
pip install -r requirements.txt
```

### Dev Server Won't Start

Check if port 8000 is already in use:

```bash
# Use a different port
python -m bengal.cli serve --port 3000
```

## Next Steps

1. **Read Documentation**
   - [README.md](README.md) - Overview
   - [ARCHITECTURE.md](ARCHITECTURE.md) - Technical details
   - [QUICKSTART.md](QUICKSTART.md) - Quick reference

2. **Explore Examples**
   ```bash
   cd examples/quickstart
   python -m bengal.cli serve
   ```

3. **Customize Your Site**
   - Create custom templates
   - Add your own CSS/JS
   - Organize content into sections

4. **Contribute**
   - See [CONTRIBUTING.md](CONTRIBUTING.md)
   - Report bugs on GitHub
   - Suggest features

## CLI Reference

```bash
# General
bengal --version             # Show version
bengal --help                # Show help

# Building
bengal build                 # Build site
bengal build --no-parallel   # Sequential build
bengal build --config path   # Use custom config

# Development
bengal serve                 # Start dev server
bengal serve --port 3000     # Custom port
bengal serve --no-watch      # Disable file watching
bengal serve --verbose       # Show detailed server activity
bengal serve --debug         # Show debug output

# Management
bengal clean                 # Clean output directory

# Creation
bengal new site <name>       # Create new site
bengal new page <name>       # Create new page
```

## Support

- **Issues**: https://github.com/bengal-ssg/bengal/issues
- **Discussions**: https://github.com/bengal-ssg/bengal/discussions
- **Docs**: https://bengal-ssg.github.io

Happy building! 🐯

