"""Tests for directive token types."""

from __future__ import annotations

from bengal.directives.tokens import DirectiveToken, DirectiveType


class TestDirectiveType:
    """Test DirectiveType enum."""

    def test_known_types_exist(self) -> None:
        """Known directive types are defined."""
        assert DirectiveType.STEP.value == "step"
        assert DirectiveType.NOTE.value == "note"
        assert DirectiveType.TABS.value == "tabs"
        assert DirectiveType.DROPDOWN.value == "dropdown"

    def test_enum_iteration(self) -> None:
        """Can iterate over directive types."""
        types = list(DirectiveType)

        assert len(types) > 0
        assert DirectiveType.STEP in types

    def test_container_types(self) -> None:
        """Container directive types are defined."""
        assert DirectiveType.STEPS.value == "steps"
        assert DirectiveType.TAB_SET.value == "tab_set"
        assert DirectiveType.CARDS_GRID.value == "cards_grid"

    def test_admonition_types(self) -> None:
        """Admonition directive types are defined."""
        assert DirectiveType.NOTE.value == "note"
        assert DirectiveType.WARNING.value == "warning"
        assert DirectiveType.TIP.value == "tip"
        assert DirectiveType.IMPORTANT.value == "important"
        assert DirectiveType.CAUTION.value == "caution"


class TestDirectiveToken:
    """Test DirectiveToken dataclass structure."""

    def test_minimal_token(self) -> None:
        """Minimal token has required type field."""
        token = DirectiveToken(type="note")

        assert token.type == "note"
        assert token.attrs == {}
        assert token.children == []

    def test_full_token(self) -> None:
        """Full token has all optional fields."""
        token = DirectiveToken(
            type="step",
            attrs={"id": "step-1", "title": "First Step"},
            children=[{"type": "paragraph"}],
        )

        assert token.type == "step"
        assert token.attrs["id"] == "step-1"
        assert len(token.children) == 1

    def test_nested_tokens(self) -> None:
        """Tokens can be nested."""
        child1 = DirectiveToken(type="step", attrs={"body": "First"})
        child2 = DirectiveToken(type="step", attrs={"body": "Second"})

        parent = DirectiveToken(
            type="steps",
            children=[child1.to_dict(), child2.to_dict()],
        )

        assert len(parent.children) == 2
        assert parent.children[0]["type"] == "step"

    def test_to_dict(self) -> None:
        """to_dict() converts token to Mistune-compatible dict."""
        token = DirectiveToken(
            type="note",
            attrs={"class": "info"},
            children=[],
        )

        result = token.to_dict()

        assert result == {
            "type": "note",
            "attrs": {"class": "info"},
            "children": [],
        }

    def test_from_dict(self) -> None:
        """from_dict() creates token from dictionary."""
        data = {
            "type": "note",
            "attrs": {"class": "info"},
            "children": [{"type": "text"}],
        }

        token = DirectiveToken.from_dict(data)

        assert token.type == "note"
        assert token.attrs == {"class": "info"}
        assert len(token.children) == 1

    def test_with_attrs(self) -> None:
        """with_attrs() returns new token with merged attrs."""
        original = DirectiveToken(type="card", attrs={"title": "My Card"})

        updated = original.with_attrs(id="card-1", open=True)

        # Original unchanged
        assert "id" not in original.attrs
        # New token has merged attrs
        assert updated.attrs["title"] == "My Card"
        assert updated.attrs["id"] == "card-1"
        assert updated.attrs["open"] is True

    def test_with_children(self) -> None:
        """with_children() returns new token with different children."""
        original = DirectiveToken(type="tabs", children=[1, 2, 3])

        updated = original.with_children([4, 5])

        # Original unchanged
        assert original.children == [1, 2, 3]
        # New token has new children
        assert updated.children == [4, 5]
