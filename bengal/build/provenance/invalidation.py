"""Data-file, template, and taxonomy invalidation for provenance filtering.

Moves the RFC incremental-build-dependency-gaps expansion out of the
orchestration phase so cache and orchestration share one implementation.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from bengal.build.provenance.filter import ProvenanceFilterResult
from bengal.build.provenance.lookups import (
    FALLBACK_INDEX_INCOMPLETE,
    FALLBACK_TEMPLATE_DEPS_MISSING,
    consult_dependency_index,
    dependency_key_candidates,
    get_pages_for_data_file,
    get_pages_from_dependency_index,
    get_taxonomy_term_pages_for_member,
    index_is_complete,
    log_incremental_fallback,
)
from bengal.rendering.template_engine.environment import (
    iter_template_files,
    resolve_template_dirs,
    template_name_for_path,
)
from bengal.utils.observability.logger import get_logger
from bengal.utils.primitives.hashing import hash_file

if TYPE_CHECKING:
    from collections.abc import Sequence

    from bengal.build.contracts import DependencyReadIndex
    from bengal.cache.build_cache import BuildCache
    from bengal.protocols import SiteLike
    from bengal.protocols.core import PageLike

logger = get_logger(__name__)

_INDEX_REASON_PREFIX = {
    "generated": "generated_changed",
    "track": "track_changed",
    "asset": "asset_changed",
    "template": "template_changed",
    "data": "data_file",
}


def _add_expanded_pages(
    expanded: set[Path],
    reasons: dict[str, list[str]],
    pages: set[Path],
    reason: str,
) -> None:
    """Add newly discovered dependents to the expanded set."""
    for page_path in pages:
        if page_path not in expanded:
            expanded.add(page_path)
            reasons.setdefault(str(page_path), []).append(reason)


def detect_changed_data_files(
    cache: BuildCache,
    site: SiteLike,
) -> set[Path]:
    """
    Detect data files that have changed since last build.

    Compares current data file hashes against stored fingerprints.

    Args:
        cache: BuildCache with stored fingerprints
        site: Site instance to find data directory

    Returns:
        Set of changed data file paths
    """
    changed: set[Path] = set()
    data_dir = site.root_path / "data"

    if not data_dir.exists():
        return changed

    # Scan data directory for YAML/JSON files
    for ext in ("*.yaml", "*.yml", "*.json", "*.toml"):
        for data_file in data_dir.glob(f"**/{ext}"):
            try:
                if cache.is_changed(data_file):
                    changed.add(data_file)
            except OSError:
                changed.add(data_file)

    if changed:
        logger.debug(
            "data_files_changed",
            count=len(changed),
            files=[str(f.name) for f in changed],
        )

    return changed


def detect_changed_templates(
    cache: BuildCache,
    site: SiteLike,
) -> set[Path]:
    """
    Detect template files that have changed since last build.

    Compares current template file hashes against stored fingerprints,
    then stores current fingerprints for ALL scanned templates so that
    the next incremental build can detect changes.

    Args:
        cache: BuildCache with stored fingerprints
        site: Site instance to find templates directory

    Returns:
        Set of changed template file paths
    """
    changed: set[Path] = set()
    for tpl_file in iter_template_files(site):
        try:
            file_changed = cache.is_changed(tpl_file)
        except OSError:
            # File error - treat as changed, skip fingerprint update
            changed.add(tpl_file)
            continue

        if file_changed:
            changed.add(tpl_file)
            # Store current fingerprint so the next incremental build can use
            # the mtime/size fast path. Unchanged files already have a valid
            # fingerprint, and cache.is_changed() refreshes touch-only files.
            try:
                stat = tpl_file.stat()
                current_hash = hash_file(tpl_file)
                cache.set_file_fingerprint(
                    tpl_file,
                    {
                        "mtime": stat.st_mtime,
                        "size": stat.st_size,
                        "hash": current_hash,
                    },
                )
            except OSError as e:
                logger.debug(
                    "template_fingerprint_update_failed",
                    file=str(tpl_file),
                    error=str(e),
                )

    if changed:
        logger.debug(
            "templates_changed",
            count=len(changed),
            files=[str(f.name) for f in changed],
        )

    return changed


def expand_forced_changed(
    forced_changed: set[Path],
    cache: BuildCache,
    site: SiteLike,
    pages: Sequence[PageLike],
    dependency_index: DependencyReadIndex | None = None,
) -> tuple[set[Path], dict[str, list[str]]]:
    """
    Expand forced_changed set to include dependency-triggered rebuilds.

    This is the core integration for RFC: rfc-incremental-build-dependency-gaps.

    Queries ``DependencyReadIndex`` for generated/track/asset/template/data
    hits. When the index is present and complete, page-finding scans for
    those kinds do not run; a miss means no dependents. When the index is
    missing, empty, or corrupt, emit a named ``fallback_reason`` and use
    the EffectTracer / cache-graph / full-rebuild path.

    Gap 1: Data file changes → dependent pages
    Gap 2: Member page changes → taxonomy term pages
    Gap 3: Template changes → dependent pages

    Args:
        forced_changed: Initial set of changed paths (from file watcher or content changes)
        cache: BuildCache with dependency tracking
        site: Site instance
        pages: List of all pages (for taxonomy lookup)

    Returns:
        Tuple of (expanded_forced_changed, reasons) where reasons maps
        page paths to lists of why they were added
    """
    expanded = set(forced_changed)
    reasons: dict[str, list[str]] = {}
    resolved_keys: set[tuple[str, str]] = set()

    # Index first: live filter consults the read model before any scan.
    for path in forced_changed:
        pages_by_kind, keys = consult_dependency_index(cache, (path,), dependency_index)
        resolved_keys.update(keys)
        for kind, index_pages in pages_by_kind.items():
            logger.debug(
                "dependency_index_hit",
                kind=kind,
                path=str(path),
                affected_pages=len(index_pages),
            )
            prefix = _INDEX_REASON_PREFIX[kind]
            _add_expanded_pages(expanded, reasons, index_pages, f"{prefix}:{path.name}")

    # Gap 1: Detect data file changes. Page-finding uses the index when
    # complete; otherwise get_pages_for_data_file emits index_incomplete.
    changed_data_files = detect_changed_data_files(cache, site)
    for data_file in changed_data_files:
        data_keys = dependency_key_candidates(cache, data_file)
        if any(("data", key) in resolved_keys for key in data_keys):
            continue
        affected_pages = get_pages_for_data_file(cache, data_file, dependency_index)
        _add_expanded_pages(expanded, reasons, affected_pages, f"data_file:{data_file.name}")

    # Gap 3: Detect template changes
    # Use per-page template dependency tracking when available.
    # Falls back to rebuilding ALL pages when no dependency data exists
    # (first build or cache miss) to ensure correctness.
    changed_templates = detect_changed_templates(cache, site)
    if changed_templates:
        # Resolve template names relative to template dirs (matches determine_template() format)
        template_dirs = resolve_template_dirs(site)

        template_names_str = ", ".join(
            template_name_for_path(t, template_dirs) for t in changed_templates
        )
        unresolved_templates: list[Path] = []
        for changed_template in changed_templates:
            template_name = template_name_for_path(changed_template, template_dirs)
            template_keys = (
                *dependency_key_candidates(cache, changed_template),
                template_name,
            )
            if any(("template", key) in resolved_keys for key in template_keys):
                continue
            unresolved_templates.append(changed_template)

        if unresolved_templates and index_is_complete(dependency_index):
            # Trust the index: hits expand pages; misses mean no dependents.
            for changed_template in unresolved_templates:
                template_name = template_name_for_path(changed_template, template_dirs)
                affected = get_pages_from_dependency_index(
                    dependency_index,
                    ("template",),
                    (*dependency_key_candidates(cache, changed_template), template_name),
                )
                if not affected:
                    continue
                logger.debug(
                    "dependency_index_template_hit",
                    template=template_name,
                    affected_pages=len(affected),
                )
                _add_expanded_pages(
                    expanded,
                    reasons,
                    affected,
                    f"template_changed:{template_name}",
                )
        elif unresolved_templates and cache.template_dependencies:
            # Selective rebuild: only rebuild pages that depend on changed templates
            log_incremental_fallback(
                FALLBACK_INDEX_INCOMPLETE,
                kind="template",
                changed_templates=template_names_str,
            )
            needs_full_rebuild = False
            for changed_template in unresolved_templates:
                template_name = template_name_for_path(changed_template, template_dirs)
                affected_paths = cache.get_pages_for_template(template_name)
                if affected_paths:
                    _add_expanded_pages(
                        expanded,
                        reasons,
                        {Path(page_path_str) for page_path_str in affected_paths},
                        f"template_changed:{template_name}",
                    )
                else:
                    # No dependency data for this template (first build or cache miss)
                    # Fall back to full rebuild for safety
                    needs_full_rebuild = True
                    break
            if needs_full_rebuild:
                logger.info(
                    "template_dependency_partial_miss",
                    reason=FALLBACK_TEMPLATE_DEPS_MISSING,
                    changed_templates=template_names_str,
                    detail=(
                        "Some changed templates have no dependency data — rebuilding all pages"
                    ),
                )
                _add_expanded_pages(
                    expanded,
                    reasons,
                    {page.source_path for page in pages},
                    f"template_changed:{template_names_str}",
                )
        elif unresolved_templates:
            # No template dependency data yet — fall back to rebuilding ALL pages
            logger.info(
                "template_dependency_full_miss",
                reason=FALLBACK_TEMPLATE_DEPS_MISSING,
                changed_templates=template_names_str,
                detail=(
                    "No template dependency data cached — rebuilding all pages "
                    "(first build after cache clear)"
                ),
            )
            _add_expanded_pages(
                expanded,
                reasons,
                {page.source_path for page in pages},
                f"template_changed:{template_names_str}",
            )

    # Gap 2: For content pages that changed, find taxonomy term pages
    # Check which changed pages have tags - their taxonomy term pages need rebuilding
    content_changes = [p for p in forced_changed if p.suffix == ".md"]
    for content_path in content_changes:
        term_pages = get_taxonomy_term_pages_for_member(cache, content_path, site)
        for term_path in term_pages:
            if term_path not in expanded:
                expanded.add(term_path)
                reasons.setdefault(str(term_path), []).append(f"member_changed:{content_path.name}")

    if len(expanded) > len(forced_changed):
        logger.info(
            "dependency_triggered_rebuilds",
            original_count=len(forced_changed),
            expanded_count=len(expanded),
            data_file_triggered=len(changed_data_files),
            template_triggered=len(changed_templates),
            taxonomy_triggered=len(content_changes),
        )

    return expanded, reasons


def apply_taxonomy_cascade(
    result: ProvenanceFilterResult,
    pages_list: Sequence[PageLike],
    incremental: bool,
    dependency_reasons: dict[str, list[str]],
) -> ProvenanceFilterResult:
    """Add taxonomy term pages when member tags changed (Gap 2)."""
    if not result.affected_tags or not incremental:
        return result

    taxonomy_pages_to_add: list[PageLike] = []
    pages_to_build_sources = {p.source_path for p in result.pages_to_build}

    for page in pages_list:
        # Check if this is a taxonomy term page
        is_taxonomy = getattr(page, "virtual", False) and (
            page.metadata.get("_taxonomy_term")
            or page.metadata.get("tag")
            or "/tags/" in str(page.source_path)
            or "/categories/" in str(page.source_path)
        )

        if not is_taxonomy:
            continue

        # Get the tag/term this page represents
        term = (
            page.metadata.get("_taxonomy_term")
            or page.metadata.get("tag")
            or page.metadata.get("title", "").lower()
        )

        if (
            term
            and str(term).lower() in {t.lower() for t in result.affected_tags}
            and page.source_path not in pages_to_build_sources
        ):
            # This taxonomy page lists a tag that was affected
            taxonomy_pages_to_add.append(page)
            dependency_reasons.setdefault(str(page.source_path), []).append(
                f"taxonomy_cascade:tag={term}"
            )

    if not taxonomy_pages_to_add:
        return result

    new_pages_to_build = list(result.pages_to_build) + taxonomy_pages_to_add
    new_pages_skipped = [p for p in result.pages_skipped if p not in taxonomy_pages_to_add]
    cascaded = ProvenanceFilterResult(
        pages_to_build=new_pages_to_build,
        assets_to_process=result.assets_to_process,
        pages_skipped=new_pages_skipped,
        total_pages=result.total_pages,
        cache_hits=len(new_pages_skipped),
        cache_misses=len(new_pages_to_build),
        affected_tags=result.affected_tags,
        affected_sections=result.affected_sections,
        changed_page_paths=result.changed_page_paths,
    )

    logger.info(
        "taxonomy_cascade_triggered",
        affected_tags=list(result.affected_tags),
        taxonomy_pages_added=len(taxonomy_pages_to_add),
    )
    return cascaded
