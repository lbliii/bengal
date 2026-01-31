"""
Tests for bengal/output/utils.py.

Tests cover:
- ANSI escape code constants
- HTTP status code color mappings
- HTTP method color mappings
- Helper functions for color lookups
"""

from __future__ import annotations

import pytest

from bengal.output.utils import (
    ANSI,
    DEFAULT_ANSI,
    DEFAULT_STYLE,
    METHOD_COLORS,
    STATUS_COLORS,
    get_method_ansi,
    get_method_style,
    get_status_ansi,
    get_status_category,
    get_status_style,
)


class TestANSIConstants:
    """Tests for ANSI escape code constants."""

    def test_reset_code(self):
        """RESET should be the standard ANSI reset sequence."""
        assert ANSI.RESET == "\033[0m"

    def test_bold_code(self):
        """BOLD should be the standard ANSI bold sequence."""
        assert ANSI.BOLD == "\033[1m"

    def test_dim_code(self):
        """DIM should be the bright black (gray) sequence."""
        assert ANSI.DIM == "\033[90m"

    def test_color_codes_are_valid_ansi(self):
        """All color codes should be valid ANSI escape sequences."""
        colors = [
            ANSI.GREEN,
            ANSI.CYAN,
            ANSI.YELLOW,
            ANSI.RED,
            ANSI.MAGENTA,
            ANSI.WHITE,
        ]
        for color in colors:
            assert color.startswith("\033[")
            assert color.endswith("m")

    def test_all_colors_are_unique(self):
        """Each color constant should have a unique value."""
        colors = {
            "GREEN": ANSI.GREEN,
            "CYAN": ANSI.CYAN,
            "YELLOW": ANSI.YELLOW,
            "RED": ANSI.RED,
            "MAGENTA": ANSI.MAGENTA,
            "WHITE": ANSI.WHITE,
            "DIM": ANSI.DIM,
        }
        values = list(colors.values())
        assert len(values) == len(set(values)), "Color codes should be unique"


class TestStatusColors:
    """Tests for HTTP status code color mappings."""

    def test_status_colors_has_all_categories(self):
        """STATUS_COLORS should have all HTTP status categories."""
        expected = {"2xx", "304", "3xx", "4xx", "5xx"}
        assert set(STATUS_COLORS.keys()) == expected

    def test_status_colors_are_tuples(self):
        """Each STATUS_COLORS entry should be (rich_style, ansi_code) tuple."""
        for category, value in STATUS_COLORS.items():
            assert isinstance(value, tuple), f"{category} should be tuple"
            assert len(value) == 2, f"{category} should have 2 elements"
            rich_style, ansi_code = value
            assert isinstance(rich_style, str), f"{category} rich_style should be str"
            assert isinstance(ansi_code, str), f"{category} ansi_code should be str"

    def test_2xx_is_green(self):
        """2xx status codes should map to green."""
        style, ansi = STATUS_COLORS["2xx"]
        assert style == "green"
        assert ansi == ANSI.GREEN

    def test_304_is_dim(self):
        """304 Not Modified should map to dim."""
        style, ansi = STATUS_COLORS["304"]
        assert style == "dim"
        assert ansi == ANSI.DIM

    def test_3xx_is_cyan(self):
        """3xx redirect codes should map to cyan."""
        style, ansi = STATUS_COLORS["3xx"]
        assert style == "cyan"
        assert ansi == ANSI.CYAN

    def test_4xx_is_yellow(self):
        """4xx client error codes should map to yellow."""
        style, ansi = STATUS_COLORS["4xx"]
        assert style == "yellow"
        assert ansi == ANSI.YELLOW

    def test_5xx_is_red(self):
        """5xx server error codes should map to red."""
        style, ansi = STATUS_COLORS["5xx"]
        assert style == "red"
        assert ansi == ANSI.RED


