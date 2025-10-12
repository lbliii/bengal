---
title: Content Organization
description: Structure your site with sections, pages, and hierarchies
type: doc
weight: 4
tags: ["organization", "structure", "sections"]
toc: true
---

# Content Organization

**Purpose**: Learn to organize your content with sections, subsections, and effective hierarchies.

## What You'll Learn

- Understand directory structure and URLs
- Create sections and subsections
- Use index pages effectively
- Choose between flat and nested structures
- Organize content for growth

## Directory Structure Basics

Your content lives in the `content/` directory. The directory structure determines your site's URL structure:

```
content/
├── _index.md              → / (homepage)
├── about.md               → /about/
├── contact.md             → /contact/
├── blog/
│   ├── _index.md         → /blog/
│   ├── first-post.md     → /blog/first-post/
│   └── second-post.md    → /blog/second-post/
└── docs/
    ├── _index.md         → /docs/
    ├── getting-started.md → /docs/getting-started/
    └── advanced/
        ├── _index.md     → /docs/advanced/
        └── features.md   → /docs/advanced/features/
```

**Key principle:** Directory structure = URL structure

## Pages vs Sections

### Regular Pages

Regular pages are single markdown files:

```
content/about.md           → /about/
content/contact.md         → /contact/
content/privacy.md         → /privacy/
```

Use regular pages for:
- Standalone content (About, Contact)
- Single-topic pages
- Landing pages

### Sections

Sections are directories that group related pages:

```
content/blog/
├── _index.md             # Section index page
├── post-1.md
├── post-2.md
└── post-3.md
```

Use sections for:
- Collections of related content
- Blog posts
- Documentation chapters
- Product categories

## Index Pages

Every section needs an `_index.md` file:

```markdown
---
title: Blog
description: Latest posts and articles
type: blog
---

# Blog

Welcome to my blog! Here's where I share thoughts on web development.
```

**What `_index.md` does:**

1. **Provides section metadata** - Title, description
2. **Creates the section homepage** - Content at `/blog/`
3. **Controls section behavior** - Templates, cascade settings
4. **Lists child pages** - Automatically in many themes

```{tip} Always Create _index.md
Even if empty, `_index.md` is required for sections. It defines the section's homepage.
```

## URL Structure

Bengal automatically generates clean URLs:

| File Path | URL | Page Type |
|-----------|-----|-----------|
| `content/_index.md` | `/` | Homepage |
| `content/about.md` | `/about/` | Page |
| `content/blog/_index.md` | `/blog/` | Section index |
| `content/blog/hello.md` | `/blog/hello/` | Page in section |
| `content/docs/guide.md` | `/docs/guide/` | Page in section |

**Note:** All URLs end with `/` for consistency and SEO.

## Nested Sections

Create hierarchies with subsections:

```
content/docs/
├── _index.md                    → /docs/
├── getting-started.md           → /docs/getting-started/
├── basics/
│   ├── _index.md               → /docs/basics/
│   ├── installation.md         → /docs/basics/installation/
│   └── configuration.md        → /docs/basics/configuration/
└── advanced/
    ├── _index.md               → /docs/advanced/
    ├── caching.md              → /docs/advanced/caching/
    └── performance/
        ├── _index.md           → /docs/advanced/performance/
        └── optimization.md     → /docs/advanced/performance/optimization/
```

**Hierarchy features:**

- Breadcrumb navigation automatically generated
- Parent/child relationships for navigation
- Metadata inheritance with cascade
- Clean logical grouping

## Choosing Structure: Flat vs Nested

### Flat Structure

Good for small sites or simple content:

```
content/
├── _index.md
├── about.md
├── services.md
├── portfolio.md
├── blog.md
└── contact.md
```

**Pros:**
- Simple to understand
- Easy to navigate
- Fast to set up

**Cons:**
- Hard to scale
- No grouping
- Limited organization

### Nested Structure

Good for larger sites or complex content:

```
content/
├── _index.md
├── about/
│   ├── _index.md
│   ├── team.md
│   └── history.md
├── products/
│   ├── _index.md
│   ├── product-a.md
│   └── product-b.md
└── docs/
    ├── _index.md
    ├── guides/
    └── reference/
```

**Pros:**
- Scales well
- Logical grouping
- Better navigation

**Cons:**
- More setup
- Deeper URLs
- More complex

## Organization Patterns

### Blog Organization

**By date:**

