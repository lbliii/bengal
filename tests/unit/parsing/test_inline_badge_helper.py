"""Unit tests for ensure_badge_base_class helper."""

from __future__ import annotations

from bengal.parsing.backends.patitas.directives.builtins.inline import ensure_badge_base_class


class TestEnsureBadgeBaseClass:
    """Test ensure_badge_base_class single-pass implementation."""

    def test_empty_input_returns_default(self) -> None:
        """Empty input returns badge badge-secondary."""
        assert ensure_badge_base_class("") == "badge badge-secondary"

    def test_already_has_badge_base(self) -> None:
        """Input with badge base returns unchanged."""
        assert ensure_badge_base_class("badge badge-primary") == "badge badge-primary"
        assert ensure_badge_base_class("badge badge-secondary") == "badge badge-secondary"

    def test_already_has_api_badge_base(self) -> None:
        """Input with api-badge base returns unchanged."""
        assert (
            ensure_badge_base_class("api-badge api-badge-primary") == "api-badge api-badge-primary"
        )

    def test_needs_badge_prefix(self) -> None:
        """Input with badge- class gets badge prefix."""
        assert ensure_badge_base_class("badge-primary") == "badge badge-primary"
        assert ensure_badge_base_class("badge-secondary") == "badge badge-secondary"

    def test_needs_api_badge_prefix(self) -> None:
        """Input with api-badge- class gets api-badge prefix."""
        assert ensure_badge_base_class("api-badge-primary") == "api-badge api-badge-primary"

    def test_custom_class_gets_badge_prefix(self) -> None:
        """Input with no base class gets badge prefix."""
        assert ensure_badge_base_class("custom") == "badge custom"
        assert ensure_badge_base_class("my-class") == "badge my-class"
