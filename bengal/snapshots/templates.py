"""
Template analysis for snapshot engine.

Functions for analyzing Jinja2/Kida templates to extract dependency graphs,
partials, and create TemplateSnapshot objects. Used during snapshot creation
for O(1) template→page lookups during incremental builds.

"""

from __future__ import annotations

import hashlib
from collections.abc import Callable
from pathlib import Path
from types import MappingProxyType
from typing import TYPE_CHECKING, Any, cast

if TYPE_CHECKING:
    from bengal.core.site import Site
    from bengal.protocols import SiteLike

from bengal.snapshots.types import (
    PageSnapshot,
    TemplateSnapshot,
)


def _get_template_partials(template_name: str, site: SiteLike) -> list[Path]:
    """
    Get partials used by template via template engine analysis.

    Uses the site's template engine to analyze template dependencies.
    This enables scout thread to warm partials ahead of workers.

    Args:
        template_name: Name of template to analyze
        site: Site instance (needed for template engine access)

    Returns:
        List of Path objects for partial templates used by this template
    """
    from bengal.rendering.engines import create_engine

    try:
        # Create engine to analyze template
        engine = create_engine(site, profile=False)

        # Get template path
        if hasattr(engine, "get_template_path"):
            template_path = engine.get_template_path(template_name)
            if not template_path:
                return []
        else:
            # Fallback: search template dirs manually
            template_path = None
            for template_dir in getattr(engine, "template_dirs", []):
                candidate = Path(template_dir) / template_name
                if candidate.exists():
                    template_path = candidate
                    break
            if not template_path:
                return []

        # Use engine's template analysis if available
        partials: set[str] = set()

        if hasattr(engine, "_track_referenced_templates"):
            # Jinja2/Kida engines have this method
            # Try to extract referenced templates
            if hasattr(engine, "_env"):
                env = engine._env

                # Jinja2 approach
                if hasattr(env, "parse"):
                    try:
                        from jinja2 import meta

                        # Type narrowing: loader may not be on Protocol
                        loader = getattr(env, "loader", None)
                        if loader and hasattr(loader, "get_source"):
                            get_source = cast(
                                Callable[
                                    [Any, str], tuple[str, str | None, Callable[[], bool] | None]
                                ],
                                loader.get_source,
                            )
                            source, _filename, _uptodate = get_source(env, template_name)
                        else:
                            raise AttributeError("Loader does not have get_source method")
                        # Type narrowing: parse method
                        parse_method = cast(Callable[[str], Any], env.parse)
                        ast = parse_method(source)
                        for ref in meta.find_referenced_templates(ast) or []:
                            if isinstance(ref, str):
                                partials.add(ref)
                    except Exception:
                        pass

                # Kida approach (if available)
                if hasattr(env, "get_template"):
                    try:
                        # Type narrowing: get_template may not be callable
                        get_template_method = getattr(env, "get_template", None)
                        if not callable(get_template_method):
                            raise AttributeError("get_template is not callable")
                        template = get_template_method(template_name)
                        if hasattr(template, "_optimized_ast"):
                            ast = template._optimized_ast
                            if hasattr(engine, "_extract_referenced_templates"):
                                # Type narrowing: check if method is callable
                                extract_method = getattr(
                                    engine, "_extract_referenced_templates", None
                                )
                                if callable(extract_method):
                                    referenced = extract_method(ast)
                                    partials.update(referenced)
                    except Exception:
                        pass

        # Convert template names to Paths
        partial_paths: list[Path] = []
        for partial_name in partials:
            if hasattr(engine, "get_template_path"):
                partial_path = engine.get_template_path(partial_name)
                if partial_path:
                    partial_paths.append(partial_path)
            else:
                # Fallback: search template dirs
                for template_dir in getattr(engine, "template_dirs", []):
                    candidate = Path(template_dir) / partial_name
                    if candidate.exists():
                        partial_paths.append(candidate)
                        break

        return partial_paths

    except Exception:
        # Template analysis is optional - don't fail snapshot creation
        return []


