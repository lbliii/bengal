"""
Provenance-based incremental filter.

Replaces IncrementalFilterEngine with content-addressed provenance checking.

Thread Safety:
    The ProvenanceFilter uses thread-safe session caches (_file_hashes,
    _computed_provenance) protected by _session_lock. ProvenanceCache is
    thread-safe. Parallel provenance computation is supported for large sites.
"""

from __future__ import annotations

import os
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any

from bengal.build.contracts.keys import CacheKey, content_key
from bengal.build.provenance.assets import (
    get_asset_key,
    get_file_hash,
    is_asset_changed,
    is_forced_by_dependency,
    load_asset_hashes,
    record_asset_hash,
    save_asset_hashes,
)
from bengal.build.provenance.inputs import (
    add_data_inputs,
    add_template_inputs,
    collect_affected,
    extract_input_paths_for_mtime,
    get_cascade_sources,
    looks_like_template_name,
    render_dependencies_for_page,
    resolve_data_dependency,
    resolve_template_path,
    template_names_for_page,
)
from bengal.build.provenance.types import (
    ContentHash,
    Provenance,
    ProvenanceRecord,
    hash_content,
    hash_dict,
)
from bengal.core.section.utils import get_page_section
from bengal.utils.observability.logger import get_logger

logger = get_logger(__name__)

if TYPE_CHECKING:
    from collections.abc import Sequence

    from bengal.build.provenance.store import ProvenanceCache
    from bengal.core.asset import Asset
    from bengal.core.site import Site
    from bengal.protocols.core import PageLike


