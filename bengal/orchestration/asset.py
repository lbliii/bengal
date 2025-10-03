"""
Asset processing orchestration for Bengal SSG.

Handles asset copying, minification, optimization, and fingerprinting.
"""

import concurrent.futures
from pathlib import Path
from threading import Lock
from typing import TYPE_CHECKING, List

if TYPE_CHECKING:
    from bengal.core.site import Site
    from bengal.core.asset import Asset

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
    
    def process(self, assets: List['Asset'], parallel: bool = True) -> None:
        """
        Process and copy assets to output directory.
        
        Args:
            assets: List of assets to process
            parallel: Whether to use parallel processing
        """
        if not assets:
            return
        
        print(f"\n📦 Assets:\n   └─ {len(assets)} files ✓")
        
        # Get configuration
        minify = self.site.config.get("minify_assets", True)
        optimize = self.site.config.get("optimize_assets", True)
        fingerprint = self.site.config.get("fingerprint_assets", True)
        
        # Use parallel processing only for larger workloads to avoid overhead
        # Threshold of 5 assets balances parallelism benefit vs thread overhead
        MIN_ASSETS_FOR_PARALLEL = 5
        
        if parallel and len(assets) >= MIN_ASSETS_FOR_PARALLEL:
            self._process_parallel(assets, minify, optimize, fingerprint)
        else:
            self._process_sequential(assets, minify, optimize, fingerprint)
    
    def _process_sequential(self, assets: List['Asset'], minify: bool, 
                           optimize: bool, fingerprint: bool) -> None:
        """
        Process assets sequentially (fallback or for small workloads).
        
        Args:
            assets: Assets to process
            minify: Whether to minify CSS/JS
            optimize: Whether to optimize images
            fingerprint: Whether to add fingerprint to filename
        """
        assets_output = self.site.output_dir / "assets"
        
        for asset in assets:
            try:
                if minify and asset.asset_type in ('css', 'javascript'):
                    asset.minify()
                
                if optimize and asset.asset_type == 'image':
                    asset.optimize()
                
                asset.copy_to_output(assets_output, use_fingerprint=fingerprint)
            except Exception as e:
                print(f"Warning: Failed to process asset {asset.source_path}: {e}")
    
    def _process_parallel(self, assets: List['Asset'], minify: bool, 
                         optimize: bool, fingerprint: bool) -> None:
        """
        Process assets in parallel for better performance.
        
        Args:
            assets: Assets to process
            minify: Whether to minify CSS/JS
            optimize: Whether to optimize images
            fingerprint: Whether to add fingerprint to filename
        """
        assets_output = self.site.output_dir / "assets"
        max_workers = self.site.config.get("max_workers", min(8, (len(assets) + 3) // 4))
        
        errors = []
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = [
                executor.submit(
                    self._process_single_asset,
                    asset,
                    assets_output,
                    minify,
                    optimize,
                    fingerprint
                )
                for asset in assets
            ]
            
            # Collect results and errors
            for future in concurrent.futures.as_completed(futures):
                try:
                    future.result()
                except Exception as e:
                    errors.append(str(e))
        
        # Report errors after all processing is complete
        if errors:
            with _print_lock:
                print(f"  ⚠️  {len(errors)} asset(s) failed to process:")
                for error in errors[:5]:  # Show first 5 errors
                    print(f"    • {error}")
                if len(errors) > 5:
                    print(f"    ... and {len(errors) - 5} more errors")
    
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

