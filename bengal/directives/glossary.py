"""
Glossary directive for Bengal SSG.

Renders key terms from a centralized glossary data file as definition lists.
Supports filtering by tags to show relevant terms for each page.

Syntax:

```markdown
:::{glossary}
:tags: directives, navigation
:::

:::{glossary}
:tags: admonitions
:sorted: true
:collapsed: true
:limit: 3
:::
```

The directive loads terms from data/glossary.yaml (via site.data.glossary) and
renders matching terms as a styled definition list.

Options:
    - tags: Comma-separated list of tags to filter terms (required)
    - sorted: Sort terms alphabetically (default: false)
    - show-tags: Display tag badges under each term (default: false)
    - collapsed: Wrap glossary in collapsible <details> element (default: false)
    - limit: Show only first N terms, with "Show all" to expand (default: all)
    - source: Custom glossary file path (default: data/glossary.yaml)

Architecture:
    Data loading is deferred to the render phase where we have access to
    renderer._site.data (pre-loaded by Site.__post_init__). This follows
    where data files are accessible via site.data.*.
"""

from __future__ import annotations

import re
from pathlib import Path
from re import Match
from typing import Any

from mistune.directives import DirectivePlugin

from bengal.utils.file_io import load_data_file
from bengal.utils.logger import get_logger

__all__ = ["GlossaryDirective", "render_glossary"]

logger = get_logger(__name__)

# Default glossary file path (relative to site root)
DEFAULT_GLOSSARY_PATH = "data/glossary.yaml"


class GlossaryDirective(DirectivePlugin):
    """
    Glossary directive using Mistune's fenced syntax.

    Syntax:
        :::{glossary}
        :tags: tag1, tag2
        :sorted: true
        :show-tags: true
        :collapsed: true
        :limit: 3
        :::

    Options:
        - tags: Comma-separated list of tags to filter terms (required)
        - sorted: Sort terms alphabetically (default: false, preserves file order)
        - show-tags: Display tag badges under each term (default: false)
        - collapsed: Wrap in collapsible <details> element (default: false)
        - limit: Show only first N terms with "Show all" expansion (default: all)
        - source: Custom glossary file path (default: data/glossary.yaml)

    Architecture:
        Parse phase records options only. Data loading is deferred to render
        phase where renderer._site provides access to site.data and site.root_path.
    """

    # Directive names this class registers (for health check introspection)
    DIRECTIVE_NAMES = ["glossary"]

    def parse(self, block: Any, m: Match[str], state: Any) -> dict[str, Any]:
        """
        Parse glossary directive options.

        Note: Data loading is deferred to render phase where we have access
        to site.data via renderer._site.

        Args:
            block: Block parser
            m: Regex match object
            state: Parser state

        Returns:
            Token dict with type 'glossary' containing options for render phase
        """
        # Parse options
        try:
            if (hasattr(self, "parser") and self.parser) or (
                hasattr(self, "parse_options")
                and self.parse_options != DirectivePlugin.parse_options
            ):
                options = dict(self.parse_options(m))
            else:
                options = {}
        except (AttributeError, TypeError):
            options = {}

        # Get tags filter (required)
        tags_str = options.get("tags", "")
        if not tags_str:
            return {
                "type": "glossary",
                "attrs": {"error": "No tags specified. Use :tags: to filter terms."},
                "children": [],
            }

        # Parse tags into list
        tags = [tag.strip().lower() for tag in tags_str.split(",") if tag.strip()]

        # Parse other options
        sorted_terms = self._parse_bool(options.get("sorted", "false"))
        show_tags = self._parse_bool(options.get("show-tags", "false"))
        collapsed = self._parse_bool(options.get("collapsed", "false"))
        limit = self._parse_int(options.get("limit", "0"))  # 0 = show all
        source_path = options.get("source", DEFAULT_GLOSSARY_PATH)

        # Build attributes for renderer - data loading deferred to render phase
        attrs = {
            "tags": tags,
            "sorted": sorted_terms,
            "show_tags": show_tags,
            "collapsed": collapsed,
            "limit": limit,
            "source": source_path,
            "_deferred": True,  # Signal that data loading is deferred
        }

        return {"type": "glossary", "attrs": attrs, "children": []}

    def _parse_bool(self, value: str | bool) -> bool:
        """Parse boolean option value."""
        if isinstance(value, bool):
            return value
        return str(value).lower() in ("true", "1", "yes", "on")

    def _parse_int(self, value: str | int) -> int:
        """Parse integer option value, returns 0 on invalid input."""
        if isinstance(value, int):
            return value
        try:
            return int(str(value).strip())
        except (ValueError, TypeError):
            return 0

    def __call__(self, directive: Any, md: Any) -> Any:
        """Register the directive and renderer."""
        directive.register("glossary", self.parse)

        if md.renderer and md.renderer.NAME == "html":
            md.renderer.register("glossary", render_glossary)


