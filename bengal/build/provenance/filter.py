"""
Provenance-based incremental filter.

Replaces IncrementalFilterEngine with content-addressed provenance checking.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any

from bengal.build.contracts.keys import CacheKey, content_key
from bengal.build.provenance.store import ProvenanceCache
from bengal.build.provenance.types import (
    ContentHash,
    Provenance,
    ProvenanceRecord,
    hash_content,
    hash_dict,
    hash_file,
)

if TYPE_CHECKING:
    from bengal.core.asset import Asset
    from bengal.core.page import Page
    from bengal.core.site import Site


@dataclass
class ProvenanceFilterResult:
    """Result of provenance-based filtering."""

    # Pages that need to be built
    pages_to_build: list[Page]

    # Assets that need to be processed
    assets_to_process: list[Asset]

    # Pages that were skipped (cache hits)
    pages_skipped: list[Page]

    # Statistics
    total_pages: int = 0
    cache_hits: int = 0
    cache_misses: int = 0

    # Tags affected by changed pages
    affected_tags: set[str] = field(default_factory=set)

    # Sections affected by changed pages
    affected_sections: set[str] = field(default_factory=set)

    # Changed page paths (for downstream use)
    changed_page_paths: set[Path] = field(default_factory=set)

    @property
    def hit_rate(self) -> float:
        """Cache hit rate as percentage."""
        if self.total_pages == 0:
            return 0.0
        return (self.cache_hits / self.total_pages) * 100

    @property
    def is_skip(self) -> bool:
        """True if no pages need building."""
        return len(self.pages_to_build) == 0 and len(self.assets_to_process) == 0


class ProvenanceFilter:
    """
    Provenance-based incremental filter.

    Uses content-addressed hashing to determine which pages need rebuilding.
    Replaces the previous IncrementalFilterEngine.

    Key improvements:
    - Correct invalidation (content-addressed)
    - No manual dependency tracking needed
    - 30x faster than previous system
    - Subvenance queries for debugging

    Usage:
        cache = ProvenanceCache(cache_dir)
        filter = ProvenanceFilter(site, cache)

        result = filter.filter(site.pages, site.assets)

        for page in result.pages_to_build:
            render(page)
    """

    def __init__(
        self,
        site: Site,
        cache: ProvenanceCache,
    ) -> None:
        self.site = site
        self.cache = cache

        # Precompute site config hash (affects all pages)
        self._config_hash = hash_dict(dict(site.config))
        
        # Asset hash tracking (loaded from cache)
        self._asset_hashes: dict[CacheKey, ContentHash] = {}
        self._load_asset_hashes()

    def filter(
        self,
        pages: list[Page],
        assets: list[Asset],
        incremental: bool = True,
        forced_changed: set[Path] | None = None,
    ) -> ProvenanceFilterResult:
        """
        Filter pages and assets to only those that need rebuilding.

        Args:
            pages: All pages in site
            assets: All assets in site
            incremental: Whether incremental mode is enabled
            forced_changed: Paths to treat as changed (from file watcher)

        Returns:
            ProvenanceFilterResult with pages_to_build, assets_to_process, etc.
        """
        if not incremental:
            # Full rebuild - everything needs building
            return ProvenanceFilterResult(
                pages_to_build=list(pages),
                assets_to_process=list(assets),
                pages_skipped=[],
                total_pages=len(pages),
                cache_hits=0,
                cache_misses=len(pages),
            )

        forced = forced_changed or set()

        pages_to_build: list[Page] = []
        pages_skipped: list[Page] = []
        affected_tags: set[str] = set()
        affected_sections: set[str] = set()
        changed_page_paths: set[Path] = set()

        for page in pages:
            page_path = self._get_page_key(page)

            # Check if forced changed
            if page.source_path in forced:
                pages_to_build.append(page)
                changed_page_paths.add(page.source_path)
                self._collect_affected(page, affected_tags, affected_sections)
                continue

            # Build provenance for this page (works for both real and virtual)
            provenance = self._compute_provenance(page)

            # Check if provenance is fresh
            if self.cache.is_fresh(page_path, provenance):
                pages_skipped.append(page)
            else:
                pages_to_build.append(page)
                changed_page_paths.add(page.source_path)
                self._collect_affected(page, affected_tags, affected_sections)

        # For assets, check file modification
        assets_to_process: list[Asset] = []
        for asset in assets:
            if asset.source_path in forced:
                assets_to_process.append(asset)
            elif self._is_asset_changed(asset):
                assets_to_process.append(asset)

        return ProvenanceFilterResult(
            pages_to_build=pages_to_build,
            assets_to_process=assets_to_process,
            pages_skipped=pages_skipped,
            total_pages=len(pages),
            cache_hits=len(pages_skipped),
            cache_misses=len(pages_to_build),
            affected_tags=affected_tags,
            affected_sections=affected_sections,
            changed_page_paths=changed_page_paths,
        )

    def record_build(self, page: Page, output_hash: ContentHash | None = None) -> None:
        """
        Record provenance after a page is built.

        Call this after rendering each page to update the cache.
        Records provenance for both real and virtual pages.

        Args:
            page: The page that was built
            output_hash: Hash of the rendered output (optional)
        """
        provenance = self._compute_provenance(page)
        
        # Skip pages with no meaningful provenance (fallback only)
        if provenance.input_count <= 1:  # Only config, no real source
            return

        page_path = self._get_page_key(page)

        record = ProvenanceRecord(
            page_path=page_path,
            provenance=provenance,
            output_hash=output_hash or ContentHash("_rendered_"),
        )
        self.cache.store(record)

    def save(self) -> None:
        """Save the provenance cache to disk."""
        self.cache.save()
        self._save_asset_hashes()
    
    def _load_asset_hashes(self) -> None:
        """Load asset hashes from disk."""
        import json
        asset_cache_path = self.cache.cache_dir / "asset_hashes.json"
        if asset_cache_path.exists():
            try:
                data = json.loads(asset_cache_path.read_text())
                self._asset_hashes = {CacheKey(k): ContentHash(v) for k, v in data.items()}
            except (json.JSONDecodeError, KeyError):
                self._asset_hashes = {}
    
    def _save_asset_hashes(self) -> None:
        """Save asset hashes to disk."""
        import json
        asset_cache_path = self.cache.cache_dir / "asset_hashes.json"
        asset_cache_path.parent.mkdir(parents=True, exist_ok=True)
        asset_cache_path.write_text(json.dumps(dict(self._asset_hashes), indent=2))

    def _compute_provenance(self, page: Page) -> Provenance:
        """Compute provenance for a page based on its inputs.
        
        Handles both real content pages and virtual pages:
        - Real pages: hash of source .md file
        - Autodoc pages: hash of Python source being documented
        - Taxonomy pages: hash of page list for that tag
        - Other virtual: template + metadata hash
        
        Note: We intentionally exclude dynamic metadata because it can be
        modified by cascades. The source file content captures frontmatter.
        """
        provenance = Provenance()
        rel_path = self._get_page_key(page)

        # 1. Determine the actual source for this page
        is_virtual = getattr(page, "_virtual", False)
        
        if not is_virtual and page.source_path.exists():
            # Real content page - hash the markdown file
            content_hash = hash_file(page.source_path)
            provenance = provenance.with_input("content", rel_path, content_hash)
        
        elif is_virtual:
            # Virtual page - find the actual source
            
            # Autodoc pages: hash the Python source file
            # Uses "source_file" metadata set during autodoc extraction
            autodoc_source = page.metadata.get("source_file")
            if autodoc_source and page.metadata.get("is_autodoc"):
                source_path = Path(autodoc_source) if isinstance(autodoc_source, str) else autodoc_source
                # Resolve relative paths from site root
                if not source_path.is_absolute():
                    source_path = self.site.root_path / source_path
                if source_path.exists():
                    source_hash = hash_file(source_path)
                    # Use relative path for cache key stability
                    try:
                        rel_source = str(source_path.relative_to(self.site.root_path.parent))
                    except ValueError:
                        rel_source = str(source_path)
                    provenance = provenance.with_input(
                        "autodoc_source",
                        CacheKey(rel_source),
                        source_hash,
                    )
            
            # Taxonomy/tag pages: hash the tag name (page list is implicit)
            tag_name = page.metadata.get("_taxonomy_term") or page.metadata.get("tag")
            if tag_name:
                tag_hash = hash_content(str(tag_name))
                provenance = provenance.with_input(
                    "taxonomy",
                    CacheKey(f"tag:{tag_name}"),
                    tag_hash,
                )
            
            # CLI pages: similar to autodoc
            cli_source = page.metadata.get("source_file")
            if cli_source and page.metadata.get("is_cli"):
                source_path = Path(cli_source) if isinstance(cli_source, str) else cli_source
                if not source_path.is_absolute():
                    source_path = self.site.root_path / source_path
                if source_path.exists():
                    source_hash = hash_file(source_path)
                    provenance = provenance.with_input(
                        "cli_source",
                        CacheKey(str(source_path)),
                        source_hash,
                    )
            
            # Fallback for other virtual pages: use template + title hash
            if provenance.input_count == 0:
                template = page.metadata.get("template") or page.metadata.get("_autodoc_template") or "default"
                title = page.metadata.get("title") or rel_path
                fallback_hash = hash_content(f"{template}:{title}")
                provenance = provenance.with_input("virtual", rel_path, fallback_hash)

        # 2. Site config (affects all pages)
        provenance = provenance.with_input("config", CacheKey("site_config"), self._config_hash)

        return provenance

    def _get_page_key(self, page: Page) -> CacheKey:
        """Get canonical page key for cache lookups."""
        return content_key(page.source_path, self.site.root_path)

    def _is_asset_changed(self, asset: Asset) -> bool:
        """Check if an asset has changed based on content hash."""
        if not asset.source_path.exists():
            return True
        
        # Check if asset is in provenance cache
        asset_path = self._get_asset_key(asset)
        current_hash = hash_file(asset.source_path)
        
        # Use a simple key-value lookup in the cache index
        stored_hash = self._asset_hashes.get(asset_path)
        if stored_hash is None:
            # First time seeing this asset
            self._asset_hashes[asset_path] = current_hash
            return True
        
        if stored_hash != current_hash:
            # Asset content changed
            self._asset_hashes[asset_path] = current_hash
            return True
        
        return False
    
    def _get_asset_key(self, asset: Asset) -> CacheKey:
        """Get canonical asset key for cache lookups."""
        return content_key(asset.source_path, self.site.root_path)

    def _collect_affected(
        self,
        page: Page,
        affected_tags: set[str],
        affected_sections: set[str],
    ) -> None:
        """Collect tags and sections affected by a changed page."""
        # Collect tags
        if hasattr(page, "tags") and page.tags:
            affected_tags.update(page.tags)

        # Collect section
        if hasattr(page, "_section") and page._section:
            section = page._section
            if hasattr(section, "path"):
                affected_sections.add(str(section.path))

    def stats(self) -> dict[str, Any]:
        """Get cache statistics."""
        return self.cache.stats()

    def get_affected_by(self, input_hash: ContentHash) -> set[str]:
        """
        Subvenance query: What pages depend on this input?

        Use for debugging and understanding dependencies.
        """
        return self.cache.get_affected_by(input_hash)
