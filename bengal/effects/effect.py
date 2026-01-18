"""
Declarative Effect type for build operations.

RFC: Snapshot-Enabled v2 Opportunities (Opportunity 1)

An Effect represents the inputs and outputs of a build operation,
replacing the bespoke detection logic in 13 detector classes.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass(frozen=True, slots=True)
class Effect:
    """
    Declarative effect of a build operation.
    
    Records what a build operation:
    - Produces (outputs)
    - Reads/depends on (depends_on)
    - Invalidates (cache keys to clear if inputs change)
    
    Replaces 13 detector classes with one unified model.
    
    Attributes:
        outputs: Files this operation produces
        depends_on: Files/keys this operation reads (paths or template names)
        invalidates: Cache keys to clear if inputs change
        operation: Name of the operation (for debugging)
        metadata: Additional context (page href, template name, etc.)
    
    Example:
        >>> effect = Effect(
        ...     outputs=frozenset({Path("public/docs/guide/index.html")}),
        ...     depends_on=frozenset({
        ...         Path("content/docs/guide.md"),
        ...         Path("templates/doc.html"),
        ...         "partials/nav.html",  # Template include
        ...     }),
        ...     invalidates=frozenset({"page:/docs/guide/"}),
        ...     operation="render_page",
        ... )
    """

    # Files this operation produces
    outputs: frozenset[Path] = field(default_factory=frozenset)

    # Files/keys this operation reads
    # Can be Path (file) or str (template name, config key, etc.)
    depends_on: frozenset[Path | str] = field(default_factory=frozenset)

    # Cache keys to clear if inputs change
    invalidates: frozenset[str] = field(default_factory=frozenset)

    # Operation name for debugging/visualization
    operation: str = ""

    # Additional context (not used for invalidation)
    metadata: dict[str, Any] = field(default_factory=dict)

    def __hash__(self) -> int:
        """Hash based on outputs for deduplication."""
        return hash(self.outputs)

    def merge_with(self, other: Effect) -> Effect:
        """
        Merge two effects into one.
        
        Useful for combining effects from multiple operations on the same output.
        
        Args:
            other: Another effect to merge with
            
        Returns:
            New Effect with combined dependencies and invalidations
        """
        return Effect(
            outputs=self.outputs | other.outputs,
            depends_on=self.depends_on | other.depends_on,
            invalidates=self.invalidates | other.invalidates,
            operation=f"{self.operation}+{other.operation}" if other.operation else self.operation,
            metadata={**self.metadata, **other.metadata},
        )

    @classmethod
    def for_page_render(
        cls,
        source_path: Path,
        output_path: Path,
        template_name: str,
        template_includes: frozenset[str],
        page_href: str,
        cascade_sources: frozenset[Path] | None = None,
        data_files: frozenset[Path] | None = None,
    ) -> Effect:
        """
        Create effect for page rendering.
        
        Convenience factory for the most common effect type.
        
        Args:
            source_path: Path to source markdown file
            output_path: Path where HTML will be written
            template_name: Name of the template used
            template_includes: Templates included/extended by the main template
            page_href: Page URL for cache key
            cascade_sources: Parent _index.md files that cascade to this page
            data_files: Data files (data/*.yaml) used by this page
            
        Returns:
            Effect for this page render operation
        """
        deps: set[Path | str] = {source_path, template_name}
        deps.update(template_includes)
        
        if cascade_sources:
            deps.update(cascade_sources)
        if data_files:
            deps.update(data_files)
        
        return cls(
            outputs=frozenset({output_path}),
            depends_on=frozenset(deps),
            invalidates=frozenset({f"page:{page_href}"}),
            operation="render_page",
            metadata={"href": page_href, "template": template_name},
        )

    @classmethod
    def for_asset_copy(
        cls,
        source_path: Path,
        output_path: Path,
        fingerprinted: bool = False,
    ) -> Effect:
        """
        Create effect for asset copy/processing.
        
        Args:
            source_path: Source asset path
            output_path: Output asset path (may include fingerprint)
            fingerprinted: Whether asset has content hash in filename
            
        Returns:
            Effect for this asset operation
        """
        return cls(
            outputs=frozenset({output_path}),
            depends_on=frozenset({source_path}),
            invalidates=frozenset({f"asset:{source_path}"}),
            operation="copy_asset" if not fingerprinted else "fingerprint_asset",
            metadata={"fingerprinted": fingerprinted},
        )

    @classmethod
    def for_index_generation(
        cls,
        output_path: Path,
        source_pages: frozenset[Path],
        index_type: str,
    ) -> Effect:
        """
        Create effect for index generation (sitemap, RSS, search index).
        
        Args:
            output_path: Path to output index file
            source_pages: Pages included in this index
            index_type: Type of index (sitemap, rss, search, etc.)
            
        Returns:
            Effect for this index generation
        """
        return cls(
            outputs=frozenset({output_path}),
            depends_on=frozenset(source_pages),
            invalidates=frozenset({f"index:{index_type}"}),
            operation=f"generate_{index_type}",
            metadata={"index_type": index_type, "page_count": len(source_pages)},
        )

    @classmethod
    def for_taxonomy_page(
        cls,
        output_path: Path,
        taxonomy_name: str,
        term: str,
        member_pages: frozenset[Path],
    ) -> Effect:
        """
        Create effect for taxonomy term page.
        
        Args:
            output_path: Path to output taxonomy page
            taxonomy_name: Name of taxonomy (tags, categories, etc.)
            term: Taxonomy term
            member_pages: Pages with this term
            
        Returns:
            Effect for this taxonomy page
        """
        return cls(
            outputs=frozenset({output_path}),
            depends_on=frozenset(member_pages),
            invalidates=frozenset({f"taxonomy:{taxonomy_name}:{term}"}),
            operation="generate_taxonomy_page",
            metadata={"taxonomy": taxonomy_name, "term": term},
        )
