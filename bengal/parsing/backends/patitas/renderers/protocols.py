"""Protocols for patitas renderer mixins.

Defines protocols that mixin classes can depend on, avoiding circular imports
between blocks/directives and html modules.

Thread-safe: Protocols are type-only constructs, no runtime overhead.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Protocol

from patitas.nodes import Block, Inline
from patitas.stringbuilder import StringBuilder

if TYPE_CHECKING:
    from bengal.cache.directive_cache import DirectiveCache
    from bengal.parsing.backends.patitas.protocols import LexerDelegate
    from bengal.parsing.backends.patitas.renderers.utils import HeadingInfo


class HtmlRendererProtocol(Protocol):
    """Protocol for HtmlRenderer, used by block/directive mixins.

    Defines the interface that mixin methods expect when using `self: HtmlRendererProtocol`.
    This breaks the circular import between html.py and the mixin modules.
    """

    # Source document
    _source: str

    # Heading tracking for TOC
    _headings: list[HeadingInfo]
    _seen_slugs: dict[str, int]

    # Configuration (read from ContextVar at render time)
    @property
    def _highlight(self) -> bool: ...

    @property
    def _highlight_style(self) -> str: ...

    @property
    def _rosettes_available(self) -> bool: ...

    @property
    def _delegate(self) -> LexerDelegate | None: ...

    @property
    def _directive_registry(self) -> Any | None: ...

    @property
    def _directive_cache(self) -> DirectiveCache | None: ...

    # Methods that mixins call
    def _heading_slugify(self, text: str) -> str: ...

    def _get_unique_slug(self, base: str) -> str: ...

    def _render_inline_children(
        self, children: list[Inline] | tuple[Inline, ...], sb: StringBuilder
    ) -> None: ...

    def _render_directive(self, node: Any, sb: StringBuilder) -> None: ...

    def _render_block(self, node: Block, sb: StringBuilder) -> None: ...

    def _extract_plain_text(self, children: list[Inline]) -> str: ...

    # Methods used by BlockRendererMixin
    def _render_fenced_code(self, node: Any, sb: StringBuilder) -> None: ...

    def _render_list_item(self, item: Any, sb: StringBuilder, tight: bool) -> None: ...

    def _render_table(self, table: Any, sb: StringBuilder) -> None: ...

    def _render_table_row(
        self, row: Any, alignments: tuple[str | None, ...], sb: StringBuilder, *, is_header: bool
    ) -> None: ...

    def _render_highlighted_tokens(self, tokens: Any, language: str, sb: StringBuilder) -> None: ...

    def _try_highlight_range(self, start: int, end: int, info: str) -> str | None: ...
