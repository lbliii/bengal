"""
Asset processing orchestration for Bengal SSG.

Handles asset copying, minification, optimization, and fingerprinting.
"""

import concurrent.futures
import time
from pathlib import Path
from threading import Lock
from typing import TYPE_CHECKING

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
    
    def __init__(self, site: 'Site'):
        """
        Initialize asset orchestrator.
        
        Args:
            site: Site instance containing assets and configuration
        """
        self.site = site
        self.logger = get_logger(__name__)
    
    def process(self, assets: list['Asset'], parallel: bool = True, 
                progress_manager=None) -> None:
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
                        if 'assets' in parts:
                            idx = parts.index('assets')
                            rel = Path(*parts[idx+1:])
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
        other_assets = [a for a in assets if a.asset_type != 'css']
        
        # If pipeline is enabled, skip raw sources that should not be copied
        assets_cfg = self.site.config.get("assets", {}) if isinstance(self.site.config.get("assets"), dict) else {}
        if assets_cfg.get("pipeline", False):
            skip_exts = {'.scss', '.sass', '.ts', '.tsx'}
            other_assets = [a for a in other_assets if a.source_path.suffix.lower() not in skip_exts]
        
        # Report discovery (skip if using progress manager)
        total_discovered = len(assets)
        total_output = len(css_entries) + len(other_assets)
        if not progress_manager:
            print("\n📦 Assets:")
            print(f"   └─ Discovered: {total_discovered} files")
            if css_modules:
                print(f"   └─ CSS bundling: {len(css_entries)} entry point(s), {len(css_modules)} module(s) bundled")
            print(f"   └─ Output: {total_output} files ✓")
        
        # Get configuration
        minify = self.site.config.get("minify_assets", True)
        optimize = self.site.config.get("optimize_assets", True)
        fingerprint = self.site.config.get("fingerprint_assets", True)
        
        # Log asset processing configuration
        self.logger.info("asset_processing_start",
                        total_assets=len(assets),
                        css_entries=len(css_entries),
                        css_modules=len(css_modules),
                        other_assets=len(other_assets),
                        mode="parallel" if parallel else "sequential",
                        minify=minify,
                        optimize=optimize,
                        fingerprint=fingerprint)
        
        # Process CSS entry points first (bundle + minify)
        for i, css_entry in enumerate(css_entries):
            self._process_css_entry(css_entry, minify, optimize, fingerprint)
            if progress_manager:
                progress_manager.update_phase(
                    'assets',
                    current=i+1,
                    current_item=f"{css_entry.source_path.name} (bundled {len(css_modules)} modules)",
                    minified=minify,
                    bundled_modules=len(css_modules)
                )
        
        # Process other assets (skip CSS modules)
        assets_to_process = other_assets
        
        # Use parallel processing only for larger workloads to avoid overhead
        MIN_ASSETS_FOR_PARALLEL = 5
        
        if parallel and len(assets_to_process) >= MIN_ASSETS_FOR_PARALLEL:
            self._process_parallel(assets_to_process, minify, optimize, fingerprint, progress_manager, len(css_entries))
        else:
            self._process_sequential(assets_to_process, minify, optimize, fingerprint, progress_manager, len(css_entries))
        
        # Log completion metrics
        duration_ms = (time.time() - start_time) * 1000
        self.logger.info("asset_processing_complete",
                        assets_processed=len(assets),
                        output_files=total_output,
                        duration_ms=duration_ms,
                        throughput=len(assets) / (duration_ms / 1000) if duration_ms > 0 else 0)
    
    def _process_css_entry(
        self,
        css_entry: 'Asset',
        minify: bool,
        optimize: bool,
        fingerprint: bool
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
            self.logger.error("css_entry_processing_failed",
                            asset_path=str(css_entry.source_path),
                            error=str(e),
                            error_type=type(e).__name__,
                            stage="bundle_or_minify")
    
    def _process_sequential(self, assets: list['Asset'], minify: bool, 
                           optimize: bool, fingerprint: bool, progress_manager=None, 
                           css_entries_processed: int = 0) -> None:
        """
        Process assets sequentially (fallback or for small workloads).
        
        Args:
            assets: Assets to process
            minify: Whether to minify CSS/JS
            optimize: Whether to optimize images
            fingerprint: Whether to add fingerprint to filename
            progress_manager: Live progress manager (optional)
            css_entries_processed: Number of CSS entries already processed
        
        Note:
            Errors during asset processing are logged but don't fail the entire build
        """
        assets_output = self.site.output_dir / "assets"
        
        for i, asset in enumerate(assets):
            try:
                if minify and asset.asset_type in ('css', 'javascript'):
                    asset.minify()
                
                if optimize and asset.asset_type == 'image':
                    asset.optimize()
                
                asset.copy_to_output(assets_output, use_fingerprint=fingerprint)
                
                if progress_manager:
                    progress_manager.update_phase(
                        'assets',
                        current=css_entries_processed + i + 1,
                        current_item=asset.source_path.name
                    )
            except Exception as e:
                self.logger.error("asset_processing_failed",
                                asset_path=str(asset.source_path),
                                asset_type=asset.asset_type,
                                error=str(e),
                                error_type=type(e).__name__,
                                mode="sequential")
    
    def _process_parallel(self, assets: list['Asset'], minify: bool, 
                         optimize: bool, fingerprint: bool, progress_manager=None,
                         css_entries_processed: int = 0) -> None:
        """
        Process assets in parallel for better performance.
        
        Uses ThreadPoolExecutor to process multiple assets concurrently.
        Errors are collected and reported after all tasks complete.
        
        Args:
            assets: Assets to process
            minify: Whether to minify CSS/JS
            optimize: Whether to optimize images
            fingerprint: Whether to add fingerprint to filename
            progress_manager: Live progress manager (optional)
            css_entries_processed: Number of CSS entries already processed
        
        Note:
            max_workers is determined from site config (default: min(8, asset_count/4))
        """
        assets_output = self.site.output_dir / "assets"
        max_workers = self.site.config.get("max_workers", min(8, (len(assets) + 3) // 4))
        
        errors = []
        completed_count = css_entries_processed
        lock = Lock()
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = []
            for asset in assets:
                future = executor.submit(
                    self._process_single_asset,
                    asset,
                    assets_output,
                    minify,
                    optimize,
                    fingerprint
                )
                futures.append((future, asset))
            
            # Collect results and errors
            for future, asset in futures:
                try:
                    future.result()
                    if progress_manager:
                        with lock:
                            completed_count += 1
                            progress_manager.update_phase(
                                'assets',
                                current=completed_count,
                                current_item=asset.source_path.name
                            )
                except Exception as e:
                    errors.append(str(e))
        
        # Report errors after all processing is complete
        if errors:
            self.logger.error("asset_batch_processing_failed",
                            total_errors=len(errors),
                            total_assets=len(assets),
                            success_rate=f"{((len(assets) - len(errors)) / len(assets) * 100):.1f}%",
                            first_errors=errors[:5],
                            mode="parallel")
    
    def _process_single_asset(
        self,
        asset: 'Asset',
        assets_output: Path,
        minify: bool,
        optimize: bool,
        fingerprint: bool
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
            if minify and asset.asset_type in ('css', 'javascript'):
                asset.minify()
            
            if optimize and asset.asset_type == 'image':
                asset.optimize()
            
            asset.copy_to_output(assets_output, use_fingerprint=fingerprint)
        except Exception as e:
            # Re-raise with asset context for better error messages
            raise Exception(f"Failed to process {asset.source_path}: {e}") from e

