"""
Cache initialization and persistence for incremental builds.

Handles loading, saving, and migration of build cache.
Extracted from IncrementalOrchestrator for single responsibility.

Key Concepts:
- Cache loading: Load existing cache or create fresh instance
- Cache migration: Migrate legacy cache from output_dir/.bengal-cache.json
- Cache saving: Persist cache after build completion

Related Modules:
- bengal.cache.build_cache: Build cache dataclass
- bengal.build.tracking: Dependency graph construction

"""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import TYPE_CHECKING

from bengal.utils.observability.logger import get_logger

if TYPE_CHECKING:
    from bengal.build.tracking import DependencyTracker
    from bengal.cache import BuildCache
    from bengal.core.asset import Asset
    from bengal.core.page import Page
    from bengal.core.site import Site
    from bengal.orchestration.build.coordinator import CacheCoordinator

logger = get_logger(__name__)


class CacheManager:
    """
    Manages cache initialization, loading, saving, and migration.

    Extracted from IncrementalOrchestrator to handle all cache-related
    operations in a single focused class.

    Attributes:
        site: Site instance for cache operations
        cache: BuildCache instance (None until initialized)
        tracker: DependencyTracker instance (None until initialized)
        coordinator: CacheCoordinator instance for unified invalidation (None until initialized)

    Example:
            >>> manager = CacheManager(site)
            >>> cache, tracker = manager.initialize(enabled=True)
            >>> # ... build operations ...
            >>> manager.save(pages_built, assets_processed)

    """

    def __init__(self, site: Site) -> None:
        """
        Initialize cache manager.

        Args:
            site: Site instance for cache operations
        """
        self.site = site
        self.cache: BuildCache | None = None
        self.tracker: DependencyTracker | None = None
        self.coordinator: CacheCoordinator | None = None

    def initialize(self, enabled: bool = False) -> tuple[BuildCache, DependencyTracker]:
        """
        Initialize cache and dependency tracker for incremental builds.

        Sets up BuildCache, DependencyTracker, and CacheCoordinator instances.
        If enabled, loads existing cache from .bengal/cache.json (migrates from
        legacy location if needed). If disabled, creates empty cache instances.

        Args:
            enabled: Whether incremental builds are enabled. If False, creates
                    empty cache instances (full rebuilds always).

        Returns:
            Tuple of (BuildCache, DependencyTracker) instances

        Process:
            1. Create .bengal/ directory if enabled
            2. Migrate legacy cache from output_dir/.bengal-cache.json if exists
            3. Load or create BuildCache instance
            4. Create DependencyTracker with cache and site
            5. Create CacheCoordinator for unified invalidation

        Example:
            >>> cache, tracker = manager.initialize(enabled=True)
            >>> # Cache loaded from .bengal/cache.json if exists
        """
        from bengal.build.tracking import DependencyTracker
        from bengal.cache import BuildCache
        from bengal.orchestration.build.coordinator import CacheCoordinator

        paths = self.site.paths
        cache_path = paths.build_cache

        if enabled:
            paths.state_dir.mkdir(parents=True, exist_ok=True)

            # Migrate legacy cache from output_dir if exists
            old_cache_path = self.site.output_dir / ".bengal-cache.json"

            if old_cache_path.exists() and not cache_path.exists():
                try:
                    shutil.copy2(old_cache_path, cache_path)
                    logger.info(
                        "cache_migrated",
                        from_location=str(old_cache_path),
                        to_location=str(cache_path),
                        action="automatic_migration",
                    )
                except Exception as e:
                    logger.warning(
                        "cache_migration_failed", error=str(e), action="using_fresh_cache"
                    )
            self.cache = BuildCache.load(cache_path)
            cache_exists = cache_path.exists()
            try:
                file_count = len(self.cache.file_fingerprints)
            except (AttributeError, TypeError):
                file_count = 0
            logger.info(
                "cache_initialized",
                enabled=True,
                cache_loaded=cache_exists,
                cached_files=file_count,
                cache_location=str(cache_path),
            )
        else:
            self.cache = BuildCache()
            logger.debug("cache_initialized", enabled=False)

        self.tracker = DependencyTracker(self.cache, self.site)

        # Initialize CacheCoordinator for unified page-level invalidation
        # RFC: rfc-cache-invalidation-architecture
        self.coordinator = CacheCoordinator(self.cache, self.tracker, self.site)

        return self.cache, self.tracker

    def check_config_changed(self) -> bool:
        """
        Check if configuration has changed (requires full rebuild).

        Uses config hash validation which captures the *effective* configuration state:
        - Base config from files (bengal.toml, config/*.yaml)
        - Environment variable overrides (BENGAL_*)
        - Build profile settings (--profile writer)

        This is more robust than file-based tracking because it detects changes
        in split config files, env vars, and profiles that wouldn't trigger
        a file hash change.

        Returns:
            True if config changed (cache was invalidated)
        """
        if not self.cache:
            return False

        config_hash = self.site.config_hash
        is_valid = self.cache.validate_config(config_hash)

        if not is_valid:
            logger.info(
                "config_changed_via_hash",
                new_hash=config_hash[:8],
                reason="effective_config_modified",
            )
            return True

        # Track config files for logging (hash is authoritative for invalidation)
        config_files = [
            self.site.root_path / "bengal.toml",
            self.site.root_path / "bengal.yaml",
            self.site.root_path / "bengal.yml",
        ]
        config_file = next((f for f in config_files if f.exists()), None)

        if config_file:
            self.cache.update_file(config_file)

        return False

    def save(self, pages_built: list[Page], assets_processed: list[Asset]) -> None:
        """
        Update cache with processed files.

        Flushes deferred fingerprint updates before saving cache.

        Args:
            pages_built: Pages that were built
            assets_processed: Assets that were processed
        """
        if not self.cache:
            return

        # Use same cache location as initialize()
        paths = self.site.paths
        paths.state_dir.mkdir(parents=True, exist_ok=True)
        cache_path = paths.build_cache

        # Track autodoc source files that were used in this build
        autodoc_source_files_updated: set[str] = set()

        # Update all page hashes and tags (skip virtual/generated pages)
        for page in pages_built:
            # For autodoc pages, update the source file hash (not the virtual source_path)
            if page.metadata.get("is_autodoc"):
                source_file = page.metadata.get("source_file")
                if source_file and source_file not in autodoc_source_files_updated:
                    source_path = Path(source_file)
                    if source_path.exists():
                        self.cache.update_file(source_path)
                        autodoc_source_files_updated.add(source_file)
                continue

            # Skip virtual pages (no source file) and generated pages
            if page.is_virtual or page.metadata.get("_generated"):
                continue
            self.cache.update_file(page.source_path)
            # Store tags for next build's comparison
            if page.tags:
                self.cache.update_tags(page.source_path, set(page.tags))
            else:
                self.cache.update_tags(page.source_path, set())

        # Update all asset hashes
        for asset in assets_processed:
            self.cache.update_file(asset.source_path)

        # Store discovered assets in cache for next build session
        # Enables skipping asset discovery walk during hot reload if no assets changed.
        if hasattr(self.site, "assets") and self.site.assets:
            self.cache.discovered_assets = {}
            for asset in self.site.assets:
                try:
                    rel_src = str(asset.source_path.relative_to(self.site.root_path))
                    self.cache.discovered_assets[rel_src] = str(asset.output_path)
                except ValueError:
                    # Asset outside root (theme asset), skip for now or store absolute
                    continue

        # Save URL claims to cache for incremental build safety
        if hasattr(self.site, "url_registry") and self.site.url_registry:
            try:
                self.cache.url_claims = self.site.url_registry.to_dict()
                logger.debug(
                    "url_claims_saved_to_cache",
                    claim_count=len(self.cache.url_claims),
                )
            except Exception as e:
                logger.debug(
                    "url_claims_cache_save_failed",
                    error=str(e),
                    error_type=type(e).__name__,
                    action="continuing_without_caching_claims",
                )

        # Update template hashes (even if not changed, to track them)
        theme_templates_dir = self._get_theme_templates_dir()
        if theme_templates_dir and theme_templates_dir.exists():
            for template_file in theme_templates_dir.rglob("*.html"):
                self.cache.update_file(template_file)

        # Update data file fingerprints for incremental detection
        # Without this, data files always appear "changed" on incremental builds
        # because they have no cached fingerprint to compare against.
        self._update_data_file_fingerprints()

        # Flush deferred fingerprint updates before saving.
        # This ensures fingerprints reflect post-build state, not mid-build state.
        if self.tracker:
            self.tracker.flush_pending_updates()

        # Save cache
        self.cache.save(cache_path)

    def _get_theme_templates_dir(self) -> Path | None:
        """
        Get the templates directory for the current theme.

        Returns:
            Path to theme templates or None if not found
        """
        # Be defensive: site.theme may be None, a string, or a Mock in tests
        theme = self.site.theme
        if not theme or not isinstance(theme, str):
            return None

        # Check in site's themes directory first
        site_theme_dir = self.site.root_path / "themes" / theme / "templates"
        if site_theme_dir.exists():
            return site_theme_dir

        # Check in Bengal's bundled themes
        import bengal

        assert bengal.__file__ is not None, "bengal module has no __file__"
        bengal_dir = Path(bengal.__file__).parent
        bundled_theme_dir = bengal_dir / "themes" / theme / "templates"
        if bundled_theme_dir.exists():
            return bundled_theme_dir

        return None

    def _update_data_file_fingerprints(self) -> None:
        """
        Update fingerprints for all data files.

        This is critical for incremental builds: without cached fingerprints,
        data files always appear "changed" which triggers conservative full
        rebuild of all pages.

        Scans data/ directory for .yaml, .yml, .json, .toml files and
        updates their fingerprints in the cache.
        """
        if not self.cache:
            return

        data_dir = self.site.root_path / "data"
        if not data_dir.exists():
            return

        # Same extensions as DataFileDetector
        data_extensions = frozenset({".yaml", ".yml", ".json", ".toml"})
        updated_count = 0

        for data_file in data_dir.rglob("*"):
            if not data_file.is_file():
                continue
            if data_file.suffix not in data_extensions:
                continue
            self.cache.update_file(data_file)
            updated_count += 1

        if updated_count > 0:
            logger.debug(
                "data_file_fingerprints_updated",
                count=updated_count,
            )
