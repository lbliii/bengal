"""Metadata dataclasses for template introspection.

Immutable, frozen dataclasses representing analysis results.
All fields are conservative estimates — may over-approximate but never under.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True, slots=True)
class BlockMetadata:
    """Metadata about a template block, inferred from static analysis.

    All fields are conservative estimates:
    - `depends_on` may include unused paths (over-approximation)
    - `is_pure` defaults to "unknown" when uncertain
    - `inferred_role` is heuristic, not semantic truth

    Thread-safe: Immutable after creation.

    Attributes:
        name: Block identifier (e.g., "nav", "content", "sidebar")

        emits_html: True if block produces any output.
            Used to detect empty blocks.

        emits_landmarks: HTML5 landmark elements emitted (nav, main, header, etc.).
            Detected from static HTML in Data nodes.

        inferred_role: Heuristic classification based on name and landmarks.
            One of: "navigation", "content", "sidebar", "header", "footer", "unknown"

        depends_on: Context paths this block may access (conservative superset).
            Example: frozenset({"page.title", "site.pages", "config.theme"})

        is_pure: Whether block output is deterministic for same inputs.
            - "pure": Deterministic, safe to cache
            - "impure": Uses random/shuffle/etc, must re-render
            - "unknown": Cannot determine, treat as potentially impure

        cache_scope: Recommended caching granularity.
            - "site": Cache once per site build (no page-specific deps)
            - "page": Cache per page (has page-specific deps)
            - "none": Cannot cache (impure)
            - "unknown": Cannot determine

    Example:
        >>> meta = template.block_metadata()
        >>> nav = meta.get("nav")
        >>> if nav and nav.is_cacheable():
        ...     cached = cache.get_or_render("nav", ...)
    """

    name: str

    # Output characteristics
    emits_html: bool = True
    emits_landmarks: frozenset[str] = frozenset()
    inferred_role: Literal[
        "navigation",
        "content",
        "sidebar",
        "header",
        "footer",
        "unknown",
    ] = "unknown"

    # Input characteristics
    depends_on: frozenset[str] = frozenset()
    is_pure: Literal["pure", "impure", "unknown"] = "unknown"

    # Derived optimization hints
    cache_scope: Literal["none", "page", "site", "unknown"] = "unknown"

    def is_cacheable(self) -> bool:
        """Check if this block can be safely cached.

        Returns True if:
        - Block is pure (deterministic)
        - Cache scope is not "none"

        Returns:
            True if block can be cached, False otherwise.
        """
        return self.is_pure == "pure" and self.cache_scope != "none"

    def depends_on_page(self) -> bool:
        """Check if block depends on page-specific context.

        Returns:
            True if any dependency starts with common page prefixes.
        """
        return any(path.startswith("page.") or path == "page" for path in self.depends_on)

    def depends_on_site(self) -> bool:
        """Check if block depends on site-wide context.

        Returns:
            True if any dependency starts with common site prefixes.
        """
        return any(path.startswith("site.") or path == "site" for path in self.depends_on)


@dataclass(frozen=True, slots=True)
class TemplateMetadata:
    """Metadata about a complete template.

    Aggregates block metadata and tracks template-level information
    like inheritance and top-level dependencies.

    Attributes:
        name: Template identifier (e.g., "page.html")

        extends: Parent template name from {% extends %}, or None.
            Example: "base.html"

        blocks: Mapping of block name → BlockMetadata.
            All blocks defined in this template.

        top_level_depends_on: Context paths used outside blocks.
            Captures dependencies from:
            - Code before/after blocks
            - Dynamic extends expressions
            - Template-level set/let statements

    Example:
        >>> meta = template.template_metadata()
        >>> print(f"Extends: {meta.extends}")
        >>> print(f"Blocks: {list(meta.blocks.keys())}")
        >>> print(f"All deps: {meta.all_dependencies()}")
    """

    name: str | None
    extends: str | None
    blocks: dict[str, BlockMetadata]
    top_level_depends_on: frozenset[str] = frozenset()

    def all_dependencies(self) -> frozenset[str]:
        """Return all context paths used anywhere in template.

        Combines top-level dependencies with all block dependencies.

        Returns:
            Frozen set of all context paths.
        """
        deps = set(self.top_level_depends_on)
        for block in self.blocks.values():
            deps |= block.depends_on
        return frozenset(deps)

    def get_block(self, name: str) -> BlockMetadata | None:
        """Get metadata for a specific block.

        Args:
            name: Block name to look up.

        Returns:
            BlockMetadata if found, None otherwise.
        """
        return self.blocks.get(name)

    def cacheable_blocks(self) -> list[BlockMetadata]:
        """Return all blocks that can be safely cached.

        Returns:
            List of BlockMetadata where is_cacheable() is True.
        """
        return [block for block in self.blocks.values() if block.is_cacheable()]

    def site_cacheable_blocks(self) -> list[BlockMetadata]:
        """Return blocks that can be cached site-wide.

        Returns:
            List of BlockMetadata where cache_scope is "site".
        """
        return [block for block in self.blocks.values() if block.cache_scope == "site"]
