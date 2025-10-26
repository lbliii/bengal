---
title: Writer Quickstart
description: Create your first site and start writing
weight: 40
categories: ["onboarding"]
---

# Writer Quickstart

Get from zero to published content in 5 minutes. This guide is for content creators who want to focus on writing.

## Prerequisites

- [Bengal installed](/getting-started/installation/)
- Basic knowledge of Markdown

## 1. Create Your Site

Use the interactive wizard to create a site:

```bash
bengal new site myblog
```

Choose a preset that matches your goal:

```
» 📝 Blog          - Personal or professional blog
  📚 Documentation - Technical docs or guides
  💼 Portfolio     - Showcase your work
  🏢 Business      - Company or product site
  📄 Resume        - Professional resume/CV site
```

:::{tip}
Choose **Blog** if you're unsure. It's a great starting point.
:::

```bash
cd myblog
```

## 2. Start the Dev Server

Launch the development server with hot reload:

```bash
bengal site serve
```

Open **http://localhost:5173/** in your browser. You'll see your new site!

:::{note}
The dev server automatically rebuilds when you save changes. Keep it running while you work.
:::

## 3. Create Your First Post

```bash
bengal new page my-first-post --section blog
```

This creates `content/blog/my-first-post.md`. Open it and edit:

```markdown
---
title: My First Post
date: 2025-10-26
tags: [welcome, tutorial]
description: Getting started with Bengal
---

# My First Post

Welcome to my new blog! This is my first post using Bengal.

## Why I Chose Bengal

- Fast builds with parallel processing
- Simple Markdown-based workflow
- Beautiful default themes
- No complicated build tooling

## What's Next?

I'm excited to share more content about:

1. Python development
2. Web performance
3. Static site generators

Stay tuned!
```

**Save the file.** The dev server automatically rebuilds and your new post appears!

## 4. Customize Your Site

Edit `bengal.toml` to personalize your site:

```toml
[site]
title = "My Awesome Blog"
description = "Thoughts on code, design, and life"
baseurl = "https://myblog.com"  # Your future domain
author = "Your Name"
language = "en"
```

## 5. Add More Content

### Create Regular Pages

```bash
# About page
bengal new page about

# Contact page
bengal new page contact
```

### Organize with Sections

```bash
# Create a tutorials section
bengal new page getting-started --section tutorials
bengal new page advanced-tips --section tutorials
```

### Use Frontmatter

Control how pages appear:

```yaml
---
title: Advanced Python Tips
date: 2025-10-26
tags: [python, advanced]
categories: [tutorial]
description: Take your Python skills to the next level
weight: 10               # Lower numbers appear first
template: post.html      # Use specific template
---
```

## 6. Build for Production

When you're ready to publish:

```bash
# Clean previous builds
bengal site clean

# Build the site
bengal site build
```

Your complete site is in the `public/` directory, ready to deploy!

## 7. Deploy Your Site

Deploy the `public/` directory to any static hosting:

**Netlify:**
1. Push your code to GitHub
2. Connect to Netlify
3. Build command: `bengal site build`
4. Publish directory: `public`

**GitHub Pages:**
```bash
git subtree push --prefix public origin gh-pages
```

**Vercel, Cloudflare Pages:** Similar to Netlify - point to `public/`

## Writing Tips

### Markdown Basics

```markdown
# Heading 1
## Heading 2
### Heading 3

**bold text**
*italic text*

[link text](https://example.com)

![image alt text](../images/photo.jpg)

- Bullet list
- Another item

1. Numbered list
2. Another item

`inline code`

```python
# Code block
def hello():
    print("Hello, World!")
```
```

### Add Images

Place images in `assets/images/`:

```markdown
![My Photo](../assets/images/photo.jpg)
```

### Link Between Pages

```markdown
Check out my [about page](../about/)
Read my [first post](../blog/my-first-post/)
```

### Use Tags and Categories

```yaml
---
title: My Post
tags: [python, tutorial, beginner]
categories: [programming, web-dev]
---
```

Tags and categories automatically create archive pages!

## Next Steps

**Learn More:**
- **Configuration** - Explore all config options
- **Themes** - Change your site's appearance
- **Content Management** - Advanced content features

**Get Inspired:**
- Check `site/content/` for example posts
- Browse [Bengal themes](/themes/)
- Read the [full documentation](/docs/)

**Need Help?**
- Join discussions on GitHub
- Read the [troubleshooting guide](/docs/troubleshooting/)
- Check out example sites in the repo

Happy writing! 🎉
