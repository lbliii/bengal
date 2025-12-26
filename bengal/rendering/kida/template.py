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


class Markup(str):
    """A string subclass that is considered safe and won't be escaped.

    This is used for macro output and the |safe filter to prevent
    double-escaping of HTML content.
    """

    def __new__(cls, value: str = "") -> Markup:
        return super().__new__(cls, value)

    def __add__(self, other: str) -> Markup:
        return Markup(super().__add__(str(other)))

    def __radd__(self, other: str) -> Markup:
        return Markup(str(other) + str(self))


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
            # Call parent's render function with blocks dict
            return parent._render_func(context, blocks)

        # Import macros from another template
        def _import_macros(template_name: str, with_context: bool, context: dict) -> dict:
            imported = env.get_template(template_name)
            # Create a context for the imported template
            import_ctx = dict(context) if with_context else {}
            # Execute the template to define macros in its context
            imported._render_func(import_ctx, None)
            # Return the context (which now contains the macros)
            return import_ctx

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
            "_Markup": Markup,
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

        # Render
        if self._render_func is None:
            raise RuntimeError("Template not properly compiled")

        return self._render_func(ctx)

    async def render_async(self, *args: Any, **kwargs: Any) -> str:
        """Render template asynchronously.

        For templates with async expressions or async for loops.

        Args:
            *args: Single dict of context variables
            **kwargs: Context variables as keyword arguments

        Returns:
            Rendered template as string
        """
        # Build context
        ctx: dict[str, Any] = {}
        ctx.update(self._env.globals)
        if args and isinstance(args[0], dict):
            ctx.update(args[0])
        ctx.update(kwargs)

        # Check for async render function
        render_async = getattr(self, "_render_async_func", None)
        if render_async is None:
            # Fall back to sync render
            return self.render(*args, **kwargs)

        return await render_async(ctx)

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
        """Get attribute with dict fallback.

        Handles both:
        - obj.attr for objects with attributes
        - dict['key'] for dict-like objects

        Complexity: O(1)
        """
        try:
            return getattr(obj, name)
        except AttributeError:
            try:
                return obj[name]
            except (KeyError, TypeError):
                return None

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
