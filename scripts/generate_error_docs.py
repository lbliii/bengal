#!/usr/bin/env python3
"""
Generate error documentation as a single glossary page from ErrorCode enum.

This script auto-generates a consolidated error reference page for the Bengal SSG
documentation site at `site/content/docs/reference/errors/_index.md`.

Each error entry includes:
- Error code anchor for direct linking
- Description of what the error means
- Common causes
- How to fix
- Code examples where helpful

Usage:
    python scripts/generate_error_docs.py

Output:
    site/content/docs/reference/errors/_index.md
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

# Error documentation content for the most common error codes
# These provide detailed explanations beyond the enum value

ERROR_DOCS: dict[str, dict[str, Any]] = {
    "C001": {
        "title": "Config YAML Parse Error",
        "description": (
            "Invalid YAML/TOML syntax in configuration file.\n\n"
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
            "❌ **Invalid**:\n"
            "```yaml\n"
            "title My Site    # Missing colon\n"
            "```\n\n"
            "✅ **Valid**:\n"
            "```yaml\n"
            "title: My Site\n"
            "```"
        ),
    },
    "C002": {
        "title": "Config Key Missing",
        "description": (
            "A required configuration key was not found.\n\n"
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
    },
    "C003": {
        "title": "Config Invalid Value",
        "description": (
            "A configuration value failed validation.\n\n"
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
            "❌ **Invalid**:\n"
            "```toml\n"
            'template_engine = "unknown_engine"\n'
            "```\n\n"
            "✅ **Valid**:\n"
            "```toml\n"
            'template_engine = "jinja2"  # or "mako", "patitas"\n'
            "```"
        ),
    },
    "C004": {
        "title": "Config Type Mismatch",
        "description": "Configuration value has wrong type.",
        "common_causes": [
            "String provided where number expected",
            "List provided where single value expected",
            "Boolean syntax error",
        ],
        "how_to_fix": [
            "Check the expected type in documentation",
            "Use correct YAML/TOML type syntax",
        ],
    },
    "C005": {
        "title": "Config Defaults Missing",
        "description": "Required default configuration could not be loaded.",
        "common_causes": [
            "Bengal installation is corrupted",
            "Custom defaults file is missing",
        ],
        "how_to_fix": [
            "Reinstall Bengal: `pip install --force-reinstall bengal`",
            "Check that default config files exist in installation",
        ],
    },
    "C006": {
        "title": "Config Environment Unknown",
        "description": "Specified environment configuration not found.",
        "common_causes": [
            "Typo in environment name",
            "Environment config file missing",
        ],
        "how_to_fix": [
            "Check available environments in `bengal.toml`",
            "Create the environment config if needed",
        ],
    },
    "C007": {
        "title": "Config Circular Reference",
        "description": "Configuration contains circular references.",
        "common_causes": [
            "Config A includes B, which includes A",
            "Self-referencing configuration value",
        ],
        "how_to_fix": [
            "Review configuration includes and references",
            "Break the circular dependency",
        ],
    },
    "C008": {
        "title": "Config Deprecated Key",
        "description": "Configuration uses a deprecated key.",
        "common_causes": [
            "Using old configuration format",
            "Key was renamed in newer version",
        ],
        "how_to_fix": [
            "Check the migration guide for the new key name",
            "Update configuration to use current syntax",
        ],
    },
    "N001": {
        "title": "Frontmatter Invalid",
        "description": (
            "Cannot parse frontmatter in content file.\n\n"
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
            "❌ **Invalid**:\n"
            "```markdown\n"
            "---\n"
            "title: My Post\n"
            "date: yesterday  # Invalid date\n"
            "---\n"
            "```\n\n"
            "✅ **Valid**:\n"
            "```markdown\n"
            "---\n"
            "title: My Post\n"
            "date: 2024-01-15\n"
            "---\n"
            "```"
        ),
    },
    "N002": {
        "title": "Frontmatter Date Invalid",
        "description": "Date value in frontmatter cannot be parsed.",
        "common_causes": [
            "Non-standard date format",
            "Invalid date (e.g., February 30)",
            "Timezone parsing issue",
        ],
        "how_to_fix": [
            "Use ISO format: `YYYY-MM-DD`",
            "Optionally add time: `YYYY-MM-DDTHH:MM:SS`",
            "Verify the date is valid",
        ],
    },
    "N003": {
        "title": "Content File Encoding",
        "description": "File uses unsupported character encoding.",
        "common_causes": [
            "File saved in non-UTF-8 encoding",
            "Binary data in text file",
            "Corrupted file",
        ],
        "how_to_fix": [
            "Convert file to UTF-8: `iconv -f LATIN1 -t UTF-8 file.md`",
            "Re-save file with UTF-8 encoding in your editor",
            "Check for binary content",
        ],
    },
    "N004": {
        "title": "Content File Not Found",
        "description": "Referenced content file does not exist.",
        "common_causes": [
            "Typo in filename reference",
            "File was moved or deleted",
            "Case sensitivity mismatch",
        ],
        "how_to_fix": [
            "Verify the file path is correct",
            "Check for case sensitivity issues",
            "Restore or recreate the file",
        ],
    },
    "N005": {
        "title": "Content Markdown Error",
        "description": "Markdown parsing failed.",
        "common_causes": [
            "Malformed markdown syntax",
            "Unclosed code blocks",
            "Invalid HTML embedded in markdown",
        ],
        "how_to_fix": [
            "Check for unclosed code fences (```)",
            "Validate embedded HTML",
            "Use a markdown linter",
        ],
    },
    "N006": {
        "title": "Content Shortcode Error",
        "description": "Shortcode in content failed to render.",
        "common_causes": [
            "Invalid shortcode syntax",
            "Missing required shortcode argument",
            "Shortcode function raised error",
        ],
        "how_to_fix": [
            'Check shortcode syntax: `{{< shortcode arg="value" >}}`',
            "Verify all required arguments are provided",
            "Review shortcode documentation",
        ],
    },
    "N007": {
        "title": "Content TOC Extraction Error",
        "description": "Failed to extract table of contents.",
        "common_causes": [
            "Invalid heading structure",
            "Heading without text",
            "Parser error",
        ],
        "how_to_fix": [
            "Ensure headings have text content",
            "Use proper heading hierarchy (h1 → h2 → h3)",
        ],
    },
    "N008": {
        "title": "Content Taxonomy Invalid",
        "description": "Invalid taxonomy value in frontmatter.",
        "common_causes": [
            "Taxonomy value is not a list",
            "Invalid taxonomy name",
            "Taxonomy not defined in config",
        ],
        "how_to_fix": [
            "Use list syntax for taxonomies: `tags: [a, b, c]`",
            "Check taxonomy is defined in config",
            "Verify taxonomy value format",
        ],
    },
    "N009": {
        "title": "Content Weight Invalid",
        "description": "Weight value must be a number.",
        "common_causes": [
            "Weight is a string instead of number",
            "Weight contains non-numeric characters",
        ],
        "how_to_fix": [
            "Use integer for weight: `weight: 10`",
            "Remove quotes around weight value",
        ],
    },
    "N010": {
        "title": "Content Slug Invalid",
        "description": "Slug contains invalid characters.",
        "common_causes": [
            "Spaces in slug",
            "Special characters",
            "Non-ASCII characters",
        ],
        "how_to_fix": [
            "Use only lowercase letters, numbers, and hyphens",
            "Example: `slug: my-page-title`",
        ],
    },
    "R001": {
        "title": "Template Not Found",
        "description": (
            "Template file could not be located.\n\n"
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
            "❌ **Frontmatter referencing missing template**:\n"
            "```yaml\n"
            "---\n"
            "layout: custom-page  # This template doesn't exist\n"
            "---\n"
            "```\n\n"
            "✅ **Using existing template**:\n"
            "```yaml\n"
            "---\n"
            "layout: page  # This template exists\n"
            "---\n"
            "```"
        ),
    },
    "R002": {
        "title": "Template Syntax Error",
        "description": (
            "Jinja2/template syntax error.\n\n"
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
            "❌ **Missing end tag**:\n"
            "```jinja2\n"
            "{% if page.draft %}\n"
            "  Draft content\n"
            "{# Missing {% endif %} #}\n"
            "```\n\n"
            "✅ **Correct**:\n"
            "```jinja2\n"
            "{% if page.draft %}\n"
            "  Draft content\n"
            "{% endif %}\n"
            "```"
        ),
    },
    "R003": {
        "title": "Template Undefined Variable",
        "description": "Variable used in template is not defined.",
        "common_causes": [
            "Typo in variable name",
            "Variable not passed to template context",
            "Using variable before it's set",
        ],
        "how_to_fix": [
            "Check spelling of variable name",
            "Verify variable is in template context",
            'Use `{{ variable | default("") }}` for optional variables',
        ],
    },
    "R004": {
        "title": "Template Filter Error",
        "description": "Template filter raised an error.",
        "common_causes": [
            "Passing wrong type to filter",
            "Filter not registered",
            "Filter function raised exception",
        ],
        "how_to_fix": [
            "Check filter expects the input type you're providing",
            "Verify custom filters are registered",
            "Review filter documentation",
        ],
    },
    "R005": {
        "title": "Template Include Error",
        "description": "Could not include referenced template.",
        "common_causes": [
            "Included template doesn't exist",
            "Circular include detected",
            "Include path is incorrect",
        ],
        "how_to_fix": [
            "Verify included template path",
            "Check for circular includes",
            "Use relative path from templates/ directory",
        ],
    },
    "R006": {
        "title": "Template Macro Error",
        "description": "Macro definition or call failed.",
        "common_causes": [
            "Macro not defined",
            "Wrong number of arguments",
            "Macro raised error",
        ],
        "how_to_fix": [
            'Ensure macro is imported: `{% from "macros.html" import mymacro %}`',
            "Check macro signature matches call",
            "Review macro implementation",
        ],
    },
    "R007": {
        "title": "Template Block Error",
        "description": "Template block inheritance error.",
        "common_causes": [
            "Block name mismatch with parent",
            "Missing parent template",
            "Invalid block nesting",
        ],
        "how_to_fix": [
            "Verify block names match parent template",
            "Check parent template exists",
            "Ensure blocks are not nested incorrectly",
        ],
    },
    "R008": {
        "title": "Template Context Error",
        "description": "Template context is invalid or corrupted.",
        "common_causes": [
            "Custom context processor raised error",
            "Conflicting context values",
            "Memory issue with large context",
        ],
        "how_to_fix": [
            "Review custom context processors",
            "Check for conflicting variable names",
            "Reduce context size if very large",
        ],
    },
    "R009": {
        "title": "Template Inheritance Error",
        "description": "Template inheritance chain is invalid.",
        "common_causes": [
            "Parent template not found",
            "Circular inheritance",
            "Invalid extends syntax",
        ],
        "how_to_fix": [
            "Verify parent template exists",
            "Check for circular inheritance",
            'Use correct syntax: `{% extends "base.html" %}`',
        ],
    },
    "R010": {
        "title": "Render Output Error",
        "description": "Failed to write rendered output.",
        "common_causes": [
            "Disk full",
            "Permission denied",
            "Invalid output path",
        ],
        "how_to_fix": [
            "Check available disk space",
            "Verify write permissions on output directory",
            "Check output path is valid",
        ],
    },
    "D001": {
        "title": "Content Directory Not Found",
        "description": (
            "The content directory could not be located.\n\n"
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
    },
    "D002": {
        "title": "Invalid Content Path",
        "description": "Content path contains invalid characters or structure.",
        "common_causes": [
            "Special characters in file/folder names",
            "Path too long for filesystem",
            "Symbolic link issues",
        ],
        "how_to_fix": [
            "Use only alphanumeric characters, hyphens, and underscores",
            "Keep paths reasonably short",
            "Avoid symbolic links in content directory",
        ],
    },
    "D003": {
        "title": "Section Index Missing",
        "description": "A content section is missing its `_index.md` file.",
        "common_causes": [
            "Section folder created without index",
            "Index file accidentally deleted",
        ],
        "how_to_fix": [
            "Create `_index.md` in the section folder",
            "Add required frontmatter with title",
        ],
    },
    "D004": {
        "title": "Circular Section Reference",
        "description": "Sections reference each other in a loop.",
        "common_causes": [
            "Section A's parent is B, but B's parent is A",
            "Symbolic links creating loops",
        ],
        "how_to_fix": [
            "Review section hierarchy",
            "Remove circular parent references",
        ],
    },
    "D005": {
        "title": "Duplicate Page Path",
        "description": (
            "Multiple pages have the same URL.\n\n"
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
    },
    "D006": {
        "title": "Invalid File Pattern",
        "description": "File pattern in configuration is invalid.",
        "common_causes": [
            "Malformed glob pattern",
            "Unsupported pattern syntax",
        ],
        "how_to_fix": [
            "Check glob pattern syntax",
            "Test pattern with `bengal explain patterns`",
        ],
    },
    "D007": {
        "title": "Permission Denied",
        "description": "Cannot access file or directory due to permissions.",
        "common_causes": [
            "File owned by different user",
            "Read permissions not set",
            "File system mounted read-only",
        ],
        "how_to_fix": [
            "Check file permissions: `ls -la`",
            "Fix permissions: `chmod 644 filename`",
            "Verify filesystem is not read-only",
        ],
    },
    "A001": {
        "title": "Cache Corruption",
        "description": "The build cache has become corrupted and cannot be read.",
        "common_causes": [
            "Interrupted build process",
            "Disk space issues during cache write",
            "Manual modification of cache files",
        ],
        "how_to_fix": [
            "Delete the `.bengal/cache/` directory",
            "Run `bengal build` to regenerate the cache",
        ],
    },
    "A002": {
        "title": "Cache Version Mismatch",
        "description": "The cache was created with a different Bengal version.",
        "common_causes": [
            "Bengal was upgraded or downgraded",
            "Cache from a different project",
        ],
        "how_to_fix": [
            "Delete the `.bengal/cache/` directory",
            "Run `bengal build` to regenerate with current version",
        ],
    },
    "A003": {
        "title": "Cache Read Error",
        "description": "Failed to read from the build cache.",
        "common_causes": [
            "File permissions issue",
            "Cache file was deleted mid-build",
            "Disk read error",
        ],
        "how_to_fix": [
            "Check file permissions on `.bengal/cache/`",
            "Delete and regenerate the cache if corrupted",
        ],
    },
    "A004": {
        "title": "Cache Write Error",
        "description": "Failed to write to the build cache.",
        "common_causes": [
            "Insufficient disk space",
            "File permissions issue",
            "Directory doesn't exist",
        ],
        "how_to_fix": [
            "Check available disk space",
            "Verify write permissions on `.bengal/` directory",
        ],
    },
    "A005": {
        "title": "Cache Invalidation Error",
        "description": "Failed to invalidate stale cache entries.",
        "common_causes": [
            "Cache corruption",
            "Concurrent build processes",
        ],
        "how_to_fix": [
            "Delete `.bengal/cache/` and rebuild",
            "Avoid running multiple builds simultaneously",
        ],
    },
    "A006": {
        "title": "Cache Lock Timeout",
        "description": "Could not acquire cache lock within timeout period.",
        "common_causes": [
            "Another Bengal process is running",
            "Previous build crashed while holding lock",
        ],
        "how_to_fix": [
            "Wait for other builds to complete",
            "Delete `.bengal/cache/*.lock` files if no builds are running",
        ],
    },
    "S001": {
        "title": "Server Port In Use",
        "description": "The requested port is already in use.",
        "common_causes": [
            "Another bengal server running",
            "Different application using the port",
            "Previous server didn't shut down cleanly",
        ],
        "how_to_fix": [
            "Use a different port: `bengal serve --port 8001`",
            "Find and stop the process using the port",
            "Wait for port to be released (can take ~30 seconds)",
        ],
    },
    "S002": {
        "title": "Server Bind Error",
        "description": "Could not bind to the network interface.",
        "common_causes": [
            "Permission denied for port < 1024",
            "Network interface doesn't exist",
            "Firewall blocking",
        ],
        "how_to_fix": [
            "Use port >= 1024 (no sudo required)",
            "Check bind address is valid",
            "Review firewall settings",
        ],
    },
    "S003": {
        "title": "Server Reload Error",
        "description": "Live reload failed to trigger.",
        "common_causes": [
            "WebSocket connection lost",
            "Browser extension blocking",
            "File watcher issue",
        ],
        "how_to_fix": [
            "Refresh browser manually",
            "Disable browser extensions temporarily",
            "Restart the dev server",
        ],
    },
    "S004": {
        "title": "Server WebSocket Error",
        "description": "WebSocket connection for live reload failed.",
        "common_causes": [
            "Proxy not configured for WebSocket",
            "Browser doesn't support WebSocket",
            "Network issue",
        ],
        "how_to_fix": [
            "Configure proxy to forward WebSocket",
            "Try a different browser",
            "Check network connectivity",
        ],
    },
    "S005": {
        "title": "Server Static File Error",
        "description": "Could not serve static file.",
        "common_causes": [
            "File doesn't exist",
            "Permission denied",
            "Path traversal blocked",
        ],
        "how_to_fix": [
            "Verify file exists in static/ directory",
            "Check file permissions",
            "Use valid relative paths only",
        ],
    },
    "T001": {
        "title": "Shortcode Not Found",
        "description": "Referenced shortcode is not registered.",
        "common_causes": [
            "Typo in shortcode name",
            "Shortcode not defined",
            "Shortcode file not loaded",
        ],
        "how_to_fix": [
            "Check shortcode name spelling",
            "Verify shortcode is defined in `shortcodes/` directory",
            "Run `bengal explain shortcodes` to list available shortcodes",
        ],
    },
    "T002": {
        "title": "Shortcode Argument Error",
        "description": "Shortcode received invalid arguments.",
        "common_causes": [
            "Missing required argument",
            "Wrong argument type",
            "Unknown argument name",
        ],
        "how_to_fix": [
            "Check shortcode documentation for required arguments",
            "Verify argument types match expected",
            "Remove unknown arguments",
        ],
    },
    "T003": {
        "title": "Shortcode Render Error",
        "description": "Shortcode execution failed.",
        "common_causes": [
            "Shortcode code raised exception",
            "Invalid return value",
            "Template error in shortcode",
        ],
        "how_to_fix": [
            "Check shortcode implementation",
            "Review error message for details",
            "Test shortcode in isolation",
        ],
    },
    "T004": {
        "title": "Directive Not Found",
        "description": "Referenced directive is not registered.",
        "common_causes": [
            "Typo in directive name",
            "Directive not defined",
            "Using MyST syntax for unregistered directive",
        ],
        "how_to_fix": [
            "Check directive name spelling",
            "Verify directive is registered",
            "Review available directives in documentation",
        ],
    },
    "T005": {
        "title": "Directive Argument Error",
        "description": "Directive received invalid arguments.",
        "common_causes": [
            "Missing required argument",
            "Invalid argument format",
            "Argument value out of range",
        ],
        "how_to_fix": [
            "Check directive documentation",
            "Provide all required arguments",
            "Use correct argument format",
        ],
    },
    "T006": {
        "title": "Directive Since Empty",
        "description": "The `{since}` directive requires a version parameter.",
        "common_causes": [
            "Empty version argument",
        ],
        "how_to_fix": [
            "Provide a version string",
        ],
        "example": "```markdown\n{since}`v2.0`\n```",
    },
    "T007": {
        "title": "Directive Deprecated Empty",
        "description": "The `{deprecated}` directive requires a version parameter.",
        "common_causes": [
            "Empty version argument",
        ],
        "how_to_fix": [
            "Provide a version string",
        ],
        "example": "```markdown\n{deprecated}`v1.5`\n```",
    },
    "T008": {
        "title": "Directive Changed Empty",
        "description": "The `{changed}` directive requires a version parameter.",
        "common_causes": [
            "Empty version argument",
        ],
        "how_to_fix": [
            "Provide a version string",
        ],
        "example": "```markdown\n{changed}`v2.1`\n```",
    },
    "T009": {
        "title": "Directive Include Not Found",
        "description": "The included file in directive was not found.",
        "common_causes": [
            "Typo in file path",
            "File doesn't exist",
            "Incorrect relative path",
        ],
        "how_to_fix": [
            "Verify file path is correct",
            "Check file exists at specified location",
            "Use path relative to content directory",
        ],
    },
    "P001": {
        "title": "YAML Parse Error",
        "description": "YAML file contains syntax errors.",
        "common_causes": [
            "Indentation with tabs instead of spaces",
            "Missing colon after key",
            "Unquoted special characters",
        ],
        "how_to_fix": [
            "Use spaces for indentation (2 or 4 spaces)",
            "Ensure colons after keys: `key: value`",
            'Quote special values: `title: "My: Title"`',
        ],
    },
    "P002": {
        "title": "JSON Parse Error",
        "description": "JSON file contains syntax errors.",
        "common_causes": [
            "Trailing comma in array or object",
            "Missing quotes around keys",
            "Single quotes instead of double",
        ],
        "how_to_fix": [
            "Remove trailing commas",
            "Use double quotes for strings",
            "Validate with `python -m json.tool file.json`",
        ],
    },
    "P003": {
        "title": "TOML Parse Error",
        "description": "TOML file contains syntax errors.",
        "common_causes": [
            "Invalid table syntax",
            "Missing quotes around strings with spaces",
            "Incorrect date format",
        ],
        "how_to_fix": [
            "Use `[section]` for tables",
            "Quote strings with spaces",
            "Use RFC 3339 date format",
        ],
    },
    "P004": {
        "title": "Markdown Parse Error",
        "description": "Markdown file cannot be parsed.",
        "common_causes": [
            "Unclosed code blocks",
            "Invalid HTML",
            "Corrupted file",
        ],
        "how_to_fix": [
            "Check for unclosed ``` code fences",
            "Validate embedded HTML",
            "Check file encoding",
        ],
    },
    "P005": {
        "title": "Frontmatter Delimiter Missing",
        "description": "Content file is missing frontmatter delimiters.",
        "common_causes": [
            "Missing opening `---`",
            "Missing closing `---`",
            "Extra whitespace before delimiter",
        ],
        "how_to_fix": [
            "Ensure file starts with `---`",
            "Add closing `---` after frontmatter",
            "Remove whitespace before first delimiter",
        ],
        "example": (
            "✅ **Correct**:\n```markdown\n---\ntitle: My Page\n---\n\nContent starts here.\n```"
        ),
    },
    "P006": {
        "title": "Glossary Parse Error",
        "description": "Glossary file contains errors.",
        "common_causes": [
            "Invalid glossary format",
            "Missing required fields",
            "Duplicate term definitions",
        ],
        "how_to_fix": [
            "Check glossary file format",
            "Ensure each term has required fields",
            "Remove duplicate definitions",
        ],
    },
    "X001": {
        "title": "Asset Not Found",
        "description": "Static asset file could not be located.",
        "common_causes": [
            "Typo in asset path",
            "Asset file missing",
            "Case sensitivity mismatch",
        ],
        "how_to_fix": [
            "Check asset path in template or content",
            "Verify file exists in `static/` directory",
            "Check for case sensitivity issues",
        ],
    },
    "X002": {
        "title": "Asset Invalid Path",
        "description": "Asset path contains invalid characters.",
        "common_causes": [
            "Path traversal attempt (`../`)",
            "Special characters in path",
            "Absolute path used",
        ],
        "how_to_fix": [
            "Use relative paths only",
            "Remove special characters",
            "Don't use `..` in asset paths",
        ],
    },
    "X003": {
        "title": "Asset Processing Failed",
        "description": "Asset pipeline processing failed.",
        "common_causes": [
            "Invalid image format",
            "Processing tool not available",
            "Memory limit exceeded",
        ],
        "how_to_fix": [
            "Verify asset file is valid",
            "Install required processing tools",
            "Reduce asset size or processing complexity",
        ],
    },
    "X004": {
        "title": "Asset Copy Error",
        "description": "Failed to copy asset to output directory.",
        "common_causes": [
            "Permission denied",
            "Disk full",
            "Target file locked",
        ],
        "how_to_fix": [
            "Check write permissions on output directory",
            "Free up disk space",
            "Close applications that may lock files",
        ],
    },
    "X005": {
        "title": "Asset Fingerprint Error",
        "description": "Failed to generate asset fingerprint/hash.",
        "common_causes": [
            "File read error",
            "Very large file",
            "Memory issue",
        ],
        "how_to_fix": [
            "Check file is readable",
            "Reduce file size if very large",
            "Increase available memory",
        ],
    },
    "X006": {
        "title": "Asset Minify Error",
        "description": "Asset minification failed.",
        "common_causes": [
            "Invalid CSS/JS syntax",
            "Minifier not available",
            "Unsupported features in source",
        ],
        "how_to_fix": [
            "Validate CSS/JS syntax",
            "Install minification dependencies",
            "Check for syntax not supported by minifier",
        ],
    },
    "G001": {
        "title": "Graph Not Built",
        "description": "Attempted to query graph before it was built.",
        "common_causes": [
            "Calling graph functions before `build()`",
            "Build failed silently",
        ],
        "how_to_fix": [
            "Ensure `site.build()` completes before graph queries",
            "Check for earlier build errors",
        ],
    },
    "G002": {
        "title": "Graph Invalid Parameter",
        "description": "Invalid parameter passed to graph function.",
        "common_causes": [
            "Page ID doesn't exist",
            "Invalid depth or limit value",
        ],
        "how_to_fix": [
            "Verify page IDs exist in the graph",
            "Use positive integers for depth/limit",
        ],
    },
    "G003": {
        "title": "Graph Cycle Detected",
        "description": "Circular reference detected in page relationships.",
        "common_causes": [
            "Page A links to B, B links to A as prerequisite",
            "Circular navigation structure",
        ],
        "how_to_fix": [
            "Review page relationships",
            "Break the cycle by removing one reference",
        ],
    },
    "G004": {
        "title": "Graph Disconnected Component",
        "description": "Pages are not reachable from navigation.",
        "common_causes": [
            "Orphan pages without parent section",
            "Missing navigation links",
        ],
        "how_to_fix": [
            "Add pages to appropriate sections",
            "Create navigation links to disconnected pages",
        ],
    },
    "G005": {
        "title": "Graph Analysis Failed",
        "description": "Graph analysis computation failed.",
        "common_causes": [
            "Graph is too large",
            "Memory constraints",
            "Invalid graph state",
        ],
        "how_to_fix": [
            "Reduce graph size if possible",
            "Increase available memory",
            "Rebuild the site from scratch",
        ],
    },
}


def get_category_display_name(category: str) -> str:
    """Get display name for an error category."""
    names = {
        "config": "Config",
        "content": "Content",
        "rendering": "Rendering",
        "discovery": "Discovery",
        "cache": "Cache",
        "server": "Server",
        "template_function": "Template Function",
        "parsing": "Parsing",
        "asset": "Asset",
        "graph": "Graph",
    }
    return names.get(category, category.title())


def get_category_description(category: str) -> str:
    """Get human-readable description for an error category."""
    descriptions = {
        "config": "Configuration loading and validation errors",
        "content": "Content file parsing and frontmatter errors",
        "rendering": "Template rendering and output generation errors",
        "discovery": "Content and section discovery errors",
        "cache": "Build cache operations errors",
        "server": "Development server errors",
        "template_function": "Shortcode and directive errors",
        "parsing": "YAML, JSON, TOML, and markdown parsing errors",
        "asset": "Static asset processing errors",
        "graph": "Graph analysis errors",
    }
    return descriptions.get(category, f"{category.title()} errors")


def get_category_prefix(category: str) -> str:
    """Get the single-letter prefix for a category."""
    prefixes = {
        "config": "C",
        "content": "N",
        "rendering": "R",
        "discovery": "D",
        "cache": "A",
        "server": "S",
        "template_function": "T",
        "parsing": "P",
        "asset": "X",
        "graph": "G",
    }
    return prefixes.get(category, category[0].upper())


def generate_error_entry(code_name: str, code_value: str, category: str) -> str:
    """Generate markdown content for a single error entry."""
    doc_content = ERROR_DOCS.get(code_name, {})

    # Use custom content if available, otherwise generate from code
    title = doc_content.get("title", code_value.replace("_", " ").title())
    description = doc_content.get(
        "description", f"Error related to {category}: {code_value.replace('_', ' ')}."
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

    # Build the entry content
    content = f"""### {code_name}: {title} {{#{code_name.lower()}}}

