---
title: "Understanding the Asset Pipeline"
date: 2025-09-10
tags: ["assets", "css", "javascript"]
categories: ["Features", "Assets"]
description: "How Bengal handles CSS, JS, and other assets"
author: "Bengal Team"
---

# Understanding the Asset Pipeline

Bengal's asset pipeline is designed to be simple but effective.

## Asset Discovery

Place assets in your `assets` directory:

```
assets/
  css/
  js/
  images/
```

## Theme Assets

Theme assets are automatically included. You can override them by placing files with the same name in your site's `assets` directory.

## Processing

Assets are:
- Copied to the output directory
- URLs are automatically generated
- Cache busting is supported (coming soon)

