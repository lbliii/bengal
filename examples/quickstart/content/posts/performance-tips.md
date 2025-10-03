---
title: "Performance Optimization Tips"
date: 2025-09-22
tags: ["performance", "optimization", "advanced"]
categories: ["Performance", "Best Practices"]
description: "Make your Bengal site blazing fast"
author: "David Kim"
---

# Performance Optimization Tips

Bengal is fast by default, but here are some tips to make it even faster.

## Use Incremental Builds

Bengal's incremental build system only rebuilds changed files:

```bash
bengal build --incremental
```

## Optimize Images

Always optimize your images before adding them to your site:

- Use modern formats (WebP, AVIF)
- Compress images
- Use appropriate dimensions

## Lazy Loading

The default theme includes lazy loading for images automatically.

