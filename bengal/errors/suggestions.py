"""
Actionable error suggestions for user-facing messages.

Provides consistent, helpful suggestions for common errors across Bengal.
Each suggestion includes:
- What went wrong
- How to fix it
- Link to documentation (when available)

Usage:
    from bengal.errors import get_suggestion, format_suggestion

    # Get suggestion for a specific error pattern
    suggestion = get_suggestion("directive", "since_empty")

    # Format suggestion for logging
    formatted = format_suggestion("directive", "since_empty")
"""

from __future__ import annotations

from typing import Any

# Centralized suggestion registry
# Format: category -> error_key -> (short_fix, detailed_explanation, doc_link)
_SUGGESTIONS: dict[str, dict[str, tuple[str, str, str | None]]] = {
    # Directive errors
    "directive": {
        "since_empty": (
            "Add version number: ```{since} 1.0.0```",
            "The {since} directive marks when a feature was added. Specify the version.",
            "/docs/directives/versioning/",
        ),
        "deprecated_empty": (
            "Add version number: ```{deprecated} 2.0.0```",
            "The {deprecated} directive marks when a feature was deprecated. Specify the version.",
            "/docs/directives/versioning/",
        ),
        "changed_empty": (
            "Add version number: ```{changed} 1.5.0```",
            "The {changed} directive marks when behavior changed. Specify the version.",
            "/docs/directives/versioning/",
        ),
        "glossary_parse_error": (
            "Check YAML syntax in glossary file",
            "Glossary files must be valid YAML with 'terms' list containing keys.",
            "/docs/directives/glossary/",
        ),
        "include_file_not_found": (
            "Verify the file path is relative to content directory",
            "Include paths are resolved relative to the content directory root.",
            "/docs/directives/include/",
        ),
        "literalinclude_file_not_found": (
            "Verify the file path is relative to site root",
            "Literalinclude paths are resolved relative to the site root directory.",
            "/docs/directives/literalinclude/",
        ),
    },
    # Config errors
    "config": {
        "defaults_missing": (
            "Create config/_default/ directory with base configuration",
            "Bengal expects a config/_default/ directory with yaml files for base settings.",
            "/docs/configuration/",
        ),
        "yaml_parse_error": (
            "Check YAML syntax (indentation, colons, quotes)",
            "Common issues: inconsistent indentation, missing colons, unquoted special characters.",
            "/docs/configuration/",
        ),
        "unknown_environment": (
            "Create config/environments/{env}.yaml or use 'development'/'production'",
            "Environment configs override defaults. Available: development, production, or custom.",
            "/docs/configuration/environments/",
        ),
    },
    # Template/rendering errors
    "template": {
        "not_found": (
            "Check template exists in themes/{theme}/templates/ or templates/",
            "Templates are loaded from theme directory first, then site templates/.",
            "/docs/templating/",
        ),
        "syntax_error": (
            "Check Jinja2 syntax (braces, filters, blocks)",
            "Common issues: unclosed {{ }}, missing {% endif %}, invalid filter.",
            "/docs/templating/jinja2/",
        ),
        "undefined_variable": (
            "Variable not available in template context",
            "Use {{ variable | default('fallback') }} for optional variables.",
            "/docs/templating/context/",
        ),
    },
    # Attribute errors (from unified URL model migration)
    "attribute": {
        "page_url": (
            "Use .href instead",
            "Page.url was renamed to .href for template URLs (includes baseurl).",
            "/docs/migration/url-model/",
        ),
        "page_relative_url": (
            "Use ._path instead",
            "Page.relative_url was renamed to ._path for internal path comparisons.",
            "/docs/migration/url-model/",
        ),
        "page_site_path": (
            "Use ._path instead",
            "Page.site_path was renamed to ._path for internal path comparisons.",
            "/docs/migration/url-model/",
        ),
        "page_permalink": (
            "Use .href instead",
            "Page.permalink was renamed to .href for consistency.",
            "/docs/migration/url-model/",
        ),
    },
    # Asset errors
    "asset": {
        "not_found": (
            "Verify asset exists in assets/ or static/ directory",
            "Assets are loaded from assets/, static/, and theme directories.",
            "/docs/assets/",
        ),
        "invalid_path": (
            "Use forward slashes and avoid ..",
            "Asset paths must be relative, use forward slashes, no directory traversal.",
            "/docs/assets/",
        ),
        "processing_failed": (
            "Check file format and permissions",
            "Asset processing may fail due to corrupt files or missing dependencies.",
            "/docs/assets/troubleshooting/",
        ),
    },
    # Content errors
    "content": {
        "frontmatter_invalid": (
            "Check YAML frontmatter syntax between --- delimiters",
            "Frontmatter must be valid YAML. Check for unquoted colons in titles.",
            "/docs/content/frontmatter/",
        ),
        "date_invalid": (
            "Use ISO format: YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS",
            "Dates must be valid ISO 8601 format.",
            "/docs/content/frontmatter/#date",
        ),
    },
    # Parsing errors
    "parsing": {
        "markdown_error": (
            "Check markdown syntax",
            "Markdown parsing errors usually indicate malformed syntax.",
            "/docs/content/markdown/",
        ),
        "toc_extraction_error": (
            "Check heading structure",
            "TOC extraction may fail with malformed or deeply nested headings.",
            "/docs/content/markdown/#table-of-contents",
        ),
    },
}


