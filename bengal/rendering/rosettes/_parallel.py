"""Parallel tokenization for free-threaded Python (3.14t+).

Enables true parallel tokenization of large files by splitting at safe
boundaries and processing chunks concurrently.
"""

from __future__ import annotations

import sys
from collections.abc import Iterator
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from typing import TYPE_CHECKING

from bengal.rendering.rosettes._types import Token

if TYPE_CHECKING:
    from bengal.rendering.rosettes.lexers._state_machine import StateMachineLexer

__all__ = ["tokenize_parallel", "is_free_threaded"]


def is_free_threaded() -> bool:
    """Check if running on free-threaded Python (3.14t+).

    Returns:
        True if running without GIL, False otherwise.
    """
    # Python 3.13+ has sys._is_gil_enabled()
    if hasattr(sys, "_is_gil_enabled"):
        return not sys._is_gil_enabled()
    return False


@dataclass(frozen=True, slots=True)
class _Chunk:
    """A chunk of source code with position metadata."""

    text: str
    start_offset: int
    start_line: int


def _find_safe_splits(code: str, target_chunk_size: int) -> list[int]:
    """Find safe split points (newlines) for parallel tokenization.

    We split at newlines to avoid splitting in the middle of tokens.
    This is a heuristic that works for most languages.

    Args:
        code: Source code to split.
        target_chunk_size: Target size for each chunk.

    Returns:
        List of positions to split at.
    """
    splits: list[int] = []
    pos = target_chunk_size

    while pos < len(code):
        # Find nearest newline before or at target
        newline_pos = code.rfind("\n", max(0, pos - target_chunk_size // 2), pos)

        if newline_pos == -1:
            # No newline found before target, look after
            newline_pos = code.find("\n", pos)
            if newline_pos == -1:
                break

        split_pos = newline_pos + 1  # Split after newline

        if split_pos > (splits[-1] if splits else 0):
            splits.append(split_pos)

        pos = split_pos + target_chunk_size

    return splits


def _make_chunks(code: str, splits: list[int]) -> list[_Chunk]:
    """Split code into chunks at the given positions.

    Args:
        code: Source code to split.
        splits: List of positions to split at.

    Returns:
        List of Chunk objects with metadata.
    """
    chunks: list[_Chunk] = []
    prev = 0
    line = 1

    for split_pos in splits:
        chunk_text = code[prev:split_pos]
        chunks.append(
            _Chunk(
                text=chunk_text,
                start_offset=prev,
                start_line=line,
            )
        )
        line += chunk_text.count("\n")
        prev = split_pos

    # Final chunk
    if prev < len(code):
        chunks.append(
            _Chunk(
                text=code[prev:],
                start_offset=prev,
                start_line=line,
            )
        )

    return chunks


def tokenize_parallel(
    lexer: StateMachineLexer,
    code: str,
    *,
    chunk_size: int = 64_000,
    max_workers: int | None = None,
) -> Iterator[Token]:
    """Parallel tokenization for large files.

    Only beneficial on free-threaded Python (3.14t+).
    Falls back to sequential on GIL Python.

    Args:
        lexer: The lexer to use.
        code: Source code to tokenize.
        chunk_size: Target chunk size in characters.
        max_workers: Maximum threads. None = CPU count.

    Yields:
        Tokens in order of appearance.
    """
    # Small files or GIL Python: sequential
    if len(code) < chunk_size * 2 or not is_free_threaded():
        yield from lexer.tokenize(code)
        return

    # Split at newlines
    splits = _find_safe_splits(code, chunk_size)

    if not splits:
        yield from lexer.tokenize(code)
        return

    chunks = _make_chunks(code, splits)

    def process_chunk(chunk: _Chunk) -> list[Token]:
        tokens = list(lexer.tokenize(chunk.text))
        # Adjust line numbers for chunks after the first
        if chunk.start_line > 1:
            return [
                Token(
                    type=t.type,
                    value=t.value,
                    line=t.line + chunk.start_line - 1,
                    column=t.column,
                )
                for t in tokens
            ]
        return tokens

    # Tokenize in parallel
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        results = list(executor.map(process_chunk, chunks))

    # Yield in order
    for chunk_tokens in results:
        yield from chunk_tokens
