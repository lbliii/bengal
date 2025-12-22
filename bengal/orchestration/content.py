"""
Content discovery and setup orchestration for Bengal SSG.

Handles content and asset discovery, page/section reference setup, cascading
frontmatter, and cross-reference indexing. This orchestrator is responsible
for populating the Site with all content before rendering.

Key Responsibilities:
    Content Discovery
        Discovers pages and sections from the content/ directory, supports
        lazy loading with PageProxy for incremental builds
    Asset Discovery
        Discovers site and theme assets from assets/ directories
    Page References
        Sets up navigation references (next, prev, parent, children) between
        pages and their sections
    Cascade Application
        Applies cascading frontmatter from section _index.md files to
        descendant pages
    Cross-Reference Index
        Builds O(1) lookup indexes for cross-references by path, slug, ID,
        heading, and anchor

Build Phases:
    The ContentOrchestrator is called during Phase 2 of the build pipeline.
    It must complete before taxonomies, menus, or rendering can proceed.

Thread Safety:
    Not thread-safe. Discovery runs on the main thread before parallel
    rendering begins.

Related Modules:
    bengal.discovery.content_discovery: Low-level content discovery
    bengal.discovery.asset_discovery: Low-level asset discovery
    bengal.core.cascade_engine: Cascade application logic

See Also:
    bengal.orchestration.build: Build coordinator that calls this orchestrator
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any

from bengal.utils.logger import get_logger

if TYPE_CHECKING:
    from bengal.core.site import Site
    from bengal.utils.build_context import BuildContext

logger = get_logger(__name__)


class ContentOrchestrator:
    """
    Handles content and asset discovery.

    Responsibilities:
        - Discover content (pages and sections)
        - Discover assets (site and theme)
        - Set up page/section references for navigation
        - Apply cascading frontmatter from sections to pages
    """

    def __init__(self, site: Site):
        """
        Initialize content orchestrator.

        Args:
            site: Site instance to populate with content
        """
        self.site = site
        self.logger = get_logger(__name__)

    def discover(
        self,
        incremental: bool = False,
        cache: Any | None = None,
        build_context: BuildContext | None = None,
        build_cache: Any | None = None,
    ) -> None:
        """
        Discover all content and assets.

        Main entry point called during build.

        Args:
            incremental: Whether this is an incremental build (enables lazy loading)
            cache: PageDiscoveryCache instance (required if incremental=True)
            build_context: Optional BuildContext for caching content during discovery.
                          When provided, raw file content is cached for later use by
                          validators, eliminating redundant disk I/O during health checks.
            build_cache: Optional BuildCache for registering autodoc dependencies.
                        When provided, enables selective autodoc rebuilds.
        """
        self.discover_content(
            incremental=incremental,
            cache=cache,
            build_context=build_context,
            build_cache=build_cache,
        )
        self.discover_assets()

    def discover_content(
        self,
        content_dir: Path | None = None,
        incremental: bool = False,
        cache: Any | None = None,
        build_context: BuildContext | None = None,
        build_cache: Any | None = None,
    ) -> None:
        """
        Discover all content (pages, sections) in the content directory.

        Supports optional lazy loading with PageProxy for incremental builds.
        When build_context is provided, raw file content is cached for later
        use by validators (build-integrated validation).

        Args:
            content_dir: Content directory path (defaults to root_path/content)
            incremental: Whether this is an incremental build (enables lazy loading)
            cache: PageDiscoveryCache instance (required if incremental=True)
            build_context: Optional BuildContext for caching content during discovery.
                          When provided, raw file content is cached for later use by
                          validators, eliminating redundant disk I/O during health checks.
            build_cache: Optional BuildCache for registering autodoc dependencies.
                        When provided, enables selective autodoc rebuilds.
        """
        if content_dir is None:
            content_dir = self.site.root_path / "content"

        # Ensure absolute path - relative paths break URL computation silently
        if not content_dir.is_absolute():
            content_dir = content_dir.resolve()
            self.logger.debug(
                "content_dir_resolved_to_absolute",
                original=str(content_dir),
                resolved=str(content_dir),
            )

        if not content_dir.exists():
            self.logger.warning("content_dir_not_found", path=str(content_dir))
            return

        self.logger.debug(
            "discovering_content",
            path=str(content_dir),
            incremental=incremental,
            use_cache=incremental and cache is not None,
        )

        import time

        from bengal.collections import load_collections
        from bengal.discovery.content_discovery import ContentDiscovery

        breakdown_ms: dict[str, float] = {}
        overall_start = time.perf_counter()

        # Load collection schemas from project root (if collections.py exists)
        t0 = time.perf_counter()
        collections = load_collections(self.site.root_path)
        breakdown_ms["collections"] = (time.perf_counter() - t0) * 1000

        # Check if strict validation is enabled
        build_config = (
            self.site.config.get("build", {}) if isinstance(self.site.config, dict) else {}
        )
        strict_validation = build_config.get("strict_collections", False)

        t0 = time.perf_counter()
        discovery = ContentDiscovery(
            content_dir,
            site=self.site,
            collections=collections,
            strict_validation=strict_validation,
            build_context=build_context,
        )
        breakdown_ms["content_discovery_init"] = (time.perf_counter() - t0) * 1000

        # Use lazy loading if incremental build with cache
        use_cache = incremental and cache is not None
        t0 = time.perf_counter()
        self.site.sections, self.site.pages = discovery.discover(use_cache=use_cache, cache=cache)
        breakdown_ms["content_discovery"] = (time.perf_counter() - t0) * 1000

        # Note: Autodoc synthetic pages disabled - using traditional Markdown generation

        # Track how many pages are proxies (for logging)
        from bengal.core.page.proxy import PageProxy

        proxy_count = sum(1 for p in self.site.pages if isinstance(p, PageProxy))
        full_page_count = len(self.site.pages) - proxy_count

        self.logger.debug(
            "raw_content_discovered",
            pages=len(self.site.pages),
            sections=len(self.site.sections),
            proxies=proxy_count,
            full_pages=full_page_count,
        )

        # Integrate virtual autodoc pages if enabled
        # Note: Autodoc pages are NOT rendered during discovery. HTML rendering is
        # deferred to the rendering phase (after menus are built) to ensure full
        # template context (including navigation) is available.
        # Pass build_cache (not page discovery cache) for autodoc dependency registration
        t0 = time.perf_counter()
        autodoc_pages, autodoc_sections = self._discover_autodoc_content(cache=build_cache)
        breakdown_ms["autodoc"] = (time.perf_counter() - t0) * 1000
        if autodoc_pages or autodoc_sections:
            self.site.pages.extend(autodoc_pages)
            self.site.sections.extend(autodoc_sections)
            self.logger.info(
                "autodoc_virtual_pages_integrated",
                pages=len(autodoc_pages),
                sections=len(autodoc_sections),
            )

        # Build section registry for path-based lookups (MUST come before _setup_page_references)
        # This enables O(1) section lookups via page._section property
        t0 = time.perf_counter()
        self.site.register_sections()
        breakdown_ms["register_sections"] = (time.perf_counter() - t0) * 1000
        self.logger.debug("section_registry_built")

        # Set up page references for navigation
        t0 = time.perf_counter()
        self._setup_page_references()
        breakdown_ms["setup_page_references"] = (time.perf_counter() - t0) * 1000
        self.logger.debug("page_references_setup")

        # Apply cascading frontmatter from sections to pages
        t0 = time.perf_counter()
        self._apply_cascades()
        breakdown_ms["cascades"] = (time.perf_counter() - t0) * 1000
        self.logger.debug("cascades_applied")

        # Set output paths for all pages immediately after discovery
        # This ensures page.href and page._path work correctly before rendering
        t0 = time.perf_counter()
        self.site._set_output_paths()
        breakdown_ms["output_paths"] = (time.perf_counter() - t0) * 1000
        self.logger.debug("output_paths_set")

        # Build cross-reference index for O(1) lookups
        t0 = time.perf_counter()
        self._build_xref_index()
        breakdown_ms["xref_index"] = (time.perf_counter() - t0) * 1000
        self.logger.debug(
            "xref_index_built", index_size=len(self.site.xref_index.get("by_path", {}))
        )

        breakdown_ms["total"] = (time.perf_counter() - overall_start) * 1000
        # Store on Site for consumption by phase_discovery (CLI details) and debug logs.
        # This is ephemeral, per-build-only state.
        self.site._discovery_breakdown_ms = breakdown_ms

    def _discover_autodoc_content(self, cache: Any | None = None) -> tuple[list[Any], list[Any]]:
        """
        Generate virtual autodoc pages if enabled.

        Args:
            cache: Optional BuildCache for registering autodoc dependencies.
                   Enables selective rebuilding of autodoc pages in incremental builds.

        Returns:
            Tuple of (pages, sections) from virtual autodoc generation.
            Returns ([], []) if virtual autodoc is disabled.
        """
        # Performance: autodoc should be opt-in. If there is no explicit autodoc
        # configuration, avoid importing and initializing the autodoc subsystem.
        autodoc_cfg = self.site.config.get("autodoc")
        if not isinstance(autodoc_cfg, dict) or not autodoc_cfg:
            return [], []

        try:
            from bengal.autodoc.orchestration import VirtualAutodocOrchestrator
            from bengal.utils.hashing import hash_dict

            orchestrator = VirtualAutodocOrchestrator(self.site)

            if not orchestrator.is_enabled():
                self.logger.debug("virtual_autodoc_not_enabled")
                return [], []

            cache_key = "__autodoc_elements_v1"
            current_cfg_hash = hash_dict(autodoc_cfg) if isinstance(autodoc_cfg, dict) else ""

            def _is_external_autodoc_source(path: Path) -> bool:
                # We intentionally ignore dependencies that live in virtualenv / site-packages.
                # These paths can vary by interpreter/env and cause spurious incremental rebuilds.
                parts = path.parts
                return (
                    "site-packages" in parts
                    or "dist-packages" in parts
                    or ".venv" in parts
                    or ".tox" in parts
                )

            # Incremental fast path: if autodoc sources are unchanged and we have a cached
            # extraction payload, rebuild virtual pages without re-extracting.
            if (
                cache is not None
                and hasattr(cache, "get_page_cache")
                and hasattr(cache, "is_changed")
            ):
                cached_payload = cache.get_page_cache(cache_key)
                if (
                    isinstance(cached_payload, dict)
                    and cached_payload.get("version")
                    == 2  # v2: dict format for ParameterInfo/RaisesInfo
                    and cached_payload.get("autodoc_config_hash") == current_cfg_hash
                ):
                    changed = False
                    if hasattr(cache, "get_autodoc_source_files"):
                        try:
                            for source in cache.get_autodoc_source_files():
                                src_path = Path(source)
                                if _is_external_autodoc_source(src_path):
                                    continue
                                if cache.is_changed(src_path):
                                    changed = True
                                    break
                        except Exception:
                            changed = True
                    else:
                        changed = True

                    if not changed:
                        pages, sections, _run = orchestrator.generate_from_cache_payload(
                            cached_payload
                        )
                        self.logger.debug(
                            "autodoc_cache_hit",
                            pages=len(pages),
                            sections=len(sections),
                        )
                        return pages, sections

            # Tolerate both 2-tuple and 3-tuple return values
            result = orchestrator.generate()
            if len(result) == 3:
                pages, sections, run_result = result
                # Log summary if there were failures or warnings
                if run_result.has_failures() or run_result.has_warnings():
                    self._log_autodoc_summary(run_result)

                # Register autodoc dependencies with cache for selective rebuilds
                if cache is not None and hasattr(cache, "add_autodoc_dependency"):
                    for source_file, page_paths in run_result.autodoc_dependencies.items():
                        src_path = Path(source_file)
                        if _is_external_autodoc_source(src_path):
                            continue
                        for page_path in page_paths:
                            cache.add_autodoc_dependency(source_file, page_path)

                    if run_result.autodoc_dependencies:
                        self.logger.debug(
                            "autodoc_dependencies_registered",
                            source_files=len(run_result.autodoc_dependencies),
                            total_mappings=sum(
                                len(p) for p in run_result.autodoc_dependencies.values()
                            ),
                        )

                # Critical for incremental cache hits: fingerprint the autodoc source files now.
                # The incremental cache saver only sees rendered pages, and autodoc "source_file"
                # in metadata is display-oriented (may be repo-relative), so we update the cache
                # using the dependency tracker keys (absolute paths) here.
                if cache is not None and hasattr(cache, "update_file"):
                    try:
                        for source_file in run_result.autodoc_dependencies:
                            src_path = Path(source_file)
                            if _is_external_autodoc_source(src_path):
                                continue
                            if src_path.exists():
                                cache.update_file(src_path)
                    except Exception as e:
                        self.logger.debug(
                            "autodoc_source_fingerprints_update_failed",
                            error=str(e),
                            error_type=type(e).__name__,
                        )

                # Persist extraction payload for incremental cache hits.
                if cache is not None and hasattr(cache, "set_page_cache"):
                    try:
                        payload = orchestrator.get_cache_payload()
                        if (
                            isinstance(payload, dict)
                            and payload.get("version") == 1
                            and payload.get("autodoc_config_hash") == current_cfg_hash
                        ):
                            cache.set_page_cache(cache_key, payload)
                            self.logger.debug(
                                "autodoc_cache_saved",
                                types=list((payload.get("elements") or {}).keys()),
                            )
                    except Exception as e:
                        self.logger.debug(
                            "autodoc_cache_save_failed",
                            error=str(e),
                            error_type=type(e).__name__,
                        )
            else:
                # 2-tuple return
                pages, sections = result
                run_result = None

            return pages, sections

        except ImportError as e:
            self.logger.debug("autodoc_import_failed", error=str(e))
            return [], []
        # Note: Other exceptions (e.g., RuntimeError from strict mode) propagate
        # to allow strict mode enforcement. Non-strict failures are logged in summary.

    def _log_autodoc_summary(self, result: Any) -> None:
        """
        Log a summary of autodoc run results.

        Args:
            result: AutodocRunResult with counts and failure details
        """
        if not result.has_failures() and not result.has_warnings():
            return

        # Build summary message
        parts = []
        if result.extracted > 0:
            parts.append(f"{result.extracted} extracted")
        if result.rendered > 0:
            parts.append(f"{result.rendered} rendered")
        if result.failed_extract > 0:
            parts.append(f"{result.failed_extract} extraction failures")
        if result.failed_render > 0:
            parts.append(f"{result.failed_render} rendering failures")
        if result.warnings > 0:
            parts.append(f"{result.warnings} warnings")

        summary = ", ".join(parts)

        # Include sample failures if any
        failure_details = []
        if result.failed_extract_identifiers:
            sample = result.failed_extract_identifiers[:5]
            failure_details.append(f"Failed extractions: {', '.join(sample)}")
        if result.failed_render_identifiers:
            sample = result.failed_render_identifiers[:5]
            failure_details.append(f"Failed renders: {', '.join(sample)}")
        if result.fallback_pages:
            sample = result.fallback_pages[:5]
            failure_details.append(f"Fallback pages: {', '.join(sample)}")

        if failure_details:
            summary += f" ({'; '.join(failure_details)})"

        # Log at warning level if failures, info if only warnings
        if result.has_failures():
            self.logger.warning("autodoc_run_summary", summary=summary)
        else:
            self.logger.info("autodoc_run_summary", summary=summary)

    def discover_assets(self, assets_dir: Path | None = None) -> None:
        """
        Discover all assets in the assets directory and theme assets.

        Args:
            assets_dir: Assets directory path (defaults to root_path/assets)
        """
        from bengal.discovery.asset_discovery import AssetDiscovery

        self.site.assets = []
        theme_asset_count = 0
        site_asset_count = 0

        # Discover theme assets first (lower priority)
        if self.site.theme:
            theme_assets_dir = self._get_theme_assets_dir()
            if theme_assets_dir and theme_assets_dir.exists():
                self.logger.debug(
                    "discovering_theme_assets", theme=self.site.theme, path=str(theme_assets_dir)
                )
                theme_discovery = AssetDiscovery(theme_assets_dir)
                theme_assets = theme_discovery.discover()
                self.site.assets.extend(theme_assets)
                theme_asset_count = len(theme_assets)

        # Discover site assets (higher priority, can override theme assets)
        if assets_dir is None:
            assets_dir = self.site.root_path / "assets"

        if assets_dir.exists():
            self.logger.debug("discovering_site_assets", path=str(assets_dir))
            site_discovery = AssetDiscovery(assets_dir)
            site_assets = site_discovery.discover()
            self.site.assets.extend(site_assets)
            site_asset_count = len(site_assets)
        elif not self.site.assets:
            # Only warn if we have no theme assets either
            self.logger.warning("assets_dir_not_found", path=str(assets_dir))

        self.logger.debug(
            "assets_discovered",
            theme_assets=theme_asset_count,
            site_assets=site_asset_count,
            total=len(self.site.assets),
        )

    def _setup_page_references(self) -> None:
        """
        Set up page references for navigation (next, prev, parent, etc.).

        Delegates to Site._setup_page_references() for the canonical implementation.
        This ensures a single source of truth for page-section reference setup.

        See Also:
            Site._setup_page_references(): Canonical implementation
            plan/active/rfc-page-section-reference-contract.md
        """
        self.site._setup_page_references()

    def _apply_cascades(self) -> None:
        """
        Apply cascading metadata from sections to their child pages and subsections.

        Section _index.md files can define metadata that automatically applies to all
        descendant pages. This allows setting common metadata at the section level
        rather than repeating it on every page.

        Cascade metadata is defined in a section's _index.md frontmatter:

        Example:
            ---
            title: "Products"
            cascade:
              type: "product"
              version: "2.0"
              show_price: true
            ---

        All pages under this section will inherit these values unless they
        define their own values (page values take precedence over cascaded values).

        Delegates to CascadeEngine for the actual implementation and collects statistics.
        """
        from bengal.core.cascade_engine import CascadeEngine

        engine = CascadeEngine(self.site.pages, self.site.sections)
        stats = engine.apply()

        # Log cascade statistics
        if stats.get("cascade_keys_applied"):
            keys_info = ", ".join(
                f"{k}({v})" for k, v in sorted(stats["cascade_keys_applied"].items())
            )
            self.logger.info(
                "cascades_applied",
                pages_processed=stats["pages_processed"],
                pages_affected=stats["pages_with_cascade"],
                root_cascade_pages=stats["root_cascade_pages"],
                cascade_keys=keys_info,
            )
        else:
            self.logger.debug(
                "cascades_applied",
                pages_processed=stats["pages_processed"],
                pages_affected=0,
                reason="no_cascades_defined",
            )

    def _check_weight_metadata(self) -> None:
        """
        Check for documentation pages without weight metadata.

        Weight is important for sequential content like docs and tutorials
        to ensure correct navigation order. This logs info (not a warning)
        to educate users about weight metadata.
        """
        doc_types = {"doc", "tutorial", "autodoc-python", "autodoc-cli", "changelog"}

        missing_weight_pages = []
        for page in self.site.pages:
            content_type = page.metadata.get("type")
            # Skip index pages (they don't need weight for navigation)
            if (
                content_type in doc_types
                and "weight" not in page.metadata
                and page.source_path.stem not in ("_index", "index")
            ):
                missing_weight_pages.append(page)

        if missing_weight_pages:
            # Log info (not warning - it's not an error, just helpful guidance)
            page_samples = [
                str(p.source_path.relative_to(self.site.root_path))
                for p in missing_weight_pages[:5]
            ]

            self.logger.info(
                "pages_without_weight",
                count=len(missing_weight_pages),
                content_types=list(doc_types),
                samples=page_samples[:5],  # Limit to 5 samples for brevity
            )

    def _build_xref_index(self) -> None:
        """
        Build cross-reference index for O(1) page lookups.

        Creates multiple indices to support different reference styles:
        - by_path: Reference by file path (e.g., 'docs/installation')
        - by_slug: Reference by slug (e.g., 'installation')
        - by_id: Reference by custom ID from frontmatter (e.g., 'install-guide')
        - by_heading: Reference by heading text for anchor links
        - by_anchor: Reference by explicit anchor ID (e.g., {#install})

        Performance: O(n) build time, O(1) lookup time
        Thread-safe: Read-only after building, safe for parallel rendering
        """
        self.site.xref_index = {
            "by_path": {},  # 'docs/getting-started' -> Page
            "by_slug": {},  # 'getting-started' -> [Pages]
            "by_id": {},  # Custom IDs from frontmatter -> Page
            "by_heading": {},  # Heading text -> [(Page, anchor)]
            "by_anchor": {},  # Explicit anchor ID -> [(Page, anchor, version_id), ...] for [[#anchor]] resolution (version-scoped)
        }

        content_dir = self.site.root_path / "content"

        for page in self.site.pages:
            # Index by relative path (without extension)
            try:
                rel_path = page.source_path.relative_to(content_dir)
                # Remove extension and normalize path separators
                path_key = str(rel_path.with_suffix("")).replace("\\", "/")
                # Also handle _index.md -> directory path
                if path_key.endswith("/_index"):
                    path_key = path_key[:-7]  # Remove '/_index'
                self.site.xref_index["by_path"][path_key] = page
            except ValueError:
                # Page is not relative to content_dir (e.g., generated page)
                pass

            # Index by slug (multiple pages can have same slug)
            if hasattr(page, "slug") and page.slug:
                self.site.xref_index["by_slug"].setdefault(page.slug, []).append(page)

            # Index custom IDs from frontmatter
            if "id" in page.metadata:
                ref_id = page.metadata["id"]
                self.site.xref_index["by_id"][ref_id] = page

            # Index headings from TOC (for anchor links)
            # NOTE: This accesses toc_items BEFORE parsing (during discovery phase).
            # This is safe because toc_items property returns [] when toc is not set,
            # and importantly does NOT cache the empty result. After parsing, when
            # toc is set, the property will extract and cache the real structure.
            if hasattr(page, "toc_items") and page.toc_items:
                for toc_item in page.toc_items:
                    heading_text = toc_item.get("title", "").lower()
                    anchor_id = toc_item.get("id", "")
                    if heading_text and anchor_id:
                        self.site.xref_index["by_heading"].setdefault(heading_text, []).append(
                            (page, anchor_id)
                        )
                        # Also index by anchor ID for direct [[#anchor]] resolution
                        # This enables explicit {#custom-id} heading anchors to be found
                        anchor_key = anchor_id.lower()
                        page_version = getattr(page, "version", None)
                        # Store as list to support multiple versions with same anchor
                        if anchor_key not in self.site.xref_index["by_anchor"]:
                            self.site.xref_index["by_anchor"][anchor_key] = []
                        # Check for collisions within the same version only
                        existing_entries = self.site.xref_index["by_anchor"][anchor_key]
                        same_version_entry = (
                            next((p, a, v) for p, a, v in existing_entries if v == page_version)
                            if any(v == page_version for _, _, v in existing_entries)
                            else None
                        )
                        if same_version_entry:
                            # Collision within same version - warn but keep existing (target directives will overwrite later)
                            existing_page, existing_anchor, _ = same_version_entry
                            self.logger.warning(
                                "anchor_collision",
                                anchor_id=anchor_id,
                                target_page=str(getattr(page, "source_path", "unknown")),
                                existing_page=str(getattr(existing_page, "source_path", "unknown")),
                                existing_anchor=existing_anchor,
                                version=page_version or "unversioned",
                                details=(
                                    f"Heading anchor '{anchor_id}' collides within version '{page_version or 'unversioned'}'. "
                                    f"Heading in {page.source_path} conflicts with existing anchor '{existing_anchor}' "
                                    f"in {existing_page.source_path}. Target directives will take precedence if added later."
                                ),
                            )
                            # Don't add duplicate - keep existing entry
                        else:
                            # No collision - add entry
                            self.site.xref_index["by_anchor"][anchor_key].append(
                                (page, anchor_id, page_version)
                            )

            # Index target directives (:::{target} id)
            # Extract target directives from content for cross-reference indexing
            # NOTE: Target directives take precedence over heading anchors since they're explicit
            if hasattr(page, "content") and page.content:
                target_anchors = self._extract_target_directives(page.content)
                page_version = getattr(page, "version", None)
                for anchor_id in target_anchors:
                    anchor_key = anchor_id.lower()
                    # Initialize list if needed
                    if anchor_key not in self.site.xref_index["by_anchor"]:
                        self.site.xref_index["by_anchor"][anchor_key] = []

                    existing_entries = self.site.xref_index["by_anchor"][anchor_key]
                    # Check for collisions within the same version only
                    same_version_collision = any(
                        existing_version == page_version
                        for _, _, existing_version in existing_entries
                    )
                    if same_version_collision:
                        # Collision within same version - target directives take precedence
                        # Remove existing same-version entries and add target directive
                        self.site.xref_index["by_anchor"][anchor_key] = [
                            (p, a, v) for p, a, v in existing_entries if v != page_version
                        ]
                        existing_page, existing_anchor, _ = next(
                            (p, a, v) for p, a, v in existing_entries if v == page_version
                        )
                        self.logger.warning(
                            "anchor_collision",
                            anchor_id=anchor_id,
                            target_page=str(getattr(page, "source_path", "unknown")),
                            existing_page=str(getattr(existing_page, "source_path", "unknown")),
                            existing_anchor=existing_anchor,
                            version=page_version or "unversioned",
                            details=(
                                f"Target directive '::{{target}} {anchor_id}' in version '{page_version or 'unversioned'}' "
                                f"collides with existing anchor '{existing_anchor}' in {existing_page.source_path}. "
                                f"Target directive takes precedence. Use '[[!{anchor_id}]]' to explicitly reference it."
                            ),
                        )
                    # Add target directive entry (takes precedence over heading anchors in same version)
                    self.site.xref_index["by_anchor"][anchor_key].append(
                        (page, anchor_id, page_version)
                    )

    def _extract_target_directives(self, content: str) -> list[str]:
        """
        Extract target directive anchor IDs from markdown content.

        Finds all :::{target} id directives and returns their anchor IDs.
        This enables indexing target anchors for cross-reference resolution.

        Args:
            content: Markdown content to search

        Returns:
            List of anchor IDs found in target directives
        """
        import re

        anchor_ids = []
        # Pattern matches :::{target} id or :::{anchor} id
        # Handles optional whitespace and closing ::: on same or next line
        pattern = r"^(\s*):{3,}\{(?:target|anchor)\}([^\n]*)$"
        lines = content.split("\n")
        i = 0
        while i < len(lines):
            match = re.match(pattern, lines[i])
            if match:
                indent = len(match.group(1))
                # Skip if indented 4+ spaces (code block)
                if indent < 4:
                    # Extract anchor ID from title (everything after directive name)
                    title = match.group(2).strip()
                    # Validate it looks like an anchor ID (starts with letter)
                    if title and re.match(r"^[a-zA-Z][a-zA-Z0-9_-]*$", title):
                        anchor_ids.append(title)
            i += 1

        return anchor_ids

    def _get_theme_assets_dir(self) -> Path | None:
        """
        Get the assets directory for the current theme.

        Returns:
            Path to theme assets or None if not found
        """
        if not self.site.theme:
            return None

        # Check in site's themes directory first
        site_theme_dir = self.site.root_path / "themes" / self.site.theme / "assets"
        if site_theme_dir.exists():
            return site_theme_dir

        # Check in Bengal's bundled themes
        import bengal

        bengal_dir = Path(bengal.__file__).parent
        bundled_theme_dir = bengal_dir / "themes" / self.site.theme / "assets"
        if bundled_theme_dir.exists():
            return bundled_theme_dir

        return None
