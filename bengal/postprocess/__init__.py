"""
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
"""

from bengal.postprocess.output_formats import OutputFormatsGenerator
from bengal.postprocess.rss import RSSGenerator
from bengal.postprocess.sitemap import SitemapGenerator
from bengal.postprocess.special_pages import SpecialPagesGenerator

__all__ = ["OutputFormatsGenerator", "RSSGenerator", "SitemapGenerator", "SpecialPagesGenerator"]

