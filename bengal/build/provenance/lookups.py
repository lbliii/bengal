"""Dependency-index and cache-graph lookups for provenance invalidation."""

from __future__ import annotations

from contextlib import suppress
from pathlib import Path
from typing import TYPE_CHECKING

from bengal.utils.observability.logger import get_logger

if TYPE_CHECKING:
    from collections.abc import Iterable

    from bengal.build.contracts import DependencyReadIndex
    from bengal.cache.build_cache import BuildCache
    from bengal.protocols import SiteLike

logger = get_logger(__name__)

INDEX_DEPENDENCY_KINDS: tuple[str, ...] = (
    "generated",
    "track",
    "asset",
    "template",
    "data",
)


def dependency_key_candidates(cache: BuildCache, path: Path) -> tuple[str, ...]:
    """Return stable key candidates for dependency-index lookups."""
    candidates: list[str] = []
    with suppress(OSError, ValueError):
        candidates.append(str(cache._cache_key(path)))
    candidates.append(path.as_posix())
    candidates.append(path.name)

    parts = path.parts
    if "content" in parts:
        rel = Path(*parts[parts.index("content") + 1 :])
        posix = rel.as_posix()
        if posix and posix != ".":
            candidates.append(posix)
            if rel.suffix:
                candidates.append(rel.with_suffix("").as_posix())
    if "generated" in parts:
        rel = Path(*parts[parts.index("generated") + 1 :])
        if rel.name in {"index.md", "index.html"}:
            rel = rel.parent
        posix = rel.as_posix()
        if posix and posix != ".":
            candidates.append(posix)

    return tuple(
        dict.fromkeys(candidate for candidate in candidates if candidate and candidate != ".")
    )


def consult_dependency_index(
    cache: BuildCache,
    paths: Iterable[Path],
    dependency_index: DependencyReadIndex | None,
    *,
    kinds: tuple[str, ...] = INDEX_DEPENDENCY_KINDS,
) -> tuple[dict[str, set[Path]], frozenset[tuple[str, str]]]:
    """Query the read index for affected pages before fallback scans.

    Returns ``(pages_by_kind, resolved_keys)``. ``pages_by_kind`` contains only
    kinds that had at least one hit. ``resolved_keys`` is the ``(kind, key)``
    pairs that produced pages so callers can skip the scan for that kind.
    """
    if dependency_index is None or dependency_index.is_empty:
        return {}, frozenset()

    pages_by_kind: dict[str, set[Path]] = {}
    resolved: set[tuple[str, str]] = set()
    for path in paths:
        keys = dependency_key_candidates(cache, path)
        for kind in kinds:
            if kind == "generated":
                pages = get_pages_for_generated(dependency_index, keys)
            elif kind == "track":
                pages = get_pages_for_track(dependency_index, keys)
            elif kind == "asset":
                pages = get_pages_for_asset(cache, path, dependency_index)
            else:
                pages = get_pages_from_dependency_index(dependency_index, (kind,), keys)
            if not pages:
                continue
            pages_by_kind.setdefault(kind, set()).update(pages)
            resolved.update(
                (kind, key) for key in keys if dependency_index.affected_page_keys(kind, key)
            )
    return pages_by_kind, frozenset(resolved)


def get_pages_from_dependency_index(
    dependency_index: DependencyReadIndex | None,
    dependency_kinds: tuple[str, ...],
    dependency_keys: tuple[str, ...],
) -> set[Path]:
    """Return affected page paths from the read index, or empty for fallback."""
    if dependency_index is None or dependency_index.is_empty:
        return set()

    pages: set[Path] = set()
    for dependency_kind in dependency_kinds:
        for dependency_key in dependency_keys:
            pages.update(
                Path(page_key)
                for page_key in dependency_index.affected_page_keys(dependency_kind, dependency_key)
            )
    return pages


