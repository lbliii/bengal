"""
Hook provenance tracking into Bengal's rendering pipeline.

This module provides a wrapper around RenderingPipeline that captures
full provenance during actual page rendering.

Usage:
    from bengal.experimental.provenance.pipeline_hook import ProvenanceRenderingPipeline
    
    pipeline = ProvenanceRenderingPipeline(site, provenance_store=store)
    pipeline.process_page(page)  # Provenance captured automatically
"""

from __future__ import annotations

import contextvars
from pathlib import Path
from typing import TYPE_CHECKING, Any

from bengal.experimental.provenance.core_types import (
    ContentHash,
    Provenance,
    ProvenanceRecord,
    hash_content,
    hash_dict,
    hash_file,
)
from bengal.experimental.provenance.store import ProvenanceStore
from bengal.experimental.provenance.tracker import ProvenanceTracker

if TYPE_CHECKING:
    from bengal.cache import DependencyTracker
    from bengal.core.page import Page
    from bengal.core.site import Site
    from bengal.orchestration.build_context import BuildContext
    from bengal.orchestration.stats import BuildStats
    from bengal.rendering.pipeline import WriteBehindCollector

# Context variable for current page provenance
_current_provenance: contextvars.ContextVar[Provenance | None] = contextvars.ContextVar(
    "current_provenance", default=None
)


def get_current_provenance() -> Provenance | None:
    """Get the current page's provenance being tracked."""
    return _current_provenance.get()


def record_template_access(template_path: Path) -> None:
    """Record a template access (called from template engine)."""
    prov = _current_provenance.get()
    if prov is None:
        return
    
    if template_path.exists():
        content_hash = hash_file(template_path)
        new_prov = prov.with_input("template", str(template_path), content_hash)
        _current_provenance.set(new_prov)


def record_data_access(data_path: str, content_hash: ContentHash) -> None:
    """Record a data file access (called from data loader)."""
    prov = _current_provenance.get()
    if prov is None:
        return
    
    new_prov = prov.with_input("data", data_path, content_hash)
    _current_provenance.set(new_prov)


def record_partial_access(partial_path: Path) -> None:
    """Record a partial/include access."""
    prov = _current_provenance.get()
    if prov is None:
        return
    
    if partial_path.exists():
        content_hash = hash_file(partial_path)
        new_prov = prov.with_input("partial", str(partial_path), content_hash)
        _current_provenance.set(new_prov)


