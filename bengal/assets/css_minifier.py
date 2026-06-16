"""CSS minification (compatibility shim).

The implementation now lives in the :mod:`bengal.css` engine — a tokenizer-based
minifier that is correct by construction (see ``plan/rfc-css-minifier-tokenizer.md``).
This module re-exports :func:`bengal.css.minify_css` so existing import sites keep
working. Prefer importing from :mod:`bengal.css` in new code.
"""

from bengal.css import minify_css

__all__ = ["minify_css"]
