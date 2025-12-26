"""Kida Template — compiled template object ready for rendering.

The Template class wraps a compiled code object and provides the `render()`
API. Templates are immutable and thread-safe for concurrent rendering.

Architecture:
    ```
    Template
    ├── _env_ref: WeakRef[Environment]  # Prevents circular refs
    ├── _code: code object              # Compiled Python bytecode
    ├── _render_func: callable          # Extracted render() function
    └── _name, _filename                # For error messages
    ```

StringBuilder Pattern:
    Generated code uses `buf.append()` + `''.join(buf)`:
    ```python
    def render(ctx, _blocks=None):
        buf = []
        _append = buf.append
        _append("Hello, ")
        _append(_e(_s(ctx["name"])))
        return ''.join(buf)
    ```
    This is O(n) vs O(n²) for string concatenation.

Memory Safety:
    Uses `weakref.ref(env)` to break potential cycles:
    `Template → (weak) → Environment → cache → Template`

Thread-Safety:
    - Templates are immutable after construction
    - `render()` creates only local state (buf list)
    - Multiple threads can call `render()` concurrently

Complexity:
    - `render()`: O(n) where n = output size
    - `_escape()`: O(n) single-pass via `str.translate()`
"""

from __future__ import annotations

import re
import weakref
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

# Spaceless: regex to remove whitespace between HTML tags
# RFC: kida-modern-syntax-features
_SPACELESS_RE = re.compile(r">\s+<")


