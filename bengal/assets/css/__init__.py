"""
Base CSS for Bengal directives.

Provides shared, opinion-free CSS that handles universal functional requirements
for directives (show/hide, accessibility, prose contamination fixes). Themes
retain full control over layout and aesthetics.

Public API:
    get_directive_base_css(): Returns bundled base CSS as a string

Architecture:
Base CSS is auto-included BEFORE theme CSS in all builds.
Same specificity rules apply, so theme CSS can override any rule.

Token Contract (soft convention):
Base CSS uses semantic tokens with fallbacks:
    --color-primary: Primary brand color
    --color-accent: Secondary accent color

See Also:
plan/rfc-directive-base-css.md: RFC describing this design
bengal/assets/css/directives/: Individual directive CSS files

"""

from __future__ import annotations

from pathlib import Path

from bengal.utils.primitives.lru_cache import LRUCache

# Thread-safe cache for directive base CSS (replaces @lru_cache for free-threading)
# maxsize=1 because we only cache a single bundled CSS string
_directive_css_cache: LRUCache[str, str] = LRUCache(maxsize=1, name="directive_css")


def get_directive_base_css() -> str:
    """
    Return bundled directive base CSS as a single string.
    
    Reads and bundles all CSS files from the directives/ subdirectory,
    resolving @import statements. The result is cached for performance.
    
    Thread-safe: Uses LRUCache with RLock for safe concurrent access
    under free-threading (PEP 703).
    
    Returns:
        Bundled CSS content (~200 lines, < 2KB)
    
    Example:
            >>> css = get_directive_base_css()
            >>> print(len(css))  # ~2000 characters
        
    """
    def _load_css() -> str:
        directives_dir = Path(__file__).parent / "directives"
        index_file = directives_dir / "_index.css"

        if not index_file.exists():
            return ""

        # Read the index file and resolve @import statements
        return _bundle_css(index_file)
    
    return _directive_css_cache.get_or_set("directive_base_css", _load_css)


def _bundle_css(css_file: Path) -> str:
    """
    Bundle CSS by resolving @import statements recursively.
    
    Args:
        css_file: Path to CSS file to bundle
    
    Returns:
        Bundled CSS content with all imports inlined
        
    """
    import re

    if not css_file.exists():
        return ""

    content = css_file.read_text(encoding="utf-8")
    base_path = css_file.parent

    # Pattern for @import url('path') or @import 'path'
    import_pattern = r"@import\s+(?:url\()?\s*['\"]([^'\"]+)['\"]\s*(?:\))?\s*;"

    def resolve_import(match: re.Match[str]) -> str:
        import_path = match.group(1)
        imported_file = base_path / import_path

        if not imported_file.exists():
            # Keep the @import (might be external URL)
            return match.group(0)

        # Recursively bundle the imported file
        return _bundle_css(imported_file)

    return re.sub(import_pattern, resolve_import, content)


def get_directive_base_css_path() -> Path:
    """
    Return the path to the directive base CSS directory.
    
    Returns:
        Path to bengal/assets/css/directives/
        
    """
    return Path(__file__).parent / "directives"
