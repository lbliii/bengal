
---
title: "postprocess"
type: python-module
source_file: "bengal/postprocess/__init__.py"
css_class: api-content
description: "Post-processing modules for Bengal SSG.  Handles generation of files and pages after main rendering: - sitemap.xml: SEO sitemap - rss.xml: RSS feed for blog posts - Output formats: JSON, LLM text f..."
---

# postprocess

Post-processing modules for Bengal SSG.

Handles generation of files and pages after main rendering:
- sitemap.xml: SEO sitemap
- rss.xml: RSS feed for blog posts
- Output formats: JSON, LLM text files for search and AI
- Special pages: 404, search page, etc.

Usage:
    from bengal.postprocess import SitemapGenerator, RSSGenerator

    sitemap = SitemapGenerator(site)
    sitemap.generate()

    rss = RSSGenerator(site)
    rss.generate()

---


