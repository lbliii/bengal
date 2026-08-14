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

- ``bengal/errors/suggestion_catalog.py`` - Static ``ActionableSuggestion`` catalog
- ``bengal/errors/exceptions.py`` - Exception classes using suggestions
- ``bengal/errors/handlers.py`` - Runtime error handlers

"""

from __future__ import annotations

import re
import traceback
from difflib import get_close_matches
from typing import TYPE_CHECKING, Any

from bengal.errors.suggestion_catalog import SUGGESTIONS as _SUGGESTIONS
from bengal.errors.suggestion_catalog import ActionableSuggestion

if TYPE_CHECKING:
    from collections.abc import Iterable
    from pathlib import Path


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
            from bengal.errors.template_callables import (
                scan_template_for_callables,
            )

            suspects.extend(scan_template_for_callables(template_path))
        except Exception:  # noqa: S110 -- suggestion scanning is advisory; never break error reporting
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
