"""Cascade, template, and data-file input helpers for provenance.

These functions are called from ProvenanceFilter during hash computation.
They do not change how provenance is combined — they only collect inputs.
"""

from __future__ import annotations

from collections.abc import Mapping
from contextlib import suppress
from pathlib import Path
from typing import TYPE_CHECKING, Any, cast

from bengal.build.contracts.keys import CacheKey, content_key
from bengal.core.section.utils import get_page_section
from bengal.utils.observability.logger import get_logger

from .assets import get_file_hash

if TYPE_CHECKING:
    from bengal.build.provenance.types import Provenance, ProvenanceRecord
    from bengal.protocols import SiteLike
    from bengal.protocols.core import PageLike

logger = get_logger(__name__)

_TEMPLATE_SUFFIXES = frozenset({".html", ".j2", ".jinja", ".jinja2", ".xml"})
_DATA_SUFFIXES = frozenset({".yaml", ".yml", ".json", ".toml"})


def get_cascade_sources(pf: Any, page: PageLike) -> list[Path]:
    """
    Get all _index.md files that contribute cascade metadata to this page.

    Traverses from the page's section up through parent sections, collecting
    index page source paths. When any cascade source changes, the page's
    provenance hash changes, triggering an incremental rebuild.

    Args:
        page: The page to find cascade sources for

    Returns:
        List of _index.md source paths, ordered from immediate parent to root
    """
    sources: list[Path] = []
    section = get_page_section(page)

    # Fallback: If _section is None but we have a section path in page.core, look it up
    if section is None:
        core = getattr(page, "core", None)
        if core is not None:
            section_path = getattr(core, "section", None)
            if section_path and pf.site:
                with suppress(
                    AttributeError, KeyError, TypeError
                ):  # silent: best-effort provenance extraction
                    section = pf.site.get_section_by_path(section_path)

    # Safety guard: prevent infinite loops from circular references or mock objects
    # Real hierarchies are never deeper than ~50 levels
    max_depth = 100
    depth = 0
    seen_ids: set[int] = set()

    while section is not None and depth < max_depth:
        # Detect circular references by tracking object ids
        section_id = id(section)
        if section_id in seen_ids:
            break  # Circular reference detected
        seen_ids.add(section_id)

        # Check if section has an index page
        index_page = getattr(section, "index_page", None)
        if index_page is not None and getattr(index_page, "virtual", False) is not True:
            # Only check filesystem for real (non-virtual) pages.
            # Virtual pages (autodoc, section-indexes) have synthetic
            # source paths that intentionally don't exist on disk.
            index_path = getattr(index_page, "source_path", None)
            if index_path is not None and isinstance(index_path, Path):
                try:
                    if index_path.exists():
                        sources.append(index_path)
                    elif index_path not in pf._warned_cascade_paths:
                        pf._warned_cascade_paths.add(index_path)
                        logger.warning(
                            "cascade_source_missing",
                            path=str(index_path),
                            hint=f"Expected _index.md at {index_path} — add it or check the content hierarchy",
                        )
                except OSError:
                    if index_path not in pf._warned_cascade_paths:
                        pf._warned_cascade_paths.add(index_path)
                        logger.warning(
                            "cascade_source_inaccessible",
                            path=str(index_path),
                            hint="File system error — check permissions on the content directory",
                        )

        # Move to parent section
        parent = getattr(section, "parent", None)
        # Break if parent is the same object (self-reference) or not a real section
        if parent is section or parent is None:
            break
        section = parent
        depth += 1

    # Diagnostic logging for cascade source discovery
    page_path = pf._get_page_key(page)
    if sources:
        logger.debug(
            "cascade_sources_found",
            page_path=str(page_path),
            source_count=len(sources),
            sources=[str(s) for s in sources],
        )
    else:
        # Log when NO cascade sources found - this might indicate a problem
        initial_section = get_page_section(page)
        logger.debug(
            "no_cascade_sources",
            page_path=str(page_path),
            has_section=initial_section is not None,
            section_name=getattr(initial_section, "name", None) if initial_section else None,
            section_has_index=getattr(initial_section, "index_page", None) is not None
            if initial_section
            else False,
        )

    return sources


def template_names_for_page(pf: Any, page: PageLike) -> set[str]:
    """Return known template names for a page from metadata and render effects."""
    names: set[str] = set()
    metadata = getattr(page, "metadata", {})
    template_attr = getattr(page, "template", None)
    if isinstance(template_attr, str) and template_attr:
        names.add(template_attr)
    elif isinstance(metadata, Mapping) and isinstance(metadata.get("template"), str):
        names.add(metadata["template"])
    elif isinstance(metadata, Mapping):
        page_type = metadata.get("type", "page")
        if page_type == "section" or metadata.get("is_section"):
            names.add("list.html")
        elif page_type == "page":
            names.add("page.html")
        else:
            names.add("single.html")

    for dep in render_dependencies_for_page(pf, page):
        if isinstance(dep, str) and looks_like_template_name(dep):
            names.add(dep)

    return names


def looks_like_template_name(value: str) -> bool:
    """Return True for dependency keys that look like template filenames."""
    return Path(value).suffix.lower() in _TEMPLATE_SUFFIXES


