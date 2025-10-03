"""Tests for math template functions."""

import pytest
from bengal.rendering.template_functions.math_functions import (
    percentage,
    times,
    divided_by,
    ceil_filter,
    floor_filter,
    round_filter,
)


class TestPercentage:
    """Tests for percentage filter."""
    
    def test_basic_percentage(self):
        assert percentage(50, 200) == "25%"
    
    def test_percentage_with_decimals(self):
        assert percentage(1, 3, decimals=2) == "33.33%"
    
    def test_percentage_zero_total(self):
        assert percentage(50, 0) == "0%"
    
    def test_percentage_100_percent(self):
        assert percentage(100, 100) == "100%"
    
    def test_percentage_over_100(self):
        assert percentage(150, 100) == "150%"
    
    def test_percentage_invalid_types(self):
        assert percentage("abc", 100) == "0%"


class TestTimes:
    """Tests for times filter."""
    
    def test_multiply_integers(self):
        assert times(5, 3) == 15.0
    
    def test_multiply_floats(self):
        assert times(2.5, 4.0) == 10.0
    
    def test_multiply_by_zero(self):
        assert times(10, 0) == 0.0
    
    def test_multiply_negative(self):
        assert times(5, -2) == -10.0
    
    def test_invalid_types(self):
        assert times("abc", 5) == 0


class TestDividedBy:
    """Tests for divided_by filter."""
    
    def test_divide_integers(self):
        assert divided_by(10, 2) == 5.0
    
    def test_divide_floats(self):
        assert divided_by(7.5, 2.5) == 3.0
    
    def test_divide_by_zero(self):
        assert divided_by(10, 0) == 0
    
    def test_divide_negative(self):
        assert divided_by(10, -2) == -5.0
    
    def test_invalid_types(self):
        assert divided_by("abc", 5) == 0


class TestCeilFilter:
    """Tests for ceil filter."""
    
    def test_ceil_positive(self):
        assert ceil_filter(4.2) == 5
    
    def test_ceil_negative(self):
        assert ceil_filter(-4.2) == -4
    
    def test_ceil_integer(self):
        assert ceil_filter(5) == 5
    
    def test_ceil_zero(self):
        assert ceil_filter(0) == 0
    
    def test_invalid_type(self):
        assert ceil_filter("abc") == 0


class TestFloorFilter:
    """Tests for floor filter."""
    
    def test_floor_positive(self):
        assert floor_filter(4.9) == 4
    
    def test_floor_negative(self):
        assert floor_filter(-4.2) == -5
    
    def test_floor_integer(self):
        assert floor_filter(5) == 5
    
    def test_floor_zero(self):
        assert floor_filter(0) == 0
    
    def test_invalid_type(self):
        assert floor_filter("abc") == 0


class TestRoundFilter:
    """Tests for round filter."""
    
    def test_round_no_decimals(self):
        assert round_filter(4.5) == 4  # Python's round() uses banker's rounding
    
    def test_round_one_decimal(self):
        assert round_filter(4.567, 1) == 4.6
    
    def test_round_two_decimals(self):
        assert round_filter(4.567, 2) == 4.57
    
    def test_round_negative(self):
        assert round_filter(-4.567, 1) == -4.6
    
    def test_round_integer(self):
        assert round_filter(5, 2) == 5
    
    def test_invalid_type(self):
        assert round_filter("abc") == 0

