"""
Cross-reference plugin for Mistune.

Provides [[link]] syntax for internal page references with O(1) lookup
performance using pre-built xref_index.
"""

from __future__ import annotations

import re
from re import Match
from typing import Any

from bengal.utils.logger import get_logger

logger = get_logger(__name__)

__all__ = ["CrossReferencePlugin"]


class CrossReferencePlugin:
    """
    Mistune plugin for inline cross-references with [[link]] syntax.

    Syntax:
        [[docs/installation]]           -> Link with page title
        [[docs/installation|Install]]   -> Link with custom text
        [[#heading-name]]               -> Link to heading anchor
        [[!target-id]]                  -> Link to target directive anchor
        [[id:my-page]]                  -> Link by custom ID
        [[id:my-page|Custom]]          -> Link by ID with custom text

    Performance: O(1) per reference (dictionary lookup from xref_index)
    Thread-safe: Read-only access to xref_index built during discovery

    Architecture:
    - Runs as inline parser (processes text before rendering)
    - Uses xref_index for O(1) lookups (no linear search)
    - Returns raw HTML that bypasses further processing
    - Broken refs get special markup for debugging/health checks

    Note: For Mistune v3, this works by post-processing the rendered HTML
    to replace [[link]] patterns. This is simpler and more compatible than
    trying to hook into the inline parser which has a complex API.
    """

    def __init__(self, xref_index: dict[str, Any]):
        """
        Initialize cross-reference plugin.

        Args:
            xref_index: Pre-built cross-reference index from site discovery
        """
        self.xref_index = xref_index
        # Compile regex once (reused for all pages)
        # Matches: [[path]] or [[path|text]]
        self.pattern = re.compile(r"\[\[([^\]|]+)(?:\|([^\]]+))?\]\]")

    def __call__(self, md: Any) -> None:
        """
        Register the plugin with Mistune.

        For Mistune v3, we post-process the HTML output to replace [[link]] patterns.
        This is simpler and more compatible than hooking into the inline parser.
        """
        if md.renderer and md.renderer.NAME == "html":
            # Store original text renderer
            original_text = md.renderer.text

            # Create wrapped renderer that processes cross-references
            def text_with_xref(text: str) -> str:
                """Render text with cross-reference substitution."""
                # First apply original text rendering
                rendered = original_text(text)
                # Then replace [[link]] patterns
                rendered = self._replace_xrefs_in_text(rendered)
                return rendered

            # Replace text renderer
            md.renderer.text = text_with_xref

    def _substitute_xrefs(self, html: str) -> str:
        """
        Substitute [[link]] patterns in HTML, avoiding code blocks.

        Args:
            html: HTML content that may contain [[link]] patterns

        Returns:
            HTML with [[link]] patterns replaced by links, respecting code blocks
        """
        # Quick rejection: most text doesn't have [[link]] patterns
        if "[[" not in html:
            return html

        # Split by code blocks (both pre/code blocks and inline code)
        # Use non-greedy matching for content
        # Pattern captures delimiters so they are included in parts
        parts = re.split(
            r"(<pre.*?</pre>|<code[^>]*>.*?</code>)", html, flags=re.DOTALL | re.IGNORECASE
        )

        for i in range(0, len(parts), 2):
            # Even indices are text outside code blocks
            parts[i] = self._replace_xrefs_in_text(parts[i])

        return "".join(parts)

    def _replace_xrefs_in_text(self, text: str) -> str:
        """
        Substitute [[link]] patterns in text node.
        """
        if "[[" not in text:
            return text

        def replace_xref(match: Match[str]) -> str:
            ref = match.group(1).strip()
            text = match.group(2).strip() if match.group(2) else None

            # Resolve reference to HTML link
            if ref.startswith("!"):
                # Target directive reference: [[!target-id]]
                return self._resolve_target(ref[1:], text)
            elif ref.startswith("#"):
                # Heading anchor reference: [[#heading-name]]
                return self._resolve_heading(ref, text)
            elif ref.startswith("id:"):
                # Custom ID reference: [[id:my-page]]
                return self._resolve_id(ref[3:], text)
            else:
                # Path reference: [[docs/page]]
                return self._resolve_path(ref, text)

        return self.pattern.sub(replace_xref, text)

    def _resolve_path(self, path: str, text: str | None = None) -> str:
        """
        Resolve path reference to link.

        O(1) dictionary lookup. Supports path#anchor syntax.
        """
        # Extract anchor fragment if present (e.g., docs/page#section -> docs/page, section)
        anchor_fragment = ""
        if "#" in path:
            path, anchor_fragment = path.split("#", 1)
            anchor_fragment = f"#{anchor_fragment}"

        # Normalize path (remove .md extension if present)
        clean_path = path.replace(".md", "")
        page = self.xref_index.get("by_path", {}).get(clean_path)

        if not page:
            # Try slug fallback
            pages = self.xref_index.get("by_slug", {}).get(clean_path, [])
            page = pages[0] if pages else None

        if not page:
            logger.debug(
                "xref_resolution_failed",
                ref=path,
                type="path",
                clean_path=clean_path,
                available_paths=len(self.xref_index.get("by_path", {})),
            )
            return (
                f'<span class="broken-ref" data-ref="{path}" '
                f'title="Page not found: {path}">[{text or path}]</span>'
            )

        url = page.url if hasattr(page, "url") else f"/{page.slug}/"
        full_url = f"{url}{anchor_fragment}"

        logger.debug(
            "xref_resolved",
            ref=path,
            type="path",
            target=page.title,
            url=full_url,
        )

        link_text = text or page.title
        return f'<a href="{full_url}">{link_text}</a>'

    def _resolve_id(self, ref_id: str, text: str | None = None) -> str:
        """
        Resolve ID reference to link.

        O(1) dictionary lookup.
        """
        page = self.xref_index.get("by_id", {}).get(ref_id)

        if not page:
            logger.debug(
                "xref_resolution_failed",
                ref=f"id:{ref_id}",
                type="id",
                available_ids=len(self.xref_index.get("by_id", {})),
            )
            return (
                f'<span class="broken-ref" data-ref="id:{ref_id}" '
                f'title="ID not found: {ref_id}">[{text or ref_id}]</span>'
            )

        logger.debug("xref_resolved", ref=f"id:{ref_id}", type="id", target=page.title)

        link_text = text or page.title
        url = page.url if hasattr(page, "url") else f"/{page.slug}/"
        return f'<a href="{url}">{link_text}</a>'

    def _resolve_target(self, anchor_id: str, text: str | None = None) -> str:
        """
        Resolve target directive reference to link.

        O(1) dictionary lookup. Only checks by_anchor (target directives).

        Args:
            anchor_id: Target directive anchor ID (without ! prefix)
            text: Optional custom link text

        Returns:
            HTML link or broken reference indicator
        """
        anchor_key = anchor_id.lower()
        explicit = self.xref_index.get("by_anchor", {}).get(anchor_key)

        if not explicit:
            logger.debug(
                "xref_resolution_failed",
                ref=f"!{anchor_id}",
                type="target",
                anchor_key=anchor_key,
                available_anchors=len(self.xref_index.get("by_anchor", {})),
            )
            return (
                f'<span class="broken-ref" data-ref="!{anchor_id}" '
                f'title="Target directive not found: {anchor_id}">[{text or anchor_id}]</span>'
            )

        page, anchor_id_resolved = explicit
        logger.debug(
            "xref_resolved",
            ref=f"!{anchor_id}",
            type="target",
            target_page=page.title if hasattr(page, "title") else "unknown",
            anchor_id=anchor_id_resolved,
        )
        link_text = text or anchor_id.replace("-", " ").title()
        url = page.url if hasattr(page, "url") else f"/{page.slug}/"
        return f'<a href="{url}#{anchor_id_resolved}">{link_text}</a>'

    def _resolve_heading(self, anchor: str, text: str | None = None) -> str:
        """
        Resolve heading anchor reference to link.

        O(1) dictionary lookup.

        Resolution order:
        1. Check explicit anchor IDs first (by_anchor) - supports {#custom-id} syntax
        2. Fall back to heading text lookup (by_heading) - existing behavior

        Note: This resolves both heading anchors and target directives.
        Use [[!target-id]] for explicit target directive references to avoid collisions.
        """
        # Remove leading # if present
        anchor_key = anchor.lstrip("#").lower()

        # First check explicit anchor IDs (supports {#custom-id} syntax)
        # This includes both heading anchors and target directives
        explicit = self.xref_index.get("by_anchor", {}).get(anchor_key)
        if explicit:
            page, anchor_id = explicit
            logger.debug(
                "xref_resolved",
                ref=anchor,
                type="explicit_anchor",
                target_page=page.title if hasattr(page, "title") else "unknown",
                anchor_id=anchor_id,
            )
            link_text = text or anchor_key.replace("-", " ").title()
            url = page.url if hasattr(page, "url") else f"/{page.slug}/"
            return f'<a href="{url}#{anchor_id}">{link_text}</a>'

        # Fall back to heading text lookup
        results = self.xref_index.get("by_heading", {}).get(anchor_key, [])

        if not results:
            logger.debug(
                "xref_resolution_failed",
                ref=anchor,
                type="heading",
                anchor_key=anchor_key,
                available_headings=len(self.xref_index.get("by_heading", {})),
                available_anchors=len(self.xref_index.get("by_anchor", {})),
            )
            return (
                f'<span class="broken-ref" data-anchor="{anchor}" '
                f'title="Heading not found: {anchor}">[{text or anchor}]</span>'
            )

        # Use first match
        page, anchor_id = results[0]
        logger.debug(
            "xref_resolved",
            ref=anchor,
            type="heading",
            target_page=page.title if hasattr(page, "title") else "unknown",
            anchor_id=anchor_id,
            matches=len(results),
        )

        link_text = text or anchor.lstrip("#").replace("-", " ").title()
        url = page.url if hasattr(page, "url") else f"/{page.slug}/"
        return f'<a href="{url}#{anchor_id}">{link_text}</a>'
