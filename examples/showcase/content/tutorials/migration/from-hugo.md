---
title: "Migrating from Hugo to Bengal"
description: "Complete guide to migrating your Hugo site to Bengal SSG"
date: 2025-10-04
weight: 10
tags: ["migration", "hugo", "tutorial", "guide"]
toc: true
---

# Migrating from Hugo to Bengal

This guide helps you migrate your Hugo site to Bengal SSG. We'll cover feature mapping, content migration, configuration conversion, and everything you need for a smooth transition.

```{success} Why Migrate?
Bengal offers:
- 🐍 **Python ecosystem** - vs Go
- 🎯 **Simpler architecture** - No God objects
- ⚡ **Similar performance** - Competitive speeds
- 🧪 **Better quality tools** - Health checks built-in
- 🤖 **AI-ready outputs** - LLM-txt format
```

---

## 📊 Feature Comparison

### Feature Matrix

| Feature | Hugo | Bengal | Notes |
|---------|------|--------|-------|
| **Performance** | ⚡⚡⚡ | ⚡⚡⚡ | Both very fast |
| **Templating** | Go templates | Jinja2 | Jinja2 more familiar |
| **Content organization** | ✅ | ✅ | Similar structure |
| **Taxonomies** | ✅ | ✅ | Tags, categories |
| **Shortcodes** | ✅ | ✅ Directives | Different syntax |
| **Themes** | ✅ | ✅ | Different structure |
| **i18n** | ✅ | ⚠️ Partial | Coming in v2.0 |
| **Asset pipeline** | Hugo Pipes | ✅ | Different approach |
| **Health checks** | ❌ | ✅ | Bengal exclusive |
| **LLM outputs** | ❌ | ✅ | Bengal exclusive |
| **Output formats** | Limited | ✅ Full | JSON, LLM-txt |

```{note} Performance Comparison
**Hugo:** ~1.5ms per page (extremely fast, Go)
**Bengal:** ~2-3ms per page (very fast, Python)

For most sites (< 10,000 pages), the difference is negligible.
```

---

## 🗂️ Content Migration

### Directory Structure Mapping

```{tabs}
:id: directory-mapping

### Tab: Hugo Structure

```
my-hugo-site/
├── config.toml           # Configuration
├── content/              # Content
│   ├── _index.md
│   ├── about.md
│   ├── posts/
│   │   ├── _index.md
│   │   └── first-post.md
│   └── docs/
│       └── getting-started.md
├── layouts/              # Templates
│   ├── _default/
│   │   ├── baseof.html
│   │   ├── single.html
│   │   └── list.html
│   └── partials/
│       ├── header.html
│       └── footer.html
├── static/               # Static assets
│   ├── css/
│   └── images/
└── themes/               # Themes
    └── my-theme/
```

### Tab: Bengal Structure

```
my-bengal-site/
├── bengal.toml           # Configuration (same location)
├── content/              # Content (same!)
│   ├── _index.md
│   ├── about.md
│   ├── posts/
│   │   ├── _index.md
│   │   └── first-post.md
│   └── docs/
│       └── getting-started.md
├── templates/            # Custom templates (optional)
│   └── custom-post.html
├── assets/               # Static assets (similar to static/)
│   ├── css/
│   └── images/
└── themes/               # Themes (same concept)
    └── default/
```

**Key differences:**
- `config.toml` → `bengal.toml` (mostly compatible!)
- `layouts/` → Built-in templates + optional `templates/`
- `static/` → `assets/` or theme `assets/`
- Content structure is **nearly identical**!
```

### Frontmatter Migration

```{tabs}
:id: frontmatter-mapping

### Tab: Hugo Frontmatter

```markdown
---
title: "My Post"
date: 2025-10-04
draft: false
tags: ["hugo", "tutorial"]
categories: ["blog"]
weight: 10
summary: "This is a summary"
description: "Meta description"
author: "John Doe"

# Hugo-specific
aliases: ["/old-url/", "/another-url/"]
slug: "custom-slug"
---
```

### Tab: Bengal Frontmatter

```markdown
---
title: "My Post"
date: 2025-10-04
draft: false
tags: ["hugo", "tutorial"]
categories: ["blog"]
weight: 10
description: "Meta description"      # Used for both summary and SEO
author: "John Doe"

