"""O(n) string accumulator (copied from the patitas/kida StringBuilder pattern).

Appends to a list and joins once, avoiding O(n^2) repeated concatenation.
Instances are local to a single serialize call — no shared mutable state.
"""


class StringBuilder:
    """Efficient string accumulator."""

    __slots__ = ("_parts",)

    def __init__(self) -> None:
        self._parts: list[str] = []

    def append(self, s: str) -> None:
        """Append ``s`` (empty strings are skipped)."""
        if s:
            self._parts.append(s)

    def build(self) -> str:
        """Join all appended parts into the final string."""
        return "".join(self._parts)
