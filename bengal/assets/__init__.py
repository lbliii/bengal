"""
Asset processing and management for Bengal SSG.

This package provides asset fingerprinting, manifest generation, and optional
Node-based pipeline integration for SCSS, PostCSS, and JavaScript bundling.

Components:
    - AssetManifest: Persistent manifest mapping logical paths to fingerprinted URLs
    - AssetManifestEntry: Individual entry with output path, fingerprint, and metadata
    - NodePipeline: Optional SCSS/PostCSS/esbuild pipeline (requires Node.js tooling)
    - PipelineConfig: Configuration dataclass for pipeline settings

Architecture:
    The assets package handles the transformation and tracking of static assets:

    1. **Discovery**: Assets are discovered by AssetOrchestrator (bengal/orchestration/)
    2. **Pipeline** (optional): SCSS/JS files are compiled via NodePipeline
    3. **Fingerprinting**: Files receive content-based hashes for cache-busting
    4. **Manifest**: AssetManifest tracks logical → output path mappings

    The manifest enables deterministic URL resolution in templates:
    ``{{ asset('css/style.css') }}`` → ``/assets/css/style.abc123.css``

Usage:
    The package is typically used via AssetOrchestrator, but can be used directly::

        from bengal.assets import AssetManifest

        manifest = AssetManifest()
        manifest.set_entry(
            "css/style.css",
            "assets/css/style.abc123.css",
            fingerprint="abc123",
            size_bytes=4096,
            updated_at=time.time(),
        )
        manifest.write(output_dir / "asset-manifest.json")

Related:
    - bengal/orchestration/asset_orchestrator.py: Asset processing orchestration
    - bengal/core/asset.py: Asset data model
    - bengal/rendering/filters.py: Template filters using manifest

See Also:
    - architecture/assets.md: Asset pipeline architecture
"""

from __future__ import annotations
