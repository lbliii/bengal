"""Fence render dispatch for registered capabilities (#584)."""

from __future__ import annotations

from html import escape
from typing import TYPE_CHECKING

from bengal.capabilities.registry import CapabilityRegistry, get_capability_registry

if TYPE_CHECKING:
    from bengal.capabilities.spec import CapabilitySpec, FenceRenderSpec


def render_fence_html(render: FenceRenderSpec, code: str) -> str:
    """Render fenced code to HTML using a declarative render contract."""
    content = escape(code) if render.escape_content else code
    class_attr = f' class="{render.css_class}"' if render.css_class else ""
    return f"<{render.element}{class_attr}>{content}</{render.element}>\n"


def fence_spec_for_language(
    language: str,
    *,
    registry: CapabilityRegistry | None = None,
) -> CapabilitySpec | None:
    """Return the capability spec registered for a fence language, if any."""
    if not language:
        return None
    registry = registry or get_capability_registry()
    return registry.fence_spec_for_language(language.lower())


def render_fenced_code(
    language: str,
    code: str,
    *,
    registry: CapabilityRegistry | None = None,
) -> str | None:
    """Render a fenced code block via the capability registry, or return None."""
    spec = fence_spec_for_language(language, registry=registry)
    if spec is None:
        return None
    render = spec.resolved_fence_render()
    if render is None:
        return None
    return render_fence_html(render, code)
