---
title: Getting Started with Bengal
date: {{date}}
tags: [bengal, tutorial, ssg]
category: technology
description: Learn how to add posts and customize your blog
params:
  author: kida
---

# Getting Started with Bengal

Bengal is a powerful static site generator that makes building websites easy and fun.

## Key Features

1. **Fast Builds** - Parallel processing for quick build times
2. **Asset Optimization** - Automatic minification and fingerprinting
3. **SEO Friendly** - Built-in sitemap and RSS generation
4. **Developer Experience** - Live reload and hot module replacement

## Add a New Post

Try creating a new post:

```bash
bengal new page my-new-post --section posts
```

Then run your site:

```bash
bengal s
```

Edit your new post in `content/posts/my-new-post.md` and see it update live.
