"""
Change detectors for incremental builds.
"""

from __future__ import annotations

from bengal.build.detectors.autodoc import AutodocChangeDetector
from bengal.build.detectors.content import ContentChangeDetector
from bengal.build.detectors.data import DataChangeDetector
from bengal.build.detectors.taxonomy import TaxonomyCascadeDetector
from bengal.build.detectors.template import TemplateChangeDetector
from bengal.build.detectors.version import VersionChangeDetector

__all__ = [
    "AutodocChangeDetector",
    "ContentChangeDetector",
    "DataChangeDetector",
    "TemplateChangeDetector",
    "TaxonomyCascadeDetector",
    "VersionChangeDetector",
]
