"""
Post-processing modules for Bengal SSG.

Handles generation of files and pages after main rendering:
- sitemap.xml: SEO sitemap
- rss.xml: RSS feed for blog posts
- Output formats: JSON, LLM text files for search and AI
- Special pages: 404, search page, etc.
- Redirect pages: Page aliases for URL redirects

Usage:

```python
from bengal.postprocess import SitemapGenerator, RSSGenerator, RedirectGenerator

sitemap = SitemapGenerator(site)
sitemap.generate()

rss = RSSGenerator(site)
rss.generate()

redirects = RedirectGenerator(site)
redirects.generate()
```
"""

from __future__ import annotations

from bengal.postprocess.output_formats import (
    OutputFormatsGenerator,
    PageJSONGenerator,
    PageTxtGenerator,
    SiteIndexGenerator,
    SiteLlmTxtGenerator,
)
from bengal.postprocess.redirects import RedirectGenerator
from bengal.postprocess.rss import RSSGenerator
from bengal.postprocess.sitemap import SitemapGenerator
from bengal.postprocess.special_pages import SpecialPagesGenerator

__all__ = [
    "OutputFormatsGenerator",
    "PageJSONGenerator",
    "PageTxtGenerator",
    "RedirectGenerator",
    "RSSGenerator",
    "SiteIndexGenerator",
    "SiteLlmTxtGenerator",
    "SitemapGenerator",
    "SpecialPagesGenerator",
]
