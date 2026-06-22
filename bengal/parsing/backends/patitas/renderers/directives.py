"""Directive rendering mixin.

Provides directive node rendering methods as a mixin class.
Handles caching for versioned sites and page-dependent directive detection.

Thread-safe: all state is local to each render() call.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import TYPE_CHECKING, Any

from patitas.stringbuilder import StringBuilder

from bengal.parsing.backends.patitas.renderers.utils import escape_attr, escape_html
from bengal.utils.observability.logger import get_logger
from bengal.utils.paths.normalize import to_posix

# Pattern for extracting hrefs from directive-rendered HTML
_DIRECTIVE_HREF = re.compile(r'<a\s+[^>]*href=["\']([^"\']+)["\']')

logger = get_logger(__name__)

if TYPE_CHECKING:
    from patitas.nodes import Block, Directive

    from bengal.parsing.backends.patitas.renderers.protocols import HtmlRendererProtocol


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

    def _render_directive(self: HtmlRendererProtocol, node: Directive, sb: StringBuilder) -> None:
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
                if is_cacheable and ("xref_index" in sig.parameters or "site" in sig.parameters):
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

        # Render with registered handler or fall back to default
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

            # Pass markdown fragment renderer for include directives
            if "render_markdown_fragment" in sig.parameters:
                kwargs["render_markdown_fragment"] = self.render_markdown_fragment

            # Pass current_page_dir for relative link resolution (./ and ../)
            if "current_page_dir" in sig.parameters:
                kwargs["current_page_dir"] = self._compute_current_page_dir()

            # Try template rendering path if handler supports it
            result = self._try_template_render(node, rendered_children, handler, kwargs)
            if result is not None:
                if cache_key and self._directive_cache:
                    self._directive_cache.put("directive_html", cache_key, result)
                self._collect_directive_links(result)
                sb.append(result)
                return

            handler.render(node, rendered_children, result_sb, **kwargs)
            result = result_sb.build()
            if cache_key and self._directive_cache:
                self._directive_cache.put("directive_html", cache_key, result)
            self._collect_directive_links(result)
            sb.append(result)
            return

        # Default rendering when no handler registered — warn about unknown directive
        self._warn_unknown_directive(node)
        result_sb.append(f'<!-- bengal: unknown directive "{escape_html(node.name)}" -->')
        result_sb.append(f'<div class="directive directive-{escape_attr(node.name)}">')
        if node.title:
            result_sb.append(f'<p class="directive-title">{escape_html(node.title)}</p>')
        result_sb.append(rendered_children)
        result_sb.append("</div>\n")

        result = result_sb.build()
        if cache_key and self._directive_cache:
            self._directive_cache.put("directive_html", cache_key, result)
        self._collect_directive_links(result)
        sb.append(result)

    def _try_template_render(
        self: HtmlRendererProtocol,
        node: Directive,
        rendered_children: str,
        handler: Any,
        kwargs: dict[str, Any],
    ) -> str | None:
        """Try rendering a directive via a Kida template override.

        Returns the rendered HTML string if a template was found, or None
        to fall back to handler.render().

        Template rendering requires both:
        1. The handler exposes get_template_context() returning a dict
        2. The site has a _directive_template_renderer callable

        Template lookup order (most specific wins):
        1. directives/{name}.html    — per-type override (e.g., note.html)
        2. directives/{token_type}.html — handler-level (e.g., admonition.html)

        This lets theme authors override all admonitions with admonition.html
        or target a single type with note.html.
        """
        if not hasattr(handler, "get_template_context"):
            return None

        site = getattr(self, "_site", None)
        renderer = getattr(site, "_directive_template_renderer", None) if site else None
        if renderer is None:
            return None

        ctx = handler.get_template_context(node, rendered_children, **kwargs)
        if ctx is None:
            return None

        # Try per-type template first (e.g., directives/note.html),
        # then fall back to handler-level (e.g., directives/admonition.html)
        token_type = getattr(handler, "token_type", None)
        result = renderer(node.name, ctx)
        if result is None and token_type and token_type != node.name:
            result = renderer(token_type, ctx)
        return result

    def _collect_directive_links(self: HtmlRendererProtocol, html: str) -> None:
        """Extract hrefs from directive output and add to links collector.

        Called after each directive renders. Only runs when a links_collector
        is attached (i.e., during page rendering in the pipeline).
        """
        collector = getattr(self, "_links_collector", None)
        if collector is None or not html or "href" not in html:
            return
        for match in _DIRECTIVE_HREF.finditer(html):
            collector.append(match.group(1))

    def _compute_current_page_dir(self: HtmlRendererProtocol) -> str | None:
        """Derive current_page_dir from page context for relative link resolution."""
        page = self._page_context
        site = getattr(self, "_site", None)
        if not page or not site or not hasattr(page, "source_path"):
            return None
        root_path = getattr(site, "root_path", None)
        if root_path is None:
            return None
        try:
            content_dir = Path(root_path) / "content"
            rel_path = Path(page.source_path).relative_to(content_dir)
            return to_posix(rel_path.parent)
        except (ValueError, TypeError) as e:
            logger.debug(
                "current_page_dir_failed",
                source_path=getattr(page, "source_path", None),
                error=str(e),
            )
            return None

    def _warn_unknown_directive(self: HtmlRendererProtocol, node: Directive) -> None:
        """Emit a warning when an unregistered directive name is encountered.

        Includes fuzzy-match suggestions if a close match exists in the registry.
        """
        from bengal.errors.utils import find_close_matches

        registered_names: frozenset[str] = frozenset()
        if self._directive_registry:
            registered_names = self._directive_registry.names

        match: str | None = None
        if registered_names:
            matches = find_close_matches(node.name, registered_names, n=1, cutoff=0.6)
            if matches:
                match = matches[0]

        # Extract source location from page context if available
        source_hint = ""
        page = self._page_context
        if page and hasattr(page, "source_path"):
            source_hint = f" in {page.source_path}"

        extra: dict[str, Any] = {"directive": node.name}
        if match:
            extra["suggestion"] = f"Did you mean '{match}'?"
        else:
            extra["hint"] = "Check spelling or register a custom directive for this name"
        source = getattr(page, "source_path", None) if page else None
        if source:
            extra["source"] = source

        logger.warning(
            f'Unknown directive "{node.name}"{source_hint}',
            **extra,
        )

    def _directive_ast_cache_key(self: HtmlRendererProtocol, node: Directive) -> str:
        """Generate cache key from directive AST structure without rendering.

        Creates a structural fingerprint of the directive that uniquely
        identifies the rendered output:

        - Directive name, title, options
        - Every node attribute of every descendant block/inline

        The fingerprint is derived by introspecting each node's ``__slots__``
        across its MRO, rather than probing a hand-picked list of attribute
        names. This is deliberately *complete*: omitting a discriminating
        attribute (``List.ordered``, ``ListItem.checked``, table cells,
        fenced-code content, ...) causes distinct directives to collide on the
        same key, so later renders serve an earlier directive's cached HTML.
        Such collisions are order-dependent and surface as flaky parity tests
        (see tests/migration/test_directive_cache_key.py). Hashing the full
        slot set keeps the key faithful as new node types/attributes are added.

        This allows cache lookup BEFORE expensive child rendering.
        """
        parts: list[str] = [node.name, node.title or ""]

        # Options as string
        if node.options:
            parts.append(repr(node.options))

        source = getattr(self, "_source", "") or ""

        def is_node(value: object) -> bool:
            """Heuristic: AST nodes carry a ``location`` slot/attribute."""
            return hasattr(value, "location") and hasattr(type(value), "__slots__")

        slot_cache: dict[type, list[str]] = {}

        def iter_slots(cls: type) -> list[str]:
            """All slot names declared across the node's MRO, in MRO order.

            Memoized per class for this key computation: a directive body can
            contain many nodes of the same type (e.g. list items), so the MRO
            walk runs once per class rather than once per node.
            """
            cached = slot_cache.get(cls)
            if cached is not None:
                return cached
            names: list[str] = []
            for klass in cls.__mro__:
                names.extend(getattr(klass, "__slots__", ()) or ())
            slot_cache[cls] = names
            return names

        def hash_value(value: object) -> str:
            """Hash an arbitrary slot value (node, sequence, or scalar)."""
            if value is None:
                return ""
            if is_node(value):
                return hash_block(value)
            if isinstance(value, (list, tuple)):
                return "[" + ",".join(hash_value(item) for item in value) + "]"
            return str(value)

        def hash_block(block: Block) -> str:
            """Hash a node's full structure without rendering.

            Walks every declared slot (except ``location``) so no
            discriminating attribute can silently collapse two distinct
            directives onto one cache key.
            """
            sig_parts = [type(block).__name__]

            # Fenced code stores content as source offsets (ZCLH), so the
            # offsets alone are not stable across documents — resolve the
            # actual source slice to keep the key content-sensitive.
            source_start = getattr(block, "source_start", None)
            source_end = getattr(block, "source_end", None)
            if isinstance(source_start, int) and isinstance(source_end, int):
                sig_parts.append(source[source_start:source_end])

            for slot in iter_slots(type(block)):
                if slot in ("location", "source_start", "source_end"):
                    continue
                sig_parts.append(slot)
                sig_parts.append(hash_value(getattr(block, slot, None)))

            return "|".join(sig_parts)

        # Hash all children
        children_sig = "".join(hash_block(child) for child in node.children)
        parts.append(str(hash(children_sig)))

        return ":".join(parts)
