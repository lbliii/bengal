"""
Unit tests for common autodoc models (QualifiedName, SourceLocation).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from bengal.autodoc.models import QualifiedName, SourceLocation


class TestSourceLocation:
    """Tests for SourceLocation dataclass."""

    def test_basic_creation(self) -> None:
        """Test basic SourceLocation creation."""
        loc = SourceLocation(file="bengal/core/site.py", line=45)
        assert loc.file == "bengal/core/site.py"
        assert loc.line == 45
        assert loc.column is None

    def test_with_column(self) -> None:
        """Test SourceLocation with column."""
        loc = SourceLocation(file="test.py", line=10, column=5)
        assert loc.file == "test.py"
        assert loc.line == 10
        assert loc.column == 5

    def test_from_path(self) -> None:
        """Test SourceLocation.from_path factory."""
        path = Path("bengal/core/site.py")
        loc = SourceLocation.from_path(path, line=100, column=20)
        assert loc.file == "bengal/core/site.py"
        assert loc.line == 100
        assert loc.column == 20

    def test_rejects_zero_line(self) -> None:
        """Test that line=0 raises ValueError."""
        with pytest.raises(ValueError, match="Line must be >= 1"):
            SourceLocation(file="test.py", line=0)

    def test_rejects_negative_line(self) -> None:
        """Test that negative line raises ValueError."""
        with pytest.raises(ValueError, match="Line must be >= 1"):
            SourceLocation(file="test.py", line=-5)

    def test_rejects_zero_column(self) -> None:
        """Test that column=0 raises ValueError."""
        with pytest.raises(ValueError, match="Column must be >= 1"):
            SourceLocation(file="test.py", line=1, column=0)

    def test_rejects_negative_column(self) -> None:
        """Test that negative column raises ValueError."""
        with pytest.raises(ValueError, match="Column must be >= 1"):
            SourceLocation(file="test.py", line=1, column=-1)

    def test_frozen(self) -> None:
        """Test that SourceLocation is frozen (immutable)."""
        loc = SourceLocation(file="test.py", line=1)
        with pytest.raises(AttributeError):
            loc.line = 2  # type: ignore[misc]

    def test_hashable(self) -> None:
        """Test that SourceLocation is hashable."""
        loc1 = SourceLocation(file="test.py", line=1)
        loc2 = SourceLocation(file="test.py", line=1)
        loc3 = SourceLocation(file="test.py", line=2)

        # Same values should be equal and have same hash
        assert loc1 == loc2
        assert hash(loc1) == hash(loc2)

        # Different values should be unequal
        assert loc1 != loc3

        # Should be usable in sets
        locs = {loc1, loc2, loc3}
        assert len(locs) == 2  # loc1 and loc2 are the same


class TestQualifiedName:
    """Tests for QualifiedName dataclass."""

    def test_basic_creation(self) -> None:
        """Test basic QualifiedName creation."""
        qn = QualifiedName(parts=("bengal", "core", "site"))
        assert qn.parts == ("bengal", "core", "site")
        assert str(qn) == "bengal.core.site"

    def test_from_string(self) -> None:
        """Test QualifiedName.from_string factory."""
        qn = QualifiedName.from_string("bengal.core.site.Site")
        assert qn.parts == ("bengal", "core", "site", "Site")

    def test_from_string_filters_empty_parts(self) -> None:
        """Test that from_string filters empty parts."""
        # Leading dots
        qn = QualifiedName.from_string("...bengal.core")
        assert qn.parts == ("bengal", "core")

        # Trailing dots
        qn = QualifiedName.from_string("bengal.core...")
        assert qn.parts == ("bengal", "core")

        # Middle empty parts
        qn = QualifiedName.from_string("bengal..core")
        assert qn.parts == ("bengal", "core")

    def test_name_property(self) -> None:
        """Test QualifiedName.name property returns last part."""
        qn = QualifiedName.from_string("bengal.core.site.Site")
        assert qn.name == "Site"

    def test_parent_property(self) -> None:
        """Test QualifiedName.parent property."""
        qn = QualifiedName.from_string("bengal.core.site.Site")
        parent = qn.parent
        assert parent is not None
        assert str(parent) == "bengal.core.site"

        # Parent of parent
        grandparent = parent.parent
        assert grandparent is not None
        assert str(grandparent) == "bengal.core"

    def test_parent_of_single_part_is_none(self) -> None:
        """Test that top-level name has no parent."""
        qn = QualifiedName(parts=("bengal",))
        assert qn.parent is None

    def test_rejects_empty_parts_tuple(self) -> None:
        """Test that empty parts tuple raises ValueError."""
        with pytest.raises(ValueError, match="QualifiedName cannot be empty"):
            QualifiedName(parts=())

    def test_rejects_empty_string_in_parts(self) -> None:
        """Test that empty string in parts raises ValueError."""
        with pytest.raises(ValueError, match="QualifiedName contains empty part"):
            QualifiedName(parts=("bengal", "", "core"))

    def test_from_string_all_empty_raises(self) -> None:
        """Test that from_string with all empty parts raises ValueError."""
        with pytest.raises(ValueError, match="QualifiedName cannot be empty"):
            QualifiedName.from_string("...")

    def test_frozen(self) -> None:
        """Test that QualifiedName is frozen (immutable)."""
        qn = QualifiedName(parts=("bengal",))
        with pytest.raises(AttributeError):
            qn.parts = ("other",)  # type: ignore[misc]

    def test_hashable(self) -> None:
        """Test that QualifiedName is hashable."""
        qn1 = QualifiedName.from_string("bengal.core")
        qn2 = QualifiedName.from_string("bengal.core")
        qn3 = QualifiedName.from_string("bengal.cli")

        # Same values should be equal and have same hash
        assert qn1 == qn2
        assert hash(qn1) == hash(qn2)

        # Different values should be unequal
        assert qn1 != qn3

        # Should be usable in sets
        names = {qn1, qn2, qn3}
        assert len(names) == 2

    def test_str_representation(self) -> None:
        """Test __str__ returns dot-separated string."""
        qn = QualifiedName(parts=("a", "b", "c"))
        assert str(qn) == "a.b.c"

    def test_custom_separator(self) -> None:
        """Test from_string with custom separator."""
        qn = QualifiedName.from_string("a/b/c", separator="/")
        assert qn.parts == ("a", "b", "c")
        assert str(qn) == "a.b.c"  # str always uses dots

