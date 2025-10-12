---
title: Frontmatter Guide
description: Essential page metadata for content organization
type: doc
weight: 5
tags: ["frontmatter", "metadata", "configuration"]
toc: true
---

# Frontmatter Guide

**Purpose**: Master frontmatter to control page behavior, SEO, and organization.

## What You'll Learn

- Understand frontmatter basics
- Use essential fields effectively
- Control page behavior
- Optimize for SEO
- Customize page metadata

## What is Frontmatter?

Frontmatter is metadata at the top of your markdown files, written in YAML:

```markdown
---
title: My Page Title
description: A brief summary
date: 2025-10-11
tags: ["guide", "tutorial"]
---

# My Page Title

Content starts here...
```

**Key points:**
- Surrounded by `---` delimiters
- Uses YAML syntax
- Must be at the very top of the file
- Controls page behavior and metadata

## Essential Fields

### title (Required)

The page title used in navigation, SEO, and display:

```yaml
---
title: Getting Started with Bengal
---
```

**Best practices:**
- Keep under 60 characters for SEO
- Make it descriptive and clear
- Use title case or sentence case consistently
- Avoid generic titles like "Page 1"

### description (Recommended)

Short summary for SEO and previews:

```yaml
---
title: Getting Started
description: Learn to create your first Bengal site in under 10 minutes
---
```

**Best practices:**
- Aim for 120-160 characters
- Include target keywords naturally
- Make it compelling (users see this in search results)
- Describe what readers will learn or gain

### date

Publication or last updated date:

```yaml
---
title: My Blog Post
date: 2025-10-11
---
```

**Formats supported:**
- `2025-10-11` (YYYY-MM-DD)
- `2025-10-11T14:30:00` (with time)
- `2025-10-11T14:30:00Z` (with timezone)

**Used for:**
- Sorting posts chronologically
- Displaying publication dates
- RSS feed ordering
- Archive pages

## Organization Fields

### tags

Categorize content with tags:

```yaml
---
title: Python Tutorial
tags: ["python", "tutorial", "beginner"]
---
```

**Best practices:**
- Use 3-7 tags per page
- Use lowercase, hyphenated slugs
- Be consistent across similar content
- Use specific tags ("python-basics" not just "tutorial")

### type

Content type for template selection:

```yaml
---
title: My Documentation Page
type: doc
---
```

**Common types:**
- `page` - Standard page (default)
- `post` - Blog post
- `doc` - Documentation page
- `tutorial` - Tutorial page
- `api-reference` - API documentation

See [Content Types](../content-types/) for details on each type.

### weight

Control sort order (lower numbers appear first):

```yaml
---
title: Introduction
weight: 1
---
```

```yaml
---
title: Advanced Topics
weight: 100
---
```

**Use cases:**
- Order tutorial steps
- Prioritize important pages
- Override alphabetical sorting
- Control navigation order

### draft

Mark pages as drafts (not published):

```yaml
---
title: Work in Progress
draft: true
---
```

Draft pages:
- Don't appear in production builds
- Visible in development with `--drafts` flag
- Useful for work-in-progress content
- Omit or set to `false` to publish

## SEO Fields

### author

Specify the content author:

```yaml
---
title: Python Best Practices
author: Jane Developer
---
```

**Used for:**
- Blog post bylines
- SEO metadata
- Author pages/archives
- RSS feeds

### keywords

SEO keywords (optional, tags are usually sufficient):

```yaml
---
title: Python Tutorial
keywords: ["python programming", "learn python", "python basics"]
---
```

```{tip} Tags vs Keywords
In Bengal, tags serve as keywords. You typically don't need a separate keywords field.
```

### canonical_url

Specify canonical URL for duplicate content:

```yaml
---
title: Republished Article
canonical_url: "https://originalsource.com/article/"
---
```

## Layout and Display

### template

Override the default template:

```yaml
---
title: Special Landing Page
template: custom-landing.html
---
```

```yaml
---
title: Product Page
type: page
template: product-page.html
---
```

### toc

Control table of contents display:

```yaml
---
title: Long Guide
toc: true   # Show TOC
---
```

```yaml
---
title: Short Page
toc: false  # Hide TOC
---
```

### show_children

Control child page tiles on section indexes:

```yaml
---
title: Documentation
type: doc
show_children: true  # Show child page tiles (default)
---
```

```yaml
---
title: Custom Section Page
show_children: false  # Hide auto-generated child tiles
---
```