def render_glossary(renderer: Any, text: str, **attrs: Any) -> str:
    """
    Render glossary to HTML as a definition list.

    Data loading happens here (deferred from parse phase) using:
    1. renderer._site.data.glossary (pre-loaded by Site from data/ directory)
    2. Fallback: file loading using renderer._site.root_path

    Args:
        renderer: Mistune renderer (has _site attribute with site.data and root_path)
        text: Rendered children content (unused for glossary)
        **attrs: Glossary attributes from directive (tags, sorted, etc.)

    Returns:
        HTML string for glossary definition list
    """
    # Check for error from parse phase
    if "error" in attrs and not attrs.get("_deferred"):
        error_msg = attrs["error"]
        path = attrs.get("path", "unknown")
        return f"""<div class="bengal-glossary-error" role="alert">
    <strong>Glossary Error:</strong> {error_msg}
    <br><small>Source: {path}</small>
</div>"""

    # Load data if deferred (normal case now)
    if attrs.get("_deferred"):
        source_path = attrs.get("source", DEFAULT_GLOSSARY_PATH)
        tags = attrs.get("tags", [])
        sorted_terms = attrs.get("sorted", False)

        # Load glossary data
        glossary_result = _load_glossary_data(renderer, source_path)

        if "error" in glossary_result:
            logger.warning(
                "glossary_load_error",
                path=source_path,
                error=glossary_result["error"],
            )
            return f"""<div class="bengal-glossary-error" role="alert">
    <strong>Glossary Error:</strong> {glossary_result["error"]}
    <br><small>Source: {source_path}</small>
</div>"""

        # Filter terms by tags
        all_terms = glossary_result.get("terms", [])
        terms = _filter_terms(all_terms, tags)

        if not terms:
            return f"""<div class="bengal-glossary-error" role="alert">
    <strong>Glossary Error:</strong> No terms found matching tags: {", ".join(tags)}
    <br><small>Source: {source_path}</small>
</div>"""

        # Sort if requested
        if sorted_terms:
            terms = sorted(terms, key=lambda t: t.get("term", "").lower())
    else:
        # Terms already loaded in parse phase
        terms = attrs.get("terms", [])

    show_tags = attrs.get("show_tags", False)
    collapsed = attrs.get("collapsed", False)
    limit = attrs.get("limit", 0)

    total_terms = len(terms)
    has_limit = limit > 0 and limit < total_terms
    visible_terms = terms[:limit] if has_limit else terms
    hidden_terms = terms[limit:] if has_limit else []

    # Build definition list for visible terms
    html_parts = ['<dl class="bengal-glossary">']

    for term_data in visible_terms:
        html_parts.append(_render_term(renderer, term_data, show_tags))

    html_parts.append("</dl>")

    # Add hidden terms in expandable section if limit was applied
    if hidden_terms:
        html_parts.append(
            f'<details class="bengal-glossary-more">'
            f"<summary>Show {len(hidden_terms)} more term{'s' if len(hidden_terms) > 1 else ''}</summary>"
        )
        html_parts.append('<dl class="bengal-glossary bengal-glossary-expanded">')
        for term_data in hidden_terms:
            html_parts.append(_render_term(renderer, term_data, show_tags))
        html_parts.append("</dl>")
        html_parts.append("</details>")

    content = "\n".join(html_parts)

    # Wrap in collapsible <details> if requested
    if collapsed:
        summary_text = f"Key Terms ({total_terms})"
        return (
            f'<details class="bengal-glossary-collapsed">\n'
            f"<summary>{summary_text}</summary>\n"
            f"{content}\n"
            f"</details>"
        )

    return content


