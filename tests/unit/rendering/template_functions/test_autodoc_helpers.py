"""
Tests for autodoc ergonomic helper functions (Tier 3).

These helpers simplify common template patterns for filtering autodoc elements.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from bengal.rendering.template_functions.autodoc import (
    children_by_type,
    private_only,
    public_only,
)


@dataclass
class MockDocElement:
    """Mock DocElement for testing."""

    name: str
    element_type: str
    children: list[Any] | None = None


class TestChildrenByType:
    """Tests for children_by_type()."""

    def test_filters_by_element_type(self) -> None:
        """Returns only children matching the specified type."""
        children = [
            MockDocElement(name="method1", element_type="method"),
            MockDocElement(name="func1", element_type="function"),
            MockDocElement(name="method2", element_type="method"),
            MockDocElement(name="attr1", element_type="attribute"),
        ]

        result = children_by_type(children, "method")

        assert len(result) == 2
        assert result[0].name == "method1"
        assert result[1].name == "method2"

    def test_returns_empty_for_no_matches(self) -> None:
        """Returns empty list when no children match."""
        children = [
            MockDocElement(name="func1", element_type="function"),
            MockDocElement(name="attr1", element_type="attribute"),
        ]

        result = children_by_type(children, "method")

        assert result == []

    def test_handles_empty_list(self) -> None:
        """Handles empty children list."""
        result = children_by_type([], "method")

        assert result == []

    def test_handles_none(self) -> None:
        """Handles None input."""
        result = children_by_type(None, "method")  # type: ignore[arg-type]

        assert result == []

    def test_handles_items_without_element_type(self) -> None:
        """Skips items without element_type attribute."""

        @dataclass
        class NoType:
            name: str

        children = [
            MockDocElement(name="method1", element_type="method"),
            NoType(name="orphan"),
        ]

        result = children_by_type(children, "method")

        assert len(result) == 1
        assert result[0].name == "method1"


class TestPublicOnly:
    """Tests for public_only()."""

    def test_filters_to_public_members(self) -> None:
        """Returns only members not starting with underscore."""
        members = [
            MockDocElement(name="public_method", element_type="method"),
            MockDocElement(name="_private_method", element_type="method"),
            MockDocElement(name="another_public", element_type="method"),
            MockDocElement(name="__dunder__", element_type="method"),
        ]

        result = public_only(members)

        assert len(result) == 2
        assert result[0].name == "public_method"
        assert result[1].name == "another_public"

    def test_returns_empty_for_all_private(self) -> None:
        """Returns empty list when all members are private."""
        members = [
            MockDocElement(name="_private1", element_type="method"),
            MockDocElement(name="__private2", element_type="method"),
        ]

        result = public_only(members)

        assert result == []

    def test_handles_empty_list(self) -> None:
        """Handles empty members list."""
        result = public_only([])

        assert result == []

    def test_handles_none(self) -> None:
        """Handles None input."""
        result = public_only(None)  # type: ignore[arg-type]

        assert result == []

    def test_handles_items_without_name(self) -> None:
        """Handles items without name attribute (treats as public)."""

        @dataclass
        class NoName:
            element_type: str

        members = [
            MockDocElement(name="public", element_type="method"),
            NoName(element_type="method"),
        ]

        # Items without name have getattr return "", which doesn't start with _
        result = public_only(members)

        assert len(result) == 2


class TestPrivateOnly:
    """Tests for private_only()."""

    def test_filters_to_private_members(self) -> None:
        """Returns only members starting with underscore."""
        members = [
            MockDocElement(name="public_method", element_type="method"),
            MockDocElement(name="_private_method", element_type="method"),
            MockDocElement(name="another_public", element_type="method"),
            MockDocElement(name="__dunder__", element_type="method"),
        ]

        result = private_only(members)

        assert len(result) == 2
        assert result[0].name == "_private_method"
        assert result[1].name == "__dunder__"

    def test_returns_empty_for_all_public(self) -> None:
        """Returns empty list when all members are public."""
        members = [
            MockDocElement(name="public1", element_type="method"),
            MockDocElement(name="public2", element_type="method"),
        ]

        result = private_only(members)

        assert result == []

    def test_handles_empty_list(self) -> None:
        """Handles empty members list."""
        result = private_only([])

        assert result == []

    def test_handles_none(self) -> None:
        """Handles None input."""
        result = private_only(None)  # type: ignore[arg-type]

        assert result == []


class TestHelperChaining:
    """Test chaining helpers together as in real templates."""

    def test_children_by_type_then_public_only(self) -> None:
        """Demonstrates chaining: filter by type, then by visibility."""
        children = [
            MockDocElement(name="public_method", element_type="method"),
            MockDocElement(name="_private_method", element_type="method"),
            MockDocElement(name="public_function", element_type="function"),
            MockDocElement(name="__init__", element_type="method"),
        ]

        # Chain: get methods, then filter to public only
        methods = children_by_type(children, "method")
        public_methods = public_only(methods)

        assert len(public_methods) == 1
        assert public_methods[0].name == "public_method"

    def test_children_by_type_then_private_only(self) -> None:
        """Demonstrates chaining: filter by type, then to private."""
        children = [
            MockDocElement(name="public_method", element_type="method"),
            MockDocElement(name="_private_method", element_type="method"),
            MockDocElement(name="public_function", element_type="function"),
            MockDocElement(name="__init__", element_type="method"),
        ]

        # Chain: get methods, then filter to private only
        methods = children_by_type(children, "method")
        private_methods = private_only(methods)

        assert len(private_methods) == 2
        names = [m.name for m in private_methods]
        assert "_private_method" in names
        assert "__init__" in names


