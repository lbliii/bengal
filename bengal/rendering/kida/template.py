"""Kida Template — compiled template object.

The Template class represents a compiled template ready for rendering.
Templates are immutable and thread-safe.

Key Design:
    - StringBuilder pattern instead of generator yields
    - Context is a simple dict (no wrapper objects at runtime)
    - Filters are bound at compile time for fast dispatch

Complexity:
    - render(): O(n) where n = output size
    - _escape(): O(n) single-pass using str.translate()
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, Any

from markupsafe import Markup

if TYPE_CHECKING:
    from bengal.rendering.kida.environment import Environment


# Pre-compiled escape table for O(n) single-pass HTML escaping
# This replaces the O(5n) chained .replace() approach
_ESCAPE_TABLE = str.maketrans(
    {
        "&": "&amp;",
        "<": "&lt;",
        ">": "&gt;",
        '"': "&quot;",
        "'": "&#39;",
    }
)

# Fast path: regex to check if escaping is needed at all
_ESCAPE_CHECK = re.compile(r'[&<>"\']')


class LoopContext:
    """Loop variable providing iteration metadata.

    Available as `loop` inside {% for %} blocks:
        - loop.index: 1-based iteration count
        - loop.index0: 0-based iteration count
        - loop.first: True if first iteration
        - loop.last: True if last iteration
        - loop.length: Total number of items
        - loop.revindex: Reverse 1-based index
        - loop.revindex0: Reverse 0-based index
        - loop.cycle(*values): Cycle through values
        - loop.previtem: Previous item (None on first)
        - loop.nextitem: Next item (None on last)

    Example:
        >>> {% for item in items %}
        ...     {{ loop.index }}: {{ item }}
        ...     {% if loop.first %}(first!){% endif %}
        ... {% endfor %}
    """

    __slots__ = ("_items", "_index", "_length")

    def __init__(self, items: list) -> None:
        self._items = items
        self._length = len(items)
        self._index = 0

    def __iter__(self):
        """Iterate through items, updating index for each."""
        for i, item in enumerate(self._items):
            self._index = i
            yield item

    @property
    def index(self) -> int:
        """1-based iteration count."""
        return self._index + 1

    @property
    def index0(self) -> int:
        """0-based iteration count."""
        return self._index

    @property
    def first(self) -> bool:
        """True if this is the first iteration."""
        return self._index == 0

    @property
    def last(self) -> bool:
        """True if this is the last iteration."""
        return self._index == self._length - 1

    @property
    def length(self) -> int:
        """Total number of items in the sequence."""
        return self._length

    @property
    def revindex(self) -> int:
        """Reverse 1-based index (counts down to 1)."""
        return self._length - self._index

    @property
    def revindex0(self) -> int:
        """Reverse 0-based index (counts down to 0)."""
        return self._length - self._index - 1

    @property
    def previtem(self) -> Any:
        """Previous item in the sequence, or None if first."""
        if self._index == 0:
            return None
        return self._items[self._index - 1]

    @property
    def nextitem(self) -> Any:
        """Next item in the sequence, or None if last."""
        if self._index >= self._length - 1:
            return None
        return self._items[self._index + 1]

    def cycle(self, *values: Any) -> Any:
        """Cycle through the given values.

        Example:
            {{ loop.cycle('odd', 'even') }}
        """
        if not values:
            return None
        return values[self._index % len(values)]

    def __repr__(self) -> str:
        return f"<LoopContext {self.index}/{self.length}>"


class Template:
    """Compiled template ready for rendering.

    Templates are immutable and thread-safe. Each render() call
    creates its own local state (StringBuilder pattern).

    Example:
        >>> env = Environment()
        >>> t = env.from_string("Hello, {{ name }}!")
        >>> t.render(name="World")
        'Hello, World!'
    """

    __slots__ = ("_env", "_code", "_name", "_filename", "_render_func")

    def __init__(
        self,
        env: Environment,
        code: Any,  # Compiled code object
        name: str | None,
        filename: str | None,
    ):
        """Initialize template with compiled code.

        Args:
            env: Parent Environment
            code: Compiled Python code object
            name: Template name (for error messages)
            filename: Source filename (for error messages)
        """
        self._env = env
        self._code = code
        self._name = name
        self._filename = filename

        # Include helper - loads and renders included template
        def _include(template_name: str, context: dict, ignore_missing: bool = False) -> str:
            try:
                included = env.get_template(template_name)
                return included.render(**context)
            except Exception:
                if ignore_missing:
                    return ""
                raise

        # Extends helper - renders parent template with child's blocks
        def _extends(template_name: str, context: dict, blocks: dict) -> str:
            parent = env.get_template(template_name)
            # Guard against templates that failed to compile properly
            if parent._render_func is None:
                raise RuntimeError(
                    f"Template '{template_name}' not properly compiled: "
                    f"_render_func is None. Check for syntax errors in the template."
                )
            # Call parent's render function with blocks dict
            return parent._render_func(context, blocks)

        # Import macros from another template
        def _import_macros(template_name: str, with_context: bool, context: dict) -> dict:
            imported = env.get_template(template_name)
            # Guard against templates that failed to compile properly
            if imported._render_func is None:
                raise RuntimeError(
                    f"Template '{template_name}' not properly compiled: "
                    f"_render_func is None. Check for syntax errors in the template."
                )
            # Create a context for the imported template
            # ALWAYS include globals (filters, functions like canonical_url, icon, etc.)
            # The with_context flag controls whether CALLER's local variables are passed
            # This matches Jinja2 behavior where globals are always available to macros
            import_ctx = dict(env.globals)
            if with_context:
                import_ctx.update(context)
            # Execute the template to define macros in its context
            imported._render_func(import_ctx, None)
            # Return the context (which now contains the macros)
            return import_ctx

        # Cache helpers - use environment's cache if available
        def _cache_get(key: str) -> str | None:
            """Get cached fragment by key."""
            cache = getattr(env, "_fragment_cache", None)
            if cache is not None:
                return cache.get(key)
            return None

        def _cache_set(key: str, value: str, ttl: str | None = None) -> None:
            """Set cached fragment."""
            cache = getattr(env, "_fragment_cache", None)
            if cache is None:
                # Create a simple dict cache if not provided
                env._fragment_cache = {}  # type: ignore[attr-defined]
                cache = env._fragment_cache
            cache[key] = value
            # Note: TTL handling would require a more sophisticated cache

        # Execute the code to get the render function
        namespace: dict[str, Any] = {
            "__builtins__": {},
            "_env": env,
            "_filters": env._filters,
            "_tests": env._tests,
            "_escape": self._escape,
            "_getattr": self._safe_getattr,
            "_include": _include,
            "_extends": _extends,
            "_import_macros": _import_macros,
            "_cache_get": _cache_get,
            "_cache_set": _cache_set,
            "_Markup": Markup,
            "_LoopContext": LoopContext,
            "_str": str,
            "_len": len,
            "_range": range,
            "_list": list,
            "_dict": dict,
            "_set": set,
            "_tuple": tuple,
            "_bool": bool,
            "_int": int,
            "_float": float,
        }
        exec(code, namespace)
        self._render_func = namespace.get("render")

    @property
    def name(self) -> str | None:
        """Template name."""
        return self._name

    @property
    def filename(self) -> str | None:
        """Source filename."""
        return self._filename

    def render(self, *args: Any, **kwargs: Any) -> str:
        """Render template with given context.

        Args:
            *args: Single dict of context variables
            **kwargs: Context variables as keyword arguments

        Returns:
            Rendered template as string

        Example:
            >>> t.render(name="World")
            'Hello, World!'
            >>> t.render({"name": "World"})
            'Hello, World!'
        """
        from bengal.rendering.kida.environment.exceptions import TemplateRuntimeError

        # Build context
        ctx: dict[str, Any] = {}

        # Add globals
        ctx.update(self._env.globals)

        # Add positional dict arg
        if args:
            if len(args) == 1 and isinstance(args[0], dict):
                ctx.update(args[0])
            else:
                raise TypeError(
                    f"render() takes at most 1 positional argument (a dict), got {len(args)}"
                )

        # Add keyword args
        ctx.update(kwargs)

        # Inject template metadata for error context
        ctx["_template"] = self._name
        ctx["_line"] = 0

        # Render with error enhancement
        if self._render_func is None:
            raise RuntimeError("Template not properly compiled")

        try:
            return self._render_func(ctx)
        except TemplateRuntimeError:
            # Already enhanced, re-raise as-is
            raise
        except Exception as e:
            # Enhance generic exceptions with template context
            raise self._enhance_error(e, ctx) from e

    def _enhance_error(self, error: Exception, ctx: dict[str, Any]) -> Exception:
        """Enhance a generic exception with template context.

        Converts generic Python exceptions into TemplateRuntimeError with
        template name and line number context.
        """
        from bengal.rendering.kida.environment.exceptions import (
            NoneComparisonError,
            TemplateRuntimeError,
        )

        template_name = ctx.get("_template")
        lineno = ctx.get("_line")
        error_str = str(error)

        # Handle None comparison errors specially
        if isinstance(error, TypeError) and "NoneType" in error_str:
            return NoneComparisonError(
                None,
                None,
                template_name=template_name,
                lineno=lineno,
                expression="<see stack trace>",
            )

        # Generic error enhancement
        return TemplateRuntimeError(
            error_str,
            template_name=template_name,
            lineno=lineno,
        )

    async def render_async(self, *args: Any, **kwargs: Any) -> str:
        """Render template asynchronously.

        For templates with async expressions or async for loops.

        Args:
            *args: Single dict of context variables
            **kwargs: Context variables as keyword arguments

        Returns:
            Rendered template as string
        """
        from bengal.rendering.kida.environment.exceptions import TemplateRuntimeError

        # Build context
        ctx: dict[str, Any] = {}
        ctx.update(self._env.globals)
        if args and isinstance(args[0], dict):
            ctx.update(args[0])
        ctx.update(kwargs)

        # Inject template metadata for error context
        ctx["_template"] = self._name
        ctx["_line"] = 0

        # Check for async render function
        render_async_func = getattr(self, "_render_async_func", None)
        if render_async_func is None:
            # Fall back to sync render
            return self.render(*args, **kwargs)

        try:
            return await render_async_func(ctx)
        except TemplateRuntimeError:
            raise
        except Exception as e:
            raise self._enhance_error(e, ctx) from e

    @staticmethod
    def _escape(value: Any) -> str:
        """HTML-escape a value.

        Complexity: O(n) single-pass using str.translate().

        Optimizations:
        1. Skip Markup objects (already safe)
        2. Fast path check - if no escapable chars, return as-is
        3. Single-pass translation instead of 5 chained .replace()

        This is ~3-5x faster than the naive approach for escape-heavy content.
        """
        # Skip Markup objects - they're already safe
        # Must check before str() conversion since str(Markup) returns plain str
        if isinstance(value, Markup):
            return str(value)
        s = str(value)
        # Fast path: no escapable characters
        if not _ESCAPE_CHECK.search(s):
            return s
        return s.translate(_ESCAPE_TABLE)

    @staticmethod
    def _safe_getattr(obj: Any, name: str) -> Any:
        """Get attribute with dict fallback and None-safe handling.

        Handles both:
        - obj.attr for objects with attributes
        - dict['key'] for dict-like objects

        None Handling (like Hugo/Go templates):
        - If obj is None, returns "" (prevents crashes)
        - If attribute value is None, returns "" (normalizes output)

        Complexity: O(1)
        """
        # None access returns empty string (like Hugo)
        if obj is None:
            return ""
        try:
            val = getattr(obj, name)
            return "" if val is None else val
        except AttributeError:
            try:
                val = obj[name]
                return "" if val is None else val
            except (KeyError, TypeError):
                return ""

    def __repr__(self) -> str:
        return f"<Template {self._name or '(inline)'}>"


class RenderedTemplate:
    """Lazy rendered template (for streaming).

    Allows iteration over rendered chunks for streaming output.
    Not implemented in initial version.
    """

    __slots__ = ("_template", "_context")

    def __init__(self, template: Template, context: dict[str, Any]):
        self._template = template
        self._context = context

    def __str__(self) -> str:
        """Render and return full string."""
        return self._template.render(self._context)

    def __iter__(self):
        """Iterate over rendered chunks."""
        # For now, yield the whole thing
        yield str(self)