def _load_glossary_data(renderer: Any, source_path: str) -> dict[str, Any]:
    """
    Load glossary data from site.data or file.

    Tries these sources in order:
    1. site.data.glossary (if source is default data/glossary.yaml)
    2. File loading using site.root_path

    Args:
        renderer: Mistune renderer with _site attribute
        source_path: Path to glossary file (default: data/glossary.yaml)

    Returns:
        Dict with 'terms' key, or 'error' key on failure
    """
    site = getattr(renderer, "_site", None)

    # Try site.data first (data files pre-loaded from data/ directory)
    if site and hasattr(site, "data") and site.data:
        # Convert path like "data/glossary.yaml" to data key "glossary"
        if source_path == DEFAULT_GLOSSARY_PATH:
            # Default path: look for site.data.glossary
            glossary_data = getattr(site.data, "glossary", None)
            if glossary_data and isinstance(glossary_data, dict):
                terms = glossary_data.get("terms", [])
                if isinstance(terms, list):
                    return {"terms": terms}
        else:
            # Custom path: try to resolve from site.data hierarchy
            # e.g., "data/team/glossary.yaml" -> site.data.team.glossary
            parts = source_path.replace("\\", "/").split("/")
            if parts and parts[0] == "data":
                parts = parts[1:]  # Remove "data" prefix
            if parts:
                # Remove .yaml/.yml extension from last part
                last = parts[-1]
                if last.endswith(".yaml") or last.endswith(".yml"):
                    parts[-1] = last.rsplit(".", 1)[0]

                # Navigate site.data hierarchy
                current = site.data
                for part in parts:
                    if hasattr(current, part):
                        current = getattr(current, part)
                    elif isinstance(current, dict) and part in current:
                        current = current[part]
                    else:
                        current = None
                        break

                if current and isinstance(current, dict):
                    terms = current.get("terms", [])
                    if isinstance(terms, list):
                        return {"terms": terms}

    # Fallback: Load from file using site.root_path
    # No CWD fallback - path resolution must be explicit
    # See: plan/active/rfc-path-resolution-architecture.md
    if not site or not hasattr(site, "root_path"):
        logger.warning(
            "glossary_missing_site_context",
            source_path=source_path,
            action="returning_error",
            hint="Ensure renderer has _site attribute with root_path",
        )
        return {"error": "Site context not available for path resolution"}
    root_path = site.root_path

    file_path = Path(root_path) / source_path

    if not file_path.exists():
        return {"error": f"Glossary file not found: {source_path}"}

    try:
        data = load_data_file(file_path, on_error="raise", caller="glossary")

        if not isinstance(data, dict):
            return {"error": "Glossary file must contain a dictionary"}

        if "terms" not in data:
            return {"error": "Glossary file must contain 'terms' list"}

        terms = data["terms"]
        if not isinstance(terms, list):
            return {"error": "'terms' must be a list"}

        return {"terms": terms}

    except Exception as e:
        logger.error("glossary_parse_error", path=str(file_path), error=str(e))
        return {"error": f"Failed to parse glossary: {e}"}


def _filter_terms(terms: list[dict[str, Any]], tags: list[str]) -> list[dict[str, Any]]:
    """
    Filter terms by tags.

    A term matches if it has ANY of the requested tags (OR logic).

    Args:
        terms: List of term dicts from glossary
        tags: List of tags to match

    Returns:
        List of matching terms
    """
    filtered = []
    tags_set = set(tags)

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


def _render_term(renderer: Any, term_data: dict[str, Any], show_tags: bool) -> str:
    """Render a single glossary term as dt/dd pair."""
    term = term_data.get("term", "Unknown Term")
    definition = term_data.get("definition", "No definition provided.")
    term_tags = term_data.get("tags", [])

    parts = []

    # Term (dt) - escape HTML but don't parse markdown
    parts.append(f"  <dt>{_escape_html(term)}</dt>")

    # Definition (dd) - parse inline markdown
    dd_content = _parse_inline_markdown(renderer, definition)

    # Optionally show tags
    if show_tags and term_tags:
        tag_badges = " ".join(
            f'<span class="bengal-glossary-tag">{_escape_html(t)}</span>' for t in term_tags
        )
        dd_content += f'<div class="bengal-glossary-tags">{tag_badges}</div>'

    parts.append(f"  <dd>{dd_content}</dd>")

    return "\n".join(parts)


def _parse_inline_markdown(renderer: Any, text: str) -> str:
    """
    Parse inline markdown in glossary definitions.

    Tries to use mistune's inline parser first (proper way),
    falls back to simple regex for basic markdown if not available.

    Args:
        renderer: Mistune renderer instance
        text: Text to parse

    Returns:
        HTML string with inline markdown converted
    """
    # Try to use mistune's inline parser (proper way)
    if hasattr(renderer, "_md"):
        md_instance = renderer._md
        if hasattr(md_instance, "inline"):
            try:
                result: str = md_instance.inline(text)
                return result
            except Exception as e:
                logger.debug(
                    "glossary_inline_parse_failed",
                    method="_md",
                    error=str(e),
                    error_type=type(e).__name__,
                    action="trying_md_fallback",
                )
                pass
    elif hasattr(renderer, "md"):
        md_instance = renderer.md
        if hasattr(md_instance, "inline"):
            try:
                result = str(md_instance.inline(text))
                return result
            except Exception as e:
                logger.debug(
                    "glossary_inline_parse_failed",
                    method="md",
                    error=str(e),
                    error_type=type(e).__name__,
                    action="using_regex_fallback",
                )
                pass

    # Fallback to simple regex for basic markdown
    # First escape HTML to prevent XSS
    text = _escape_html(text)
    # **bold** -> <strong>bold</strong>
    text = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)
    # *italic* -> <em>italic</em> (but not if it's part of **bold**)
    text = re.sub(r"(?<!\*)\*([^*]+?)\*(?!\*)", r"<em>\1</em>", text)
    # `code` -> <code>code</code>
    text = re.sub(r"`(.+?)`", r"<code>\1</code>", text)
    return text


def _escape_html(text: str) -> str:
    """Escape HTML special characters."""
    return (
        str(text)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )
