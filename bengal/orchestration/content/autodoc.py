"""Remote sources and autodoc registration for ContentOrchestrator."""

from __future__ import annotations

import re
from pathlib import Path
from typing import TYPE_CHECKING, Any, cast

from bengal.utils.observability.logger import get_logger

if TYPE_CHECKING:
    from bengal.autodoc.orchestration.result import AutodocRunResult
    from bengal.cache.page_discovery_cache import PageDiscoveryCache
    from bengal.protocols import PageLike, SectionLike

logger = get_logger("bengal.orchestration.content")


def _is_external_autodoc_source(path: Path) -> bool:
    """Return True for autodoc sources living in virtualenv / site-packages.

    These paths can vary by interpreter/env and cause spurious incremental
    rebuilds, so we intentionally ignore them as dependencies.
    """
    parts = path.parts
    return (
        "site-packages" in parts or "dist-packages" in parts or ".venv" in parts or ".tox" in parts
    )


def _resolve_autodoc_source(path: Path, root_path: Path) -> Path:
    """Resolve an autodoc source path against the site/repo root.

    Autodoc sources may be stored as repo-relative paths (e.g.
    "site/../bengal/..."). Resolve relative paths against the site root
    first, then the repo root.
    """
    if path.is_absolute():
        return path
    candidate = root_path / path
    if candidate.exists():
        return candidate
    candidate = root_path.parent / path
    if candidate.exists():
        return candidate
    return candidate


def _fetch_remote_sources(
    orchestrator: Any,
    collections: dict,
    content_dir: Path,
) -> None:
    """Fetch remote content sources and write to content directory.

    For each collection with a remote loader, fetches content entries
    and writes them as markdown files into the collection's directory
    under content_dir. Uses the ContentLayerManager's built-in caching
    to avoid re-fetching on every build.

    This bridges the gap between the content layer (async fetch + cache)
    and the directory walker (filesystem-based discovery).
    """
    remote_collections = {
        name: config
        for name, config in collections.items()
        if getattr(config, "is_remote", False) and getattr(config, "loader", None)
    }

    if not remote_collections:
        return

    logger.info(
        "fetching_remote_sources",
        count=len(remote_collections),
        collections=list(remote_collections.keys()),
    )

    from bengal.cache.paths import BengalPaths
    from bengal.content.sources.manager import ContentLayerManager

    paths = BengalPaths(orchestrator.site.root_path)
    manager = ContentLayerManager(cache_dir=paths.content_dir)

    for name, config in remote_collections.items():
        manager.register_custom_source(name, config.loader)

    try:
        entries = manager.fetch_all_sync(use_cache=True)
    except Exception as e:
        logger.warning(
            "remote_source_fetch_failed",
            error=str(e),
            error_type=type(e).__name__,
        )
        return

    # Write fetched entries to content directory as markdown files
    written = 0
    for entry in entries:
        collection_name = entry.source_name
        config = remote_collections.get(collection_name)
        if config is None:
            continue

        # Determine target directory
        directory = getattr(config, "directory", None) or collection_name
        target_dir = content_dir / directory
        target_dir.mkdir(parents=True, exist_ok=True)

        # Write markdown file (sanitize slug to prevent path traversal)
        slug = entry.slug or entry.id
        slug = re.sub(r"[^\w\-.]", "-", slug).strip("-.")
        if not slug:
            slug = f"entry-{written}"
        target_file = target_dir / f"{slug}.md"

        # Verify resolved path stays within target_dir
        if not target_file.resolve().is_relative_to(target_dir.resolve()):
            logger.warning("remote_source_slug_traversal", slug=slug)
            continue

        # Build frontmatter + content
        import yaml

        fm = dict(entry.frontmatter or {})
        if entry.source_url:
            fm["source_url"] = entry.source_url
        frontmatter = yaml.dump(fm, sort_keys=False, default_flow_style=False).strip()
        text = f"---\n{frontmatter}\n---\n\n{entry.content or ''}"

        from bengal.utils.io.atomic_write import atomic_write_text

        atomic_write_text(target_file, text)
        written += 1

    if written:
        logger.info("remote_sources_written", entries=written)


