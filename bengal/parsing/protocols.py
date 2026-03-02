"""
Parser protocols for extended Markdown parser interfaces.

RichMarkdownParser extends BaseMarkdownParser with cross-reference support,
variable substitution, and context-aware parsing. Used by the rendering
pipeline when the parser supports these features.
"""

from __future__ import annotations

from typing import Any, Protocol


class RichMarkdownParser(Protocol):
    """Parser with xref, context, and variable substitution support.

    Implemented by PatitasParser. The rendering pipeline narrows to this
    protocol when calling enable_cross_references, parse_with_toc_and_context,
    or accessing _var_plugin for placeholder restoration.
    """

    _var_plugin: Any | None

    def enable_cross_references(
        self,
        xref_index: dict[str, Any],
        version_config: Any | None = None,
        cross_version_tracker: Any | None = None,
        external_ref_resolver: Any | None = None,
    ) -> None:
        """Enable cross-reference support with [[link]] syntax."""
        ...

    def parse_with_toc_and_context(
        self, content: str, metadata: dict[str, Any], context: dict[str, Any]
    ) -> tuple[str, str, str, str]:
        """Parse with variable substitution and extract TOC, excerpt, meta description."""
        ...

    def parse_with_context(
        self, content: str, metadata: dict[str, Any], context: dict[str, Any]
    ) -> str:
        """Parse Markdown with variable substitution support."""
        ...
