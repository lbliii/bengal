"""Recursive descent parser producing typed AST.

Consumes token stream from Lexer and builds typed AST nodes.
Produces immutable (frozen) dataclass nodes for thread-safety.

Architecture:
The parser uses a mixin-based design for separation of concerns:
- `TokenNavigationMixin`: Token stream traversal
- `InlineParsingMixin`: Inline content (emphasis, links, code spans)
- `BlockParsingMixin`: Block-level content (paragraphs, lists, tables)

Thread Safety:
Parser produces immutable AST (frozen dataclasses).
Safe to share AST across threads.

Configuration:
Uses ContextVar pattern for configuration (RFC: rfc-contextvar-config-implementation).
Configuration is read from thread-local ContextVar, not stored in slots.
This enables 50% slot reduction (18→9) and ~2x instantiation speedup.

"""

from __future__ import annotations

from collections.abc import Sequence

from bengal.rendering.parsers.patitas.config import ParseConfig, get_parse_config
from bengal.rendering.parsers.patitas.lexer import Lexer
from bengal.rendering.parsers.patitas.nodes import Block, FencedCode
from bengal.rendering.parsers.patitas.parsing import (
    BlockParsingMixin,
    InlineParsingMixin,
    TokenNavigationMixin,
)
from bengal.rendering.parsers.patitas.parsing.containers import ContainerStack
from bengal.rendering.parsers.patitas.parsing.inline.links import _normalize_label, _process_escapes
from bengal.rendering.parsers.patitas.tokens import Token, TokenType


