"""
Unit tests for error codes module.

These tests verify the integrity of the ErrorCode enum and lookup functions.
Added after discovering duplicate value bug (G005/V006 both had "graph_analysis_failed").

See Also:
- bengal/errors/codes.py
"""

from __future__ import annotations

import pytest

from bengal.errors.codes import ErrorCode, get_codes_by_category, get_error_code_by_name


class TestErrorCodeUniqueness:
    """Tests ensuring all error codes have unique values."""

    def test_all_error_code_values_are_unique(self) -> None:
        """Each ErrorCode must have a unique value to avoid enum aliasing."""
        values = [code.value for code in ErrorCode]
        duplicates = [v for v in set(values) if values.count(v) > 1]

        if duplicates:
            # Find which codes share the duplicate values
            duplicate_codes = []
            for dup_value in duplicates:
                codes_with_value = [c.name for c in ErrorCode if c.value == dup_value]
                duplicate_codes.append(f"{dup_value!r}: {codes_with_value}")

            pytest.fail(
                "Found duplicate ErrorCode values (causes enum aliasing):\n"
                + "\n".join(f"  • {d}" for d in duplicate_codes)
            )

    def test_all_error_code_names_are_unique(self) -> None:
        """Each ErrorCode must have a unique name."""
        names = [code.name for code in ErrorCode]
        assert len(names) == len(set(names)), "Duplicate ErrorCode names found"

    def test_no_enum_aliases_exist(self) -> None:
        """Verify no enum members are aliases of other members."""
        seen_values: dict[str, str] = {}
        aliases: list[str] = []

        for code in ErrorCode:
            if code.value in seen_values:
                aliases.append(f"{code.name} is alias of {seen_values[code.value]}")
            else:
                seen_values[code.value] = code.name

        if aliases:
            pytest.fail(
                "Found enum aliases (duplicate values):\n" + "\n".join(f"  • {a}" for a in aliases)
            )


class TestErrorCodeCategories:
    """Tests for error code category properties."""

    def test_all_codes_have_valid_category(self) -> None:
        """Every error code should map to a known category."""
        valid_categories = {
            "config",
            "content",
            "rendering",
            "discovery",
            "cache",
            "server",
            "template_function",
            "parsing",
            "asset",
            "graph",
            "autodoc",
            "validator",
            "build",
        }

        for code in ErrorCode:
            assert code.category in valid_categories, (
                f"{code.name} has unknown category: {code.category}"
            )

    def test_code_prefix_matches_category(self) -> None:
        """Error code prefix letter should match its category."""
        prefix_to_category = {
            "C": "config",
            "N": "content",
            "R": "rendering",
            "D": "discovery",
            "A": "cache",
            "S": "server",
            "T": "template_function",
            "P": "parsing",
            "X": "asset",
            "G": "graph",
            "O": "autodoc",
            "V": "validator",
            "B": "build",
        }

        for code in ErrorCode:
            prefix = code.name[0]
            expected_category = prefix_to_category.get(prefix)
            assert expected_category is not None, f"Unknown prefix {prefix} in {code.name}"
            assert code.category == expected_category, (
                f"{code.name} has category {code.category!r}, "
                f"expected {expected_category!r} based on prefix"
            )


class TestErrorCodeLookup:
    """Tests for error code lookup functions."""

    def test_lookup_by_code_name(self) -> None:
        """Can look up error code by its name (e.g., 'R001')."""
        code = get_error_code_by_name("R001")
        assert code == ErrorCode.R001

    def test_lookup_by_code_name_case_insensitive(self) -> None:
        """Lookup by name is case insensitive."""
        assert get_error_code_by_name("r001") == ErrorCode.R001
        assert get_error_code_by_name("R001") == ErrorCode.R001

    def test_lookup_by_value(self) -> None:
        """Can look up error code by its value."""
        code = get_error_code_by_name("template_not_found")
        assert code == ErrorCode.R001

    def test_lookup_nonexistent_returns_none(self) -> None:
        """Looking up nonexistent code returns None."""
        assert get_error_code_by_name("NONEXISTENT") is None
        assert get_error_code_by_name("fake_error_value") is None

    def test_get_codes_by_category(self) -> None:
        """Can get all codes in a category."""
        rendering_codes = get_codes_by_category("rendering")
        assert len(rendering_codes) > 0
        assert all(c.category == "rendering" for c in rendering_codes)
        assert ErrorCode.R001 in rendering_codes

    def test_get_codes_by_invalid_category(self) -> None:
        """Getting codes for invalid category returns empty list."""
        codes = get_codes_by_category("nonexistent_category")
        assert codes == []


class TestErrorCodeProperties:
    """Tests for error code property methods."""

    def test_docs_url_format(self) -> None:
        """docs_url returns correctly formatted URL."""
        assert ErrorCode.R001.docs_url == "/docs/reference/errors/#r001"
        assert ErrorCode.C001.docs_url == "/docs/reference/errors/#c001"

    def test_subsystem_mapping(self) -> None:
        """subsystem returns the correct Bengal package."""
        assert ErrorCode.R001.subsystem == "rendering"
        assert ErrorCode.C001.subsystem == "config"
        assert ErrorCode.B001.subsystem == "orchestration"

    def test_str_returns_name(self) -> None:
        """String representation is the code name."""
        assert str(ErrorCode.R001) == "R001"
        assert str(ErrorCode.C001) == "C001"
