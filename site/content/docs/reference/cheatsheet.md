---
title: Cheatsheet
description: Quick reference for common Bengal commands, patterns, and configurations
weight: 1
tags:
- reference
- cheatsheet
- quick-reference
---

# Cheatsheet

Single-page quick reference for Bengal. Print it, pin it, bookmark it.

---

## CLI Commands

### Build & Serve

```bash
# Build site
bengal build                           # Full build
bengal build --fast                    # Parallel + quiet, max speed
bengal build --incremental             # Only changed files (auto if cache exists)
bengal build --profile dev             # Developer profile (full debug)
bengal build --profile theme-dev       # Themer profile (template focus)
bengal build --dashboard               # Interactive TUI dashboard
bengal build --strict                  # Fail on template errors (CI/CD)
bengal build --validate                # Validate templates before build
bengal build --memory-optimized        # Streaming build (5K+ pages)
bengal build --dry-run                 # Preview build without writing files
bengal build --explain                 # Show why pages rebuilt/skipped
bengal build --explain --explain-json  # Machine-readable explain output
PYTHON_GIL=0 bengal build --fast       # Free-threaded mode (Python 3.14+)

# Development server
bengal serve                           # Default port 5173
bengal serve --port 8080               # Custom port
bengal serve --no-open                 # Don't open browser
bengal serve --no-watch                # Disable file watching
bengal serve --dashboard               # Interactive TUI dashboard
bengal serve --version v2              # Focus on single version

# Clean
bengal clean                           # Remove output directory
bengal clean --cache                   # Also clear build cache
bengal clean --all                     # Remove output + cache
bengal clean --stale-server            # Kill stale server processes
```

### Create Content

```bash
# New project
bengal new site mysite                 # Interactive wizard
bengal new site mysite --template blog  # Skip wizard with template

# New content
bengal new page my-page                # Page at content/my-page.md
bengal new page post --section blog    # Page at content/blog/post.md

# New templates
bengal new layout article              # templates/layouts/article.html
bengal new partial sidebar             # templates/partials/sidebar.html
bengal new theme mytheme               # themes/mytheme/
```

### Validation & Health

```bash
bengal validate                        # Full validation
bengal validate --changed              # Only changed files
bengal validate --watch                # Watch mode (continuous)
bengal validate --verbose              # Show all checks
bengal validate --suggestions          # Show quality suggestions
bengal health linkcheck                # Check all links
bengal health linkcheck --external-only # External links only
bengal health linkcheck --internal-only # Internal links only
bengal health --dashboard              # Interactive health dashboard
```

### Configuration

```bash
bengal config show                     # Show effective config
bengal config show --origin            # Show config source files
bengal config doctor                   # Validate configuration
bengal config diff --against production # Compare environments
bengal config init                     # Create config directory
```

### Utilities

```bash
bengal utils theme list                # List available themes
bengal utils theme debug               # Debug theme resolution
bengal utils theme swizzle TEMPLATE    # Copy template for customization
bengal utils perf                      # Performance metrics
bengal graph analyze                   # Site structure analysis
bengal graph analyze --tree            # Tree visualization
bengal graph suggest                   # Link suggestions
bengal graph orphans                   # Find disconnected pages
bengal explain PAGE                    # Introspect page rendering
```

---

## Front Matter

### Essential Fields

```yaml
---
title: "Page Title"                    # Required
description: "SEO meta description"    # Recommended
date: 2024-01-15                       # Publication date
draft: false                           # true = exclude from production
weight: 10                             # Sort order (lower = first)
---
```

### Taxonomies & Classification

```yaml
---
tags: [python, tutorial, beginner]
categories: [guides]
author: "Jane Doe"
---
```

### Type & Variant

```yaml
---
type: post                             # Template type (templates/post/)
variant: custom                        # Visual presentation variant
template: special.html                 # Specific template file
---
```

### Advanced Options

```yaml
---
aliases: ["/old-url/", "/another/"]    # URL redirects
slug: custom-url                       # Override URL slug
url: /exact/path/                      # Exact URL path
cascade:                               # Pass to child pages
  author: "Jane Doe"
  draft: true
outputs: [html, json, rss]             # Output formats
no_format: true                        # Skip HTML formatting
---
```

---

## Template Variables

### Page Context

```kida
{{ page.title }}              {# Page title #}
{{ page.description }}        {# Meta description #}
{{ page.content }}            {# Rendered HTML content #}
{{ page.excerpt }}            {# Auto-generated excerpt #}
{{ page.href }}               {# URL with baseurl applied #}
{{ page._path }}              {# Site-relative URL (for comparisons) #}
{{ page.date }}               {# Publication date #}
{{ page.lastmod }}            {# Last modified date #}
{{ page.draft }}              {# Draft status (boolean) #}
{{ page.weight }}             {# Sort weight #}
{{ page.tags }}               {# List of tags #}
{{ page.categories }}         {# List of categories #}
{{ page.reading_time }}       {# Estimated reading time #}
{{ page.word_count }}         {# Word count #}
{{ page.toc }}                {# Table of contents HTML #}
```

### Site Context

```kida
{{ site.title }}              {# Site title #}
{{ site.description }}        {# Site description #}
{{ site.baseurl }}            {# Base URL #}
{{ site.language }}           {# Site language code #}
{{ site.author }}             {# Default author #}
{{ site.pages }}              {# All pages #}
{{ site.sections }}           {# All sections #}
{{ site.menus.main }}         {# Main menu items #}
```

### Section Context

```kida
{{ section.title }}           {# Section title #}
{{ section.pages }}           {# Pages in this section #}
{{ section.subsections }}     {# Child sections #}
{{ section.parent }}          {# Parent section #}
```