class ProvenanceRenderingPipeline:
    """
    Wrapper around RenderingPipeline that captures provenance.
    
    Delegates all rendering to the real pipeline while capturing
    provenance data for each page.
    
    Usage:
        store = ProvenanceStore(cache_dir)
        pipeline = ProvenanceRenderingPipeline(
            site,
            provenance_store=store,
            dependency_tracker=tracker,
        )
        
        for page in pages:
            pipeline.process_page(page)
        
        pipeline.save_provenance()
    """
    
    def __init__(
        self,
        site: Site,
        provenance_store: ProvenanceStore,
        dependency_tracker: DependencyTracker | None = None,
        quiet: bool = False,
        build_stats: BuildStats | None = None,
        build_context: BuildContext | None = None,
        changed_sources: set[Path] | None = None,
        block_cache: Any | None = None,
        write_behind: WriteBehindCollector | None = None,
    ):
        self.site = site
        self.provenance_store = provenance_store
        self._build_id = ""
        
        # Statistics
        self.pages_processed = 0
        self.cache_hits = 0
        self.cache_misses = 0
        self.total_inputs_captured = 0
        
        # Create the real pipeline
        from bengal.rendering.pipeline import RenderingPipeline
        
        self._real_pipeline = RenderingPipeline(
            site,
            dependency_tracker=dependency_tracker,
            quiet=quiet,
            build_stats=build_stats,
            build_context=build_context,
            changed_sources=changed_sources,
            block_cache=block_cache,
            write_behind=write_behind,
        )
    
    def process_page(self, page: Page) -> None:
        """
        Process a page with provenance tracking.
        
        On cache HIT: Skip render entirely (instant).
        On cache MISS: Run full render and capture provenance.
        """
        self.pages_processed += 1
        
        # Compute page path relative to site root
        try:
            page_path = str(page.source_path.relative_to(self.site.root_path))
        except ValueError:
            page_path = str(page.source_path)
        
        # Initialize provenance with known inputs
        provenance = self._capture_initial_provenance(page)
        
        # Check if we can skip (provenance cache hit)
        if self.provenance_store.is_fresh(page_path, provenance):
            self.cache_hits += 1
            self.total_inputs_captured += provenance.input_count
            # SKIP RENDER - output is already correct!
            return
        
        # Cache miss - need to render
        self.cache_misses += 1
        
        # Set up provenance tracking context
        token = _current_provenance.set(provenance)
        
        try:
            # Run the real pipeline
            self._real_pipeline.process_page(page)
            
            # Get final provenance (may have been updated during render)
            final_provenance = _current_provenance.get() or provenance
            
            # Compute output hash
            output_hash = ContentHash("_rendered_")
            if hasattr(page, "output_path") and page.output_path:
                output_path = self.site.output_dir / page.output_path
                if output_path.exists():
                    output_hash = hash_file(output_path)
            
            # Store provenance
            record = ProvenanceRecord(
                page_path=page_path,
                provenance=final_provenance,
                output_hash=output_hash,
                build_id=self._build_id,
            )
            self.provenance_store.store(record)
            self.total_inputs_captured += final_provenance.input_count
            
        finally:
            _current_provenance.reset(token)
    
    def _capture_initial_provenance(self, page: Page) -> Provenance:
        """Capture initial provenance before rendering starts."""
        provenance = Provenance()
        
        # 1. Source content
        if page.source_path.exists():
            content_hash = hash_file(page.source_path)
            try:
                rel_path = str(page.source_path.relative_to(self.site.root_path))
            except ValueError:
                rel_path = str(page.source_path)
            provenance = provenance.with_input("content", rel_path, content_hash)
        
        # 2. Frontmatter metadata
        if page.metadata:
            meta_hash = hash_dict(dict(page.metadata))
            provenance = provenance.with_input("metadata", "frontmatter", meta_hash)
        
        # 3. Site config (affects all pages)
        config_hash = hash_dict(dict(self.site.config))
        provenance = provenance.with_input("config", "site_config", config_hash)
        
        # 4. Section metadata (if in a section)
        if hasattr(page, "_section") and page._section:
            section = page._section
            if hasattr(section, "metadata") and section.metadata:
                section_hash = hash_dict(dict(section.metadata))
                provenance = provenance.with_input("section", "section_config", section_hash)
        
        # 5. Template (if we can determine it)
        template_name = page.metadata.get("template") or page.metadata.get("layout")
        if template_name:
            template_path = self._find_template(template_name)
            if template_path and template_path.exists():
                template_hash = hash_file(template_path)
                provenance = provenance.with_input("template", str(template_path), template_hash)
        
        return provenance
    
    def _find_template(self, template_name: str) -> Path | None:
        """Find a template file by name."""
        # Check common locations
        search_paths = [
            self.site.root_path / "templates",
            self.site.root_path / "themes" / self.site.theme / "templates",
        ]
        
        for search_dir in search_paths:
            for ext in ["", ".html", ".jinja2", ".j2"]:
                candidate = search_dir / f"{template_name}{ext}"
                if candidate.exists():
                    return candidate
        
        return None
    
    def save_provenance(self) -> None:
        """Persist all provenance data."""
        self.provenance_store.save()
    
    def stats(self) -> dict[str, Any]:
        """Get tracking statistics."""
        return {
            "pages_processed": self.pages_processed,
            "cache_hits": self.cache_hits,
            "cache_misses": self.cache_misses,
            "hit_rate": self.cache_hits / max(1, self.pages_processed) * 100,
            "total_inputs_captured": self.total_inputs_captured,
            "avg_inputs_per_page": self.total_inputs_captured / max(1, self.pages_processed),
        }


def run_provenance_build(
    site: Site,
    pages: list[Page] | None = None,
    cache_dir: Path | None = None,
) -> dict[str, Any]:
    """
    Run a full build with provenance tracking.
    
    This is a convenience function that sets up the provenance pipeline
    and runs it against all pages.
    
    Args:
        site: Bengal site instance
        pages: Pages to build (default: all)
        cache_dir: Provenance cache directory
        
    Returns:
        Build statistics including provenance data
    """
    import time
    
    # Setup
    cache_dir = cache_dir or site.root_path / ".bengal" / "provenance"
    store = ProvenanceStore(cache_dir)
    
    pipeline = ProvenanceRenderingPipeline(
        site,
        provenance_store=store,
    )
    
    target_pages = pages or list(site.pages)
    
    # Build
    start = time.time()
    
    for page in target_pages:
        try:
            pipeline.process_page(page)
        except Exception as e:
            print(f"Error processing {page.source_path}: {e}")
    
    # Save
    pipeline.save_provenance()
    
    elapsed = (time.time() - start) * 1000
    
    # Results
    stats = pipeline.stats()
    stats["elapsed_ms"] = elapsed
    stats["pages_per_second"] = len(target_pages) / (elapsed / 1000) if elapsed > 0 else 0
    
    return stats
