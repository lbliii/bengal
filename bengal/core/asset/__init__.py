"""
Asset handling for static files (images, CSS, JS, fonts, etc.).

Provides the Asset dataclass for representing static files with methods
for processing, optimization, fingerprinting, and output generation.

Public API:
    Asset: Static file representation with processing capabilities

CSS Utilities (also exported):
    transform_css_nesting: Transform CSS nesting syntax for browser compatibility
    remove_duplicate_bare_h1_rules: Remove duplicate h1 rules from CSS
    lossless_minify_css: Minify CSS without losing functionality

Key Concepts:
    Entry Points: CSS/JS files that serve as bundle roots (style.css, bundle.js).
        Entry points can @import other CSS files which are inlined during bundling.

    Modules: CSS/JS files imported by entry points. These are bundled into
        the entry point and not copied separately to output.

    Fingerprinting: SHA256-based cache-busting via filename suffixes
        (e.g., style.css → style.1a2b3c4d.css). Enables aggressive caching.

    Atomic Writes: Crash-safe file writing using temporary files and rename.
        Prevents partial writes from corrupting output.

Processing Pipeline:
    1. Discovery: Find assets in theme and site directories
    2. Bundling: Resolve @import statements (CSS entry points)
    3. Transformation: CSS nesting → flat CSS for browser compatibility
    4. Minification: Remove whitespace/comments (CSS/JS)
    5. Fingerprinting: Generate content hash for cache-busting
    6. Output: Atomic write to output directory

Related Packages:
    bengal.orchestration.asset: Asset discovery and build orchestration
    bengal.utils.css_minifier: CSS minification implementation
    bengal.utils.atomic_write: Atomic file writing utilities

Package Structure:
    asset_core.py: Asset dataclass with processing methods
    css_transforms.py: CSS transformation utilities
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
