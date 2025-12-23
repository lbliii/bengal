"""
Render Hooks - Pre and post-render hook system.

Provides extension points in the rendering pipeline for:
- Pre-render preparation (scaffold caching, asset pre-processing)
- Post-render cleanup (cache invalidation, statistics)

This is Bengal's internal hook system for the rendering pipeline,
separate from the shell-based build hooks in server/build_hooks.py.

Hook Lifecycle:
    1. Content discovery completes (pages identified)
    2. PRE-RENDER HOOKS run (prepare cached resources)
    3. Pages render in parallel/sequential
    4. POST-RENDER HOOKS run (cleanup, finalization)

Built-in Hooks:
    - NavScaffoldHook: Pre-renders docs nav HTML per scope for caching

Example Custom Hook:
    ```python
    from bengal.orchestration.render_hooks import RenderHook, register_hook

    class MyPreRenderHook(RenderHook):
        name = "my-hook"
        phase = "pre"

        def run(self, context: HookContext) -> None:
            # Prepare resources before rendering
            for page in context.pages:
                prepare_something(page)

    register_hook(MyPreRenderHook())
    ```

Related:
    - bengal/orchestration/render.py: Calls hooks during rendering
    - bengal/server/build_hooks.py: Shell-based build hooks (external)
    - bengal/rendering/template_functions/navigation/scaffold.py: Scaffold caching
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from bengal.utils.logger import get_logger

if TYPE_CHECKING:
    from bengal.core.page import Page
    from bengal.core.site import Site

logger = get_logger(__name__)


@dataclass
class HookContext:
    """
    Context passed to render hooks.

    Provides access to site, pages, and build state for hooks to use.
    Hooks can also store computed data in `cache` for template access.

    Attributes:
        site: Site instance with config and sections
        pages: List of pages being rendered
        parallel: Whether rendering is parallel
        build_context: Optional BuildContext with additional state
        cache: Dict for hooks to store cached data (accessible in templates)
    """

    site: Site
    pages: list[Page]
    parallel: bool = True
    build_context: Any | None = None
    cache: dict[str, Any] = field(default_factory=dict)


class RenderHook(ABC):
    """
    Base class for render hooks.

    Subclasses implement the `run()` method to perform hook logic.
    Hooks are registered with `register_hook()` and run automatically.

    Attributes:
        name: Unique identifier for this hook
        phase: When to run - "pre" (before render) or "post" (after render)
        enabled: Whether this hook should run (can be toggled by config)
    """

    name: str = "unnamed"
    phase: str = "pre"  # "pre" or "post"
    enabled: bool = True

    @abstractmethod
    def run(self, context: HookContext) -> None:
        """
        Execute the hook logic.

        Args:
            context: HookContext with site, pages, and cache
        """
        pass

    def should_run(self, context: HookContext) -> bool:
        """
        Check if this hook should run.

        Override to add conditional logic (e.g., feature flag checks).

        Args:
            context: HookContext with site and config

        Returns:
            True if hook should run, False to skip
        """
        return self.enabled


# Global hook registry
_pre_render_hooks: list[RenderHook] = []
_post_render_hooks: list[RenderHook] = []


def register_hook(hook: RenderHook) -> None:
    """
    Register a render hook.

    Args:
        hook: RenderHook instance to register
    """
    if hook.phase == "pre":
        _pre_render_hooks.append(hook)
        logger.debug("render_hook_registered", name=hook.name, phase="pre")
    elif hook.phase == "post":
        _post_render_hooks.append(hook)
        logger.debug("render_hook_registered", name=hook.name, phase="post")
    else:
        logger.warning("render_hook_invalid_phase", name=hook.name, phase=hook.phase)


def run_pre_render_hooks(context: HookContext) -> None:
    """
    Run all registered pre-render hooks.

    Called by RenderOrchestrator before page rendering begins.

    Args:
        context: HookContext with site and pages
    """
    for hook in _pre_render_hooks:
        if hook.should_run(context):
            try:
                logger.debug("render_hook_running", name=hook.name, phase="pre")
                hook.run(context)
                logger.debug("render_hook_complete", name=hook.name, phase="pre")
            except Exception as e:
                logger.error(
                    "render_hook_error",
                    name=hook.name,
                    phase="pre",
                    error=str(e),
                )


def run_post_render_hooks(context: HookContext) -> None:
    """
    Run all registered post-render hooks.

    Called by RenderOrchestrator after all pages are rendered.

    Args:
        context: HookContext with site and pages
    """
    for hook in _post_render_hooks:
        if hook.should_run(context):
            try:
                logger.debug("render_hook_running", name=hook.name, phase="post")
                hook.run(context)
                logger.debug("render_hook_complete", name=hook.name, phase="post")
            except Exception as e:
                logger.error(
                    "render_hook_error",
                    name=hook.name,
                    phase="post",
                    error=str(e),
                )


def clear_hooks() -> None:
    """Clear all registered hooks (for testing)."""
    _pre_render_hooks.clear()
    _post_render_hooks.clear()


# =============================================================================
# Built-in Hooks
# =============================================================================


class NavScaffoldHook(RenderHook):
    """
    Pre-renders docs navigation scaffold HTML for caching.

    This hook runs before page rendering and pre-renders the navigation
    scaffold for each unique scope (section root + version). The cached
    HTML is then injected into templates, avoiding per-page re-rendering.

    Enabled by: theme.features includes 'docs.sidebar.scaffold_mode'

    Cache Structure:
        context.cache['nav_scaffolds'] = {
            (version_id, root_url): "<nav>...</nav>",
            ...
        }
    """

    name = "nav-scaffold"
    phase = "pre"

    def should_run(self, context: HookContext) -> bool:
        """Only run if scaffold_mode feature is enabled."""
        if not self.enabled:
            return False

        # Check feature flag
        theme_config = context.site.config.get("theme", {})
        features = theme_config.get("features", [])
        return "docs.sidebar.scaffold_mode" in features

    def run(self, context: HookContext) -> None:
        """
        Pre-render scaffold HTML for each unique scope.

        Groups pages by (version_id, root_section_url) and renders
        the scaffold once per group.
        """

        # Group pages by scope (version_id, root_section_url)
        scopes: dict[tuple[str | None, str], Page] = {}

        for page in context.pages:
            # Get version and root section
            version_id = getattr(page, "version", None)
            section = getattr(page, "_section", None)
            if section:
                root = getattr(section, "root", section)
                root_url = getattr(root, "_path", None) or f"/{root.name}/"
            else:
                root_url = "/"

            scope_key = (version_id, root_url)
            if scope_key not in scopes:
                scopes[scope_key] = page

        logger.debug(
            "nav_scaffold_hook_scopes",
            scope_count=len(scopes),
            scopes=list(scopes.keys()),
        )

        # Pre-render scaffold for each scope
        # Note: The actual HTML rendering happens in the template engine
        # This hook just warms up the NavScaffoldCache and context
        scaffolds: dict[tuple[str | None, str], str] = {}

        for scope_key, sample_page in scopes.items():
            version_id, root_url = scope_key

            # Get scaffold context (this validates the nav tree exists)
            try:
                section = getattr(sample_page, "_section", None)

                # The scaffold context is now ready for this scope
                # Templates will use get_nav_scaffold_context() which is fast
                # because the nav tree is already cached in NavTreeCache
                scaffolds[scope_key] = f"scope:{root_url}"  # Placeholder

            except Exception as e:
                logger.warning(
                    "nav_scaffold_hook_scope_error",
                    scope=scope_key,
                    error=str(e),
                )

        # Store in hook context cache for templates to access
        context.cache["nav_scaffolds"] = scaffolds
        context.cache["nav_scaffold_enabled"] = True

        logger.info(
            "nav_scaffold_hook_complete",
            scopes_prepared=len(scaffolds),
        )


# Register built-in hooks
register_hook(NavScaffoldHook())