{description}

**Common Causes**
{causes_md}

**How to Fix**
{fix_md}
"""

    if example:
        content += f"""
**Example**

{example}
"""

    content += "\n---\n"

    return content


def generate_glossary_page(codes: list[tuple[str, str, str]]) -> str:
    """Generate the error code glossary page."""
    # Group codes by category
    categories: dict[str, list[tuple[str, str]]] = {}
    for code_name, code_value, category in codes:
        if category not in categories:
            categories[category] = []
        categories[category].append((code_name, code_value))

    # Build category table (sorted alphabetically by prefix)
    category_info = []
    for cat in categories:
        prefix = get_category_prefix(cat)
        name = get_category_display_name(cat)
        desc = get_category_description(cat)
        category_info.append((prefix, name, cat, desc))
    category_info.sort(key=lambda x: x[0])

    category_rows = [f"| {p} | {n} | {d} |" for p, n, _, d in category_info]
    category_table = "\n".join(category_rows)

    # Define category order for sections
    category_order = [
        "cache",
        "config",
        "discovery",
        "graph",
        "content",
        "parsing",
        "rendering",
        "server",
        "template_function",
        "asset",
    ]

    # Build sections for each category
    sections = []
    for cat in category_order:
        if cat not in categories:
            continue

        cat_codes = sorted(categories[cat], key=lambda x: x[0])
        prefix = get_category_prefix(cat)
        display_name = get_category_display_name(cat)

        section_header = f"## {display_name} Errors ({prefix}xxx) {{#{cat}}}\n"

        entries = []
        for code_name, code_value in cat_codes:
            entries.append(generate_error_entry(code_name, code_value, cat))

        sections.append(section_header + "\n" + "\n".join(entries))

    all_sections = "\n".join(sections)

    return f"""---