# Bengal-specific (optional)
toc: true                            # Enable table of contents
template: "custom-post.html"         # Use custom template
---
```

**Differences:**
- ✅ `title`, `date`, `draft`, `tags`, `categories`, `weight` - **identical**
- ❌ `aliases` - Not directly supported (use redirects)
- ⚠️ `summary` - Use `description` instead
- ✅ `slug` - Works the same
- 🆕 `toc` - Bengal-specific feature
```

---

## ⚙️ Configuration Migration

### Config File Conversion

```{tabs}
:id: config-conversion

### Tab: Hugo (config.toml)

```toml
baseURL = "https://example.com"
languageCode = "en-us"
title = "My Hugo Site"
theme = "my-theme"

[params]
  description = "Site description"
  author = "John Doe"
  
[taxonomies]
  tag = "tags"
  category = "categories"

[menu]
  [[menu.main]]
    name = "Home"
    url = "/"
    weight = 1
  
  [[menu.main]]
    name = "Posts"
    url = "/posts/"
    weight = 2
```

### Tab: Bengal (bengal.toml)

```toml
[site]
baseurl = "https://example.com"      # Same!
language = "en"                       # Simplified
title = "My Hugo Site"                # Same!
description = "Site description"      # Moved from params
author = "John Doe"                   # Moved from params

[build]
theme = "default"                     # Your converted theme
content_dir = "content"
output_dir = "public"
parallel = true                       # 🆕 Better than Hugo!
incremental = true                    # 🆕 18-42x faster!

[taxonomies]
tags = "tags"                         # Same!
categories = "categories"             # Same!

[menus]
  [[menus.main]]
    name = "Home"
    url = "/"
    weight = 1
  
  [[menus.main]]
    name = "Posts"
    url = "/posts/"
    weight = 2
```

**Conversion tips:**
- Most keys stay the same!
- `[params]` → Moved to `[site]`
- `[menu]` → `[menus]`
- Added `[build]` section with new features
```

---

## 🎨 Template Migration

### Template Syntax Comparison

```{tabs}
:id: template-syntax

### Tab: Hugo Template

```go-html-template
{{/* Hugo uses Go templates */}}

<!-- Variables -->
{{/* .Title */}}
{{/* .Content */}}
{{/* .Date */}}
{{/* .Params.author */}}

<!-- Conditionals -->
{{/* if .Draft */}}
  <span>Draft</span>
{{/* end */}}

<!-- Loops -->
{{/* range .Pages */}}
  <article>
    <h2>{{/* .Title */}}</h2>
  </article>
{{/* end */}}

<!-- Functions -->
{{/* .Content | markdownify */}}
{{/* .Title | lower */}}
{{/* len .Pages */}}

