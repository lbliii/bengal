"""Tests for role mapping (TokenType -> SyntaxRole)."""

from __future__ import annotations

from bengal.rendering.rosettes import TokenType
from bengal.rendering.rosettes.themes._mapping import ROLE_MAPPING
from bengal.rendering.rosettes.themes._roles import SyntaxRole


class TestRoleMapping:
    """Test TokenType to SyntaxRole mapping."""

    def test_all_token_types_have_roles(self) -> None:
        """All TokenType values should map to SyntaxRole."""
        for token_type in TokenType:
            role = ROLE_MAPPING.get(token_type)
            assert role is not None, f"TokenType.{token_type.name} has no role mapping"
            assert isinstance(role, SyntaxRole)

    def test_keyword_maps_to_control_flow(self) -> None:
        """Keywords should map to CONTROL_FLOW or DECLARATION."""
        role = ROLE_MAPPING.get(TokenType.KEYWORD)
        assert role in [SyntaxRole.CONTROL_FLOW, SyntaxRole.DECLARATION]

    def test_string_maps_to_string(self) -> None:
        """String types should map to STRING."""
        role = ROLE_MAPPING.get(TokenType.STRING)
        assert role == SyntaxRole.STRING

    def test_number_maps_to_number(self) -> None:
        """Number types should map to NUMBER."""
        role = ROLE_MAPPING.get(TokenType.NUMBER)
        assert role == SyntaxRole.NUMBER

    def test_comment_maps_to_comment(self) -> None:
        """Comment types should map to COMMENT."""
        role = ROLE_MAPPING.get(TokenType.COMMENT)
        assert role == SyntaxRole.COMMENT
