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

import re
import traceback
from dataclasses import dataclass, field
from difflib import get_close_matches
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Iterable
    from pathlib import Path


@dataclass(frozen=True, slots=True)
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
            check_files=["bengal/core/page/__init__.py", "bengal/core/page/metadata_helpers.py"],
            related_codes=["N002"],
            grep_patterns=["parse_date", "DateParseError"],
        ),
        "encoding_error": ActionableSuggestion(
            fix="Save file with UTF-8 encoding",
            explanation="Content files should be UTF-8 encoded. Check for special characters.",
            docs_url="/docs/content/",
            before_snippet="# File saved with Windows-1252 or other encoding",
            after_snippet="# Save with UTF-8: In VS Code, click encoding in status bar",
            check_files=["bengal/content/discovery/content_parser.py"],
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
            check_files=["bengal/parsing/__init__.py"],
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
            fix="Clear cache with: bengal clean --cache && bengal build",
            explanation="Cache files may be corrupted. Safe to delete and rebuild.",
            docs_url="/docs/configuration/cache/",
            before_snippet="# Cache corruption detected",
            after_snippet="bengal clean --cache\nbengal build",
            check_files=["bengal/cache/"],
            related_codes=["A001"],
            grep_patterns=["CacheCorruption", "validate_cache"],
        ),
        "version_mismatch": ActionableSuggestion(
            fix="Clear cache after Bengal upgrade: bengal clean --cache && bengal build",
            explanation="Cache format changed between versions. Clear cache to rebuild.",
            docs_url="/docs/configuration/cache/",
            before_snippet="# Cache version mismatch after upgrade",
            after_snippet="bengal clean --cache\nbengal build",
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
    # ============================================================
    # Autodoc errors
    # ============================================================
    "autodoc": {
        "extraction_failed": ActionableSuggestion(
            fix="Check if the source module is importable and has no syntax errors",
            explanation="Autodoc failed to extract elements from the specified source.",
            docs_url="/docs/autodoc/",
            before_snippet="# Module with syntax error or missing import",
            after_snippet="# Fix syntax errors and ensure all imports are available",
            check_files=["bengal/autodoc/", "bengal/autodoc/extractors/"],
            related_codes=["O001"],
            grep_patterns=["autodoc_extract", "AutodocExtractor"],
        ),
        "cache_corruption": ActionableSuggestion(
            fix="Clear autodoc cache: rm -rf .bengal/cache/autodoc/",
            explanation="Autodoc cache format is corrupted or incompatible with current version.",
            docs_url="/docs/autodoc/cache/",
            before_snippet="# Cache file has invalid format",
            after_snippet="rm -rf .bengal/cache/autodoc/\nbengal build",
            check_files=["bengal/autodoc/base.py", "bengal/autodoc/orchestration/"],
            related_codes=["A001", "O001"],
            grep_patterns=["autodoc_cache", "from_cache_dict", "CACHE_VERSION"],
        ),
        "syntax_error": ActionableSuggestion(
            fix="Fix Python syntax errors in the source file",
            explanation="Autodoc cannot parse files with syntax errors.",
            docs_url="/docs/autodoc/",
            before_snippet="# Python file with syntax error",
            after_snippet="# Run: python -m py_compile <source_file>",
            check_files=["bengal/autodoc/extractors/python.py"],
            related_codes=["O002"],
            grep_patterns=["SyntaxError", "parse_python"],
        ),
        "openapi_parse_failed": ActionableSuggestion(
            fix="Check OpenAPI spec for valid YAML/JSON syntax",
            explanation="OpenAPI specification file could not be parsed.",
            docs_url="/docs/autodoc/openapi/",
            before_snippet="# Invalid OpenAPI YAML/JSON",
            after_snippet="# Validate with: npx @redocly/cli lint openapi.yaml",
            check_files=["bengal/autodoc/extractors/openapi.py"],
            related_codes=["O003"],
            grep_patterns=["openapi_parse", "OpenAPIExtractor"],
        ),
    },
    # ============================================================
    # Validator/Health errors
    # ============================================================
    "validator": {
        "crashed": ActionableSuggestion(
            fix="Check validator implementation for unhandled exceptions",
            explanation="A health validator raised an unhandled exception.",
            docs_url="/docs/health/validators/",
            before_snippet="# Validator raised exception",
            after_snippet="# Check bengal/health/validators/ for the failing validator",
            check_files=["bengal/health/validators/", "bengal/health/check.py"],
            related_codes=["V001"],
            grep_patterns=["Validator", "health_check"],
        ),
        "linkcheck_timeout": ActionableSuggestion(
            fix="Increase timeout or check network connectivity",
            explanation="External link check timed out while verifying URLs.",
            docs_url="/docs/health/linkcheck/",
            before_snippet="# Link check timed out",
            after_snippet="bengal health linkcheck --timeout 60\n# Or skip external: bengal health linkcheck --internal-only",
            check_files=["bengal/health/validators/links.py"],
            related_codes=["V004"],
            grep_patterns=["linkcheck", "timeout", "aiohttp"],
        ),
        "linkcheck_network_error": ActionableSuggestion(
            fix="Check network connectivity and firewall settings",
            explanation="Network error occurred while checking external links.",
            docs_url="/docs/health/linkcheck/",
            before_snippet="# Network error during link check",
            after_snippet="# Check if URLs are accessible: curl -I <url>",
            check_files=["bengal/health/validators/links.py"],
            related_codes=["V005"],
            grep_patterns=["linkcheck", "network_error", "ClientError"],
        ),
    },
    # ============================================================
    # Build errors
    # ============================================================
    "build": {
        "phase_failed": ActionableSuggestion(
            fix="Check build logs for the specific phase that failed",
            explanation="A build phase failed to complete successfully.",
            docs_url="/docs/build/",
            before_snippet="# Build phase failure",
            after_snippet="bengal build --verbose",
            check_files=["bengal/orchestration/build.py"],
            related_codes=["B001"],
            grep_patterns=["build_phase", "BuildPhase"],
        ),
        "parallel_error": ActionableSuggestion(
            fix="Try running with --jobs 1 to isolate the issue",
            explanation="Parallel processing encountered an error.",
            docs_url="/docs/build/performance/",
            before_snippet="# Parallel build failure",
            after_snippet="bengal build --jobs 1",
            check_files=["bengal/orchestration/render.py"],
            related_codes=["B002"],
            grep_patterns=["parallel", "ProcessPoolExecutor", "ThreadPoolExecutor"],
        ),
        "write_behind_failed": ActionableSuggestion(
            fix="Check disk space and file permissions in output directory",
            explanation="Background file writer thread failed while writing output.",
            docs_url="/docs/build/",
            before_snippet="# Writer thread failure",
            after_snippet="# Check disk space: df -h\n# Check permissions: ls -la public/",
            check_files=["bengal/rendering/pipeline/write_behind.py"],
            related_codes=["R010", "B001"],
            grep_patterns=["write_behind", "WriteBehindWriter"],
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
    if not query or not query.strip():
        return []
    query_lower = query.lower().strip()
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


# =============================================================================
# Template-error suggestion engine (Sprint A1.3)
# =============================================================================
# These functions absorb the dynamic suggestion logic that previously lived in
# ``bengal/rendering/errors/exceptions.py`` (construction-time single
# suggestion) and ``bengal/rendering/errors/display.py`` (display-time
# enhancement list). Both legacy entry points now delegate here.
#
# The dynamic engine inspects the actual exception text + source line to
# synthesize advice, complementing the static :class:`ActionableSuggestion`
# registry above (which keys advice by ``(category, error_key)``).

# Identifiers excluded from "suspect callable" detection — common builtins
# and Jinja control-flow keywords that almost always resolve safely.
_SAFE_CALLABLE_NAMES: frozenset[str] = frozenset(
    {
        "if",
        "for",
        "while",
        "with",
        "set",
        "print",
        "range",
        "len",
        "dict",
        "list",
        "str",
        "int",
        "float",
        "isinstance",
        "getattr",
        "hasattr",
        "type",
        "exec",
    }
)


def suggest_type_comparison(error: BaseException) -> str:
    """Build advice for a ``'<' not supported between …`` TypeError.

    Parses the type names out of the exception message and produces a
    YAML-frontmatter-aware hint — the most common source of mixed-type
    comparisons in Bengal templates.
    """
    error_str = str(error)
    match = re.search(
        r"not supported between instances of '(\w+)' and '(\w+)'",
        error_str,
    )
    if match:
        type_a, type_b = match.group(1), match.group(2)
        return (
            f"A comparison failed because one value is {type_a} and another "
            f"is {type_b}. This usually happens when a metadata field like "
            f"'weight' is numeric in one YAML file (weight: 10) but quoted "
            f"in another (weight: '10'). Check your frontmatter and section "
            f"_index.md files for inconsistent types. Sorting and template "
            f"comparisons require all values to share the same type."
        )
    return (
        "A comparison or sort failed due to mixed types (e.g. int vs str). "
        "Check that metadata fields like 'weight' use consistent types "
        "across all YAML frontmatter and _index.md files."
    )


def identify_none_callable(error: BaseException, template_path: Path | None = None) -> str | None:
    """Identify which template callable was None in a TypeError.

    Walks the traceback for filter/function call sites and (when
    available) scans the template source for likely culprits. Returns
    a humanised "Likely cause: …" string, or ``None`` when no
    suspects can be identified.
    """
    tb = traceback.extract_tb(error.__traceback__)
    suspects: list[str] = []

    for frame in reversed(tb):
        if "filters" in frame.filename.lower():
            suspects.append("a filter function")
            continue

        if not frame.line:
            continue
        line = frame.line

        filter_match = re.search(r"\|\s*(\w+)", line)
        if filter_match:
            suspects.append(f"filter '{filter_match.group(1)}'")

        call_match = re.search(r"(\w+)\s*\(", line)
        if call_match:
            func_name = call_match.group(1)
            if func_name not in _SAFE_CALLABLE_NAMES:
                suspects.append(f"function '{func_name}'")

    if template_path and template_path.exists():
        try:
            from bengal.rendering.errors.context_extractor import (
                scan_template_for_callables,
            )

            suspects.extend(scan_template_for_callables(template_path))
        except Exception:  # noqa: S110
            pass

    unique_suspects = list(dict.fromkeys(suspects))
    if not unique_suspects:
        return None
    if len(unique_suspects) == 1:
        return (
            f"Likely cause: {unique_suspects[0]} is None or not registered. "
            f"Verify it's defined in template globals or context."
        )
    formatted = ", ".join(unique_suspects[:3])
    if len(unique_suspects) > 3:
        formatted += f" (and {len(unique_suspects) - 3} more)"
    return f"Suspected callables: {formatted}. One of these is likely None or not registered."


def find_filter_alternatives(
    error: BaseException, available_filters: list[str], *, max_results: int = 3
) -> list[str]:
    """Levenshtein-near filter names for an "unknown filter" error.

    Decoupled from the template engine: the caller passes the list of
    registered filter names (typically ``sorted(env.filters)``).
    """
    match = re.search(r"No filter named ['\"](\w+)['\"]", str(error))
    if not match:
        return []
    return get_close_matches(match.group(1), available_filters, n=max_results, cutoff=0.6)


def find_variable_alternatives(
    error: BaseException,
    *,
    available_names: Iterable[str] | None = None,
    max_results: int = 3,
) -> list[str]:
    """Levenshtein-near variable names for an "undefined variable" error.

    Prefers the candidate set Kida already collected on the exception
    (``error._available_names``) since that reflects exactly what was in
    scope when the lookup failed. Falls back to a caller-supplied
    ``available_names`` (typically ``env.globals``) when the exception
    didn't carry one.

    Returns the empty list when no candidate set is available or no
    matches clear the cutoff — better silence than a misleading hint.
    """
    name = getattr(error, "name", None)
    if not name:
        return []

    candidates = getattr(error, "_available_names", None)
    if not candidates:
        candidates = available_names
    if not candidates:
        return []

    return get_close_matches(name, list(candidates), n=max_results, cutoff=0.6)


def generate_template_suggestion(
    error: BaseException,
    error_type: str,
    template_path: Path | None = None,
) -> str | None:
    """Construction-time suggestion for a template error.

    Picks one primary hint based on the canonical ``error_type`` string
    (the legacy classifier's vocabulary — ``"callable"``, ``"none_access"``,
    ``"type_comparison"``, ``"filter"``, ``"undefined"``, ``"syntax"``).
    """
    error_str = str(error).lower()

    if error_type == "type_comparison":
        return suggest_type_comparison(error)

    if error_type == "callable":
        callable_info = identify_none_callable(error, template_path)
        if callable_info:
            return callable_info
        return (
            "A function or filter being called is None. Check that all filters and "
            "template functions are properly registered in the template engine."
        )

    if error_type == "none_access":
        return (
            "A variable is None when it should be a list, dict, or string. "
            "Check that all context variables are properly initialized. "
            "Common causes: missing data in page.metadata, section is None, or "
            "element is None. Use {% if var %} guards before accessing."
        )

    if error_type == "filter":
        if "in_section" in error_str:
            return (
                "Bengal doesn't have 'in_section' filter. Check if the page is "
                "in a section using: {% if page.parent %}"
            )
        if "is_ancestor" in error_str:
            return "Use page comparison instead: {% if page._path == other_page._path %}"

    elif error_type == "undefined":
        if "metadata.weight" in error_str:
            return "Use safe access: {{ page.metadata.get('weight', 0) }}"

    elif error_type == "syntax":
        if "with" in error_str:
            return "Jinja2 doesn't support 'with' in include. Use {% set %} before {% include %}"
        if "default=" in error_str:
            return (
                "The 'default' parameter in sort() is not supported. "
                "Remove it or use a custom filter."
            )

    return None


# --- Display-time enhancement (formerly display._generate_enhanced_suggestions)


def _extract_variable_name(error_message: str) -> str | None:
    """Pull the bound variable name out of an "undefined" message."""
    patterns = (
        r"'([^']+)' is undefined",
        r"undefined variable: ([^\s]+)",
        r"no such element: ([^\s]+)",
    )
    for pattern in patterns:
        match = re.search(pattern, error_message)
        if match:
            return match.group(1)
    return None


def _extract_filter_name(error_message: str) -> str | None:
    match = re.search(r"no filter named ['\"]([^'\"]+)['\"]", error_message, re.IGNORECASE)
    return match.group(1) if match else None


def _extract_dict_attribute(error_message: str) -> str | None:
    match = re.search(r"'dict object' has no attribute '([^']+)'", error_message)
    return match.group(1) if match else None


# Common typo → correct spelling for frontmatter fields. Surfaced in the
# "did you mean?" line of the undefined-variable suggestion.
_FRONTMATTER_TYPOS: dict[str, str] = {
    "titel": "title",
    "dat": "date",
    "autor": "author",
    "sumary": "summary",
    "desciption": "description",
    "metdata": "metadata",
    "conent": "content",
}


def _enhance_callable_suggestions(base: list[str], source_line: str | None) -> list[str]:
    base.append(
        "A filter or function is None! This means something "
        "expected to be callable wasn't registered properly."
    )
    if source_line:
        filter_matches = re.findall(r"\|\s*(\w+)", source_line)
        if filter_matches:
            base.append(
                f"Suspected filters: {', '.join(filter_matches)} - "
                f"verify these are registered in the template engine."
            )
        func_matches = [
            f for f in re.findall(r"(\w+)\s*\(", source_line) if f not in _SAFE_CALLABLE_NAMES
        ]
        if func_matches:
            base.append(
                f"Suspected functions: {', '.join(func_matches)} - "
                f"verify these are defined in template globals or context."
            )
    base.append(
        "Common causes: missing filter registration, context variable is None when "
        "a method is called on it, or a global function wasn't added to the engine."
    )
    base.append(
        "Debug tip: Add {% if debug %}{{ element | pprint }}{% endif %} "
        "to inspect what's being passed to the template."
    )
    return base


def _enhance_none_access_suggestions(base: list[str], source_line: str | None) -> list[str]:
    base.append(
        "A variable is None! This happens when using 'in' operator "
        "or iterating over a variable that doesn't exist or is None."
    )
    if source_line:
        in_match = re.search(r"in\s+(\w+(?:\.\w+)*)", source_line)
        if in_match:
            var_name = in_match.group(1)
            base.append(
                f"Variable {var_name} is likely None. "
                f"Add a guard: {{% if {var_name} and x in {var_name} %}}"
            )
        for_match = re.search(r"for\s+\w+\s+in\s+(\w+(?:\.\w+)*)", source_line)
        if for_match:
            var_name = for_match.group(1)
            base.append(
                f"Variable {var_name} is likely None. "
                f"Add a guard: {{% if {var_name} %}}{{% for x in {var_name} %}}...{{% endif %}}"
            )
    base.append(
        "Common causes: missing context variable, accessing .children or .pages on None, "
        "or optional metadata that wasn't provided."
    )
    base.append("Debug tip: Add {{ var | pprint }} before the error line to see what's None.")
    return base


def _enhance_undefined_suggestions(base: list[str], message: str) -> list[str]:
    if "'dict object' has no attribute" in message:
        attr = _extract_dict_attribute(message)
        base.append("Unsafe dict access detected! Dict keys should use .get() method")
        if attr:
            base.append(
                f"Replace dict.{attr} with dict.get('{attr}') or dict.get('{attr}', 'default')"
            )
        base.append("Common locations: page.metadata, site.config, section.metadata")
        base.append(
            "Note: This error only appears in strict mode (serve). "
            "Use bengal build --strict to catch in builds."
        )
        return base

    var_name = _extract_variable_name(message)
    if not var_name:
        return base

    if var_name.lower() in _FRONTMATTER_TYPOS:
        base.append(f"Common typo: try '{_FRONTMATTER_TYPOS[var_name.lower()]}' instead")
    base.append(f"Use safe access: {{{{ {var_name} | default('fallback') }}}}")
    if "." in var_name:
        base_path, attr = var_name.rsplit(".", 1)
        base.append(f"Or use dict access: {{{{ {base_path}.get('{attr}', 'default') }}}}")
    else:
        base.append(f"Add '{var_name}' to page frontmatter")
    return base


def enhance_template_suggestions(
    error_type: str,
    message: str,
    *,
    primary_suggestion: str | None = None,
    source_line: str | None = None,
) -> list[str]:
    """Display-time enrichment list for a template error.

    Mirrors the legacy ``display._generate_enhanced_suggestions``: starts
    with the construction-time ``primary_suggestion`` (when present) and
    appends context-aware advice based on ``error_type`` and any visible
    ``source_line`` from the rendered code frame.
    """
    suggestions: list[str] = []
    if primary_suggestion:
        suggestions.append(primary_suggestion)

    error_str = message.lower()

    if error_type == "callable":
        return _enhance_callable_suggestions(suggestions, source_line)

    if error_type == "none_access":
        return _enhance_none_access_suggestions(suggestions, source_line)

    if error_type == "undefined":
        return _enhance_undefined_suggestions(suggestions, message)

    if error_type == "filter":
        filter_name = _extract_filter_name(message)
        if filter_name:
            suggestions.append("Check available filters in bengal --help or documentation")
            if "date" in filter_name.lower():
                suggestions.append("For dates, use {{ date | date('%Y-%m-%d') }}")
        return suggestions

    if error_type == "syntax":
        if "unexpected" in error_str:
            suggestions.append("Check for missing %} or }} tags")
        if "expected token" in error_str:
            suggestions.append("Verify Jinja2 syntax - might be using unsupported features")
        if "endfor" in error_str or "endif" in error_str:
            suggestions.append(
                "Every {% for %} needs {% endfor %}, every {% if %} needs {% endif %}"
            )

    return suggestions