def _snapshot_templates(
    site: Site,
    page_cache: dict[int, PageSnapshot],
) -> tuple[
    MappingProxyType[str, TemplateSnapshot],
    MappingProxyType[str, frozenset[str]],
    MappingProxyType[str, tuple[PageSnapshot, ...]],
]:
    """
    Analyze all templates used by pages and create template snapshots.

    Returns:
        templates: Mapping of template name to TemplateSnapshot
        dependency_graph: Reverse index - template_name -> dependent template names
        dependents: Reverse index - template_name -> pages using this template
    """
    templates: dict[str, TemplateSnapshot] = {}
    dependency_graph: dict[str, set[str]] = {}  # Which templates depend on this one

    # Get all unique templates used by pages
    used_templates: set[str] = set()
    template_to_pages: dict[str, list[PageSnapshot]] = {}

    for page in page_cache.values():
        template_name = page.template_name
        used_templates.add(template_name)
        template_to_pages.setdefault(template_name, []).append(page)

    # Analyze each template
    for template_name in used_templates:
        template_snapshot = _analyze_template(template_name, site)
        if template_snapshot:
            templates[template_name] = template_snapshot

            # Build reverse dependency graph
            for dep in template_snapshot.all_dependencies:
                dependency_graph.setdefault(dep, set()).add(template_name)

    # Convert dependency_graph values to frozensets
    dependency_graph_frozen = {k: frozenset(v) for k, v in dependency_graph.items()}

    # Calculate transitive dependents (pages affected by template change)
    # A page is affected if its template or any ancestor template changes
    template_dependents: dict[str, list[PageSnapshot]] = {}

    for template_name in templates:
        # Direct pages using this template
        direct_pages = template_to_pages.get(template_name, [])

        # Templates that extend/include this one (and their pages)
        dependent_templates = _get_transitive_dependents(template_name, dependency_graph_frozen)

        all_affected_pages: list[PageSnapshot] = list(direct_pages)
        for dep_template in dependent_templates:
            all_affected_pages.extend(template_to_pages.get(dep_template, []))

        template_dependents[template_name] = all_affected_pages

    # Also add dependents for templates that are only included (not direct pages)
    for template_name in dependency_graph_frozen:
        if template_name not in template_dependents:
            dependent_templates = _get_transitive_dependents(template_name, dependency_graph_frozen)
            all_affected_pages = []
            for dep_template in dependent_templates:
                all_affected_pages.extend(template_to_pages.get(dep_template, []))
            if all_affected_pages:
                template_dependents[template_name] = all_affected_pages

    return (
        MappingProxyType(templates),
        MappingProxyType(dependency_graph_frozen),
        MappingProxyType({k: tuple(v) for k, v in template_dependents.items()}),
    )


def _analyze_template(template_name: str, site: SiteLike) -> TemplateSnapshot | None:
    """
    Analyze a single template and create a TemplateSnapshot.

    Uses Jinja2/Kida meta analysis to extract:
    - extends relationships
    - includes/imports
    - block definitions
    - macro definitions and usages
    """
    from bengal.rendering.engines import create_engine

    try:
        engine = create_engine(site, profile=False)

        # Get template path
        template_path = None
        if hasattr(engine, "get_template_path"):
            template_path = engine.get_template_path(template_name)

        if not template_path:
            # Search template dirs
            for template_dir in getattr(engine, "template_dirs", []):
                candidate = Path(template_dir) / template_name
                if candidate.exists():
                    template_path = candidate
                    break

        if not template_path or not template_path.exists():
            return None

        # Read template content for hash
        try:
            content = template_path.read_text(encoding="utf-8")
        except Exception:
            content = ""

        content_hash = hashlib.sha256(content.encode()).hexdigest()[:16]

        # Parse template using Jinja2 meta (works for both Jinja2 and Kida)
        extends: str | None = None
        includes: set[str] = set()
        imports: set[str] = set()
        blocks: set[str] = set()
        macros_defined: set[str] = set()
        macros_used: set[str] = set()
        all_deps: set[str] = set()

        if hasattr(engine, "_env"):
            env = engine._env

            try:
                from jinja2 import meta
                from jinja2 import nodes as jinja_nodes

                # Load source
                if hasattr(env, "loader") and env.loader:
                    try:
                        # Type narrowing: Jinja2 loader has get_source method
                        loader = env.loader
                        if not hasattr(loader, "get_source"):
                            raise AttributeError("Loader does not have get_source method")
                        get_source = cast(
                            Callable[[Any, str], tuple[str, str | None, Callable[[], bool] | None]],
                            loader.get_source,
                        )
                        source, _filename, _uptodate = get_source(env, template_name)

                        # Type narrowing: Jinja2 Environment has parse method
                        if not hasattr(env, "parse"):
                            raise AttributeError("Environment does not have parse method")
                        parse_method = cast(Callable[[str], Any], env.parse)
                        ast = parse_method(source)

                        # Find referenced templates (extends, includes, imports)
                        for ref in meta.find_referenced_templates(ast) or []:
                            if isinstance(ref, str):
                                all_deps.add(ref)

                        # Walk AST for more details
                        for node in ast.body:
                            if isinstance(node, jinja_nodes.Extends):
                                if isinstance(node.template, jinja_nodes.Const):
                                    extends = str(node.template.value)
                                    all_deps.add(extends)
                            elif isinstance(node, jinja_nodes.Include):
                                if isinstance(node.template, jinja_nodes.Const):
                                    includes.add(str(node.template.value))
                            elif isinstance(node, jinja_nodes.FromImport):
                                if isinstance(node.template, jinja_nodes.Const):
                                    imports.add(str(node.template.value))
                            elif isinstance(node, jinja_nodes.Block):
                                blocks.add(node.name)
                            elif isinstance(node, jinja_nodes.Macro):
                                macros_defined.add(node.name)

                        # Look for macro calls in the AST
                        def find_macro_calls(node: Any) -> None:
                            if hasattr(node, "node"):
                                if isinstance(node.node, jinja_nodes.Name):
                                    pass  # Simple variable, not a macro call
                            if hasattr(node, "iter_child_nodes"):
                                for child in node.iter_child_nodes():
                                    find_macro_calls(child)

                        find_macro_calls(ast)

                    except Exception:
                        pass

            except ImportError:
                # Jinja2 not available, try basic parsing
                pass

        # Get transitive dependencies
        transitive_deps = _get_transitive_deps_for_template(template_name, site, all_deps)
        all_deps.update(transitive_deps)

        return TemplateSnapshot(
            path=template_path,
            name=template_name,
            extends=extends,
            includes=tuple(sorted(includes)),
            imports=tuple(sorted(imports)),
            blocks=tuple(sorted(blocks)),
            macros_defined=tuple(sorted(macros_defined)),
            macros_used=tuple(sorted(macros_used)),
            content_hash=content_hash,
            all_dependencies=frozenset(all_deps),
        )

    except Exception:
        # Template analysis is optional - don't fail snapshot creation
        return None


