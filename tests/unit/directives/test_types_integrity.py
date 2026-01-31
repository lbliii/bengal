"""
TypedDict integrity tests for directive types.

These tests ensure that TypedDicts are correctly defined and inherited,
and document the actual field names used in the directive type system.
"""

from __future__ import annotations

from typing import get_type_hints

import pytest

from bengal.directives.types import (
    AdmonitionAttrs,
    CardAttrs,
    CodeBlockAttrs,
    DirectiveAttrs,
    DirectiveToken,
    DropdownAttrs,
    GridAttrs,
    ImageAttrs,
    IncludeAttrs,
    StepAttrs,
    StyledAttrs,
    TabItemAttrs,
    TabSetAttrs,
    TitledAttrs,
)


class TestTypedDictInheritance:
    """Test that TypedDicts inherit correctly."""

    def test_directive_attrs_base_fields(self):
        """DirectiveAttrs should define the base fields."""
        hints = get_type_hints(DirectiveAttrs)
        # Uses class_ to avoid Python keyword, not classes
        assert "class_" in hints
        assert "id" in hints
        assert "title" in hints

    def test_titled_attrs_has_own_fields(self):
        """TitledAttrs should have its own fields plus inherited ones."""
        hints = get_type_hints(TitledAttrs)
        # Own fields
        assert "icon" in hints
        assert "collapsible" in hints
        assert "open" in hints
        # Inherited from DirectiveAttrs
        assert "title" in hints

    def test_dropdown_attrs_has_own_fields(self):
        """DropdownAttrs should have its own fields plus inherited."""
        hints = get_type_hints(DropdownAttrs)
        assert "open" in hints
        assert "icon" in hints
        # Inherited
        assert "title" in hints

    def test_card_attrs_has_own_fields(self):
        """CardAttrs should have its own fields."""
        hints = get_type_hints(CardAttrs)
        assert "link" in hints
        assert "image" in hints
        assert "footer" in hints

    def test_step_attrs_has_own_fields(self):
        """StepAttrs should have its own fields."""
        hints = get_type_hints(StepAttrs)
        assert "number" in hints

    def test_all_typed_dicts_have_base_fields(self):
        """All directive TypedDicts should have the base fields from DirectiveAttrs."""
        base_fields = {"class_", "id", "title"}

        directive_types = [
            DirectiveAttrs,
            TitledAttrs,
            DropdownAttrs,
            CardAttrs,
            TabSetAttrs,
            TabItemAttrs,
            StepAttrs,
            AdmonitionAttrs,
            IncludeAttrs,
            CodeBlockAttrs,
            ImageAttrs,
            GridAttrs,
        ]

        for typed_dict in directive_types:
            hints = get_type_hints(typed_dict)
            for field in base_fields:
                assert field in hints, f"{typed_dict.__name__} missing base field '{field}'"


class TestDirectiveTokenIntegrity:
    """Test DirectiveToken TypedDict correctness."""

    def test_directive_token_fields(self):
        """DirectiveToken should have all expected fields."""
        hints = get_type_hints(DirectiveToken)
        expected = {"type", "attrs", "children"}
        assert expected.issubset(hints.keys())

    def test_directive_token_type_field(self):
        """DirectiveToken.type should be str."""
        hints = get_type_hints(DirectiveToken)
        assert hints["type"] == str


class TestTypedDictTotality:
    """Test TypedDict total=False behavior."""

    def test_directive_attrs_total_false(self):
        """DirectiveAttrs should have total=False (all fields optional)."""
        # In Python, TypedDicts with total=False have __required_keys__ empty
        assert len(DirectiveAttrs.__required_keys__) == 0

    def test_titled_attrs_total_false(self):
        """TitledAttrs should have total=False."""
        assert len(TitledAttrs.__required_keys__) == 0


