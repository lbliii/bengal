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

"""

from __future__ import annotations

from collections.abc import Callable, Iterator, Sequence
from dataclasses import dataclass
from html import escape as html_escape
from html import unescape as html_unescape
from typing import TYPE_CHECKING, Any, Literal

from bengal.rendering.parsers.patitas.nodes import (
    Block,
    BlockQuote,
    CodeSpan,
    Directive,
    Emphasis,
    FencedCode,
    FootnoteDef,
    FootnoteRef,
    Heading,
    HtmlBlock,
    HtmlInline,
    Image,
    IndentedCode,
    Inline,
    LineBreak,
    Link,
    List,
    ListItem,
    Math,
    MathBlock,
    Paragraph,
    Role,
    SoftBreak,
    Strikethrough,
    Strong,
    Table,
    TableRow,
    Text,
    ThematicBreak,
)
from bengal.rendering.parsers.patitas.accumulator import get_metadata
from bengal.rendering.parsers.patitas.render_config import RenderConfig, get_render_config
from bengal.rendering.parsers.patitas.stringbuilder import StringBuilder

if TYPE_CHECKING:
    from bengal.directives.cache import DirectiveCache
    from bengal.rendering.parsers.patitas.protocols import LexerDelegate


@dataclass(frozen=True, slots=True)
class HeadingInfo:
    """Heading metadata collected during rendering.

    Used to build TOC without post-render regex scanning.
    Collected by HtmlRenderer during the AST walk.

    """

    level: int
    text: str
    slug: str


class HtmlRenderer:
    """Render AST to HTML using StringBuilder pattern.

    O(n) rendering using StringBuilder for string accumulation.
    All state is local to each render() call.

    Configuration:
        Uses ContextVar pattern for thread-safe configuration.
        Highlighting, registries, and transformers are read from RenderConfig via properties.
        Set configuration using render_config_context() or set_render_config().

    Usage:
        >>> from bengal.rendering.parsers.patitas.render_config import render_config_context, RenderConfig
        >>> with render_config_context(RenderConfig(highlight=True)):
        ...     renderer = HtmlRenderer(source)
        ...     html = renderer.render(ast)
        '<h1>Hello <strong>World</strong></h1>\\n'

    Thread Safety:
        Multiple threads can render concurrently without synchronization.
        Each call creates independent StringBuilder.

    """

    __slots__ = (
        # Per-render state only (7 slots)
        "_source",
        "_delegate",
        "_headings",
        "_seen_slugs",
        "_page_context",
        "_current_page",
        "_directive_cache",
    )

    def __init__(
        self,
        source: str = "",
        *,
        delegate: LexerDelegate | None = None,
        directive_cache: DirectiveCache | None = None,
        page_context: Any | None = None,
    ) -> None:
        """Initialize renderer with source and per-render state only.

        Configuration is read from ContextVar, not passed as parameters.
        Use render_config_context() or set_render_config() to configure.

        Args:
            source: Original source buffer for zero-copy extraction
            delegate: Optional sub-lexer delegate for ZCLH handoff
            directive_cache: Optional cache for rendered directive output (per-site, not config)
            page_context: Optional page context for directives that need page/section info
        """
        self._source = source
        self._delegate = delegate
        self._headings: list[HeadingInfo] = []
        self._seen_slugs: dict[str, int] = {}  # For unique slug generation
        # Page context for directives (child-cards, breadcrumbs, etc.)
        self._page_context = page_context
        # Alias for _page_context (used by directives that look for _current_page)
        self._current_page = page_context
        # Directive cache is per-site, passed in (not config)
        self._directive_cache = directive_cache

    def _reset(
        self,
        source: str = "",
        *,
        delegate: LexerDelegate | None = None,
        directive_cache: DirectiveCache | None = None,
        page_context: Any | None = None,
    ) -> None:
        """Reset renderer state for reuse.

        Clears per-render state while preserving object identity.
        Used by RendererPool.acquire() for instance pooling.

        Args:
            source: Original source buffer for zero-copy extraction
            delegate: Optional sub-lexer delegate for ZCLH handoff
            directive_cache: Optional cache for rendered directive output
            page_context: Optional page context for directives
        """
        self._source = source
        self._delegate = delegate
        self._headings = []
        self._seen_slugs = {}
        self._page_context = page_context
        self._current_page = page_context
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
    def _slugify(self) -> Callable[[str], str]:
        """Get slugify function for heading IDs."""
        return self._config.slugify or _default_slugify

    @property
    def _rosettes_available(self) -> bool:
        """Check if rosettes highlighter is available."""
        return self._config.rosettes_available

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

    def _render_footnotes_section(self, footnotes: list[FootnoteDef], sb: StringBuilder) -> None:
        """Render footnote definitions as a section at the end of the document."""
        sb.append('<section class="footnotes">\n<ol>\n')

        for fn in footnotes:
            identifier = _escape_attr(fn.identifier)
            sb.append(f'<li id="fn-{identifier}">')

            # Render footnote content
            if fn.children:
                for child in fn.children:
                    if isinstance(child, Paragraph):
                        # Inline the paragraph content with back-reference
                        sb.append("<p>")
                        self._render_inline_children(child.children, sb)
                        sb.append(f'<a href="#fnref-{identifier}" class="footnote">&#8617;</a>')
                        sb.append("</p>")
                    else:
                        self._render_block(child, sb)

            sb.append("</li>\n")

        sb.append("</ol>\n</section>\n")

    def _render_block(self, node: Block, sb: StringBuilder) -> None:
        """Render a block node to StringBuilder."""
        match node:
            case Heading(level=level, children=children, explicit_id=explicit_id):
                # Extract text and generate slug during AST walk
                text = self._extract_plain_text(children)

                # Use explicit ID if provided (parsed from {#custom-id} syntax)
                slug = explicit_id or self._get_unique_slug(text)

                # Collect heading info for TOC generation
                self._headings.append(HeadingInfo(level=level, text=text, slug=slug))

                # Emit heading with ID already included
                sb.append(f'<h{level} id="{slug}">')
                self._render_inline_children(children, sb)
                sb.append(f"</h{level}>\n")

            case Paragraph(children=children):
                sb.append("<p>")
                self._render_inline_children(children, sb)
                sb.append("</p>\n")

            case FencedCode() as node:
                self._render_fenced_code(node, sb)

            case IndentedCode(code=code):
                # CommonMark: code block content always ends with newline before </code>
                escaped = _escape_html(code)
                if not escaped.endswith("\n"):
                    escaped += "\n"
                sb.append(f"<pre><code>{escaped}</code></pre>\n")

            case BlockQuote(children=children):
                sb.append("<blockquote>\n")
                for child in children:
                    self._render_block(child, sb)
                sb.append("</blockquote>\n")

            case List(items=items, ordered=ordered, start=start, tight=tight):
                if ordered:
                    if start != 1:
                        sb.append(f'<ol start="{start}">\n')
                    else:
                        sb.append("<ol>\n")
                else:
                    sb.append("<ul>\n")

                for item in items:
                    self._render_list_item(item, sb, tight)

                if ordered:
                    sb.append("</ol>\n")
                else:
                    sb.append("</ul>\n")

            case ThematicBreak():
                sb.append("<hr />\n")

            case HtmlBlock(html=html):
                sb.append(html)
                if not html.endswith("\n"):
                    sb.append("\n")

            case Directive() as directive:
                self._render_directive(directive, sb)

            case Table() as table:
                self._render_table(table, sb)

            case MathBlock(content=content):
                # Accumulate metadata if context is active
                meta = get_metadata()
                if meta:
                    meta.has_math = True

                # Render as div with math-block class (for MathJax/KaTeX)
                sb.append('<div class="math-block">\n')
                sb.append(_escape_html(content))
                sb.append("\n</div>\n")

            case FootnoteDef():
                # Footnote definitions are collected and rendered at document end
                pass  # Handled in post-processing

    def _render_list_item(self, item: ListItem, sb: StringBuilder, tight: bool) -> None:
        """Render a list item.

        Tight list items unwrap paragraphs but still render block elements with newlines.
        """
        if item.checked is not None:
            # Task list item - match Mistune's class names
            sb.append('<li class="task-list-item">')
            checked_attr = " checked" if item.checked else ""
            sb.append(
                f'<input class="task-list-item-checkbox" type="checkbox" disabled{checked_attr}/>'
            )
        else:
            sb.append("<li>")
            # Empty list items should render as <li></li> without newline
            if not item.children:
                sb.append("</li>\n")
                return

            # For tight lists: add newline if item has non-paragraph block elements
            # For loose lists: always add newline
            if not tight:
                sb.append("\n")
            elif item.children and not isinstance(item.children[0], Paragraph):
                # Tight list but first child is a block element (like thematic break)
                sb.append("\n")

        if tight:
            # Tight list: render children without paragraph wrapper
            for i, child in enumerate(item.children):
                if isinstance(child, Paragraph):
                    self._render_inline_children(child.children, sb)
                    # Add newline before next block element (like nested list)
                    if i + 1 < len(item.children) and not isinstance(
                        item.children[i + 1], Paragraph
                    ):
                        sb.append("\n")
                else:
                    self._render_block(child, sb)
        else:
            # Loose list: include paragraph wrappers
            for child in item.children:
                self._render_block(child, sb)

        sb.append("</li>\n")

    def _render_table(self, table: Table, sb: StringBuilder) -> None:
        """Render a table with thead and tbody."""
        # Accumulate metadata if context is active
        meta = get_metadata()
        if meta:
            meta.has_tables = True

        # Wrap in table-wrapper for horizontal scrolling on narrow screens
        sb.append('<div class="table-wrapper"><table>\n')

        # Render header rows
        if table.head:
            sb.append("<thead>\n")
            for row in table.head:
                self._render_table_row(row, table.alignments, sb, is_header=True)
            sb.append("</thead>\n")

        # Render body rows
        if table.body:
            sb.append("<tbody>\n")
            for row in table.body:
                self._render_table_row(row, table.alignments, sb, is_header=False)
            sb.append("</tbody>\n")

        sb.append("</table></div>")

    def _render_table_row(
        self,
        row: TableRow,
        alignments: tuple[str | None, ...],
        sb: StringBuilder,
        is_header: bool,
    ) -> None:
        """Render a table row with pretty-printing (matching Mistune)."""
        sb.append("<tr>\n")
        tag = "th" if is_header else "td"

        for i, cell in enumerate(row.cells):
            align = alignments[i] if i < len(alignments) else None
            if align:
                sb.append(f'  <{tag} style="text-align: {align}">')
            else:
                sb.append(f"  <{tag}>")
            self._render_inline_children(cell.children, sb)
            sb.append(f"</{tag}>\n")

        sb.append("</tr>\n")

    # Directives that depend on page context and should NOT be cached
    # These output different content based on the current page's location in the site tree
    _PAGE_DEPENDENT_DIRECTIVES = frozenset(
        {
            "child-cards",  # Shows children of current section
            "breadcrumbs",  # Shows path to current page
            "siblings",  # Shows siblings of current page
            "prev-next",  # Shows previous/next pages
            "related",  # Shows related pages based on tags
            "auto-toc",  # Shows table of contents for current page
        }
    )

    def _render_directive(self, node: Directive, sb: StringBuilder) -> None:
        """Render a directive block.

        Uses registered handler if available, otherwise falls back to default.
        Caches rendered output for versioned sites (auto-enabled when directive_cache provided).

        Optimization: Check cache BEFORE rendering children to skip work on cache hits.

        Note: Page-dependent directives (those that need page_context or get_page_context,
        or are listed in _PAGE_DEPENDENT_DIRECTIVES) are NOT cached since their output
        varies by page. This includes child-cards, breadcrumbs, siblings, prev-next, related, etc.
        """
        import inspect

        # Determine if directive is cacheable (not page-dependent)
        is_cacheable = node.name not in self._PAGE_DEPENDENT_DIRECTIVES
        handler = None
        sig = None
        if self._directive_registry:
            handler = self._directive_registry.get(node.name)
            if handler and hasattr(handler, "render"):
                sig = inspect.signature(handler.render)
                # Page-dependent directives are NOT cacheable
                if is_cacheable and (
                    "page_context" in sig.parameters or "get_page_context" in sig.parameters
                ):
                    is_cacheable = False

        # Check directive cache FIRST (before rendering children) - only for cacheable directives
        cache_key: str | None = None
        if self._directive_cache and is_cacheable:
            # Lightweight AST-based cache key (no rendering needed)
            cache_key = self._directive_ast_cache_key(node)
            cached = self._directive_cache.get("directive_html", cache_key)
            if cached:
                sb.append(cached)
                return

        # Cache miss: now render children
        children_sb = StringBuilder()
        for child in node.children:
            self._render_block(child, children_sb)
        rendered_children = children_sb.build()

        # Render with registered handler
        result_sb = StringBuilder()
        if handler and sig:
            kwargs: dict[str, Any] = {}

            # Pass page context getter for directives that need it (child-cards, breadcrumbs, etc.)
            if "get_page_context" in sig.parameters:
                kwargs["get_page_context"] = lambda: self._page_context

            # Pass page context directly for simpler directive interfaces
            if "page_context" in sig.parameters:
                kwargs["page_context"] = self._page_context

            if "render_child_directive" in sig.parameters:
                kwargs["render_child_directive"] = self._render_block

            handler.render(node, rendered_children, result_sb, **kwargs)

            result = result_sb.build()
            if cache_key and self._directive_cache:
                self._directive_cache.put("directive_html", cache_key, result)
            sb.append(result)
            return

        # Default rendering
        result_sb.append(f'<div class="directive directive-{_escape_attr(node.name)}">')
        if node.title:
            result_sb.append(f'<p class="directive-title">{_escape_html(node.title)}</p>')
        result_sb.append(rendered_children)
        result_sb.append("</div>\n")

        result = result_sb.build()
        if cache_key and self._directive_cache:
            self._directive_cache.put("directive_html", cache_key, result)
        sb.append(result)

    def _directive_ast_cache_key(self, node: Directive) -> str:
        """Generate cache key from directive AST structure without rendering.

        Creates a lightweight hash of the directive's structure:
        - Directive name, title, options
        - Recursive structure of all child blocks

        This allows cache lookup BEFORE expensive child rendering.
        """
        parts: list[str] = [node.name, node.title or ""]

        # Options as string
        if node.options:
            parts.append(repr(node.options))

        # Recursive AST structure hash
        def hash_block(block: Block) -> str:
            """Hash a block's structure without rendering."""
            sig_parts = [type(block).__name__]

            # Add content-bearing attributes
            if hasattr(block, "content"):
                sig_parts.append(str(getattr(block, "content", "")))
            if hasattr(block, "code"):
                sig_parts.append(str(getattr(block, "code", "")))
            if hasattr(block, "info"):
                sig_parts.append(str(getattr(block, "info", "")))
            if hasattr(block, "level"):
                sig_parts.append(str(getattr(block, "level", "")))
            if hasattr(block, "url"):
                sig_parts.append(str(getattr(block, "url", "")))

            # Recurse into children
            if hasattr(block, "children"):
                children = getattr(block, "children", ())
                if children:
                    sig_parts.extend(hash_block(child) for child in children)

            return "|".join(sig_parts)

        # Hash all children
        children_sig = "".join(hash_block(child) for child in node.children)
        parts.append(str(hash(children_sig)))

        return ":".join(parts)

    def _render_fenced_code(
        self,
        node: FencedCode,
        sb: StringBuilder,
    ) -> None:
        """Render fenced code block with optional zero-copy highlighting."""
        info = node.info
        lang = info.split()[0].lower() if info else None

        # Accumulate metadata if context is active
        meta = get_metadata()
        if meta:
            meta.add_code_block(lang)

        if lang == "mermaid":
            sb.append(
                f'<div class="mermaid">{_escape_html(node.get_code(self._source))}</div>\n'
            )
            return

        # Attempt syntax highlighting via delegate (ZCLH protocol)
        if self._delegate and info:
            lang = info.split()[0].lower()
            if self._delegate.supports_language(lang):
                tokens = self._delegate.tokenize_range(
                    self._source,
                    node.source_start,
                    node.source_end,
                    lang,
                )
                self._render_highlighted_tokens(tokens, lang, sb)
                return

        # Fallback: internal highlighting or plain code
        if self._highlight and info:
            # Strip trailing newline from code range before highlighting
            end = node.source_end
            if end > node.source_start and self._source[end - 1] == "\n":
                end -= 1
            highlighted = self._try_highlight_range(node.source_start, end, info)
            if highlighted:
                # Rosettes parity: ensure trailing newline before closing tags
                if highlighted.endswith("</code></pre></div>"):
                    highlighted = highlighted[:-19] + "\n</code></pre></div>"
                sb.append(highlighted)
                return

        # Plain code block extraction
        code = node.get_code(self._source)
        # Strip trailing newline from last line (parity with IndentedCode)
        if code.endswith("\n"):
            code = code[:-1]
        sb.append("<pre><code")
        if info:
            # CommonMark: decode HTML entities in info string before using as class
            lang = html_unescape(info.split()[0])
            if lang:
                sb.append(f' class="language-{_escape_attr(lang)}"')
        sb.append(">")
        sb.append(_escape_html(code))
        # CommonMark: empty code blocks have no trailing newline
        if code:
            sb.append("\n</code></pre>\n")
        else:
            sb.append("</code></pre>\n")

    def _render_highlighted_tokens(
        self,
        tokens: Any,
        language: str,
        sb: StringBuilder,
    ) -> None:
        """Render tokens from a sub-lexer delegate."""
        # This assumes tokens are compatible with rosettes format
        # but we wrap them in standard containers for safety.
        sb.append(f'<div class="highlight {self._highlight_style}"><pre>')
        sb.append(f'<code class="language-{_escape_attr(language)}">')

        # Basic token rendering if not already stringified
        for token in tokens:
            if hasattr(token, "html"):
                sb.append(token.html)
            elif hasattr(token, "value"):
                # Handle basic token objects (type, value)
                cls = f' class="token {getattr(token, "type", "text")}"'
                sb.append(f"<span{cls}>{_escape_html(token.value)}</span>")
            else:
                sb.append(_escape_html(str(token)))

        sb.append("\n</code></pre></div>\n")

    def _try_highlight_range(self, start: int, end: int, info: str) -> str | None:
        """Try to highlight a source range using internal rosettes.

        Uses rosettes_available from RenderConfig (computed once at module import).
        """
        if not self._rosettes_available:
            return None

        lang = info.split()[0] if info else ""
        if not lang:
            return None

        try:
            from rosettes import highlight

            return highlight(
                self._source,
                lang,
                css_class_style=self._highlight_style,
                start=start,
                end=end,
            )
        except (LookupError, ValueError):
            return None

    def _render_inline_children(self, children: Sequence[Inline], sb: StringBuilder) -> None:
        """Render inline children using dict dispatch for speed."""
        # Local references for tight loop
        dispatch = _INLINE_DISPATCH
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
        handler = _INLINE_DISPATCH.get(type(node))
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
        base_slug = self._slugify(text)
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
            result.append(f'<li><a href="#{heading.slug}">{_escape_html(heading.text)}</a>')
            prev_level = level

        # Close remaining tags
        result.append("</li>")
        result.append("</ul>")

        return "".join(result)


