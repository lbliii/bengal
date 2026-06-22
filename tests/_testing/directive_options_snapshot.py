"""Capture directive option tables from the Patitas registry (issue #626)."""

from __future__ import annotations

from dataclasses import MISSING, fields
from pathlib import Path
from typing import Any

import yaml

from bengal.parsing.backends.patitas.directives.registry import create_default_registry

_REPO_ROOT = Path(__file__).resolve().parents[2]
_DEFAULT_SNAPSHOT = (
    _REPO_ROOT / "tests" / "unit" / "docs" / "fixtures" / "directive_options_snapshot.yaml"
)
_DEFAULT_DOC = (
    _REPO_ROOT / "site" / "content" / "docs" / "reference" / "directives" / "_registry-options.md"
)


def _option_display_name(field_name: str, aliases: dict[str, str]) -> str:
    reverse = {value: key for key, value in aliases.items()}
    public_name = reverse.get(
        field_name, field_name.rstrip("_") if field_name.endswith("_") else field_name
    )
    return f":{public_name}:"


def _format_default(value: Any) -> str:
    if value is MISSING:
        return "—"
    if value is None:
        return "none"
    if isinstance(value, bool):
        return "true" if value else "false"
    if value == "":
        return '""'
    return str(value)


def options_table_for_class(options_class: type) -> str:
    """Render a markdown option table from a directive options dataclass."""
    aliases = getattr(options_class, "_aliases", {})
    rows: list[tuple[str, str, str]] = []
    for field in fields(options_class):
        if field.name.startswith("_"):
            continue
        rows.append(
            (
                _option_display_name(field.name, aliases),
                _format_default(field.default),
                "—",
            )
        )
    if not rows:
        return "_No typed options._"

    lines = [
        "| Option | Default | Description |",
        "|--------|---------|-------------|",
    ]
    lines.extend(
        f"| `{option}` | {default} | {description} |" for option, default, description in rows
    )
    return "\n".join(lines)


def registry_option_tables() -> dict[str, dict[str, str]]:
    """Build snapshot payload keyed by token_type."""
    registry = create_default_registry()
    payload: dict[str, dict[str, str]] = {}
    for handler in registry.handlers:
        options_class = getattr(handler, "options_class", None)
        if options_class is None:
            continue
        names = ", ".join(f"`{{{name}}}`" for name in sorted(handler.names))
        payload[handler.token_type] = {
            "names": names,
            "options_class": options_class.__name__,
            "table": options_table_for_class(options_class),
        }
    return dict(sorted(payload.items()))


def snapshot_path(path: Path | None = None) -> Path:
    return path or _DEFAULT_SNAPSHOT


def write_snapshot(path: Path | None = None) -> Path:
    target = snapshot_path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    payload = registry_option_tables()
    target.write_text(
        yaml.safe_dump(payload, sort_keys=True, allow_unicode=True),
        encoding="utf-8",
    )
    return target


def load_snapshot(path: Path | None = None) -> dict[str, dict[str, str]]:
    return yaml.safe_load(snapshot_path(path).read_text(encoding="utf-8"))


def render_registry_options_doc(payload: dict[str, dict[str, str]] | None = None) -> str:
    """Render the generated directives options reference page."""
    data = payload or registry_option_tables()
    sections: list[str] = [
        "---",
        "title: Directive Options (Registry)",
        "nav_title: Registry Options",
        "description: Auto-generated directive option tables from create_default_registry()",
        "weight: 90",
        "tags:",
        "- reference",
        "- directives",
        "---",
        "",
        "# Directive Options (Registry)",
        "",
        "Auto-generated from `create_default_registry()`. Regenerate with:",
        "",
        "```bash",
        "python scripts/update_directive_options_snapshot.py",
        "```",
        "",
        "For usage examples, see the category pages under [[docs/reference/directives|Directives Reference]].",
        "",
    ]
    for token_type, entry in data.items():
        sections.extend(
            [
                f"## `{token_type}` {{#{token_type}}}",
                "",
                f"**Directives:** {entry['names']}",
                "",
                f"**Options class:** `{entry['options_class']}`",
                "",
                entry["table"],
                "",
            ]
        )
    return "\n".join(sections).rstrip() + "\n"


def write_registry_options_doc(
    doc_path: Path | None = None,
    payload: dict[str, dict[str, str]] | None = None,
) -> Path:
    target = doc_path or _DEFAULT_DOC
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(render_registry_options_doc(payload), encoding="utf-8")
    return target
