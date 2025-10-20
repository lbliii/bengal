"""
Bengal SSG - A pythonic static site generator.
"""


from __future__ import annotations

__version__ = "0.1.2"
__author__ = "Bengal Contributors"

from bengal.core.asset import Asset
from bengal.core.page import Page
from bengal.core.section import Section
from bengal.core.site import Site

__all__ = ["Asset", "Page", "Section", "Site", "__version__"]