def _escape_html(text: str) -> str:
    """Escape HTML special characters for text content.
    
    Per CommonMark spec:
    - < > & must be escaped (XSS prevention)
    - " should be escaped to &quot; (for safety)
    - ' should remain literal in text content (not &#x27;)
    
    Also strips internal  markers used for lazy continuation escaping.
        
    """
    # Strip internal \x00 markers (used to prevent block element detection in lazy continuation)
    text = text.replace("\x00", "")
    # html_escape with quote=True escapes both " and '
    # We only want to escape " but not '
    result = html_escape(text, quote=False)  # Escapes < > &
    result = result.replace('"', "&quot;")  # Also escape "
    return result


def _escape_attr(text: str) -> str:
    """Escape HTML attribute value."""
    return html_escape(text, quote=True)


def _encode_url(url: str) -> str:
    """Encode URL for use in href attribute per CommonMark spec.
    
    CommonMark requires:
    1. Percent-encoding of special characters in URLs (space, backslash, etc.)
    2. HTML escaping of characters that are special in HTML (& → &amp;)
    
    The final output goes in an HTML attribute, so we need both:
    - URL percent-encoding for URL-special characters
    - HTML escaping for HTML-special characters (&, <, >, ", ')
        
    """
    import html
    from urllib.parse import quote

    # First, decode any HTML entities (e.g., &auml; → ä)
    decoded = html.unescape(url)

    # Preserve already-valid percent sequences
    # Split on existing %XX patterns and encode each part
    result = []
    i = 0
    while i < len(decoded):
        # Check for existing percent encoding
        if decoded[i] == "%" and i + 2 < len(decoded):
            hex_chars = decoded[i + 1 : i + 3]
            if all(c in "0123456789ABCDEFabcdef" for c in hex_chars):
                # Valid percent sequence - preserve it
                result.append(decoded[i : i + 3])
                i += 3
                continue

        char = decoded[i]

        # Characters safe in URLs (RFC 3986 unreserved + sub-delims + : / ? # @ = &)
        # CommonMark allows more lax URLs so we preserve more chars
        if (
            char
            in "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-._~:/?#[]@!$&'()*+,;="
        ):
            result.append(char)
        else:
            # Percent-encode this character
            encoded = quote(char, safe="")
            result.append(encoded)

        i += 1

    # Now HTML-escape the result for use in an attribute
    # This converts & → &amp;, etc.
    url_encoded = "".join(result)
    return html_escape(url_encoded, quote=True)


