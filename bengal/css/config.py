"""Configuration for the CSS minifier."""

from enum import Enum


class MinifyLevel(Enum):
    """How aggressively to minify.

    Levels are a strict superset chain; every level is meaning-preserving.

    - ``SAFE``: lossless whitespace/comment removal only (default).
    - ``OPTIMIZE``: safe + token-level value normalization (colors, numbers).
    - ``AGGRESSIVE``: optimize + cascade-invariant structural rewrites
      (empty-rule removal, exact-duplicate dedup, adjacent rule merging).
    """

    SAFE = "safe"
    OPTIMIZE = "optimize"
    AGGRESSIVE = "aggressive"

    @classmethod
    def coerce(cls, value: MinifyLevel | str) -> MinifyLevel:
        """Coerce a string or enum into a :class:`MinifyLevel`."""
        if isinstance(value, cls):
            return value
        try:
            return cls(str(value).lower())
        except ValueError:
            return cls.SAFE
