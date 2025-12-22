"""
Actionable error suggestions for user-facing messages.

This module provides a centralized registry of actionable suggestions
for common errors across Bengal. Each suggestion includes:

- **Fix**: Short one-line fix description
- **Explanation**: What went wrong and why
- **Code Snippets**: Before/after examples showing the fix
- **Documentation Link**: URL to relevant documentation
- **Files to Check**: Source files to investigate
- **Grep Patterns**: Search patterns for codebase investigation
- **Related Codes**: Associated error codes

Suggestion Categories
=====================

- **directive**: Version directives (since, deprecated, changed), glossary, include
- **config**: Configuration errors (YAML, missing keys, environments)
- **template**: Rendering errors (not found, syntax, undefined variables)
- **attribute**: Attribute errors (URL model migration helpers)
- **asset**: Asset errors (not found, invalid path, processing)
- **content**: Content errors (frontmatter, dates, encoding)
- **parsing**: Parse errors (markdown, TOC extraction)
- **cache**: Cache errors (corruption, version mismatch)
- **server**: Server errors (port in use)

Functions
=========

**get_suggestion(category, error_key)**
    Get an ``ActionableSuggestion`` for a specific error pattern.

**format_suggestion(category, error_key)**
    Format a suggestion as a string for logging.

**format_suggestion_full(category, error_key)**
    Format a complete suggestion with all details.

**get_attribute_error_suggestion(error_msg)**
    Pattern-match AttributeError messages to URL model migrations.

**search_suggestions(query)**
    Search suggestions by keyword across all categories.

Usage
=====

Get a suggestion::

    from bengal.errors import get_suggestion

    suggestion = get_suggestion("template", "not_found")
    print(suggestion.fix)
    print(suggestion.after_snippet)

Format for logging::

    from bengal.errors import format_suggestion

    formatted = format_suggestion("directive", "since_empty")
    logger.info(formatted)

Search for suggestions::

    from bengal.errors import search_suggestions

    results = search_suggestions("template")
    for category, key, suggestion in results:
        print(f"{category}.{key}: {suggestion.fix}")

See Also
========

- ``bengal/errors/exceptions.py`` - Exception classes using suggestions
- ``bengal/errors/handlers.py`` - Runtime error handlers
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ActionableSuggestion:
    """
    A structured, actionable suggestion for fixing an error.

    Attributes:
        fix: Short one-line fix description
        explanation: Longer explanation of what went wrong
        docs_url: Link to documentation
        before_snippet: Example of broken code
        after_snippet: Example of fixed code
        check_files: Files to investigate for this error
        related_codes: Related error codes
        grep_patterns: Patterns to search for in codebase
    """

    fix: str
    explanation: str
    docs_url: str | None = None
    before_snippet: str | None = None
    after_snippet: str | None = None
    check_files: list[str] = field(default_factory=list)
    related_codes: list[str] = field(default_factory=list)
    grep_patterns: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "fix": self.fix,
            "explanation": self.explanation,
            "docs_url": self.docs_url,
            "before_snippet": self.before_snippet,
            "after_snippet": self.after_snippet,
            "check_files": self.check_files,
            "related_codes": self.related_codes,
            "grep_patterns": self.grep_patterns,
        }


# Centralized suggestion registry with ActionableSuggestion
_SUGGESTIONS: dict[str, dict[str, ActionableSuggestion]] = {
    # ============================================================
    # Directive errors
    # ============================================================
    "directive": {
        "since_empty": ActionableSuggestion(
            fix="Add version number: ```{since} 1.0.0```",
            explanation="The {since} directive marks when a feature was added. Specify the version.",
            docs_url="/docs/directives/versioning/",
            before_snippet="```{since}\n```",
            after_snippet="```{since} 1.0.0\nNew feature description\n```",
            check_files=["bengal/directives/versioning.py"],
            related_codes=["T006"],
            grep_patterns=["since_directive", "VersionDirective"],
        ),
        "deprecated_empty": ActionableSuggestion(
            fix="Add version number: ```{deprecated} 2.0.0```",
            explanation="The {deprecated} directive marks when a feature was deprecated. Specify the version.",
            docs_url="/docs/directives/versioning/",
            before_snippet="```{deprecated}\n```",
            after_snippet="```{deprecated} 2.0.0\nUse new_feature instead\n```",
            check_files=["bengal/directives/versioning.py"],
            related_codes=["T007"],
            grep_patterns=["deprecated_directive", "VersionDirective"],
        ),
        "changed_empty": ActionableSuggestion(
            fix="Add version number: ```{changed} 1.5.0```",
            explanation="The {changed} directive marks when behavior changed. Specify the version.",
            docs_url="/docs/directives/versioning/",
            before_snippet="```{changed}\n```",
            after_snippet="```{changed} 1.5.0\nBehavior now does X instead of Y\n```",
            check_files=["bengal/directives/versioning.py"],
            related_codes=["T008"],
            grep_patterns=["changed_directive", "VersionDirective"],
        ),
        "glossary_parse_error": ActionableSuggestion(
            fix="Check YAML syntax in glossary file",
            explanation="Glossary files must be valid YAML with 'terms' list containing keys.",
            docs_url="/docs/directives/glossary/",
            before_snippet="terms\n  - key: value",  # Invalid YAML
            after_snippet="terms:\n  - key: value\n    definition: explanation",
            check_files=["bengal/directives/glossary.py", "data/*.yaml"],
            related_codes=["P006"],
            grep_patterns=["GlossaryDirective", "parse_glossary"],
        ),
        "include_file_not_found": ActionableSuggestion(
            fix="Verify the file path is relative to content directory",
            explanation="Include paths are resolved relative to the content directory root.",
            docs_url="/docs/directives/include/",
            before_snippet="```{include} /path/to/file.md\n```",
            after_snippet="```{include} snippets/example.md\n```",
            check_files=["bengal/directives/include.py", "content/"],
            related_codes=["T009", "N004"],
            grep_patterns=["IncludeDirective", "resolve_include_path"],
        ),
        "literalinclude_file_not_found": ActionableSuggestion(
            fix="Verify the file path is relative to site root",
            explanation="Literalinclude paths are resolved relative to the site root directory.",
            docs_url="/docs/directives/literalinclude/",
            before_snippet="```{literalinclude} /absolute/path.py\n```",
            after_snippet="```{literalinclude} examples/code.py\n:lines: 1-10\n```",
            check_files=["bengal/directives/literalinclude.py"],
            related_codes=["T009", "N004"],
            grep_patterns=["LiteralIncludeDirective", "resolve_literal_path"],
        ),
    },
    # ============================================================
    # Config errors
    # ============================================================
    "config": {
        "defaults_missing": ActionableSuggestion(
            fix="Create config/_default/ directory with base configuration",
            explanation="Bengal expects a config/_default/ directory with yaml files for base settings.",
            docs_url="/docs/configuration/",
            before_snippet="# Missing: config/_default/",
            after_snippet="config/_default/\n├── site.yaml\n├── params.yaml\n└── menus.yaml",
            check_files=["bengal/config/loader.py", "config/_default/"],
            related_codes=["C005"],
            grep_patterns=["load_config", "DEFAULT_CONFIG"],
        ),
        "yaml_parse_error": ActionableSuggestion(
            fix="Check YAML syntax (indentation, colons, quotes)",
            explanation="Common issues: inconsistent indentation, missing colons, unquoted special characters.",
            docs_url="/docs/configuration/",
            before_snippet="title:My Site  # Missing space after colon",
            after_snippet='title: "My Site"  # Quoted string with proper spacing',
            check_files=["config/"],
            related_codes=["C001", "P001"],
            grep_patterns=["yaml.safe_load", "YAMLError"],
        ),
        "unknown_environment": ActionableSuggestion(
            fix="Create config/environments/{env}.yaml or use 'development'/'production'",
            explanation="Environment configs override defaults. Available: development, production, or custom.",
            docs_url="/docs/configuration/environments/",
            before_snippet="# Missing: config/environments/staging.yaml",
            after_snippet="# Create config/environments/staging.yaml\nbaseurl: https://staging.example.com",
            check_files=["bengal/config/loader.py", "config/environments/"],
            related_codes=["C006"],
            grep_patterns=["load_environment_config", "ENVIRONMENT"],
        ),
        "invalid_value": ActionableSuggestion(
            fix="Check the value type and format in configuration",
            explanation="Configuration values must match expected types (string, number, list, etc.).",
            docs_url="/docs/configuration/reference/",
            before_snippet='pagination: "yes"  # Should be number or boolean',
            after_snippet="pagination: 10  # Number of items per page",
            check_files=["bengal/config/schema.py"],
            related_codes=["C003"],
            grep_patterns=["validate_config", "ConfigSchema"],
        ),
    },
    # ============================================================
    # Template/rendering errors
    # ============================================================
    "template": {
        "not_found": ActionableSuggestion(
            fix="Check template exists in themes/{theme}/templates/ or templates/",
            explanation="Templates are loaded from theme directory first, then site templates/.",
            docs_url="/docs/templating/",
            before_snippet="layout: custom-layout  # Template not found",
            after_snippet="# Create themes/default/templates/custom-layout.html\n# Or: templates/custom-layout.html",
            check_files=[
                "bengal/rendering/template_engine.py",
                "themes/",
                "templates/",
            ],
            related_codes=["R001"],
            grep_patterns=["get_template", "TemplateNotFound", "template_loader"],
        ),
        "syntax_error": ActionableSuggestion(
            fix="Check Jinja2 syntax (braces, filters, blocks)",
            explanation="Common issues: unclosed {{ }}, missing {% endif %}, invalid filter.",
            docs_url="/docs/templating/jinja2/",
            before_snippet="{% if condition %}\n  Content\n# Missing: {% endif %}",
            after_snippet="{% if condition %}\n  Content\n{% endif %}",
            check_files=["bengal/rendering/template_engine.py"],
            related_codes=["R002"],
            grep_patterns=["TemplateSyntaxError", "render_template"],
        ),
        "undefined_variable": ActionableSuggestion(
            fix="Use {{ variable | default('fallback') }} for optional variables",
            explanation="Variable not available in template context. Use default filter for optional values.",
            docs_url="/docs/templating/context/",
            before_snippet="{{ page.author.name }}  # May be undefined",
            after_snippet="{{ page.author.name | default('Unknown Author') }}",
            check_files=[
                "bengal/rendering/template_context.py",
                "bengal/rendering/template_engine.py",
            ],
            related_codes=["R003"],
            grep_patterns=["UndefinedError", "template_context", "StrictUndefined"],
        ),
        "filter_error": ActionableSuggestion(
            fix="Check filter name and arguments",
            explanation="Filter may not exist or received wrong argument types.",
            docs_url="/docs/templating/filters/",
            before_snippet="{{ content | unknownfilter }}",
            after_snippet="{{ content | safe }}  # Use built-in filter",
            check_files=["bengal/rendering/filters.py"],
            related_codes=["R004"],
            grep_patterns=["register_filter", "jinja_filters"],
        ),
        "context_error": ActionableSuggestion(
            fix="Check template context building in render orchestrator",
            explanation="Template context may be missing expected variables.",
            docs_url="/docs/templating/context/",
            before_snippet="# Context missing expected variable",
            after_snippet="# Check bengal/rendering/template_context.py\n# Ensure variable is added to context",
            check_files=[
                "bengal/rendering/template_context.py",
                "bengal/orchestration/render.py",
            ],
            related_codes=["R008"],
            grep_patterns=["build_context", "template_context", "PageContext"],
        ),
    },
    # ============================================================
    # Attribute errors (URL model migration)
    # ============================================================
    "attribute": {
        "page_url": ActionableSuggestion(
            fix="Use .href instead",
            explanation="Page.url was renamed to .href for template URLs (includes baseurl).",
            docs_url="/docs/migration/url-model/",
            before_snippet="{{ page.url }}",
            after_snippet="{{ page.href }}",
            check_files=["bengal/core/page/navigation.py"],
            related_codes=["R003"],
            grep_patterns=[r"\.url\b", "page.href"],
        ),
        "page_relative_url": ActionableSuggestion(
            fix="Use ._path instead",
            explanation="Page.relative_url was renamed to ._path for internal path comparisons.",
            docs_url="/docs/migration/url-model/",
            before_snippet="{{ page.relative_url }}",
            after_snippet="{{ page._path }}",
            check_files=["bengal/core/page/navigation.py"],
            related_codes=["R003"],
            grep_patterns=[r"\.relative_url", "page._path"],
        ),
        "page_site_path": ActionableSuggestion(
            fix="Use ._path instead",
            explanation="Page.site_path was renamed to ._path for internal path comparisons.",
            docs_url="/docs/migration/url-model/",
            before_snippet="page.site_path",
            after_snippet="page._path",
            check_files=["bengal/core/page/navigation.py"],
            related_codes=["R003"],
            grep_patterns=[r"\.site_path", "page._path"],
        ),
        "page_permalink": ActionableSuggestion(
            fix="Use .href instead",
            explanation="Page.permalink was renamed to .href for consistency.",
            docs_url="/docs/migration/url-model/",
            before_snippet="{{ page.permalink }}",
            after_snippet="{{ page.href }}",
            check_files=["bengal/core/page/navigation.py"],
            related_codes=["R003"],
            grep_patterns=[r"\.permalink", "page.href"],
        ),
    },
    # ============================================================
    # Asset errors
    # ============================================================
    "asset": {
        "not_found": ActionableSuggestion(
            fix="Verify asset exists in assets/ or static/ directory",
            explanation="Assets are loaded from assets/, static/, and theme directories.",
            docs_url="/docs/assets/",
            before_snippet='<link href="/missing.css">',
            after_snippet="# Place file in: assets/css/style.css or static/style.css",
            check_files=["bengal/assets/", "assets/", "static/"],
            related_codes=["X001"],
            grep_patterns=["find_asset", "asset_not_found"],
        ),
        "invalid_path": ActionableSuggestion(
            fix="Use forward slashes and avoid ..",
            explanation="Asset paths must be relative, use forward slashes, no directory traversal.",
            docs_url="/docs/assets/",
            before_snippet="assets\\..\\secret.txt",
            after_snippet="assets/images/logo.png",
            check_files=["bengal/assets/resolver.py"],
            related_codes=["X002"],
            grep_patterns=["validate_asset_path", "path_traversal"],
        ),
        "processing_failed": ActionableSuggestion(
            fix="Check file format and permissions",
            explanation="Asset processing may fail due to corrupt files or missing dependencies.",
            docs_url="/docs/assets/troubleshooting/",
            before_snippet="# Corrupt or unsupported file",
            after_snippet="# Check file with: file assets/image.png\n# Check permissions: ls -la assets/",
            check_files=["bengal/assets/processor.py"],
            related_codes=["X003"],
            grep_patterns=["process_asset", "AssetProcessingError"],
        ),
    },
    # ============================================================
    # Content errors
    # ============================================================
    "content": {
        "frontmatter_invalid": ActionableSuggestion(
            fix="Check YAML frontmatter syntax between --- delimiters",
            explanation="Frontmatter must be valid YAML. Check for unquoted colons in titles.",
            docs_url="/docs/content/frontmatter/",
            before_snippet="---\ntitle: My Post: A Story\n---",
            after_snippet='---\ntitle: "My Post: A Story"\n---',
            check_files=["bengal/rendering/frontmatter.py"],
            related_codes=["N001", "P001"],
            grep_patterns=["parse_frontmatter", "frontmatter_error"],
        ),
        "date_invalid": ActionableSuggestion(
            fix="Use ISO format: YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS",
            explanation="Dates must be valid ISO 8601 format.",
            docs_url="/docs/content/frontmatter/#date",
            before_snippet="date: January 15, 2024",
            after_snippet="date: 2024-01-15\n# Or with time: 2024-01-15T10:30:00",
            check_files=["bengal/core/page/metadata.py"],
            related_codes=["N002"],
            grep_patterns=["parse_date", "DateParseError"],
        ),
        "encoding_error": ActionableSuggestion(
            fix="Save file with UTF-8 encoding",
            explanation="Content files should be UTF-8 encoded. Check for special characters.",
            docs_url="/docs/content/",
            before_snippet="# File saved with Windows-1252 or other encoding",
            after_snippet="# Save with UTF-8: In VS Code, click encoding in status bar",
            check_files=["bengal/discovery/content.py"],
            related_codes=["N003"],
            grep_patterns=["encoding", "UnicodeDecodeError"],
        ),
    },
    # ============================================================
    # Parsing errors
    # ============================================================
    "parsing": {
        "markdown_error": ActionableSuggestion(
            fix="Check markdown syntax",
            explanation="Markdown parsing errors usually indicate malformed syntax.",
            docs_url="/docs/content/markdown/",
            before_snippet="[broken link(missing bracket)",
            after_snippet="[fixed link](https://example.com)",
            check_files=["bengal/rendering/markdown_parser.py"],
            related_codes=["P004", "N005"],
            grep_patterns=["MarkdownParser", "parse_markdown"],
        ),
        "toc_extraction_error": ActionableSuggestion(
            fix="Check heading structure",
            explanation="TOC extraction may fail with malformed or deeply nested headings.",
            docs_url="/docs/content/markdown/#table-of-contents",
            before_snippet="####### Too deep heading (max is ######)",
            after_snippet="###### Maximum depth heading",
            check_files=["bengal/rendering/toc.py"],
            related_codes=["N007"],
            grep_patterns=["extract_toc", "TocExtractor"],
        ),
    },
    # ============================================================
    # Cache errors
    # ============================================================
    "cache": {
        "corruption": ActionableSuggestion(
            fix="Clear cache with: rm -rf .bengal/cache/ or bengal build --no-cache",
            explanation="Cache files may be corrupted. Safe to delete and rebuild.",
            docs_url="/docs/configuration/cache/",
            before_snippet="# Cache corruption detected",
            after_snippet="rm -rf .bengal/cache/\nbengal build",
            check_files=["bengal/cache/"],
            related_codes=["A001"],
            grep_patterns=["CacheCorruption", "validate_cache"],
        ),
        "version_mismatch": ActionableSuggestion(
            fix="Clear cache after Bengal upgrade: bengal build --no-cache",
            explanation="Cache format changed between versions. Clear cache to rebuild.",
            docs_url="/docs/configuration/cache/",
            before_snippet="# Cache version mismatch after upgrade",
            after_snippet="bengal build --no-cache",
            check_files=["bengal/cache/version.py"],
            related_codes=["A002"],
            grep_patterns=["CACHE_VERSION", "version_mismatch"],
        ),
    },
    # ============================================================
    # Server errors
    # ============================================================
    "server": {
        "port_in_use": ActionableSuggestion(
            fix="Use different port: bengal serve --port 8080",
            explanation="Port 1313 (default) is already in use by another process.",
            docs_url="/docs/cli/serve/",
            before_snippet="# Port 1313 already in use",
            after_snippet="bengal serve --port 8080\n# Or find process: lsof -i :1313",
            check_files=["bengal/server/"],
            related_codes=["S001"],
            grep_patterns=["port_in_use", "bind_error"],
        ),
    },
}


def get_suggestion(category: str, error_key: str) -> ActionableSuggestion | None:
    """
    Get actionable suggestion for an error.

    Args:
        category: Error category (directive, config, template, etc.)
        error_key: Specific error identifier

    Returns:
        ActionableSuggestion if found, None otherwise
    """
    if category not in _SUGGESTIONS:
        return None

    return _SUGGESTIONS[category].get(error_key)


def get_suggestion_dict(category: str, error_key: str) -> dict[str, Any] | None:
    """
    Get suggestion as dictionary.

    Args:
        category: Error category
        error_key: Specific error identifier

    Returns:
        Dict with 'fix', 'explanation', and optional 'docs_url', or None
    """
    suggestion = get_suggestion(category, error_key)
    if not suggestion:
        return None

    result = {
        "fix": suggestion.fix,
        "explanation": suggestion.explanation,
    }
    if suggestion.docs_url:
        result["docs_url"] = suggestion.docs_url
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
        context["suggestion"] = suggestion.fix
        if suggestion.docs_url:
            context["docs_url"] = suggestion.docs_url
        if suggestion.check_files:
            context["check_files"] = suggestion.check_files
        if suggestion.grep_patterns:
            context["grep_patterns"] = suggestion.grep_patterns
    return context


def format_suggestion(
    category: str, error_key: str, *, include_snippets: bool = False
) -> str | None:
    """
    Format suggestion as a string for logging.

    Args:
        category: Error category
        error_key: Specific error identifier
        include_snippets: Whether to include code snippets

    Returns:
        Formatted suggestion string or None
    """
    suggestion = get_suggestion(category, error_key)
    if not suggestion:
        return None

    parts = [f"Fix: {suggestion.fix}"]

    if include_snippets and suggestion.before_snippet and suggestion.after_snippet:
        parts.append(f"\nBefore:\n{suggestion.before_snippet}")
        parts.append(f"\nAfter:\n{suggestion.after_snippet}")

    if suggestion.docs_url:
        parts.append(f"\nDocs: {suggestion.docs_url}")

    return "\n".join(parts)


def format_suggestion_full(category: str, error_key: str) -> str | None:
    """
    Format full suggestion with all details.

    Args:
        category: Error category
        error_key: Specific error identifier

    Returns:
        Fully formatted suggestion string or None
    """
    suggestion = get_suggestion(category, error_key)
    if not suggestion:
        return None

    parts = [
        f"Fix: {suggestion.fix}",
        f"Explanation: {suggestion.explanation}",
    ]

    if suggestion.before_snippet and suggestion.after_snippet:
        parts.append(f"\n❌ Before:\n{suggestion.before_snippet}")
        parts.append(f"\n✅ After:\n{suggestion.after_snippet}")

    if suggestion.check_files:
        parts.append(f"\nFiles to check: {', '.join(suggestion.check_files)}")

    if suggestion.related_codes:
        parts.append(f"Related error codes: {', '.join(suggestion.related_codes)}")

    if suggestion.docs_url:
        parts.append(f"Documentation: {suggestion.docs_url}")

    return "\n".join(parts)


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
                return f"{suggestion.fix}. {suggestion.explanation}"
    return None


def get_all_suggestions_for_category(category: str) -> dict[str, ActionableSuggestion]:
    """
    Get all suggestions for a category.

    Args:
        category: Error category

    Returns:
        Dictionary of error_key -> ActionableSuggestion
    """
    return _SUGGESTIONS.get(category, {})


def search_suggestions(query: str) -> list[tuple[str, str, ActionableSuggestion]]:
    """
    Search suggestions by keyword.

    Args:
        query: Search query (searches fix, explanation, and patterns)

    Returns:
        List of (category, key, suggestion) tuples matching query
    """
    query_lower = query.lower()
    results = []

    for category, suggestions in _SUGGESTIONS.items():
        for key, suggestion in suggestions.items():
            # Search in fix, explanation, and patterns
            searchable = (
                suggestion.fix.lower()
                + suggestion.explanation.lower()
                + " ".join(suggestion.grep_patterns).lower()
            )
            if query_lower in searchable:
                results.append((category, key, suggestion))

    return results
