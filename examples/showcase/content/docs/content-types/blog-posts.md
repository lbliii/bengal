---
title: Blog Posts
description: Create blog articles with dates, tags, and hero images
type: doc
weight: 2
tags: ["content-types", "blog", "posts"]
toc: true
---

# Blog Posts

**Purpose**: Create time-based blog articles with rich metadata and features.

## What You'll Learn

- Create blog posts
- Use post-specific frontmatter
- Add hero images and metadata
- Organize with tags and categories

## When to Use

Use blog posts for:

- **Articles** - Long-form content
- **News** - Company/project updates
- **Tutorials** - Educational content
- **Announcements** - Important updates
- **Any time-based content**

## Basic Structure

```markdown
---
title: Getting Started with Python
description: A beginner-friendly introduction to Python programming
type: post
date: 2025-10-11
author: Jane Developer
tags: ["python", "tutorial", "beginner"]
hero_image: /assets/images/python-guide.jpg
---

# Getting Started with Python

Python is a versatile programming language perfect for beginners...

## Why Learn Python?

Python's simplicity makes it ideal for...
```

## Post-Specific Frontmatter

### date (Required)

Publication date for chronological ordering:

```yaml
---
date: 2025-10-11
---
```

**Formats:**
- `2025-10-11` (YYYY-MM-DD)
- `2025-10-11T14:30:00` (with time)

### author

Post author:

```yaml
---
author: Jane Developer
---
```

### hero_image

Feature image displayed at top:

```yaml
---
hero_image: /assets/images/hero.jpg
---
```

### tags

Categorize and organize:

```yaml
---
tags: ["python", "tutorial", "beginner"]
---
```

### excerpt

Custom preview text (auto-generated if omitted):

```yaml
---
excerpt: "Learn Python basics in this comprehensive beginner guide."
---
```

## Post Layout Features

### Hero Section

- Large hero image
- Post title overlay
- Author and date display

### Metadata Display

- Publication date
- Author name
- Reading time (auto-calculated)
- Tag list

### Content Area

- Prose typography
- Optimized for reading
- Table of contents (if enabled)

### Post Footer

- Tags
- Related posts
- Social sharing (theme-dependent)
- Author bio (theme-dependent)

## Complete Example

```markdown
---
title: Building Your First Static Site
description: Step-by-step guide to creating a static site with Bengal
type: post
date: 2025-10-11
updated: 2025-10-15
author: Jane Developer
tags: ["tutorial", "beginner", "bengal"]
categories: ["Tutorials", "Web Development"]
hero_image: /assets/images/first-site-hero.jpg
toc: true
---

# Building Your First Static Site

Static sites are making a comeback, and for good reason...

## What You'll Need

Before starting, ensure you have:

- Python 3.8 or higher
- Basic command line knowledge
- A text editor

## Step 1: Installation

Install Bengal with pip:

\`\`\`bash
pip install bengal
\`\`\`

## Step 2: Create Your Site

...
```

## Organizing Blog Posts

### Directory Structure

```
content/blog/
├── _index.md              # Blog section index
├── first-post.md
├── second-post.md
└── third-post.md
```

### Section Index

Create `content/blog/_index.md`:

```markdown
---
title: Blog
description: Latest articles and updates
type: blog
---

# Blog

Welcome to our blog! Here's where we share insights...
```

### URL Structure

Posts appear at `/blog/post-slug/`:

- `content/blog/first-post.md` → `/blog/first-post/`
- `content/blog/python-guide.md` → `/blog/python-guide/`

## Best Practices

### Write Good Titles

```markdown
✅ Good titles:
- "Getting Started with Python"
- "10 Tips for Better Code"
- "Understanding Static Sites"

❌ Avoid:
- "Post 1"
- "Untitled"
- "My Thoughts"
```

### Use Descriptive Slugs

Filenames become URLs:

```
✅ Good filenames:
- python-getting-started.md
- static-site-benefits.md
- deployment-guide.md

❌ Avoid:
- post1.md
- article.md
- temp.md
```

### Add Hero Images

Hero images make posts more engaging:

- Use high-quality images
- Optimize for web (< 500KB)
- Relevant to content
- Consistent aspect ratio

### Tag Consistently

```markdown
✅ Consistent tagging:
tags: ["python", "tutorial", "beginner"]
tags: ["javascript", "tutorial", "beginner"]
tags: ["ruby", "tutorial", "beginner"]

❌ Inconsistent:
tags: ["Python", "Tutorial"]
tags: ["javascript tutorial"]
tags: ["Ruby Beginner"]
```

## Tags and Categories

### Tags

Specific keywords (3-7 per post):

```yaml
---
tags: ["python", "web-development", "tutorial", "beginner"]
---
```

### Categories

Broader groupings:

```yaml
---
categories: ["Programming", "Web Development"]
---
```

**Difference:**
- **Tags:** Specific topics (many tags, focused)
- **Categories:** Broad groups (few categories, general)

## Related Posts

Bengal automatically generates related posts based on:

- Shared tags
- Same categories
- Similar titles

Displayed in post footer (theme-dependent).

## Quick Reference

**Minimal post:**
```yaml
---
title: Post Title
type: post
date: 2025-10-11
tags: ["tag1", "tag2"]
---
```

**Complete post:**
```yaml
---
title: Post Title
description: Brief summary
type: post
date: 2025-10-11
updated: 2025-10-15
author: Author Name
tags: ["tag1", "tag2"]
categories: ["Category1"]
hero_image: /assets/images/hero.jpg
toc: true
---
```

## Next Steps

- **[Documentation](documentation.md)** - Technical docs
- **[Taxonomies](../advanced/taxonomies.md)** - Tags and categories
- **[SEO](../advanced/seo.md)** - Optimize for search
- **[Frontmatter Guide](../writing/frontmatter-guide.md)** - Metadata

## Related

- [Content Types Overview](index.md) - All types
- [Getting Started](../writing/getting-started.md) - Create content
- [Internal Links](../writing/internal-links.md) - Cross-references

