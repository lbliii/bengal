#!/usr/bin/env python3
"""
Generate error documentation pages from ErrorCode enum.

This script auto-generates error documentation pages for the Bengal SSG
documentation site. It creates:

1. Individual error pages at `site/content/docs/errors/{code}.md`
2. An index page at `site/content/docs/errors/_index.md`

Each error page includes:
- Error code and category
- Description of what the error means
- Common causes
- How to fix
- Related error codes

Usage:
    python scripts/generate_error_docs.py

Output:
    site/content/docs/errors/{code}.md for each error code
    site/content/docs/errors/_index.md for the index page
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

# Error documentation content for the most common error codes
# These provide detailed explanations beyond the enum value

ERROR_DOCS: dict[str, dict[str, Any]] = {
    "C001": {
        "title": "Config YAML Parse Error",
        "description": "Invalid YAML/TOML syntax in configuration file",
        "what_this_means": (
            "The configuration file (`bengal.toml` or `bengal.yaml`) contains "
            "invalid syntax that cannot be parsed. Bengal cannot start without "
            "a valid configuration file."
        ),
        "common_causes": [
            "Missing colons after keys",
            "Incorrect indentation (YAML uses spaces, not tabs)",
            "Unquoted special characters (`:`, `#`, `@`)",
            "Unclosed quotes or brackets",
            "Mixing YAML and TOML syntax",
        ],
        "how_to_fix": [
            "Check the line number in the error message",
            "Look for the common issues listed above",
            "Use a YAML validator: https://yamlvalidator.com",
            "Compare with the example config in Bengal documentation",
        ],
        "example": (
            "**❌ Invalid**:\n"
            "```yaml\n"
            "title My Site    # Missing colon\n"
            "```\n\n"
            "**✅ Valid**:\n"
            "```yaml\n"
            "title: My Site\n"
            "```"
        ),
    },
    "C002": {
        "title": "Config Key Missing",
        "description": "A required configuration key was not found",
        "what_this_means": (
            "The configuration file is missing a required key. Some Bengal "
            "features require specific configuration to be present."
        ),
        "common_causes": [
            "Typo in configuration key name",
            "Key defined in wrong section",
            "Missing required configuration section",
        ],
        "how_to_fix": [
            "Check the spelling of the configuration key",
            "Verify the key is in the correct section",
            "Review the Bengal configuration reference",
        ],
        "example": None,
    },
    "C003": {
        "title": "Config Invalid Value",
        "description": "A configuration value failed validation",
        "what_this_means": (
            "A configuration value is not valid for its setting. This could be "
            "a wrong type, an invalid option, or a value outside allowed range."
        ),
        "common_causes": [
            "Using an unsupported value for a setting",
            "Type mismatch (e.g., string instead of number)",
            "Invalid file format extension",
            "Unsupported template engine name",
        ],
        "how_to_fix": [
            "Check the allowed values for the setting",
            "Verify the type matches what's expected",
            "Review the configuration reference documentation",
        ],
        "example": (
            "**❌ Invalid**:\n"
            "```toml\n"
            'template_engine = "unknown_engine"\n'
            "```\n\n"
            "**✅ Valid**:\n"
            "```toml\n"
            'template_engine = "jinja2"  # or "mako", "patitas"\n'
            "```"
        ),
    },
    "N001": {
        "title": "Frontmatter Invalid",
        "description": "Cannot parse frontmatter in content file",
        "what_this_means": (
            "The frontmatter (YAML between `---` delimiters) in a content file "
            "contains syntax errors and cannot be parsed."
        ),
        "common_causes": [
            "Missing closing `---` delimiter",
            "Invalid YAML syntax in frontmatter",
            "Tabs instead of spaces for indentation",
            "Special characters not properly quoted",
        ],
        "how_to_fix": [
            "Check that frontmatter has both opening and closing `---`",
            "Validate YAML syntax in the frontmatter",
            "Ensure dates are in ISO format (YYYY-MM-DD)",
            "Quote values with special characters",
        ],
        "example": (
            "**❌ Invalid**:\n"
            "```markdown\n"
            "---\n"
            "title: My Post\n"
            "date: yesterday  # Invalid date\n"
            "---\n"
            "```\n\n"
            "**✅ Valid**:\n"
            "```markdown\n"
            "---\n"
            "title: My Post\n"
            "date: 2024-01-15\n"
            "---\n"
            "```"
        ),
    },
    "R001": {
        "title": "Template Not Found",
        "description": "Template file could not be located",
        "what_this_means": (
            "Bengal could not find the specified template file. This usually "
            "happens when a page requests a template that doesn't exist."
        ),
        "common_causes": [
            "Typo in template name in frontmatter",
            "Template file not in templates/ directory",
            "Theme template not found",
            "Case sensitivity issue (templates/Page.html vs page.html)",
        ],
        "how_to_fix": [
            "Check the template name in your page's frontmatter",
            "Verify the template file exists in templates/ or theme",
            "Check for case sensitivity in the filename",
            "Run `bengal explain templates` to see available templates",
        ],
        "example": (
            "**❌ Frontmatter referencing missing template**:\n"
            "```yaml\n"
            "---\n"
            "layout: custom-page  # This template doesn't exist\n"
            "---\n"
            "```\n\n"
            "**✅ Using existing template**:\n"
            "```yaml\n"
            "---\n"
            "layout: page  # This template exists\n"
            "---\n"
            "```"
        ),
    },
    "R002": {
        "title": "Template Syntax Error",
        "description": "Jinja2/template syntax error",
        "what_this_means": (
            "The template contains a syntax error that prevents it from "
            "being parsed. This is usually a Jinja2 syntax issue."
        ),
        "common_causes": [
            "Missing `{% endif %}` or `{% endfor %}`",
            "Unclosed `{{` or `{%` tags",
            "Invalid filter syntax",
            "Mismatched block names",
        ],
        "how_to_fix": [
            "Check the line number in the error message",
            "Ensure all blocks have matching end tags",
            "Verify filter syntax: `{{ value | filter }}`",
            "Check for unclosed variable tags",
        ],
        "example": (
            "**❌ Missing end tag**:\n"
            "```jinja2\n"
            "{% if page.draft %}\n"
            "  Draft content\n"
            "{# Missing {% endif %} #}\n"
            "```\n\n"
            "**✅ Correct**:\n"
            "```jinja2\n"
            "{% if page.draft %}\n"
            "  Draft content\n"
            "{% endif %}\n"
            "```"
        ),
    },
    "D001": {
        "title": "Content Directory Not Found",
        "description": "The content directory could not be located",
        "what_this_means": (
            "Bengal could not find the content directory specified in your "
            "configuration. Without content, there's nothing to build."
        ),
        "common_causes": [
            "Running bengal from wrong directory",
            "Content directory was renamed or moved",
            "Typo in content_dir configuration",
        ],
        "how_to_fix": [
            "Verify you're in the site root directory",
            "Check that content/ directory exists",
            "Run `bengal init` to create site structure",
        ],
        "example": None,
    },
    "D005": {
        "title": "Duplicate Page Path",
        "description": "Multiple pages have the same URL",
        "what_this_means": (
            "Two or more pages are configured to output to the same URL. "
            "This would cause one to overwrite the other."
        ),
        "common_causes": [
            "Duplicate slugs in frontmatter",
            "Conflicting autodoc output paths",
            "Multiple index files in same directory",
        ],
        "how_to_fix": [
            "Give each page a unique slug",
            "Check autodoc configuration for conflicts",
            "Remove duplicate content files",
        ],
        "example": None,
    },
}


def get_category_description(category: str) -> str:
    """Get human-readable description for an error category."""
    descriptions = {
        "config": "Configuration loading and validation errors",
        "content": "Content file parsing and frontmatter errors",
        "rendering": "Template rendering and output generation errors",
        "discovery": "Content and section discovery errors",
        "cache": "Build cache operations errors",
        "server": "Development server errors",
        "template_function": "Template function, shortcode, and directive errors",
        "parsing": "YAML, JSON, TOML, and markdown parsing errors",
        "asset": "Static asset processing errors",
        "graph": "Graph analysis errors",
    }
    return descriptions.get(category, f"{category.title()} errors")


def generate_error_page(code_name: str, code_value: str, category: str) -> str:
    """Generate markdown content for an error documentation page."""
    doc_content = ERROR_DOCS.get(code_name, {})

    # Use custom content if available, otherwise generate from code
    title = doc_content.get("title", code_value.replace("_", " ").title())
    description = doc_content.get("description", f"Error code {code_name}")
    what_this_means = doc_content.get(
        "what_this_means",
        f"Error code `{code_name}` indicates a {category} error: **{code_value.replace('_', ' ')}**.",
    )
    common_causes = doc_content.get(
        "common_causes", ["Check the error message for specific details"]
    )
    how_to_fix = doc_content.get(
        "how_to_fix", ["Review the error message and suggestion for guidance"]
    )
    example = doc_content.get("example", None)

    # Format common causes as markdown list
    causes_md = "\n".join(f"- {cause}" for cause in common_causes)

    # Format how to fix as markdown list
    fix_md = "\n".join(f"{i + 1}. {step}" for i, step in enumerate(how_to_fix))

    # Build the page content
    content = f'''---
title: "{code_name}: {title}"
description: "{description}"
error_code: "{code_name}"
category: "{category}"
---

# {code_name}: {title}

{what_this_means}

## Common Causes

{causes_md}

## How to Fix

{fix_md}

'''

    if example:
        content += f"""## Example

