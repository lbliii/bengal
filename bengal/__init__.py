"""
Bengal SSG - A high-performance static site generator.
"""

__version__ = "0.1.0"
__author__ = "Bengal Contributors"

from bengal.core.site import Site
from bengal.core.page import Page
from bengal.core.section import Section
from bengal.core.asset import Asset

__all__ = ["Site", "Page", "Section", "Asset", "__version__"]

