"""Kida render path: menus, URLs, named templates, and template strings."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from kida.environment import (
    TemplateNotFoundError as KidaTemplateNotFoundError,
)
from kida.environment import (
    TemplateSyntaxError as KidaTemplateSyntaxError,
)

from bengal.errors import BengalRenderingError
from bengal.errors.codes import ErrorCode
from bengal.rendering.context.lazy import LazyPageContext
from bengal.rendering.engines.errors import TemplateNotFoundError
from bengal.rendering.errors.classifier import ErrorClassifier

if TYPE_CHECKING:
    from pathlib import Path


def get_menu(engine: Any, menu_name: str = "main") -> list[dict]:
    """Get menu items as dicts (cached)."""
    i18n = engine.site.config.get("i18n", {}) or {}
    lang = getattr(engine.site, "current_language", None)
    if lang and i18n.get("strategy") != "none":
        localized = engine.site.menu_localized.get(menu_name, {}).get(lang)
        if localized is not None:
            cache_key = f"{menu_name}:{lang}"
            if cache_key not in engine._menu_dict_cache:
                engine._menu_dict_cache[cache_key] = [item.to_dict() for item in localized]
            return engine._menu_dict_cache[cache_key]

    if menu_name not in engine._menu_dict_cache:
        menu = engine.site.menu.get(menu_name, [])
        engine._menu_dict_cache[menu_name] = [item.to_dict() for item in menu]
    return engine._menu_dict_cache[menu_name]


def get_menu_lang(engine: Any, menu_name: str = "main", lang: str = "") -> list[dict]:
    """Get menu items for a specific language (cached)."""
    if not lang:
        return engine._get_menu(menu_name)

    cache_key = f"{menu_name}:{lang}"
    if cache_key in engine._menu_dict_cache:
        return engine._menu_dict_cache[cache_key]

    localized = engine.site.menu_localized.get(menu_name, {}).get(lang)
    if localized is None:
        return engine._get_menu(menu_name)

    engine._menu_dict_cache[cache_key] = [item.to_dict() for item in localized]
    return engine._menu_dict_cache[cache_key]


def invalidate_menu_cache(engine: Any) -> None:
    """
    Invalidate the menu dict cache.

    Call this after menus are rebuilt to ensure fresh dicts are generated.
    Page-specific active state is computed in templates from the current
    page URL so cached menu dictionaries can be reused across renders.
    """
    engine._menu_dict_cache.clear()


def url_for(
    engine: Any,
    target: Any,
    page: Any = None,
    version: str | None = "current",
    baseurl: bool = True,
) -> str:
    """Generate a render-context-aware URL for pages, sections, and paths."""
    from bengal.rendering.urls import RenderURLContext
    from bengal.rendering.urls import url_for as resolve_url_for

    return resolve_url_for(
        target,
        RenderURLContext.for_page(engine.site, page),
        version=version,
        baseurl=baseurl,
    )


def render_template(
    engine: Any,
    name: str,
    context: dict[str, Any],
) -> str:
    """Render a named template.

    Args:
        name: Template identifier (e.g., "blog/single.html")
        context: Variables available to the template

    Returns:
        Rendered HTML string

    Raises:
        TemplateNotFoundError: If template doesn't exist
        TemplateRenderError: If rendering fails
    """
    # Record template dependency for EffectTracer (via ContextVar)
    from bengal.effects.render_integration import (
        record_extra_dependency,
        record_template_include,
    )

    record_template_include(name)
    template_path = engine.get_template_path(name)
    if template_path:
        record_extra_dependency(template_path)
    # Track all templates in the inheritance chain (extends/includes)
    engine._track_referenced_templates(name)

    try:
        template = engine._env.get_template(name)

        # Get page-aware functions (t, current_lang, etc.)
        # Instead of mutating env.globals (not thread-safe), we pass them in context.
        # Preserve LazyValue entries so Kida only evaluates fields the template reads.
        ctx = LazyPageContext()
        ctx.update(engine._env.globals)
        ctx.update({"site": engine.site, "config": engine.site.config})
        ctx.update(context)

        page = context.get("page")
        if hasattr(engine._env, "_page_aware_factory"):
            page_functions = engine._env._page_aware_factory(page)
            ctx.update(page_functions)

        # Cached blocks are automatically used by Template.render()
        # Profile template rendering if enabled
        if engine._profiler:
            engine._profiler.start_template(name)
            try:
                result = engine._render_kida_template(template, ctx)
            finally:
                engine._profiler.end_template(name)
            return result
        return engine._render_kida_template(template, ctx)

    except KidaTemplateNotFoundError as e:
        raise TemplateNotFoundError(name, engine.template_dirs) from e
    except KidaTemplateSyntaxError as e:
        # Use format_compact() for a structured message when available
        if hasattr(e, "format_compact"):
            msg = f"Template syntax error in '{name}':\n{e.format_compact()}"
        else:
            msg = f"Template syntax error in '{name}': {e}"
        raise BengalRenderingError(
            message=msg,
            code=ErrorCode.R002,
            original_error=e,
            file_path=getattr(e, "filename", None),
            line_number=getattr(e, "lineno", None),
        ) from e
    except TypeError as e:
        # Enhanced error messages for common template callable errors.
        # Delegate code classification to the canonical ErrorClassifier so
        # the live render path cannot drift from its tests: NoneType-not-
        # callable -> R015, macro-resolved-to-Undefined -> R006, otherwise
        # the generic render-output code.
        code = ErrorClassifier().classify(e)
        if code is ErrorCode.R015:
            # Try to identify what was being called
            import traceback

            tb = traceback.extract_tb(e.__traceback__)
            context_info = []
            for frame in reversed(tb):
                if frame.line:
                    context_info.append(f"  at {frame.filename}:{frame.lineno}: {frame.line}")
                    if len(context_info) >= 3:
                        break

            context_str = "\n".join(context_info) if context_info else "  (no context available)"
            raise BengalRenderingError(
                message=(
                    f"Template '{name}': A function or filter is None (not callable).\n"
                    f"Call stack:\n{context_str}\n"
                    f"Check that all filters and template functions are properly registered."
                ),
                code=code,
                original_error=e,
            ) from e
        if code is ErrorCode.R006:
            raise BengalRenderingError(
                message=(
                    f"Template '{name}': A macro from {{% from X import y %}} resolved to "
                    "Undefined. Check that the imported template defines the macro. "
                    "If this occurs during parallel builds, try --no-parallel."
                ),
                code=code,
                original_error=e,
                suggestion="Check that the imported template defines the macro. "
                "If this occurs during parallel builds, try --no-parallel.",
            ) from e
        raise BengalRenderingError(
            message=f"Template render error in '{name}': {e}",
            code=ErrorCode.R010,
            original_error=e,
            file_path=getattr(e, "filename", None),
            line_number=getattr(e, "lineno", None),
        ) from e
    except Exception as e:
        # Use format_compact() for Kida errors that reach the generic handler
        if hasattr(e, "format_compact"):
            msg = f"Template render error in '{name}':\n{e.format_compact()}"
        else:
            msg = f"Template render error in '{name}': {e}"
        raise BengalRenderingError(
            message=msg,
            code=ErrorCode.R010,
            original_error=e,
            file_path=getattr(e, "filename", None),
            line_number=getattr(e, "lineno", None),
            suggestion=getattr(e, "hint", None) or getattr(e, "suggestion", None),
        ) from e


def render_kida_template(engine: Any, template: Any, context: LazyPageContext) -> str:
    """Render a compiled Kida template without materializing lazy values."""
    render_func = getattr(template, "_render_func", None)
    render_scaffold = getattr(template, "_render_scaffold", None)
    check_output_size = getattr(template, "_check_output_size", None)
    if render_func is None or render_scaffold is None or check_output_size is None:
        return template.render(context)

    with render_scaffold(
        (context,),
        {},
        "render",
        use_cached_blocks=True,
    ) as (_eager_context, _render_context, blocks_arg):
        return check_output_size(render_func(context, blocks_arg))


def render_string(
    engine: Any,
    template: str,
    context: dict[str, Any],
    *,
    strict: bool = True,
) -> str:
    """Render a template string.

    Args:
        template: Template content as string
        context: Variables available to the template
        strict: If False, return empty string for undefined variables instead of raising

    Returns:
        Rendered HTML string
    """
    import warnings

    from kida.environment.exceptions import UndefinedError

    try:
        # Dynamic strings bypass bytecode cache intentionally — suppress the
        # kida 0.4.0 UserWarning about from_string() without name=.
        with warnings.catch_warnings():
            warnings.filterwarnings("ignore", message="from_string.*bypasses bytecode cache")
            tmpl = engine._env.from_string(template)

        # Get page-aware functions (t, current_lang, etc.)
        # Instead of mutating env.globals (not thread-safe), we pass them in context.
        ctx = LazyPageContext()
        ctx.update(engine._env.globals)
        ctx.update({"site": engine.site, "config": engine.site.config})
        ctx.update(context)

        page = context.get("page")
        if hasattr(engine._env, "_page_aware_factory"):
            page_functions = engine._env._page_aware_factory(page)
            ctx.update(page_functions)

        return engine._render_kida_template(tmpl, ctx)

    except UndefinedError as e:
        # When strict=False, return empty string for undefined variables
        # This allows preprocessing to handle documentation examples gracefully
        if not strict:
            return ""
        if hasattr(e, "format_compact"):
            msg = f"Template string render error:\n{e.format_compact()}"
        else:
            msg = f"Template string render error: {e}"
        raise BengalRenderingError(
            message=msg,
            code=ErrorCode.R003,
            original_error=e,
            file_path=getattr(e, "filename", None),
            line_number=getattr(e, "lineno", None),
            suggestion=getattr(e, "hint", None) or getattr(e, "suggestion", None),
        ) from e
    except Exception as e:
        if hasattr(e, "format_compact"):
            msg = f"Template string render error:\n{e.format_compact()}"
        else:
            msg = f"Template string render error: {e}"
        raise BengalRenderingError(
            message=msg,
            code=ErrorCode.R010,
            original_error=e,
            file_path=getattr(e, "filename", None),
            line_number=getattr(e, "lineno", None),
            suggestion=getattr(e, "hint", None) or getattr(e, "suggestion", None),
        ) from e


def template_exists(engine: Any, name: str) -> bool:
    """Check if a template exists.

    Args:
        name: Template identifier

    Returns:
        True if template can be loaded
    """
    try:
        engine._env.get_template(name)
        return True
    except KidaTemplateNotFoundError, OSError:
        return False


def get_template_path(engine: Any, name: str) -> Path | None:
    """Resolve template name to filesystem path.

    Args:
        name: Template identifier

    Returns:
        Absolute path to template, or None if not found
    """
    for base in engine.template_dirs:
        path = base / name
        if path.is_file():
            return path
    return None
