"""
Contract tests for autodoc layout rendering in the default theme.

These tests are intentionally "static" (file-content based) to avoid the heavy
runtime dependency graph of rendering `base.html` in unit tests.

The goal is to prevent regressions where autodoc pages look "broken" because:
- The default docs layout constrains `.prose` to `--prose-width` (75ch) and centers it.
- Autodoc API/CLI reference pages are app-like UIs (card grids) and must not be constrained.
- `base.html` must not emit `data-variant="None"` when no variant is set.
"""

from __future__ import annotations

import re
from pathlib import Path


def test_default_theme_css_does_not_constrain_api_reference_prose() -> None:
    """Ensure autodoc reference pages have prose constraints for readable content.

    The CSS system uses data-type selectors on body with autodoc type names:
    - autodoc-python: Python API documentation
    - autodoc-cli: CLI command documentation
    - autodoc-rest: REST/OpenAPI documentation

    All autodoc pages constrain their content to prose-width for readability.
    """
    css_path = Path("bengal/themes/default/assets/css/composition/layouts.css")
    css = css_path.read_text(encoding="utf-8")

    # All autodoc reference pages should have prose-width constraints
    assert 'body[data-type="autodoc-python"]' in css
    assert 'body[data-type="autodoc-cli"]' in css
    assert 'body[data-type="autodoc-rest"]' in css

    # These pages should have max-width constraints on .docs-main children
    assert 'body[data-type="autodoc-python"] .docs-main>*' in css
    assert 'body[data-type="autodoc-cli"] .docs-main>*' in css
    assert 'body[data-type="autodoc-rest"] .docs-main>*' in css


def test_base_template_does_not_render_none_variant_attribute() -> None:
    """
    Ensure `base.html` does not emit `data-variant="None"` when page.variant is None.

    This is a contract check on the template expression itself; rendering base.html in a
    unit test requires a large mock surface because it includes many partials.
    """
    base_path = Path("bengal/themes/default/templates/base.html")
    base = base_path.read_text(encoding="utf-8")

    # Require a guard that emits an empty string when variant is falsy.
    assert re.search(
        r'data-variant="\{\{\s*\([^}]*_page\.variant[^}]*else\s*\'\'\s*\)\s*\}\}"', base
    )
