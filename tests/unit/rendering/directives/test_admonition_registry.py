"""Guard: the ``important`` admonition is registered (#288).

The dogfood build reported an H201 "Unknown directive 'important'" error (plus a
cascading PosixPath-serialization error) because ``important`` — a standard
docutils/MyST admonition — was not in ADMONITION_TYPES. Registering it propagates
to the directive registry and the directives health validator.
"""

from __future__ import annotations

from bengal.parsing.backends.patitas.directives.builtins.admonition import (
    ADMONITION_TYPES,
    TYPE_TO_CSS,
    TYPE_TO_ICON,
)

_VALID_CSS = {
    "note",
    "tip",
    "warning",
    "danger",
    "error",
    "info",
    "example",
    "success",
    "seealso",
}


def test_important_admonition_is_registered() -> None:
    assert "important" in ADMONITION_TYPES


def test_important_admonition_maps_to_valid_css_and_icon() -> None:
    # Mapped to an existing CSS class (no orphan selector) and a non-empty icon.
    assert TYPE_TO_CSS.get("important") in _VALID_CSS
    assert TYPE_TO_ICON.get("important")
