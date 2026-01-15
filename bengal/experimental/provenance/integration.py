"""
Integration with Bengal's rendering pipeline.

This module provides tools to:
1. Run a provenance-tracked build alongside normal builds
2. Compare provenance-based cache decisions vs current system
3. Benchmark overhead of provenance tracking

Usage:
    from bengal.experimental.provenance.integration import ProvenanceBuildRunner
    
    runner = ProvenanceBuildRunner(site)
    results = runner.run_comparison_build()
    print(results.summary())
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any

from bengal.experimental.provenance.core_types import (
    ContentHash,
    Provenance,
    hash_content,
    hash_dict,
    hash_file,
)
from bengal.experimental.provenance.store import ProvenanceStore
from bengal.experimental.provenance.tracker import ProvenanceTracker

if TYPE_CHECKING:
    from bengal.core.page import Page
    from bengal.core.site import Site


@dataclass
class PageProvenanceResult:
    """Result of provenance-tracked page render."""
    
    page_path: str
    provenance: Provenance
    render_time_ms: float
    cache_decision: str  # "hit", "miss", "new"
    current_system_decision: str  # What current system would do
    inputs_captured: int


@dataclass
class ComparisonBuildResult:
    """Results of comparison build."""
    
    pages_analyzed: int = 0
    provenance_hits: int = 0
    provenance_misses: int = 0
    current_hits: int = 0
    current_misses: int = 0
    
    # Agreement tracking
    agreements: int = 0  # Both systems made same decision
    provenance_only_hits: int = 0  # Provenance hit, current miss
    current_only_hits: int = 0  # Current hit, provenance miss
    
    # Timing
    total_time_ms: float = 0
    provenance_overhead_ms: float = 0
    
    # Details
    page_results: list[PageProvenanceResult] = field(default_factory=list)
    
    def summary(self) -> str:
        """Human-readable summary."""
        lines = [
            "=" * 60,
            "Provenance vs Current System Comparison",
            "=" * 60,
            f"Pages analyzed: {self.pages_analyzed}",
            "",
            "Cache Decisions:",
            f"  Provenance hits:  {self.provenance_hits} ({self.provenance_hits/max(1,self.pages_analyzed)*100:.1f}%)",
            f"  Provenance misses: {self.provenance_misses}",
            f"  Current hits:     {self.current_hits} ({self.current_hits/max(1,self.pages_analyzed)*100:.1f}%)",
            f"  Current misses:   {self.current_misses}",
            "",
            "Agreement:",
            f"  Both agree:        {self.agreements} ({self.agreements/max(1,self.pages_analyzed)*100:.1f}%)",
            f"  Provenance better: {self.provenance_only_hits} (more cache hits)",
            f"  Current better:    {self.current_only_hits}",
            "",
            f"Timing:",
            f"  Total time:        {self.total_time_ms:.1f}ms",
            f"  Provenance overhead: {self.provenance_overhead_ms:.1f}ms ({self.provenance_overhead_ms/max(1,self.total_time_ms)*100:.1f}%)",
            "=" * 60,
        ]
        return "\n".join(lines)


class ProvenanceBuildRunner:
    """
    Runs provenance-tracked builds for comparison with current system.
    
    This is a READ-ONLY wrapper - it doesn't modify Bengal's actual
    cache or build output. It just captures provenance and compares
    cache decisions.
    """
    
    def __init__(self, site: Site, cache_dir: Path | None = None):
        self.site = site
        self.cache_dir = cache_dir or site.root_path / ".bengal" / "provenance"
        self.store = ProvenanceStore(self.cache_dir)
        self.tracker = ProvenanceTracker(self.store, site.root_path)
    
    def run_comparison_build(
        self,
        pages: list[Page] | None = None,
        limit: int | None = None,
    ) -> ComparisonBuildResult:
        """
        Run provenance tracking on pages and compare with current cache system.
        
        Args:
            pages: Pages to analyze (default: all site pages)
            limit: Max pages to analyze (for quick testing)
            
        Returns:
            ComparisonBuildResult with detailed analysis
        """
        result = ComparisonBuildResult()
        start_time = time.time()
        
        # Get pages to analyze
        target_pages = pages or list(self.site.pages)
        if limit:
            target_pages = target_pages[:limit]
        
        result.pages_analyzed = len(target_pages)
        
        for page in target_pages:
            page_result = self._analyze_page(page)
            result.page_results.append(page_result)
            
            # Update counts
            if page_result.cache_decision == "hit":
                result.provenance_hits += 1
            else:
                result.provenance_misses += 1
            
            if page_result.current_system_decision == "hit":
                result.current_hits += 1
            else:
                result.current_misses += 1
            
            # Track agreement
            if page_result.cache_decision == page_result.current_system_decision:
                result.agreements += 1
            elif page_result.cache_decision == "hit":
                result.provenance_only_hits += 1
            else:
                result.current_only_hits += 1
            
            result.provenance_overhead_ms += page_result.render_time_ms
        
        # Save provenance store
        self.store.save()
        
        result.total_time_ms = (time.time() - start_time) * 1000
        
        return result
    
    def _analyze_page(self, page: Page) -> PageProvenanceResult:
        """Analyze a single page with provenance tracking."""
        start = time.time()
        page_path = str(page.source_path.relative_to(self.site.root_path))
        
        # Capture provenance for this page
        provenance = self._capture_page_provenance(page)
        
        # Check provenance cache decision
        prov_decision = "hit" if self.store.is_fresh(page_path, provenance) else "miss"
        
        # Check current system's cache decision
        current_decision = self._check_current_cache(page)
        
        # Store provenance for next comparison
        from bengal.experimental.provenance.core_types import ProvenanceRecord
        from datetime import datetime
        
        record = ProvenanceRecord(
            page_path=page_path,
            provenance=provenance,
            output_hash=ContentHash("_not_rendered_"),  # We're not actually rendering
            created_at=datetime.now(),
        )
        self.store.store(record)
        
        render_time = (time.time() - start) * 1000
        
        return PageProvenanceResult(
            page_path=page_path,
            provenance=provenance,
            render_time_ms=render_time,
            cache_decision=prov_decision,
            current_system_decision=current_decision,
            inputs_captured=provenance.input_count,
        )
    
    def _capture_page_provenance(self, page: Page) -> Provenance:
        """
        Capture provenance for a page WITHOUT actually rendering it.
        
        This simulates what a full provenance-tracked render would capture.
        """
        from bengal.experimental.provenance.core_types import Provenance
        
        provenance = Provenance()
        
        # 1. Source content
        if page.source_path.exists():
            content_hash = hash_file(page.source_path)
            provenance = provenance.with_input(
                "content",
                str(page.source_path.relative_to(self.site.root_path)),
                content_hash,
            )
        
        # 2. Frontmatter metadata
        if page.metadata:
            meta_hash = hash_dict(dict(page.metadata))
            provenance = provenance.with_input(
                "metadata",
                str(page.source_path.relative_to(self.site.root_path)),
                meta_hash,
            )
        
        # 3. Templates (simulate template chain)
        template_name = page.metadata.get("template", page.metadata.get("layout", "default"))
        template_paths = self._resolve_template_chain(template_name)
        for tpath in template_paths:
            if tpath.exists():
                provenance = provenance.with_input(
                    "template",
                    str(tpath.relative_to(self.site.root_path)) if tpath.is_relative_to(self.site.root_path) else str(tpath),
                    hash_file(tpath),
                )
        
        # 4. Site config (affects all pages)
        config_hash = hash_dict(dict(self.site.config))
        provenance = provenance.with_input("config", "site_config", config_hash)
        
        # 5. Section config (if page is in a section)
        if hasattr(page, "_section") and page._section:
            section = page._section
            if hasattr(section, "metadata") and section.metadata:
                section_hash = hash_dict(dict(section.metadata))
                section_path = getattr(section, "source_path", "section")
                provenance = provenance.with_input("section", str(section_path), section_hash)
        
        return provenance
    
    def _resolve_template_chain(self, template_name: str) -> list[Path]:
        """Resolve template inheritance chain."""
        templates = []
        
        # Try to find the template in template directories
        template_dirs = [
            self.site.root_path / "templates",
            self.site.root_path / "themes" / self.site.theme / "templates",
        ]
        
        # Also check theme package
        try:
            from bengal.core.theme.registry import get_theme_package
            theme_pkg = get_theme_package(self.site.theme)
            if theme_pkg:
                pkg_templates = Path(theme_pkg.__path__[0]) / "templates"
                if pkg_templates.exists():
                    template_dirs.append(pkg_templates)
        except Exception:
            pass
        
        # Find template file
        for tdir in template_dirs:
            for ext in [".html", ".jinja2", ".j2"]:
                candidate = tdir / f"{template_name}{ext}"
                if candidate.exists():
                    templates.append(candidate)
                    break
            
            # Also try with .html suffix already included
            candidate = tdir / template_name
            if candidate.exists():
                templates.append(candidate)
        
        # TODO: Parse template for {% extends %} to get full chain
        # For now, just return found templates
        
        return templates
    
    def _check_current_cache(self, page: Page) -> str:
        """
        Check what current Bengal cache system would decide.
        
        Returns "hit" or "miss".
        """
        try:
            # Try to access Bengal's build cache
            from bengal.cache import BuildCache
            
            cache_path = self.site.root_path / ".bengal" / "cache.json.zst"
            if not cache_path.exists():
                cache_path = self.site.root_path / ".bengal" / "cache.json"
            
            if not cache_path.exists():
                return "miss"  # No cache exists
            
            cache = BuildCache.load(cache_path)
            
            # Check if page is marked as changed
            if cache.is_changed(page.source_path):
                return "miss"
            
            return "hit"
        except Exception:
            # If we can't check current cache, assume miss
            return "miss"
    
    def get_affected_pages(self, changed_path: str) -> set[str]:
        """
        SUBVENANCE query: What pages would need rebuild if this file changed?
        """
        return self.tracker.get_affected_pages(changed_path)
    
    def show_lineage(self, page_path: str) -> None:
        """Print lineage for debugging."""
        for line in self.tracker.get_lineage(page_path):
            print(line)


def run_provenance_benchmark(site: Site, limit: int = 50) -> ComparisonBuildResult:
    """
    Quick benchmark of provenance tracking.
    
    Usage:
        from bengal.experimental.provenance.integration import run_provenance_benchmark
        results = run_provenance_benchmark(site, limit=100)
        print(results.summary())
    """
    runner = ProvenanceBuildRunner(site)
    return runner.run_comparison_build(limit=limit)


# CLI entry point for testing
def main():
    """Run provenance comparison from command line."""
    import sys
    
    # Try to find a Bengal site
    from pathlib import Path
    
    site_root = Path.cwd()
    if not (site_root / "bengal.yaml").exists() and not (site_root / "config").exists():
        site_root = site_root / "site"
    
    if not site_root.exists():
        print("No Bengal site found. Run from a Bengal site directory.")
        sys.exit(1)
    
    print(f"Loading site from {site_root}...")
    
    try:
        from bengal.core.site import Site
        from bengal.config import load_config
        
        config = load_config(site_root)
        site = Site(site_root, config)
        
        # Discover content
        from bengal.orchestration.content import ContentOrchestrator
        content = ContentOrchestrator(site)
        content.discover()
        
        print(f"Found {len(site.pages)} pages")
        print()
        
        # Run comparison
        limit = int(sys.argv[1]) if len(sys.argv) > 1 else 20
        results = run_provenance_benchmark(site, limit=limit)
        print(results.summary())
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
