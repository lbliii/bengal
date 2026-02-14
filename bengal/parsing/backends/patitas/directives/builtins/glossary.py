"""Glossary directive for Bengal SSG (Patitas-native).

Renders key terms from a centralized glossary data file as definition lists.
Supports filtering by tags to show relevant terms for each page.

Syntax:
    :::{glossary}
    :tags: directives, navigation
    :::

    :::{glossary}
    :tags: admonitions
    :sorted: true
    :collapsed: true
    :limit: 3
    :::

Options:
    - tags: Comma-separated list of tags to filter terms (required)
    - sorted: Sort terms alphabetically (default: false)
    - show-tags: Display tag badges under each term (default: false)
    - collapsed: Wrap glossary in collapsible <details> element (default: false)
    - limit: Show only first N terms, with "Show all" to expand (default: 0 = all)
    - source: Custom glossary file path (default: data/glossary.yaml)

Architecture:
    Data loading is deferred to the render phase where site context provides
    access to site.data (pre-loaded by Site.__post_init__) and site.root_path
    for fallback file loading.

Context Requirements:
    Requires site context (injected via ``site`` keyword argument by
    DirectiveRendererMixin when ``"site" in sig.parameters``).

Thread Safety:
    Stateless handler. Safe for concurrent use across threads.

HTML Output:
    Matches Bengal's glossary directive exactly for parity with the
    Mistune-based implementation.

"""

from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any, ClassVar

from patitas.directives.options import DirectiveOptions
from patitas.nodes import Directive

from bengal.parsing.backends.patitas.directives.contracts import DirectiveContract
from bengal.utils.primitives.text import escape_html

if TYPE_CHECKING:
    from patitas.location import SourceLocation
    from patitas.nodes import Block
    from patitas.stringbuilder import StringBuilder

__all__ = ["GlossaryDirective"]

# Default glossary file path (relative to site root)
DEFAULT_GLOSSARY_PATH = "data/glossary.yaml"

# Simple inline markdown patterns for definition rendering fallback
_BOLD_RE = re.compile(r"\*\*(.+?)\*\*")
_ITALIC_RE = re.compile(r"\*(.+?)\*")
_CODE_RE = re.compile(r"`([^`]+)`")
_LINK_RE = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")


# =============================================================================
# Options
# =============================================================================


@dataclass(frozen=True, slots=True)
class GlossaryOptions(DirectiveOptions):
    """Options for glossary directive."""

    tags: str = ""
    """Comma-separated list of tags to filter terms (required)."""

    sorted: bool = False
    """Sort terms alphabetically (default: false, preserves file order)."""

    show_tags: bool = False
    """Display tag badges under each term (default: false)."""

    collapsed: bool = False
    """Wrap glossary in collapsible <details> element (default: false)."""

    limit: int = 0
    """Show only first N terms with expansion (default: 0 = show all)."""

    source: str = DEFAULT_GLOSSARY_PATH
    """Custom glossary file path (default: data/glossary.yaml)."""


# =============================================================================
# Directive
# =============================================================================


