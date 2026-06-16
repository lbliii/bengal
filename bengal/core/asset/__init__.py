"""
Asset handling for static files (images, CSS, JS, fonts, etc.).

Provides the Asset dataclass for representing static files with methods
for processing, optimization, fingerprinting, and output generation.

Public API:
Asset: Static file representation with processing capabilities

CSS minification lives in :mod:`bengal.css` (tokenizer-based engine).

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
3. Minification: bengal.css tokenizer engine (CSS/JS)
4. Fingerprinting: Generate content hash for cache-busting
5. Output: Atomic write to output directory

Related Packages:
bengal.orchestration.asset: Asset discovery and build orchestration
bengal.css: CSS tokenizer/parser/minifier engine
bengal.utils.io.atomic_write: Atomic file writing utilities

Package Structure:
asset_core.py: Asset dataclass with processing methods

"""

from bengal.core.asset.asset_core import Asset

__all__ = [
    "Asset",
]
