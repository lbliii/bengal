"""
Math functions for templates.

Provides 6 essential mathematical operations for calculations in templates.
"""

from __future__ import annotations

import math
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from jinja2 import Environment

    from bengal.core.site import Site

type Number = int | float


def register(env: Environment, site: Site) -> None:
    """Register math functions with Jinja2 environment."""
    env.filters.update(
        {
            "percentage": percentage,
            "times": times,
            "divided_by": divided_by,
            "ceil": ceil_filter,
            "floor": floor_filter,
            "round": round_filter,
        }
    )


def percentage(part: Number, total: Number, decimals: int = 0) -> str:
    """
    Calculate percentage.

    Args:
        part: Part value
        total: Total value
        decimals: Number of decimal places (default: 0)

    Returns:
        Formatted percentage string with % sign

    Example:
        {{ completed | percentage(total_tasks) }}  # "75%"
        {{ score | percentage(max_score, 2) }}     # "87.50%"
    """
    if total == 0:
        return "0%"

    try:
        pct = (float(part) / float(total)) * 100
        return f"{pct:.{decimals}f}%"
    except (TypeError, ValueError, ZeroDivisionError):
        return "0%"


def times(value: Number, multiplier: Number) -> Number:
    """
    Multiply value by multiplier.

    Args:
        value: Value to multiply
        multiplier: Multiplier

    Returns:
        Product

    Example:
        {{ price | times(1.1) }}  # Add 10% tax
        {{ count | times(5) }}     # Multiply by 5
    """
    try:
        return float(value) * float(multiplier)
    except (TypeError, ValueError):
        return 0


def divided_by(value: Number, divisor: Number) -> Number:
    """
    Divide value by divisor.

    Args:
        value: Value to divide
        divisor: Divisor

    Returns:
        Quotient (0 if divisor is 0)

    Example:
        {{ total | divided_by(count) }}       # Average
        {{ seconds | divided_by(60) }}        # Convert to minutes
    """
    if divisor == 0:
        return 0

    try:
        return float(value) / float(divisor)
    except (TypeError, ValueError):
        return 0


def ceil_filter(value: Number) -> int:
    """
    Round up to nearest integer.

    Args:
        value: Value to round

    Returns:
        Ceiling value

    Example:
        {{ 4.2 | ceil }}   # 5
        {{ 4.9 | ceil }}   # 5
    """
    try:
        return math.ceil(float(value))
    except (TypeError, ValueError):
        return 0


def floor_filter(value: Number) -> int:
    """
    Round down to nearest integer.

    Args:
        value: Value to round

    Returns:
        Floor value

    Example:
        {{ 4.2 | floor }}  # 4
        {{ 4.9 | floor }}  # 4
    """
    try:
        return math.floor(float(value))
    except (TypeError, ValueError):
        return 0


def round_filter(value: Number, decimals: int = 0) -> Number:
    """
    Round to specified decimal places.

    Args:
        value: Value to round
        decimals: Number of decimal places (default: 0)

    Returns:
        Rounded value

    Example:
        {{ 4.567 | round }}     # 5
        {{ 4.567 | round(2) }}  # 4.57
        {{ 4.567 | round(1) }}  # 4.6
    """
    try:
        return round(float(value), decimals)
    except (TypeError, ValueError):
        return 0
