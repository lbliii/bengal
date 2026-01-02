"""Directive parsing for Patitas parser.

Handles MyST-style directive blocks with contract validation.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from bengal.rendering.parsers.patitas.nodes import Block, Directive
from bengal.rendering.parsers.patitas.tokens import TokenType

if TYPE_CHECKING:
    from bengal.rendering.parsers.patitas.tokens import Token


class DirectiveParsingMixin:
    """Mixin for directive parsing with contract validation.

    Required Host Attributes:
        - _current: Token | None
        - _directive_registry: DirectiveRegistry | None
        - _directive_stack: list[str]
        - _strict_contracts: bool

    Required Host Methods:
        - _at_end() -> bool
        - _advance() -> Token | None
        - _parse_block() -> Block | None
    """

    _current: Token | None
    _directive_registry: object | None
    _directive_stack: list[str]
    _strict_contracts: bool

    def _parse_directive(self) -> Directive:
        """Parse directive block (:::{name} ... :::).

        Returns Directive with typed options. If a handler is registered,
        uses the handler's options_class and parse() method. Otherwise,
        creates Directive directly with default DirectiveOptions.
        """
        from bengal.rendering.parsers.patitas.directives.options import DirectiveOptions

        start_token = self._current
        assert start_token is not None and start_token.type == TokenType.DIRECTIVE_OPEN
        self._advance()

        # Get directive name
        name = ""
        if self._current and self._current.type == TokenType.DIRECTIVE_NAME:
            name = self._current.value
            self._advance()

        # Get optional title
        title: str | None = None
        if self._current and self._current.type == TokenType.DIRECTIVE_TITLE:
            title = self._current.value
            self._advance()

        # Parse raw options dict
        raw_options: dict[str, str] = {}
        while not self._at_end():
            token = self._current
            assert token is not None

            if token.type == TokenType.DIRECTIVE_OPTION:
                # Parse key:value from token
                if ":" in token.value:
                    key, value = token.value.split(":", 1)
                    raw_options[key.strip()] = value.strip()
                self._advance()
            elif token.type == TokenType.BLANK_LINE:
                # Skip blank lines in option section
                self._advance()
                break  # Options section ends at first blank line
            else:
                break

        # Get handler from registry (if available)
        handler = None
        if self._directive_registry:
            handler = self._directive_registry.get(name)

        # Validate parent contract BEFORE parsing children
        if handler and hasattr(handler, "contract") and handler.contract:
            parent_name = self._directive_stack[-1] if self._directive_stack else None
            violation = handler.contract.validate_parent(name, parent_name)
            if violation:
                from bengal.errors import DirectiveContractError
                from bengal.utils.logger import get_logger

                logger = get_logger(__name__)
                if self._strict_contracts and violation.violation_type != "suggested_parent":
                    raise DirectiveContractError(
                        violation.message,
                        location=start_token.location,
                        suggestion=violation.suggestion,
                    )
                else:
                    logger.warning(
                        "directive_contract_violation",
                        directive=name,
                        parent=parent_name,
                        violation_message=violation.message,
                    )

        # Parse options into typed object
        if handler and hasattr(handler, "options_class"):
            typed_options = handler.options_class.from_raw(raw_options)
        else:
            # No handler - use default DirectiveOptions
            typed_options = DirectiveOptions.from_raw(raw_options)

        # Check if handler needs raw content preserved
        preserves_raw_content = False
        if handler and hasattr(handler, "preserves_raw_content"):
            preserves_raw_content = handler.preserves_raw_content

        # Push onto stack before parsing children
        self._directive_stack.append(name)

        # Parse content (nested blocks)
        children: list[Block] = []
        raw_content_parts: list[str] = []
        try:
            while not self._at_end():
                token = self._current
                assert token is not None

                if token.type == TokenType.DIRECTIVE_CLOSE:
                    self._advance()
                    break
                elif token.type == TokenType.BLANK_LINE:
                    if preserves_raw_content:
                        raw_content_parts.append("\n")
                    self._advance()
                    continue

                # Capture raw content from token value before parsing
                # This preserves the original text for directives that need it
                # (e.g., gallery directive parsing markdown image syntax)
                if preserves_raw_content and token.value:
                    raw_content_parts.append(token.value)
                    raw_content_parts.append("\n")

                block = self._parse_block()
                if block is not None:
                    children.append(block)
        finally:
            # Always pop from stack, even on error
            self._directive_stack.pop()

        # Validate children contract AFTER parsing
        if handler and hasattr(handler, "contract") and handler.contract:
            child_directives = [c for c in children if isinstance(c, Directive)]
            violations = handler.contract.validate_children(name, child_directives)
            if violations:
                from bengal.errors import DirectiveContractError
                from bengal.utils.logger import get_logger

                logger = get_logger(__name__)
                for violation in violations:
                    if self._strict_contracts:
                        raise DirectiveContractError(
                            violation.message,
                            location=start_token.location,
                            suggestion=violation.suggestion,
                        )
                    else:
                        logger.warning(
                            "directive_contract_violation",
                            directive=name,
                            violation_message=violation.message,
                        )

        # Build raw_content if needed
        raw_content: str | None = None
        if preserves_raw_content:
            raw_content = "".join(raw_content_parts) if raw_content_parts else ""

        # Use handler if available, otherwise create Directive directly
        if handler and hasattr(handler, "parse"):
            # Handler returns Directive with typed options
            directive = handler.parse(
                name=name,
                title=title,
                options=typed_options,
                content=raw_content or "",
                children=children,
                location=start_token.location,
            )
            # Ensure raw_content is set if handler requested it
            if preserves_raw_content and directive.raw_content is None:
                # Reconstruct directive with raw_content
                from dataclasses import replace

                directive = replace(directive, raw_content=raw_content)
            return directive
        else:
            # No handler - create Directive directly with typed options
            return Directive(
                location=start_token.location,
                name=name,
                title=title,
                options=typed_options,
                children=tuple(children),
                raw_content=raw_content,
            )
