#!/usr/bin/env python3
"""
Generate template functions reference from register_all().

Introspects the template function registry by running register_all() with
a mock environment and site, then writes a Markdown reference to
site/content/docs/reference/template-functions/reference-generated.md.

Auto-generated on each build. Do not edit the output file manually.

Usage:
    python scripts/generate_template_functions_reference.py
"""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace


def _stable_impl_name(value: object, key: str = "") -> str:
    """Return a stable identifier for a filter/function implementation.

    Avoids repr() with memory addresses and <lambda> for deterministic docs.
    """
    if hasattr(value, "__name__") and getattr(value, "__name__", ""):
        name = getattr(value, "__name__", "")
        if name != "<lambda>":
            return name
    # Lambdas and wrappers: use registration key (e.g. get_auto_nav)
    if key:
        return key
    # Use class name for proxy objects, descriptors, etc.
    return type(value).__name__


def _collect_registrations() -> tuple[dict[str, str], dict[str, str]]:
    """Run register_all with mock env/site and collect filter/function names.

    Returns:
        (filters, functions) - filters map name->implementation, functions same.
        Implementation uses stable identifiers (no memory addresses).
    """
    filters_out: dict[str, str] = {}
    globals_out: dict[str, str] = {}

    class CapturingDict(dict[str, object]):
        def __init__(self, out: dict[str, str]) -> None:
            super().__init__()
            self._out = out

        def __setitem__(self, key: str, value: object) -> None:
            super().__setitem__(key, value)
            self._out[key] = _stable_impl_name(value, key)

        def update(self, other: object = (), /, **kw: object) -> None:
            super().update(other, **kw)
            d = dict(other) if isinstance(other, dict) else kw
            for k, v in d.items():
                self._out[k] = _stable_impl_name(v, k)

    env = SimpleNamespace()
    env.filters = CapturingDict(filters_out)
    env.globals = CapturingDict(globals_out)
    env.tests = {}  # Jinja2/Kida test functions (e.g. defined, undefined)

    site = SimpleNamespace(
        root_path=Path("."),
        pages=[],
        config={},
        baseurl="",
    )

    from bengal.rendering.template_functions import register_all

    register_all(env, site, engine_type="jinja")

    return filters_out, globals_out


def generate() -> str:
    """Generate template functions reference Markdown."""
    filters, functions = _collect_registrations()

    lines = [
        "---",
        "title: Template Functions Reference (Generated)",
        "nav_title: Functions Index",
        "description: Auto-generated index of all template filters and functions",
        "weight: 45",
        "---",
        "",
        "# Template Functions Reference",
        "",
        "This page is **auto-generated** from `register_all()`.",
        "Do not edit manually. Run `poe gen-docs` or `poe build` to regenerate.",
        "",
        "## Filters",
        "",
        "Use with the pipe operator: `{{ value | filter_name }}` or `{{ value |> filter_name }}`",
        "",
        "| Filter | Implementation |",
        "|--------|----------------|",
    ]

    for name in sorted(filters.keys()):
        impl = filters[name]
        lines.append(f"| `{name}` | `{impl}` |")

    lines.extend(
        [
            "",
            "## Functions",
            "",
            "Call directly: `{{ function_name() }}` or `{{ function_name(arg) }}`",
            "",
            "| Function | Implementation |",
            "|----------|----------------|",
        ]
    )

    for name in sorted(functions.keys()):
        impl = functions[name]
        lines.append(f"| `{name}` | `{impl}` |")

    lines.extend(
        [
            "",
            "## See Also",
            "",
            "- [String & Date Filters](/docs/reference/template-functions/string-date-filters/)",
            "- [Collection Filters](/docs/reference/template-functions/collection-filters/)",
            "- [Content Filters](/docs/reference/template-functions/content-filters/)",
            "- [Navigation Functions](/docs/reference/template-functions/navigation-functions/)",
            "- [Linking Functions](/docs/reference/template-functions/linking-functions/)",
            "",
        ]
    )

    return "\n".join(lines)


def main() -> None:
    """Generate template functions reference and write to docs."""
    root = Path(__file__).resolve().parent.parent
    out_path = (
        root
        / "site"
        / "content"
        / "docs"
        / "reference"
        / "template-functions"
        / "reference-generated.md"
    )
    out_path.parent.mkdir(parents=True, exist_ok=True)
    content = generate()
    out_path.write_text(content, encoding="utf-8")
    print(f"Wrote {out_path}")


if __name__ == "__main__":
    main()
