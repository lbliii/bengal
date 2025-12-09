"""
Term/Glossary plugin for Mistune.

Provides {term}`Word` syntax for linking to glossary terms.
"""

from __future__ import annotations

import re
from typing import Any

from bengal.utils.text import slugify

__all__ = ["TermPlugin"]


class TermPlugin:
    """
    Mistune plugin for {term}`Word` syntax.

    Syntax:
        {term}`Word`          -> Link to /glossary/#term-word
        {term}`Word Text`     -> Link to /glossary/#term-word-text

    Architecture:
    - Runs as a standard Mistune inline plugin
    - Registers a high-priority rule to capture {term}`...`
    """

    def __call__(self, md: Any) -> None:
        """Register the plugin with Mistune."""
        # Register inline rule
        # Pattern: {term}`Content`
        md.inline.register(
            "term",
            r"\{term\}`([^`]+)`",
            self.parse_term,
            before="codespan",
        )

        # Register renderer
        if md.renderer and md.renderer.NAME == "html":
            md.renderer.register("term", self.render_term)

    def parse_term(self, inline: Any, m: re.Match[str], state: Any) -> int:
        """Parse {term}`...` syntax."""
        text = m.group(1)
        state.append_token({"type": "term", "raw": text})
        return m.end()

    def render_term(self, renderer: Any, text: str) -> str:
        """Render term token to HTML."""
        # The text is in the 'raw' field of the token, passed as text argument
        # if using standard renderer, but here we get the text content
        slug = slugify(text)
        return f'<a href="/glossary/#term-{slug}" class="term-link" data-term="{slug}">{text}</a>'
