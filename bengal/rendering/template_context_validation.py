"""Template context validation using Kida's validate_context() API.

Validates that templates receive all required context variables before render.
Catches UndefinedError at validation time instead of during build.

RFC: kida-template-introspection
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, is_dataclass
from dataclasses import fields as dataclass_fields
from types import MappingProxyType, SimpleNamespace
from typing import TYPE_CHECKING, Any

from bengal.rendering.engines.errors import TemplateError
from bengal.utils.observability.logger import get_logger

if TYPE_CHECKING:
    from bengal.protocols import SiteLike, TemplateEngine


@dataclass
class TemplateContextError:
    """Error from template context validation."""

    template: str
    missing_vars: list[str]
    message: str
    severity: str = "error"
    suggestion: str | None = None
    diagnostic_code: str | None = None


def validate_template_contexts(
    engine: TemplateEngine,
    site: SiteLike,
    template_names: list[str] | None = None,
) -> list[TemplateContextError]:
    """Validate that templates receive all required context variables.

    Uses Kida's template.validate_context() to check for missing variables
    before render. Only works with engines that support INTROSPECTION (Kida).

    Args:
        engine: Template engine instance
        site: Site instance for building representative context
        template_names: Optional list of template names to validate.
                        If None, validates all templates from engine.list_templates().

    Returns:
        List of TemplateContextError for templates with missing variables
    """
    from bengal.protocols import EngineCapability

    if not engine.has_capability(EngineCapability.INTROSPECTION):
        return []

    if template_names is None:
        template_names = engine.list_templates()

    # Build representative context from first page or minimal globals.
    sample_context = _build_sample_context(site)
    contract_paths = _build_contract_paths(sample_context)

    errors: list[TemplateContextError] = []

    for name in template_names:
        try:
            template = engine.env.get_template(name)
        except Exception:  # noqa: S112
            continue

        if not hasattr(template, "validate_context"):
            continue

        contract_errors = _check_kida_context_contract(template, contract_paths)
        if contract_errors:
            errors.extend(contract_errors)
            continue

        missing = template.validate_context(sample_context)
        if missing:
            errors.append(
                TemplateContextError(
                    template=name,
                    missing_vars=missing,
                    message=f"Missing context variables: {', '.join(sorted(missing))}",
                )
            )

    return errors


_DYNAMIC_CONTEXT_PREFIXES = (
    "metadata.",
    "page.metadata.",
    "page.params.",
    "params.",
    "site.data.",
    "site.params.",
    "config.params.",
    "theme.",
    "menus.",
)


def _check_kida_context_contract(
    template: Any,
    contract_paths: set[str],
) -> list[TemplateContextError]:
    """Use Kida's dotted-path contract checker when available."""
    try:
        from kida.analysis import check_context_contract
    except ImportError:
        return []

    issues = check_context_contract(template, contract_paths)
    errors: list[TemplateContextError] = []
    for issue in issues:
        path = getattr(issue, "path", "")
        if any(path.startswith(prefix) for prefix in _DYNAMIC_CONTEXT_PREFIXES):
            continue
        errors.append(
            TemplateContextError(
                template=getattr(issue, "template_name", None) or getattr(template, "name", ""),
                missing_vars=[path] if path else [],
                message=getattr(issue, "message", str(issue)),
                severity=getattr(issue, "severity", "error"),
                suggestion=getattr(issue, "suggestion", None),
                diagnostic_code=getattr(issue, "code", None),
            )
        )
    return errors


def _build_contract_paths(context: Mapping[str, Any]) -> set[str]:
    """Build dotted context paths for Kida 0.9 contract validation."""
    paths: set[str] = set()
    for key, value in context.items():
        key_str = str(key)
        paths.add(key_str)
        _collect_contract_paths(value, key_str, paths, depth=0)
    return paths


def _collect_contract_paths(
    value: Any,
    prefix: str,
    paths: set[str],
    *,
    depth: int,
) -> None:
    """Collect stable dotted paths without executing arbitrary callables."""
    if depth >= 4 or value is None or isinstance(value, str | bytes | int | float | bool):
        return

    if isinstance(value, Mapping | MappingProxyType):
        for key, child in value.items():
            if isinstance(key, str):
                child_prefix = f"{prefix}.{key}"
                paths.add(child_prefix)
                _collect_contract_paths(child, child_prefix, paths, depth=depth + 1)
        return

    if isinstance(value, SimpleNamespace):
        items = vars(value).items()
    elif is_dataclass(value):
        items = (
            (field.name, getattr(value, field.name, None)) for field in dataclass_fields(value)
        )
    else:
        items = _public_context_attrs(value)

    for name, child in items:
        if not name or name.startswith("_") or callable(child):
            continue
        child_prefix = f"{prefix}.{name}"
        paths.add(child_prefix)
        _collect_contract_paths(child, child_prefix, paths, depth=depth + 1)


def _public_context_attrs(value: Any) -> list[tuple[str, Any]]:
    """Return public non-callable attributes for Bengal context wrappers."""
    module = type(value).__module__
    if not module.startswith("bengal."):
        return []

    attrs: list[tuple[str, Any]] = []
    for name in dir(type(value)):
        if name.startswith("_"):
            continue
        descriptor = getattr(type(value), name, None)
        if not isinstance(descriptor, property):
            continue
        try:
            child = getattr(value, name)
        except Exception as e:
            get_logger(__name__).debug(
                "template_context_contract_attr_skipped",
                context_type=type(value).__name__,
                attribute=name,
                error=str(e),
                error_type=type(e).__name__,
            )
            continue
        attrs.append((name, child))
    return attrs


def _build_sample_context(site: SiteLike) -> dict[str, Any]:
    """Build a representative context for validation.

    Uses first page from site if available, otherwise minimal globals.
    """
    from bengal.rendering.context import build_page_context, get_engine_globals

    # Start with globals (site, config, theme, etc.)
    context = dict(get_engine_globals(site))

    # Add page context if we have pages
    if site.pages:
        page = site.pages[0]
        content = page.html_content or "" if hasattr(page, "html_content") else ""
        page_context = build_page_context(
            page=page,
            site=site,
            content=content,
            lazy=False,
        )
        context.update(page_context)
    else:
        # Minimal page-like object for templates that only need basic structure
        mock_page = SimpleNamespace(
            title="Sample",
            _path="/sample/",
            metadata={},
            _section=None,
            html_content="",
        )
        if hasattr(site, "regular_pages") and site.regular_pages:
            mock_page._section = getattr(site.regular_pages[0], "_section", None)
        page_context = build_page_context(
            page=mock_page,
            site=site,
            content="",
            lazy=False,
        )
        context.update(page_context)

    return context


def context_errors_to_template_errors(
    context_errors: list[TemplateContextError],
) -> list[TemplateError]:
    """Convert TemplateContextError to TemplateError for CLI reporting."""
    return [
        TemplateError(
            template=e.template,
            message=e.message,
            error_type="undefined",
            severity=e.severity,
            suggestion=e.suggestion,
            diagnostic_code=e.diagnostic_code,
        )
        for e in context_errors
    ]
