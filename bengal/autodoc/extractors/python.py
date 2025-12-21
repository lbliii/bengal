"""
Python API documentation extractor (backward-compatibility shim).

This module is preserved for backward compatibility. The implementation
has been refactored into the bengal.autodoc.extractors.python package.

New code should import from:
    from bengal.autodoc.extractors.python import PythonExtractor

Deprecated:
    Direct import from this module is deprecated as of the Sprint 6
    architecture refactoring. Use the package import instead.
"""

from __future__ import annotations

import warnings

from bengal.autodoc.extractors.python import PythonExtractor

# Emit deprecation warning on direct import
warnings.warn(
    "Importing PythonExtractor from bengal.autodoc.extractors.python (file) is deprecated. "
    "Import from bengal.autodoc.extractors.python (package) instead.",
    DeprecationWarning,
    stacklevel=2,
)

__all__ = ["PythonExtractor"]
