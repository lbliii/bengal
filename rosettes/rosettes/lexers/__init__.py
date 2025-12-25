"""Rosettes lexers package.

Lexers are loaded lazily via the registry.
Import individual lexers only when needed.
"""

from rosettes.lexers._base import PatternLexer, Rule

__all__ = ["PatternLexer", "Rule"]
