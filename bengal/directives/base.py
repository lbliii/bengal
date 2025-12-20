"""
Base class for Bengal directives.

Provides BengalDirective as the foundation for all directive implementations,
offering automatic registration, typed options, contract validation, and
encapsulated rendering.

Architecture:
    BengalDirective extends mistune's DirectivePlugin with:
    - Automatic directive and renderer registration via NAMES/TOKEN_TYPE
    - Typed option parsing via OPTIONS_CLASS
    - Nesting validation via CONTRACT
    - Template method pattern for parse flow
    - Encapsulated render method

Related:
    - bengal/directives/tokens.py: DirectiveToken
    - bengal/directives/options.py: DirectiveOptions
    - bengal/directives/contracts.py: DirectiveContract
"""

from __future__ import annotations

from abc import abstractmethod
from re import Match
from typing import Any, ClassVar

from mistune.directives import DirectivePlugin

from bengal.utils.logger import get_logger

# Re-export commonly used items for convenience
from .contracts import (  # noqa: F401
    CARD_CONTRACT,
    CARDS_CONTRACT,
    CODE_TABS_CONTRACT,
    STEP_CONTRACT,
    STEPS_CONTRACT,
    TAB_ITEM_CONTRACT,
    TAB_SET_CONTRACT,
    ContractValidator,
    ContractViolation,
    DirectiveContract,
)
from .errors import DirectiveError, format_directive_error  # noqa: F401
from .options import ContainerOptions, DirectiveOptions, StyledOptions, TitledOptions  # noqa: F401
from .tokens import DirectiveToken
from .utils import (  # noqa: F401
    attr_str,
    bool_attr,
    build_class_string,
    class_attr,
    data_attrs,
    escape_html,
)