title: Error Code Reference
nav_title: Error Codes
description: Complete reference for all Bengal error codes with explanations and solutions
weight: 50
icon: alert-triangle
tags: [reference, errors, troubleshooting]
---

# Error Code Reference

Bengal uses prefixed error codes for quick identification and searchability. Each code links to its entry below with explanations and solutions.

## Error Categories

| Prefix | Category | Description |
|--------|----------|-------------|
{category_table}

---

{all_sections}

## Getting Help

If you encounter an error:

1. Check the error message and suggestion in the CLI output
2. Search this page for the error code (Ctrl+F / Cmd+F)
3. Review the troubleshooting steps above
4. Check the [troubleshooting guide](/docs/guides/troubleshooting/)

For bugs or unclear errors, please [open an issue](https://github.com/bengal-ssg/bengal/issues).
"""


def main() -> None:
    """Generate error documentation as a single glossary page."""
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

    # Remove old individual error pages
    for md_file in output_dir.glob("*.md"):
        if md_file.name != "_index.md":
            md_file.unlink()
            print(f"Removed: {md_file}")

    # Collect all codes
    codes: list[tuple[str, str, str]] = []
    for code in ErrorCode:
        codes.append((code.name, code.value, code.category))

    # Generate glossary page
    glossary_content = generate_glossary_page(codes)
    index_path = output_dir / "_index.md"
    index_path.write_text(glossary_content)
    print(f"Generated: {index_path}")

    print(f"\n✓ Generated glossary page with {len(codes)} error codes")
    print(f"  Output: {index_path}")


if __name__ == "__main__":
    main()
