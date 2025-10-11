---
title: Standard Pages
description: Simple content pages for about, contact, and general content
type: doc
weight: 1
tags: ["content-types", "pages"]
toc: true
---

# Standard Pages

**Purpose**: Create simple, general-purpose content pages.

## What You'll Learn

- Create standard content pages
- Use the page layout
- Add common page elements
- Best practices for simple pages

## When to Use

Use standard pages for:

- **About pages** - Company/project information
- **Contact pages** - Contact forms and information
- **Landing pages** - Simple promotional pages
- **Legal pages** - Privacy, terms of service
- **Simple content** - Any general prose content

## Basic Structure

```markdown
---
title: About Us
description: Learn about our company and mission
type: page
---

# About Us

We're a team dedicated to building great software.

## Our Mission

Making static sites easy for everyone.

## Our Team

Meet the people behind the project...
```

## Page Features

### Simple Layout

- Clean, minimal design
- Centered prose content
- Optional table of contents
- Basic navigation

### Supported Elements

- All markdown formatting
- Images and media
- Directives (admonitions, tabs, etc.)
- Internal and external links

## Common Page Types

### About Page

```markdown
---
title: About
description: Learn about Bengal SSG
type: page
---

# About Bengal

Bengal is a modern static site generator...

## History

Started in 2024...

## Team

Our contributors...
```

### Contact Page

```markdown
---
title: Contact
description: Get in touch with us
type: page
---

# Contact Us

Have questions? We'd love to hear from you!

## Email

contact@example.com

## Social Media

- Twitter: @username
- GitHub: github.com/username
```

### Landing Page

```markdown
---
title: Welcome
description: Welcome to our site
type: page
template: landing.html
---

# Welcome to Our Site

Discover amazing content...

```{button} Get Started
:link: /docs/
:type: primary
```
```

## Quick Reference

**Standard page:**
```yaml
---
title: Page Title
type: page
---

# Content here
```

## Next Steps

- **[Blog Posts](blog-posts.md)** - Time-based articles
- **[Documentation](documentation.md)** - Technical docs
- **[Frontmatter Guide](../writing/frontmatter-guide.md)** - Metadata

## Related

- [Content Types Overview](index.md) - All types
- [Getting Started](../writing/getting-started.md) - Create pages
- [Markdown Basics](../writing/markdown-basics.md) - Formatting