def _escape_link_title(title: str) -> str:
    """Escape link title for use in title attribute per CommonMark spec.
    
    Titles use HTML escaping but must also decode HTML entities first.
    E.g., &quot; in source becomes " which then becomes &quot; in output.
        
    """
    import html

    # Decode entities first, then HTML-escape
    decoded = html.unescape(title)
    return html_escape(decoded, quote=True)


def _default_slugify(text: str) -> str:
    """Default slugify function for heading IDs.
    
    Uses bengal.utils.text.slugify with HTML unescaping enabled.
        
    """
    from bengal.utils.text import slugify

    return slugify(text, unescape_html=True, max_length=100)


# =============================================================================
# Inline dispatch handlers (dict dispatch is ~2x faster than match statement)
# =============================================================================


def _render_text(node: Text, sb: StringBuilder, render_children) -> None:
    # Use text_transformer if provided (e.g., for variable substitution)
    # This happens BEFORE HTML escaping to allow variables to contain HTML (e.g. icons)
    # but the renderer will then escape the result for safety.
    # Note: VariableSubstitutionPlugin handles its own safety checks.
    content = node.content
    renderer = getattr(render_children, "__self__", None)
    if renderer and hasattr(renderer, "_text_transformer") and renderer._text_transformer:
        content = renderer._text_transformer(content)

    # Accumulate word count if metadata context is active
    meta = get_metadata()
    if meta:
        meta.add_words(content)

    sb.append(_escape_html(content))


