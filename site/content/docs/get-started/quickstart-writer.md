---
title: Writer Quickstart
description: Create your first site and start writing content
weight: 20
type: doc
draft: false
lang: en
tags: [onboarding, writing, quickstart]
keywords: [writing, content, markdown, frontmatter]
category: onboarding
aliases:
  - /docs/getting-started/writer-quickstart/
---

# Writer Quickstart

Get from zero to published content in 5 minutes. This guide is for content creators who want to focus on writing.

## Prerequisites

- [Bengal installed](/docs/get-started/installation/)
- Basic knowledge of Markdown

## Create Your Site

Use the interactive wizard:

```bash
bengal new site myblog
cd myblog
```

Choose a preset that matches your goal (Blog, Documentation, Portfolio, etc.).

## Start the Dev Server

```bash
bengal site serve
```

Open **http://localhost:5173/** in your browser. The dev server automatically rebuilds when you save changes.

## Create Your First Post

```bash
bengal new page my-first-post --section blog
```

Edit `content/blog/my-first-post.md`:

```markdown
---
title: My First Post
date: 2025-01-15
tags: [welcome, tutorial]
description: Getting started with Bengal
draft: false
---

# My First Post

Welcome to my new blog! This is my first post using Bengal.

## Why I Chose Bengal

- Fast builds with parallel processing
- Simple Markdown-based workflow
- Customizable themes and templates

Stay tuned for more!
```

**Save the file.** Your new post appears automatically!

## Customize Your Site

Edit `bengal.toml`:

```toml
[site]
title = "My Awesome Blog"
description = "Thoughts on code, design, and life"
baseurl = "https://myblog.com"
author = "Your Name"
language = "en"
```

## Build for Production

```bash
bengal site build
```

Your complete site is in `public/`, ready to deploy!

## Deploy

Deploy the `public/` directory to any static hosting:

- **Netlify**: Build command: `bengal site build`, Publish: `public`
- **GitHub Pages**: Use the workflow in [Automate with GitHub Actions](/docs/tutorials/automate-with-github-actions/)
- **Vercel**: Build command: `bengal site build`, Output: `public`

## Frontmatter Reference

Common frontmatter fields:

| Field | Description |
|-------|-------------|
| `title` | Page title (required) |
| `date` | Publication date |
| `tags` | Tags for taxonomy (e.g., `[python, web]`) |
| `weight` | Sort order (lower = first) |
| `draft` | `true` to hide from builds |
| `description` | SEO description |

## Next Steps

- **[Build a Blog](/docs/tutorials/build-a-blog/)** — Full tutorial
- **[Content Authoring](/docs/content/authoring/)** — Markdown features
- **[Content Organization](/docs/content/organization/)** — Structure your content
- **[Theming](/docs/theming/)** — Customize appearance

Happy writing! 🎉


