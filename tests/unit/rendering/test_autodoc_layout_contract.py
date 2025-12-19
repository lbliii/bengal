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
    """Ensure OpenAPI/CLI reference pages opt out of prose centering constraints.

    The new CSS system uses data-type selectors on body with semantic type names:
    - openapi-reference: REST/OpenAPI documentation
    - cli-reference: CLI command documentation
    - python-reference: Python API documentation (keeps prose constraints)

    OpenAPI and CLI pages get larger container width, while Python API docs
    keep prose constraints for readable docstring content.
    """
    css_path = Path("bengal/themes/default/assets/css/composition/layouts.css")
    css = css_path.read_text(encoding="utf-8")

    # OpenAPI and CLI reference pages should have container-lg constraints
    assert 'body[data-type="openapi-reference"]' in css
    assert 'body[data-type="cli-reference"]' in css

    # These pages should reset .prose max-width to 100%
    assert 'body[data-type="openapi-reference"] .docs-main .prose' in css
    assert 'body[data-type="cli-reference"] .docs-main .prose' in css

    # Python API docs use prose-width constraints
    assert 'body[data-type="python-reference"]' in css


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