class GlossaryDirective:
    """
    Glossary directive rendering terms from a centralized data file.

    Syntax:
        :::{glossary}
        :tags: tag1, tag2
        :sorted: true
        :show-tags: true
        :collapsed: true
        :limit: 3
        :::

    Options:
        :tags: Comma-separated list of tags to filter terms (required)
        :sorted: Sort terms alphabetically (default: false)
        :show-tags: Display tag badges under each term (default: false)
        :collapsed: Wrap in collapsible <details> element (default: false)
        :limit: Show only first N terms with "Show all" expansion (default: all)
        :source: Custom glossary file path (default: data/glossary.yaml)

    Requires:
        Site context for loading glossary data (injected by renderer).

    Thread Safety:
        Stateless handler. Safe for concurrent use.

    """

    names: ClassVar[tuple[str, ...]] = ("glossary",)
    token_type: ClassVar[str] = "glossary"
    contract: ClassVar[DirectiveContract | None] = None
    options_class: ClassVar[type[GlossaryOptions]] = GlossaryOptions

    def parse(
        self,
        name: str,
        title: str | None,
        options: GlossaryOptions,
        content: str,
        children: Sequence[Block],
        location: SourceLocation,
    ) -> Directive:
        """Build glossary AST node.

        Captures all options for deferred data loading at render time.
        No I/O happens here - data loading is deferred to render phase
        where site context is available.
        """
        return Directive(
            location=location,
            name=name,
            title=title,
            options=options,
            children=(),
        )

    def render(
        self,
        node: Directive[GlossaryOptions],
        rendered_children: str,
        sb: StringBuilder,
        *,
        site: Any = None,
    ) -> None:
        """Render glossary as HTML definition list.

        Data loading happens here (deferred from parse phase) using:
        1. site.data.glossary (pre-loaded by Site from data/ directory)
        2. Fallback: file loading via load_data_file using site.root_path

        Args:
            node: Glossary directive AST node with typed options
            rendered_children: Rendered child content (unused for glossary)
            sb: StringBuilder for HTML output
            site: Site context injected by DirectiveRendererMixin

        """
        opts = node.options

        # Parse tags from comma-separated string
        tags = [t.strip().lower() for t in opts.tags.split(",") if t.strip()] if opts.tags else []

        if not tags:
            sb.append('<div class="bengal-glossary-error" role="alert">\n')
            sb.append(
                "  <strong>Glossary Error:</strong>"
                " No tags specified. Use :tags: to filter terms.\n"
            )
            sb.append("</div>\n")
            return

        # Load glossary data from site context
        glossary_result = _load_glossary_data(site, opts.source)

        if "error" in glossary_result:
            error_msg = glossary_result["error"]
            sb.append('<div class="bengal-glossary-error" role="alert">\n')
            sb.append(f"  <strong>Glossary Error:</strong> {escape_html(error_msg)}\n")
            sb.append(f"  <br><small>Source: {escape_html(opts.source)}</small>\n")
            sb.append("</div>\n")
            return

        # Filter terms by tags
        all_terms: list[dict[str, Any]] = glossary_result.get("terms", [])
        terms = _filter_terms(all_terms, tags)

        if not terms:
            sb.append('<div class="bengal-glossary-error" role="alert">\n')
            sb.append(
                "  <strong>Glossary Error:</strong>"
                f" No terms found matching tags: {', '.join(tags)}\n"
            )
            sb.append(f"  <br><small>Source: {escape_html(opts.source)}</small>\n")
            sb.append("</div>\n")
            return

        # Sort if requested
        if opts.sorted:
            terms = sorted(terms, key=lambda t: t.get("term", "").lower())

        total_terms = len(terms)
        has_limit = opts.limit > 0 and opts.limit < total_terms
        visible_terms = terms[: opts.limit] if has_limit else terms
        hidden_terms = terms[opts.limit :] if has_limit else []

        # Wrap in collapsible <details> if requested
        if opts.collapsed:
            summary_text = f"Key Terms ({total_terms})"
            sb.append('<details class="bengal-glossary-collapsed">\n')
            sb.append(f"<summary>{escape_html(summary_text)}</summary>\n")

        # Build definition list for visible terms
        sb.append('<dl class="bengal-glossary">\n')
        for term_data in visible_terms:
            _render_term(term_data, opts.show_tags, sb)
        sb.append("</dl>\n")

        # Add hidden terms in expandable section if limit was applied
        if hidden_terms:
            count = len(hidden_terms)
            plural = "s" if count > 1 else ""
            sb.append('<details class="bengal-glossary-more">\n')
            sb.append(f"<summary>Show {count} more term{plural}</summary>\n")
            sb.append('<dl class="bengal-glossary bengal-glossary-expanded">\n')
            for term_data in hidden_terms:
                _render_term(term_data, opts.show_tags, sb)
            sb.append("</dl>\n")
            sb.append("</details>\n")

        # Close collapsible wrapper
        if opts.collapsed:
            sb.append("</details>\n")


# =============================================================================
# Data Loading
# =============================================================================


def _load_glossary_data(site: Any, source_path: str) -> dict[str, Any]:
    """Load glossary data from site.data or file.

    Tries these sources in order:
    1. site.data.glossary (if source is default data/glossary.yaml)
    2. File loading using site.root_path and load_data_file

    Args:
        site: Site object with data and root_path attributes
        source_path: Path to glossary file (default: data/glossary.yaml)

    Returns:
        Dict with 'terms' key on success, or 'error' key on failure

    """
    # Try site.data first (data files pre-loaded from data/ directory)
    if site and hasattr(site, "data") and site.data:
        if source_path == DEFAULT_GLOSSARY_PATH:
            # Default path: look for site.data.glossary
            glossary_data = getattr(site.data, "glossary", None)
            if glossary_data and isinstance(glossary_data, dict):
                terms = glossary_data.get("terms", [])
                if isinstance(terms, list):
                    return {"terms": terms}
        else:
            # Custom path: resolve from site.data hierarchy
            # e.g., "data/team/glossary.yaml" -> site.data.team.glossary
            result = _resolve_from_site_data(site.data, source_path)
            if result is not None:
                return result

    # Fallback: Load from file using site.root_path
    if not site or not hasattr(site, "root_path"):
        return {"error": "Site context not available for glossary data loading"}

    root_path = site.root_path
    file_path = Path(root_path) / source_path

    if not file_path.exists():
        return {"error": f"Glossary file not found: {source_path}"}

    try:
        from bengal.utils.io.file_io import load_data_file

        data = load_data_file(file_path, on_error="raise", caller="glossary")

        if not isinstance(data, dict):
            return {"error": "Glossary file must contain a dictionary"}

        if "terms" not in data:
            return {"error": "Glossary file must contain 'terms' list"}

        terms = data["terms"]
        if not isinstance(terms, list):
            return {"error": "'terms' must be a list"}

        return {"terms": terms}

    except Exception as exc:
        return {"error": f"Failed to parse glossary: {exc}"}


