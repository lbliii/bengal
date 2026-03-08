"""Template context validation using Kida's validate_context() API.

Validates that templates receive all required context variables before render.
Catches UndefinedError at validation time instead of during build.

RFC: kida-template-introspection
"""

from __future__ import annotations

from dataclasses import dataclass
from types import SimpleNamespace
from typing import TYPE_CHECKING, Any

from bengal.rendering.engines.errors import TemplateError

if TYPE_CHECKING:
    from bengal.protocols import SiteLike, TemplateEngine


@dataclass
class TemplateContextError:
    """Error from template context validation."""

    template: str
    missing_vars: list[str]
    message: str


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

    # Build representative context from first page or minimal globals
    sample_context = _build_sample_context(site)

    errors: list[TemplateContextError] = []

    for name in template_names:
        try:
            template = engine.env.get_template(name)
        except Exception:
            continue

        if not hasattr(template, "validate_context"):
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
        )
        for e in context_errors
    ]
