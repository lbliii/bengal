"""
Asset processing orchestration for Bengal SSG.

Handles asset copying, minification, optimization, and fingerprinting.
"""

from __future__ import annotations

import concurrent.futures
import time
from pathlib import Path
from threading import Lock
from typing import TYPE_CHECKING

from bengal.assets.manifest import AssetManifest
from bengal.config.defaults import get_max_workers
from bengal.utils.logger import get_logger

if TYPE_CHECKING:
    from bengal.core.asset import Asset
    from bengal.core.site import Site

# Thread-safe output lock for parallel processing
_print_lock = Lock()


class AssetOrchestrator:
    """
    Handles asset processing.

    Responsibilities:
        - Copy assets to output directory
        - Minify CSS/JavaScript
        - Optimize images
        - Add fingerprints to filenames
        - Parallel/sequential processing
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
        except Exception:
            # Defensive: if site/assets are not available yet
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
            except Exception:
                self._cached_css_entry_points = []
            self._cached_assets_id = current_id
            self._cached_assets_len = current_len

        return self._cached_css_entry_points

    def process(self, assets: list[Asset], parallel: bool = True, progress_manager=None) -> None:
        """
        Process and copy assets to output directory.

        CSS entry points (style.css) are bundled to resolve @imports.
        CSS modules are skipped (they're bundled into entry points).
        All other assets are processed normally.

        Args:
            assets: List of assets to process
            parallel: Whether to use parallel processing
            progress_manager: Live progress manager (optional)
        """
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

        # Ensure CSS entry points are rebuilt when any CSS module changes.
        # In incremental builds, the changed set may only include modules (e.g., base/*.css),
        # but the output actually used by templates is the bundled entry (style.css).
        # To keep dev workflow intuitive, when modules changed and no entry is queued,
        # pull entry points from the full site asset list so they get re-bundled.
        if css_modules and not css_entries:
            site_entries = self._get_site_css_entries_cached()
            if site_entries:
                css_entries = site_entries
            else:
                # Fallback: if a project truly has no entry points, treat modules as standalone
                other_assets.extend(css_modules)
                css_modules = []

        # If pipeline is enabled, skip raw sources that should not be copied
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

        # Report discovery (skip if using progress manager)
        total_discovered = len(assets)
        total_output = len(css_entries) + len(other_assets)
        if not progress_manager:
            print("\n📦 Assets:")
            print(f"   └─ Discovered: {total_discovered} files")
            if css_modules:
                print(
                    f"   └─ CSS bundling: {len(css_entries)} entry point(s), {len(css_modules)} module(s) bundled"
                )
            print(f"   └─ Output: {total_output} files ✓")

        # Get configuration
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
            total_items >= MIN_ITEMS_FOR_PARALLEL or (len(css_entries) > 0 and len(other_assets) > 0)
        )

        if should_run_parallel:
            self._process_concurrently(
                css_entries,
                other_assets,
                minify,
                optimize,
                fingerprint,
                progress_manager,
                css_modules_count=len(css_modules)
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
                css_modules_count=len(css_modules)
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

    def _process_concurrently(
        self,
        css_entries: list[Asset],
        other_assets: list[Asset],
        minify: bool,
        optimize: bool,
        fingerprint: bool,
        progress_manager,
        css_modules_count: int,
    ) -> None:
        """
        Process CSS and other assets concurrently using a shared thread pool.
        """
        assets_output = self.site.output_dir / "assets"
        total_assets = len(css_entries) + len(other_assets)
        # Use configured max_workers, or auto-detect with asset-aware bound
        config_workers = self.site.config.get("max_workers")
        max_workers = get_max_workers(config_workers) if config_workers else min(8, max(1, (total_assets + 3) // 4))

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
                future = executor.submit(self._process_css_entry, entry, minify, optimize, fingerprint)
                futures.append((future, entry, True)) # True = is_css_entry

            # Submit other assets
            for asset in other_assets:
                future = executor.submit(
                    self._process_single_asset, asset, assets_output, minify, optimize, fingerprint
                )
                futures.append((future, asset, False)) # False = not css_entry

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

                    if should_update:
                        with lock:
                            completed_count += pending_updates
                            progress_manager.update_phase(
                                "assets",
                                current=completed_count,
                                current_item=item_name,
                                minified=minify if is_css_entry else None,
                                bundled_modules=css_modules_count if is_css_entry else None
                            )
                            pending_updates = 0
                            last_update_time = now

                except Exception as e:
                    errors.append(str(e))

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
        progress_manager,
        css_modules_count: int,
    ) -> None:
        """Process assets sequentially."""
        assets_output = self.site.output_dir / "assets"
        completed = 0

        # Helper to handle single item
        def process_one(asset, is_css_entry):
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
                        bundled_modules=css_modules_count if is_css_entry else None
                    )
            except Exception as e:
                 self.logger.error(
                    "asset_processing_failed",
                    asset_path=str(asset.source_path),
                    error=str(e),
                    error_type=type(e).__name__,
                    mode="sequential",
                )

        # Process CSS
        for entry in css_entries:
            process_one(entry, True)

        # Process others
        for asset in other_assets:
            process_one(asset, False)

    def _create_js_bundle(self, js_modules: list[Asset], assets_cfg: dict) -> Asset | None:
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
        from bengal.utils.js_bundler import bundle_js_files, get_theme_js_bundle_order, get_theme_js_excluded

        try:
            # Get configuration
            minify = assets_cfg.get("minify", True)

            # Determine bundle order and exclusions
            bundle_order = get_theme_js_bundle_order()
            excluded = get_theme_js_excluded()

            # Build file path map from modules
            module_map = {a.source_path.name: a.source_path for a in js_modules}

            # Order files according to bundle order
            ordered_files: list[Path] = []
            for name in bundle_order:
                if name in module_map and name not in excluded:
                    ordered_files.append(module_map[name])

            # Add any remaining files not in explicit order
            remaining = sorted(
                f for name, f in module_map.items()
                if name not in excluded and f not in ordered_files
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
            bundle_dir = self.site.root_path / ".bengal" / "js_bundle"
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

        except Exception as e:
            # Re-raise with context so caller can handle logging/error collection
            raise Exception(
                f"Failed to process CSS entry {css_entry.source_path.name}: {e}"
            ) from e

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
            if minify and asset.asset_type in ("css", "javascript"):
                asset.minify()

            if optimize and asset.asset_type == "image":
                asset.optimize()

            asset.copy_to_output(assets_output, use_fingerprint=fingerprint)
        except Exception as e:
            # Re-raise with asset context for better error messages
            raise Exception(f"Failed to process {asset.source_path}: {e}") from e

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