def _resolve_from_site_data(data: Any, source_path: str) -> dict[str, Any] | None:
    """Resolve glossary data from site.data hierarchy.

    Navigates the site.data object using the source path.
    e.g., "data/team/glossary.yaml" -> site.data.team.glossary

    Args:
        data: Site data object (attribute-based or dict-based)
        source_path: Relative path to glossary file

    Returns:
        Dict with 'terms' key if found, None otherwise

    """
    from bengal.utils.paths.normalize import to_posix

    parts = to_posix(source_path).split("/")
    # Remove "data" prefix if present
    if parts and parts[0] == "data":
        parts = parts[1:]
    if not parts:
        return None

    # Remove .yaml/.yml extension from last part
    last = parts[-1]
    for ext in (".yaml", ".yml", ".json", ".toml"):
        if last.endswith(ext):
            parts[-1] = last[: -len(ext)]
            break

    # Navigate hierarchy
    current: Any = data
    for part in parts:
        if hasattr(current, part):
            current = getattr(current, part)
        elif isinstance(current, dict) and part in current:
            current = current[part]
        else:
            return None

    if current and isinstance(current, dict):
        terms = current.get("terms", [])
        if isinstance(terms, list):
            return {"terms": terms}

    return None


# =============================================================================
# Filtering
# =============================================================================


def _filter_terms(terms: list[dict[str, Any]], tags: list[str]) -> list[dict[str, Any]]:
    """Filter terms by tags (OR logic).

    A term matches if it has ANY of the requested tags.

    Args:
        terms: List of term dicts from glossary data
        tags: List of lowercase tags to match

    Returns:
        List of matching terms

    """
    tags_set = frozenset(tags)
    filtered: list[dict[str, Any]] = []

    for term in terms:
        term_tags = term.get("tags", [])
        if not isinstance(term_tags, list):
            term_tags = [term_tags]

        # Convert to lowercase for comparison
        term_tags_lower = {t.lower() for t in term_tags if isinstance(t, str)}

        # Match if any tag overlaps
        if term_tags_lower & tags_set:
            filtered.append(term)

    return filtered


# =============================================================================
# Rendering
# =============================================================================


def _render_term(term_data: dict[str, Any], show_tags: bool, sb: StringBuilder) -> None:
    """Render a single glossary term as dt/dd pair.

    Args:
        term_data: Dict with 'term', 'definition', and optional 'tags'
        show_tags: Whether to display tag badges
        sb: StringBuilder for HTML output

    """
    term = term_data.get("term", "Unknown Term")
    definition = term_data.get("definition", "No definition provided.")
    term_tags: list[str] = term_data.get("tags", [])

    # Term (dt) - escape HTML, no markdown parsing
    sb.append(f"  <dt>{escape_html(term)}</dt>\n")

    # Definition (dd) - render inline markdown
    dd_content = _render_inline_markdown(definition)

    # Optionally show tags as badges
    if show_tags and term_tags:
        tag_badges = " ".join(
            f'<span class="bengal-glossary-tag">{escape_html(t)}</span>' for t in term_tags
        )
        dd_content += f'\n<div class="bengal-glossary-tags">{tag_badges}</div>'

    sb.append(f"  <dd>{dd_content}</dd>\n")


def _render_inline_markdown(text: str) -> str:
    """Render inline markdown in glossary definitions.

    Attempts to use the thread-local Patitas parser for full markdown
    support. Falls back to simple regex-based inline rendering.

    Args:
        text: Raw definition text (may contain inline markdown)

    Returns:
        HTML string with inline markdown converted

    """
    try:
        from bengal.rendering.pipeline.thread_local import get_thread_parser

        parser = get_thread_parser()
        html = parser.parse(text, metadata={}).strip()

        # Strip outer <p> wrapper if the result is a single paragraph
        if html.startswith("<p>") and html.endswith("</p>"):
            inner = html[3:-4].strip()
            if "<p" not in inner and "</p>" not in inner:
                return inner
        return html
    except Exception:
        # Fallback: simple regex-based inline markdown
        return _regex_inline_markdown(text)


def _regex_inline_markdown(text: str) -> str:
    """Simple regex-based inline markdown rendering (fallback).

    Handles bold, italic, code, and links. Escapes HTML first
    to prevent injection from untrusted glossary content.

    Args:
        text: Raw text to convert

    Returns:
        HTML string with basic inline formatting

    """
    result = escape_html(text)
    result = _BOLD_RE.sub(r"<strong>\1</strong>", result)
    result = _ITALIC_RE.sub(r"<em>\1</em>", result)
    result = _CODE_RE.sub(r"<code>\1</code>", result)
    result = _LINK_RE.sub(r'<a href="\2">\1</a>', result)
    return result
