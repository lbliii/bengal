"""
Cross-reference plugin for Mistune.

Provides [[link]] syntax for internal page references with O(1) lookup
performance using pre-built xref_index.

Extended to support cross-version linking:
    [[v2:path]]     -> Link to path in version v2
    [[latest:path]] -> Link to path in latest version
"""

from __future__ import annotations

import re
from collections.abc import Callable
from pathlib import Path
from re import Match
from typing import TYPE_CHECKING, Any

from bengal.utils.logger import get_logger

if TYPE_CHECKING:
    from bengal.core.version import VersionConfig

logger = get_logger(__name__)

# Type alias for cross-version dependency callback
CrossVersionTracker = Callable[[Path, str, str], None]

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
        [[id:my-page|Custom]]           -> Link by ID with custom text
        [[v2:docs/guide]]               -> Link to docs/guide in version v2
        [[v2:docs/guide|Guide v2]]      -> Link to v2 with custom text
        [[latest:docs/guide]]           -> Link to docs/guide in latest version

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

    def __init__(
        self,
        xref_index: dict[str, Any],
        version_config: VersionConfig | None = None,
        cross_version_tracker: CrossVersionTracker | None = None,
    ):
        """
        Initialize cross-reference plugin.

        Args:
            xref_index: Pre-built cross-reference index from site discovery
            version_config: Optional versioning configuration for cross-version links
            cross_version_tracker: Optional callback to track cross-version link dependencies.
                Called with (source_page, target_version, target_path) when a [[v2:path]]
                link is resolved. Used by DependencyTracker for incremental rebuilds.

        RFC: rfc-versioned-docs-pipeline-integration (Phase 2)
        """
        self.xref_index = xref_index
        self.version_config = version_config
        self.current_version: str | None = (
            None  # Current page's version (set per-page during rendering)
        )
        self.current_source_page: Path | None = (
            None  # Current page's source path (set per-page during rendering)
        )
        self._cross_version_tracker = cross_version_tracker
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
            link_text = match.group(2).strip() if match.group(2) else None

            # Resolve reference to HTML link
            if ref.startswith("!"):
                # Target directive reference: [[!target-id]]
                return self._resolve_target(ref[1:], link_text)
            elif ref.startswith("#"):
                # Heading anchor reference: [[#heading-name]]
                return self._resolve_heading(ref, link_text)
            elif ref.startswith("id:"):
                # Custom ID reference: [[id:my-page]]
                return self._resolve_id(ref[3:], link_text)
            elif ":" in ref and not ref.startswith(("http:", "https:", "mailto:")):
                # Cross-version reference: [[v2:docs/page]] or [[latest:docs/page]]
                return self._resolve_version_link(ref, link_text)
            else:
                # Path reference: [[docs/page]]
                return self._resolve_path(ref, link_text)

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

        url = page.href
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
        url = page.href
        return f'<a href="{url}">{link_text}</a>'

    def _resolve_target(self, anchor_id: str, text: str | None = None) -> str:
        """
        Resolve target directive reference to link.

        Prefers anchors from the same version as the current page, falls back to other versions.

        Args:
            anchor_id: Target directive anchor ID (without ! prefix)
            text: Optional custom link text

        Returns:
            HTML link or broken reference indicator
        """
        anchor_key = anchor_id.lower()
        anchor_entries = self.xref_index.get("by_anchor", {}).get(anchor_key)

        if not anchor_entries:
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

        # Handle list of tuples format: [(page, anchor_id, version_id), ...]
        # Prefer same-version anchor, fall back to first available
        same_version_entry = None
        for entry in anchor_entries:
            if len(entry) >= 3 and entry[2] == self.current_version:
                same_version_entry = entry
                break

        if same_version_entry:
            page, anchor_id_resolved, _ = same_version_entry
        else:
            # Fall back to first entry (any version)
            page, anchor_id_resolved, _ = anchor_entries[0]

        logger.debug(
            "xref_resolved",
            ref=f"!{anchor_id}",
            type="target",
            target_page=page.title if hasattr(page, "title") else "unknown",
            anchor_id=anchor_id_resolved,
            version_match=self.current_version
            if hasattr(page, "version") and getattr(page, "version", None) == self.current_version
            else None,
        )
        link_text = text or anchor_id.replace("-", " ").title()
        url = page.href
        return f'<a href="{url}#{anchor_id_resolved}">{link_text}</a>'

    def _resolve_heading(self, anchor: str, text: str | None = None) -> str:
        """
        Resolve heading anchor reference to link.

        Prefers anchors from the same version as the current page, falls back to other versions.

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
        anchor_entries = self.xref_index.get("by_anchor", {}).get(anchor_key)
        if anchor_entries:
            # Handle list of tuples format: [(page, anchor_id, version_id), ...]
            # Prefer same-version anchor, fall back to first available
            same_version_entry = None
            for entry in anchor_entries:
                if len(entry) >= 3 and entry[2] == self.current_version:
                    same_version_entry = entry
                    break

            if same_version_entry:
                page, anchor_id, _ = same_version_entry
            else:
                # Fall back to first entry (any version)
                page, anchor_id, _ = anchor_entries[0]

            logger.debug(
                "xref_resolved",
                ref=anchor,
                type="explicit_anchor",
                target_page=page.title if hasattr(page, "title") else "unknown",
                anchor_id=anchor_id,
                version_match=self.current_version
                if hasattr(page, "version")
                and getattr(page, "version", None) == self.current_version
                else None,
            )
            link_text = text or anchor_key.replace("-", " ").title()
            url = page.href
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
        url = page.href
        return f'<a href="{url}#{anchor_id}">{link_text}</a>'

    def _resolve_version_link(self, ref: str, text: str | None = None) -> str:
        """
        Resolve cross-version link reference.

        Handles [[v2:path]] and [[latest:path]] syntax.

        RFC: rfc-versioned-docs-pipeline-integration (Phase 2)
        - Tracks cross-version link dependencies for incremental rebuilds

        Args:
            ref: Reference string in format "version:path"
            text: Optional custom link text

        Returns:
            HTML link or broken reference indicator
        """
        # Parse version:path format
        version_id, path = ref.split(":", 1)

        # Track cross-version dependency for incremental rebuilds
        if self._cross_version_tracker is not None and self.current_source_page is not None:
            # Normalize path for tracking (remove anchor, clean up)
            track_path = path.split("#")[0].replace(".md", "").strip("/")
            self._cross_version_tracker(
                self.current_source_page,
                version_id,
                track_path,
            )

        # Check if versioning is enabled
        if not self.version_config or not self.version_config.enabled:
            logger.debug(
                "xref_resolution_failed",
                ref=ref,
                type="version",
                reason="versioning_disabled",
            )
            return (
                f'<span class="broken-ref" data-ref="{ref}" '
                f'title="Versioning not enabled">[{text or path}]</span>'
            )

        # Resolve version (supports aliases like "latest", "stable")
        target_version = self.version_config.get_version_or_alias(version_id)

        if not target_version:
            logger.debug(
                "xref_resolution_failed",
                ref=ref,
                type="version",
                version_id=version_id,
                reason="version_not_found",
            )
            return (
                f'<span class="broken-ref" data-ref="{ref}" '
                f'title="Version not found: {version_id}">[{text or path}]</span>'
            )

        # Extract anchor fragment if present
        anchor_fragment = ""
        if "#" in path:
            path, anchor_fragment = path.split("#", 1)
            anchor_fragment = f"#{anchor_fragment}"

        # Try to find the page in xref_index to get title for link text
        clean_path = path.replace(".md", "").strip("/")
        page = self.xref_index.get("by_path", {}).get(clean_path)

        # Build URL with version prefix
        if target_version.latest:
            # Latest version has no prefix in URL
            url = f"/{clean_path}/"
        else:
            # Find the versioned section to construct proper URL
            # Default to first versioned section if path doesn't start with one
            versioned_section = None
            for section in self.version_config.sections:
                if clean_path.startswith(section):
                    versioned_section = section
                    break

            if versioned_section:
                # Path already includes section: docs/guide -> docs/v2/guide
                section_rest = clean_path[len(versioned_section) :].lstrip("/")
                url = f"/{versioned_section}/{target_version.id}/{section_rest}/"
            else:
                # No section match, assume first versioned section
                if self.version_config.sections:
                    section = self.version_config.sections[0]
                    url = f"/{section}/{target_version.id}/{clean_path}/"
                else:
                    url = f"/{target_version.id}/{clean_path}/"

        full_url = f"{url}{anchor_fragment}"

        # Determine link text
        if text:
            link_text = text
        elif page and hasattr(page, "title"):
            link_text = f"{page.title} ({target_version.label})"
        else:
            link_text = f"{clean_path} ({target_version.label})"

        logger.debug(
            "xref_resolved",
            ref=ref,
            type="version",
            version_id=target_version.id,
            url=full_url,
        )

        return f'<a href="{full_url}">{link_text}</a>'