def get_suggestion(category: str, error_key: str) -> dict[str, str] | None:
    """
    Get actionable suggestion for an error.

    Args:
        category: Error category (directive, config, template, etc.)
        error_key: Specific error identifier

    Returns:
        Dict with 'fix', 'explanation', and optional 'docs_url', or None
    """
    if category not in _SUGGESTIONS:
        return None

    if error_key not in _SUGGESTIONS[category]:
        return None

    fix, explanation, docs_url = _SUGGESTIONS[category][error_key]
    result = {
        "fix": fix,
        "explanation": explanation,
    }
    if docs_url:
        result["docs_url"] = docs_url
    return result


def enhance_error_context(
    context: dict[str, Any],
    category: str,
    error_key: str,
) -> dict[str, Any]:
    """
    Enhance error context dict with actionable suggestion.

    Args:
        context: Existing error context dict
        category: Error category
        error_key: Specific error identifier

    Returns:
        Context dict with 'suggestion' added if available
    """
    suggestion = get_suggestion(category, error_key)
    if suggestion:
        context["suggestion"] = suggestion["fix"]
        if "docs_url" in suggestion:
            context["docs_url"] = suggestion["docs_url"]
    return context


def format_suggestion(category: str, error_key: str) -> str | None:
    """
    Format suggestion as a single string for logging.

    Args:
        category: Error category
        error_key: Specific error identifier

    Returns:
        Formatted suggestion string or None
    """
    suggestion = get_suggestion(category, error_key)
    if not suggestion:
        return None

    result = f"Fix: {suggestion['fix']}"
    if "docs_url" in suggestion:
        result += f" (see {suggestion['docs_url']})"
    return result


# Pattern-based matching for AttributeError messages
# Maps error message fragments to (category, key) for lookup
_ATTRIBUTE_ERROR_PATTERNS: dict[str, tuple[str, str]] = {
    "has no attribute 'url'": ("attribute", "page_url"),
    "has no attribute 'relative_url'": ("attribute", "page_relative_url"),
    "has no attribute 'site_path'": ("attribute", "page_site_path"),
    "has no attribute 'permalink'": ("attribute", "page_permalink"),
}


def get_attribute_error_suggestion(error_msg: str) -> str | None:
    """
    Get actionable suggestion for AttributeError based on error message.

    Pattern-matches the error message against known migrations and returns
    a formatted suggestion string.

    Args:
        error_msg: The error message from AttributeError

    Returns:
        Formatted suggestion string or None if no match
    """
    for pattern, (category, key) in _ATTRIBUTE_ERROR_PATTERNS.items():
        if pattern in error_msg:
            suggestion = get_suggestion(category, key)
            if suggestion:
                return f"{suggestion['fix']}. {suggestion['explanation']}"
    return None