---

## Common Patterns

### List Pages in Section

```kida
{% for page in section.pages |> sort_by('date', reverse=true) %}
  <article>
    <h2><a href="{{ page.href }}">{{ page.title }}</a></h2>
    <time>{{ page.date | date('%B %d, %Y') }}</time>
    <p>{{ page.excerpt | card_excerpt(30, page.title, page.description) | safe }}</p>
  </article>
{% end %}
```

### Card Preview (no title duplication)

```kida
{# Use card_excerpt so preview text does not repeat the title or description #}
<p>{{ page.excerpt | card_excerpt(30, page.title, page.description) | safe }}</p>

{# Tiles/docs: excerpt_for_card + excerpt for char truncation #}
<p>{{ item.description | excerpt_for_card(item.title) | excerpt(120) }}</p>
```

### Render Tags

```kida
{% for tag in page.tags %}
  <a href="/tags/{{ tag | slugify }}/" class="tag">{{ tag }}</a>
{% end %}
```

### Conditional Content

```kida
{% if page.draft %}
  <div class="draft-banner">⚠️ Draft</div>
{% end %}

{% if page.toc %}
  <nav class="toc">{{ page.toc }}</nav>
{% end %}
```

### Include Partials

```kida
{% include "partials/header.html" %}
{% include "partials/footer.html" %}
{% include "partials/sidebar.html" with context %}
```

### Navigation Menu

```kida
<nav>
  {% for item in site.menus.main |> sort_by('weight') %}
    <a href="{{ item.url }}"
       {% if page._path == item.url %}class="active"{% end %}>
      {{ item.name }}
    </a>
  {% end %}
</nav>
```

### Breadcrumbs

```kida
<nav class="breadcrumbs">
  <a href="/">Home</a>
  {% for ancestor in page.ancestors %}
    <span>/</span>
    <a href="{{ ancestor.url }}">{{ ancestor.title }}</a>
  {% end %}
  <span>/</span>
  <span>{{ page.title }}</span>
</nav>
```

---

## Project Structure

```tree
mysite/
├── bengal.toml              # Configuration
├── content/                 # Source content
│   ├── _index.md            # Homepage
│   ├── about.md             # Standalone page
│   └── blog/                # Section
│       ├── _index.md        # Section index
│       ├── first-post.md    # Blog post
│       └── second-post/     # Page bundle
│           ├── index.md     # Page content
│           └── image.png    # Co-located asset
├── templates/               # Custom templates
│   ├── base.html            # Base template
│   ├── partials/            # Reusable fragments
│   └── post/                # Post type templates
│       └── single.html
├── assets/                  # Static assets
│   ├── css/
│   ├── js/
│   └── images/
├── data/                    # Data files (YAML/JSON)
├── themes/                  # Local themes
└── public/                  # Output (generated)
```

---

## Configuration Quick Reference

### Minimal Config

```toml
[site]
title = "My Site"
baseurl = "https://example.com"
```

### Common Settings

```toml
[site]
title = "My Site"
baseurl = "https://example.com"
description = "Site description for SEO"
language = "en"
author = "Your Name"

[build]
output_dir = "public"
fast_mode = true                # Parallel + quiet

[theme]
name = "default"
default_appearance = "system"   # light, dark, system

[assets]
minify = true
fingerprint = true

[markdown]
parser = "patitas"  # Default (thread-safe, O(n))
table_of_contents = true
gfm = true

[[menu.main]]
name = "Home"
url = "/"
weight = 1

[[menu.main]]
name = "Blog"
url = "/blog/"
weight = 2
```

---

## Quick Commands

| Task | Command |
|------|---------|
| Build site | `bengal build` |
| Fast build | `bengal build --fast` |
| Preview build | `bengal build --dry-run` |
| Debug incremental | `bengal build --explain` |
| Dev server | `bengal serve` |
| New page | `bengal new page <name>` |
| Validate | `bengal validate` |
| Link check | `bengal health linkcheck` |
| Show config | `bengal config show` |
| Analyze site | `bengal graph analyze` |
| Help | `bengal --help` |

### Short Aliases

| Alias | Command |
|-------|---------|
| `bengal b` | `bengal build` |
| `bengal s` | `bengal serve` |
| `bengal c` | `bengal clean` |
| `bengal v` | `bengal validate` |
| `bengal dev` | `bengal serve` |
| `bengal check` | `bengal validate` |

---

## Filters Reference

```kida
{{ "hello world" | title }}           {# Hello World #}
{{ "Hello World" | slugify }}         {# hello-world #}
{{ page.date | date('%Y-%m-%d') }}    {# 2024-01-15 #}
{{ page.date | timeago }}             {# 2 days ago #}
{{ text | truncate(100) }}            {# First 100 chars... #}
{{ text | striptags }}                {# Remove HTML tags #}
{{ list | length }}                   {# Count items #}
{{ list | first }}                    {# First item #}
{{ list | last }}                     {# Last item #}
{{ list |> sort_by('date') }}   {# Sort by attribute #}
{{ list | reverse }}                  {# Reverse order #}
{{ list | join(', ') }}               {# Join with comma #}
{{ path | asset_url }}                {# Fingerprinted URL #}
```

---

:::{seealso}
- [[docs/reference/architecture/tooling/cli|Full CLI Reference]] — All commands and options
- [[docs/reference/template-functions|Template Functions]] — All template helpers
- [[docs/content/authoring/linking|Linking Guide]] — Complete linking reference
- [[docs/reference/architecture/tooling/config|Configuration Reference]] — All config options
:::
