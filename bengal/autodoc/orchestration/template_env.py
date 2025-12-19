"""
Template environment factory for autodoc.

Creates and configures Jinja2 template environments for rendering autodoc pages.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any

from jinja2 import Environment, FileSystemLoader, pass_context, select_autoescape
from jinja2.runtime import Context

from bengal.utils.logger import get_logger

if TYPE_CHECKING:
    from bengal.core.site import Site

logger = get_logger(__name__)


def create_template_environment(site: Site) -> Environment:
    """
    Create Jinja2 environment for HTML templates.

    Args:
        site: Site instance for configuration and context

    Returns:
        Configured Jinja2 Environment
    """
    # Import icon function from main template system
    # Icons are already preloaded during main template engine initialization
    from bengal.rendering.template_functions.icons import icon

    # Template directories in priority order
    template_dirs = []

    # User templates (highest priority) - check all reference types
    for ref_type in ["autodoc/python", "autodoc/cli", "openautodoc/python"]:
        user_templates = site.root_path / "templates" / ref_type
        if user_templates.exists():
            template_dirs.append(str(user_templates))

    # Theme templates (for inheriting theme styles) - prefer theme templates
    if site.theme:
        theme_templates = get_theme_templates_dir(site)
        if theme_templates:
            template_dirs.append(str(theme_templates))

    # Built-in fallback templates (lowest priority)
    import bengal

    builtin_templates = Path(bengal.__file__).parent / "autodoc" / "fallback"
    if builtin_templates.exists():
        template_dirs.append(str(builtin_templates))

    if not template_dirs:
        logger.warning("autodoc_no_template_dirs", fallback="inline_templates")
        # Use a minimal fallback
        return Environment(autoescape=select_autoescape())

    env = Environment(
        loader=FileSystemLoader(template_dirs),
        autoescape=select_autoescape(["html", "htm", "xml"]),
        trim_blocks=True,
        lstrip_blocks=True,
    )

    # Add icon function from main template system
    env.globals["icon"] = icon

    # Register ALL template functions (strings, collections, dates, urls, i18n,
    # navigation, seo, etc.)
    # This ensures autodoc templates have access to the same functions as regular templates
    from bengal.rendering.template_functions import register_all

    register_all(env, site)

    # Add global variables that base.html templates expect
    env.globals["site"] = site
    env.globals["config"] = site.config
    env.globals["theme"] = site.theme_config

    # Add versioning context (required by version-selector.html and version-banner.html)
    # Autodoc pages are not versioned, so current_version is always None
    env.globals["versioning_enabled"] = site.versioning_enabled
    env.globals["versions"] = site.versions
    env.globals["current_version"] = None
    env.globals["is_latest_version"] = True

    # Add bengal metadata (used by base.html for generator meta tag)
    from bengal.utils.metadata import build_template_metadata

    try:
        env.globals["bengal"] = build_template_metadata(site)
    except Exception as e:
        logger.debug(
            "autodoc_template_metadata_build_failed",
            error=str(e),
            error_type=type(e).__name__,
        )
        env.globals["bengal"] = {"engine": {"name": "Bengal SSG", "version": "unknown"}}

    # Register dateformat filter (from url_helpers for legacy compatibility)
    from bengal.rendering.template_engine.url_helpers import filter_dateformat

    env.filters["dateformat"] = filter_dateformat

    # Register menu functions (required by base.html templates)
    # These are simplified versions that work without TemplateEngine instance
    def get_menu(menu_name: str = "main") -> list[dict[str, Any]]:
        """Get menu items by name."""
        menu = site.menu.get(menu_name, [])
        return [item.to_dict() for item in menu]

    def get_menu_lang(menu_name: str = "main", lang: str = "") -> list[dict[str, Any]]:
        """Get menu items for a specific language."""
        if not lang:
            return get_menu(menu_name)
        localized = site.menu_localized.get(menu_name, {}).get(lang)
        if localized is None:
            return get_menu(menu_name)
        return [item.to_dict() for item in localized]

    env.globals["get_menu"] = get_menu
    env.globals["get_menu_lang"] = get_menu_lang

    # Register asset_url function (required by base templates)
    # This is a simplified version that works without full TemplateEngine
    from bengal.rendering.template_engine.url_helpers import with_baseurl

    @pass_context
    def asset_url(ctx: Context, asset_path: str) -> str:
        """Generate URL for an asset with baseurl handling."""
        # Normalize path
        safe_path = (asset_path or "").replace("\\", "/").strip()
        while safe_path.startswith("/"):
            safe_path = safe_path[1:]
        if not safe_path:
            return "/assets/"

        # In dev server mode, return simple path
        if site.dev_mode:
            return with_baseurl(f"/assets/{safe_path}", site)

        # Otherwise, return path with baseurl
        return with_baseurl(f"/assets/{safe_path}", site)

    env.globals["asset_url"] = asset_url

    # Register url_for function (required by base templates)
    def url_for(page_path: str) -> str:
        """Generate URL for a page path."""
        if not page_path:
            return "/"
        # Normalize and add baseurl
        path = page_path.strip()
        if not path.startswith("/"):
            path = "/" + path
        return with_baseurl(path, site)

    env.globals["url_for"] = url_for

    # Add Python's getattr for safe attribute access in templates
    # Usage: getattr(element, 'children', []) to safely get children with default
    # Required because templates may use StrictUndefined mode
    env.globals["getattr"] = getattr

    # Note: Custom tests (match) and filters (first_sentence) are now
    # registered via register_all() from bengal.rendering.template_functions

    return env


def get_theme_templates_dir(site: Site) -> Path | None:
    """Get theme templates directory if available."""
    if not site.theme:
        return None

    import bengal

    bengal_dir = Path(bengal.__file__).parent
    theme_dir = bengal_dir / "themes" / site.theme / "templates"
    return theme_dir if theme_dir.exists() else None


def relativize_paths(message: str, site: Site) -> str:
    """
    Convert absolute paths in error messages to project-relative paths.

    Makes error messages less noisy by showing paths relative to the
    project root (e.g., /bengal/themes/... instead of /Users/name/.../bengal/themes/...).

    Args:
        message: Error message that may contain absolute paths
        site: Site instance for root path

    Returns:
        Message with absolute paths converted to project-relative paths
    """
    import re

    root_path = str(site.root_path)
    # Also handle bengal package paths
    import bengal

    bengal_path = str(Path(bengal.__file__).parent.parent)

    # Replace project root path with project name
    project_name = site.root_path.name
    message = message.replace(root_path, f"/{project_name}")

    # Replace bengal package path with /bengal (for theme paths, etc.)
    message = message.replace(bengal_path, "")

    # Clean up any double slashes
    message = re.sub(r"//+", "/", message)

    return message