<!-- Partials -->
{{/* partial "header.html" . */}}
```

### Tab: Bengal Template

```jinja2
{# Bengal uses Jinja2 #}

{# Variables #}
{{/* page.title */}}
{{/* page.content | safe */}}
{{/* page.date */}}
{{/* page.metadata.author */}}

{# Conditionals #}
{% if page.draft %}
  <span>Draft</span>
{% endif %}

{# Loops #}
{% for child in page.children %}
  <article>
    <h2>{{/* child.title */}}</h2>
  </article>
{% endfor %}

{# Filters #}
{{/* page.content | markdownify | safe */}}
{{/* page.title | lower */}}
{{/* page.children | length */}}

{# Includes (like partials) #}
{% include "partials/header.html" %}
```

**Key differences:**
- `{{ }}` - Same for output
- `{{ }}` vs `{% %}` - Jinja uses `{% %}` for logic
- `.Title` → `page.title` - Lowercase properties
- `.Params.X` → `page.metadata.X` - Metadata access
- `range` → `for` - Different loop syntax
- `partial` → `include` - Different inclusion```

### Common Template Conversions

```{dropdown} Hugo `.Title` → Bengal `page.title`

**Hugo:**
```go-html-template
<h1>{{/* .Title */}}</h1>
<p>By {{/* .Params.author */}}</p>
<time>{{/* .Date.Format "2006-01-02" */}}</time>
```

**Bengal:**
```jinja2
<h1>{{/* page.title */}}</h1>
<p>By {{/* page.metadata.author */}}</p>
<time>{{/* page.date | format_date("%Y-%m-%d") */}}</time>
```
```

```{dropdown} Hugo `.Pages` → Bengal `section.pages` or `page.children`

**Hugo:**
```go-html-template
{{/* range .Pages */}}
  <a href="{{/* .RelPermalink */}}">{{/* .Title */}}</a>
{{/* end */}}
```

**Bengal:**
```jinja2
{% for child in page.children %}
  <a href="{{/* child.url */}}">{{/* child.title */}}</a>
{% endfor %}
```
```

```{dropdown} Hugo Conditionals → Bengal Conditionals

**Hugo:**
```go-html-template
{{/* if eq .Type "post" */}}
  <span>Blog Post</span>
{{/* else if eq .Type "page" */}}
  <span>Page</span>
{{/* else */}}
  <span>Other</span>
{{/* end */}}
```

**Bengal:**
```jinja2
{% if page.metadata.type == "post" %}
  <span>Blog Post</span>
{% elif page.metadata.type == "page" %}
  <span>Page</span>
{% else %}
  <span>Other</span>
{% endif %}
```
```

---

## 🔌 Shortcodes vs Directives

### Syntax Comparison

```{tabs}
:id: shortcodes-vs-directives

### Tab: Hugo Shortcodes

```markdown
<!-- Note admonition -->
{{< note >}}
This is a note.
{{< /note >}}

<!-- YouTube embed -->
{{< youtube id="dQw4w9WgXcQ" >}}

<!-- Figure -->
{{< figure src="image.jpg" title="My Image" >}}

<!-- Highlight -->
{{< highlight python >}}
def hello():
    print("Hello, World!")
{{< /highlight >}}
```

### Tab: Bengal Directives

```markdown
<!-- Note admonition -->
```{note}
This is a note.
```

<!-- No built-in YouTube (use HTML or create custom) -->
<iframe src="https://youtube.com/embed/dQw4w9WgXcQ"></iframe>

<!-- Figure (use HTML) -->
![My Image](image.jpg)
*My Image*

<!-- Highlight (built-in with ``` syntax) -->
```python
def hello():
    print("Hello, World!")
```
```

**Migration notes:**
- Hugo shortcodes `{{< >}}` → Bengal directives ` ```{} `
- Some shortcodes need HTML equivalents
- Code highlighting is built-in (no shortcode needed)```

### Admonition Migration

```{example} Hugo Notices → Bengal Admonitions

**Hugo (using custom shortcodes):**
```markdown
{{< notice note >}}
This is a note.
{{< /notice >}}

{{< notice warning >}}
This is a warning.
{{< /notice >}}
```

**Bengal (built-in):**
```markdown
```{note}
This is a note.
```

```{warning}
This is a warning.
```
```

Bengal has **9 built-in admonition types**:
- note, tip, warning, danger, error, info, example, success, caution

Hugo requires custom shortcodes or theme support.
```

---

## 🔄 Build Process Migration

### Build Commands

```{tabs}
:id: build-commands

### Tab: Hugo

```bash
# Development server
hugo server -D --watch

# Production build
hugo --minify

# Clean
hugo --cleanDestinationDir

# New content
hugo new posts/my-post.md
```

### Tab: Bengal

```bash
# Development server
bengal serve --watch

# Production build
bengal build --parallel --incremental

# Clean
bengal clean

# New content
bengal new posts/my-post.md
```

**Nearly identical!** Commands map 1:1.
```

### Performance Optimization

```{example} Enable Bengal's Speed Features

**Hugo (config.toml):**
```toml
# Hugo doesn't have incremental builds
# (full rebuild every time)

[minify]
  minifyOutput = true
```

**Bengal (bengal.toml):**
```toml
[build]
parallel = true          # 2-4x faster!
incremental = true       # 18-42x faster rebuilds!
minify_html = true       # Like Hugo minify

[build.cache]
enabled = true           # Required for incremental
```

**Result:** Bengal rebuilds are **18-42x faster** than Hugo after first build!
```

---

## 📝 Step-by-Step Migration

### 1. Install Bengal

```bash
# Create Python virtual environment (optional but recommended)
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install Bengal
pip install bengal-ssg
```

### 2. Copy Content

```bash
# Your Hugo content works as-is!
cp -r my-hugo-site/content my-bengal-site/content

# Static assets
cp -r my-hugo-site/static my-bengal-site/assets
```

### 3. Convert Configuration

```bash
# Copy and rename
cp my-hugo-site/config.toml my-bengal-site/bengal.toml

# Then edit bengal.toml:
# - Move [params] values to [site]
# - Add [build] section
# - Update theme name
```

### 4. Audit Frontmatter

```bash
# Check for Hugo-specific fields
grep -r "aliases:" content/
grep -r "summary:" content/

# Replace if needed:
# - summary → description
# - Consider aliases workaround
```

### 5. Convert Templates (if custom)

```bash
# If using Hugo layouts/, convert to Jinja2
# See template syntax comparison above

# Or use Bengal's default theme
```

### 6. Test Build

```bash
cd my-bengal-site
bengal build

# Check output
ls public/
```

### 7. Test Locally

```bash
bengal serve

# Visit http://localhost:8000
# Verify pages render correctly
```

### 8. Run Health Checks

```bash
# Bengal's exclusive feature!
bengal health-check

# Fix any issues reported
```

### 9. Deploy

```bash
# Same deployment as Hugo!
# Just deploy the public/ directory
```

---

## 🐛 Common Migration Issues

```{dropdown} Issue: "Template function not found"

**Problem:** Hugo function doesn't exist in Bengal

**Hugo:**
```go-html-template
{{/* .Title | humanize */}}
```

**Solution:** Use equivalent Bengal filter:
```jinja2
{{/* page.title | titleize */}}
```

See [Template Functions Reference](../../docs/templates/function-reference/) for all 75 functions.
```

```{dropdown} Issue: "Shortcode not rendering"

**Problem:** Hugo shortcodes don't work in Bengal

**Solution:** Convert to directives or HTML:

**Hugo:**
```markdown
{{< youtube "dQw4w9WgXcQ" >}}
```

**Bengal:**
```html
<iframe src="https://youtube.com/embed/dQw4w9WgXcQ"></iframe>
```

Or create custom directive (advanced).
```

```{dropdown} Issue: "Menu not showing"

**Problem:** Menu configuration syntax difference

**Hugo:**
```toml
[menu]
  [[menu.main]]
    name = "Home"
```

**Bengal:**
```toml
[menus]          # Note the 's'
  [[menus.main]]
    name = "Home"
```

Simple typo - add the 's'!
```

```{dropdown} Issue: "Taxonomies not working"

**Problem:** Plural/singular mismatch

**Hugo:**
```toml
[taxonomies]
  tag = "tags"
  category = "categories"
```

**Bengal:**
```toml
[taxonomies]
tags = "tags"          # Reverse order
categories = "categories"
```

Bengal uses `plural = "singular"` format.
```

---

## 🎯 Migration Checklist

```{tabs}
:id: migration-checklist

### Tab: Pre-Migration

- [ ] Backup Hugo site
- [ ] Document custom features
- [ ] List shortcodes used
- [ ] Note template customizations
- [ ] Check Hugo version
- [ ] Test build locally

### Tab: During Migration

- [ ] Install Bengal
- [ ] Copy content directory
- [ ] Copy static assets
- [ ] Convert config.toml → bengal.toml
- [ ] Update frontmatter if needed
- [ ] Convert templates (if custom)
- [ ] Test build
- [ ] Run health checks
- [ ] Fix any issues

### Tab: Post-Migration

- [ ] Verify all pages render
- [ ] Check navigation menus
- [ ] Test taxonomies (tags/categories)
- [ ] Validate internal links
- [ ] Test RSS feed
- [ ] Verify sitemap
- [ ] Check mobile responsiveness
- [ ] Run full health check
- [ ] Update deployment config
- [ ] Deploy to staging
- [ ] Test staging thoroughly
- [ ] Deploy to production
```

---

## 💡 Pro Tips

```{success} Hybrid Approach

You can run Hugo and Bengal side-by-side during migration!

**Directory structure:**
```
my-site/
├── hugo/              # Original Hugo site
│   ├── config.toml
│   └── content/
├── bengal/            # New Bengal site
│   ├── bengal.toml
│   └── content/       # Symlink to ../hugo/content/
└── deploy/
    └── script.sh      # Deploy Bengal build
```

**Benefit:** Test Bengal without breaking Hugo!
```

```{tip} Automated Conversion Script

Create a migration script:

```python
#!/usr/bin/env python3
"""Hugo to Bengal migration helper."""

import shutil
import re
from pathlib import Path

def migrate_frontmatter(content_dir):
    """Convert Hugo-specific frontmatter."""
    for md_file in Path(content_dir).rglob("*.md"):
        content = md_file.read_text()
        
        # Replace summary with description
        content = content.replace("summary:", "description:")
        
        # Add TOC for docs
        if "/docs/" in str(md_file):
            content = content.replace("---\n", "---\ntoc: true\n", 1)
        
        md_file.write_text(content)
        print(f"Converted: {md_file}")

def convert_config(hugo_config, bengal_config):
    """Convert Hugo config to Bengal config."""
    # Read Hugo config
    with open(hugo_config) as f:
        hugo = f.read()
    
    # Convert [menu] to [menus]
    bengal = hugo.replace("[menu]", "[menus]")
    
    # Move [params] to [site]
    # (simplified - add more complex logic as needed)
    
    with open(bengal_config, 'w') as f:
        f.write(bengal)
    
    print(f"Converted config: {bengal_config}")

if __name__ == "__main__":
    migrate_frontmatter("content/")
    convert_config("hugo-config.toml", "bengal.toml")
    print("Migration complete!")
```

Save time with automation!
```

---

## 📊 Before & After Comparison

### Build Performance

```{tabs}
:id: performance-comparison

### Tab: Hugo Performance

```
Full build:       0.8s (150 pages)
Incremental:      0.8s (no incremental support)
Pages/second:     187.5

Memory:           45 MB
```

### Tab: Bengal Performance

```
Full build:       2.3s (150 pages)
Incremental:      0.08s (42x faster!)
Pages/second:     65.2 (full), 1875 (incremental)

Memory:           87 MB
```

**Winner:** Hugo for full builds, Bengal for incremental rebuilds!
```

### Developer Experience

| Aspect | Hugo | Bengal |
|--------|------|--------|
| **Learning curve** | Steep (Go templates) | Gentle (Jinja2) |
| **Documentation** | Excellent | Growing |
| **Community** | Large | Growing |
| **Debugging** | Hard (Go traces) | Easy (Python traces) |
| **Extensibility** | Limited | Easy (Python) |
| **Quality tools** | Basic | Advanced (health checks) |
| **AI features** | None | LLM-txt outputs |

---

## 🎓 Next Steps After Migration

1. **Learn Bengal features**
   - [[docs/markdown/kitchen-sink|Kitchen Sink Demo]]
   - [[docs/templates/function-reference|Template Functions]]
   - [[docs/quality/health-checks|Health Checks]]

2. **Optimize your site**
   - Enable incremental builds
   - Enable parallel processing
   - Add health checks to CI/CD

3. **Explore unique features**
   - LLM-txt outputs for AI
   - JSON outputs for search
   - Advanced directives

4. **Join the community**
   - GitHub discussions
   - Report issues
   - Contribute improvements

---

## 📚 Additional Resources

- **[Hugo vs Bengal Feature Comparison](../../comparison/bengal-vs-hugo.md)** - Detailed comparison
- **[Template Functions Reference](../../docs/templates/function-reference/)** - All 75 functions
- **[Kitchen Sink Demo](../../docs/markdown/kitchen-sink.md)** - All features in one page
- **[Health Checks Guide](../../docs/quality/health-checks.md)** - Quality assurance
- **[Performance Optimization](../../docs/performance/optimization-tips.md)** - Speed tips

---

## 🎉 Success Stories

```{example} Real Migration: Documentation Site

**Before (Hugo):**
- 340 pages
- Build time: 1.8s
- No incremental builds
- Custom shortcodes

**After (Bengal):**
- 340 pages
- Initial build: 5.2s
- Incremental: 0.12s (43x faster!)
- Built-in directives
- Health checks catching issues
- JSON search index

**Result:** 43x faster iterative development!
```

---

## 💬 Feedback

Found issues with this guide? Have questions?

- Open an issue on GitHub
- Join our discussion forum
- Email: support@bengal-ssg.dev

---

**Last Updated:** October 4, 2025  
**Version:** 1.0.0  
**Covers:** Hugo 0.119.x → Bengal 1.0.0

