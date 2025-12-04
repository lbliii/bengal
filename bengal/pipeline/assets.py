"""
Assets stream for processing assets (fingerprinting, optimization, copying).

This module provides stream-based asset processing that replaces
AssetOrchestrator with a declarative, reactive approach.

Flow:
    assets → fingerprint → optimize → copy_to_output → processed_assets
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from bengal.pipeline.core import Stream
from bengal.utils.logger import get_logger

if TYPE_CHECKING:
    from bengal.core.asset import Asset
    from bengal.core.site import Site

logger = get_logger(__name__)


def create_assets_stream(
    assets: list[Asset],
    site: Site,
    *,
    parallel: bool = True,
) -> Stream[Asset]:
    """
    Create a stream that processes assets (fingerprinting, optimization, copying).

    This stream:
    1. Optionally runs Node-based pipeline (SCSS/PostCSS/JS/TS compilation)
    2. Separates CSS entry points, CSS modules, and other assets
    3. Handles JS bundling if enabled
    4. Processes CSS entries (bundles @imports)
    5. Processes other assets (copy, minify, optimize, fingerprint)
    6. Generates asset manifest

    Args:
        assets: List of assets to process
        site: Site instance
        parallel: Whether to use parallel processing

    Returns:
        Stream emitting processed assets

    Example:
        >>> assets_stream = create_assets_stream(site.assets, site)
        >>> # After iterating, assets are processed and copied to output
        >>> list(assets_stream.iterate())
    """
    from bengal.pipeline.core import StreamItem
    from bengal.pipeline.streams import SourceStream

    # Optionally run Node-based pipeline first
    processed_assets = _run_node_pipeline(assets, site)

    if not processed_assets:
        logger.info("asset_processing_skipped", reason="no_assets")

        # Return empty stream
        def empty_producer():
            if False:  # Make it a generator
                yield

        return SourceStream(empty_producer, name="empty_assets")

    # Separate assets by type
    css_entries, css_modules, other_assets, js_bundle = _separate_assets(processed_assets, site)

    # Create stream from assets to process
    def assets_producer():
        """Produce StreamItems from assets list."""
        # CSS entries (will bundle modules)
        for i, asset in enumerate(css_entries):
            yield StreamItem.create(
                source="css_entries",
                id=f"css_{i}",
                value=asset,
            )
        # Other assets (including JS bundle if created)
        for i, asset in enumerate(other_assets):
            yield StreamItem.create(
                source="other_assets",
                id=f"asset_{i}",
                value=asset,
            )

    assets_stream = SourceStream(assets_producer, name="assets")

    # Get processing config
    minify = site.config.get("minify_assets", True)
    optimize = site.config.get("optimize_assets", True)
    fingerprint = site.config.get("fingerprint_assets", True)
    assets_output = site.output_dir / "assets"

    # Process assets
    def process_asset(asset: Asset) -> Asset:
        """Process a single asset."""
        # Check if this is a CSS entry point
        is_css_entry = asset.is_css_entry_point()

        if is_css_entry:
            _process_css_entry(asset, site, minify, optimize, fingerprint, css_modules)
        else:
            _process_single_asset(asset, assets_output, minify, optimize, fingerprint)

        return asset

    processed_stream = assets_stream.map(process_asset, name="process_asset")

    # Add parallelism if requested
    if parallel:
        from bengal.config.defaults import get_max_workers

        max_workers = get_max_workers(site.config.get("max_workers"))
        processed_stream = processed_stream.parallel(workers=max_workers)

    # After all assets are processed, write manifest
    def write_manifest(assets_list: list[Asset]) -> list[Asset]:
        """Write asset manifest after all assets are processed."""
        _write_asset_manifest(assets_list, site)
        return assets_list

    # Collect all processed assets, write manifest, then flatten
    collected_stream = processed_stream.collect(name="collect_processed_assets")
    manifest_stream = collected_stream.map(write_manifest, name="write_manifest")
    flattened_stream = manifest_stream.flat_map(lambda assets: iter(assets), name="flatten_assets")

    return flattened_stream


def _run_node_pipeline(assets: list[Asset], site: Site) -> list[Asset]:
    """
    Optionally run Node-based pipeline (SCSS/PostCSS/JS/TS compilation).

    Args:
        assets: List of assets
        site: Site instance

    Returns:
        Updated list of assets (may include compiled assets)
    """
    try:
        from bengal.assets.pipeline import from_site as pipeline_from_site

        pipeline = pipeline_from_site(site)
        compiled = pipeline.build()
        if compiled:
            from bengal.core.asset import Asset

            for out_path in compiled:
                if out_path.is_file():
                    # Register path relative to temp pipeline root
                    rel = out_path
                    parts = list(out_path.parts)
                    if "assets" in parts:
                        idx = parts.index("assets")
                        rel = Path(*parts[idx + 1 :])
                    assets.append(Asset(source_path=out_path, output_path=rel))
    except Exception as e:
        logger.warning("asset_pipeline_failed", error=str(e))

    return assets


def _separate_assets(
    assets: list[Asset], site: Site
) -> tuple[list[Asset], list[Asset], list[Asset], Asset | None]:
    """
    Separate assets into CSS entries, CSS modules, other assets, and JS bundle.

    Args:
        assets: List of all assets
        site: Site instance

    Returns:
        Tuple of (css_entries, css_modules, other_assets, js_bundle)
    """

    css_entries = [a for a in assets if a.is_css_entry_point()]
    css_modules = [a for a in assets if a.is_css_module()]
    other_assets = [a for a in assets if a.asset_type != "css"]

    # Check if JS bundling is enabled
    assets_cfg = (
        site.config.get("assets", {}) if isinstance(site.config.get("assets"), dict) else {}
    )
    bundle_js = assets_cfg.get("bundle_js", False)

    js_bundle = None
    if bundle_js:
        # Separate JS modules from other assets
        js_modules = [a for a in other_assets if a.is_js_module()]
        other_assets = [a for a in other_assets if not a.is_js_module()]

        # Generate bundle.js if there are modules to bundle
        if js_modules:
            js_bundle = _create_js_bundle(js_modules, assets_cfg, site)
            if js_bundle:
                other_assets.append(js_bundle)

    # In incremental builds, if modules changed but no entry is queued, pull entries
    # so they get re-bundled (templates use bundled entries, not raw modules)
    if css_modules and not css_entries:
        # Get CSS entries from site (cached)
        site_entries = _get_site_css_entries_cached(site)
        if site_entries:
            css_entries = site_entries
        else:
            other_assets.extend(css_modules)
            css_modules = []

    # Filter out pipeline-processed files if pipeline is enabled
    if assets_cfg.get("pipeline", False):
        skip_exts = {".scss", ".sass", ".ts", ".tsx"}
        other_assets = [a for a in other_assets if a.source_path.suffix.lower() not in skip_exts]

    return css_entries, css_modules, other_assets, js_bundle


def _get_site_css_entries_cached(site: Site) -> list[Asset]:
    """
    Return cached list of CSS entry points from the full site asset list.

    Args:
        site: Site instance

    Returns:
        List of CSS entry point assets
    """
    # Simple implementation - just filter site.assets
    # (Full caching logic can be added later if needed)
    try:
        return [a for a in site.assets if a.is_css_entry_point()]
    except Exception:
        return []


def _create_js_bundle(js_modules: list[Asset], assets_cfg: dict, site: Site) -> Asset | None:
    """
    Create a JS bundle from JS modules.

    Args:
        js_modules: List of JS module assets
        assets_cfg: Assets configuration
        site: Site instance

    Returns:
        Bundle asset, or None if bundling failed
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

        # Build file path map from modules
        module_map = {a.source_path.name: a.source_path for a in js_modules}

        # Order files according to bundle order
        ordered_files: list[Path] = []
        for name in bundle_order:
            if name in module_map and name not in excluded:
                ordered_files.append(module_map[name])

        # Add any remaining files not in explicit order
        remaining = sorted(
            f for name, f in module_map.items() if name not in excluded and f not in ordered_files
        )
        ordered_files.extend(remaining)

        if not ordered_files:
            logger.warning("js_bundle_no_files_to_bundle")
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
        bundle_dir = site.root_path / ".bengal" / "js_bundle"
        bundle_dir.mkdir(parents=True, exist_ok=True)
        bundle_path = bundle_dir / "bundle.js"
        bundle_path.write_text(bundled_content, encoding="utf-8")

        logger.info(
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
        logger.error("js_bundle_failed", error=str(e))
        return None


def _process_css_entry(
    asset: Asset,
    site: Site,
    minify: bool,
    optimize: bool,
    fingerprint: bool,
    css_modules: list[Asset],
) -> None:
    """
    Process a CSS entry point (bundles @imports).

    Args:
        asset: CSS entry point asset
        site: Site instance
        minify: Whether to minify CSS
        optimize: Whether to optimize CSS
        fingerprint: Whether to fingerprint CSS
        css_modules: List of CSS modules to bundle (unused, but kept for API compatibility)
    """
    try:
        assets_output = site.output_dir / "assets"

        # Step 1: Bundle CSS (resolve all @imports)
        bundled_css = asset.bundle_css()

        # Store bundled content for minification
        asset._bundled_content = bundled_css

        # Step 2: Minify (if enabled)
        if minify:
            asset.minify()
        else:
            # Use bundled content as-is
            asset._minified_content = bundled_css

        # Step 3: Output to public directory
        asset.copy_to_output(assets_output, use_fingerprint=fingerprint)

    except Exception as e:
        logger.error(
            "css_entry_processing_failed",
            asset_path=str(asset.source_path),
            error=str(e),
        )
        raise


def _process_single_asset(
    asset: Asset,
    assets_output: Path,
    minify: bool,
    optimize: bool,
    fingerprint: bool,
) -> None:
    """
    Process a single asset (copy, minify, optimize, fingerprint).

    Args:
        asset: Asset to process
        assets_output: Output directory for assets
        minify: Whether to minify
        optimize: Whether to optimize
        fingerprint: Whether to fingerprint
    """
    try:
        # Minify before copying (if enabled)
        if minify and asset.asset_type in ("css", "javascript"):
            asset.minify()

        # Optimize before copying (if enabled)
        if optimize and asset.asset_type == "image":
            asset.optimize()

        # Copy to output (with fingerprint if enabled)
        asset.copy_to_output(assets_output, use_fingerprint=fingerprint)

    except Exception as e:
        logger.error(
            "asset_processing_failed",
            asset_path=str(asset.source_path),
            error=str(e),
        )
        raise


def _write_asset_manifest(assets: list[Asset], site: Site) -> None:
    """
    Write asset manifest for cache-busting.

    Args:
        assets: List of processed assets
        site: Site instance
    """
    from bengal.assets.manifest import AssetManifest

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
            relative_output = final_path.relative_to(site.output_dir)
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

    manifest_path = site.output_dir / "asset-manifest.json"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest.write(manifest_path)