{example}

"""

    content += f"""## Related

- [Error Code Reference](/docs/reference/errors/)
- [{category.title()} Errors](/docs/reference/errors/#{category})
"""

    return content


def generate_index_page(codes: list[tuple[str, str, str]]) -> str:
    """Generate the error code index page."""
    # Group codes by category
    categories: dict[str, list[tuple[str, str]]] = {}
    for code_name, code_value, category in codes:
        if category not in categories:
            categories[category] = []
        categories[category].append((code_name, code_value))

    # Build category table
    category_rows = []
    for cat in sorted(categories.keys()):
        prefix = cat[0].upper()
        desc = get_category_description(cat)
        category_rows.append(f"| {prefix} | {cat.title()} | {desc} |")
    category_table = "\n".join(category_rows)

    # Build code list for each category
    code_sections = []
    for cat in sorted(categories.keys()):
        cat_codes = sorted(categories[cat], key=lambda x: x[0])
        rows = []
        for code_name, code_value in cat_codes:
            title = code_value.replace("_", " ").title()
            rows.append(f"| [{code_name}]({code_name.lower()}/) | {title} |")
        code_table = "\n".join(rows)

        code_sections.append(f"""### {cat.title()} Errors ({cat[0].upper()}xxx)

| Code | Description |
|------|-------------|
{code_table}
""")

    all_codes_section = "\n".join(code_sections)

    return f"""---
title: Error Code Reference
nav_title: Error Codes
description: Complete reference for all Bengal error codes
weight: 50
icon: alert-triangle
tags: [reference, errors, troubleshooting]
---

# Error Code Reference

Bengal uses prefixed error codes for quick identification and searchability.
Each error code links to documentation with explanations and solutions.

## Error Categories

| Prefix | Category | Description |
|--------|----------|-------------|
{category_table}

## All Error Codes

{all_codes_section}

## Getting Help

If you encounter an error:

1. Check the error message and suggestion in the CLI output
2. Click the documentation link shown with the error
3. Review this reference for related errors
4. Check the [troubleshooting guide](/docs/guides/troubleshooting/)

For bugs or unclear errors, please [open an issue](https://github.com/bengal-ssg/bengal/issues).
"""


def main() -> None:
    """Generate error documentation pages."""
    # Import here to avoid issues if bengal isn't installed
    try:
        from bengal.errors.codes import ErrorCode
    except ImportError:
        print("Error: Could not import bengal.errors.codes")
        print("Make sure you're running from the bengal project root")
        print("and bengal is installed: pip install -e .")
        return

    # Determine output directory
    script_dir = Path(__file__).parent
    project_root = script_dir.parent
    output_dir = project_root / "site" / "content" / "docs" / "reference" / "errors"

    # Create output directory
    output_dir.mkdir(parents=True, exist_ok=True)

    # Collect all codes
    codes: list[tuple[str, str, str]] = []
    for code in ErrorCode:
        codes.append((code.name, code.value, code.category))

    # Generate individual error pages
    for code_name, code_value, category in codes:
        content = generate_error_page(code_name, code_value, category)
        output_path = output_dir / f"{code_name.lower()}.md"
        output_path.write_text(content)
        print(f"Generated: {output_path}")

    # Generate index page
    index_content = generate_index_page(codes)
    index_path = output_dir / "_index.md"
    index_path.write_text(index_content)
    print(f"Generated: {index_path}")

    print(f"\n✓ Generated {len(codes)} error pages + 1 index page")
    print(f"  Output: {output_dir}")


if __name__ == "__main__":
    main()
