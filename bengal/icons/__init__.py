"""
Theme-aware icon resolution for Bengal.

This package provides centralized icon loading with theme-aware resolution.
All icon loading (template functions, plugins, directives) uses this module.

Resolution Order (first match wins):
    1. site/themes/{theme}/assets/icons/{name}.svg   ← Site overrides
    2. bengal/themes/{theme}/assets/icons/{name}.svg ← Theme icons
    3. bengal/themes/{parent}/assets/icons/{name}.svg ← Parent theme
    4. bengal/themes/default/assets/icons/{name}.svg ← Bengal defaults

Example:
    >>> from bengal.icons import resolver
    >>> resolver.initialize(site)
    >>> svg_content = resolver.load_icon("warning")
"""

from bengal.icons import resolver, svg

__all__ = ["resolver", "svg"]
