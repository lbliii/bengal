"""
Extractors for different documentation types.

Each extractor converts a specific source type into DocElements.
"""


from __future__ import annotations

from bengal.autodoc.extractors.openapi import OpenAPIExtractor
from bengal.autodoc.extractors.python import PythonExtractor

__all__ = ["OpenAPIExtractor", "PythonExtractor"]