def _discover_autodoc_content(
    orchestrator: Any,
    cache: PageDiscoveryCache | None = None,
    build_cache: Any | None = None,
) -> tuple[list[PageLike], list[SectionLike]]:
    """
    Generate virtual autodoc pages if enabled.

    Args:
        cache: Optional PageDiscoveryCache for incremental autodoc page loading.
        build_cache: Optional BuildCache for AST caching and dependency tracking.
                    RFC: rfc-build-performance-optimizations Phase 3
                    Enables AST caching to skip parsing unchanged Python files.

    Returns:
        Tuple of (pages, sections) from virtual autodoc generation.
        Returns ([], []) if virtual autodoc is disabled.
    """
    # Performance: autodoc should be opt-in. If there is no explicit autodoc
    # configuration, avoid importing and initializing the autodoc subsystem.
    autodoc_cfg = orchestrator.site.config.get("autodoc")
    if not isinstance(autodoc_cfg, dict) or not autodoc_cfg:
        return [], []

    try:
        from bengal import __version__
        from bengal.autodoc.orchestration import VirtualAutodocOrchestrator
        from bengal.utils.primitives.hashing import hash_dict

        # RFC: rfc-build-performance-optimizations Phase 3
        # Pass build_cache to orchestrator for AST caching
        autodoc_orchestrator = VirtualAutodocOrchestrator(orchestrator.site, cache=build_cache)

        if not autodoc_orchestrator.is_enabled():
            logger.debug("virtual_autodoc_not_enabled")
            return [], []

        cache_key = "__autodoc_elements_v1"
        current_cfg_hash = hash_dict(autodoc_cfg) if isinstance(autodoc_cfg, dict) else ""

        # Incremental fast path: if autodoc sources are unchanged and we have a cached
        # extraction payload, rebuild virtual pages without re-extracting.
        if cache is not None and hasattr(cache, "get_page_cache") and hasattr(cache, "is_changed"):
            cached_payload = cache.get_page_cache(cache_key)
            if (
                isinstance(cached_payload, dict)
                and cached_payload.get("version") == __version__
                and cached_payload.get("autodoc_config_hash") == current_cfg_hash
            ):
                changed = False
                if hasattr(cache, "autodoc_tracker"):
                    try:
                        for source in cache.autodoc_tracker.get_autodoc_source_files():
                            src_path = _resolve_autodoc_source(
                                Path(source), orchestrator.site.root_path
                            )
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
                    try:
                        pages, sections, run_result = (
                            autodoc_orchestrator.generate_from_cache_payload(cached_payload)
                        )
                        # Register autodoc dependencies with build_cache so autodoc_tracker is populated
                        orchestrator._register_autodoc_dependencies(run_result, build_cache)

                        logger.debug(
                            "autodoc_cache_hit",
                            pages=len(pages),
                            sections=len(sections),
                        )
                        return pages, cast("list[SectionLike]", sections)
                    except (TypeError, KeyError, ValueError) as e:
                        # Cache payload is malformed - invalidate and fall back to re-extraction
                        logger.warning(
                            "autodoc_cache_payload_malformed",
                            cache_key=cache_key,
                            error=str(e),
                            error_type=type(e).__name__,
                            action="invalidating_cache_and_re_extracting",
                        )
                        if hasattr(cache, "invalidate_page_cache"):
                            cache.invalidate_page_cache(cache_key)
                        # Fall through to re-extraction below

        pages, sections, run_result = autodoc_orchestrator.generate()
        # Log summary if there were failures or warnings
        if run_result.has_failures() or run_result.has_warnings():
            orchestrator._log_autodoc_summary(run_result)

        # Register autodoc dependencies with build_cache for selective rebuilds
        # CRITICAL: Pass source_hash and source_mtime for incremental detection.
        if build_cache is not None and hasattr(build_cache, "autodoc_tracker"):
            orchestrator._register_autodoc_dependencies(run_result, build_cache)

            if run_result.autodoc_dependencies:
                logger.debug(
                    "autodoc_dependencies_registered",
                    source_files=len(run_result.autodoc_dependencies),
                    total_mappings=sum(len(p) for p in run_result.autodoc_dependencies.values()),
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
                    logger.debug(
                        "autodoc_source_fingerprints_update_failed",
                        error=str(e),
                        error_type=type(e).__name__,
                    )

            # Persist extraction payload for incremental cache hits.
            if cache is not None and hasattr(cache, "set_page_cache"):
                try:
                    payload = autodoc_orchestrator.get_cache_payload()
                    if (
                        isinstance(payload, dict)
                        and payload.get("version") == __version__
                        and payload.get("autodoc_config_hash") == current_cfg_hash
                    ):
                        cache.set_page_cache(cache_key, payload)
                        logger.debug(
                            "autodoc_cache_saved",
                            types=list((payload.get("elements") or {}).keys()),
                        )
                except Exception as e:
                    logger.debug(
                        "autodoc_cache_save_failed",
                        error=str(e),
                        error_type=type(e).__name__,
                    )

        return pages, cast("list[SectionLike]", sections)

    except ImportError as e:
        logger.debug("autodoc_import_failed", error=str(e))
        return [], []
    # Note: Other exceptions (e.g., RuntimeError from strict mode) propagate
    # to allow strict mode enforcement. Non-strict failures are logged in summary.


def _register_autodoc_dependencies(
    orchestrator: Any, run_result: AutodocRunResult, build_cache: Any
) -> None:
    """
    Register autodoc source -> page dependencies with the build cache.

    Shared by both the warm cache-hit and cold fresh-extraction paths so
    their error handling cannot drift. For each source file: resolve the
    path, skip virtualenv/site-packages sources, skip (and warn on) missing
    sources, then hash/stat the source under an ``OSError`` guard so a
    present-but-unreadable source degrades gracefully (warning) instead of
    crashing the build. ``Path.exists()`` returns False (not raises) on
    permission errors, so an unreadable source slips past the exists guard
    into the hash/stat calls; the guard here is what makes both paths safe.
    """
    if build_cache is None or not hasattr(build_cache, "autodoc_tracker"):
        return

    from bengal.utils.primitives.hashing import hash_file

    for source_file, page_hashes in run_result.autodoc_dependencies.items():
        src_path = _resolve_autodoc_source(Path(source_file), orchestrator.site.root_path)
        if _is_external_autodoc_source(src_path):
            continue
        if not src_path.exists():
            logger.warning(
                "autodoc_source_missing",
                source_file=str(source_file),
            )
            continue

        try:
            source_hash = hash_file(src_path)
            source_mtime = src_path.stat().st_mtime
        except OSError:
            logger.warning(
                "autodoc_source_stat_failed",
                source_file=str(source_file),
            )
            continue

        for page_path, content_hash in page_hashes.items():
            build_cache.autodoc_tracker.add_autodoc_dependency(
                source_file,
                page_path,
                site_root=orchestrator.site.root_path,
                source_hash=source_hash,
                source_mtime=source_mtime,
                content_hash=content_hash,
            )


def _log_autodoc_summary(_orchestrator: Any, result: AutodocRunResult) -> None:
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
        logger.warning("autodoc_run_summary", summary=summary)
    else:
        logger.info("autodoc_run_summary", summary=summary)
