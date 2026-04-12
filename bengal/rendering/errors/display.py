"""
Display functions for template errors.

Functions:
    display_template_error: Main entry point for displaying errors

Helper Functions:
    _generate_enhanced_suggestions: Context-aware suggestion generation
    _extract_variable_name: Extract variable name from undefined error
    _extract_filter_name: Extract filter name from filter error
    _extract_dict_attribute: Extract attribute from dict access error
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .exceptions import TemplateRenderError


def display_template_error(error: TemplateRenderError, use_color: bool = True) -> None:
    """Display a template error in the terminal."""
    _display_template_error_plain(error)


def _generate_enhanced_suggestions(error: TemplateRenderError) -> list[str]:
    """Generate context-aware suggestions for template errors."""
    suggestions = []

    # Start with existing suggestion (TemplateRenderError has it; engine TemplateError does not)
    suggestion = getattr(error, "suggestion", None)
    if suggestion:
        suggestions.append(suggestion)

    error_str = str(error.message).lower()

    # Enhanced suggestions based on error type
    if error.error_type == "callable":
        # This is a "NoneType is not callable" error
        suggestions.append(
            "A filter or function is None! This means something "
            "expected to be callable wasn't registered properly."
        )

        # Try to find clues from the source line
        if error.template_context.source_line:
            line = error.template_context.source_line

            # Look for filter patterns: | filter_name
            filter_matches = re.findall(r"\|\s*(\w+)", line)
            if filter_matches:
                suggestions.append(
                    f"Suspected filters: {', '.join(filter_matches)} - "
                    f"verify these are registered in the template engine."
                )

            # Look for function calls: func_name(
            func_matches = re.findall(r"(\w+)\s*\(", line)
            func_matches = [
                f
                for f in func_matches
                if f not in ("if", "for", "while", "with", "set", "range", "len", "dict", "list")
            ]
            if func_matches:
                suggestions.append(
                    f"Suspected functions: {', '.join(func_matches)} - "
                    f"verify these are defined in template globals or context."
                )

        suggestions.append(
            "Common causes: missing filter registration, context variable is None when "
            "a method is called on it, or a global function wasn't added to the engine."
        )
        suggestions.append(
            "Debug tip: Add {% if debug %}{{ element | pprint }}{% endif %} "
            "to inspect what's being passed to the template."
        )
        return suggestions

    if error.error_type == "none_access":
        # This is "argument of type 'NoneType' is not a container or iterable"
        suggestions.append(
            "A variable is None! This happens when using 'in' operator "
            "or iterating over a variable that doesn't exist or is None."
        )

        # Try to find clues from the source line
        if error.template_context.source_line:
            line = error.template_context.source_line

            # Look for 'in' patterns: if x in y
            in_match = re.search(r"in\s+(\w+(?:\.\w+)*)", line)
            if in_match:
                var_name = in_match.group(1)
                suggestions.append(
                    f"Variable {var_name} is likely None. "
                    f"Add a guard: {{% if {var_name} and x in {var_name} %}}"
                )

            # Look for for loops: for x in y
            for_match = re.search(r"for\s+\w+\s+in\s+(\w+(?:\.\w+)*)", line)
            if for_match:
                var_name = for_match.group(1)
                suggestions.append(
                    f"Variable {var_name} is likely None. "
                    f"Add a guard: {{% if {var_name} %}}{{% for x in {var_name} %}}...{{% endif %}}"
                )

        suggestions.append(
            "Common causes: missing context variable, accessing .children or .pages on None, "
            "or optional metadata that wasn't provided."
        )
        suggestions.append(
            "Debug tip: Add {{ var | pprint }} before the error line to see what's None."
        )
        return suggestions

    if error.error_type == "undefined":
        var_name = _extract_variable_name(error.message)

        # ENHANCED: Detect unsafe dict access patterns
        if "'dict object' has no attribute" in error.message:
            # This is THE key pattern we just fixed!
            attr = _extract_dict_attribute(error.message)
            suggestions.append("Unsafe dict access detected! Dict keys should use .get() method")
            if attr:
                suggestions.append(
                    f"Replace dict.{attr} with dict.get('{attr}') or dict.get('{attr}', 'default')"
                )
            suggestions.append("Common locations: page.metadata, site.config, section.metadata")
            suggestions.append(
                "Note: This error only appears in strict mode (serve). Use bengal build --strict to catch in builds."
            )
            return suggestions  # Return early with specific guidance

        if var_name:
            # Common typos
            typo_map = {
                "titel": "title",
                "dat": "date",
                "autor": "author",
                "sumary": "summary",
                "desciption": "description",
                "metdata": "metadata",
                "conent": "content",
            }

            if var_name.lower() in typo_map:
                suggestions.append(f"Common typo: try '{typo_map[var_name.lower()]}' instead")

            # Suggest safe access
            suggestions.append(f"Use safe access: {{{{ {var_name} | default('fallback') }}}}")

            # Check if it looks like metadata access
            if "." in var_name:
                base, attr = var_name.rsplit(".", 1)
                suggestions.append(f"Or use dict access: {{{{ {base}.get('{attr}', 'default') }}}}")
            else:
                # Suggest adding to frontmatter
                suggestions.append(f"Add '{var_name}' to page frontmatter")

    elif error.error_type == "filter":
        filter_name = _extract_filter_name(error.message)

        if filter_name:
            # Suggest checking documentation
            suggestions.append("Check available filters in bengal --help or documentation")

            # Common filter mistakes
            if "date" in filter_name.lower():
                suggestions.append("For dates, use {{ date | date('%Y-%m-%d') }}")

    elif error.error_type == "syntax":
        if "unexpected" in error_str:
            suggestions.append("Check for missing %} or }} tags")

        if "expected token" in error_str:
            suggestions.append("Verify Jinja2 syntax - might be using unsupported features")

        if "endfor" in error_str or "endif" in error_str:
            suggestions.append(
                "Every {% for %} needs {% endfor %}, every {% if %} needs {% endif %}"
            )

    return suggestions


def _extract_variable_name(error_message: str) -> str | None:
    """Extract variable name from undefined variable error."""
    # Try different patterns
    patterns = [
        r"'([^']+)' is undefined",
        r"undefined variable: ([^\s]+)",
        r"no such element: ([^\s]+)",
    ]

    for pattern in patterns:
        match = re.search(pattern, error_message)
        if match:
            return match.group(1)

    return None


def _extract_filter_name(error_message: str) -> str | None:
    """Extract filter name from filter error."""
    match = re.search(r"no filter named ['\"]([^'\"]+)['\"]", error_message, re.IGNORECASE)
    if match:
        return match.group(1)

    return None


def _extract_dict_attribute(error_message: str) -> str | None:
    """Extract attribute name from dict access error."""
    # Pattern: 'dict object' has no attribute 'attr_name'
    match = re.search(r"'dict object' has no attribute '([^']+)'", error_message)
    if match:
        return match.group(1)

    return None


def _display_template_error_plain(error: TemplateRenderError) -> None:
    """Plain-text fallback display (no Rich)."""
    import sys

    out = sys.stdout

    error_type_names = {
        "syntax": "Template Syntax Error",
        "filter": "Unknown Filter",
        "undefined": "Undefined Variable",
        "runtime": "Template Runtime Error",
        "callable": "None Is Not Callable",
        "none_access": "None Is Not Iterable",
        "other": "Template Error",
    }

    header = error_type_names.get(error.error_type, "Template Error")
    print(f"\n  {header}", file=out)

    ctx = error.template_context
    if ctx.template_path:
        print(f"\n  File: {ctx.template_path}", file=out)
    else:
        print(f"\n  Template: {ctx.template_name}", file=out)

    if ctx.line_number:
        print(f"  Line: {ctx.line_number}", file=out)

    if ctx.surrounding_lines:
        print("\n  Code:", file=out)
        for line_num, line_content in ctx.surrounding_lines:
            is_error_line = line_num == ctx.line_number
            prefix = ">" if is_error_line else " "
            print(f"  {prefix} {line_num:4d} | {line_content}", file=out)

            if is_error_line and ctx.source_line:
                pointer = " " * (len(f"  {prefix} {line_num:4d} | ")) + "^" * min(
                    len(ctx.source_line.strip()), 40
                )
                print(pointer, file=out)

    print(f"\n  Error: {error.message}", file=out)

    suggestion = getattr(error, "suggestion", None)
    if suggestion:
        print(f"\n  Suggestion: {suggestion}", file=out)

    available_alternatives = getattr(error, "available_alternatives", None) or []
    if available_alternatives:
        print(
            f"\n  Did you mean: {', '.join(f'{alt!r}' for alt in available_alternatives)}", file=out
        )

    inclusion_chain = getattr(error, "inclusion_chain", None)
    if inclusion_chain:
        print("\n  Template Chain:", file=out)
        for line in str(inclusion_chain).split("\n"):
            print(f"  {line}", file=out)

    page_source = getattr(error, "page_source", None)
    if page_source:
        print(f"\n  Used by page: {page_source}", file=out)

    search_paths = getattr(error, "search_paths", None) or []
    if search_paths:
        print("\n  Template Search Paths:", file=out)
        for i, search_path in enumerate(search_paths, 1):
            found_marker = ""
            if ctx.template_path and ctx.template_path.is_relative_to(search_path):
                found_marker = " <-- found here"
            print(f"     {i}. {search_path}{found_marker}", file=out)

    print(file=out)
