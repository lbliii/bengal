"""
Glossary directive for Bengal SSG.

Renders key terms from a centralized glossary data file as definition lists.
Supports filtering by tags to show relevant terms for each page.

Syntax:
    :::{glossary}
    :tags: directives, navigation
    :::

    :::{glossary}
    :tags: admonitions
    :sorted: true
    :::

The directive loads terms from data/glossary.yaml and renders matching
terms as a styled definition list.
"""

from __future__ import annotations

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
        :::

    Options:
        - tags: Comma-separated list of tags to filter terms (required)
        - sorted: Sort terms alphabetically (default: false, preserves file order)
        - show-tags: Display tag badges under each term (default: false)
        - source: Custom glossary file path (default: data/glossary.yaml)
    """

    def parse(self, block: Any, m: Match, state: Any) -> dict[str, Any]:
        """
        Parse glossary directive.

        Args:
            block: Block parser
            m: Regex match object
            state: Parser state

        Returns:
            Token dict with type 'glossary'
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
        source_path = options.get("source", DEFAULT_GLOSSARY_PATH)

        # Load glossary data
        glossary_result = self._load_glossary(source_path, state)

        if "error" in glossary_result:
            logger.error(
                "glossary_load_error",
                path=source_path,
                error=glossary_result["error"],
            )
            return {
                "type": "glossary",
                "attrs": {"error": glossary_result["error"], "path": source_path},
                "children": [],
            }

        # Filter terms by tags
        all_terms = glossary_result.get("terms", [])
        filtered_terms = self._filter_terms(all_terms, tags)

        if not filtered_terms:
            return {
                "type": "glossary",
                "attrs": {
                    "error": f"No terms found matching tags: {', '.join(tags)}",
                    "path": source_path,
                },
                "children": [],
            }

        # Sort if requested
        if sorted_terms:
            filtered_terms = sorted(filtered_terms, key=lambda t: t.get("term", "").lower())

        # Build attributes for renderer
        attrs = {
            "terms": filtered_terms,
            "tags": tags,
            "sorted": sorted_terms,
            "show_tags": show_tags,
            "source": source_path,
        }

        return {"type": "glossary", "attrs": attrs, "children": []}

    def _load_glossary(self, path: str, state: Any) -> dict[str, Any]:
        """
        Load glossary from YAML file.

        Args:
            path: Relative path to glossary file
            state: Parser state (contains site context)

        Returns:
            Dict with 'terms' key, or 'error' key on failure
        """
        # Try to get root_path from state (set by rendering pipeline)
        root_path = getattr(state, "root_path", None) or Path.cwd()
        file_path = Path(root_path) / path

        # Check if file exists
        if not file_path.exists():
            return {"error": f"Glossary file not found: {path}"}

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

    def _filter_terms(self, terms: list[dict], tags: list[str]) -> list[dict]:
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

    def _parse_bool(self, value: str | bool) -> bool:
        """Parse boolean option value."""
        if isinstance(value, bool):
            return value
        return str(value).lower() in ("true", "1", "yes", "on")

    def __call__(self, directive: Any, md: Any) -> Any:
        """Register the directive and renderer."""
        directive.register("glossary", self.parse)

        if md.renderer and md.renderer.NAME == "html":
            md.renderer.register("glossary", render_glossary)


def render_glossary(renderer: Any, text: str, **attrs: Any) -> str:
    """
    Render glossary to HTML as a definition list.

    Args:
        renderer: Mistune renderer
        text: Rendered children content (unused for glossary)
        **attrs: Glossary attributes from directive

    Returns:
        HTML string for glossary definition list
    """
    # Check for error
    if "error" in attrs:
        error_msg = attrs["error"]
        path = attrs.get("path", "unknown")
        return f"""<div class="bengal-glossary-error" role="alert">
    <strong>Glossary Error:</strong> {error_msg}
    <br><small>Source: {path}</small>
</div>"""

    terms = attrs["terms"]
    show_tags = attrs.get("show_tags", False)

    # Build definition list
    html_parts = ['<dl class="bengal-glossary">']

    for term_data in terms:
        term = term_data.get("term", "Unknown Term")
        definition = term_data.get("definition", "No definition provided.")
        term_tags = term_data.get("tags", [])

        # Term (dt)
        html_parts.append(f"  <dt>{_escape_html(term)}</dt>")

        # Definition (dd)
        dd_content = _escape_html(definition)

        # Optionally show tags
        if show_tags and term_tags:
            tag_badges = " ".join(
                f'<span class="bengal-glossary-tag">{_escape_html(t)}</span>'
                for t in term_tags
            )
            dd_content += f'<div class="bengal-glossary-tags">{tag_badges}</div>'

        html_parts.append(f"  <dd>{dd_content}</dd>")

    html_parts.append("</dl>")

    return "\n".join(html_parts)


def _escape_html(text: str) -> str:
    """Escape HTML special characters."""
    return (
        str(text)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )

