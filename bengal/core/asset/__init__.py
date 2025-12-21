"""
Asset handling for static files (images, CSS, JS, fonts, etc.).

Provides asset discovery, processing (minification, optimization, bundling),
fingerprinting for cache-busting, and atomic output writing. Handles CSS
nesting transformation, CSS bundling via @import resolution, and image
optimization.

Key Concepts:
    - Entry points: CSS/JS files that serve as bundle roots (style.css, bundle.js)
    - Modules: CSS/JS files imported by entry points (bundled, not copied separately)
    - Fingerprinting: Hash-based cache-busting via filename suffixes
    - Atomic writes: Crash-safe file writing using temporary files

Related Modules:
    - bengal.orchestration.asset: Asset discovery and orchestration
    - bengal.utils.css_minifier: CSS minification implementation
    - bengal.utils.atomic_write: Atomic file writing utilities

Package Structure:
    - asset_core.py: Asset dataclass and primary methods
    - css_transforms.py: CSS transformation utilities (nesting, dedup, minify)
"""

from bengal.core.asset.asset_core import Asset
from bengal.core.asset.css_transforms import (
    lossless_minify_css,
    remove_duplicate_bare_h1_rules,
    transform_css_nesting,
)

# Aliases (tests import these)
_transform_css_nesting = transform_css_nesting
_remove_duplicate_bare_h1_rules = remove_duplicate_bare_h1_rules
_lossless_minify_css_string = lossless_minify_css

__all__ = [
    "Asset",
    # CSS transform utilities
    "transform_css_nesting",
    "remove_duplicate_bare_h1_rules",
    "lossless_minify_css",
    # Aliases
    "_transform_css_nesting",
    "_remove_duplicate_bare_h1_rules",
    "_lossless_minify_css_string",
]
