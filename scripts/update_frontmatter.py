#!/usr/bin/env python3
"""
Update frontmatter in site/content markdown files to match new schema.

Moves css_class and source_file to params section.
"""

import re
from pathlib import Path
from re import Match


def update_frontmatter(content: str) -> str:
    """Update frontmatter to move css_class and source_file to params."""
    # Pattern to match frontmatter block
    frontmatter_pattern = r"^---\n(.*?)\n---"

    def replace_frontmatter(match: Match[str]) -> str:
        frontmatter_content = match.group(1)
        lines = frontmatter_content.split("\n")

        # Track if we need to add params section
        has_css_class = False
        has_source_file = False
        css_class_value = None
        source_file_value = None

        # Collect other lines
        other_lines = []
        for line in lines:
            stripped = line.strip()
            if stripped.startswith("css_class:"):
                has_css_class = True
                # Extract value (handle both quoted and unquoted)
                css_class_value = line.split(":", 1)[1].strip().strip("\"'")
            elif stripped.startswith("source_file:"):
                has_source_file = True
                source_file_value = line.split(":", 1)[1].strip().strip("\"'")
            else:
                other_lines.append(line)

        # If we have css_class or source_file, add params section
        if has_css_class or has_source_file:
            # Find where to insert params (before closing ---)
            # Add params section
            params_lines = ["params:"]
            if has_css_class:
                params_lines.append(f'  css_class: "{css_class_value}"')
            if has_source_file:
                params_lines.append(f'  source_file: "{source_file_value}"')

            # Insert params before the last line (or at end)
            other_lines.extend(params_lines)

        return f"---\n{chr(10).join(other_lines)}\n---"

    # Replace frontmatter
    result = re.sub(
        frontmatter_pattern, replace_frontmatter, content, flags=re.MULTILINE | re.DOTALL
    )
    return result


def main():
    """Update all markdown files in site/content."""
    site_content = Path("site/content")
    updated_count = 0

    for md_file in sorted(site_content.rglob("*.md")):
        content = md_file.read_text(encoding="utf-8")

        # Check if file needs updating
        if "css_class:" in content or "source_file:" in content:
            updated_content = update_frontmatter(content)
            if updated_content != content:
                md_file.write_text(updated_content, encoding="utf-8")
                updated_count += 1
                print(f"Updated: {md_file}")

    print(f"\nUpdated {updated_count} files")


if __name__ == "__main__":
    main()


