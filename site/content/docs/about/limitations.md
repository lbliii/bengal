---
title: Limitations
description: What Bengal doesn't do
weight: 25
type: doc
tags: [limitations, constraints]
---

# Limitations

## No Server-Side Rendering

Bengal generates static HTML at build time. There's no runtime server.

For dynamic content, use client-side JavaScript or edge functions.

## No Image Optimization

Bengal doesn't resize or compress images. Use external tools like `sharp` or a CDN with image optimization.

## Large Sites

Sites with 10,000+ pages will have slower full builds. Incremental builds stay fast.

## Windows

Developed on macOS/Linux. Windows works but may have edge cases.

## See Also

- [Comparison](/docs/about/comparison/)
- [FAQ](/docs/about/faq/)
