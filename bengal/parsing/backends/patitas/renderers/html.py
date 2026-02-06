"""HTML renderer using StringBuilder pattern.

Renders typed AST to HTML with O(n) performance using StringBuilder.

Thread Safety:
All state is local to each render() call.
Multiple threads can render concurrently without synchronization.

Single-Pass Heading Decoration:
Heading IDs are generated during the AST walk, eliminating the need for
regex-based post-processing. TOC data is collected during rendering.

Configuration:
Uses ContextVar pattern for configuration (RFC: rfc-contextvar-config-implementation).
Configuration is read from thread-local ContextVar, not stored in slots.
This enables 50% slot reduction (14→7) and ~1.3x instantiation speedup.

Module Structure (RFC: rfc-code-health-improvements Phase 3):
- html.py: Core HtmlRenderer class (this file)
- blocks.py: Block-level rendering mixin
- inline.py: Inline dispatch handlers and table
- directives.py: Directive rendering mixin
- utils.py: Helper functions (escape, encode, slugify)
"""

from __future__ import annotations

from collections.abc import Callable, Iterator, Sequence
from typing import TYPE_CHECKING, Any, Literal

from patitas.nodes import (
    Block,
    CodeSpan,
    Emphasis,
    FootnoteDef,
    Inline,
    Link,
    Math,
    Role,
    Strikethrough,
    Strong,
    Text,
)
from patitas.stringbuilder import StringBuilder

from bengal.parsing.backends.patitas.render_config import RenderConfig, get_render_config

# Import modular components
from bengal.parsing.backends.patitas.renderers.blocks import BlockRendererMixin
from bengal.parsing.backends.patitas.renderers.directives import (
    PAGE_DEPENDENT_DIRECTIVES,
    DirectiveRendererMixin,
)
from bengal.parsing.backends.patitas.renderers.inline import INLINE_DISPATCH
from bengal.parsing.backends.patitas.renderers.utils import (
    HeadingInfo,
    default_slugify,
    escape_html,
)

if TYPE_CHECKING:
    from bengal.cache.directive_cache import DirectiveCache
    from bengal.parsing.backends.patitas.protocols import LexerDelegate


# Re-export HeadingInfo for backward compatibility
__all__ = ["HeadingInfo", "HtmlRenderer"]


