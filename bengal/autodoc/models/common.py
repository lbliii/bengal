"""
Common types for autodoc typed metadata.

Provides shared types used across all metadata domains:
- SourceLocation: Source code location for a documented element
- QualifiedName: Validated qualified name for a documented element
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class SourceLocation:
    """
    Source code location for a documented element.

    Attributes:
        file: Path to source file (string for serializability)
        line: Line number (1-based)
        column: Column number (optional, 1-based)

    Example:
        >>> loc = SourceLocation(file="bengal/core/site.py", line=45)
        >>> loc.file
        'bengal/core/site.py'
    """

    file: str
    line: int
    column: int | None = None

    def __post_init__(self) -> None:
        """Validate line number is positive."""
        from bengal.errors import BengalError

        if self.line < 1:
            raise BengalError(
                f"Line must be >= 1, got {self.line}",
                suggestion="Line numbers must be 1-based (first line is 1)",
            )
        if self.column is not None and self.column < 1:
            raise BengalError(
                f"Column must be >= 1, got {self.column}",
                suggestion="Column numbers must be 1-based (first column is 1)",
            )

    @classmethod
    def from_path(cls, path: Path, line: int, column: int | None = None) -> SourceLocation:
        """
        Create from Path object.

        Args:
            path: Path to source file
            line: Line number (1-based)
            column: Column number (optional, 1-based)

        Returns:
            SourceLocation instance
        """
        return cls(file=str(path), line=line, column=column)


@dataclass(frozen=True, slots=True)
class QualifiedName:
    """
    Validated qualified name for a documented element.

    Ensures qualified names don't have empty parts (e.g., from
    malformed module paths like "...bengal.core").

    Attributes:
        parts: Tuple of name parts (non-empty strings)

    Example:
        >>> qn = QualifiedName.from_string("bengal.core.site.Site")
        >>> qn.parts
        ('bengal', 'core', 'site', 'Site')
        >>> qn.name
        'Site'
        >>> str(qn)
        'bengal.core.site.Site'
    """

    parts: tuple[str, ...]

    def __post_init__(self) -> None:
        """Validate parts are non-empty."""
        if not self.parts:
            from bengal.errors import BengalError

            raise BengalError(
                "QualifiedName cannot be empty",
                suggestion="Provide at least one name part",
            )
        for part in self.parts:
            if not part:
                from bengal.errors import BengalError

                raise BengalError(
                    f"QualifiedName contains empty part: {self.parts}",
                    suggestion="Remove empty parts from qualified name",
                )

    @classmethod
    def from_string(cls, qualified_name: str, separator: str = ".") -> QualifiedName:
        """
        Create from dot-separated string, filtering empty parts.

        Args:
            qualified_name: Dot-separated qualified name
            separator: Part separator (default: ".")

        Returns:
            QualifiedName instance

        Example:
            >>> QualifiedName.from_string("...bengal.core")
            QualifiedName(parts=('bengal', 'core'))
        """
        parts = tuple(p for p in qualified_name.split(separator) if p)
        return cls(parts=parts)

    def __str__(self) -> str:
        """Return dot-separated string representation."""
        return ".".join(self.parts)

    @property
    def name(self) -> str:
        """
        Last part of the qualified name.

        Example:
            >>> QualifiedName.from_string("bengal.core.Site").name
            'Site'
        """
        return self.parts[-1]

    @property
    def parent(self) -> QualifiedName | None:
        """
        Parent qualified name, or None if top-level.

        Example:
            >>> qn = QualifiedName.from_string("bengal.core.Site")
            >>> str(qn.parent)
            'bengal.core'
        """
        if len(self.parts) <= 1:
            return None
        return QualifiedName(parts=self.parts[:-1])
