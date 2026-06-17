"""
Guard: the default theme has ONE JS enhancement model — custom elements (#537).

The old dual system (the ``data-bengal`` lazy registry in ``bengal-enhance.js``
with its ``Bengal.enhance.register`` calls + ``MutationObserver`` + deferred-init
hack, layered on top of eager ``<script defer>`` self-init) was collapsed into a
single custom-elements model: ``core/define.js`` provides ``Bengal.define`` /
``Bengal.Base`` and declarative enhancements are autonomous ``<bengal-*>`` elements
that init via ``connectedCallback``.

This guard prevents the dual system from silently returning — it is the kind of
whole-tree invariant a targeted suite misses but ``fast-check`` catches.
"""

from __future__ import annotations

import re
from pathlib import Path

THEME = Path(__file__).resolve().parents[3] / "bengal" / "themes" / "default"
JS = THEME / "assets" / "js"
TEMPLATES = THEME / "templates"


def test_registry_files_are_gone() -> None:
    """The registry module and the placeholder shim no longer exist."""
    assert not (JS / "bengal-enhance.js").exists(), "bengal-enhance.js must be deleted"
    assert not (JS / "enhancements" / "docs-nav.js").exists(), (
        "the docs-nav.js registry shim must be deleted"
    )


def test_no_register_calls_in_shipped_js() -> None:
    """No shipped theme JS may call into the removed ``Bengal.enhance`` registry."""
    offenders = [
        js.relative_to(JS).as_posix()
        for js in JS.rglob("*.js")
        if ".enhance.register(" in js.read_text(encoding="utf-8")
    ]
    assert not offenders, f"Stale registry registrations remain in: {offenders}"


def test_no_registry_data_bengal_attr_in_templates() -> None:
    """
    Templates must not carry the registry ``data-bengal="NAME"`` attribute.

    The unrelated ``data-bengal-build-badge-*`` namespace (build-badge.js) has a
    hyphen after ``bengal`` and is intentionally allowed.
    """
    pattern = re.compile(r'data-bengal=["\']')
    offenders = []
    for tpl in TEMPLATES.rglob("*.html"):
        for lineno, line in enumerate(tpl.read_text(encoding="utf-8").splitlines(), 1):
            if pattern.search(line):
                offenders.append(f"{tpl.relative_to(THEME).as_posix()}:{lineno}")
    assert not offenders, f"Registry data-bengal= attrs in templates: {offenders}"


def test_custom_element_foundation_present() -> None:
    """``core/define.js`` provides the single enhancement model's primitives."""
    define = (JS / "core" / "define.js").read_text(encoding="utf-8")
    assert "customElements.define" in define
    assert "window.Bengal.define" in define
    assert "window.Bengal.Base" in define
    assert "connectedCallback" in define


def test_converted_modules_define_custom_elements() -> None:
    """The four registry citizens are now autonomous custom elements."""
    expected = {
        "enhancements/toc.js": "bengal-toc",
        "enhancements/tracks.js": "bengal-track-nav",
        "enhancements/interactive.js": "bengal-docs-nav",
        "enhancements/api-catalog.js": "bengal-api-catalog",
    }
    for rel, tag in expected.items():
        text = (JS / rel).read_text(encoding="utf-8")
        assert f"Bengal.define('{tag}'" in text, f"{rel} must define <{tag}>"
