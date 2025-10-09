"""
Cross-reference plugin for Mistune.

Provides [[link]] syntax for internal page references with O(1) lookup
performance using pre-built xref_index.
"""

import re
from typing import Any, Dict, Match, Optional

from bengal.utils.logger import get_logger

logger = get_logger(__name__)

__all__ = ['CrossReferencePlugin']


class CrossReferencePlugin:
    """
    Mistune plugin for inline cross-references with [[link]] syntax.
    
    Syntax:
        [[docs/installation]]           -> Link with page title
        [[docs/installation|Install]]   -> Link with custom text
        [[#heading-name]]               -> Link to heading anchor
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
    
    def __init__(self, xref_index: Dict[str, Any]):
        """
        Initialize cross-reference plugin.
        
        Args:
            xref_index: Pre-built cross-reference index from site discovery
        """
        self.xref_index = xref_index
        # Compile regex once (reused for all pages)
        # Matches: [[path]] or [[path|text]]
        self.pattern = re.compile(
            r'\[\[([^\]|]+)(?:\|([^\]]+))?\]\]'
        )
    
    def __call__(self, md):
        """
        Register the plugin with Mistune.
        
        For Mistune v3, we post-process the HTML output to replace [[link]] patterns.
        This is simpler and more compatible than hooking into the inline parser.
        """
        if md.renderer and md.renderer.NAME == 'html':
            # Store original text renderer
            original_text = md.renderer.text
            
            # Create wrapped renderer that processes cross-references
            def text_with_xref(text: str) -> str:
                """Render text with cross-reference substitution."""
                # First apply original text rendering
                rendered = original_text(text)
                # Then replace [[link]] patterns
                rendered = self._substitute_xrefs(rendered)
                return rendered
            
            # Replace text renderer
            md.renderer.text = text_with_xref
        
        return md
    
    def _substitute_xrefs(self, text: str) -> str:
        """
        Substitute [[link]] patterns in text with resolved links.
        
        Args:
            text: Text content that may contain [[link]] patterns
        
        Returns:
            Text with [[link]] patterns replaced by HTML links
        """
        # Quick rejection: most text doesn't have [[link]] patterns
        # This saves expensive regex matching on 90%+ of text nodes
        if '[[' not in text:
            return text
        
        def replace_xref(match: Match) -> str:
            ref = match.group(1).strip()
            text = match.group(2).strip() if match.group(2) else None
            
            # Resolve reference to HTML link
            if ref.startswith('#'):
                return self._resolve_heading(ref, text)
            elif ref.startswith('id:'):
                return self._resolve_id(ref[3:], text)
            else:
                return self._resolve_path(ref, text)
        
        return self.pattern.sub(replace_xref, text)
    
    def _resolve_path(self, path: str, text: Optional[str] = None) -> str:
        """
        Resolve path reference to link.
        
        O(1) dictionary lookup.
        """
        # Normalize path (remove .md extension if present)
        clean_path = path.replace('.md', '')
        page = self.xref_index.get('by_path', {}).get(clean_path)
        
        if not page:
            # Try slug fallback
            pages = self.xref_index.get('by_slug', {}).get(clean_path, [])
            page = pages[0] if pages else None
        
        if not page:
            logger.debug(
                "xref_resolution_failed",
                ref=path,
                type="path",
                clean_path=clean_path,
                available_paths=len(self.xref_index.get('by_path', {}))
            )
            return (
                f'<span class="broken-ref" data-ref="{path}" '
                f'title="Page not found: {path}">[{text or path}]</span>'
            )
        
        logger.debug(
            "xref_resolved",
            ref=path,
            type="path",
            target=page.title,
            url=page.url if hasattr(page, 'url') else f'/{page.slug}/'
        )
        
        link_text = text or page.title
        url = page.url if hasattr(page, 'url') else f'/{page.slug}/'
        return f'<a href="{url}">{link_text}</a>'
    
    def _resolve_id(self, ref_id: str, text: Optional[str] = None) -> str:
        """
        Resolve ID reference to link.
        
        O(1) dictionary lookup.
        """
        page = self.xref_index.get('by_id', {}).get(ref_id)
        
        if not page:
            logger.debug(
                "xref_resolution_failed",
                ref=f"id:{ref_id}",
                type="id",
                available_ids=len(self.xref_index.get('by_id', {}))
            )
            return (
                f'<span class="broken-ref" data-ref="id:{ref_id}" '
                f'title="ID not found: {ref_id}">[{text or ref_id}]</span>'
            )
        
        logger.debug(
            "xref_resolved",
            ref=f"id:{ref_id}",
            type="id",
            target=page.title
        )
        
        link_text = text or page.title
        url = page.url if hasattr(page, 'url') else f'/{page.slug}/'
        return f'<a href="{url}">{link_text}</a>'
    
    def _resolve_heading(self, anchor: str, text: Optional[str] = None) -> str:
        """
        Resolve heading anchor reference to link.
        
        O(1) dictionary lookup.
        """
        # Remove leading # if present
        heading_key = anchor.lstrip('#').lower()
        results = self.xref_index.get('by_heading', {}).get(heading_key, [])
        
        if not results:
            logger.debug(
                "xref_resolution_failed",
                ref=anchor,
                type="heading",
                heading_key=heading_key,
                available_headings=len(self.xref_index.get('by_heading', {}))
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
            target_page=page.title if hasattr(page, 'title') else 'unknown',
            anchor_id=anchor_id,
            matches=len(results)
        )
        
        link_text = text or anchor.lstrip('#').replace('-', ' ').title()
        url = page.url if hasattr(page, 'url') else f'/{page.slug}/'
        return f'<a href="{url}#{anchor_id}">{link_text}</a>'

