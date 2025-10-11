---
title: Documentation Pages
description: Create technical documentation with navigation and TOC
type: doc
weight: 3
tags: ["content-types", "documentation", "technical-writing"]
toc: true
---

# Documentation Pages

**Purpose**: Create technical documentation with rich navigation features.

## What You'll Learn

- Create documentation pages
- Use doc-specific features
- Organize documentation structure
- Enable navigation aids

## When to Use

Use documentation type for:

- **Technical guides** - Installation, configuration
- **API references** - Function and class docs
- **User manuals** - How-to guides
- **Knowledge base** - Support articles

## Basic Structure

```markdown
---
title: Installation Guide
description: How to install and configure Bengal
type: doc
weight: 10
toc: true
---

# Installation Guide

Follow these steps to install Bengal...

## Prerequisites

## Installation Steps

## Configuration

## Troubleshooting
```

## Doc-Specific Features

### Documentation Sidebar

- Hierarchical section navigation
- Auto-generated from directory structure
- Active page highlighting
- Expand/collapse sections

### Table of Contents Sidebar

- Extracted from page headings
- H2-H4 headings included
- Jump-to-section links
- Reading progress indicator

### Breadcrumb Navigation

- Shows current location
- Click to navigate up hierarchy
- Auto-generated from structure

### Sequential Navigation

- Previous/next page links
- Based on weight or alphabetical order
- Appears at bottom of page

## Doc-Specific Frontmatter

### weight

Control document ordering:

```yaml
---
weight: 10  # Lower numbers appear first
---
```

**Example ordering:**
```
getting-started.md  (weight: 1)
installation.md     (weight: 10)
configuration.md    (weight: 20)
advanced.md         (weight: 100)
```

### toc

Enable table of contents:

```yaml
---
toc: true   # Show TOC
---
```

### show_children

Control child page tiles on index pages:

```yaml
---
show_children: true  # Show child page tiles (default)
---
```

## Documentation Structure

### Recommended Organization

```
content/docs/
├── _index.md                 # Docs homepage
├── getting-started.md        # weight: 1
├── basics/
│   ├── _index.md
│   ├── installation.md       # weight: 10
│   └── configuration.md      # weight: 20
├── guides/
│   ├── _index.md
│   ├── content-creation.md
│   └── deployment.md
└── advanced/
    ├── _index.md
    ├── caching.md
    └── performance.md
```

### Section Index Pages

Every section needs `_index.md`:

```markdown
---
title: Basics
description: Fundamental concepts and setup
type: doc
weight: 10
---

# Basics

Learn the fundamentals of Bengal...
```

## Complete Example

```markdown
---
title: Configuration Guide
description: Complete guide to configuring Bengal
type: doc
weight: 20
toc: true
tags: ["configuration", "setup"]
---

# Configuration Guide

Bengal uses `bengal.toml` for configuration.

## Basic Configuration

Create `bengal.toml` in your project root:

\`\`\`toml
[site]
title = "My Site"
baseurl = "https://example.com"
\`\`\`

## Site Options

### title

Your site's title...

### baseurl

Base URL for your site...

## Build Options

Configure build behavior:

\`\`\`toml
[build]
parallel = true
incremental = true
\`\`\`

## Next Steps

See [Advanced Configuration](../advanced/configuration.md).
```

## Best Practices

### Use Clear Hierarchy

```
✅ Good structure:
docs/
├── getting-started.md      # Top level
├── guides/                 # Second level
│   ├── guide-1.md
│   └── guide-2.md
└── reference/              # Second level
    ├── api.md
    └── cli.md

❌ Too deep:
docs/section1/subsection/subsubsection/page.md
```

### Set Logical Weights

```yaml
✅ Good weights:
getting-started.md    # weight: 1
installation.md       # weight: 10
configuration.md      # weight: 20
advanced-topics.md    # weight: 100

❌ Random weights:
page-1.md    # weight: 47
page-2.md    # weight: 3
page-3.md    # weight: 92
```

### Enable TOC for Long Pages

```yaml
---
title: Comprehensive Guide
toc: true   # Enable for pages with 5+ sections
---
```

## Navigation Features

### Sidebar Navigation

Automatically generated from:
- Directory structure
- Section _index.md files
- Page titles and weights

### Breadcrumbs

Auto-generated path:
```
Home > Docs > Guides > Configuration
```

### Prev/Next Links

Sequential navigation based on weight:
```
← Previous: Installation  |  Next: Deployment →
```

## Cross-Referencing

Link to other docs:

```markdown
See the [installation guide](../getting-started.md).
For advanced options, check [configuration](configuration.md).
Learn about [[deployment]] in the deployment guide.
```

## Quick Reference

**Minimal doc page:**
```yaml
---
title: Page Title
type: doc
---
```

**Complete doc page:**
```yaml
---
title: Page Title
description: Brief summary
type: doc
weight: 10
toc: true
tags: ["tag1", "tag2"]
---
```

## Next Steps

- **[Tutorials](tutorials.md)** - Educational guides
- **[Content Organization](../writing/content-organization.md)** - Structure
- **[Navigation](../advanced/navigation.md)** - Menus and links
- **[Frontmatter Guide](../writing/frontmatter-guide.md)** - Metadata

## Related

- [Content Types Overview](index.md) - All types
- [Writing Guide](../writing/) - Content creation
- [Directives](../directives/) - Rich content features

