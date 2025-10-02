---
title: "Working with Sections"
date: 2025-09-15
tags: ["tutorial", "organization", "content"]
description: "Organize your content with Bengal sections"
---

# Working with Sections

Sections help you organize content into logical groups.

## Creating Sections

Simply create a directory in your `content` folder:

```
content/
  posts/
  docs/
  tutorials/
```

## Section Configuration

Each section can have its own configuration in your `bengal.toml`:

```toml
[sections.posts]
title = "Blog Posts"
template = "post.html"

[sections.docs]
title = "Documentation"
template = "doc.html"
```

## Archive Pages

Bengal automatically creates archive pages for each section.