class BengalDirective(DirectivePlugin):
    """
    Base class for Bengal directives with nesting validation.

    Provides:
    - Automatic directive and renderer registration
    - Typed option parsing via OPTIONS_CLASS
    - Contract validation for parent-child relationships
    - Shared utility methods (escape_html, build_class_string)
    - Consistent type hints and logging

    Subclass Requirements:
        NAMES: List of directive names to register (e.g., ["dropdown", "details"])
        TOKEN_TYPE: Token type string for AST (e.g., "dropdown")
        OPTIONS_CLASS: (optional) Typed options dataclass
        CONTRACT: (optional) Nesting validation contract
        parse_directive(): Build token from parsed components
        render(): Render token to HTML

    Example:
        class DropdownDirective(BengalDirective):
            NAMES = ["dropdown", "details"]
            TOKEN_TYPE = "dropdown"
            OPTIONS_CLASS = DropdownOptions

            def parse_directive(self, title, options, content, children, state):
                return DirectiveToken(
                    type=self.TOKEN_TYPE,
                    attrs={"title": title or "Details", "open": options.open},
                    children=children,
                )

            def render(self, renderer, text, **attrs):
                title = attrs.get("title", "Details")
                is_open = attrs.get("open", False)
                open_attr = " open" if is_open else ""
                return f"<details{open_attr}><summary>{title}</summary>{text}</details>"

    Example with Contract:
        class StepDirective(BengalDirective):
            NAMES = ["step"]
            TOKEN_TYPE = "step"
            CONTRACT = DirectiveContract(requires_parent=("steps",))

            def parse_directive(self, ...): ...
            def render(self, ...): ...
    """

    # -------------------------------------------------------------------------
    # Class Attributes (override in subclass)
    # -------------------------------------------------------------------------

    # Directive names to register (e.g., ["dropdown", "details"])
    NAMES: ClassVar[list[str]]

    # Token type for AST (e.g., "dropdown")
    TOKEN_TYPE: ClassVar[str]

    # Typed options class (defaults to base DirectiveOptions)
    OPTIONS_CLASS: ClassVar[type[DirectiveOptions]] = DirectiveOptions

    # Contract for nesting validation (optional)
    CONTRACT: ClassVar[DirectiveContract | None] = None

    # -------------------------------------------------------------------------
    # Initialization
    # -------------------------------------------------------------------------

    def __init__(self) -> None:
        """Initialize directive with logger."""
        super().__init__()
        self.logger = get_logger(self.__class__.__module__)

    # -------------------------------------------------------------------------
    # Parse Flow with Contract Validation
    # -------------------------------------------------------------------------

    def parse(self, block: Any, m: Match[str], state: Any) -> dict[str, Any]:
        """
        Standard parse flow with contract validation.

        Validation steps:
        1. Validate parent context (if CONTRACT.requires_parent)
        2. Parse content and children
        3. Validate children (if CONTRACT.requires_children)

        Override parse_directive() instead of this method for most cases.
        Override this method only if you need custom pre/post processing.

        Args:
            block: Mistune block parser instance
            m: Regex match object from directive pattern
            state: Parser state

        Returns:
            Token dict for mistune AST
        """
        # Get source location for error messages
        location = self._get_source_location(state)

        # STEP 1: Validate parent context BEFORE parsing
        # Only validate if we know the source file (skip examples/secondary parsing)
        if self.CONTRACT and self.CONTRACT.has_parent_requirement and location:
            parent_type = self._get_parent_directive_type(state)
            violations = ContractValidator.validate_parent(
                self.CONTRACT, self.TOKEN_TYPE, parent_type, location
            )
            for v in violations:
                self.logger.warning(v.violation_type, **v.to_log_dict())

        # STEP 2: Parse content
        title = self.parse_title(m)
        raw_options = dict(self.parse_options(m))
        content = self.parse_content(m)

        # Push current directive onto stack for child validation
        self._push_directive_stack(state, self.TOKEN_TYPE)

        try:
            children = self.parse_tokens(block, content, state)
        finally:
            # Always pop, even on error
            self._pop_directive_stack(state)

        # Parse options into typed instance
        options = self.OPTIONS_CLASS.from_raw(raw_options)

        # STEP 3: Validate children AFTER parsing
        if self.CONTRACT and self.CONTRACT.has_child_requirement:
            # Convert children to list of dicts for validation
            child_dicts = [c if isinstance(c, dict) else {"type": "unknown"} for c in children]
            violations = ContractValidator.validate_children(
                self.CONTRACT, self.TOKEN_TYPE, child_dicts, location
            )
            for v in violations:
                self.logger.warning(v.violation_type, **v.to_log_dict())

        # Build token via subclass
        token = self.parse_directive(title, options, content, children, state)

        # Return dict for mistune compatibility
        if isinstance(token, DirectiveToken):
            return token.to_dict()
        return token

    def _get_parent_directive_type(self, state: Any) -> str | None:
        """
        Extract parent directive type from parser state.

        Mistune tracks directive nesting in state. This method extracts
        the immediate parent directive type for contract validation.

        Args:
            state: Parser state

        Returns:
            Parent directive type (e.g., "steps") or None if at root
        """
        # Check for Bengal's directive stack in state
        directive_stack = getattr(state, "_directive_stack", None)
        if directive_stack and len(directive_stack) > 0:
            return str(directive_stack[-1])

        # Fallback: check state.env for parent tracking
        env = getattr(state, "env", {})
        if isinstance(env, dict):
            stack = env.get("directive_stack", [])
            if stack:
                return str(stack[-1])

        return None

    def _push_directive_stack(self, state: Any, directive_type: str) -> None:
        """
        Push current directive onto the stack for child validation.

        Args:
            state: Parser state
            directive_type: Current directive type
        """
        env = getattr(state, "env", None)
        if env is None:
            # Create env dict if it doesn't exist
            try:
                state.env = {}
                env = state.env
            except AttributeError:
                return

        if isinstance(env, dict):
            if "directive_stack" not in env:
                env["directive_stack"] = []
            env["directive_stack"].append(directive_type)

    def _pop_directive_stack(self, state: Any) -> None:
        """
        Pop current directive from the stack.

        Args:
            state: Parser state
        """
        env = getattr(state, "env", {})
        if isinstance(env, dict):
            stack = env.get("directive_stack", [])
            if stack:
                stack.pop()

    def _get_source_location(self, state: Any) -> str | None:
        """
        Extract source file location from parser state.

        Args:
            state: Parser state

        Returns:
            Location string like "content/guide.md:45" or None
        """
        env = getattr(state, "env", {})
        if isinstance(env, dict):
            source_file = env.get("source_file", "")
            # Line number tracking would require mistune modifications
            if source_file:
                return str(source_file)
        return None

    # -------------------------------------------------------------------------
    # Abstract Methods (must override in subclass)
    # -------------------------------------------------------------------------

    @abstractmethod
    def parse_directive(
        self,
        title: str,
        options: DirectiveOptions,
        content: str,
        children: list[Any],
        state: Any,
    ) -> DirectiveToken | dict[str, Any]:
        """
        Build the token from parsed components.

        Override this method to implement directive-specific logic.

        Args:
            title: Directive title (text after directive name)
            options: Parsed and typed options
            content: Raw content string (rarely needed, use children)
            children: Parsed nested content tokens
            state: Parser state (for accessing heading levels, etc.)

        Returns:
            DirectiveToken or dict for AST
        """
        ...

    @abstractmethod
    def render(self, renderer: Any, text: str, **attrs: Any) -> str:
        """
        Render token to HTML.

        Args:
            renderer: Mistune renderer instance
            text: Pre-rendered children HTML
            **attrs: Token attributes

        Returns:
            HTML string
        """
        ...

    # -------------------------------------------------------------------------
    # Registration
    # -------------------------------------------------------------------------

    def __call__(self, directive: Any, md: Any) -> None:
        """
        Register directive names and renderer.

        Override only if you need custom registration logic
        (e.g., multiple token types like AdmonitionDirective).

        Args:
            directive: Mistune directive registry
            md: Mistune Markdown instance
        """
        for name in self.NAMES:
            directive.register(name, self.parse)

        if md.renderer and md.renderer.NAME == "html":
            md.renderer.register(self.TOKEN_TYPE, self.render)

    # -------------------------------------------------------------------------
    # Shared Utilities
    # -------------------------------------------------------------------------

    @staticmethod
    def escape_html(text: str) -> str:
        """
        Escape HTML special characters for use in attributes.

        Escapes: & < > " '

        Args:
            text: Raw text to escape

        Returns:
            HTML-escaped text
        """
        return escape_html(text)

    @staticmethod
    def build_class_string(*classes: str) -> str:
        """
        Build CSS class string from multiple class sources.

        Filters out empty strings and joins with space.

        Args:
            *classes: Variable number of class strings

        Returns:
            Space-joined class string

        Example:
            build_class_string("dropdown", "", "my-class")
            # Returns: "dropdown my-class"
        """
        return build_class_string(*classes)

    @staticmethod
    def bool_attr(name: str, value: bool) -> str:
        """
        Return HTML boolean attribute string.

        Args:
            name: Attribute name (e.g., "open")
            value: Whether to include the attribute

        Returns:
            " name" if value is True, "" otherwise

        Example:
            bool_attr("open", True)   # Returns: " open"
            bool_attr("open", False)  # Returns: ""
        """
        return bool_attr(name, value)


__all__ = [
    # Base class
    "BengalDirective",
    # Tokens
    "DirectiveToken",
    # Options
    "DirectiveOptions",
    "StyledOptions",
    "ContainerOptions",
    "TitledOptions",
    # Contracts
    "DirectiveContract",
    "ContractValidator",
    "ContractViolation",
    "STEPS_CONTRACT",
    "STEP_CONTRACT",
    "TAB_SET_CONTRACT",
    "TAB_ITEM_CONTRACT",
    "CARDS_CONTRACT",
    "CARD_CONTRACT",
    "CODE_TABS_CONTRACT",
    # Errors
    "DirectiveError",
    "format_directive_error",
    # Utilities
    "escape_html",
    "build_class_string",
    "bool_attr",
    "data_attrs",
    "attr_str",
    "class_attr",
]