class Parser(
    TokenNavigationMixin,
    InlineParsingMixin,
    BlockParsingMixin,
):
    """Recursive descent parser for Markdown.

    Consumes tokens from Lexer and builds typed AST.

    Architecture:
        Uses mixin inheritance to separate concerns while maintaining
        a single entry point. Each mixin handles one aspect of the grammar:

        - `TokenNavigationMixin`: Token stream access, advance, peek
        - `InlineParsingMixin`: Emphasis, links, code spans, etc.
        - `BlockParsingMixin`: Lists, tables, code blocks, directives, etc.

    Configuration:
        Uses ContextVar pattern for thread-safe configuration.
        Plugin flags and registries are read from ParseConfig via properties.
        Set configuration using parse_config_context() or set_parse_config().

    Usage:
        >>> from bengal.rendering.parsers.patitas.config import parse_config_context, ParseConfig
        >>> with parse_config_context(ParseConfig(tables_enabled=True)):
        ...     parser = Parser("# Hello\\n\\nWorld")
        ...     ast = parser.parse()
        >>> ast[0]
        Heading(level=1, children=(Text(content='Hello'),), ...)

    Thread Safety:
        Parser instances are single-use and not thread-safe. Create one per
        parse operation. The resulting AST is immutable and thread-safe.

    """

    __slots__ = (
        # Per-parse state only (9 slots)
        "_source",
        "_tokens",
        "_pos",
        "_current",
        "_source_file",
        "_directive_stack",
        "_link_refs",
        "_containers",
        "_allow_setext_headings",
    )

    def __init__(
        self,
        source: str,
        source_file: str | None = None,
    ) -> None:
        """Initialize parser with source text only.

        Configuration is read from ContextVar, not passed as parameters.
        Use parse_config_context() or set_parse_config() to configure.

        Args:
            source: Markdown source text
            source_file: Optional source file path for error messages
        """
        self._source = source
        self._source_file = source_file
        self._tokens: list[Token] = []
        self._pos = 0
        self._current: Token | None = None

        # Link reference definitions: label (lowercase) -> (url, title)
        self._link_refs: dict[str, tuple[str, str]] = {}

        # Directive support - stack is per-parse state
        self._directive_stack: list[str] = []

        # Container stack for tracking nesting context (Phase 2)
        # Initialized to document-level frame by default
        self._containers = ContainerStack()

        # Setext heading control - can be disabled for blockquote lazy continuation
        self._allow_setext_headings = True

    def _reinit(self, source: str, source_file: str | None = None) -> None:
        """Reset parser for reuse with new source.

        Avoids full __init__ overhead by reusing existing object.
        Lexer is re-created (lightweight) to tokenize new source.

        Used by ParserPool.acquire() for instance pooling.

        Args:
            source: New markdown source text
            source_file: Optional source file path for error messages
        """
        self._source = source
        self._source_file = source_file

        # Re-tokenize with new source (Lexer is lightweight)
        lexer = Lexer(self._source, self._source_file, text_transformer=self._text_transformer)
        self._tokens = list(lexer.tokenize())
        self._pos = 0
        self._current = self._tokens[0] if self._tokens else None

        # Reset per-parse state
        self._link_refs = {}
        self._containers = ContainerStack()
        self._directive_stack = []
        self._allow_setext_headings = True

    # =========================================================================
    # Config access via properties (read from ContextVar)
    # =========================================================================

    @property
    def _config(self) -> ParseConfig:
        """Get current parse configuration from ContextVar."""
        return get_parse_config()

    @property
    def _tables_enabled(self) -> bool:
        """Check if GFM table parsing is enabled."""
        return self._config.tables_enabled

    @property
    def _strikethrough_enabled(self) -> bool:
        """Check if ~~strikethrough~~ syntax is enabled."""
        return self._config.strikethrough_enabled

    @property
    def _task_lists_enabled(self) -> bool:
        """Check if [x] task list items are enabled."""
        return self._config.task_lists_enabled

    @property
    def _footnotes_enabled(self) -> bool:
        """Check if [^footnote] syntax is enabled."""
        return self._config.footnotes_enabled

    @property
    def _math_enabled(self) -> bool:
        """Check if $math$ and $$math$$ syntax is enabled."""
        return self._config.math_enabled

    @property
    def _autolinks_enabled(self) -> bool:
        """Check if URL/email autolink detection is enabled."""
        return self._config.autolinks_enabled

    @property
    def _directive_registry(self):
        """Get directive registry for handler lookup."""
        return self._config.directive_registry

    @property
    def _strict_contracts(self) -> bool:
        """Check if strict contract validation is enabled."""
        return self._config.strict_contracts

    @property
    def _text_transformer(self):
        """Get optional text transformer callback."""
        return self._config.text_transformer

    def parse(self) -> Sequence[Block]:
        """Parse source into AST blocks.

        Returns:
            Sequence of Block nodes

        Thread Safety:
            Returns immutable AST (frozen dataclasses).
        """
        # Tokenize source
        lexer = Lexer(self._source, self._source_file, text_transformer=self._text_transformer)
        self._tokens = list(lexer.tokenize())
        self._pos = 0
        self._current = self._tokens[0] if self._tokens else None

        # First pass: collect link reference definitions
        # These are needed before inline parsing to resolve [text][ref] patterns
        # Note: CommonMark 6.1 says link reference definitions cannot interrupt paragraphs.
        in_paragraph = False

        for token in self._tokens:
            if token.type == TokenType.LINK_REFERENCE_DEF:
                if not in_paragraph:
                    # Value format: label|url|title
                    parts = token.value.split("|", 2)
                    if len(parts) >= 2:
                        raw_label = parts[0]
                        # Skip labels containing unescaped '[' (e.g., ref[])
                        if "[" in raw_label.replace("\\[", ""):
                            continue
                        label = _normalize_label(raw_label)
                        # CommonMark 6.1: "If there are several link reference definitions
                        # with the same case-insensitive label, the first one is used."
                        if label not in self._link_refs:
                            # Process backslash escapes in URL and title (CommonMark 6.1)
                            url = _process_escapes(parts[1])
                            title = _process_escapes(parts[2]) if len(parts) > 2 else ""
                            self._link_refs[label] = (url, title)
                # Link ref defs themselves terminate any preceding paragraph
                in_paragraph = False
            elif token.type in (TokenType.PARAGRAPH_LINE, TokenType.INDENTED_CODE):
                # Both PARAGRAPH_LINE and INDENTED_CODE can be part of a paragraph
                in_paragraph = True
            elif token.type == TokenType.BLANK_LINE:
                in_paragraph = False
            elif token.type in (
                TokenType.ATX_HEADING,
                TokenType.THEMATIC_BREAK,
                TokenType.FENCED_CODE_START,
                TokenType.BLOCK_QUOTE_MARKER,
                TokenType.LIST_ITEM_MARKER,
                TokenType.HTML_BLOCK,
                TokenType.DIRECTIVE_OPEN,
                TokenType.FOOTNOTE_DEF,
            ):
                # Most block-level elements terminate a paragraph
                in_paragraph = False

        # Parse blocks
        blocks: list[Block] = []
        while not self._at_end():
            block = self._parse_block()
            if block is not None:
                blocks.append(block)

        return tuple(blocks)

    def _parse_nested_content(
        self,
        content: str,
        location,
        *,
        allow_setext_headings: bool = True,
    ) -> tuple[Block, ...]:
        """Parse nested content as blocks (for block quotes, list items).

        Creates a sub-parser to handle nested block-level content.
        Plugin settings are inherited via ContextVar (no manual copying needed).
        Link reference definitions are shared via explicit assignment.

        Args:
            content: The markdown content to parse as blocks
            location: Source location for error reporting
            allow_setext_headings: If False, disable setext heading detection
                (used for blockquote content with lazy continuation lines)

        Returns:
            Tuple of Block nodes
        """
        if not content.strip():
            return ()

        # Create sub-parser - config is inherited via ContextVar automatically
        sub_parser = Parser(content, self._source_file)

        # Setext heading control (per-parse state, not config)
        sub_parser._allow_setext_headings = allow_setext_headings

        # Share link reference definitions (they're document-wide)
        sub_parser._link_refs = self._link_refs

        blocks = sub_parser.parse()

        # Fix up FencedCode nodes: their source_start/source_end are relative
        # to `content`, not the original source. Add content_override so
        # get_code() returns the correct content.
        fixed_blocks = []
        for block in blocks:
            if isinstance(block, FencedCode) and block.content_override is None:
                # Extract code from sub-parser's source (content)
                code = block.get_code(content)
                fixed_block = FencedCode(
                    location=block.location,
                    source_start=block.source_start,
                    source_end=block.source_end,
                    info=block.info,
                    marker=block.marker,
                    fence_indent=block.fence_indent,
                    content_override=code,
                )
                fixed_blocks.append(fixed_block)
            else:
                fixed_blocks.append(block)

        return tuple(fixed_blocks)