@dataclass(frozen=True, slots=True)
class ProvenanceFilterResult:
    """Result of provenance-based filtering."""

    # Pages that need to be built
    pages_to_build: list[PageLike]

    # Assets that need to be processed
    assets_to_process: list[Asset]

    # Pages that were skipped (cache hits)
    pages_skipped: list[PageLike]

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
        self._build_started_at = time.time()
        self._build_started_at_ns = time.time_ns()

        # Precompute site config hash (affects all pages)
        self._config_hash = hash_dict(dict(site.config))

        # Asset hash tracking (loaded from cache)
        # Value: ContentHash (str) for legacy, or dict with hash, mtime, size for mtime short-circuit
        self._asset_hashes: dict[CacheKey, ContentHash | dict[str, Any]] = {}
        self._load_asset_hashes()

        # Session caches to avoid redundant I/O and computation
        # Protected by lock for thread-safe access during parallel operations
        self._file_hashes: dict[Path, ContentHash] = {}
        self._computed_provenance: dict[CacheKey, Provenance] = {}
        self._session_lock = threading.Lock()

        # Observability: mtime short-circuit hits (reset each filter())
        self._mtime_short_circuit_hits: int = 0

        # Deduplicate cascade source warnings (one per path per build)
        self._warned_cascade_paths: set[Path] = set()

        # Snapshot of render effects keyed by source page. The entry is rebuilt
        # when the tracer gains more effects during render.
        self._render_dependency_cache: tuple[int, dict[CacheKey, tuple[Path | str, ...]]] | None = (
            None
        )

    def filter(
        self,
        pages: Sequence[PageLike],
        assets: Sequence[Asset],
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
            # CRITICAL: Still compute and cache asset hashes for subsequent incremental builds
            # Without this, the next incremental build would see all assets as "changed"
            # and trigger the fingerprint cascade (forcing a full page rebuild).
            for asset in assets:
                self._record_asset_hash(asset)

            # OPTIMIZATION: Skip provenance pre-computation. We already know the answer
            # (build everything). Provenance will be computed on-demand in record_build()
            # after each page renders, avoiding a 20+ second block before parsing/assets.
            # Total work is unchanged; it's distributed to the record phase instead.

            return ProvenanceFilterResult(
                pages_to_build=list(pages),
                assets_to_process=list(assets),
                pages_skipped=[],
                total_pages=len(pages),
                cache_hits=0,
                cache_misses=len(pages),
            )

        forced = forced_changed or set()
        # Normalize forced paths to content_key for consistent comparison.
        # Watcher uses absolute Paths; discovery uses relative. Both must match.
        forced_keys: set[str] = {content_key(p.resolve(), self.site.root_path) for p in forced}

        self._mtime_short_circuit_hits = 0

        pages_to_build: list[PageLike] = []
        pages_skipped: list[PageLike] = []
        affected_tags: set[str] = set()
        affected_sections: set[str] = set()
        changed_page_paths: set[Path] = set()

        # Phase 1: Quick classification - collect pages needing provenance check
        pages_to_verify: list[tuple[PageLike, ContentHash]] = []
        for page in pages:
            page_path = self._get_page_key(page)

            if page_path in forced_keys:
                pages_to_build.append(page)
                changed_page_paths.add(page.source_path)
                self._collect_affected(page, affected_tags, affected_sections)
                continue

            stored_hash = self.cache.get_stored_hash(page_path)
            if stored_hash is None:
                pages_to_build.append(page)
                changed_page_paths.add(page.source_path)
                self._collect_affected(page, affected_tags, affected_sections)
                continue

            pages_to_verify.append((page, stored_hash))

        # Phase 2: Verify cache validity - parallel when many pages
        parallel_threshold = 100
        if len(pages_to_verify) >= parallel_threshold:
            from bengal.utils.concurrency.work_scope import WorkScope

            max_workers = min(32, (os.cpu_count() or 1) + 4)
            with WorkScope("provenance-verify", max_workers=max_workers) as scope:
                results = scope.map(
                    lambda item: self._verify_page_provenance(item[0], item[1]),
                    pages_to_verify,
                )
                for r, (page, _) in zip(results, pages_to_verify, strict=True):
                    if r.error:
                        raise r.error
                    assert r.value is not None  # guarded by r.error check above
                    build, skip, tags, sections, paths, cascade_invalidated = r.value
                    if cascade_invalidated:
                        page._cascade_invalidated = True
                    if build is not None:
                        pages_to_build.append(build)
                        affected_tags.update(tags)
                        affected_sections.update(sections)
                        changed_page_paths.update(paths)
                    if skip is not None:
                        pages_skipped.append(skip)
        else:
            for page, stored_hash in pages_to_verify:
                build, skip, tags, sections, paths, cascade_invalidated = (
                    self._verify_page_provenance(page, stored_hash)
                )
                if cascade_invalidated:
                    page._cascade_invalidated = True
                if build is not None:
                    pages_to_build.append(build)
                    affected_tags.update(tags)
                    affected_sections.update(sections)
                    changed_page_paths.update(paths)
                if skip is not None:
                    pages_skipped.append(skip)

        # For assets, check file modification or forced change
        # Include assets when: direct path match, dependency changed (e.g. @import'd CSS), or hash changed
        assets_to_process: list[Asset] = [
            asset
            for asset in assets
            if content_key(asset.source_path, self.site.root_path) in forced_keys
            or self._is_forced_by_dependency(asset, forced)
            or self._is_asset_changed(asset)
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

    def _mtime_short_circuit(self, page: PageLike, stored_hash: ContentHash) -> bool:
        """
        Try to skip verification via mtime check. Returns True if cache hit.

        If BENGAL_PROVENANCE_MTIME=0, always returns False (disabled).
        """
        if os.environ.get("BENGAL_PROVENANCE_MTIME", "1") == "0":
            return False

        page_path = self._get_page_key(page)
        input_paths = self.cache.get_input_paths(page_path)
        last_build = self.cache.get_last_build_time()
        last_build_ns = self.cache.get_last_build_time_ns()

        if not input_paths or last_build is None:
            return False

        for rel_path in input_paths:
            found = False
            for base in (self.site.root_path, self.site.root_path.parent):
                full_path = base / rel_path
                try:
                    if full_path.exists():
                        found = True
                        stat = full_path.stat()
                        if last_build_ns is not None:
                            changed_after_build = stat.st_mtime_ns > last_build_ns
                        else:
                            changed_after_build = stat.st_mtime > last_build
                        if changed_after_build:
                            return False  # File changed, need full verification
                        break
                except OSError:
                    return False  # File error, do full verification
            if not found:
                return False  # File missing, do full verification
        return True

    def _verify_page_provenance(
        self,
        page: PageLike,
        stored_hash: ContentHash,
    ) -> tuple[PageLike | None, PageLike | None, set[str], set[str], set[Path], bool]:
        """
        Verify if cached provenance still matches. Thread-safe.

        Returns:
            (page_to_build, page_to_skip, affected_tags, affected_sections,
             changed_paths, cascade_invalidated)
            Exactly one of page_to_build or page_to_skip is non-None.
        """
        tags: set[str] = set()
        sections: set[str] = set()
        paths: set[Path] = set()
        cascade_invalidated = False
        page_path = self._get_page_key(page)
        is_virtual = getattr(page, "virtual", False)

        # mtime short-circuit: skip hashing if no input file changed since last build
        if self._mtime_short_circuit(page, stored_hash):
            with self._session_lock:
                self._mtime_short_circuit_hits += 1
            return (None, page, tags, sections, paths, cascade_invalidated)

        if not is_virtual and page.source_path.exists():
            provenance_fast = self._compute_provenance_fast(page)
            if provenance_fast is not None and provenance_fast.combined_hash == stored_hash:
                return (None, page, tags, sections, paths, cascade_invalidated)
            if provenance_fast is not None:
                cascade_invalidated = True

        try:
            provenance = self._compute_provenance(page)
        except Exception as e:
            logger.debug(
                "provenance_computation_failed",
                page_path=str(page_path),
                error=str(e),
                is_virtual=is_virtual,
            )
            self._collect_affected(page, tags, sections)
            paths.add(page.source_path)
            return (page, None, tags, sections, paths, cascade_invalidated)

        if provenance.input_count == 0:
            logger.warning(
                "empty_provenance_computed",
                page_path=str(page_path),
                is_virtual=is_virtual,
                suggestion="Page may have no valid source - treating as cache miss",
            )
            self._collect_affected(page, tags, sections)
            paths.add(page.source_path)
            return (page, None, tags, sections, paths, cascade_invalidated)

        if provenance.combined_hash == stored_hash:
            return (None, page, tags, sections, paths, cascade_invalidated)
        self._collect_affected(page, tags, sections)
        paths.add(page.source_path)
        return (page, None, tags, sections, paths, cascade_invalidated)

    def record_build(self, page: PageLike, output_hash: ContentHash | None = None) -> None:
        """
        Record provenance after a page is built (thread-safe).

        Call this after rendering each page to update the cache.
        Records provenance for both real and virtual pages.

        Args:
            page: The page that was built
            output_hash: Hash of the rendered output (optional)
        """
        record_with_paths = self.build_record(page, output_hash)
        if record_with_paths is None:
            return
        record, input_paths = record_with_paths
        self.cache.store(record, input_paths)

    def build_record(
        self, page: PageLike, output_hash: ContentHash | None = None
    ) -> tuple[ProvenanceRecord, list[str]] | None:
        """Build a provenance record without persisting it."""
        page_path = self._get_page_key(page)
        # Recompute after rendering so provenance captures dependencies observed
        # during this render (template includes and data files), not just the
        # pre-render verification snapshot.
        with self._session_lock:
            self._computed_provenance.pop(page_path, None)
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
                is_virtual=getattr(page, "virtual", False),
                has_section=get_page_section(page) is not None,
                source_path=str(getattr(page, "source_path", None)),
            )
            return None

        record = ProvenanceRecord(
            page_path=page_path,
            provenance=provenance,
            output_hash=output_hash or ContentHash("_rendered_"),
        )
        input_paths = self._extract_input_paths_for_mtime(record)
        return record, input_paths

    def save(self) -> None:
        """Save the provenance cache to disk."""
        self.cache.save(
            last_build_time=self._build_started_at,
            last_build_time_ns=self._build_started_at_ns,
        )
        self._save_asset_hashes()

    def _load_asset_hashes(self) -> None:
        load_asset_hashes(self)

    def _save_asset_hashes(self) -> None:
        save_asset_hashes(self)

    def _get_file_hash(self, path: Path) -> ContentHash:
        return get_file_hash(self, path)

    def _get_cascade_sources(self, page: PageLike) -> list[Path]:
        return get_cascade_sources(self, page)

    def _template_names_for_page(self, page: PageLike) -> set[str]:
        return template_names_for_page(self, page)

    def _looks_like_template_name(self, value: str) -> bool:
        return looks_like_template_name(value)

    def _resolve_template_path(self, template_name: str) -> Path | None:
        return resolve_template_path(self, template_name)

    def _add_template_inputs(self, provenance: Provenance, page: PageLike) -> Provenance:
        return add_template_inputs(self, provenance, page)

    def _render_dependencies_for_page(self, page: PageLike) -> tuple[Path | str, ...]:
        return render_dependencies_for_page(self, page)

    def _resolve_data_dependency(self, dependency: Path) -> Path | None:
        return resolve_data_dependency(self, dependency)

    def _add_data_inputs(self, provenance: Provenance, page: PageLike) -> Provenance:
        return add_data_inputs(self, provenance, page)

    def _compute_provenance_fast(self, page: PageLike) -> Provenance | None:
        """
        Fast-path provenance computation for simple content pages.

        Computes content + cascade sources + config hash.
        Returns None if page needs full provenance computation (virtual, etc.).

        This is an optimization to avoid full provenance computation for
        cache hits on regular markdown files.
        """
        # Only works for real content pages (not virtual)
        is_virtual = getattr(page, "virtual", False)
        if is_virtual:
            return None  # Need full computation for virtual pages

        # Check if already computed for this page.
        page_path = self._get_page_key(page)
        with self._session_lock:
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
            except OSError, ValueError:
                # Fall back to full computation if cascade source can't be hashed
                return None

        provenance = self._add_template_inputs(provenance, page)
        provenance = self._add_data_inputs(provenance, page)

        provenance = provenance.with_input("config", CacheKey("site_config"), self._config_hash)

        # Cache for later (record_build) - thread-safe
        with self._session_lock:
            if page_path not in self._computed_provenance:
                self._computed_provenance[page_path] = provenance
            return self._computed_provenance[page_path]

    def _compute_provenance(self, page: PageLike) -> Provenance:
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

        # Check cache first.
        with self._session_lock:
            cached = self._computed_provenance.get(page_path)
        if cached is not None:
            return cached

        provenance = Provenance()
        rel_path = page_path

        # 1. Determine the actual source for this page
        is_virtual = getattr(page, "virtual", False)

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
            except OSError, ValueError:
                pass  # Skip if cascade source can't be hashed

        # 3. Render-time dependencies observed while rendering this page.
        provenance = self._add_template_inputs(provenance, page)
        provenance = self._add_data_inputs(provenance, page)

        # 4. Site config (affects all pages)
        provenance = provenance.with_input("config", CacheKey("site_config"), self._config_hash)

        # Cache for later - thread-safe
        with self._session_lock:
            if page_path not in self._computed_provenance:
                self._computed_provenance[page_path] = provenance
            return self._computed_provenance[page_path]

    def _get_page_key(self, page: PageLike) -> CacheKey:
        """Get canonical page key for cache lookups."""
        return content_key(page.source_path, self.site.root_path)

    def _extract_input_paths_for_mtime(self, record: ProvenanceRecord) -> list[str]:
        return extract_input_paths_for_mtime(self, record)

    def _is_forced_by_dependency(self, asset: Asset, forced: set[Path]) -> bool:
        return is_forced_by_dependency(self, asset, forced)

    def _is_asset_changed(self, asset: Asset) -> bool:
        return is_asset_changed(self, asset)

    def _get_asset_key(self, asset: Asset) -> CacheKey:
        return get_asset_key(self, asset)

    def _record_asset_hash(self, asset: Asset) -> None:
        record_asset_hash(self, asset)

    def _collect_affected(
        self,
        page: PageLike,
        affected_tags: set[str],
        affected_sections: set[str],
    ) -> None:
        collect_affected(page, affected_tags, affected_sections)

    def stats(self) -> dict[str, Any]:
        """Get cache statistics."""
        return self.cache.stats()

    def get_affected_by(self, input_hash: ContentHash) -> set[CacheKey]:
        """
        Subvenance query: What pages depend on this input?

        Use for debugging and understanding dependencies.
        """
        return self.cache.get_affected_by(input_hash)