## Blog-Specific Fields

### hero_image

Feature image for blog posts:

```yaml
---
title: My Blog Post
hero_image: /assets/images/hero.jpg
---
```

### excerpt

Custom excerpt (otherwise auto-generated):

```yaml
---
title: My Post
excerpt: "This is a custom summary that appears in post lists and previews."
---
```

### categories

Blog categories (similar to tags but hierarchical):

```yaml
---
title: Python Web Development
categories: ["Programming", "Web Development"]
tags: ["python", "flask", "tutorial"]
---
```

## Advanced Fields

### cascade

Apply metadata to all descendant pages:

```yaml
---
title: API Documentation
type: api-reference
cascade:
  type: api-reference
  show_toc: true
  author: API Team
---
```

Place in section `_index.md` to affect all pages in that section.

### aliases

Create redirect URLs:

```yaml
---
title: New Page Location
aliases:
  - /old-location/
  - /another-old-path/
---
```

### url

Override the automatic URL:

```yaml
---
title: Special Page
url: /custom/path/
---
```

```{warning} Custom URLs
Only override URLs when necessary. Automatic URLs are usually better for organization.
```

## Complete Examples

### Blog Post

```yaml
---
title: Getting Started with Python
description: A comprehensive guide for Python beginners
date: 2025-10-11
author: Jane Developer
type: post
tags: ["python", "tutorial", "beginner"]
hero_image: /assets/images/python-guide.jpg
toc: true
---
```

### Documentation Page

```yaml
---
title: Installation Guide
description: How to install and configure Bengal SSG
type: doc
weight: 10
tags: ["installation", "getting-started"]
toc: true
---
```

### Section Index

```yaml
---
title: Writing Guide
description: Learn to create content with Bengal
type: doc
weight: 10
show_children: true
cascade:
  type: doc
---
```

### Landing Page

```yaml
---
title: Welcome to My Site
description: Discover amazing content about web development
template: landing.html
toc: false
---
```

## YAML Syntax Tips

### Strings

```yaml
# Simple strings (no quotes needed)
title: My Page Title

# Strings with special characters (use quotes)
title: "Title: with colon"
description: 'Title with "quotes"'

# Multi-line strings
description: >
  This is a long description
  that spans multiple lines.
```

### Lists

```yaml
# Inline list
tags: ["python", "tutorial"]

# Block list
tags:
  - python
  - tutorial
  - beginner
```

### Booleans

```yaml
draft: true
toc: false
show_children: true
```

### Numbers

```yaml
weight: 10
reading_time: 5
```

## Common Mistakes

```{warning} Avoid These Issues
```

**Missing delimiters:**
```yaml
# ❌ Wrong (missing closing ---)
---
title: My Page

# Content here
```

```yaml
# ✅ Correct
---
title: My Page
---

# Content here
```

**Invalid YAML:**
```yaml
# ❌ Wrong (indentation matters)
---
tags:
- python
  - tutorial
---
```

```yaml
# ✅ Correct
---
tags:
  - python
  - tutorial
---
```

**Special characters:**
```yaml
# ❌ Wrong (unquoted colon)
title: Note: Important Information

# ✅ Correct
title: "Note: Important Information"
```

## Field Reference

Quick reference of all common fields:

| Field | Type | Purpose |
|-------|------|---------|
| `title` | string | Page title (required) |
| `description` | string | SEO and preview summary |
| `date` | date | Publication date |
| `tags` | list | Content tags |
| `type` | string | Content type |
| `weight` | number | Sort order |
| `draft` | boolean | Draft status |
| `author` | string | Content author |
| `toc` | boolean | Show table of contents |
| `template` | string | Custom template |
| `hero_image` | string | Feature image path |
| `canonical_url` | string | Canonical URL |
| `show_children` | boolean | Show child page tiles |

See [Frontmatter Standard](../frontmatter-standard.md) for complete reference.

## Next Steps

Master frontmatter, then move on to:

- **[Content Organization](content-organization.md)** - Structure your site
- **[SEO](../advanced/seo.md)** - Optimize for search engines
- **[Content Types](../content-types/)** - Different layouts
- **[Taxonomies](../advanced/taxonomies.md)** - Tags and categories

## Related

- [Getting Started](getting-started.md) - Create your first page
- [Blog Posts](../content-types/blog-posts.md) - Blog-specific frontmatter
- [Documentation](../content-types/documentation.md) - Doc-specific frontmatter
