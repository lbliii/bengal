"""Base class for Bengal directives.

This module provides ``BengalDirective``, the foundation for all directive
implementations. It extends Mistune's ``DirectivePlugin`` with automatic
registration, typed options, and contract-based nesting validation.

Features:
    - **Automatic Registration**: Directives register themselves via ``NAMES``
      and ``TOKEN_TYPE`` class attributes.
    - **Typed Options**: Parse directive options into typed dataclasses using
      ``OPTIONS_CLASS``.
    - **Contract Validation**: Define valid parent-child relationships via
      ``CONTRACT`` to catch invalid nesting at parse time.
    - **Template Method Pattern**: Override ``parse_directive()`` and ``render()``
      for directive-specific logic.

Class Attributes:
    NAMES: List of directive names to register (e.g., ``["dropdown", "details"]``).
    TOKEN_TYPE: Token type string for the AST (e.g., ``"dropdown"``).
    OPTIONS_CLASS: Dataclass for typed option parsing (default: ``DirectiveOptions``).
    CONTRACT: Optional nesting validation contract (default: ``None``).

Example:
    Create a custom dropdown directive::

        from bengal.directives import BengalDirective, DirectiveToken

        class DropdownDirective(BengalDirective):
            NAMES = ["dropdown"]
            TOKEN_TYPE = "dropdown"

            def parse_directive(self, title, options, content, children, state):
                return DirectiveToken(
                    type=self.TOKEN_TYPE,
                    attrs={"title": title or "Details"},
                    children=children,
                )

            def render(self, renderer, text, **attrs):
                title = attrs.get("title", "Details")
                return f"<details><summary>{title}</summary>{text}</details>"

See Also:
    - ``bengal.directives.tokens``: ``DirectiveToken`` definition.
    - ``bengal.directives.options``: ``DirectiveOptions`` base class.
    - ``bengal.directives.contracts``: ``DirectiveContract`` for nesting rules.
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
    """Base class for Bengal directives with automatic registration and validation.

    Subclass this to create custom directives. The base class handles directive
    registration, option parsing, contract validation, and provides shared
    utilities for HTML generation.

    Subclass Requirements:
        Define these class attributes:
            NAMES: List of directive names (e.g., ``["dropdown", "details"]``).
            TOKEN_TYPE: Token type for the AST (e.g., ``"dropdown"``).

        Override these methods:
            parse_directive: Build the token from parsed components.
            render: Render the token to HTML.

        Optionally define:
            OPTIONS_CLASS: Typed options dataclass (default: ``DirectiveOptions``).
            CONTRACT: Nesting validation contract (default: ``None``).

    Attributes:
        logger: Module logger for warnings and debug output.

    Example:
        Basic directive with options::

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
                    open_attr = " open" if attrs.get("open") else ""
                    return f"<details{open_attr}><summary>{title}</summary>{text}</details>"

        Directive with contract validation::

            class StepDirective(BengalDirective):
                NAMES = ["step"]
                TOKEN_TYPE = "step"
                CONTRACT = DirectiveContract(requires_parent=("steps",))

                def parse_directive(self, title, options, content, children, state):
                    # Implementation here
                    ...

                def render(self, renderer, text, **attrs):
                    # Render implementation
                    ...
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
        """Initialize the directive with a module-level logger."""
        super().__init__()
        self.logger = get_logger(self.__class__.__module__)

    # -------------------------------------------------------------------------
    # Parse Flow with Contract Validation
    # -------------------------------------------------------------------------

    def parse(self, block: Any, m: Match[str], state: Any) -> dict[str, Any]:
        """Parse directive content with automatic contract validation.

        This method implements the standard parse flow:
            1. Validate parent context (if ``CONTRACT.requires_parent`` is set).
            2. Parse title, options, and content from the match.
            3. Recursively parse nested content into child tokens.
            4. Validate children (if ``CONTRACT.requires_children`` is set).
            5. Delegate to ``parse_directive()`` for directive-specific logic.

        Override ``parse_directive()`` for most cases. Override this method only
        if you need custom pre- or post-processing around the standard flow.

        Args:
            block: Mistune block parser instance.
            m: Regex match object from the directive pattern.
            state: Parser state containing environment and context.

        Returns:
            Token dictionary for the Mistune AST.

        Note:
            Contract violations emit warnings via the logger rather than raising
            exceptions, allowing graceful degradation of invalid markup.
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
        """Extract the parent directive type from parser state.

        Used by contract validation to verify ``requires_parent`` constraints.
        Checks both Bengal's directive stack and Mistune's state environment.

        Args:
            state: Parser state containing the directive stack.

        Returns:
            Parent directive type (e.g., ``"steps"``) or ``None`` if at root level.
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
        """Push the current directive onto the nesting stack.

        Called before parsing nested content so child directives can validate
        their parent context via ``_get_parent_directive_type()``.

        Args:
            state: Parser state to modify.
            directive_type: The directive type to push (e.g., ``"steps"``).
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
        """Pop the current directive from the nesting stack.

        Called after parsing nested content to restore the previous context.

        Args:
            state: Parser state to modify.
        """
        env = getattr(state, "env", {})
        if isinstance(env, dict):
            stack = env.get("directive_stack", [])
            if stack:
                stack.pop()

    def _get_source_location(self, state: Any) -> str | None:
        """Extract the source file path from parser state.

        Used for error messages and logging to help locate issues in content.

        Args:
            state: Parser state containing environment data.

        Returns:
            Source file path (e.g., ``"content/guide.md"``) or ``None`` if unavailable.
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
        """Build the AST token from parsed components.

        Override this method to implement directive-specific parsing logic.
        Called by ``parse()`` after options are parsed and children are processed.

        Args:
            title: Directive title (text after the directive name on the opening line).
            options: Typed options instance parsed from ``:option: value`` lines.
            content: Raw content string (rarely needed; prefer ``children``).
            children: Parsed nested content as a list of AST tokens.
            state: Parser state for accessing context like heading levels.

        Returns:
            A ``DirectiveToken`` or dict representing the AST node.

        Example:
            ::

                def parse_directive(self, title, options, content, children, state):
                    return DirectiveToken(
                        type=self.TOKEN_TYPE,
                        attrs={"title": title or "Default Title"},
                        children=children,
                    )
        """
        ...

    @abstractmethod
    def render(self, renderer: Any, text: str, **attrs: Any) -> str:
        """Render the directive token to HTML.

        Override this method to produce the final HTML output for the directive.
        Called by Mistune during the rendering phase.

        Args:
            renderer: Mistune renderer instance (provides access to other renderers).
            text: Pre-rendered HTML string of nested children.
            **attrs: Token attributes from ``parse_directive()`` (e.g., title, options).

        Returns:
            HTML string to insert into the output.

        Example:
            ::

                def render(self, renderer, text, **attrs):
                    title = attrs.get("title", "Details")
                    return f"<details><summary>{title}</summary>{text}</details>"
        """
        ...

    # -------------------------------------------------------------------------
    # Registration
    # -------------------------------------------------------------------------

    def __call__(self, directive: Any, md: Any) -> None:
        """Register directive names and the renderer with Mistune.

        Called when the directive is added to a Mistune markdown instance.
        Registers all names in ``NAMES`` and binds the ``render()`` method
        to the ``TOKEN_TYPE``.

        Override only for custom registration (e.g., directives with multiple
        token types like ``AdmonitionDirective``).

        Args:
            directive: Mistune directive registry to register parse handlers.
            md: Mistune Markdown instance to register the renderer.
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
        """Escape HTML special characters for safe use in attributes.

        Escapes: ``&``, ``<``, ``>``, ``"``, ``'``.

        Args:
            text: Raw text to escape.

        Returns:
            HTML-escaped string safe for use in attribute values.
        """
        return escape_html(text)

    @staticmethod
    def build_class_string(*classes: str) -> str:
        """Build a CSS class string from multiple class sources.

        Filters out empty strings and joins with spaces.

        Args:
            *classes: Variable number of class strings (may include empty strings).

        Returns:
            Space-joined class string, or empty string if no classes.

        Example:
            >>> BengalDirective.build_class_string("dropdown", "", "my-class")
            'dropdown my-class'
        """
        return build_class_string(*classes)

    @staticmethod
    def bool_attr(name: str, value: bool) -> str:
        """Generate an HTML boolean attribute string.

        Args:
            name: Attribute name (e.g., ``"open"``, ``"disabled"``).
            value: Whether to include the attribute.

        Returns:
            ``" name"`` if value is ``True``, empty string otherwise.

        Example:
            >>> BengalDirective.bool_attr("open", True)
            ' open'
            >>> BengalDirective.bool_attr("open", False)
            ''
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
