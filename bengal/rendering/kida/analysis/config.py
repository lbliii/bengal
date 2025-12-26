"""Analysis configuration for template introspection.

Allows customization of naming conventions for standalone Kida use.
Bengal uses defaults; other frameworks may override.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class AnalysisConfig:
    """Configuration for template analysis.

    Allows customization of naming conventions for standalone Kida use.
    Bengal uses defaults; other frameworks may override.

    Attributes:
        page_prefixes: Variable prefixes indicating per-page scope.
            Variables starting with these are considered page-specific
            and blocks using them get cache_scope="page".

        site_prefixes: Variable prefixes indicating site-wide scope.
            Variables starting with these are considered site-wide
            and blocks using only these get cache_scope="site".

        extra_pure_functions: Additional functions to treat as pure.
            Extend the built-in list of known pure functions.

        extra_impure_filters: Additional filters to treat as impure.
            Extend the built-in list of known impure filters.

    Example:
        >>> # Custom configuration for a blog framework
        >>> config = AnalysisConfig(
        ...     page_prefixes=frozenset({"post.", "post", "article.", "article"}),
        ...     site_prefixes=frozenset({"settings.", "settings", "global."}),
        ... )
        >>> analyzer = BlockAnalyzer(config=config)
    """

    # Naming conventions for cache scope inference
    page_prefixes: frozenset[str] = frozenset(
        {
            "page.",
            "page",
            "post.",
            "post",
            "item.",
            "item",
            "doc.",
            "doc",
            "entry.",
            "entry",
        }
    )
    site_prefixes: frozenset[str] = frozenset(
        {
            "site.",
            "site",
            "config.",
            "config",
            "global.",
            "global",
        }
    )

    # Extend purity analysis
    extra_pure_functions: frozenset[str] = frozenset()
    extra_impure_filters: frozenset[str] = frozenset()


# Default configuration for Bengal
DEFAULT_CONFIG = AnalysisConfig()
