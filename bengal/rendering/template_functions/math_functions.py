"""
Math functions for templates.

Provides 6 essential mathematical operations for calculations in templates.
"""

from __future__ import annotations

import math
from typing import TYPE_CHECKING

from bengal.config.utils import coerce_int
from bengal.rendering.utils.template_safe import template_safe

if TYPE_CHECKING:
    from bengal.protocols import SiteLike, TemplateEnvironment

type Number = int | float


def register(env: TemplateEnvironment, site: SiteLike) -> None:
    """Register functions with template environment."""
    env.filters.update(
        {
            "percentage": percentage,
            "times": times,
            "divided_by": divided_by,
            "ceil": ceil_filter,
            "floor": floor_filter,
            "round": round_filter,
            "coerce_int": coerce_int_filter,
        }
    )


def coerce_int_filter(value: object, default: int = 0) -> int:
    """
    Coerce value to int for template expressions (YAML/config may pass strings).

    Example:
        {{ (excerpt_words | coerce_int(150)) // 2 }}
    """
    return coerce_int(value, default)


@template_safe(
    default="0%",
    exceptions=(TypeError, ValueError, ZeroDivisionError),
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
    pct = (float(part) / float(total)) * 100
    return f"{pct:.{decimals}f}%"


@template_safe(default=0)
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
    return float(value) * float(multiplier)


@template_safe(default=0, exceptions=(TypeError, ValueError, ZeroDivisionError))
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
    divisor_f = float(divisor)
    if divisor_f == 0:
        return 0
    return float(value) / divisor_f


@template_safe(default=0)
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
    return math.ceil(float(value))


@template_safe(default=0)
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
    return math.floor(float(value))


@template_safe(default=0)
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
    return round(float(value), decimals)