class TestTypedDictInstantiation:
    """Test that TypedDicts can be instantiated correctly."""

    def test_directive_attrs_empty(self):
        """DirectiveAttrs can be instantiated empty (total=False)."""
        attrs: DirectiveAttrs = {}
        assert isinstance(attrs, dict)

    def test_directive_attrs_with_values(self):
        """DirectiveAttrs can be instantiated with values."""
        attrs: DirectiveAttrs = {"title": "Test", "class_": "my-class"}
        assert attrs["title"] == "Test"
        assert attrs["class_"] == "my-class"

    def test_titled_attrs_with_inherited_fields(self):
        """TitledAttrs should accept inherited fields from DirectiveAttrs."""
        attrs: TitledAttrs = {
            "title": "Test",
            "class_": "cls",
            "icon": "star",
            "collapsible": True,
            "open": False,
        }
        assert attrs["title"] == "Test"
        assert attrs["icon"] == "star"

    def test_dropdown_attrs_full(self):
        """DropdownAttrs should accept all its fields."""
        attrs: DropdownAttrs = {
            "title": "Dropdown",
            "class_": "my-dropdown",
            "icon": "chevron",
            "open": False,
        }
        assert attrs["open"] is False

    def test_card_attrs_full(self):
        """CardAttrs should accept all its fields."""
        attrs: CardAttrs = {
            "title": "Card",
            "class_": "my-card",
            "link": "/path",
            "footer": "Read more",
        }
        assert attrs["link"] == "/path"


class TestIncludeAttrsIntegrity:
    """Test include-related TypedDict integrity."""

    def test_include_attrs_has_file_field(self):
        """IncludeAttrs should have file field."""
        hints = get_type_hints(IncludeAttrs)
        assert "file" in hints

    def test_include_attrs_has_lines_field(self):
        """IncludeAttrs should have lines field for line selection."""
        hints = get_type_hints(IncludeAttrs)
        # Uses 'lines' as a line spec like "1-10"
        assert "lines" in hints

    def test_include_attrs_has_markers(self):
        """IncludeAttrs should have start_after/end_before markers."""
        hints = get_type_hints(IncludeAttrs)
        assert "start_after" in hints
        assert "end_before" in hints

    def test_code_block_attrs_fields(self):
        """CodeBlockAttrs should have code-specific fields."""
        hints = get_type_hints(CodeBlockAttrs)
        assert "language" in hints
        assert "linenos" in hints
        assert "hl_lines" in hints
        assert "start_line" in hints


class TestSpecificDirectiveAttrs:
    """Test specific directive attribute types."""

    def test_admonition_attrs_has_type(self):
        """AdmonitionAttrs should have type field."""
        hints = get_type_hints(AdmonitionAttrs)
        assert "type" in hints

    def test_tab_set_attrs_has_sync(self):
        """TabSetAttrs should have sync field."""
        hints = get_type_hints(TabSetAttrs)
        assert "sync" in hints
        assert "selected" in hints

    def test_tab_item_attrs_has_label(self):
        """TabItemAttrs should have label field."""
        hints = get_type_hints(TabItemAttrs)
        assert "label" in hints
        assert "sync" in hints

    def test_image_attrs_has_src(self):
        """ImageAttrs should have src and alt fields."""
        hints = get_type_hints(ImageAttrs)
        assert "src" in hints
        assert "alt" in hints

    def test_grid_attrs_has_layout(self):
        """GridAttrs should have layout fields."""
        hints = get_type_hints(GridAttrs)
        assert "columns" in hints
        assert "gutter" in hints


class TestTypeHintConsistency:
    """Test that type hints are consistent across related types."""

    def test_title_type_consistent(self):
        """All TypedDicts with title should have the same type."""
        types_with_title = [
            DirectiveAttrs,
            TitledAttrs,
            DropdownAttrs,
            CardAttrs,
            StepAttrs,
            TabSetAttrs,
            TabItemAttrs,
        ]

        title_types = []
        for t in types_with_title:
            hints = get_type_hints(t)
            if "title" in hints:
                title_types.append((t.__name__, hints["title"]))

        # All should have the same type for title
        if title_types:
            first_type = title_types[0][1]
            for name, hint in title_types[1:]:
                assert hint == first_type, (
                    f"Inconsistent title type: {name} has {hint}, expected {first_type}"
                )

    def test_class_field_consistent(self):
        """All TypedDicts should use class_ (not classes) for CSS class."""
        directive_types = [
            DirectiveAttrs,
            TitledAttrs,
            DropdownAttrs,
            CardAttrs,
        ]

        for t in directive_types:
            hints = get_type_hints(t)
            # Should use class_ not classes (to avoid Python keyword)
            assert "class_" in hints
            assert "classes" not in hints
