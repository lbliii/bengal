---
title: Limitations
description: What Bengal doesn't do
weight: 25
type: doc
tags:
- limitations
- constraints
---

# Limitations

## No Server-Side Rendering

Bengal generates static HTML at build time. There's no runtime server.

For dynamic content, use client-side JavaScript or edge functions.

## No Image Resizing

Bengal compresses images (using Pillow with quality optimization) but doesn't resize them or generate responsive variants. Use external tools like `sharp` or a CDN for resizing and responsive image generation.

## Large Sites

Sites with 10,000+ pages will have slower full builds. Incremental builds stay fast.

## Windows

Developed on macOS/Linux. Windows works but may have edge cases.

## See Also

- [Comparison](/docs/about/comparison/)
- [FAQ](/docs/about/faq/)
