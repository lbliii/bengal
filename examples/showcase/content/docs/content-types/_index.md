---
title: Content Types
description: Different page layouts and content formats in Bengal
type: doc
weight: 30
cascade:
  type: doc
tags: ["content-types", "layouts", "templates"]
---

# Content Types

Bengal supports different content types, each with its own layout and features. Choose the right type for your content.

## What Are Content Types?

Content types determine how pages are rendered:

- **Template selection** - Which template renders the page
- **Layout features** - Sidebar, TOC, navigation
- **Metadata fields** - Type-specific frontmatter
- **URL structure** - How pages are organized

Set the type in frontmatter:

```yaml
---
title: My Page
type: doc  # Content type
---
```

## Available Types

| Type | Purpose | Features |
|------|---------|----------|
| **[page](pages.md)** | Standard pages | Simple prose layout |
| **[post](blog-posts.md)** | Blog posts | Hero images, tags, dates |
| **[doc](documentation.md)** | Documentation | Sidebar nav, TOC, breadcrumbs |
| **[tutorial](tutorials.md)** | Tutorials | Step-by-step structure |

## Choosing a Type

### Use `page` For

- About pages
- Contact pages
- Landing pages
- Simple content pages

```yaml
---
title: About Us
type: page
---
```

### Use `post` For

- Blog articles
- News updates
- Announcements
- Time-based content

```yaml
---
title: Latest Updates
type: post
date: 2025-10-11
tags: ["news", "updates"]
---
```

### Use `doc` For

- Technical documentation
- Guides and references
- API documentation
- Knowledge base articles

```yaml
---
title: Installation Guide
type: doc
weight: 10
---
```

### Use `tutorial` For

- Step-by-step guides
- Learning paths
- How-to articles
- Educational content

```yaml
---
title: Python Basics
type: tutorial
difficulty: beginner
---
```

## Type-Specific Features

### Page (Standard)

**Layout:** Simple prose content

**Features:**
- Clean, minimal layout
- Optional TOC
- Basic navigation

**Use for:** General content

### Post (Blog)

**Layout:** Blog post with metadata

**Features:**
- Hero images
- Author information
- Publication date
- Tags and categories
- Reading time
- Related posts

**Use for:** Time-based articles

### Doc (Documentation)

**Layout:** Documentation with navigation

**Features:**
- Documentation sidebar
- Table of contents sidebar
- Breadcrumb navigation
- Previous/next page links
- Section organization

**Use for:** Technical content

### Tutorial (Educational)

**Layout:** Step-by-step guide

**Features:**
- Prerequisites section
- Difficulty levels
- Duration estimates
- Progress indicators
- Next steps

**Use for:** Learning content

## Template Hierarchy

Bengal chooses templates in this order:

1. **Explicit template** - From frontmatter `template:` field
2. **Type template** - Based on `type:` field (e.g., `doc/single.html`)
3. **Default template** - Falls back to `page.html`

**Example:**

```yaml
---
title: Special Page
type: doc
template: custom-doc.html  # Override default doc template
---
```

## Type Conventions

### Naming

Use lowercase, hyphenated type names:

```yaml
✅ Good:
type: doc
type: blog-post
type: tutorial

❌ Avoid:
type: Doc
type: BlogPost
type: TUTORIAL
```

### Consistency

Use the same type for similar content:

```
content/docs/
├── guide-1.md      # type: doc
├── guide-2.md      # type: doc
└── guide-3.md      # type: doc
```

## Custom Types

You can create custom types by adding templates:

1. **Create template** - `templates/custom-type/single.html`
2. **Use in frontmatter** - `type: custom-type`
3. **Template applied** - Bengal uses your custom template

See theme documentation for creating custom templates.

## Quick Start

### Create a Blog Post

```markdown
---
title: My First Post
type: post
date: 2025-10-11
author: Jane Doe
tags: ["tutorial", "beginner"]
hero_image: /assets/images/hero.jpg
---

# My First Post

Content here...
```

### Create Documentation

```markdown
---
title: Getting Started
type: doc
weight: 1
toc: true
---

# Getting Started

Documentation content...
```

### Create a Tutorial

```markdown
---
title: Python Basics
type: tutorial
difficulty: beginner
duration: 30
---

# Python Basics

Tutorial content...
```

## Browse Content Types

Learn more about each type:

- **[Standard Pages](pages.md)** - Simple content pages
- **[Blog Posts](blog-posts.md)** - Articles and news
- **[Documentation](documentation.md)** - Technical docs
- **[Tutorials](tutorials.md)** - Educational guides

## Next Steps

- **[Frontmatter Guide](../writing/frontmatter-guide.md)** - Page metadata
- **[Content Organization](../writing/content-organization.md)** - Site structure
- **[Templates](../templates/)** - Template documentation

## Related

- [Writing Guide](../writing/) - Content creation basics
- [Directives](../directives/) - Rich content features
- [Advanced Features](../advanced/) - Power user tips

