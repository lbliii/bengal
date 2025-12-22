"""
Post-processing generators for Bengal SSG.

This package provides generators that run after the main rendering phase to
produce ancillary files and pages. These outputs enhance SEO, enable content
syndication, support search functionality, and provide alternative content
formats for AI/LLM consumption.

Generators:
    SEO & Syndication:
        - SitemapGenerator: XML sitemap for search engine discovery
        - RSSGenerator: RSS 2.0 feeds for content syndication

    Special Pages:
        - SpecialPagesGenerator: 404 error page, search page, graph visualization
        - RedirectGenerator: HTML redirect pages for URL aliases

    Output Formats:
        - OutputFormatsGenerator: Facade for all output format generators
        - PageJSONGenerator: Per-page JSON files for programmatic access
        - PageTxtGenerator: Per-page plain text for AI/LLM consumption
        - SiteIndexGenerator: Site-wide search index (index.json)
        - SiteLlmTxtGenerator: Full site content as single text file

Architecture:
    Post-processing runs after all pages are rendered and output paths are
    known. Generators receive a Site instance with fully populated pages
    and configuration. Each generator writes directly to the output directory
    using atomic file operations for crash safety.

    The PostprocessOrchestrator (bengal.orchestration.postprocess) coordinates
    these generators in the correct order and handles configuration.

Configuration:
    Post-processing is configured in bengal.toml under various sections:

    - [sitemap]: Sitemap generation options
    - [rss]: RSS feed configuration
    - [search]: Search page and index settings
    - [graph]: Knowledge graph visualization
    - [output_formats]: JSON, LLM text output formats
    - [redirects]: Redirect file generation

Example:
    Generators are typically invoked by the PostprocessOrchestrator, but can
    be used directly for testing or custom workflows:

    >>> from bengal.postprocess import SitemapGenerator, RSSGenerator
    >>> from bengal.postprocess import RedirectGenerator, OutputFormatsGenerator
    >>>
    >>> # Generate XML sitemap
    >>> sitemap = SitemapGenerator(site)
    >>> sitemap.generate()
    >>>
    >>> # Generate RSS feed
    >>> rss = RSSGenerator(site)
    >>> rss.generate()
    >>>
    >>> # Generate redirect pages for aliases
    >>> redirects = RedirectGenerator(site)
    >>> redirects.generate()
    >>>
    >>> # Generate output formats (JSON, LLM text)
    >>> formats = OutputFormatsGenerator(site, config=site.config)
    >>> formats.generate()

Related:
    - bengal.orchestration.postprocess: Coordinates post-processing phase
    - bengal.core.site: Site container with pages and configuration
    - bengal.core.page: Page objects with metadata and content
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
    # SEO & Syndication
    "RSSGenerator",
    "SitemapGenerator",
    # Special Pages
    "RedirectGenerator",
    "SpecialPagesGenerator",
    # Output Formats
    "OutputFormatsGenerator",
    "PageJSONGenerator",
    "PageTxtGenerator",
    "SiteIndexGenerator",
    "SiteLlmTxtGenerator",
]
