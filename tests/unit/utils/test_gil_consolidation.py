"""Guard tests for canonical GIL detection (#381 finding 7)."""

from __future__ import annotations

from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[3]
_BENGAL_ROOT = _REPO_ROOT / "bengal"
_GIL_MODULE = _BENGAL_ROOT / "utils" / "concurrency" / "gil.py"

_FORBIDDEN_MARKERS = ("_is_gil_enabled", "Py_GIL_DISABLED")


def _is_allowed(path: Path) -> bool:
    try:
        path.relative_to(_GIL_MODULE.parent)
    except ValueError:
        return False
    return path == _GIL_MODULE


@pytest.mark.parametrize("marker", _FORBIDDEN_MARKERS)
def test_gil_detection_implementation_is_canonical(marker: str) -> None:
    offenders: list[str] = []
    for path in _BENGAL_ROOT.rglob("*.py"):
        if _is_allowed(path):
            continue
        if marker in path.read_text(encoding="utf-8"):
            offenders.append(str(path.relative_to(_REPO_ROOT)))
    assert offenders == [], f"{marker} found outside canonical gil.py: {offenders}"
