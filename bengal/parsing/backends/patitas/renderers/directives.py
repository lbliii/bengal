"""Directive rendering mixin.

Provides directive node rendering methods as a mixin class.
Handles caching for versioned sites and page-dependent directive detection.

Thread-safe: all state is local to each render() call.
"""

from __future__ import annotations

from typing import Any

from patitas.nodes import Block, Directive
from patitas.stringbuilder import StringBuilder

from bengal.parsing.backends.patitas.renderers.utils import escape_attr, escape_html


# Directives that depend on page context and should NOT be cached
# These output different content based on the current page's location in the site tree
PAGE_DEPENDENT_DIRECTIVES = frozenset(
    {
        "child-cards",  # Shows children of current section
        "breadcrumbs",  # Shows path to current page
        "siblings",  # Shows siblings of current page
        "prev-next",  # Shows previous/next pages
        "related",  # Shows related pages based on tags
        "auto-toc",  # Shows table of contents for current page
    }
)


class DirectiveRendererMixin:
    """Mixin providing directive rendering methods.

    Expects the parent class to provide:
    - _directive_registry: Optional registry
    - _directive_cache: Optional cache
    - _page_context: Optional page context
    - _render_block(node, sb): method
    """

    def _render_directive(self, node: Directive, sb: StringBuilder) -> None:
        """Render a directive block.

        Uses registered handler if available, otherwise falls back to default.
        Caches rendered output for versioned sites (auto-enabled when directive_cache provided).

        Optimization: Check cache BEFORE rendering children to skip work on cache hits.

        Note: Page-dependent directives (those that need page_context or get_page_context,
        or are listed in PAGE_DEPENDENT_DIRECTIVES) are NOT cached since their output
        varies by page. This includes child-cards, breadcrumbs, siblings, prev-next, related, etc.
        """
        import inspect

        # Determine if directive is cacheable (not page-dependent or context-dependent)
        is_cacheable = node.name not in PAGE_DEPENDENT_DIRECTIVES
        handler = None
        sig = None
        if self._directive_registry:
            handler = self._directive_registry.get(node.name)
            if handler and hasattr(handler, "render"):
                sig = inspect.signature(handler.render)
                # Page-dependent directives are NOT cacheable
                if is_cacheable and (
                    "page_context" in sig.parameters or "get_page_context" in sig.parameters
                ):
                    is_cacheable = False
                # Context-dependent directives (xref_index, site) are NOT cacheable
                # because their output varies based on cross-reference resolution
                if is_cacheable and (
                    "xref_index" in sig.parameters or "site" in sig.parameters
                ):
                    is_cacheable = False

        # Check directive cache FIRST (before rendering children) - only for cacheable directives
        cache_key: str | None = None
        if self._directive_cache and is_cacheable:
            # Lightweight AST-based cache key (no rendering needed)
            cache_key = self._directive_ast_cache_key(node)
            cached = self._directive_cache.get("directive_html", cache_key)
            if cached:
                sb.append(cached)
                return

        # Cache miss: now render children
        children_sb = StringBuilder()
        for child in node.children:
            self._render_block(child, children_sb)
        rendered_children = children_sb.build()

        # Render with registered handler
        result_sb = StringBuilder()
        if handler and sig:
            kwargs: dict[str, Any] = {}

            # Pass page context getter for directives that need it (child-cards, breadcrumbs, etc.)
            if "get_page_context" in sig.parameters:
                kwargs["get_page_context"] = lambda: self._page_context

            # Pass page context directly for simpler directive interfaces
            if "page_context" in sig.parameters:
                kwargs["page_context"] = self._page_context

            if "render_child_directive" in sig.parameters:
                kwargs["render_child_directive"] = self._render_block

            # Pass xref_index for directives that resolve cross-references (cards, etc.)
            if "xref_index" in sig.parameters:
                kwargs["xref_index"] = getattr(self, "_xref_index", None)

            # Pass site context for directives that need site-wide information
            if "site" in sig.parameters:
                kwargs["site"] = getattr(self, "_site", None)

            handler.render(node, rendered_children, result_sb, **kwargs)

            result = result_sb.build()
            if cache_key and self._directive_cache:
                self._directive_cache.put("directive_html", cache_key, result)
            sb.append(result)
            return

        # Default rendering
        result_sb.append(f'<div class="directive directive-{escape_attr(node.name)}">')
        if node.title:
            result_sb.append(f'<p class="directive-title">{escape_html(node.title)}</p>')
        result_sb.append(rendered_children)
        result_sb.append("</div>\n")

        result = result_sb.build()
        if cache_key and self._directive_cache:
            self._directive_cache.put("directive_html", cache_key, result)
        sb.append(result)

    def _directive_ast_cache_key(self, node: Directive) -> str:
        """Generate cache key from directive AST structure without rendering.

        Creates a lightweight hash of the directive's structure:
        - Directive name, title, options
        - Recursive structure of all child blocks

        This allows cache lookup BEFORE expensive child rendering.
        """
        parts: list[str] = [node.name, node.title or ""]

        # Options as string
        if node.options:
            parts.append(repr(node.options))

        # Recursive AST structure hash
        def hash_block(block: Block) -> str:
            """Hash a block's structure without rendering."""
            sig_parts = [type(block).__name__]

            # Add content-bearing attributes
            if hasattr(block, "content"):
                sig_parts.append(str(getattr(block, "content", "")))
            if hasattr(block, "code"):
                sig_parts.append(str(getattr(block, "code", "")))
            if hasattr(block, "info"):
                sig_parts.append(str(getattr(block, "info", "")))
            if hasattr(block, "level"):
                sig_parts.append(str(getattr(block, "level", "")))
            if hasattr(block, "url"):
                sig_parts.append(str(getattr(block, "url", "")))

            # Recurse into children
            if hasattr(block, "children"):
                children = getattr(block, "children", ())
                if children:
                    sig_parts.extend(hash_block(child) for child in children)

            return "|".join(sig_parts)

        # Hash all children
        children_sig = "".join(hash_block(child) for child in node.children)
        parts.append(str(hash(children_sig)))

        return ":".join(parts)