class LoopContext:
    """Loop iteration metadata accessible as `loop` inside `{% for %}` blocks.

    Provides index tracking, boundary detection, and utility methods for
    common iteration patterns. All properties are computed on-access.

    Properties:
        index: 1-based iteration count (1, 2, 3, ...)
        index0: 0-based iteration count (0, 1, 2, ...)
        first: True on the first iteration
        last: True on the final iteration
        length: Total number of items in the sequence
        revindex: Reverse 1-based index (counts down to 1)
        revindex0: Reverse 0-based index (counts down to 0)
        previtem: Previous item in sequence (None on first)
        nextitem: Next item in sequence (None on last)

    Methods:
        cycle(*values): Return values[index % len(values)]

    Example:
        ```jinja
        <ul>
        {% for item in items %}
            <li class="{{ loop.cycle('odd', 'even') }}">
                {{ loop.index }}/{{ loop.length }}: {{ item }}
                {% if loop.first %}← First{% endif %}
                {% if loop.last %}← Last{% endif %}
            </li>
        {% end %}
        </ul>
        ```

    Output:
        ```html
        <ul>
            <li class="odd">1/3: Apple ← First</li>
            <li class="even">2/3: Banana</li>
            <li class="odd">3/3: Cherry ← Last</li>
        </ul>
        ```
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

    Wraps a compiled code object containing a `render(ctx, _blocks)` function.
    Templates are immutable and thread-safe for concurrent `render()` calls.

    Thread-Safety:
        - Template object is immutable after construction
        - Each `render()` call creates local state only (buf list)
        - Multiple threads can render the same template simultaneously

    Memory Safety:
        Uses `weakref.ref(env)` to prevent circular reference leaks:
        `Template → (weak) → Environment → _cache → Template`

    Attributes:
        name: Template identifier (for error messages)
        filename: Source file path (for error messages)

    Methods:
        render(**context): Render template with given variables
        render_async(**context): Async render for templates with await

    Error Enhancement:
        Runtime errors are caught and enhanced with template context:
        ```
        TemplateRuntimeError: 'NoneType' has no attribute 'title'
          Location: article.html:15
          Expression: {{ post.title }}
          Values:
            post = None (NoneType)
          Suggestion: Check if 'post' is defined before accessing .title
        ```

    Example:
        >>> from bengal.rendering.kida import Environment
        >>> env = Environment()
        >>> t = env.from_string("Hello, {{ name | upper }}!")
        >>> t.render(name="World")
        'Hello, WORLD!'

        >>> t.render({"name": "World"})  # Dict context also works
        'Hello, WORLD!'
    """

    __slots__ = ("_env_ref", "_code", "_name", "_filename", "_render_func")

    def __init__(
        self,
        env: Environment,
        code: Any,  # Compiled code object
        name: str | None,
        filename: str | None,
    ):
        """Initialize template with compiled code.

        Args:
            env: Parent Environment (stored as weak reference)
            code: Compiled Python code object
            name: Template name (for error messages)
            filename: Source filename (for error messages)
        """
        # Use weakref to prevent circular reference: Template <-> Environment
        self._env_ref: weakref.ref[Environment] = weakref.ref(env)
        self._code = code
        self._name = name
        self._filename = filename

        # Capture env reference for closures (will be dereferenced at call time)
        env_ref = self._env_ref

        # Include helper - loads and renders included template
        def _include(
            template_name: str,
            context: dict,
            ignore_missing: bool = False,
            *,  # Force remaining args to be keyword-only
            blocks: dict | None = None,  # RFC: kida-modern-syntax-features (embed)
        ) -> str:
            _env = env_ref()
            if _env is None:
                raise RuntimeError("Environment has been garbage collected")
            try:
                included = _env.get_template(template_name)
                # If blocks are provided (for embed), call the render function directly
                # with blocks parameter
                if blocks is not None and included._render_func is not None:
                    return included._render_func(context, blocks)
                return included.render(**context)
            except Exception:
                if ignore_missing:
                    return ""
                raise

        # Extends helper - renders parent template with child's blocks
        def _extends(template_name: str, context: dict, blocks: dict) -> str:
            _env = env_ref()
            if _env is None:
                raise RuntimeError("Environment has been garbage collected")
            parent = _env.get_template(template_name)
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
            _env = env_ref()
            if _env is None:
                raise RuntimeError("Environment has been garbage collected")
            imported = _env.get_template(template_name)
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
            import_ctx = dict(_env.globals)
            if with_context:
                import_ctx.update(context)
            # Execute the template to define macros in its context
            imported._render_func(import_ctx, None)
            # Return the context (which now contains the macros)
            return import_ctx

        # Cache helpers - use environment's LRU cache
        def _cache_get(key: str) -> str | None:
            """Get cached fragment by key (with TTL support)."""
            _env = env_ref()
            if _env is None:
                return None
            return _env._fragment_cache.get(key)

        def _cache_set(key: str, value: str, ttl: str | None = None) -> None:
            """Set cached fragment (TTL is configured at Environment level)."""
            _env = env_ref()
            if _env is None:
                return
            # Note: Per-key TTL would require a more sophisticated cache.
            # Currently uses environment-level TTL for all fragments.
            _env._fragment_cache.set(key, value)

        # Strict mode variable lookup helper
        def _lookup(ctx: dict, var_name: str) -> Any:
            """Look up a variable in strict mode.

            In strict mode, undefined variables raise UndefinedError instead
            of silently returning None. This catches typos and missing variables
            early, improving debugging experience.

            Performance:
                - Fast path (defined var): O(1) dict lookup
                - Error path: Raises UndefinedError with template context
            """
            from bengal.rendering.kida.environment.exceptions import UndefinedError

            try:
                return ctx[var_name]
            except KeyError:
                # Get template context for better error messages
                template_name = ctx.get("_template")
                lineno = ctx.get("_line")
                raise UndefinedError(var_name, template_name, lineno)

        # Default filter helper for strict mode
        def _default_safe(
            value_fn: Any,
            default_value: Any = "",
            boolean: bool = False,
        ) -> Any:
            """Safe default filter that works with strict mode.

            In strict mode, the value expression might raise UndefinedError.
            This helper catches that and returns the default value.

            Args:
                value_fn: A lambda that evaluates the value expression
                default_value: The fallback value if undefined or None/falsy
                boolean: If True, check for falsy values; if False, check for None only

            Returns:
                The value if defined and valid, otherwise the default
            """
            from bengal.rendering.kida.environment.exceptions import UndefinedError

            try:
                value = value_fn()
            except UndefinedError:
                return default_value

            # Apply default filter logic
            if boolean:
                # Return default if value is falsy
                return value if value else default_value
            else:
                # Return default only if value is None
                return value if value is not None else default_value

        # Is defined test helper for strict mode
        def _is_defined(value_fn: Any) -> bool:
            """Check if a value is defined in strict mode.

            In strict mode, we need to catch UndefinedError to determine
            if a variable is defined.

            Args:
                value_fn: A lambda that evaluates the value expression

            Returns:
                True if the value is defined (doesn't raise UndefinedError
                and is not None), False otherwise
            """
            from bengal.rendering.kida.environment.exceptions import UndefinedError

            try:
                value = value_fn()
                return value is not None
            except UndefinedError:
                return False

        # Spaceless helper - removes whitespace between HTML tags
        # RFC: kida-modern-syntax-features
        def _spaceless(html: str) -> str:
            """Remove whitespace between HTML tags.

            Example:
                {% spaceless %}
                <ul>
                    <li>a</li>
                </ul>
                {% end %}
                Output: <ul><li>a</li></ul>
            """
            return _SPACELESS_RE.sub("><", html).strip()

        # Numeric coercion helper for arithmetic operations
        def _coerce_numeric(value: Any) -> int | float:
            """Coerce value to numeric type for arithmetic operations.

            Handles Markup objects (from macros) and strings that represent numbers.
            This prevents string multiplication when doing arithmetic with macro results.

            Example:
                macro returns Markup('  24  ')
                _coerce_numeric(Markup('  24  ')) -> 24

            Args:
                value: Any value, typically Markup from macro or filter result

            Returns:
                int if value parses as integer, float if decimal, 0 for non-numeric
            """
            # Fast path: already numeric (but not bool, which is a subclass of int)
            if isinstance(value, (int, float)) and not isinstance(value, bool):
                return value

            # Convert to string and strip whitespace
            s = str(value).strip()

            # Try int first (more common), then float
            try:
                return int(s)
            except ValueError:
                try:
                    return float(s)
                except ValueError:
                    # Non-numeric string defaults to 0
                    return 0

        # Str helper that converts None to empty string for template output
        # RFC: kida-modern-syntax-features - needed for optional chaining
        def _str_safe(value: Any) -> str:
            """Convert value to string, treating None as empty string.

            This is used for template output so that optional chaining
            expressions that evaluate to None produce empty output rather
            than the literal string 'None'.
            """
            if value is None:
                return ""
            return str(value)

        # Execute the code to get the render function
        namespace: dict[str, Any] = {
            "__builtins__": {},
            "_env": env,  # Direct ref needed during exec for globals access
            "_filters": env._filters,
            "_tests": env._tests,
            "_escape": self._escape,
            "_getattr": self._safe_getattr,
            "_getattr_none": self._getattr_preserve_none,  # RFC: kida-modern-syntax-features
            "_lookup": _lookup,  # Strict mode variable lookup
            "_default_safe": _default_safe,  # Default filter for strict mode
            "_is_defined": _is_defined,  # Is defined test for strict mode
            "_coerce_numeric": _coerce_numeric,  # Numeric coercion for macro arithmetic
            "_spaceless": _spaceless,  # RFC: kida-modern-syntax-features
            "_str_safe": _str_safe,  # RFC: kida-modern-syntax-features - None to empty string
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
    def _env(self) -> Environment:
        """Get the Environment (dereferences weak reference)."""
        env = self._env_ref()
        if env is None:
            raise RuntimeError("Environment has been garbage collected")
        return env

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
            # Check if this is an UndefinedError (from strict mode)
            # These are already well-formatted, so don't wrap them
            from bengal.rendering.kida.environment.exceptions import UndefinedError

            if isinstance(e, UndefinedError):
                raise
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
            # Check if this is an UndefinedError (from strict mode)
            from bengal.rendering.kida.environment.exceptions import UndefinedError

            if isinstance(e, UndefinedError):
                raise
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

    @staticmethod
    def _getattr_preserve_none(obj: Any, name: str) -> Any:
        """Get attribute with dict fallback, preserving None values.

        Like _safe_getattr but preserves None values instead of converting
        to empty string. Used for optional chaining (?.) so that null
        coalescing (??) can work correctly.

        Part of RFC: kida-modern-syntax-features

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