class TestMethodColors:
    """Tests for HTTP method color mappings."""

    def test_method_colors_has_common_methods(self):
        """METHOD_COLORS should have all common HTTP methods."""
        expected = {"GET", "POST", "PUT", "DELETE", "PATCH"}
        assert set(METHOD_COLORS.keys()) == expected

    def test_get_is_cyan(self):
        """GET method should map to cyan."""
        style, ansi = METHOD_COLORS["GET"]
        assert style == "cyan"
        assert ansi == ANSI.CYAN

    def test_post_is_yellow(self):
        """POST method should map to yellow."""
        style, ansi = METHOD_COLORS["POST"]
        assert style == "yellow"
        assert ansi == ANSI.YELLOW

    def test_put_is_magenta(self):
        """PUT method should map to magenta."""
        style, ansi = METHOD_COLORS["PUT"]
        assert style == "magenta"
        assert ansi == ANSI.MAGENTA

    def test_patch_is_magenta(self):
        """PATCH method should map to magenta (same as PUT)."""
        style, ansi = METHOD_COLORS["PATCH"]
        assert style == "magenta"
        assert ansi == ANSI.MAGENTA

    def test_delete_is_red(self):
        """DELETE method should map to red."""
        style, ansi = METHOD_COLORS["DELETE"]
        assert style == "red"
        assert ansi == ANSI.RED


class TestGetStatusCategory:
    """Tests for get_status_category() helper."""

    @pytest.mark.parametrize(
        ("status", "expected"),
        [
            ("200", "2xx"),
            ("201", "2xx"),
            ("204", "2xx"),
            ("299", "2xx"),
        ],
    )
    def test_2xx_category(self, status: str, expected: str):
        """2xx status codes should return '2xx' category."""
        assert get_status_category(status) == expected

    def test_304_special_case(self):
        """304 should return its own category (not 3xx)."""
        assert get_status_category("304") == "304"

    @pytest.mark.parametrize(
        ("status", "expected"),
        [
            ("301", "3xx"),
            ("302", "3xx"),
            ("307", "3xx"),
            ("308", "3xx"),
        ],
    )
    def test_3xx_category(self, status: str, expected: str):
        """3xx status codes (except 304) should return '3xx' category."""
        assert get_status_category(status) == expected

    @pytest.mark.parametrize(
        ("status", "expected"),
        [
            ("400", "4xx"),
            ("401", "4xx"),
            ("403", "4xx"),
            ("404", "4xx"),
            ("422", "4xx"),
            ("499", "4xx"),
        ],
    )
    def test_4xx_category(self, status: str, expected: str):
        """4xx status codes should return '4xx' category."""
        assert get_status_category(status) == expected

    @pytest.mark.parametrize(
        ("status", "expected"),
        [
            ("500", "5xx"),
            ("502", "5xx"),
            ("503", "5xx"),
            ("504", "5xx"),
        ],
    )
    def test_5xx_category(self, status: str, expected: str):
        """5xx status codes should return '5xx' category."""
        assert get_status_category(status) == expected

    @pytest.mark.parametrize(
        "status",
        [
            "100",  # 1xx informational
            "199",
            "600",  # Invalid
            "999",
        ],
    )
    def test_other_codes_return_default(self, status: str):
        """Non-2xx/3xx/4xx/5xx codes should return 'default'."""
        assert get_status_category(status) == "default"

    @pytest.mark.parametrize(
        "invalid",
        [
            "invalid",
            "",
            "abc",
            "20a",
            None,
        ],
    )
    def test_invalid_input_returns_default(self, invalid):
        """Invalid input should return 'default'."""
        assert get_status_category(invalid) == "default"


class TestGetStatusStyle:
    """Tests for get_status_style() function."""

    def test_200_returns_green(self):
        """200 OK should return 'green' style."""
        assert get_status_style("200") == "green"

    def test_304_returns_dim(self):
        """304 Not Modified should return 'dim' style."""
        assert get_status_style("304") == "dim"

    def test_301_returns_cyan(self):
        """301 Redirect should return 'cyan' style."""
        assert get_status_style("301") == "cyan"

    def test_404_returns_yellow(self):
        """404 Not Found should return 'yellow' style."""
        assert get_status_style("404") == "yellow"

    def test_500_returns_red(self):
        """500 Server Error should return 'red' style."""
        assert get_status_style("500") == "red"

    def test_invalid_returns_default(self):
        """Invalid status should return DEFAULT_STYLE."""
        assert get_status_style("invalid") == DEFAULT_STYLE


