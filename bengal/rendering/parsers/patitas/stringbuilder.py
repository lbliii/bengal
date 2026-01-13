"""StringBuilder for O(n) string accumulation.

Adopts kida's proven StringBuilder pattern for efficient HTML output.
Appends to a list, joins once at the end: O(n) total vs O(n²) for
repeated string concatenation.

Thread Safety:
StringBuilder instances are local to each render() call.
No shared mutable state.

Performance:
For a 1000-line document with 500 rendered fragments:
- String concatenation: ~125,000 character copies
- StringBuilder: ~25,000 character copies (5x faster)

"""

from __future__ import annotations


class StringBuilder:
    """Efficient string accumulator.
    
    Appends to a list, joins once at the end.
    O(n) total vs O(n²) for repeated string concatenation.
    
    Usage:
            >>> sb = StringBuilder()
            >>> sb.append("<h1>")
            >>> sb.append("Hello")
            >>> sb.append("</h1>")
            >>> sb.build()
            '<h1>Hello</h1>'
    
    Thread Safety:
        Instance is local to each render() call.
        No shared mutable state.
        
    """

    __slots__ = ("_parts",)

    def __init__(self) -> None:
        """Initialize empty StringBuilder."""
        self._parts: list[str] = []

    def append(self, s: str) -> StringBuilder:
        """Append a string to the builder.

        Args:
            s: String to append (empty strings are skipped)

        Returns:
            self for method chaining
        """
        if s:
            self._parts.append(s)
        return self

    def append_line(self, s: str = "") -> StringBuilder:
        """Append a string followed by newline.

        Args:
            s: String to append (empty = just newline)

        Returns:
            self for method chaining
        """
        if s:
            self._parts.append(s)
        self._parts.append("\n")
        return self

    def extend(self, strings: list[str]) -> StringBuilder:
        """Append multiple strings at once.

        Args:
            strings: List of strings to append

        Returns:
            self for method chaining
        """
        self._parts.extend(s for s in strings if s)
        return self

    def build(self) -> str:
        """Join all parts into final string.

        Returns:
            Concatenated string of all appended parts
        """
        return "".join(self._parts)

    def clear(self) -> StringBuilder:
        """Clear all accumulated parts.

        Returns:
            self for method chaining
        """
        self._parts.clear()
        return self

    def __len__(self) -> int:
        """Return number of parts (not total length)."""
        return len(self._parts)

    def __bool__(self) -> bool:
        """Return True if any parts have been appended."""
        return bool(self._parts)
