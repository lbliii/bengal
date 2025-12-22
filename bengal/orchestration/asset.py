"""
Asset processing orchestration for Bengal SSG.

Handles asset copying, minification, optimization, and fingerprinting.
Coordinates parallel asset processing, generates asset manifest for
cache-busting, and manages fingerprint cleanup.

Key Concepts:
    - Parallel processing: Concurrent asset processing for performance
    - Asset manifest: JSON manifest mapping logical paths to fingerprinted files
    - Fingerprinting: Hash-based cache-busting via filename suffixes
    - Cleanup: Removal of stale fingerprinted files

Related Modules:
    - bengal.core.asset: Asset representation and processing (package)
    - bengal.assets.manifest: Asset manifest generation
    - bengal.rendering.template_engine: Template access to asset manifest

See Also:
    - bengal/orchestration/asset.py:AssetOrchestrator for orchestration logic
    - plan/active/rfc-asset-fingerprinting.md: Asset fingerprinting design
"""

from __future__ import annotations

import concurrent.futures
import time
from pathlib import Path
from threading import Lock
from typing import TYPE_CHECKING, Any

from bengal.assets.manifest import AssetManifest
from bengal.config.defaults import get_max_workers
from bengal.utils.logger import get_logger

if TYPE_CHECKING:
    from bengal.cli.progress import LiveProgressManager
    from bengal.core.asset import Asset
    from bengal.core.output import OutputCollector
    from bengal.core.site import Site

# Thread-safe output lock for parallel processing
_print_lock = Lock()