```
content/blog/
├── _index.md
├── 2025/
│   ├── 01/
│   │   └── new-year-post.md
│   └── 02/
│       └── february-update.md
```

**By topic:**

```
content/blog/
├── _index.md
├── web-development/
│   ├── _index.md
│   └── posts...
└── design/
    ├── _index.md
    └── posts...
```

**Flat (recommended):**

```
content/blog/
├── _index.md
├── post-1.md
├── post-2.md
└── post-3.md
```

Use frontmatter dates and tags for organization instead of directories.

### Documentation Organization

**By feature:**

```
content/docs/
├── _index.md
├── installation/
├── configuration/
├── content-creation/
└── deployment/
```

**By skill level:**

```
content/docs/
├── _index.md
├── beginner/
├── intermediate/
└── advanced/
```

**By topic (recommended):**

```
content/docs/
├── _index.md
├── getting-started.md
├── writing/
├── directives/
├── content-types/
└── advanced/
```

### E-commerce Organization

```
content/
├── _index.md
├── products/
│   ├── _index.md
│   ├── category-1/
│   │   ├── _index.md
│   │   ├── product-a.md
│   │   └── product-b.md
│   └── category-2/
│       └── ...
├── guides/
└── support/
```

## Best Practices

### 1. Keep URLs Clean

```
✅ Good:
content/docs/getting-started.md → /docs/getting-started/
content/blog/python-tips.md     → /blog/python-tips/

❌ Avoid:
content/docs/docs-getting-started.md → /docs/docs-getting-started/
content/blog/2025-01-01-post.md     → /blog/2025-01-01-post/
```

### 2. Use Descriptive Names

```
✅ Good:
content/installation-guide.md
content/api-reference.md
content/troubleshooting.md

❌ Avoid:
content/page1.md
content/doc.md
content/temp.md
```

### 3. Limit Nesting Depth

```
✅ Good (2-3 levels):
content/docs/advanced/caching.md

❌ Avoid (too deep):
content/docs/reference/api/v2/endpoints/users/details.md
```

Aim for 2-3 levels max. Deeper hierarchies are hard to navigate.

### 4. Group Related Content

```
✅ Good:
content/tutorials/
├── _index.md
├── beginner-tutorial.md
├── intermediate-tutorial.md
└── advanced-tutorial.md

❌ Scattered:
content/beginner-tutorial.md
content/guide-2.md
content/advanced-stuff.md
```

### 5. Plan for Growth

Start simple, add structure as you grow:

```
Phase 1 (Launch):
content/
├── _index.md
├── about.md
└── blog/

Phase 2 (Growth):
content/
├── _index.md
├── about/
├── blog/
└── docs/

Phase 3 (Mature):
content/
├── _index.md
├── about/
├── blog/
├── docs/
├── tutorials/
└── api/
```

## Navigation Considerations

Your content structure affects navigation:

### Breadcrumbs

Breadcrumbs follow the directory structure:

```
/docs/advanced/caching/
↓
Home > Docs > Advanced > Caching
```

### Sidebars

Documentation sidebars reflect hierarchy:

```
Docs
├── Getting Started
├── Basics
│   ├── Installation
│   └── Configuration
└── Advanced
    ├── Caching
    └── Performance
```

### Menus

Section structure doesn't require matching menu structure. Configure menus independently in `bengal.toml`.

## Real-World Example

Here's a complete site structure:

```
content/
├── _index.md                      # Homepage
├── about.md                       # About page
├── blog/                          # Blog section
│   ├── _index.md
│   ├── first-post.md
│   ├── second-post.md
│   └── third-post.md
├── docs/                          # Documentation
│   ├── _index.md
│   ├── getting-started.md
│   ├── writing/
│   │   ├── _index.md
│   │   ├── basics.md
│   │   └── advanced.md
│   └── directives/
│       ├── _index.md
│       └── admonitions.md
└── tutorials/                     # Tutorials
    ├── _index.md
    ├── beginner-tutorial.md
    └── advanced-tutorial.md
```

## Next Steps

Now that you understand content organization:

- **[Frontmatter Guide](frontmatter-guide.md)** - Configure page metadata
- **[Internal Links](internal-links.md)** - Link between pages
- **[Navigation](../advanced/navigation.md)** - Configure menus
- **[Content Types](../content-types/)** - Different layouts for different content

## Related

- [Getting Started](getting-started.md) - Create your first page
- [Blog Posts](../content-types/blog-posts.md) - Writing blog content
- [Documentation](../content-types/documentation.md) - Creating docs
