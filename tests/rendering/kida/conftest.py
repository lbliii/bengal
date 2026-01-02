"""Pytest configuration and fixtures for Kida tests."""

import pytest

from bengal.rendering.kida import DictLoader, Environment


@pytest.fixture
def env():
    """Create a basic Kida Environment."""
    return Environment()


@pytest.fixture
def env_autoescape():
    """Create a Kida Environment with autoescape enabled."""
    return Environment(autoescape=True)


@pytest.fixture
def env_trim():
    """Create a Kida Environment with trim_blocks enabled."""
    return Environment(trim_blocks=True)


@pytest.fixture
def env_with_loader():
    """Create a Kida Environment with DictLoader and test templates."""
    loader = DictLoader(
        {
            "base.html": (
                "<html>"
                "<head>{% block head %}{% endblock %}</head>"
                "<body>{% block body %}{% endblock %}</body>"
                "</html>"
            ),
            "child.html": ('{% extends "base.html" %}{% block body %}Hello World{% endblock %}'),
            "partial.html": "<p>Partial content</p>",
            "macros.html": (
                "{% def greet(name) %}Hello {{ name }}{% end %}"
                "{% def add(a, b) %}{{ a + b }}{% end %}"
            ),
        }
    )
    return Environment(loader=loader)


def assert_template_equal(template_result: str, expected: str) -> None:
    """Assert template result equals expected, normalizing whitespace.

    Args:
        template_result: The actual template rendering result.
        expected: The expected output.
    """
    # Normalize whitespace for comparison
    actual_normalized = " ".join(template_result.split())
    expected_normalized = " ".join(expected.split())
    assert actual_normalized == expected_normalized, (
        f"Template output mismatch:\n"
        f"  Actual: {actual_normalized!r}\n"
        f"  Expected: {expected_normalized!r}"
    )


def assert_contains(template_result: str, *expected_parts: str) -> None:
    """Assert template result contains all expected parts.

    Args:
        template_result: The actual template rendering result.
        expected_parts: Strings that should all be present in the result.
    """
    for part in expected_parts:
        assert part in template_result, (
            f"Template output missing expected content:\n"
            f"  Missing: {part!r}\n"
            f"  Actual: {template_result!r}"
        )
