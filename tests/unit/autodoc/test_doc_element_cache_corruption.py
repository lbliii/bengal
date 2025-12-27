"""
Tests for handling corrupted cache data in DocElement deserialization.

Tests that DocElement.from_dict() gracefully handles malformed cache data
without crashing builds, allowing cache self-healing.
"""

from __future__ import annotations

from bengal.autodoc.base import DocElement


class TestMalformedCacheData:
    """Tests for handling malformed cache data."""

    def test_from_dict_with_string_children_skips_invalid(self) -> None:
        """Test that string children are skipped instead of crashing."""
        data = {
            "name": "test",
            "qualified_name": "module.test",
            "description": "Test element",
            "element_type": "module",
            "source_file": None,
            "line_number": None,
            "metadata": {},
            "children": [
                "invalid_string_child",  # Invalid: string instead of dict
                {
                    "name": "valid_child",
                    "qualified_name": "module.test.valid_child",
                    "description": "Valid child",
                    "element_type": "function",
                    "source_file": None,
                    "line_number": None,
                    "metadata": {},
                    "children": [],
                    "examples": [],
                    "see_also": [],
                    "deprecated": None,
                },
            ],
            "examples": [],
            "see_also": [],
            "deprecated": None,
        }

        # Should not crash - invalid children are skipped
        element = DocElement.from_dict(data)

        assert element.name == "test"
        # Only valid child should be deserialized
        assert len(element.children) == 1
        assert element.children[0].name == "valid_child"

    def test_from_dict_with_string_data_returns_malformed_element(self) -> None:
        """Test that string data (instead of dict) returns a placeholder element."""
        # This simulates cache corruption where the entire element is a string
        data = "corrupted_cache_entry"  # Invalid: string instead of dict

        # Should not crash - returns a placeholder element
        element = DocElement.from_dict(data)  # type: ignore[arg-type]

        assert element.name == "<malformed>"
        assert element.qualified_name == "<malformed>"
        assert element.description == "Malformed cache entry (skipped)"
        assert element.element_type == "unknown"
        assert len(element.children) == 0

    def test_from_dict_with_mixed_valid_invalid_children(self) -> None:
        """Test handling of mixed valid/invalid children."""
        data = {
            "name": "parent",
            "qualified_name": "module.parent",
            "description": "Parent element",
            "element_type": "class",
            "source_file": None,
            "line_number": None,
            "metadata": {},
            "children": [
                "invalid1",  # String
                123,  # Number
                None,  # None
                {
                    "name": "valid1",
                    "qualified_name": "module.parent.valid1",
                    "description": "Valid child 1",
                    "element_type": "method",
                    "source_file": None,
                    "line_number": None,
                    "metadata": {},
                    "children": [],
                    "examples": [],
                    "see_also": [],
                    "deprecated": None,
                },
                {
                    "name": "valid2",
                    "qualified_name": "module.parent.valid2",
                    "description": "Valid child 2",
                    "element_type": "method",
                    "source_file": None,
                    "line_number": None,
                    "metadata": {},
                    "children": [],
                    "examples": [],
                    "see_also": [],
                    "deprecated": None,
                },
            ],
            "examples": [],
            "see_also": [],
            "deprecated": None,
        }

        element = DocElement.from_dict(data)

        assert element.name == "parent"
        # Only valid dict children should be deserialized
        assert len(element.children) == 2
        assert element.children[0].name == "valid1"
        assert element.children[1].name == "valid2"

    def test_from_dict_with_nested_corrupted_children(self) -> None:
        """Test handling of nested corrupted children."""
        data = {
            "name": "parent",
            "qualified_name": "module.parent",
            "description": "Parent element",
            "element_type": "class",
            "source_file": None,
            "line_number": None,
            "metadata": {},
            "children": [
                {
                    "name": "child",
                    "qualified_name": "module.parent.child",
                    "description": "Child element",
                    "element_type": "method",
                    "source_file": None,
                    "line_number": None,
                    "metadata": {},
                    "children": [
                        "invalid_grandchild",  # Invalid nested child
                        {
                            "name": "valid_grandchild",
                            "qualified_name": "module.parent.child.valid_grandchild",
                            "description": "Valid grandchild",
                            "element_type": "function",
                            "source_file": None,
                            "line_number": None,
                            "metadata": {},
                            "children": [],
                            "examples": [],
                            "see_also": [],
                            "deprecated": None,
                        },
                    ],
                    "examples": [],
                    "see_also": [],
                    "deprecated": None,
                },
            ],
            "examples": [],
            "see_also": [],
            "deprecated": None,
        }

        element = DocElement.from_dict(data)

        assert element.name == "parent"
        assert len(element.children) == 1
        child = element.children[0]
        assert child.name == "child"
        # Only valid grandchild should be deserialized
        assert len(child.children) == 1
        assert child.children[0].name == "valid_grandchild"

    def test_to_dict_validates_children_types(self) -> None:
        """Test that to_dict() validates children are DocElement instances."""
        # Create element with invalid child (string instead of DocElement)
        # This simulates a bug where non-DocElement objects get into children
        element = DocElement(
            name="test",
            qualified_name="module.test",
            description="Test element",
            element_type="module",
        )

        # Manually inject invalid child (bypassing type checking)
        element.children.append("invalid_child")  # type: ignore[arg-type]

        # Should log error but not crash - invalid children are filtered
        data = element.to_dict()

        # Invalid child should be filtered out
        assert len(data["children"]) == 0

    def test_to_jsonable_with_doc_element_in_metadata_converts_properly(self) -> None:
        """Test that DocElement objects in metadata are converted via to_dict(), not str()."""
        # Create a child element
        child = DocElement(
            name="child",
            qualified_name="module.parent.child",
            description="Child element",
            element_type="function",
        )

        # Create parent with child in metadata (simulating a bug scenario)
        parent = DocElement(
            name="parent",
            qualified_name="module.parent",
            description="Parent element",
            element_type="class",
            metadata={"nested_element": child},  # DocElement in metadata
        )

        # Should convert child via to_dict(), not str()
        data = parent.to_dict()

        assert data["name"] == "parent"
        # Metadata should contain the child as a dict, not a string
        nested = data["metadata"].get("nested_element")
        assert isinstance(nested, dict), "DocElement in metadata should be converted to dict"
        assert nested["name"] == "child"
        assert nested["qualified_name"] == "module.parent.child"
