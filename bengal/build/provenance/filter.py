"""
Provenance-based incremental filter.

Replaces IncrementalFilterEngine with content-addressed provenance checking.

Thread Safety:
    The ProvenanceFilter is designed for single-threaded use within a build,
    but uses thread-safe backing stores (ProvenanceCache). Session caches
    (_file_hashes, _computed_provenance) are per-filter instance and should
    not be shared between threads without synchronization.
"""

from __future__ import annotations

import threading
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
from bengal.utils.io.json_compat import JSONDecodeError
from bengal.utils.io.json_compat import dump as json_dump
from bengal.utils.io.json_compat import load as json_load
from bengal.utils.observability.logger import get_logger

logger = get_logger(__name__)

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

        # Session caches to avoid redundant I/O and computation
        # Protected by lock for thread-safe access during parallel operations
        self._file_hashes: dict[Path, ContentHash] = {}
        self._computed_provenance: dict[CacheKey, Provenance] = {}
        self._session_lock = threading.Lock()

    def filter(
        self,
        pages: list[Page],
        assets: list[Asset],
        incremental: bool = True,
        forced_changed: set[Path] | None = None,
        trust_unchanged: bool = False,
    ) -> ProvenanceFilterResult:
        """
        Filter pages and assets to only those that need rebuilding.

        Args:
            pages: All pages in site
            assets: All assets in site
            incremental: Whether incremental mode is enabled
            forced_changed: Paths to treat as changed (from file watcher)
            trust_unchanged: When True and forced_changed is set, pages NOT in
                           forced_changed that have a stored provenance hash are
                           immediately treated as cache hits without recomputing
                           provenance. This avoids file I/O for unchanged pages
                           during dev server rebuilds. Safe because:
                           - Source file didn't change (not in forced_changed)
                           - Cascade sources are expanded by _expand_forced_changed
                           - Config changes trigger full rebuilds
                           (RFC: reactive-rebuild-architecture Phase 1c)

        Returns:
            ProvenanceFilterResult with pages_to_build, assets_to_process, etc.
        """
        if not incremental:
            # Full rebuild - everything needs building
            # CRITICAL: Still compute and cache asset hashes for subsequent incremental builds
            # Without this, the next incremental build would see all assets as "changed"
            # and trigger the fingerprint cascade (forcing a full page rebuild).
            for asset in assets:
                self._record_asset_hash(asset)

            # Pre-compute provenance for all pages so record_build() uses consistent values
            # This ensures the same cascade source hashes are used during both
            # filter (here) and record (after render) phases
            for page in pages:
                page_path = self._get_page_key(page)
                if page_path not in self._computed_provenance:
                    try:
                        self._compute_provenance(page)  # Caches internally
                    except Exception as e:
                        logger.debug(
                            "provenance_precompute_failed",
                            page_path=str(page_path),
                            error=str(e),
                        )

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

        # RFC: reactive-rebuild-architecture Phase 1c
        # Track how many pages we skip via trust_unchanged for observability
        trust_skipped = 0

        for page in pages:
            page_path = self._get_page_key(page)

            # Check if forced changed (fast path - skip cache check)
            if page.source_path in forced:
                pages_to_build.append(page)
                changed_page_paths.add(page.source_path)
                self._collect_affected(page, affected_tags, affected_sections)
                continue

            # CRITICAL OPTIMIZATION: Check cache FIRST before computing provenance
            # This avoids expensive file hashing for cache hits
            stored_hash = self.cache.get_stored_hash(page_path)
            if stored_hash is None:
                # No cache entry - definitely need to build
                pages_to_build.append(page)
                changed_page_paths.add(page.source_path)
                self._collect_affected(page, affected_tags, affected_sections)
                continue

            # RFC: reactive-rebuild-architecture Phase 1c
            # When trust_unchanged is enabled and forced_changed is provided,
            # pages NOT in forced_changed with a stored hash can be trusted
            # immediately — no file hashing needed. This is safe during dev
            # server rebuilds because:
            # - The file watcher tells us exactly what changed
            # - Cascade sources are expanded before we get here
            # - Config changes trigger full (non-incremental) rebuilds
            if trust_unchanged and forced:
                pages_skipped.append(page)
                trust_skipped += 1
                continue

            # Cache entry exists - check if it's still valid
            # For simple content pages, use fast-path (content + config only)
            is_virtual = getattr(page, "_virtual", False)
            if not is_virtual and page.source_path.exists():
                provenance_fast = self._compute_provenance_fast(page)
                if provenance_fast is not None and provenance_fast.combined_hash == stored_hash:
                    # Cache hit via fast path - skip full computation
                    pages_skipped.append(page)
                    continue
                # Hash mismatch - mark page for rebuild
                # Also set _cascade_invalidated if cascade sources changed
                # This tells the rendering pipeline to bypass its own cache
                if provenance_fast is not None:
                    page._cascade_invalidated = True  # type: ignore[attr-defined]

            # Fast path didn't match or page is virtual - compute full provenance
            try:
                provenance = self._compute_provenance(page)
            except Exception as e:
                # If provenance computation fails, treat as cache miss (rebuild)
                logger.debug(
                    "provenance_computation_failed",
                    page_path=str(page_path),
                    error=str(e),
                    is_virtual=is_virtual,
                )
                pages_to_build.append(page)
                changed_page_paths.add(page.source_path)
                self._collect_affected(page, affected_tags, affected_sections)
                continue

            # Ensure provenance has at least config input (sanity check)
            if provenance.input_count == 0:
                logger.warning(
                    "empty_provenance_computed",
                    page_path=str(page_path),
                    is_virtual=is_virtual,
                    suggestion="Page may have no valid source - treating as cache miss",
                )
                pages_to_build.append(page)
                changed_page_paths.add(page.source_path)
                self._collect_affected(page, affected_tags, affected_sections)
                continue

            # Check if provenance matches stored hash
            if provenance.combined_hash == stored_hash:
                pages_skipped.append(page)
            else:
                pages_to_build.append(page)
                changed_page_paths.add(page.source_path)
                self._collect_affected(page, affected_tags, affected_sections)

        if trust_skipped > 0:
            logger.info(
                "provenance_trust_unchanged",
                trust_skipped=trust_skipped,
                recomputed=len(pages) - trust_skipped - len([p for p in pages if p.source_path in forced]),
            )

        # For assets, check file modification
        assets_to_process: list[Asset] = [
            asset
            for asset in assets
            if asset.source_path in forced or self._is_asset_changed(asset)
        ]

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
        Record provenance after a page is built (thread-safe).

        Call this after rendering each page to update the cache.
        Records provenance for both real and virtual pages.

        Args:
            page: The page that was built
            output_hash: Hash of the rendered output (optional)
        """
        # OPTIMIZATION: Use already computed provenance if available from filter phase
        page_path = self._get_page_key(page)

        # Thread-safe access to session cache
        provenance = self._computed_provenance.get(page_path)

        if provenance is None:
            provenance = self._compute_provenance(page)

        # Skip pages with no meaningful provenance (fallback only)
        # This commonly happens for generated taxonomy pages during cold builds where
        # provenance is computed before files are fully populated. Not a problem since
        # cold builds rebuild everything anyway.
        if provenance.input_count <= 1:  # Only config, no real source
            logger.debug(
                "skipping_provenance_storage",
                page_path=str(page_path),
                input_count=provenance.input_count,
                is_virtual=getattr(page, "_virtual", False),
                has_section=getattr(page, "_section", None) is not None,
                source_path=str(getattr(page, "source_path", None)),
            )
            return

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
        asset_cache_path = self.cache.cache_dir / "asset_hashes.json"
        try:
            data = json_load(asset_cache_path)
            self._asset_hashes = {CacheKey(k): ContentHash(v) for k, v in data.items()}
        except (FileNotFoundError, JSONDecodeError, KeyError):
            self._asset_hashes = {}

    def _save_asset_hashes(self) -> None:
        """Save asset hashes to disk (atomic write for crash safety)."""
        asset_cache_path = self.cache.cache_dir / "asset_hashes.json"
        json_dump(dict(self._asset_hashes), asset_cache_path)

    def _get_file_hash(self, path: Path) -> ContentHash:
        """Get file hash from session cache or compute it (thread-safe)."""
        # Fast path: check without lock
        cached = self._file_hashes.get(path)
        if cached is not None:
            return cached

        # Compute hash (outside lock - I/O)
        computed = hash_file(path)

        # Store in cache with lock
        with self._session_lock:
            # Double-check in case another thread computed it
            if path not in self._file_hashes:
                self._file_hashes[path] = computed
            return self._file_hashes[path]

    def _get_cascade_sources(self, page: Page) -> list[Path]:
        """
        Get all _index.md files that contribute cascade metadata to this page.

        Traverses from page._section up through parent sections, collecting
        index page source paths. When any cascade source changes, the page's
        provenance hash changes, triggering an incremental rebuild.

        Args:
            page: The page to find cascade sources for

        Returns:
            List of _index.md source paths, ordered from immediate parent to root
        """
        sources: list[Path] = []
        section = getattr(page, "_section", None)

        # Fallback: If _section is None but we have a section path in page.core, look it up
        # This handles PageProxy objects that may not have _section set properly
        if section is None:
            core = getattr(page, "core", None)
            if core is not None:
                section_path = getattr(core, "section", None)
                if section_path and self.site:
                    try:
                        section = self.site.get_section_by_path(section_path)
                    except (AttributeError, KeyError, TypeError):
                        pass

        # Safety guard: prevent infinite loops from circular references or mock objects
        # Real hierarchies are never deeper than ~50 levels
        max_depth = 100
        depth = 0
        seen_ids: set[int] = set()

        while section is not None and depth < max_depth:
            # Detect circular references by tracking object ids
            section_id = id(section)
            if section_id in seen_ids:
                break  # Circular reference detected
            seen_ids.add(section_id)

            # Check if section has an index page
            index_page = getattr(section, "index_page", None)
            if index_page is not None:
                index_path = getattr(index_page, "source_path", None)
                if index_path is not None and isinstance(index_path, Path):
                    # Verify file exists (could be virtual or deleted)
                    try:
                        if index_path.exists():
                            sources.append(index_path)
                    except OSError:
                        pass  # Skip if file system error

            # Move to parent section
            parent = getattr(section, "parent", None)
            # Break if parent is the same object (self-reference) or not a real section
            if parent is section or parent is None:
                break
            section = parent
            depth += 1

        # Diagnostic logging for cascade source discovery
        page_path = self._get_page_key(page)
        if sources:
            logger.debug(
                "cascade_sources_found",
                page_path=str(page_path),
                source_count=len(sources),
                sources=[str(s) for s in sources],
            )
        else:
            # Log when NO cascade sources found - this might indicate a problem
            initial_section = getattr(page, "_section", None)
            logger.debug(
                "no_cascade_sources",
                page_path=str(page_path),
                has_section=initial_section is not None,
                section_name=getattr(initial_section, "name", None) if initial_section else None,
                section_has_index=getattr(initial_section, "index_page", None) is not None
                if initial_section
                else False,
            )

        return sources

    def _compute_provenance_fast(self, page: Page) -> Provenance | None:
        """
        Fast-path provenance computation for simple content pages.

        Computes content + cascade sources + config hash.
        Returns None if page needs full provenance computation (virtual, etc.).

        This is an optimization to avoid full provenance computation for
        cache hits on regular markdown files.
        """
        # Only works for real content pages (not virtual)
        is_virtual = getattr(page, "_virtual", False)
        if is_virtual:
            return None  # Need full computation for virtual pages

        # Check if already computed for this page (fast path without lock)
        page_path = self._get_page_key(page)
        cached = self._computed_provenance.get(page_path)
        if cached is not None:
            return cached

        # Defensive check: file may have been deleted between filter start and now
        # (race condition with file watcher in dev server)
        try:
            if not page.source_path.exists():
                return None  # File missing - need full check

            # Fast path: Compute content hash
            content_hash = self._get_file_hash(page.source_path)
        except OSError:
            # File system error (deleted, permission denied, etc.)
            return None

        # Build provenance: content + cascade sources + config
        provenance = Provenance()
        provenance = provenance.with_input("content", page_path, content_hash)

        # Add cascade sources (parent _index.md files that contribute cascade metadata)
        # When any cascade source changes, page provenance changes, triggering rebuild
        cascade_sources = self._get_cascade_sources(page)
        for idx, cascade_path in enumerate(cascade_sources):
            try:
                cascade_hash = self._get_file_hash(cascade_path)
                # Use relative path for cache key stability
                rel_cascade = str(cascade_path.relative_to(self.site.root_path))
                provenance = provenance.with_input(
                    f"cascade_{idx}",
                    CacheKey(f"cascade:{rel_cascade}"),
                    cascade_hash,
                )
            except (OSError, ValueError):
                # Fall back to full computation if cascade source can't be hashed
                return None

        provenance = provenance.with_input("config", CacheKey("site_config"), self._config_hash)

        # Cache for later (record_build) - thread-safe
        with self._session_lock:
            if page_path not in self._computed_provenance:
                self._computed_provenance[page_path] = provenance
            return self._computed_provenance[page_path]

    def _compute_provenance(self, page: Page) -> Provenance:
        """Compute provenance for a page based on its inputs.

        Handles both real content pages and virtual pages:
        - Real pages: hash of source .md file
        - Autodoc pages: hash of Python source being documented
        - Taxonomy pages: hash of page list for that tag
        - Other virtual: template + metadata hash

        Also includes cascade sources (parent _index.md files) so that when
        cascade metadata changes, affected pages are rebuilt.
        """
        page_path = self._get_page_key(page)

        # Check cache first (fast path without lock)
        cached = self._computed_provenance.get(page_path)
        if cached is not None:
            return cached

        provenance = Provenance()
        rel_path = page_path

        # 1. Determine the actual source for this page
        is_virtual = getattr(page, "_virtual", False)

        if not is_virtual:
            # Real content page - hash the markdown file
            try:
                if page.source_path.exists():
                    content_hash = self._get_file_hash(page.source_path)
                    provenance = provenance.with_input("content", rel_path, content_hash)
            except OSError:
                pass  # File system error - skip content input

        elif is_virtual:
            # Virtual page - find the actual source

            # Autodoc pages: hash the Python source file
            # Uses "source_file" metadata set during autodoc extraction
            autodoc_source = page.metadata.get("source_file")
            if autodoc_source and page.metadata.get("is_autodoc"):
                source_path = (
                    Path(autodoc_source) if isinstance(autodoc_source, str) else autodoc_source
                )
                # Resolve relative paths from site root
                if not source_path.is_absolute():
                    # Try site root first
                    candidate = self.site.root_path / source_path
                    if candidate.exists():
                        source_path = candidate
                    else:
                        # Try parent (repo root)
                        candidate = self.site.root_path.parent / source_path
                        if candidate.exists():
                            source_path = candidate

                if source_path.exists():
                    source_hash = self._get_file_hash(source_path)
                    # Use relative path for cache key stability
                    try:
                        # Try relative to site root first
                        rel_source = str(source_path.relative_to(self.site.root_path))
                    except ValueError:
                        try:
                            # Try relative to repo root
                            rel_source = str(source_path.relative_to(self.site.root_path.parent))
                        except ValueError:
                            # Fallback to absolute path string
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
                    source_hash = self._get_file_hash(source_path)
                    provenance = provenance.with_input(
                        "cli_source",
                        CacheKey(str(source_path)),
                        source_hash,
                    )

            # Fallback for other virtual pages: use template + title hash
            if provenance.input_count == 0:
                template = (
                    page.metadata.get("template")
                    or page.metadata.get("_autodoc_template")
                    or "default"
                )
                title = page.metadata.get("title") or rel_path
                fallback_hash = hash_content(f"{template}:{title}")
                provenance = provenance.with_input("virtual", rel_path, fallback_hash)

        # 2. Cascade sources (parent _index.md files that contribute cascade metadata)
        # When any cascade source changes, page provenance changes, triggering rebuild
        cascade_sources = self._get_cascade_sources(page)
        for idx, cascade_path in enumerate(cascade_sources):
            try:
                cascade_hash = self._get_file_hash(cascade_path)
                # Use relative path for cache key stability
                rel_cascade = str(cascade_path.relative_to(self.site.root_path))
                provenance = provenance.with_input(
                    f"cascade_{idx}",
                    CacheKey(f"cascade:{rel_cascade}"),
                    cascade_hash,
                )
            except (OSError, ValueError):
                pass  # Skip if cascade source can't be hashed

        # 3. Site config (affects all pages)
        provenance = provenance.with_input("config", CacheKey("site_config"), self._config_hash)

        # Cache for later - thread-safe
        with self._session_lock:
            if page_path not in self._computed_provenance:
                self._computed_provenance[page_path] = provenance
            return self._computed_provenance[page_path]

    def _get_page_key(self, page: Page) -> CacheKey:
        """Get canonical page key for cache lookups."""
        return content_key(page.source_path, self.site.root_path)

    def _is_asset_changed(self, asset: Asset) -> bool:
        """
        Check if an asset has changed based on content hash.

        OPTIMIZATION: Uses mtime check first to avoid hashing unchanged files.

        Thread Safety:
            Uses local variables for hash comparisons. Asset hash dict
            updates are safe because each asset has a unique key.
        """
        try:
            if not asset.source_path.exists():
                return True
        except OSError:
            return True  # File system error - treat as changed

        asset_path = self._get_asset_key(asset)
        stored_hash = self._asset_hashes.get(asset_path)

        # OPTIMIZATION: If we have a stored hash, check mtime first
        # This avoids expensive file hashing for unchanged files
        if stored_hash is not None:
            try:
                # Get mtime for quick check (much faster than hashing)
                _ = asset.source_path.stat().st_mtime
                # For now, we still hash to be safe, but we could cache mtime too
            except OSError:
                return True  # File error - treat as changed

        # Compute hash (necessary for correctness)
        try:
            current_hash = self._get_file_hash(asset.source_path)
        except OSError:
            return True  # File error - treat as changed

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

    def _record_asset_hash(self, asset: Asset) -> None:
        """
        Record an asset's hash without checking if changed.

        Used during full builds to populate the asset hash cache for
        subsequent incremental builds. Without this, the first incremental
        build after a full build would see all assets as "changed".
        """
        try:
            if not asset.source_path.exists():
                return
            current_hash = self._get_file_hash(asset.source_path)
            asset_key = self._get_asset_key(asset)
            self._asset_hashes[asset_key] = current_hash
        except OSError:
            pass  # Skip assets that can't be hashed

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

    def get_affected_by(self, input_hash: ContentHash) -> set[CacheKey]:
        """
        Subvenance query: What pages depend on this input?

        Use for debugging and understanding dependencies.
        """
        return self.cache.get_affected_by(input_hash)
