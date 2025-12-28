"""ReDoS prevention tests — verify O(n) time guarantee with pathological inputs."""

from __future__ import annotations

import time

import pytest

from bengal.rendering.rosettes import get_lexer, list_languages


@pytest.mark.slow
@pytest.mark.parametrize("language", list_languages())
def test_lexer_no_redos(language: str) -> None:
    """Lexer should complete in O(n) time for pathological input.

    All 54 lexers must pass this test to prevent ReDoS vulnerabilities.
    Uses 1s timeout to account for CI hardware variance.
    """
    from contextlib import suppress

    lexer = get_lexer(language)

    # Pathological patterns (language-agnostic)
    patterns = [
        '"' + '\\"' * 100 + "x",  # Repeated escapes
        "(" * 50 + "x" + ")" * 50,  # Deep nesting
        "/* " + "/* " * 20 + "x",  # Nested comments (if language supports)
        "a" + "+a" * 100,  # Repeated operators
    ]

    for pattern in patterns:
        start = time.perf_counter()
        with suppress(Exception):  # Error is OK, hang is not
            list(lexer.tokenize(pattern))
        elapsed = time.perf_counter() - start

        # O(n) means linear time; generous 1s timeout for CI variance
        assert elapsed < 1.0, f"{language}: {pattern[:50]}... took {elapsed:.3f}s"


def test_lexer_linear_scaling() -> None:
    """Verify doubling input size approximately doubles time (not exponential)."""
    lexer = get_lexer("python")

    small = "x = 1\n" * 1000  # 1K lines
    large = "x = 1\n" * 2000  # 2K lines

    start = time.perf_counter()
    list(lexer.tokenize(small))
    small_time = time.perf_counter() - start

    start = time.perf_counter()
    list(lexer.tokenize(large))
    large_time = time.perf_counter() - start

    # Large should be ~2x small (with tolerance), not exponential
    ratio = large_time / small_time if small_time > 0 else float("inf")
    assert ratio < 4.0, f"Scaling ratio {ratio:.2f}x suggests non-linear time"


@pytest.mark.parametrize("language", ["python", "javascript", "rust", "go"])
def test_pathological_string_patterns(language: str) -> None:
    """Test known ReDoS patterns for string lexers."""
    lexer = get_lexer(language)

    # Classic ReDoS: repeated escapes
    pathological = 'f"' + '\\"' * 50 + "x"

    start = time.perf_counter()
    list(lexer.tokenize(pathological))
    elapsed = time.perf_counter() - start

    # O(n) means ~linear scaling
    # For 100 chars, should complete in < 100ms
    assert elapsed < 0.1, f"{language}: Took {elapsed:.3f}s — possible ReDoS"


@pytest.mark.parametrize("language", ["python", "javascript", "rust"])
def test_nested_comment_explosion(language: str) -> None:
    """Test nested comment patterns that can cause exponential backtracking."""
    lexer = get_lexer(language)

    # Deeply nested comments (if language supports)
    if language in ["rust", "c", "cpp"]:
        pathological = "/* " * 20 + "x"

        start = time.perf_counter()
        list(lexer.tokenize(pathological))
        elapsed = time.perf_counter() - start

        assert elapsed < 0.1, f"{language}: Nested comments took {elapsed:.3f}s"
