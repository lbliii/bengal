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
"""

from __future__ import annotations

from collections.abc import Callable, Sequence

from bengal.rendering.parsers.patitas.lexer import Lexer
from bengal.rendering.parsers.patitas.nodes import Block
from bengal.rendering.parsers.patitas.parsing import (
    BlockParsingMixin,
    InlineParsingMixin,
    TokenNavigationMixin,
)
from bengal.rendering.parsers.patitas.parsing.containers import ContainerStack
from bengal.rendering.parsers.patitas.parsing.inline.links import _process_escapes
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

    Usage:
        >>> parser = Parser("# Hello\\n\\nWorld")
        >>> ast = parser.parse()
        >>> ast[0]
        Heading(level=1, children=(Text(content='Hello'),), ...)

    Thread Safety:
        Parser instances are single-use and not thread-safe. Create one per
        parse operation. The resulting AST is immutable and thread-safe.
    """

    __slots__ = (
        "_source",
        "_tokens",
        "_pos",
        "_current",
        "_source_file",
        # Transformation
        "_text_transformer",
        # Plugin flags - set by Markdown class
        "_tables_enabled",
        "_strikethrough_enabled",
        "_task_lists_enabled",
        "_footnotes_enabled",
        "_math_enabled",
        "_autolinks_enabled",
        # Directive support
        "_directive_registry",
        "_directive_stack",
        "_strict_contracts",
        # Link reference definitions
        "_link_refs",
        # Container stack for tracking nesting context (Phase 2)
        "_containers",
    )

    def __init__(
        self,
        source: str,
        source_file: str | None = None,
        *,
        directive_registry=None,
        strict_contracts: bool = False,
        text_transformer: Callable[[str], str] | None = None,
    ) -> None:
        """Initialize parser with source text.

        Args:
            source: Markdown source text
            source_file: Optional source file path for error messages
            directive_registry: Optional directive registry for handler lookup
            strict_contracts: If True, raise errors on contract violations
            text_transformer: Optional callback to transform plain text lines
        """
        self._source = source
        self._source_file = source_file
        self._tokens: list[Token] = []
        self._pos = 0
        self._current: Token | None = None
        self._text_transformer = text_transformer

        # Plugin flags - default to disabled, set by Markdown class
        self._tables_enabled = False
        self._strikethrough_enabled = False
        self._task_lists_enabled = False
        self._footnotes_enabled = False
        self._math_enabled = False
        self._autolinks_enabled = False

        # Link reference definitions: label (lowercase) -> (url, title)
        self._link_refs: dict[str, tuple[str, str]] = {}

        # Directive support
        self._directive_registry = directive_registry
        self._directive_stack: list[str] = []
        self._strict_contracts = strict_contracts

        # Container stack for tracking nesting context (Phase 2)
        # Initialized to document-level frame by default
        self._containers = ContainerStack()

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
                        label = parts[
                            0
                        ].casefold()  # Labels are case-insensitive (Unicode casefold)
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

    def _parse_nested_content(self, content: str, location) -> tuple[Block, ...]:
        """Parse nested content as blocks (for block quotes, list items).

        Creates a sub-parser to handle nested block-level content while
        preserving plugin settings and link reference definitions.

        Args:
            content: The markdown content to parse as blocks
            location: Source location for error reporting

        Returns:
            Tuple of Block nodes
        """
        if not content.strip():
            return ()

        # Create sub-parser with same settings
        sub_parser = Parser(
            content,
            self._source_file,
            directive_registry=self._directive_registry,
            strict_contracts=self._strict_contracts,
            text_transformer=self._text_transformer,
        )

        # Copy plugin settings
        sub_parser._tables_enabled = self._tables_enabled
        sub_parser._strikethrough_enabled = self._strikethrough_enabled
        sub_parser._task_lists_enabled = self._task_lists_enabled
        sub_parser._footnotes_enabled = self._footnotes_enabled
        sub_parser._math_enabled = self._math_enabled
        sub_parser._autolinks_enabled = self._autolinks_enabled

        # Share link reference definitions (they're document-wide)
        sub_parser._link_refs = self._link_refs

        return tuple(sub_parser.parse())
