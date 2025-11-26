"""
Term directive for inline tooltips.

Syntax:
    {term="Definition text"}Term Name{/term}
    {term}Term Name{/term} (uses term as definition, or looks up in glossary - glossary lookup not implemented yet)

Renders as:
    <span class="term" data-tooltip="Definition text">Term Name</span>
"""

from __future__ import annotations

import re

from bengal.utils.logger import get_logger

logger = get_logger(__name__)

# Pattern: {term ...} ... {/term}
# Matches:
#   {term}text{/term}
#   {term="def"}text{/term}
#   {term def}text{/term}
TERM_PATTERN = r"\{term(?P<term_attrs>.*?)\}(?P<term_text>.*?)\{/term\}"


def parse_term(inline, m, state):
    """Parse term directive."""
    attrs_str = m.group("term_attrs").strip()
    text = m.group("term_text")

    definition = ""

    # Parse attributes
    # Case 1: {term="definition"}
    # Case 2: {term='definition'}
    # Case 3: {term} (no attrs)

    if attrs_str:
        # simple regex to catch ="..." or ='...' or just text
        # This is a naive parser, similar to how other simple directives might work
        # Ideally we'd use a proper attribute parser

        # Check for ="..."
        match = re.match(r'^=["\']?(.*?)["\']?$', attrs_str)
        if match:
            definition = match.group(1)
        else:
            # Fallback: treat whole attr string as definition if it doesn't start with =
            # This handles {term definition} (if we want to support that, though typical is ="")
            # Let's assume standard key=value or just value for default arg
            definition = attrs_str

    if not definition:
        # Default: if no definition provided, use text as definition (or maybe later lookup)
        definition = f"Definition for {text}"

    return "term", text, definition


def render_term(renderer, text: str, definition: str) -> str:
    """Render term to HTML."""
    # Escape definition for attribute
    safe_def = definition.replace('"', "&quot;")
    return f'<span class="term" data-tooltip="{safe_def}">{text}</span>'


def term_plugin(md):
    """Register term plugin with Mistune."""
    md.inline.register("term", TERM_PATTERN, parse_term, before="link")

    if md.renderer and md.renderer.NAME == "html":
        md.renderer.register("term", render_term)
