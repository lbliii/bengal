"""
Syntax highlighting backend protocol definition.

This module defines the interface contract that ALL highlighting backends must implement.
The protocol ensures consistent behavior across Pygments, tree-sitter, and any
custom or third-party backends.

Design Philosophy:
    - **Runtime checkable**: Can verify implementations at runtime
    - **Clear contracts**: Each method documents preconditions and guarantees
    - **Minimal interface**: Only essential methods required
    - **Follows Bengal patterns**: Matches TemplateEngineProtocol style

Required Methods:
    - highlight(): Render code with syntax highlighting
    - supports_language(): Check if backend supports a language

Required Properties:
    - name: Backend identifier for configuration

Implementing Custom Backends:
    To create a custom backend, implement all protocol methods:

    .. code-block:: python

        class MyBackend:
            @property
            def name(self) -> str:
                return "my-backend"

            def highlight(
                self,
                code: str,
                language: str,
                hl_lines: list[int] | None = None,
                show_linenos: bool = False,
            ) -> str:
                # Implementation...

            def supports_language(self, language: str) -> bool:
                # Implementation...

    Then register it:

    >>> from bengal.rendering.highlighting import register_backend
    >>> register_backend("my-backend", MyBackend)

Related Modules:
    - bengal.rendering.highlighting: Backend factory and registration
    - bengal.rendering.highlighting.pygments: Default Pygments backend
    - bengal.rendering.highlighting.tree_sitter: Optional tree-sitter backend
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class HighlightBackend(Protocol):
    """
    Standardized interface for Bengal syntax highlighting backends.

    Follows Bengal's "bring your own X" pattern established by:
    - TemplateEngineProtocol (template engines)
    - BaseMarkdownParser (markdown parsers)
    - ContentSource (content sources)

    REQUIRED PROPERTIES:
        name: Backend identifier (used in config, e.g., "pygments", "tree-sitter")

    REQUIRED METHODS:
        highlight(): Render code with syntax highlighting to HTML
        supports_language(): Check if backend supports a language

    ALL methods are required. No optional methods. This ensures:
        - Consistent behavior across backends
        - Easy testing and mocking
        - Clear contract for third-party backends
    """

    @property
    def name(self) -> str:
        """
        Backend identifier for configuration.

        Returns:
            Unique backend name (e.g., "pygments", "tree-sitter")

        Contract:
            - MUST be lowercase, hyphen-separated
            - MUST be stable (same value across calls)
        """
        ...

    def highlight(
        self,
        code: str,
        language: str,
        hl_lines: list[int] | None = None,
        show_linenos: bool = False,
    ) -> str:
        """
        Render code with syntax highlighting.

        Args:
            code: Source code to highlight
            language: Programming language identifier (e.g., "python", "rust")
            hl_lines: Line numbers to highlight (1-indexed). Empty list or None
                     means no highlighted lines.
            show_linenos: Whether to include line numbers in output

        Returns:
            HTML string with highlighted code. The output should:
            - Be wrapped in appropriate container elements (<pre>, <code>, etc.)
            - Use CSS classes (not inline styles) for tokens
            - Be compatible with Pygments CSS themes

        Raises:
            No exceptions should be raised. On errors:
            - Return escaped plain text as fallback
            - Log warning for debugging

        Contract:
            - MUST return valid HTML (never raise)
            - MUST escape HTML entities in code
            - MUST use CSS classes compatible with Pygments themes
            - SHOULD fall back gracefully for unsupported languages
        """
        ...

    def supports_language(self, language: str) -> bool:
        """
        Check if this backend supports the given language.

        Args:
            language: Programming language identifier

        Returns:
            True if backend can highlight this language, False otherwise

        Contract:
            - MUST NOT raise exceptions (return False instead)
            - SHOULD handle common aliases (e.g., "js" -> "javascript")
        """
        ...