def get_pages_for_data_file(
    cache: BuildCache,
    data_file: Path,
    dependency_index: DependencyReadIndex | None = None,
) -> set[Path]:
    """
    Find pages that depend on a data file.

    Queries the EffectTracer (loaded from effects.json) for pages whose
    rendering recorded a dependency on the given data file.  Falls back
    to the BuildCache dependency graph when no tracer is available.

    Args:
        cache: BuildCache with dependency tracking
        data_file: Path to the data file

    Returns:
        Set of page source paths that depend on this data file
    """
    pages: set[Path] = set()
    index_pages = get_pages_from_dependency_index(
        dependency_index,
        ("data",),
        dependency_key_candidates(cache, data_file),
    )
    if index_pages:
        logger.debug(
            "dependency_index_data_hit",
            data_file=str(data_file),
            affected_pages=len(index_pages),
        )
        return index_pages

    # Primary: query EffectTracer for data file dependencies.
    # During rendering, TrackedData records data file access via
    # record_data_file_access() → EffectContext.data_files → Effect.depends_on.
    # The tracer is loaded from effects.json on incremental builds.
    # Note: we check for tracer effects (not bet.enabled) because enabled
    # controls recording of new effects, not reading persisted ones.
    from bengal.effects.render_integration import BuildEffectTracer

    bet = BuildEffectTracer.get_instance()
    tracer = bet.tracer
    if tracer.effects:
        for effect in tracer.effects:
            if effect.operation != "render_page":
                continue
            if data_file not in effect.depends_on:
                continue
            # Extract the page's source path from metadata rather than
            # scanning depends_on for .md files, which would incorrectly
            # include cascade sources (_index.md parents).
            source = effect.metadata.get("source_path")
            if source:
                pages.add(Path(source))

    # Fallback: check BuildCache dependency graph (for backward compat)
    if not pages:
        dep_key = cache._cache_key(data_file)
        for page_str, deps in cache.dependencies.items():
            if dep_key in deps:
                pages.add(Path(page_str))

    return pages


def get_pages_for_generated(
    dependency_index: DependencyReadIndex | None,
    generated_keys: tuple[str, ...],
) -> set[Path]:
    """Return pages indexed under generated-kind keys, or empty for fallback."""
    return get_pages_from_dependency_index(dependency_index, ("generated",), generated_keys)


def get_pages_for_track(
    dependency_index: DependencyReadIndex | None,
    track_keys: tuple[str, ...],
) -> set[Path]:
    """Return pages indexed under track-kind keys, or empty for fallback."""
    return get_pages_from_dependency_index(dependency_index, ("track",), track_keys)


def get_pages_for_asset(
    cache: BuildCache,
    asset_path: Path,
    dependency_index: DependencyReadIndex | None = None,
) -> set[Path]:
    """Return pages that reference an asset, preferring the read index."""
    index_pages = get_pages_from_dependency_index(
        dependency_index,
        ("asset",),
        dependency_key_candidates(cache, asset_path),
    )
    if index_pages:
        logger.debug(
            "dependency_index_asset_hit",
            asset=str(asset_path),
            affected_pages=len(index_pages),
        )
    return index_pages


def get_pages_for_template(
    cache: BuildCache,
    template_path: Path,
    dependency_index: DependencyReadIndex | None = None,
) -> set[Path]:
    """
    Find pages that use a template.

    Queries the cache's reverse dependency graph for pages that depend
    on the given template.

    Args:
        cache: BuildCache with reverse dependency tracking
        template_path: Path to the template file

    Returns:
        Set of page source paths that use this template
    """
    pages: set[Path] = set()
    index_pages = get_pages_from_dependency_index(
        dependency_index,
        ("template",),
        dependency_key_candidates(cache, template_path),
    )
    if index_pages:
        logger.debug(
            "dependency_index_template_hit",
            template=str(template_path),
            affected_pages=len(index_pages),
        )
        return index_pages

    template_key = cache._cache_key(template_path)

    # Check reverse dependencies
    dependents = cache.reverse_dependencies.get(template_key, set())
    for page_str in dependents:
        pages.add(Path(page_str))

    # Also check forward dependencies (for completeness)
    for page_str, deps in cache.dependencies.items():
        if template_key in deps:
            pages.add(Path(page_str))

    return pages


def get_taxonomy_term_pages_for_member(
    cache: BuildCache,
    member_path: Path,
    site: SiteLike,
) -> set[Path]:
    """
    Find taxonomy term pages that list a member page.

    When a member page's metadata changes (title, date, summary),
    the taxonomy term pages listing it need to be rebuilt.

    Args:
        cache: BuildCache with taxonomy tracking
        member_path: Path to the member page that changed
        site: Site instance to find taxonomy term pages

    Returns:
        Set of taxonomy term page paths to rebuild
    """
    term_pages: set[Path] = set()
    member_key = cache._cache_key(member_path)

    # Get tags for this member page from cache
    tags = cache.taxonomy_index.page_tags.get(member_key, set())

    for tag in tags:
        # Find the virtual taxonomy term page for this tag
        # Taxonomy term pages are virtual (no source file), but we need
        # to identify them so they get rebuilt
        # The key format matches what track_taxonomy() uses
        tag_key = f"tag:{str(tag).lower().replace(' ', '-')}"
        term_page_key = f"_generated/tags/{tag_key}"

        # Add the term page path (virtual)
        # For virtual pages, we use a synthetic path
        term_pages.add(Path(term_page_key))

    return term_pages