class AssetOrchestrator:
    """
    Orchestrates asset processing for static files.

    Handles asset copying, minification, optimization, and fingerprinting.
    Supports parallel processing for performance and maintains CSS entry point
    cache for efficient incremental builds.

    Creation:
        Direct instantiation: AssetOrchestrator(site)
            - Created by BuildOrchestrator during build
            - Requires Site instance with assets populated

    Attributes:
        site: Site instance containing assets and configuration
        logger: Logger instance for asset processing events
        _cached_css_entry_points: Cached CSS entry points (invalidated on asset changes)
        _cached_assets_id: Asset list identity for cache invalidation
        _cached_assets_len: Asset list length for cache invalidation

    Relationships:
        - Uses: Asset class for asset representation and processing
        - Uses: AssetManifest for cache-busting manifest generation
        - Used by: BuildOrchestrator for asset processing phase
        - Uses: ThreadPoolExecutor for parallel asset processing

    Thread Safety:
        Thread-safe for parallel asset processing. Uses thread-safe locks
        for output operations and maintains thread-local state where needed.

    Examples:
        orchestrator = AssetOrchestrator(site)
        orchestrator.process(site.assets, parallel=True, progress_manager=progress)
    """

    def __init__(self, site: Site):
        """
        Initialize asset orchestrator.

        Args:
            site: Site instance containing assets and configuration
        """
        self.site = site
        self.logger = get_logger(__name__)
        # Ephemeral cache for CSS entry points discovered from full site asset list.
        # Invalidation strategy: recompute when the site.assets identity or length changes.
        self._cached_css_entry_points: list[Asset] | None = None
        self._cached_assets_id: int | None = None
        self._cached_assets_len: int | None = None
        # Output collector for hot reload tracking (set during process())
        self._collector: OutputCollector | None = None

    def _get_site_css_entries_cached(self) -> list[Asset]:
        """
        Return cached list of CSS entry points from the full site asset list.

        This avoids repeatedly filtering the entire site assets on incremental rebuilds
        when only CSS modules changed. We use a simple invalidation signal that is
        robust under dev-server rebuilds where `Site.reset_ephemeral_state()` replaces
        `site.assets` entirely:
            - If the identity (id) of `site.assets` changes, invalidate
            - If the length changes, invalidate
        If either condition is met or cache is empty, recompute.
        """
        try:
            current_id = id(self.site.assets)
            current_len = len(self.site.assets)
        except Exception as e:
            # Defensive: if site/assets are not available yet
            self.logger.debug(
                "css_entry_cache_id_check_failed",
                error=str(e),
                error_type=type(e).__name__,
            )
            return []

        if (
            self._cached_css_entry_points is None
            or self._cached_assets_id != current_id
            or self._cached_assets_len != current_len
        ):
            try:
                self._cached_css_entry_points = [
                    a for a in self.site.assets if a.is_css_entry_point()
                ]
            except Exception as e:
                self.logger.debug(
                    "css_entry_cache_population_failed",
                    error=str(e),
                    error_type=type(e).__name__,
                )
                self._cached_css_entry_points = []
            self._cached_assets_id = current_id
            self._cached_assets_len = current_len

        return self._cached_css_entry_points

    def _record_asset_output(self, asset: Asset) -> None:
        """
        Record asset output for hot reload tracking.

        Called after successful copy_to_output() to track the asset
        in the output collector (if present).

        Args:
            asset: Asset that was just written to output
        """
        if self._collector is None:
            return

        output_path = getattr(asset, "output_path", None)
        if not isinstance(output_path, Path):
            return

        # Record using auto-detection from extension
        self._collector.record(output_path, phase="asset")

    def process(
        self,
        assets: list[Asset],
        parallel: bool = True,
        progress_manager: LiveProgressManager | None = None,
        collector: OutputCollector | None = None,
    ) -> None:
        """
        Process and copy assets to output directory.

        CSS entry points (style.css) are bundled to resolve @imports.
        CSS modules are skipped (they're bundled into entry points).
        All other assets are processed normally.

        Args:
            assets: List of assets to process
            parallel: Whether to use parallel processing
            progress_manager: Live progress manager (optional)
            collector: Optional output collector for hot reload tracking
        """
        # Store collector for use by _process_* methods
        self._collector = collector

        # Optional Node-based pipeline: compile SCSS/PostCSS and bundle JS/TS first
        try:
            from bengal.assets.pipeline import from_site as pipeline_from_site

            pipeline = pipeline_from_site(self.site)
            compiled = pipeline.build()
            if compiled:
                from bengal.core.asset import Asset

                for out_path in compiled:
                    if out_path.is_file():
                        # Register path relative to temp pipeline root; we want output under public/assets/**
                        # Compute a path relative to the temp_out_dir/assets prefix if present
                        rel = out_path
                        # Best-effort normalization: look for '/assets/' marker
                        parts = list(out_path.parts)
                        if "assets" in parts:
                            idx = parts.index("assets")
                            rel = Path(*parts[idx + 1 :])
                        assets.append(Asset(source_path=out_path, output_path=rel))
        except Exception as e:
            # Log and continue with normal asset processing
            self.logger.warning("asset_pipeline_failed", error=str(e))

        if not assets:
            self.logger.info("asset_processing_skipped", reason="no_assets")
            return

        start_time = time.time()

        # Performance: load the previous manifest once so stale fingerprint cleanup
        # can delete exact old outputs (O(1)) instead of scanning directories (glob).
        try:
            manifest_path = self.site.output_dir / "asset-manifest.json"
            self.site._asset_manifest_previous = AssetManifest.load(manifest_path)
        except Exception:
            self.site._asset_manifest_previous = None

        # Separate CSS entry points, CSS modules, and other assets
        css_entries = [a for a in assets if a.is_css_entry_point()]
        css_modules = [a for a in assets if a.is_css_module()]
        other_assets = [a for a in assets if a.asset_type != "css"]

        # Check if JS bundling is enabled
        assets_cfg = (
            self.site.config.get("assets", {})
            if isinstance(self.site.config.get("assets"), dict)
            else {}
        )
        bundle_js = assets_cfg.get("bundle_js", False)

        # Handle JS bundling if enabled
        js_bundle_asset = None
        js_modules: list[Asset] = []
        if bundle_js:
            from bengal.core.asset import Asset

            # Separate JS modules from other assets
            js_modules = [a for a in other_assets if a.is_js_module()]
            other_assets = [a for a in other_assets if not a.is_js_module()]

            # Generate bundle.js if there are modules to bundle
            if js_modules:
                js_bundle_asset = self._create_js_bundle(js_modules, assets_cfg)
                if js_bundle_asset:
                    # Add bundle to processing queue
                    other_assets.append(js_bundle_asset)

        # In incremental builds, if modules changed but no entry is queued, pull entries
        # so they get re-bundled (templates use bundled entries, not raw modules)
        if css_modules and not css_entries:
            site_entries = self._get_site_css_entries_cached()
            if site_entries:
                css_entries = site_entries
            else:
                other_assets.extend(css_modules)
                css_modules = []

        assets_cfg = (
            self.site.config.get("assets", {})
            if isinstance(self.site.config.get("assets"), dict)
            else {}
        )
        if assets_cfg.get("pipeline", False):
            skip_exts = {".scss", ".sass", ".ts", ".tsx"}
            other_assets = [
                a for a in other_assets if a.source_path.suffix.lower() not in skip_exts
            ]

        total_discovered = len(assets)
        total_output = len(css_entries) + len(other_assets)
        if not progress_manager:
            from bengal.output import CLIOutput

            cli = CLIOutput()
            cli.section("Assets")
            cli.detail(f"{cli.icons.tree_end} Discovered: {total_discovered} files", indent=1)
            if css_modules:
                cli.detail(
                    f"{cli.icons.tree_end} CSS bundling: {len(css_entries)} entry point(s), {len(css_modules)} module(s) bundled",
                    indent=1,
                )
            cli.detail(
                f"{cli.icons.tree_end} Output: {total_output} files {cli.icons.success}", indent=1
            )

        minify = self.site.config.get("minify_assets", True)
        optimize = self.site.config.get("optimize_assets", True)
        fingerprint = self.site.config.get("fingerprint_assets", True)

        # Log asset processing configuration
        self.logger.info(
            "asset_processing_start",
            total_assets=len(assets),
            css_entries=len(css_entries),
            css_modules=len(css_modules),
            other_assets=len(other_assets),
            mode="parallel" if parallel else "sequential",
            minify=minify,
            optimize=optimize,
            fingerprint=fingerprint,
        )

        # OPTIMIZATION: Process all assets concurrently if appropriate
        # We run concurrently if:
        # 1. parallel=True is requested AND
        # 2. We have enough work to justify thread overhead (>= 5 items OR mixed CSS/assets)
        # This allows CSS bundling to overlap with other asset processing

        total_items = len(css_entries) + len(other_assets)
        MIN_ITEMS_FOR_PARALLEL = 5

        should_run_parallel = parallel and (
            total_items >= MIN_ITEMS_FOR_PARALLEL
            or (len(css_entries) > 0 and len(other_assets) > 0)
        )

        if should_run_parallel:
            self._process_concurrently(
                css_entries,
                other_assets,
                minify,
                optimize,
                fingerprint,
                progress_manager,
                css_modules_count=len(css_modules),
            )
        else:
            # Sequential fallback
            self._process_sequentially(
                css_entries,
                other_assets,
                minify,
                optimize,
                fingerprint,
                progress_manager,
                css_modules_count=len(css_modules),
            )

        # Log completion metrics
        duration_ms = (time.time() - start_time) * 1000
        self.logger.info(
            "asset_processing_complete",
            assets_processed=len(assets),
            output_files=total_output,
            duration_ms=duration_ms,
            throughput=len(assets) / (duration_ms / 1000) if duration_ms > 0 else 0,
        )
        self._write_asset_manifest(assets)

        # Clear collector reference
        self._collector = None

    def _process_concurrently(
        self,
        css_entries: list[Asset],
        other_assets: list[Asset],
        minify: bool,
        optimize: bool,
        fingerprint: bool,
        progress_manager: LiveProgressManager | None,
        css_modules_count: int,
    ) -> None:
        """
        Process CSS and other assets concurrently using a shared thread pool.
        """
        assets_output = self.site.output_dir / "assets"
        total_assets = len(css_entries) + len(other_assets)
        # Use configured max_workers, or auto-detect with asset-aware bound
        config_workers = self.site.config.get("max_workers")
        max_workers = (
            get_max_workers(config_workers)
            if config_workers
            else min(8, max(1, (total_assets + 3) // 4))
        )

        errors = []
        completed_count = 0
        lock = Lock()

        last_update_time = time.time()
        update_interval = 0.1
        pending_updates = 0

        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = []

            # Submit CSS entries
            for entry in css_entries:
                future = executor.submit(
                    self._process_css_entry, entry, minify, optimize, fingerprint
                )
                futures.append((future, entry, True))  # True = is_css_entry

            # Submit other assets
            for asset in other_assets:
                future = executor.submit(
                    self._process_single_asset, asset, assets_output, minify, optimize, fingerprint
                )
                futures.append((future, asset, False))  # False = not css_entry

            # Collect results as they complete
            for future, asset, is_css_entry in futures:
                try:
                    future.result()

                    # Progress update logic
                    item_name = (
                        f"{asset.source_path.name} (bundled {css_modules_count} modules)"
                        if is_css_entry
                        else asset.source_path.name
                    )

                    pending_updates += 1
                    now = time.time()
                    should_update = progress_manager and (
                        pending_updates >= 10 or (now - last_update_time) >= update_interval
                    )

                    if should_update and progress_manager is not None:
                        with lock:
                            completed_count += pending_updates
                            progress_manager.update_phase(
                                "assets",
                                current=completed_count,
                                current_item=item_name,
                                minified=minify if is_css_entry else None,
                                bundled_modules=css_modules_count if is_css_entry else None,
                            )
                            pending_updates = 0
                            last_update_time = now

                except Exception as e:
                    from bengal.errors import BengalError, ErrorContext, enrich_error

                    # Enrich error with context
                    asset_path = asset.source_path if hasattr(asset, "source_path") else None
                    context = ErrorContext(
                        file_path=asset_path,
                        operation="processing asset",
                        suggestion="Check file permissions, encoding, and format",
                        original_error=e,
                    )
                    enriched = enrich_error(e, context, BengalError)
                    errors.append(str(enriched))
                    # Collect error in build stats if available
                    if hasattr(self, "site") and hasattr(self.site, "_last_build_stats"):
                        stats = self.site._last_build_stats
                        if stats:
                            stats.add_error(enriched, category="assets")

        # Final progress update for any remaining pending updates
        if progress_manager and pending_updates > 0:
            with lock:
                completed_count += pending_updates
                progress_manager.update_phase("assets", current=completed_count)

        if errors:
            self.logger.error(
                "asset_batch_processing_failed",
                total_errors=len(errors),
                total_assets=total_assets,
                success_rate=f"{((total_assets - len(errors)) / total_assets * 100):.1f}%",
                first_errors=errors[:5],
                mode="concurrent",
            )

    def _process_sequentially(
        self,
        css_entries: list[Asset],
        other_assets: list[Asset],
        minify: bool,
        optimize: bool,
        fingerprint: bool,
        progress_manager: LiveProgressManager | None,
        css_modules_count: int,
    ) -> None:
        """Process assets sequentially."""
        from bengal.errors import (
            BengalError,
            ErrorAggregator,
            ErrorContext,
            enrich_error,
            extract_error_context,
            format_suggestion,
        )

        assets_output = self.site.output_dir / "assets"
        completed = 0
        total_assets = len(css_entries) + len(other_assets)

        # Track errors for aggregation
        aggregator = ErrorAggregator(total_items=total_assets)

        # Helper to handle single item
        def process_one(asset: Asset, is_css_entry: bool) -> None:
            nonlocal completed
            try:
                if is_css_entry:
                    self._process_css_entry(asset, minify, optimize, fingerprint)
                else:
                    self._process_single_asset(asset, assets_output, minify, optimize, fingerprint)

                completed += 1
                if progress_manager:
                    item_name = (
                        f"{asset.source_path.name} (bundled {css_modules_count} modules)"
                        if is_css_entry
                        else asset.source_path.name
                    )
                    progress_manager.update_phase(
                        "assets",
                        current=completed,
                        current_item=item_name,
                        minified=minify if is_css_entry else None,
                        bundled_modules=css_modules_count if is_css_entry else None,
                    )
            except Exception as e:
                # Get actionable suggestion
                suggestion = format_suggestion("asset", "processing_failed")

                # Enrich error with context
                error_context = ErrorContext(
                    file_path=asset.source_path,
                    operation="processing asset",
                    suggestion=suggestion or "Check file permissions, encoding, and format",
                    original_error=e,
                )
                enriched = enrich_error(e, error_context, BengalError)

                # Extract context for logging and aggregation
                context = extract_error_context(e, asset)
                context["operation"] = "processing asset"
                context["mode"] = "sequential"
                if suggestion:
                    context["suggestion"] = suggestion

                # Only log individual error if below threshold or first samples
                threshold = 5
                if aggregator.should_log_individual(e, context, threshold=threshold, max_samples=3):
                    self.logger.error(
                        "asset_processing_failed",
                        asset_path=str(asset.source_path),
                        error=str(enriched),
                        error_type=type(e).__name__,
                        mode="sequential",
                        suggestion=suggestion,
                    )

                # Add to aggregator
                aggregator.add_error(e, context=context)

                # Collect error in build stats if available
                if hasattr(self, "site") and hasattr(self.site, "_last_build_stats"):
                    stats = self.site._last_build_stats
                    if stats:
                        stats.add_error(enriched, category="assets")

        # Process CSS
        for entry in css_entries:
            process_one(entry, True)

        # Process others
        for asset in other_assets:
            process_one(asset, False)

        # Log aggregated summary if threshold exceeded
        aggregator.log_summary(self.logger, threshold=5, error_type="assets")

    def _create_js_bundle(
        self, js_modules: list[Asset], assets_cfg: dict[str, Any]
    ) -> Asset | None:
        """
        Create a bundled JavaScript file from individual JS modules.

        Uses pure Python bundler (no Node.js dependency) to concatenate
        theme JavaScript files in the correct load order.

        Args:
            js_modules: List of JS module assets to bundle
            assets_cfg: Assets configuration dict

        Returns:
            Asset representing the bundle.js file, or None if bundling fails
        """
        from bengal.core.asset import Asset
        from bengal.utils.js_bundler import (
            bundle_js_files,
            get_theme_js_bundle_order,
            get_theme_js_excluded,
        )

        try:
            # Get configuration
            minify = assets_cfg.get("minify", True)

            # Determine bundle order and exclusions
            bundle_order = get_theme_js_bundle_order()
            excluded = get_theme_js_excluded()

            # Build file path map from modules (support subdirectories)
            # Find js_dir by looking at one of the modules
            js_dir = None
            if js_modules:
                js_dir = js_modules[0].source_path.parent
                # Walk up to find the js/ directory
                while js_dir.name != "js" and js_dir.parent != js_dir:
                    js_dir = js_dir.parent
                if js_dir.name != "js":
                    js_dir = js_modules[0].source_path.parent

            module_map = {}
            for a in js_modules:
                if js_dir:
                    # Get relative path from js_dir (e.g., "core/theme.js" or "utils.js")
                    rel_path = a.source_path.relative_to(js_dir)
                    rel_path_str = str(rel_path).replace("\\", "/")  # Normalize Windows paths
                    module_map[rel_path_str] = a.source_path
                    # Also index by filename
                    if rel_path_str != a.source_path.name:
                        module_map[a.source_path.name] = a.source_path
                else:
                    # Fallback to filename only
                    module_map[a.source_path.name] = a.source_path

            # Order files according to bundle order
            ordered_files: list[Path] = []
            for name in bundle_order:
                if name in module_map and name not in excluded:
                    ordered_files.append(module_map[name])

            # Add any remaining files not in explicit order
            remaining = sorted(
                f
                for rel_path, f in module_map.items()
                if rel_path not in excluded and f not in ordered_files
            )
            ordered_files.extend(remaining)

            if not ordered_files:
                self.logger.warning("js_bundle_no_files_to_bundle")
                return None

            # Bundle the files
            bundled_content = bundle_js_files(
                ordered_files,
                minify=minify,
                add_source_comments=not minify,
            )

            if not bundled_content:
                return None

            # Write bundle to temp location
            bundle_dir = self.site.paths.js_bundle_dir
            bundle_dir.mkdir(parents=True, exist_ok=True)
            bundle_path = bundle_dir / "bundle.js"
            bundle_path.write_text(bundled_content, encoding="utf-8")

            self.logger.info(
                "js_bundle_created",
                files_bundled=len(ordered_files),
                size_kb=len(bundled_content) / 1024,
                output=str(bundle_path),
            )

            # Create Asset for the bundle (already minified if minify=True)
            bundle_asset = Asset(
                source_path=bundle_path,
                output_path=Path("js/bundle.js"),
                asset_type="javascript",
            )
            bundle_asset._site = self.site  # type: ignore[attr-defined]
            # Mark as already minified to avoid double-minification
            if minify:
                bundle_asset._minified_content = bundled_content
                bundle_asset.minified = True

            return bundle_asset

        except Exception as e:
            self.logger.error("js_bundle_failed", error=str(e))
            return None

    def _process_css_entry(
        self, css_entry: Asset, minify: bool, optimize: bool, fingerprint: bool
    ) -> None:
        """
        Process a CSS entry point (e.g., style.css) with bundling.

        Steps:
        1. Bundle all @import statements into single file
        2. Minify the bundled CSS
        3. Output to public directory

        Args:
            css_entry: CSS entry point asset
            minify: Whether to minify
            optimize: Whether to optimize (unused for CSS)
            fingerprint: Whether to add hash to filename

        Raises:
            Exception: If CSS bundling or minification fails
        """
        try:
            css_entry._site = self.site  # type: ignore[attr-defined]
            assets_output = self.site.output_dir / "assets"

            # Step 1: Bundle CSS (resolve all @imports)
            bundled_css = css_entry.bundle_css()

            # Store bundled content for minification
            css_entry._bundled_content = bundled_css

            # Step 2: Minify (if enabled)
            if minify:
                css_entry.minify()
            else:
                # Use bundled content as-is
                css_entry._minified_content = bundled_css

            # Step 3: Output to public directory
            css_entry.copy_to_output(assets_output, use_fingerprint=fingerprint)

            # Record output for hot reload tracking
            self._record_asset_output(css_entry)

        except Exception as e:
            from bengal.errors import BengalError, ErrorContext, enrich_error

            # Enrich error with context
            context = ErrorContext(
                file_path=css_entry.source_path,
                operation="processing CSS entry",
                suggestion="Check CSS syntax, file encoding, and dependencies",
                original_error=e,
            )
            enriched = enrich_error(e, context, BengalError)
            # Re-raise with context so caller can handle logging/error collection
            raise enriched from e

    def _process_single_asset(
        self, asset: Asset, assets_output: Path, minify: bool, optimize: bool, fingerprint: bool
    ) -> None:
        """
        Process a single asset (called in parallel).

        Args:
            asset: Asset to process
            assets_output: Output directory for assets
            minify: Whether to minify CSS/JS
            optimize: Whether to optimize images
            fingerprint: Whether to add fingerprint to filename

        Raises:
            Exception: If asset processing fails
        """
        try:
            # Provide site context for best-effort performance caches and diagnostics.
            # (Assets are passive models, but storing context on the instance is safe and local.)
            asset._site = self.site  # type: ignore[attr-defined]
            if minify and asset.asset_type in ("css", "javascript"):
                asset.minify()

            if optimize and asset.asset_type == "image":
                asset.optimize()

            asset.copy_to_output(assets_output, use_fingerprint=fingerprint)

            # Record output for hot reload tracking
            self._record_asset_output(asset)
        except Exception as e:
            from bengal.errors import BengalError, ErrorContext, enrich_error

            # Enrich error with context
            context = ErrorContext(
                file_path=asset.source_path,
                operation="processing asset",
                suggestion="Check file permissions, encoding, and format",
                original_error=e,
            )
            enriched = enrich_error(e, context, BengalError)
            # Re-raise with asset context for better error messages
            raise enriched from e

    def _write_asset_manifest(self, assets: list[Asset]) -> None:
        """
        Persist an asset-manifest.json file mapping logical assets to final outputs.
        """
        manifest = AssetManifest()
        for asset in assets:
            final_path = getattr(asset, "output_path", None)
            if not isinstance(final_path, Path):
                continue
            if not final_path.is_absolute():
                continue
            if not final_path.exists():
                continue
            try:
                relative_output = final_path.relative_to(self.site.output_dir)
            except ValueError:
                continue

            logical = asset.logical_path or Path(asset.source_path.name)
            logical_str = (
                logical.as_posix() if isinstance(logical, Path) else Path(str(logical)).as_posix()
            )

            stat = final_path.stat()
            manifest.set_entry(
                logical_path=logical_str,
                output_path=relative_output.as_posix(),
                fingerprint=asset.fingerprint,
                size_bytes=stat.st_size,
                updated_at=stat.st_mtime,
            )

        manifest_path = self.site.output_dir / "asset-manifest.json"
        manifest_path.parent.mkdir(parents=True, exist_ok=True)
        manifest.write(manifest_path)
