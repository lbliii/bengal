"""
Post-processing modules for sitemap, RSS, custom output formats, special pages, etc.
"""

from bengal.postprocess.sitemap import SitemapGenerator
from bengal.postprocess.rss import RSSGenerator
from bengal.postprocess.output_formats import OutputFormatsGenerator
from bengal.postprocess.special_pages import SpecialPagesGenerator

__all__ = ["SitemapGenerator", "RSSGenerator", "OutputFormatsGenerator", "SpecialPagesGenerator"]