def resolve_template_path(pf: Any, template_name: str) -> Path | None:
    """Resolve a template name against render-visible template directories."""
    from bengal.rendering.template_engine.environment import resolve_template_dirs

    site_like = cast("SiteLike", pf.site)
    for template_dir in resolve_template_dirs(site_like):
        candidate = template_dir / template_name
        try:
            if candidate.exists():
                return candidate
        except OSError:
            continue
    return None


def add_template_inputs(pf: Any, provenance: Provenance, page: PageLike) -> Provenance:
    """Add primary and render-observed template files to page provenance."""
    from bengal.rendering.template_engine.environment import (
        resolve_template_dirs,
        template_name_for_path,
    )

    site_like = cast("SiteLike", pf.site)
    template_dirs = resolve_template_dirs(site_like)
    template_paths: dict[str, Path] = {}

    for template_name in template_names_for_page(pf, page):
        resolved = resolve_template_path(pf, template_name)
        if resolved is not None:
            template_paths[template_name] = resolved

    for dep in render_dependencies_for_page(pf, page):
        if isinstance(dep, Path) and dep.suffix.lower() in _TEMPLATE_SUFFIXES:
            try:
                if dep.exists():
                    template_paths[template_name_for_path(dep, template_dirs)] = dep
            except OSError:
                continue

    for template_name, template_path in sorted(template_paths.items()):
        try:
            provenance = provenance.with_input(
                "template",
                CacheKey(template_name),
                get_file_hash(pf, template_path),
            )
        except OSError:
            continue
    return provenance


def render_dependencies_for_page(pf: Any, page: PageLike) -> tuple[Path | str, ...]:
    """Return render-time dependencies recorded for a page, if any."""
    from bengal.effects.render_integration import BuildEffectTracer

    effects = BuildEffectTracer.get_instance().tracer.effects
    effect_count = len(effects)
    with pf._session_lock:
        cached = pf._render_dependency_cache
    if cached is not None and cached[0] == effect_count:
        return cached[1].get(pf._get_page_key(page), ())

    dependencies_by_source: dict[CacheKey, list[Path | str]] = {}
    for effect in effects:
        if effect.operation != "render_page":
            continue
        source = effect.metadata.get("source_path")
        if not source:
            continue
        try:
            source_key = content_key(Path(source), pf.site.root_path)
        except OSError, TypeError, ValueError:
            source_key = CacheKey(str(source))
        dependencies_by_source.setdefault(source_key, []).extend(effect.depends_on)

    frozen = {key: tuple(values) for key, values in dependencies_by_source.items()}
    with pf._session_lock:
        pf._render_dependency_cache = (effect_count, frozen)
    return frozen.get(pf._get_page_key(page), ())


def resolve_data_dependency(pf: Any, dependency: Path) -> Path | None:
    """Resolve a render dependency if it points into the site's data directory."""
    candidate = dependency if dependency.is_absolute() else pf.site.root_path / dependency
    try:
        rel = candidate.resolve().relative_to((pf.site.root_path / "data").resolve())
    except OSError, ValueError:
        return None
    if candidate.suffix.lower() not in _DATA_SUFFIXES or ".." in rel.parts:
        return None
    try:
        if candidate.exists():
            return candidate
    except OSError:
        return None
    return None


def add_data_inputs(pf: Any, provenance: Provenance, page: PageLike) -> Provenance:
    """Add data files observed during page rendering to page provenance."""
    data_paths: set[Path] = set()
    for dep in render_dependencies_for_page(pf, page):
        if isinstance(dep, Path):
            resolved = resolve_data_dependency(pf, dep)
            if resolved is not None:
                data_paths.add(resolved)

    for data_path in sorted(data_paths):
        try:
            provenance = provenance.with_input(
                "data",
                content_key(data_path, pf.site.root_path),
                get_file_hash(pf, data_path),
            )
        except OSError:
            continue
    return provenance


def extract_input_paths_for_mtime(pf: Any, record: ProvenanceRecord) -> list[str]:
    """
    Extract file paths from provenance record for mtime short-circuit.

    Returns paths that resolve to existing files. Skips config, taxonomy, virtual.
    """
    result: list[str] = []
    for inp in record.provenance.inputs:
        if inp.input_type in ("content", "autodoc_source", "cli_source", "data"):
            path_str = str(inp.path)
        elif inp.input_type.startswith("cascade_"):
            path_str = str(inp.path).replace("cascade:", "", 1)
        elif inp.input_type == "template":
            template_path = resolve_template_path(pf, str(inp.path))
            if template_path is None:
                continue
            path_str = str(template_path)
        else:
            continue  # Skip config, taxonomy, virtual

        # Resolve to file - try site root first, then parent
        for base in (pf.site.root_path, pf.site.root_path.parent):
            full_path = base / path_str
            try:
                if full_path.exists():
                    # Return path relative to site root for consistency
                    try:
                        rel = str(full_path.relative_to(pf.site.root_path))
                    except ValueError:
                        rel = path_str
                    result.append(rel)
                    break
            except OSError:
                continue
    return result


def collect_affected(
    page: PageLike,
    affected_tags: set[str],
    affected_sections: set[str],
) -> None:
    """Collect tags and sections affected by a changed page."""
    # Collect tags
    if hasattr(page, "tags") and page.tags:
        affected_tags.update(page.tags)

    # Collect section
    if (section := get_page_section(page)) and hasattr(section, "path"):
        affected_sections.add(str(section.path))
