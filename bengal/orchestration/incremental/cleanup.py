"""
Cleanup utilities for incremental builds.

Handles cleanup of deleted source files and their corresponding output files.
Ensures stale content is removed when source files are deleted.

Key Concepts:
    - Source file tracking: Track which source files produced which output
    - Output cleanup: Remove output when source is deleted
    - Autodoc cleanup: Handle autodoc pages when Python source files deleted

Related Modules:
    - bengal.cache.build_cache: Build cache with output_sources mapping
    - bengal.orchestration.incremental: Incremental build coordination
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from bengal.utils.logger import get_logger

if TYPE_CHECKING:
    from bengal.cache import BuildCache
    from bengal.core.site import Site

logger = get_logger(__name__)


def cleanup_deleted_files(site: Site, cache: BuildCache) -> int:
    """
    Clean up output files for deleted source files.

    Checks cache for source files that no longer exist and deletes
    their corresponding output files. This prevents stale content
    from remaining in the output directory after source deletion.

    Args:
        site: Site instance for output directory access
        cache: BuildCache instance with source mappings

    Returns:
        Count of deleted output files
    """
    # Also clean up deleted autodoc source files
    _cleanup_deleted_autodoc_sources(site, cache)

    if not cache.output_sources:
        return 0

    deleted_count = 0

    # Build set of current source paths from output_sources
    deleted_sources = []

    for output_path_str, source_path_str in cache.output_sources.items():
        source_path = Path(source_path_str)
        # Check if source file still exists on disk
        if not source_path.exists():
            deleted_sources.append((output_path_str, source_path_str))

    if deleted_sources:
        logger.info(
            "deleted_sources_detected",
            count=len(deleted_sources),
            files=[Path(src).name for _, src in deleted_sources[:5]],  # Show first 5
        )

    # Clean up output files for deleted sources
    for output_path_str, source_path_str in deleted_sources:
        # Delete the output file
        output_path = site.output_dir / output_path_str
        if output_path.exists():
            try:
                output_path.unlink()
                deleted_count += 1
                logger.debug(
                    "deleted_output_file",
                    source=Path(source_path_str).name,
                    output=output_path_str,
                )

                # Also try to remove empty parent directories
                try:
                    if output_path.parent != site.output_dir:
                        output_path.parent.rmdir()  # Only removes if empty
                except OSError:
                    pass  # Directory not empty or other issue, ignore

            except Exception as e:
                logger.warning("failed_to_delete_output", output=output_path_str, error=str(e))

        # Remove from cache
        if output_path_str in cache.output_sources:
            del cache.output_sources[output_path_str]

        # Remove from file_fingerprints (file_hashes is a compatibility property)
        if source_path_str in cache.file_fingerprints:
            del cache.file_fingerprints[source_path_str]
        if source_path_str in cache.page_tags:
            del cache.page_tags[source_path_str]
        if source_path_str in cache.parsed_content:
            del cache.parsed_content[source_path_str]

    if deleted_count > 0:
        logger.info(
            "cleanup_complete",
            deleted_outputs=deleted_count,
            deleted_sources=len(deleted_sources),
        )

    return deleted_count


def _cleanup_deleted_autodoc_sources(site: Site, cache: BuildCache) -> None:
    """
    Clean up autodoc pages when their source files are deleted.

    Checks tracked autodoc source files and removes corresponding output
    when the source no longer exists. This prevents stale autodoc pages
    from remaining when Python/OpenAPI source files are deleted.

    Args:
        site: Site instance for output directory access
        cache: BuildCache instance with autodoc mappings
    """
    if not hasattr(cache, "autodoc_dependencies"):
        return

    try:
        source_files = list(cache.get_autodoc_source_files())
    except (TypeError, AttributeError):
        return

    deleted_sources: list[str] = []
    for source_file in source_files:
        source_path = Path(source_file)
        if not source_path.exists():
            deleted_sources.append(source_file)

    if not deleted_sources:
        return

    logger.info(
        "autodoc_source_files_deleted",
        count=len(deleted_sources),
        files=[Path(s).name for s in deleted_sources[:5]],
    )

    for source_file in deleted_sources:
        # Get affected autodoc pages before removing from cache
        affected_pages = cache.remove_autodoc_source(source_file)

        # Remove output files for affected pages
        for page_path in affected_pages:
            # Autodoc pages use source_id like "python/api/module.md"
            # Convert to output path: "api/module/index.html"
            url_path = page_path.replace("python/", "").replace("cli/", "")
            if url_path.endswith(".md"):
                url_path = url_path[:-3]
            output_path = site.output_dir / url_path / "index.html"

            if output_path.exists():
                try:
                    output_path.unlink()
                    logger.debug(
                        "autodoc_output_deleted",
                        source=Path(source_file).name,
                        output=str(output_path.relative_to(site.output_dir)),
                    )
                    # Try to remove empty parent directories
                    try:
                        if output_path.parent != site.output_dir:
                            output_path.parent.rmdir()
                    except OSError:
                        pass  # Directory not empty
                except OSError as e:
                    logger.warning(
                        "autodoc_output_delete_failed",
                        output=str(output_path),
                        error=str(e),
                    )

        # Remove from file_fingerprints
        if source_file in cache.file_fingerprints:
            del cache.file_fingerprints[source_file]
