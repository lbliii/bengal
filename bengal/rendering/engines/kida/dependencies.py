"""Template dependency discovery for Kida extends/includes/imports."""

from __future__ import annotations

from typing import Any


def track_referenced_templates(engine: Any, template_name: str) -> None:
    """Track all referenced templates (extends/includes/imports) as dependencies.

    Recursively walks the template tree to find all templates that could
    affect the output. Tracks:
    - Parent templates ({% extends %})
    - Included templates ({% include %})
    - Imported templates ({% import %}, {% from ... import %})

    Args:
        template_name: Name of template to analyze
    """
    from bengal.effects.render_integration import (
        record_extra_dependency,
        record_template_include,
    )

    referenced_templates = engine._get_referenced_template_names(template_name)
    for ref_name in referenced_templates:
        record_template_include(ref_name)
        ref_path = engine.get_template_path(ref_name)
        if ref_path:
            record_extra_dependency(ref_path)


def get_referenced_template_names(engine: Any, template_name: str) -> tuple[str, ...]:
    """Return transitive referenced template names, cached for this engine."""
    with engine._template_dependency_cache_lock:
        cached = engine._template_dependency_cache.get(template_name)
    if cached is not None:
        return cached

    referenced_templates = engine._discover_referenced_template_names(template_name)
    with engine._template_dependency_cache_lock:
        existing = engine._template_dependency_cache.setdefault(
            template_name,
            referenced_templates,
        )
    return existing


def discover_referenced_template_names(engine: Any, template_name: str) -> tuple[str, ...]:
    """Discover transitive referenced templates by walking Kida dependencies."""
    seen: set[str] = {template_name}
    to_process: list[str] = [template_name]
    ordered: list[str] = []

    while to_process:
        current_name = to_process.pop()

        try:
            template = engine._env.get_template(current_name)

            # Prefer Kida's dependencies() API when available (cleaner, public API)
            referenced: set[str] = set()
            if hasattr(template, "dependencies"):
                deps = template.dependencies()
                for key in ("extends", "includes", "embeds", "imports"):
                    referenced.update(deps.get(key, []))

            # Fall back to AST walk if dependencies() returned nothing (e.g. bytecode cache)
            if not referenced:
                ast = getattr(template, "_optimized_ast", None)
                if ast is not None:
                    referenced = engine._extract_referenced_templates(ast)

            for ref_name in referenced:
                if ref_name in seen:
                    continue
                seen.add(ref_name)
                ordered.append(ref_name)

                # Queue for recursive processing (catches nested includes)
                to_process.append(ref_name)

        except AttributeError, TypeError, KeyError, OSError:
            # Template analysis is optional - don't fail the build
            continue

    return tuple(ordered)


def extract_referenced_templates(engine: Any, ast: Any) -> set[str]:
    """Extract all referenced template names from an AST.

    Walks the AST to find Extends, Include, Import, and FromImport nodes
    and extracts their template names (if static strings).

    Args:
        ast: Parsed template AST

    Returns:
        Set of template names referenced by this template
    """
    referenced: set[str] = set()
    nodes_to_visit: list[Any] = [ast]

    while nodes_to_visit:
        node = nodes_to_visit.pop()
        if node is None:
            continue

        node_type = type(node).__name__

        # Check for template-referencing nodes
        if node_type in ("Extends", "Include", "Import", "FromImport"):
            template_expr = getattr(node, "template", None)
            if template_expr and type(template_expr).__name__ == "Const":
                value = getattr(template_expr, "value", None)
                if isinstance(value, str):
                    referenced.add(value)

        # Recurse into child nodes
        for attr in ("body", "else_", "empty", "cases", "default"):
            child = getattr(node, attr, None)
            if child is not None:
                if isinstance(child, (list, tuple)):
                    nodes_to_visit.extend(child)
                else:
                    nodes_to_visit.append(child)

        # Handle extends on Template node
        if node_type == "Template":
            extends = getattr(node, "extends", None)
            if extends:
                nodes_to_visit.append(extends)

    return referenced
