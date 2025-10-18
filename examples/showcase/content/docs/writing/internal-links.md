---
title: Internal Links
description: Cross-reference pages with markdown links and Bengal's cross-reference syntax
type: doc
weight: 6
tags: ["links", "cross-references", "navigation"]
toc: true
---

# Internal Links

**Purpose**: Link pages together using markdown links and Bengal's powerful cross-reference syntax.

## What You'll Learn

- Create basic markdown links
- Use cross-reference syntax `[[page]]`
- Link to sections and subsections
- Add anchor links within pages
- Choose between relative and absolute paths

## Basic Markdown Links

Link to other pages using standard markdown:

```markdown
See the [getting started guide](getting-started.md).
Read more in the [frontmatter guide](frontmatter-guide.md).
```

### Relative Paths

Link to pages in the same directory:

```markdown
[Same directory](other-page.md)
[Parent directory](../parent-page.md)
[Subdirectory](subdir/page.md)
```

### Absolute Paths

Link from the site root with `/`:

```markdown
[About page](/about/)
[Blog posts](/blog/)
[Docs](/docs/writing/getting-started/)
```

```{tip} Relative vs Absolute
Use relative links for nearby pages (same section). Use absolute links for pages in different sections.
```

## Cross-Reference Syntax

Bengal's special `[[page]]` syntax for easy cross-referencing:

```markdown
See [[getting-started]] for basics.
Learn about [[frontmatter-guide]].
Check out [[content-organization]].
```

**Advantages:**
- No need to remember file extensions
- Automatically resolves page URLs
- Works across sections
- Less typing than full paths

### How It Works

```markdown
[[page-slug]]          → Finds page by slug
[[section/page]]       → Finds page in section
[[page|Custom Text]]   → Custom link text (if supported)
```

**Examples:**

```markdown
Start with [[getting-started]].
Read about [[directives/admonitions]].
See [[content-types/blog-posts]] for blog help.
```

## Linking to Sections

Link to section index pages:

```markdown
Browse the [writing guide](/docs/writing/).
Check out the [[directives]] section.
Explore [[content-types]].
```

Section `_index.md` files create the section homepage at `/section/`.

## Anchor Links

Link to specific headings within pages:

### Creating Anchors

Headings automatically become anchors:

```markdown
## Installation Steps

Link to this: [installation steps](#installation-steps)
```

Bengal converts headings to URL-safe slugs:
- `## Installation Steps` → `#installation-steps`
- `## API Reference` → `#api-reference`
- `## FAQ: Common Questions` → `#faq-common-questions`

### Linking to Anchors

**Same page:**

```markdown
Jump to [best practices](#best-practices).
See [examples](#examples) below.
```

**Other pages:**

```markdown
See [installation steps](/docs/getting-started/#installation-steps).
Check [markdown basics](markdown-basics.md#headings).
```

**With cross-references:**

```markdown
[[getting-started#prerequisites]]
[[markdown-basics#headings]]
```

## Link Text Best Practices

### Good Link Text

```markdown
✅ Learn more in the [getting started guide](getting-started.md).
✅ See our [installation instructions](/docs/install/).
✅ Read about [content organization](content-organization.md).
```

### Poor Link Text

```markdown
❌ Click [here](getting-started.md) to get started.
❌ Read more [here](/docs/).
❌ [Link](page.md)
```

**Why it matters:**
- Better accessibility for screen readers
- Better SEO (descriptive link text)
- Easier to scan
- More context for readers

### Link Text Patterns

```markdown
# Action-oriented
[Create your first page](getting-started.md)
[Configure your site](../configuration.md)

# Descriptive
Learn about [content organization](content-organization.md)
See the [markdown syntax guide](markdown-basics.md)

# Contextual
Read the [frontmatter guide](frontmatter-guide.md) for metadata options
Check [advanced features](../advanced/) for power user tips
```

## Common Link Patterns

### Next Steps

```markdown
## Next Steps

Ready to continue? Check out these guides:

- [Markdown Basics](markdown-basics.md) - Essential syntax
- [Content Organization](content-organization.md) - Structure your site
- [Frontmatter Guide](frontmatter-guide.md) - Page metadata
```

### Related Content

