"""
Template-error fallback and overlay helpers for Renderer.

Strict-undefined / Kida error behavior is unchanged: collect into BuildStats,
re-raise in strict mode, else render the overlay or a minimal HTML page.
"""

from __future__ import annotations

import os
from typing import TYPE_CHECKING, Any

from bengal.protocols import SiteLike
from bengal.rendering.errors import TemplateRenderError

if TYPE_CHECKING:
    from bengal.protocols import PageLike


def get_site_title(renderer: Any) -> str:
    """Get site title from config, supporting both Config and dict."""
    config = renderer.site.config
    if hasattr(config, "site"):
        return config.site.title or "Site"
    site_section = config.get("site", {})
    if isinstance(site_section, dict):
        return site_section.get("title", "Site")
    return config.get("title", "Site")


def render_fallback(renderer: Any, page: PageLike, content: str) -> str:
    """
    Render a fallback HTML page with basic styling.

    When the main template fails, we still try to produce a usable page
    with basic CSS and structure (though without partials/navigation).
    """
    # Try to include CSS if available
    css_link = ""
    if isinstance(renderer.site, SiteLike):
        css_file = renderer.site.output_dir / "assets" / "css" / "style.css"
        if css_file.exists():
            css_link = '<link rel="stylesheet" href="/assets/css/style.css">'

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{page.title} - {renderer._get_site_title()}</title>
    {css_link}
    <style>
        /* Emergency fallback styling */
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            line-height: 1.6;
            max-width: 800px;
            margin: 0 auto;
            padding: 2rem;
            color: #333;
        }}
        .fallback-notice {{
            background: #fff3cd;
            border: 1px solid #ffc107;
            border-radius: 4px;
            padding: 1rem;
            margin-bottom: 2rem;
        }}
        article {{
            background: white;
            padding: 2rem;
            border-radius: 8px;
        }}
        h1 {{ color: #2c3e50; }}
        code {{ background: #f4f4f4; padding: 0.2em 0.4em; border-radius: 3px; }}
        pre {{ background: #f4f4f4; padding: 1rem; border-radius: 4px; overflow-x: auto; }}
    </style>
</head>
<body>
    <div class="fallback-notice">
        <strong>⚠️ Notice:</strong> This page is displayed in fallback mode due to a template error.
        Some features (navigation, sidebars, etc.) may be missing.
    </div>
    <article>
        <h1>{page.title}</h1>
        {content}
    </article>
</body>
</html>
"""


def handle_render_error(
    renderer: Any,
    page: PageLike,
    content: str,
    template_name: str,
    exc: Exception,
) -> str:
    """Collect a template error, re-raise in strict mode, or return overlay HTML."""
    rich_error = TemplateRenderError.from_jinja2_error(
        exc, template_name, page.source_path, renderer.template_engine
    )

    config = renderer.site.config
    if hasattr(config, "build"):
        strict_mode = config.build.strict_mode
        debug_mode = config.build.debug
    else:
        build_section = config.get("build", {})
        strict_mode = (
            build_section.get("strict_mode", False)
            if isinstance(build_section, dict)
            else config.get("strict_mode", False)
        )
        debug_mode = (
            build_section.get("debug", False)
            if isinstance(build_section, dict)
            else config.get("debug", False)
        )

    show_traceback = debug_mode or (os.environ.get("BENGAL_DEV_SERVER") == "1")
    rich_error._show_traceback = show_traceback
    rich_error._original_exception = exc

    # Always collect into build_stats for deferred display after rendering.
    # This prevents interleaved output when parallel threads hit the same error.
    if renderer.build_stats:
        dedup = renderer.build_stats.get_error_deduplicator()
        if dedup.should_display(rich_error):
            renderer.build_stats.add_template_error(rich_error)

    if strict_mode:
        raise rich_error from exc

    # Render the error overlay in place of the page so a developer
    # hitting the URL in the dev server lands on a useful page.
    try:
        from bengal.errors.overlay import render_error_page

        return render_error_page(
            rich_error,
            page_title=f"Build Error — {page.title}",
        )
    except Exception:
        # Defensive: never let the overlay renderer mask the
        # original error path. Fall back to the legacy minimal HTML.
        return renderer._render_fallback(page, content)