def _render_emphasis(node: Emphasis, sb: StringBuilder, render_children) -> None:
    sb.append("<em>")
    render_children(node.children, sb)
    sb.append("</em>")


def _render_strong(node: Strong, sb: StringBuilder, render_children) -> None:
    sb.append("<strong>")
    render_children(node.children, sb)
    sb.append("</strong>")


def _render_link(node: Link, sb: StringBuilder, render_children) -> None:
    # Accumulate link metadata if context is active
    meta = get_metadata()
    if meta:
        if node.url.startswith(("http://", "https://")):
            meta.add_external_link(node.url)
        else:
            meta.add_internal_link(node.url)

    sb.append(f'<a href="{_encode_url(node.url)}"')
    if node.title:
        sb.append(f' title="{_escape_link_title(node.title)}"')
    sb.append(">")
    render_children(node.children, sb)
    sb.append("</a>")


def _render_image(node: Image, sb: StringBuilder, render_children) -> None:
    # Accumulate image metadata if context is active
    meta = get_metadata()
    if meta:
        meta.add_image(node.url)

    sb.append(f'<img src="{_encode_url(node.url)}" alt="{_escape_attr(node.alt)}"')
    if node.title:
        sb.append(f' title="{_escape_link_title(node.title)}"')
    sb.append(" />")


