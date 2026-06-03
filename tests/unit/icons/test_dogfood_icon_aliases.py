"""Guard: icon names referenced by docs content must resolve to real SVGs (#288).

These names were reported as "missing icons" on the dogfood build because
``external`` was aliased to a non-existent ``arrow-square-out`` and the rest had
no ICON_MAP entry (so they fell through to ``{name}.svg``, which did not exist).
This test fails if any alias points at an SVG that is not present in the default
theme — i.e. it discriminates: a broken alias re-breaks it.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from bengal.icons.svg import ICON_MAP

# Names referenced from dogfood content frontmatter / card directives that were
# missing before #288.
DOGFOOD_ICON_NAMES = ["external", "languages", "python", "robot", "stethoscope", "arrows"]

_ICONS_DIR = Path("bengal/themes/default/assets/icons")


@pytest.mark.parametrize("name", DOGFOOD_ICON_NAMES)
def test_dogfood_referenced_icon_resolves_to_existing_svg(name: str) -> None:
    target = ICON_MAP.get(name, name)
    svg = _ICONS_DIR / f"{target}.svg"
    assert svg.exists(), f"icon {name!r} -> {target!r}.svg does not exist in the default theme"


def test_external_icon_not_aliased_to_missing_arrow_square_out() -> None:
    """Regression guard for the specific #288 bug."""
    assert ICON_MAP.get("external") != "arrow-square-out"
    assert not (_ICONS_DIR / "arrow-square-out.svg").exists()
