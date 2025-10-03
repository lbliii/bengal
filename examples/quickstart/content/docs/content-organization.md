---
title: "Content Organization"
description: "How to organize your content with pages, sections, and index files"
date: 2025-10-03
---

# Content Organization

Learn how to structure your Bengal site with pages, sections, and index files.

## Directory Structure

Bengal discovers content from the `content/` directory:

```
content/
  index.md              # Site homepage
  about.md              # Regular page
  docs/                 # Section
    _index.md           # Section index
    getting-started.md  # Page in section
    advanced/           # Subsection
      _index.md         # Subsection index
      tips.md           # Page in subsection
```

## Pages vs Sections

### Pages

Regular markdown files that become individual pages on your site:

```
content/
  about.md          → /about/
  contact.md        → /contact/
```

### Sections

Directories that group related pages together:

```
content/
  docs/
    page1.md        → /docs/page1/
    page2.md        → /docs/page2/
```

Sections can have subsections, creating a hierarchical structure.

## Index Files: `index.md` vs `_index.md`

Bengal supports two types of index files, and **both work identically**. However, there's a recommended convention:

### `_index.md` - Section Index (Recommended)

**Use for:** Sections that contain child pages or define cascading metadata.

```markdown
# content/docs/_index.md
---
title: "Documentation"
description: "Complete documentation for our product"
cascade:
  version: "2.0"
  product_name: "SuperApp"
---

# Documentation

Welcome to our documentation section.
```

**Why `_index.md`?**
- ✅ Clear intent: "This is a section with children"
- ✅ Matches Hugo convention (easier for Hugo users)
- ✅ Visually distinct from regular `index.md`
- ✅ Perfect for cascading frontmatter

### `index.md` - Standalone Page

**Use for:** Site root or standalone pages without children.

```markdown
# content/index.md
---
title: "Welcome to My Site"
---

# Welcome

This is my awesome website!
```

**Why `index.md`?**
- ✅ Common convention for site homepage
- ✅ Clear for standalone pages
- ✅ Familiar to all web developers

### The Truth: Both Work the Same

Behind the scenes, Bengal treats both identically:

```python
# Both become section index pages
if page.source_path.stem in ("index", "_index"):
    self.index_page = page
    
    # Both support cascade
    if 'cascade' in page.metadata:
        self.metadata['cascade'] = page.metadata['cascade']
```

**Use whichever makes sense for your content!** The convention is just a guideline to help you stay organized.

## Recommended Structure

Here's a clean, conventional structure:

```
content/
  index.md                    # Site homepage (standalone)
  
  blog/
    _index.md                 # Blog section index (has children)
    first-post.md
    second-post.md
  
  docs/
    _index.md                 # Docs section (has cascade)
    getting-started.md
    advanced/
      _index.md               # Subsection with cascade
      tips.md
      tricks.md
  
  api/
    v2/
      _index.md               # API v2 section with cascade
      authentication.md
      users.md
```

## Cascade with Section Indexes

Section index files (`_index.md`) are perfect for defining cascading metadata:

```yaml
# content/docs/v2/_index.md
---
title: "Version 2.0 Documentation"
cascade:
  version: "2.0"
  product_name: "DataFlow API"
  api_base_url: "https://api.example.com/v2"
---

# Version 2.0 Documentation

All child pages inherit version, product_name, and api_base_url!
```

Then in child pages:

```markdown
# content/docs/v2/quickstart.md
---
title: "Quick Start"
---

# Quick Start for DataFlow API

Connect to https://api.example.com/v2 to get started...
```

The variables are automatically replaced during build!

See [Cascading Frontmatter](/docs/cascading-frontmatter/) for more details.

## Content Discovery

Bengal automatically discovers all content files with these extensions:

- `.md` - Markdown (primary)
- `.markdown` - Markdown (alternative)
- `.rst` - reStructuredText
- `.txt` - Plain text

Files and directories starting with `.` or `_` are skipped, **except** for `_index.md` and `_index.markdown`.

## Best Practices

### ✅ Do

- Use `_index.md` for sections with child pages
- Use `index.md` for the site root
- Use cascades in `_index.md` to DRY your metadata
- Group related content in sections
- Use meaningful directory names (they become URLs)

### ❌ Don't

- Mix `index.md` and `_index.md` in the same directory
- Use spaces in directory names (use hyphens: `getting-started`)
- Nest too deeply (3-4 levels max for good UX)
- Put content outside `content/` directory

## Examples

### Blog Structure

```
content/
  blog/
    _index.md                 # Blog landing page
    2025/
      my-first-post.md
      another-post.md
```

### Documentation Structure

```
content/
  docs/
    _index.md                 # Docs home (with cascade)
    getting-started/
      _index.md               # Getting Started section
      installation.md
      configuration.md
    guides/
      _index.md               # Guides section
      deployment.md
      optimization.md
```

### Product Site Structure

```
content/
  index.md                    # Homepage
  products/
    _index.md                 # Products section (with cascade)
    widget-2000.md
    gadget-pro.md
  support/
    _index.md                 # Support section
    faq.md
    contact.md
```

## Navigation

Bengal automatically builds navigation from your content structure:

- **Breadcrumbs** - Generated from section hierarchy
- **Section menus** - Access via `section.pages` and `section.subsections`
- **Site-wide** - All pages accessible via `site.pages`

Example template code for listing pages:

```html
<!-- List all pages in current section -->
<div class="page-list">
  <!-- Use section.pages in your template -->
  <!-- Loop through and display page.title and page.url -->
</div>

<!-- List all subsections -->
<div class="subsection-list">
  <!-- Use section.subsections to access child sections -->
  <!-- Each subsection has its own pages array -->
</div>
```

See [Template System](/docs/template-system/) for complete template variable reference.

## Learn More

- [Cascading Frontmatter](/docs/cascading-frontmatter/) - Inherit metadata across sections
- [Template System](/docs/template-system/) - Access pages and sections in templates
- [Advanced Markdown](/docs/advanced-markdown/) - Markdown features and extensions

---

**Key Takeaway:** Use `_index.md` for sections with children (especially with cascade), and `index.md` for standalone pages. Both work the same in Bengal, but the convention keeps your structure clear!

