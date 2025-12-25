"""
Tests for the HighlightBackend protocol.

Validates that the protocol is properly defined and can be used
for type checking and runtime verification.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from bengal.rendering.highlighting import HighlightBackend
from bengal.rendering.highlighting.rosettes import RosettesBackend

if TYPE_CHECKING:
    pass


class TestHighlightBackendProtocol:
    """Test the HighlightBackend protocol definition."""

    def test_protocol_is_runtime_checkable(self) -> None:
        """Protocol should be usable with isinstance()."""
        backend = RosettesBackend()
        assert isinstance(backend, HighlightBackend)

    def test_rosettes_backend_implements_protocol(self) -> None:
        """RosettesBackend should implement all protocol methods."""
        backend = RosettesBackend()

        # Check required property
        assert hasattr(backend, "name")
        assert backend.name == "rosettes"

        # Check required methods
        assert hasattr(backend, "highlight")
        assert callable(backend.highlight)

        assert hasattr(backend, "supports_language")
        assert callable(backend.supports_language)

    def test_protocol_method_signatures(self) -> None:
        """Protocol methods should accept the documented arguments."""
        backend = RosettesBackend()

        # highlight() should accept these arguments
        result = backend.highlight(
            code="print('hello')",
            language="python",
            hl_lines=[1],
            show_linenos=True,
        )
        assert isinstance(result, str)
        assert len(result) > 0

        # supports_language() should accept language string
        result = backend.supports_language("python")
        assert isinstance(result, bool)


class TestCustomBackendProtocolCompliance:
    """Test that custom backends can implement the protocol."""

    def test_minimal_backend_implementation(self) -> None:
        """A minimal backend implementation should work."""

        class MinimalBackend:
            @property
            def name(self) -> str:
                return "minimal"

            def highlight(
                self,
                code: str,
                language: str,
                hl_lines: list[int] | None = None,
                show_linenos: bool = False,
            ) -> str:
                return f"<pre><code>{code}</code></pre>"

            def supports_language(self, language: str) -> bool:
                return True

        backend = MinimalBackend()
        assert isinstance(backend, HighlightBackend)

    def test_incomplete_backend_not_protocol_compliant(self) -> None:
        """A backend missing methods should not pass isinstance check."""

        class IncompleteBackend:
            @property
            def name(self) -> str:
                return "incomplete"

            # Missing highlight() and supports_language()

        backend = IncompleteBackend()
        assert not isinstance(backend, HighlightBackend)
