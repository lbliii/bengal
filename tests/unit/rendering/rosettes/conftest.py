"""Shared pytest fixtures for Rosettes tests."""

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from bengal.rendering.rosettes import Token, get_lexer, list_languages

if TYPE_CHECKING:
    pass

# Test fixtures directory
FIXTURES_DIR = Path(__file__).parent / "fixtures"


@pytest.fixture(scope="session")
def fixtures_dir() -> Path:
    """Return the fixtures directory path."""
    return FIXTURES_DIR


@pytest.fixture(scope="session")
def all_languages() -> list[str]:
    """Return list of all supported languages."""
    return list_languages()


@pytest.fixture
def python_lexer():
    """Get Python lexer instance."""
    return get_lexer("python")


@pytest.fixture
def javascript_lexer():
    """Get JavaScript lexer instance."""
    return get_lexer("javascript")


@pytest.fixture
def rust_lexer():
    """Get Rust lexer instance."""
    return get_lexer("rust")


@pytest.fixture
def kida_lexer():
    """Get Kida lexer instance."""
    return get_lexer("kida")


def load_fixture(language: str, fixture_name: str) -> tuple[str, list[dict]]:
    """Load a test fixture.

    Args:
        language: Language name (e.g., 'python').
        fixture_name: Fixture name without extension (e.g., 'keywords').

    Returns:
        Tuple of (input_code, expected_tokens) where expected_tokens is a list
        of dicts with 'type', 'value', 'line', 'column' keys.
    """
    lang_dir = FIXTURES_DIR / language
    input_file = lang_dir / f"{fixture_name}.{_get_extension(language)}"
    tokens_file = lang_dir / f"{fixture_name}.tokens"

    if not input_file.exists():
        raise FileNotFoundError(f"Fixture input not found: {input_file}")

    input_code = input_file.read_text(encoding="utf-8")

    if tokens_file.exists():
        expected_tokens = json.loads(tokens_file.read_text(encoding="utf-8"))
    else:
        # No expected tokens file - return empty list (test will generate)
        expected_tokens = []

    return input_code, expected_tokens


def _get_extension(language: str) -> str:
    """Get file extension for a language."""
    extensions = {
        "python": "py",
        "javascript": "js",
        "typescript": "ts",
        "rust": "rs",
        "go": "go",
        "kida": "kida",
        "html": "html",
        "css": "css",
        "yaml": "yml",
        "json": "json",
        "bash": "sh",
        "sql": "sql",
        "markdown": "md",
    }
    return extensions.get(language, "txt")


def tokens_to_dict(tokens: list[Token]) -> list[dict]:
    """Convert Token objects to dicts for comparison."""
    return [
        {
            "type": token.type.value,
            "value": token.value,
            "line": token.line,
            "column": token.column,
        }
        for token in tokens
    ]


def assert_tokens_match(
    actual: list[Token],
    expected: list[dict],
    *,
    fuzzy_boundaries: bool = False,
    tolerance: int = 1,
) -> None:
    """Assert that actual tokens match expected tokens.

    Args:
        actual: List of actual Token objects.
        expected: List of expected token dicts.
        fuzzy_boundaries: If True, allow ±tolerance character boundary differences.
        tolerance: Character tolerance for fuzzy matching.
    """
    actual_dicts = tokens_to_dict(actual)

    if len(actual_dicts) != len(expected):
        # Show first few differences
        diff_msg = f"Token count mismatch: {len(actual_dicts)} != {len(expected)}\n"
        diff_msg += f"First 5 actual: {actual_dicts[:5]}\n"
        diff_msg += f"First 5 expected: {expected[:5]}"
        raise AssertionError(diff_msg)

    for i, (actual_token, expected_token) in enumerate(zip(actual_dicts, expected, strict=True)):
        if fuzzy_boundaries:
            # Allow tolerance in column/line positions
            if actual_token["type"] != expected_token["type"]:
                raise AssertionError(
                    f"Token {i}: type mismatch: {actual_token['type']} != {expected_token['type']}"
                )
            if actual_token["value"] != expected_token["value"]:
                raise AssertionError(
                    f"Token {i}: value mismatch: {actual_token['value']} != {expected_token['value']}"
                )
            # Check column within tolerance
            col_diff = abs(actual_token["column"] - expected_token["column"])
            if col_diff > tolerance:
                raise AssertionError(
                    f"Token {i}: column out of tolerance: {actual_token['column']} vs {expected_token['column']}"
                )
        else:
            # Strict matching
            assert actual_token == expected_token, (
                f"Token {i} mismatch: {actual_token} != {expected_token}"
            )
