"""
Guard: default theme trusts platform primitives (#538).

Prevents re-introducing deleted bespoke JS for focus traps, popover positioning,
nav hover dropdowns, and runtime static-decoration DOM surgery.
"""

from __future__ import annotations

from pathlib import Path

THEME = Path(__file__).resolve().parents[3] / "bengal" / "themes" / "default"
JS = THEME / "assets" / "js"


def test_nav_dropdown_module_removed() -> None:
    assert not (JS / "core" / "nav-dropdown.js").exists()


def test_no_hand_rolled_dialog_focus_traps() -> None:
    search = (JS / "core" / "search.js").read_text(encoding="utf-8")
    assert "handleTabKey" not in search


def test_no_js_popover_positioning_helpers() -> None:
    offenders: list[str] = []
    for rel in ("core/theme.js", "enhancements/action-bar.js"):
        text = (JS / rel).read_text(encoding="utf-8")
        if "positionPopover" in text or "getBoundingClientRect" in text:
            offenders.append(rel)
    assert not offenders, f"JS popover positioning remains in: {offenders}"


def test_main_js_uses_delegated_code_copy_only() -> None:
    main = (JS / "main.js").read_text(encoding="utf-8")
    assert "setupCodeCopyButtons" not in main
    assert "setupExternalLinks" not in main
    assert "setupSmoothScroll" not in main
    assert "setupDelegatedCodeCopy" in main


def test_toc_scroll_spy_uses_intersection_observer() -> None:
    toc = (JS / "enhancements" / "toc.js").read_text(encoding="utf-8")
    assert "IntersectionObserver" in toc
    assert "initHeadingObserver" in toc
    assert "initSmoothScroll" not in toc


def test_clipboard_is_async_api_only() -> None:
    utils = (JS / "utils.js").read_text(encoding="utf-8")
    assert "execCommand" not in utils
    assert "navigator.clipboard" in utils