```markdown
## Related

- [Getting Started](getting-started.md)
- [Internal Links](internal-links.md)
- [Images and Assets](images-and-assets.md)
```

### Inline References

```markdown
Bengal supports multiple [content types](../content-types/), including documentation pages, blog posts, and tutorials.

You can customize page behavior with [frontmatter](frontmatter-guide.md).
```

### Navigation Hints

```markdown
See the [[getting-started]] guide to create your first page.

For advanced features, explore:
- [[advanced/variables]] - Variable substitution
- [[advanced/taxonomies]] - Tags and categories
- [[advanced/navigation]] - Menu configuration
```

## Linking Examples

### Tutorial Navigation

```markdown
← Previous: [Markdown Basics](markdown-basics.md) | Next: [Images and Assets](images-and-assets.md) →
```

### Table of Contents

```markdown
## In This Guide

1. [Installation](#installation)
2. [Configuration](#configuration)
3. [Usage](#usage)
4. [Troubleshooting](#troubleshooting)
```

### Cross-Section Links

```markdown
This guide assumes you've completed [[getting-started]].

For more information, see:
- [[directives/admonitions]] - Callout boxes
- [[content-types/documentation]] - Doc pages
- [[advanced/seo]] - SEO optimization
```

## Link Validation

Bengal can validate links during builds:

```bash
# Build with link validation
bengal site build

# Health check includes link validation
# Broken links appear in health report
```

**Common issues:**

```{warning} Link Problems
- **Broken links**: Page doesn't exist
- **Case sensitivity**: `Page.md` vs `page.md`
- **Missing anchors**: `#heading` doesn't exist
- **External redirects**: External URL changed
```

## Testing Links

Always test your links:

```bash
# Start dev server
bengal site serve

# Navigate to your pages
# Click all links to verify they work
```

```{tip} Development Workflow
Use `bengal site serve` with live reload. When you save changes, the site rebuilds automatically and you can test links immediately.
```

## Best Practices Summary

```{success} Link Best Practices
1. **Use descriptive text** - Not "click here"
2. **Test all links** - Use dev server to verify
3. **Use cross-references** - Simpler than full paths
4. **Be consistent** - Choose one style and stick to it
5. **Check case** - Filenames are case-sensitive
6. **Use relative paths** for nearby pages
7. **Use absolute paths** for distant pages
8. **Add anchors** for long pages
```

## Common Mistakes

### Wrong Paths

```markdown
# ❌ Wrong (no extension)
[Guide](getting-started)

# ✅ Correct
[Guide](getting-started.md)
```

### Case Sensitivity

```markdown
# ❌ Wrong (incorrect case)
[Guide](Getting-Started.md)

# ✅ Correct
[Guide](getting-started.md)
```

### Missing Leading Slash

```markdown
# ❌ Wrong (relative but meant absolute)
[Docs](docs/getting-started/)

# ✅ Correct (absolute)
[Docs](/docs/getting-started/)
```

## Advanced: Dynamic Links

Use variable substitution for dynamic links:

```markdown
---
github_repo: "https://github.com/user/repo"
---

View the source on [GitHub]({{ page.metadata.github_repo }}).
```

See [[advanced/variables]] for more on variable substitution.

## Quick Reference

| Link Type | Syntax | Example |
|-----------|--------|---------|
| Relative | `[text](file.md)` | `[Guide](getting-started.md)` |
| Absolute | `[text](/path/)` | `[Docs](/docs/)` |
| Cross-ref | `[[page]]` | `[[getting-started]]` |
| Anchor | `[text](#anchor)` | `[Top](#introduction)` |
| Section | `[[section/page]]` | `[[docs/guide]]` |
| External | `[text](url)` | `[Bengal](https://bengal-ssg.org)` |

## Next Steps

Master internal linking, then explore:

- **[External Links](external-links.md)** - Link to external resources
- **[Images and Assets](images-and-assets.md)** - Add media to content
- **[Navigation](../advanced/navigation.md)** - Configure site menus
- **[Content Organization](content-organization.md)** - Structure your site

## Related

- [Getting Started](getting-started.md) - Create your first page
- [Markdown Basics](markdown-basics.md) - Essential syntax
- [Content Organization](content-organization.md) - Site structure
