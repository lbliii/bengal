"""Tests for Frontmatter dataclass."""

from __future__ import annotations

from datetime import datetime

import pytest

from bengal.core.page.frontmatter import Frontmatter


class TestFrontmatterFromDict:
    """Test Frontmatter.from_dict factory."""

    def test_separates_known_and_extra_fields(self) -> None:
        """Frontmatter.from_dict separates known and extra fields."""
        data = {
            "title": "My Post",
            "tags": ["python", "testing"],
            "custom_field": "value",
            "another_custom": 42,
        }
        fm = Frontmatter.from_dict(data)

        assert fm.title == "My Post"
        assert fm.tags == ["python", "testing"]
        assert fm.extra["custom_field"] == "value"
        assert fm.extra["another_custom"] == 42

    def test_handles_empty_dict(self) -> None:
        """Empty dict creates default Frontmatter."""
        fm = Frontmatter.from_dict({})

        assert fm.title == ""
        assert fm.tags == []
        assert fm.extra == {}

    def test_preserves_date_type(self) -> None:
        """Date field is preserved from input."""
        now = datetime.now()
        fm = Frontmatter.from_dict({"date": now})

        assert fm.date == now


class TestFrontmatterDictAccess:
    """Test dict-style access for template compatibility."""

    def test_getitem_known_field(self) -> None:
        """Dict access works for known fields."""
        fm = Frontmatter(title="Test")

        assert fm["title"] == "Test"

    def test_getitem_extra_field(self) -> None:
        """Dict access works for extra fields."""
        fm = Frontmatter(extra={"custom": "value"})

        assert fm["custom"] == "value"

    def test_getitem_missing_raises_keyerror(self) -> None:
        """Dict access raises KeyError for missing keys."""
        fm = Frontmatter()

        with pytest.raises(KeyError):
            _ = fm["nonexistent"]

    def test_get_with_default(self) -> None:
        """get() returns default for missing keys."""
        fm = Frontmatter()

        assert fm.get("missing") is None
        assert fm.get("missing", "default") == "default"

    def test_contains_known_field(self) -> None:
        """'in' operator works for known fields."""
        fm = Frontmatter(title="Test")

        assert "title" in fm
        assert "slug" not in fm  # None value

    def test_contains_extra_field(self) -> None:
        """'in' operator works for extra fields."""
        fm = Frontmatter(extra={"custom": "value"})

        assert "custom" in fm
        assert "missing" not in fm


class TestFrontmatterIteration:
    """Test iteration methods for templates."""

    def test_keys_yields_set_fields(self) -> None:
        """keys() yields fields with non-None values."""
        fm = Frontmatter(title="Test", tags=["a", "b"])

        keys = list(fm.keys())

        assert "title" in keys
        assert "tags" in keys
        assert "slug" not in keys  # None

    def test_keys_includes_extra(self) -> None:
        """keys() includes extra field keys."""
        fm = Frontmatter(title="Test", extra={"custom": "value"})

        keys = list(fm.keys())

        assert "custom" in keys

    def test_items_yields_key_value_pairs(self) -> None:
        """items() yields (key, value) tuples."""
        fm = Frontmatter(title="Test", tags=["a"])

        items = dict(fm.items())

        assert items["title"] == "Test"
        assert items["tags"] == ["a"]
