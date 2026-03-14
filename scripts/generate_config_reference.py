#!/usr/bin/env python3
"""
Generate config reference documentation from DEFAULTS.

Reads bengal.config.defaults.DEFAULTS and writes a Markdown reference
to site/content/docs/reference/architecture/tooling/config-reference.md.

Auto-generated on each build. Do not edit the output file manually.

Usage:
    python scripts/generate_config_reference.py
"""

from __future__ import annotations

import json
from pathlib import Path


def _format_value(value: object) -> str:
    """Format a config value for display."""
    if value is None:
        return "`null`"
    if isinstance(value, bool):
        return "`true`" if value else "`false`"
    if isinstance(value, (int, float)):
        return str(value)
    if isinstance(value, str):
        return f"`{json.dumps(value)}`"
    if isinstance(value, list):
        items = ", ".join(_format_value(v) for v in value[:5])
        if len(value) > 5:
            items += f", ... ({len(value)} total)"
        return f"[{items}]"
    if isinstance(value, dict):
        return f"*object* ({len(value)} keys)"
    return str(value)


def generate() -> str:
    """Generate config reference Markdown from DEFAULTS."""
    from bengal.config.defaults import DEFAULTS

    lines = [
        "---",
        "title: Config Reference",
        "nav_title: Config Reference",
        "description: Auto-generated reference of all configuration options and defaults",
        "weight: 25",
        "---",
        "",
        "# Config Reference",
        "",
        "This page is **auto-generated** from `bengal.config.defaults.DEFAULTS`.",
        "Do not edit manually. Run `poe gen-docs` or `poe build` to regenerate.",
        "",
        "## Top-Level Keys",
        "",
        "| Key | Description |",
        "|-----|-------------|",
    ]

    # Brief descriptions for top-level keys
    descriptions: dict[str, str] = {
        "site": "Site metadata (title, baseurl, author, language)",
        "build": "Build settings (output_dir, parallel, incremental, pretty_urls)",
        "dev": "Development server (port, live_reload, watch)",
        "static": "Static files (enabled, dir)",
        "html_output": "HTML formatting (mode, remove_comments)",
        "assets": "Asset processing (minify, optimize, fingerprint)",
        "theme": "Theme settings (name, syntax highlighting, features)",
        "content": "Content processing (excerpt, TOC, sorting)",
        "search": "Search configuration (Lunr, UI, analytics)",
        "pagination": "Pagination (per_page)",
        "health_check": "Health validators and thresholds",
        "features": "Feature toggles (rss, sitemap, search, json)",
        "graph": "Graph visualization",
        "i18n": "Internationalization",
        "output_formats": "Output formats (JSON, llm_txt, changelog)",
        "structured_data": "Schema.org JSON-LD",
        "connect_to_ide": "Cursor MCP one-click install",
        "content_signals": "AI/crawler content policy",
        "markdown": "Markdown parser (patitas, toc_depth)",
        "external_refs": "Cross-project documentation links",
        "link_previews": "Wikipedia-style hover cards",
        "document_application": "View Transitions, speculation rules",
    }

    for key in sorted(DEFAULTS.keys()):
        desc = descriptions.get(key, "")
        lines.append(f"| `{key}` | {desc} |")

    lines.append("")
    lines.append("## Default Values by Section")
    lines.append("")

    for key in sorted(DEFAULTS.keys()):
        value = DEFAULTS[key]
        lines.append(f"### `{key}`")
        lines.append("")
        if isinstance(value, dict):
            for k, v in sorted(value.items()):
                fmt = _format_value(v)
                if isinstance(v, dict):
                    lines.append(f"- **`{k}`**: {fmt}")
                    for sk, sv in sorted(v.items()):
                        lines.append(f"  - `{sk}`: {_format_value(sv)}")
                else:
                    lines.append(f"- **`{k}`**: {fmt}")
        else:
            lines.append(f"- {_format_value(value)}")
        lines.append("")

    return "\n".join(lines)


def main() -> None:
    """Generate config reference and write to docs."""
    root = Path(__file__).resolve().parent.parent
    out_path = (
        root
        / "site"
        / "content"
        / "docs"
        / "reference"
        / "architecture"
        / "tooling"
        / "config-reference.md"
    )
    out_path.parent.mkdir(parents=True, exist_ok=True)
    content = generate()
    out_path.write_text(content, encoding="utf-8")
    print(f"Wrote {out_path}")


if __name__ == "__main__":
    main()
