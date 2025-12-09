"""
Advanced collection manipulation functions for templates.

Provides 3 advanced functions for working with lists.
"""

from __future__ import annotations

import random
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from jinja2 import Environment

    from bengal.core.site import Site


def register(env: Environment, site: Site) -> None:
    """Register advanced collection functions with Jinja2 environment."""
    env.filters.update(
        {
            "sample": sample,
            "shuffle": shuffle,
            "chunk": chunk,
        }
    )


def sample(items: list[Any], count: int = 1, seed: int | None = None) -> list[Any]:
    """
    Get random sample of items.

    Args:
        items: List to sample from
        count: Number of items to sample (default: 1)
        seed: Random seed for reproducibility (optional)

    Returns:
        Random sample of items

    Example:
        {% set featured = posts | sample(3) %}
        {% for post in featured %}
            {{ post.title }}
        {% endfor %}
    """
    if not items:
        return []

    if count >= len(items):
        return items.copy()

    if seed is not None:
        random.seed(seed)

    return random.sample(items, min(count, len(items)))


def shuffle(items: list[Any], seed: int | None = None) -> list[Any]:
    """
    Shuffle items randomly.

    Args:
        items: List to shuffle
        seed: Random seed for reproducibility (optional)

    Returns:
        Shuffled copy of list

    Example:
        {% set random_posts = posts | shuffle %}
    """
    if not items:
        return []

    result = items.copy()

    if seed is not None:
        random.seed(seed)

    random.shuffle(result)
    return result


def chunk(items: list[Any], size: int) -> list[list[Any]]:
    """
    Split list into chunks of specified size.

    Args:
        items: List to chunk
        size: Chunk size

    Returns:
        List of chunks

    Example:
        {% for row in items | chunk(3) %}
            <div class="row">
            {% for item in row %}
                <div class="col">{{ item }}</div>
            {% endfor %}
            </div>
        {% endfor %}
    """
    if not items or size <= 0:
        return []

    return [items[i : i + size] for i in range(0, len(items), size)]