class HtmlRenderer(BlockRendererMixin, DirectiveRendererMixin):
    """Render AST to HTML using StringBuilder pattern.

    O(n) rendering using StringBuilder for string accumulation.
    All state is local to each render() call.

    Configuration:
        Uses ContextVar pattern for thread-safe configuration.
        Highlighting, registries, and transformers are read from RenderConfig via properties.
        Set configuration using render_config_context() or set_render_config().

    Usage:
        >>> from bengal.parsing.backends.patitas.render_config import render_config_context, RenderConfig
        >>> with render_config_context(RenderConfig(highlight=True)):
        ...     renderer = HtmlRenderer(source)
        ...     html = renderer.render(ast)
        '<h1>Hello <strong>World</strong></h1>\\n'

    Thread Safety:
        Multiple threads can render concurrently without synchronization.
        Each call creates independent StringBuilder.

    Module Structure:
        Block rendering methods: blocks.py (BlockRendererMixin)
        Directive rendering: directives.py (DirectiveRendererMixin)
        Inline dispatch: inline.py (INLINE_DISPATCH table)
        Utilities: utils.py (escape functions, HeadingInfo)
    """

    # Class attribute for backward compatibility (re-exported from directives.py)
    _PAGE_DEPENDENT_DIRECTIVES = PAGE_DEPENDENT_DIRECTIVES

    __slots__ = (
        "_current_page",
        "_delegate",
        "_directive_cache",
        "_headings",
        "_page_context",
        "_seen_slugs",
        "_site",
        # Per-render state only (9 slots)
        "_source",
        "_xref_index",
    )

    def __init__(
        self,
        source: str = "",
        *,
        delegate: LexerDelegate | None = None,
        directive_cache: DirectiveCache | None = None,
        page_context: Any | None = None,
        xref_index: dict[str, Any] | None = None,
        site: Any | None = None,
    ) -> None:
        """Initialize renderer with source and per-render state only.

        Configuration is read from ContextVar, not passed as parameters.
        Use render_config_context() or set_render_config() to configure.

        Args:
            source: Original source buffer for zero-copy extraction
            delegate: Optional sub-lexer delegate for ZCLH handoff
            directive_cache: Optional cache for rendered directive output (per-site, not config)
            page_context: Optional page context for directives that need page/section info
            xref_index: Optional cross-reference index for link resolution
            site: Optional site object for site-wide context
        """
        self._source = source
        self._delegate = delegate
        self._headings: list[HeadingInfo] = []
        self._seen_slugs: dict[str, int] = {}  # For unique slug generation
        # Page context for directives (child-cards, breadcrumbs, etc.)
        self._page_context = page_context
        # Alias for _page_context (used by directives that look for _current_page)
        self._current_page = page_context
        # Cross-reference index for link resolution (cards, xref roles, etc.)
        self._xref_index = xref_index
        # Site object for site-wide context
        self._site = site
        # Directive cache is per-site, passed in (not config)
        self._directive_cache = directive_cache

    def _reset(
        self,
        source: str = "",
        *,
        delegate: LexerDelegate | None = None,
        directive_cache: DirectiveCache | None = None,
        page_context: Any | None = None,
        xref_index: dict[str, Any] | None = None,
        site: Any | None = None,
    ) -> None:
        """Reset renderer state for reuse.

        Clears per-render state while preserving object identity.
        Used by RendererPool.acquire() for instance pooling.

        Args:
            source: Original source buffer for zero-copy extraction
            delegate: Optional sub-lexer delegate for ZCLH handoff
            directive_cache: Optional cache for rendered directive output
            page_context: Optional page context for directives
            xref_index: Optional cross-reference index for link resolution
            site: Optional site object for site-wide context
        """
        self._source = source
        self._delegate = delegate
        self._headings = []
        self._seen_slugs = {}
        self._page_context = page_context
        self._current_page = page_context
        self._xref_index = xref_index
        self._site = site
        self._directive_cache = directive_cache

    # =========================================================================
    # Config access via properties (read from ContextVar)
    # =========================================================================

    @property
    def _config(self) -> RenderConfig:
        """Get current render configuration from ContextVar."""
        return get_render_config()

    @property
    def _highlight(self) -> bool:
        """Check if syntax highlighting is enabled."""
        return self._config.highlight

    @property
    def _highlight_style(self) -> Literal["semantic", "pygments"]:
        """Get highlighting style."""
        return self._config.highlight_style

    @property
    def _directive_registry(self):
        """Get directive registry for custom directive rendering."""
        return self._config.directive_registry

    @property
    def _role_registry(self):
        """Get role registry for custom role rendering."""
        return self._config.role_registry

    @property
    def _text_transformer(self) -> Callable[[str], str] | None:
        """Get optional text transformer callback."""
        return self._config.text_transformer

    @property
    def _heading_slugify(self) -> Callable[[str], str]:
        """Get slugify function for heading IDs."""
        return self._config.slugify or default_slugify

    @property
    def _rosettes_available(self) -> bool:
        """Check if rosettes highlighter is available."""
        return self._config.rosettes_available

    # =========================================================================
    # Main render entry point
    # =========================================================================

    def render(self, nodes: Sequence[Block]) -> str:
        """Render AST nodes to HTML.

        Heading IDs are generated during this walk (single-pass decoration).
        Use get_headings() after render() to retrieve collected heading info.

        Args:
            nodes: Sequence of Block AST nodes

        Returns:
            Rendered HTML string
        """
        # Clear heading state for fresh render
        self._headings = []
        self._seen_slugs = {}

        sb = StringBuilder()
        footnotes: list[FootnoteDef] = []

        for node in nodes:
            # Collect footnote definitions for rendering at the end
            if isinstance(node, FootnoteDef):
                footnotes.append(node)
            else:
                self._render_block(node, sb)

        # Render footnote definitions section at the end
        if footnotes:
            self._render_footnotes_section(footnotes, sb)

        return sb.build()

    # =========================================================================
    # Inline rendering (uses dispatch table from inline.py)
    # =========================================================================

    def _render_inline_children(self, children: Sequence[Inline], sb: StringBuilder) -> None:
        """Render inline children using dict dispatch for speed."""
        # Local references for tight loop
        dispatch = INLINE_DISPATCH
        render_children = self._render_inline_children
        role_registry = self._role_registry
        for child in children:
            # Check for Role nodes with registry-based rendering
            if isinstance(child, Role) and role_registry is not None:
                handler = role_registry.get(child.name)
                if handler is not None:
                    handler.render(child, sb)
                    continue
            # Fall through to default dispatch
            handler = dispatch.get(type(child))
            if handler:
                handler(child, sb, render_children)

    def _render_inline(self, node: Inline, sb: StringBuilder) -> None:
        """Render an inline node using dict dispatch."""
        # Check for Role nodes with registry-based rendering
        if isinstance(node, Role) and self._role_registry is not None:
            handler = self._role_registry.get(node.name)
            if handler is not None:
                handler.render(node, sb)
                return
        # Fall through to default dispatch
        handler = INLINE_DISPATCH.get(type(node))
        if handler:
            handler(node, sb, self._render_inline_children)

    def iter_blocks(self, nodes: Sequence[Block]) -> Iterator[str]:
        """Iterate over rendered blocks.

        Yields HTML for each block node. Useful for streaming.

        Args:
            nodes: Sequence of Block AST nodes

        Yields:
            HTML string for each block
        """

        for node in nodes:
            sb = StringBuilder()
            self._render_block(node, sb)
            yield sb.build()

    # =========================================================================
    # Single-Pass Heading Decoration
    # =========================================================================

    def _extract_plain_text(self, children: Sequence[Inline]) -> str:
        """Extract plain text from inline nodes.

        Recursively extracts text content without HTML tags.
        Used for slug generation and TOC text.

        Args:
            children: Sequence of inline nodes

        Returns:
            Concatenated plain text
        """
        parts: list[str] = []
        for child in children:
            if isinstance(child, Text):
                content = child.content
                # Apply text transformer if present (e.g., variable substitution)
                if self._text_transformer:
                    content = self._text_transformer(content)
                parts.append(content)
            elif isinstance(child, CodeSpan):
                parts.append(child.code)
            elif isinstance(child, (Emphasis, Strong, Strikethrough, Link)):
                parts.append(self._extract_plain_text(child.children))
            elif isinstance(child, Math):
                parts.append(child.content)
            # Skip: Image, LineBreak, SoftBreak, HtmlInline, Role, FootnoteRef
        return "".join(parts)

    def _get_unique_slug(self, text: str) -> str:
        """Generate a unique slug for a heading.

        Handles duplicate headings by appending -1, -2, etc.

        Args:
            text: Heading text to slugify

        Returns:
            Unique slug string
        """
        base_slug = self._heading_slugify(text)
        if not base_slug:
            base_slug = "heading"

        # Check for duplicates
        if base_slug not in self._seen_slugs:
            self._seen_slugs[base_slug] = 0
            return base_slug

        # Increment counter and append suffix
        self._seen_slugs[base_slug] += 1
        return f"{base_slug}-{self._seen_slugs[base_slug]}"

    def get_headings(self) -> list[HeadingInfo]:
        """Get headings collected during rendering.

        Call after render() to retrieve heading info for TOC generation.

        Returns:
            List of HeadingInfo with level, text, and slug
        """
        return self._headings.copy()

    def get_toc_items(self) -> list[dict[str, Any]]:
        """Get structured TOC data.

        Returns list of dicts compatible with existing TOC data format.

        Returns:
            List of {"level": int, "text": str, "slug": str} dicts
        """
        return [{"level": h.level, "text": h.text, "slug": h.slug} for h in self._headings]

    def get_toc_html(self) -> str:
        """Build TOC HTML from collected headings.

        Generates nested <ul> structure for table of contents.

        Returns:
            TOC HTML string, empty if no headings
        """
        if not self._headings:
            return ""

        result: list[str] = ['<ul class="toc">']
        prev_level = self._headings[0].level

        for heading in self._headings:
            level = heading.level

            # Handle nesting changes
            if level > prev_level:
                # Deeper: open new nested list(s)
                for _ in range(level - prev_level):
                    result.append("<ul>")
            elif level < prev_level:
                # Shallower: close nested list(s)
                for _ in range(prev_level - level):
                    result.append("</li></ul>")
                result.append("</li>")
            elif result[-1] not in ("</ul>", '<ul class="toc">'):
                # Same level, close previous item
                result.append("</li>")

            # Add TOC item
            result.append(f'<li><a href="#{heading.slug}">{escape_html(heading.text)}</a>')
            prev_level = level

        # Close remaining tags
        result.append("</li>")
        result.append("</ul>")

        return "".join(result)
