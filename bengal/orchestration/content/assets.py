"""Asset discovery, provider assets, and library bundles for ContentOrchestrator."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from bengal.core.diagnostics import emit as emit_diagnostic
from bengal.utils.observability.logger import get_logger

logger = get_logger("bengal.orchestration.content")


def _library_asset_manifest_provenance(
    library_asset: Any,
    *,
    sources: tuple[Any, ...],
) -> dict[str, Any]:
    """Return sanitized manifest provenance for a theme-library asset."""
    package = str(getattr(library_asset, "package", "") or "")
    mode = str(getattr(library_asset, "mode", "") or "")
    source_paths: list[str] = []
    for source in sources:
        contract_path = getattr(source, "contract_path", None)
        if isinstance(contract_path, Path) and contract_path != Path("."):
            source_paths.append(contract_path.as_posix())
        else:
            source_paths.append(Path(source.source_path).name)

    provenance: dict[str, Any] = {"kind": "theme_library"}
    if package:
        provenance["package"] = package
    if mode:
        provenance["mode"] = mode
    if source_paths:
        provenance["sources"] = source_paths
    return provenance


def discover_assets(orchestrator: Any, assets_dir: Path | None = None) -> None:
    """
    Discover all assets in the assets directory and theme assets.

    Args:
        assets_dir: Assets directory path (defaults to root_path/assets)
    """
    # Optimization: Skip asset discovery if only content files changed
    options = getattr(orchestrator.site, "_last_build_options", None)
    cache = getattr(orchestrator.site, "_cache", None)

    if (
        options
        and options.incremental
        and options.changed_sources
        and not options.structural_changed
    ):
        content_extensions = {".md", ".markdown", ".html", ".txt", ".ipynb"}
        non_content_changes = [
            s for s in options.changed_sources if s.suffix.lower() not in content_extensions
        ]

        if (
            not non_content_changes
            and cache
            and hasattr(cache, "discovered_assets")
            and cache.discovered_assets
        ):
            from bengal.core.asset import Asset

            orchestrator.site.assets = []
            for src_rel, out_rel in cache.discovered_assets.items():
                orchestrator.site.assets.append(
                    Asset(
                        source_path=orchestrator.site.root_path / src_rel,
                        output_path=Path(out_rel),
                    )
                )
            logger.debug(
                "asset_discovery_skipped",
                reason="only_content_changed",
                count=len(orchestrator.site.assets),
            )
            return

    from bengal.content.discovery.asset_discovery import AssetDiscovery
    from bengal.services.theme import get_theme_assets_chain

    orchestrator.site.assets = []

    if orchestrator.site.theme:
        for theme_dir in get_theme_assets_chain(
            orchestrator.site.root_path, orchestrator.site.theme
        ):
            if theme_dir and theme_dir.exists():
                theme_discovery = AssetDiscovery(theme_dir)
                orchestrator.site.assets.extend(theme_discovery.discover())

    orchestrator._discover_provider_assets()

    if assets_dir is None:
        assets_dir = orchestrator.site.root_path / "assets"

    if assets_dir.exists():
        emit_diagnostic(orchestrator.site, "debug", "discovering_site_assets", path=str(assets_dir))
        site_discovery = AssetDiscovery(assets_dir)
        orchestrator.site.assets.extend(site_discovery.discover())
    elif not orchestrator.site.assets:
        emit_diagnostic(orchestrator.site, "warning", "assets_dir_not_found", path=str(assets_dir))

    if orchestrator.site.assets:
        dedup: dict[str, Any] = {}
        order: list[str] = []
        for asset in orchestrator.site.assets:
            key = str(asset.output_path) if asset.output_path else str(asset.source_path.name)
            if key in dedup:
                dedup[key] = asset
            else:
                dedup[key] = asset
                order.append(key)
        orchestrator.site.assets = [dedup[k] for k in order]

    logger.debug("assets_discovered", total=len(orchestrator.site.assets))


def _discover_provider_assets(orchestrator: Any) -> None:
    """Discover assets from theme library providers, namespaced by prefix."""
    from collections import defaultdict

    from bengal.content.discovery.asset_discovery import AssetDiscovery
    from bengal.core.asset import Asset
    from bengal.core.theme.providers import (
        LibraryAsset,
        get_provider_asset_dirs,
        get_provider_assets,
        resolve_theme_providers,
    )
    from bengal.core.theme.resolution import resolve_theme_chain

    if not orchestrator.site.theme:
        return

    theme_chain = resolve_theme_chain(orchestrator.site.root_path, orchestrator.site.theme)
    providers = resolve_theme_providers(orchestrator.site.root_path, theme_chain)
    if not providers:
        return

    bundle_groups: dict[tuple[Path, str], list[LibraryAsset]] = defaultdict(list)

    for library_asset in get_provider_assets(providers):
        if library_asset.mode == "none":
            continue
        if not library_asset.source_path.exists():
            from bengal.errors import BengalAssetError, ErrorCode

            raise BengalAssetError(
                f"Theme library asset not found: {library_asset.source_path}",
                code=ErrorCode.X001,
                suggestion=(
                    "Check the provider get_library_contract() asset path or remove "
                    "the asset from the contract."
                ),
                file_path=library_asset.source_path,
            )
        if library_asset.mode == "bundle":
            bundle_groups[(library_asset.logical_path, library_asset.asset_type)].append(
                library_asset
            )
            continue
        output_path = library_asset.logical_path
        asset_type = library_asset.asset_type
        orchestrator.site.assets.append(
            Asset(
                source_path=library_asset.source_path,
                output_path=output_path,
                asset_type=asset_type,
                logical_path=output_path,
                standalone=asset_type == "css",
                manifest_provenance=_library_asset_manifest_provenance(
                    library_asset,
                    sources=(library_asset,),
                ),
            )
        )

    for (logical_path, asset_type), assets in bundle_groups.items():
        if asset_type not in {"css", "javascript"}:
            from bengal.errors import BengalAssetError, ErrorCode

            raise BengalAssetError(
                f"Theme library bundle target '{logical_path.as_posix()}' has "
                f"unsupported asset type '{asset_type}'.",
                code=ErrorCode.X003,
                suggestion="Use bundle mode only for CSS or JavaScript provider assets.",
            )

        bundle_dir = orchestrator.site.root_path / ".bengal" / "cache" / "library-assets"
        bundle_path = bundle_dir / logical_path
        orchestrator._write_library_asset_bundle(bundle_path, assets, asset_type)
        orchestrator.site.assets.append(
            Asset(
                source_path=bundle_path,
                output_path=logical_path,
                asset_type=asset_type,
                logical_path=logical_path,
                standalone=asset_type == "css",
                manifest_provenance=_library_asset_manifest_provenance(
                    assets[0],
                    sources=tuple(assets),
                ),
            )
        )

    for prefix, asset_root in get_provider_asset_dirs(providers):
        discovery = AssetDiscovery(asset_root)
        for asset in discovery.discover():
            if asset.output_path:
                asset.output_path = Path(prefix) / asset.output_path
                asset.logical_path = asset.output_path
            # Some libraries expose CSS and Kida templates from the same package
            # root; only browser-downloadable assets should enter the manifest.
            if asset.source_path.suffix.lower() == ".html":
                continue
            # Provider CSS files (e.g. a component library's bundle) are
            # standalone static files, not modules imported by a site/theme
            # style.css entry point.
            if asset.source_path.suffix.lower() == ".css" and asset.source_path.name != "style.css":
                asset.standalone = True
            orchestrator.site.assets.append(asset)


def _write_library_asset_bundle(
    _orchestrator: Any,
    bundle_path: Path,
    assets: list[Any],
    asset_type: str,
) -> None:
    """Concatenate declared library assets into a generated bundle source."""
    from bengal.utils.io.atomic_write import atomic_write_text

    comment_open, comment_close = ("/*", "*/") if asset_type == "css" else ("//", "")
    chunks: list[str] = []
    for asset in assets:
        content = asset.source_path.read_text(encoding="utf-8")
        if comment_close:
            chunks.append(f"{comment_open} {asset.source_path.name} {comment_close}\n{content}")
        else:
            chunks.append(f"{comment_open} {asset.source_path.name}\n{content}")
    separator = "\n\n" if asset_type == "css" else "\n;\n"
    atomic_write_text(bundle_path, separator.join(chunks), encoding="utf-8")