def _render_code_span(node: CodeSpan, sb: StringBuilder, render_children) -> None:
    sb.append(f"<code>{_escape_html(node.code)}</code>")


def _render_line_break(node: LineBreak, sb: StringBuilder, render_children) -> None:
    sb.append("<br />\n")


def _render_soft_break(node: SoftBreak, sb: StringBuilder, render_children) -> None:
    sb.append("\n")


def _render_html_inline(node: HtmlInline, sb: StringBuilder, render_children) -> None:
    sb.append(node.html)


def _render_role(node: Role, sb: StringBuilder, render_children) -> None:
    # Default role rendering - can be overridden by registry
    sb.append(
        f'<span class="role role-{_escape_attr(node.name)}">{_escape_html(node.content)}</span>'
    )


# =============================================================================
# Plugin inline dispatch handlers
# =============================================================================


def _render_strikethrough(node: Strikethrough, sb: StringBuilder, render_children) -> None:
    sb.append("<del>")
    render_children(node.children, sb)
    sb.append("</del>")


def _render_math(node: Math, sb: StringBuilder, render_children) -> None:
    # Accumulate math metadata if context is active
    meta = get_metadata()
    if meta:
        meta.has_math = True

    # Inline math - rendered with span.math class for MathJax/KaTeX
    sb.append(f'<span class="math">{_escape_html(node.content)}</span>')


def _render_footnote_ref(node: FootnoteRef, sb: StringBuilder, render_children) -> None:
    # Footnote reference - links to footnote definition (Mistune-compatible output)
    identifier = _escape_attr(node.identifier)
    sb.append(
        f'<sup class="footnote-ref" id="fnref-{identifier}">'
        f'<a href="#fn-{identifier}">{_escape_html(node.identifier)}</a></sup>'
    )


# Type -> handler dispatch table (O(1) lookup, faster than match)
_INLINE_DISPATCH = {
    Text: _render_text,
    Emphasis: _render_emphasis,
    Strong: _render_strong,
    Link: _render_link,
    Image: _render_image,
    CodeSpan: _render_code_span,
    LineBreak: _render_line_break,
    SoftBreak: _render_soft_break,
    HtmlInline: _render_html_inline,
    Role: _render_role,
    # Plugin nodes
    Strikethrough: _render_strikethrough,
    Math: _render_math,
    FootnoteRef: _render_footnote_ref,
}
