#!/usr/bin/env python3
"""
Clean up frontmatter in site/content/docs markdown files to match new schema.

- Moves custom fields (icon, hidden) to params section
- Ensures consistent field ordering
- Standardizes formatting
"""

from pathlib import Path
from typing import Any

# Standard field order (from frontmatter reference)
STANDARD_FIELDS_ORDER = [
    "title",
    "description",
    "date",
    "draft",
    "weight",
    "slug",
    "url",
    "aliases",
    "lang",
    "type",
    "layout",
    "template",
    "tags",
    "categories",
    "keywords",
    "authors",
    "category",
    "canonical",
    "noindex",
    "og_image",
    "og_type",
    "menu",
    "nav_title",
    "parent",
    "cascade",
    "outputs",
    "resources",
    "toc",  # Standard field from DocPage schema
    "params",  # Custom fields go here
]

# Custom fields that should move to params
CUSTOM_FIELDS = ["icon", "hidden", "card_color"]


def parse_frontmatter(content: str) -> tuple[dict[str, Any], str]:
    """Parse frontmatter and body from markdown content."""
    if not content.startswith("---"):
        return {}, content

    # Find end of frontmatter
    end_idx = content.find("---", 3)
    if end_idx == -1:
        return {}, content

    frontmatter_str = content[3:end_idx].strip()
    body = content[end_idx + 3 :].lstrip("\n")

    # Parse YAML (simple parsing - handles basic cases)
    import yaml

    try:
        metadata = yaml.safe_load(frontmatter_str) or {}
    except Exception:
        # If YAML parsing fails, return empty dict
        return {}, content

    return metadata, body


def format_frontmatter(metadata: dict[str, Any]) -> str:
    """Format metadata as YAML frontmatter with proper ordering."""
    # Separate standard and custom fields
    standard_fields = {}
    custom_fields = {}

    for key, value in metadata.items():
        if key in CUSTOM_FIELDS:
            custom_fields[key] = value
        else:
            standard_fields[key] = value

    # Build ordered frontmatter
    lines = ["---"]

    # Add standard fields in order
    for field in STANDARD_FIELDS_ORDER:
        if field in standard_fields:
            value = standard_fields[field]
            lines.append(format_field(field, value))
            del standard_fields[field]

    # Add any remaining standard fields (not in order list)
    for key, value in sorted(standard_fields.items()):
        lines.append(format_field(key, value))

    # Add params section if we have custom fields
    if custom_fields:
        # Check if params already exists
        if "params" in standard_fields:
            # Merge with existing params
            existing_params = standard_fields.pop("params", {})
            if isinstance(existing_params, dict):
                custom_fields.update(existing_params)
        lines.append("params:")
        for key, value in sorted(custom_fields.items()):
            lines.append(f"  {key}: {format_value(value)}")

    lines.append("---")
    return "\n".join(lines) + "\n"


def format_field(key: str, value: Any) -> str:
    """Format a single frontmatter field."""
    if value is None:
        return f"{key}: null"
    elif isinstance(value, bool):
        return f"{key}: {str(value).lower()}"
    elif isinstance(value, (int, float)):
        return f"{key}: {value}"
    elif isinstance(value, str):
        # Quote if contains special chars or starts with number
        if ":" in value or value.startswith(("0", "1", "2", "3", "4", "5", "6", "7", "8", "9")):
            return f'{key}: "{value}"'
        return f"{key}: {value}"
    elif isinstance(value, list):
        if not value:
            return f"{key}: []"
        # Format as inline list if short, multi-line if long
        if len(value) <= 3 and all(isinstance(v, str) and len(v) < 20 for v in value):
            items = ", ".join(format_value(v) for v in value)
            return f"{key}: [{items}]"
        else:
            lines = [f"{key}:"]
            for item in value:
                lines.append(f"  - {format_value(item)}")
            return "\n".join(lines)
    elif isinstance(value, dict):
        lines = [f"{key}:"]
        for k, v in sorted(value.items()):
            lines.append(f"  {k}: {format_value(v)}")
        return "\n".join(lines)
    else:
        return f"{key}: {format_value(value)}"


def format_value(value: Any) -> str:
    """Format a YAML value."""
    if value is None:
        return "null"
    elif isinstance(value, bool):
        return str(value).lower()
    elif isinstance(value, (int, float)):
        return str(value)
    elif isinstance(value, str):
        # Quote if contains special chars
        if (
            ":" in value
            or " " in value
            or value.startswith(("0", "1", "2", "3", "4", "5", "6", "7", "8", "9"))
        ):
            return f'"{value}"'
        return value
    elif isinstance(value, list):
        return f"[{', '.join(format_value(v) for v in value)}]"
    elif isinstance(value, dict):
        items = ", ".join(f"{k}: {format_value(v)}" for k, v in value.items())
        return f"{{{items}}}"
    else:
        return str(value)


def update_file(file_path: Path) -> bool:
    """Update frontmatter in a single file. Returns True if changed."""
    try:
        content = file_path.read_text(encoding="utf-8")
        metadata, body = parse_frontmatter(content)

        if not metadata:
            return False

        # Check if we need to update (has custom fields at top level)
        needs_update = any(key in metadata for key in CUSTOM_FIELDS)

        # Also check if params already exists and has these fields
        if "params" in metadata:
            params = metadata.get("params", {})
            if any(key in params for key in CUSTOM_FIELDS):
                # Already in params, but might need reordering
                needs_update = True

        if not needs_update:
            return False

        # Move custom fields to params
        params = metadata.get("params", {})
        for field in CUSTOM_FIELDS:
            if field in metadata:
                params[field] = metadata.pop(field)

        if params:
            metadata["params"] = params

        # Format new frontmatter
        new_frontmatter = format_frontmatter(metadata)
        new_content = new_frontmatter + body

        if new_content != content:
            file_path.write_text(new_content, encoding="utf-8")
            return True

        return False
    except Exception as e:
        print(f"Error processing {file_path}: {e}")
        return False


def main():
    """Update all markdown files in site/content/docs."""
    docs_dir = Path("site/content/docs")
    updated_count = 0

    for md_file in sorted(docs_dir.rglob("*.md")):
        if update_file(md_file):
            print(f"Updated: {md_file.relative_to(docs_dir)}")
            updated_count += 1

    print(f"\nUpdated {updated_count} files")


if __name__ == "__main__":
    main()