def _get_transitive_deps_for_template(
    template_name: str,
    site: SiteLike,
    direct_deps: set[str],
    max_depth: int = 10,
) -> set[str]:
    """
    Recursively find all transitive template dependencies.

    Prevents infinite loops with max_depth and seen set.
    """
    from bengal.rendering.engines import create_engine

    all_deps: set[str] = set()
    seen: set[str] = {template_name}
    queue = list(direct_deps)
    depth = 0

    try:
        engine = create_engine(site, profile=False)
        env = getattr(engine, "_env", None)

        if not env or not hasattr(env, "loader") or not env.loader:
            return all_deps

        from jinja2 import meta

        while queue and depth < max_depth:
            depth += 1
            next_queue: list[str] = []

            for dep_name in queue:
                if dep_name in seen:
                    continue
                seen.add(dep_name)
                all_deps.add(dep_name)

                try:
                    # Type narrowing: loader and parse methods
                    loader = getattr(env, "loader", None)
                    if loader and hasattr(loader, "get_source"):
                        get_source = cast(
                            Callable[[Any, str], tuple[str, str | None, Callable[[], bool] | None]],
                            loader.get_source,
                        )
                        source, _filename, _uptodate = get_source(env, dep_name)
                    else:
                        continue
                    parse_method = cast(Callable[[str], Any], env.parse)
                    ast = parse_method(source)
                    next_queue.extend(
                        ref
                        for ref in (meta.find_referenced_templates(ast) or [])
                        if isinstance(ref, str) and ref not in seen
                    )
                except Exception:
                    continue

            queue = next_queue

    except Exception:
        pass

    return all_deps


def _get_transitive_dependents(
    template_name: str,
    dependency_graph: MappingProxyType[str, frozenset[str]] | dict[str, frozenset[str]],
    max_depth: int = 10,
) -> set[str]:
    """
    Get all templates that transitively depend on the given template.

    If template A extends B, and B extends C, then changing C affects A and B.
    """
    dependents: set[str] = set()
    seen: set[str] = {template_name}
    queue = list(dependency_graph.get(template_name, frozenset()))
    depth = 0

    while queue and depth < max_depth:
        depth += 1
        next_queue: list[str] = []

        for dep_name in queue:
            if dep_name in seen:
                continue
            seen.add(dep_name)
            dependents.add(dep_name)

            # Templates that depend on this dependent
            next_queue.extend(
                further_dep
                for further_dep in dependency_graph.get(dep_name, frozenset())
                if further_dep not in seen
            )

        queue = next_queue

    return dependents


def pages_affected_by_template_change(
    template_path: Path,
    snapshot: SiteSnapshot,
) -> set[PageSnapshot]:
    """
    Instantly determine which pages need rebuild when a template changes.

    O(1) lookup instead of O(pages) scan.

    Args:
        template_path: Path to the changed template
        snapshot: Current site snapshot

    Returns:
        Set of pages that need to be re-rendered
    """
    template_name = template_path.name

    # Direct lookup in template_dependents
    affected = set(snapshot.template_dependents.get(template_name, ()))

    # Also check by full path for templates in theme directories
    for name, template in snapshot.templates.items():
        if template.path == template_path:
            affected.update(snapshot.template_dependents.get(name, ()))

    return affected


# Avoid circular import — SiteSnapshot used in type annotation
from bengal.snapshots.types import SiteSnapshot  # noqa: E402