class TestGetStatusAnsi:
    """Tests for get_status_ansi() function."""

    def test_200_returns_green_ansi(self):
        """200 OK should return green ANSI code."""
        assert get_status_ansi("200") == ANSI.GREEN

    def test_304_returns_dim_ansi(self):
        """304 Not Modified should return dim ANSI code."""
        assert get_status_ansi("304") == ANSI.DIM

    def test_301_returns_cyan_ansi(self):
        """301 Redirect should return cyan ANSI code."""
        assert get_status_ansi("301") == ANSI.CYAN

    def test_404_returns_yellow_ansi(self):
        """404 Not Found should return yellow ANSI code."""
        assert get_status_ansi("404") == ANSI.YELLOW

    def test_500_returns_red_ansi(self):
        """500 Server Error should return red ANSI code."""
        assert get_status_ansi("500") == ANSI.RED

    def test_invalid_returns_empty(self):
        """Invalid status should return empty string."""
        assert get_status_ansi("invalid") == ""


class TestGetMethodStyle:
    """Tests for get_method_style() function."""

    def test_get_returns_cyan(self):
        """GET method should return 'cyan' style."""
        assert get_method_style("GET") == "cyan"

    def test_post_returns_yellow(self):
        """POST method should return 'yellow' style."""
        assert get_method_style("POST") == "yellow"

    def test_put_returns_magenta(self):
        """PUT method should return 'magenta' style."""
        assert get_method_style("PUT") == "magenta"

    def test_patch_returns_magenta(self):
        """PATCH method should return 'magenta' style."""
        assert get_method_style("PATCH") == "magenta"

    def test_delete_returns_red(self):
        """DELETE method should return 'red' style."""
        assert get_method_style("DELETE") == "red"

    def test_unknown_returns_default(self):
        """Unknown method should return DEFAULT_STYLE."""
        assert get_method_style("OPTIONS") == DEFAULT_STYLE
        assert get_method_style("HEAD") == DEFAULT_STYLE


class TestGetMethodAnsi:
    """Tests for get_method_ansi() function."""

    def test_get_returns_cyan_ansi(self):
        """GET method should return cyan ANSI code."""
        assert get_method_ansi("GET") == ANSI.CYAN

    def test_post_returns_yellow_ansi(self):
        """POST method should return yellow ANSI code."""
        assert get_method_ansi("POST") == ANSI.YELLOW

    def test_put_returns_magenta_ansi(self):
        """PUT method should return magenta ANSI code."""
        assert get_method_ansi("PUT") == ANSI.MAGENTA

    def test_delete_returns_red_ansi(self):
        """DELETE method should return red ANSI code."""
        assert get_method_ansi("DELETE") == ANSI.RED

    def test_unknown_returns_default_ansi(self):
        """Unknown method should return DEFAULT_ANSI."""
        assert get_method_ansi("OPTIONS") == DEFAULT_ANSI


class TestBackwardCompatibility:
    """Tests ensuring backward compatibility with colors.py re-exports."""

    def test_colors_module_exports_status_color_code(self):
        """colors.py should export get_status_color_code (alias for get_status_ansi)."""
        from bengal.output.colors import get_status_color_code

        assert get_status_color_code("200") == ANSI.GREEN
        assert get_status_color_code("404") == ANSI.YELLOW

    def test_colors_module_exports_status_style(self):
        """colors.py should export get_status_style."""
        from bengal.output.colors import get_status_style as colors_get_status_style

        assert colors_get_status_style("200") == "green"
        assert colors_get_status_style("500") == "red"

    def test_colors_module_exports_method_color_code(self):
        """colors.py should export get_method_color_code (alias for get_method_ansi)."""
        from bengal.output.colors import get_method_color_code

        assert get_method_color_code("GET") == ANSI.CYAN
        assert get_method_color_code("DELETE") == ANSI.RED

    def test_colors_module_exports_method_style(self):
        """colors.py should export get_method_style."""
        from bengal.output.colors import get_method_style as colors_get_method_style

        assert colors_get_method_style("GET") == "cyan"
        assert colors_get_method_style("POST") == "yellow"
