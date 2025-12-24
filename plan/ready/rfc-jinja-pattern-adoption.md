# RFC: Jinja Pattern Adoption for Bengal

**Status**: Implemented ✅
**Created**: 2025-12-23  
**Updated**: 2025-12-23  
**Author**: AI Assistant + Lawrence Lane  
**Priority**: P2 (Medium)  
**Related**: `bengal/rendering/`, `bengal/directives/`, `bengal/cache/`  
**Confidence**: 85% 🟢  
**Recommendation**: Implement P1-P4; defer P5-P7

---

## Executive Summary

After analyzing the Jinja2 codebase alongside Bengal, several architectural patterns emerge that Bengal can adopt to improve caching robustness, API ergonomics, and extensibility. This RFC proposes **7 adoptable patterns** across three categories:

| Category | Patterns | Impact |
|----------|----------|--------|
| **Caching & Validation** | 2 patterns | More robust cache invalidation |
| **API Ergonomics** | 3 patterns | Cleaner template function registration |
| **Extensibility** | 2 patterns | Better directive/extension ordering |

**Key Insight**: Bengal already uses Jinja2 as its template engine, making these patterns directly compatible. The adoption focuses on bringing Jinja's *internal best practices* to Bengal's own subsystems.

---

## Current State Analysis

### What Bengal Does Well (Jinja-Aligned)

| Pattern | Bengal Implementation | Status |
|---------|----------------------|--------|
| Template bytecode caching | Uses `FileSystemBytecodeCache` | ✅ Excellent |
| Loader composition | `ChoiceLoader` + `PrefixLoader` for themes | ✅ Excellent |
| LRU template cache | Default `cache_size=400` | ✅ Excellent |
| ChainableUndefined | Safe dot-notation access | ✅ Excellent |

### Gaps Identified

| Area | Current State | Jinja Pattern |
|------|---------------|---------------|
| Cache version validation | Manual cache clearing | Magic header validation |
| Template function registration | Manual `env.globals[name] = func` | `@pass_context` decorators |
| Missing value handling | `None` for missing | `missing` sentinel |
| Directive ordering | Implicit (list order) | Explicit priority system |
| Async/sync bridging | Separate implementations | `@async_variant` decorator |
| Site configuration overlays | Deep copy or recreate | Overlay pattern |

---

## Proposal 1: Magic Header Cache Validation

### Problem

Bengal's build cache (`cache.json.zst`) has no version identifier. When Bengal or Python is upgraded, stale caches can cause subtle bugs or require manual `bengal clean`:

```python
# Current: No version checking
def load(self) -> BuildCacheData:
    if self._cache_file.exists():
        data = decompress_and_load(self._cache_file)
        return BuildCacheData(**data)  # May be incompatible!
```

### Jinja's Solution

Jinja embeds a magic header with format version + Python version:

```python
# jinja2/bccache.py:33-41
bc_version = 5
bc_magic = (
    b"j2"
    + pickle.dumps(bc_version, 2)
    + pickle.dumps((sys.version_info[0] << 24) | sys.version_info[1], 2)
)
```

### Proposed Implementation

```python
# bengal/cache/version.py (NEW)
"""Cache version management with magic header validation."""

import pickle
import sys
from typing import NamedTuple

# Increment when cache format changes
CACHE_FORMAT_VERSION = 1

# Magic bytes: "bg" + format version + Python version
CACHE_MAGIC = (
    b"bg"
    + pickle.dumps(CACHE_FORMAT_VERSION, 2)
    + pickle.dumps((sys.version_info[0] << 24) | sys.version_info[1], 2)
)


class CacheVersion(NamedTuple):
    """Parsed cache version info."""
    format_version: int
    python_major: int
    python_minor: int

    @classmethod
    def current(cls) -> "CacheVersion":
        return cls(
            format_version=CACHE_FORMAT_VERSION,
            python_major=sys.version_info[0],
            python_minor=sys.version_info[1],
        )

    def is_compatible(self) -> bool:
        """Check if this version is compatible with current runtime."""
        current = self.current()
        return (
            self.format_version == current.format_version
            and self.python_major == current.python_major
            and self.python_minor == current.python_minor
        )


def validate_cache_header(data: bytes) -> tuple[bool, bytes]:
    """
    Validate cache magic header and return remaining data.

    Returns:
        Tuple of (is_valid, remaining_data)
    """
    if not data.startswith(b"bg"):
        return False, data

    if len(data) < len(CACHE_MAGIC):
        return False, data

    header = data[:len(CACHE_MAGIC)]
    if header != CACHE_MAGIC:
        return False, data

    return True, data[len(CACHE_MAGIC):]


def prepend_cache_header(data: bytes) -> bytes:
    """Prepend magic header to cache data."""
    return CACHE_MAGIC + data
```

```python
# bengal/cache/compression.py (MODIFIED)
from bengal.cache.version import validate_cache_header, prepend_cache_header

def load_compressed_cache(path: Path, logger: BengalLogger | None = None) -> dict | None:
    """Load and decompress cache with version validation."""
    if not path.exists():
        return None

    try:
        compressed = path.read_bytes()

        # Validate magic header
        is_valid, remaining = validate_cache_header(compressed)
        if not is_valid:
            if logger:
                logger.info("cache_version_mismatch", path=str(path), action="rebuilding")
            return None

        # Decompress remaining data
        decompressed = zstd.decompress(remaining)
        return json.loads(decompressed)
    except Exception as e:
        if logger:
            logger.warning("cache_load_failed", path=str(path), error=str(e))
        return None


def save_compressed_cache(path: Path, data: dict, logger: BengalLogger | None = None) -> bool:
    """Compress and save cache with version header."""
    try:
        json_bytes = json.dumps(data, separators=(",", ":")).encode()
        compressed = zstd.compress(json_bytes)

        # Prepend magic header
        versioned = prepend_cache_header(compressed)

        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(versioned)
        return True
    except Exception as e:
        if logger:
            logger.warning("cache_save_failed", path=str(path), error=str(e))
        return False
```

### Benefits

1. **Automatic invalidation**: No more "did you run `bengal clean`?" debugging
2. **Safe upgrades**: Python 3.12→3.13 or Bengal 0.2→0.3 auto-clears stale caches
3. **Clear logging**: User sees "cache_version_mismatch" instead of cryptic errors

### Migration Path

1. Add `version.py` module
2. Update `compression.py` to use headers
3. First build after upgrade auto-rebuilds (expected behavior)

---

## Proposal 2: MISSING Sentinel Pattern

### Problem

Bengal uses `None` to represent missing values, but `None` can be a valid value:

```python
# Current: Ambiguous
cache_value = cache.get("key")
if cache_value is None:
    # Is it missing, or was None the cached value?
    cache_value = compute_value()
```

### Jinja's Solution

A dedicated `missing` singleton:

```python
# jinja2/utils.py:22-30
class _MissingType:
    def __repr__(self) -> str:
        return "missing"

    def __reduce__(self) -> str:
        return "missing"

missing: t.Any = _MissingType()
```

### Proposed Implementation

```python
# bengal/utils/sentinel.py (NEW)
"""Sentinel values for unambiguous missing/undefined states."""

from typing import Any


class _MissingType:
    """Sentinel for missing values (distinct from None)."""

    __slots__ = ()
    _instance: "_MissingType | None" = None

    def __new__(cls) -> "_MissingType":
        if cls._instance is None:
            cls._instance = object.__new__(cls)
        return cls._instance

    def __repr__(self) -> str:
        return "MISSING"

    def __bool__(self) -> bool:
        return False

    def __reduce__(self) -> str:
        return "MISSING"


MISSING: Any = _MissingType()
"""Sentinel value indicating a missing/unset value (distinct from None)."""


def is_missing(value: Any) -> bool:
    """Check if a value is the MISSING sentinel."""
    return value is MISSING
```

### Usage Examples

```python
# bengal/cache/build_cache/core.py
from bengal.utils.sentinel import MISSING, is_missing

class BuildCache:
    def get_parsed_content(self, page_path: str) -> ParsedContent | _MissingType:
        """Get cached parsed content, or MISSING if not cached."""
        key = self._content_key(page_path)
        return self._parsed_content.get(key, MISSING)

    def get_or_compute(self, key: str, compute_fn: Callable[[], T]) -> T:
        """Get cached value or compute and cache it."""
        cached = self._cache.get(key, MISSING)
        if not is_missing(cached):
            return cached

        value = compute_fn()
        self._cache[key] = value
        return value
```

```python
# bengal/config/loader.py
from bengal.utils.sentinel import MISSING

def get_config_value(config: dict, key: str, default: Any = MISSING) -> Any:
    """Get config value with explicit missing detection."""
    value = config.get(key, MISSING)
    if value is MISSING:
        if default is MISSING:
            raise ConfigError(f"Required config key missing: {key}")
        return default
    return value
```

### Benefits

1. **Unambiguous**: `None` can be a valid cached/configured value
2. **Type-safe**: IDEs can distinguish `T | _MissingType` from `T | None`
3. **Picklable**: Works with cache serialization

---

## Proposal 3: Template Function Decorators

### Problem

Bengal's template function registration is verbose and repetitive:

```python
# bengal/rendering/template_functions/strings.py (CURRENT)
def truncate(text: str, length: int = 100, suffix: str = "...") -> str:
    """Truncate text to length."""
    if len(text) <= length:
        return text
    return text[:length - len(suffix)] + suffix

def register(env: Environment, site: Site) -> None:
    env.filters["truncate"] = truncate
    env.filters["slugify"] = slugify
    env.filters["titlecase"] = titlecase
    # ... 20+ more registrations
```

### Jinja's Solution

Decorators that mark functions for context injection:

```python
# jinja2/utils.py
def pass_context(f: F) -> F:
    """Pass the Context as the first argument."""
    f.jinja_pass_arg = _PassArg.context
    return f
```

### Proposed Implementation

```python
# bengal/rendering/template_functions/decorators.py (NEW)
"""Decorators for template function registration."""

from __future__ import annotations

import enum
from functools import wraps
from typing import TYPE_CHECKING, Any, Callable, TypeVar

if TYPE_CHECKING:
    from jinja2 import Environment
    from bengal.core.site import Site

F = TypeVar("F", bound=Callable[..., Any])


class _PassArg(enum.Enum):
    """What argument to pass to the function."""
    site = enum.auto()
    page = enum.auto()
    config = enum.auto()
    none = enum.auto()


class _RegisterAs(enum.Enum):
    """How to register the function."""
    filter = enum.auto()
    function = enum.auto()
    test = enum.auto()


def _get_pass_arg(func: Callable) -> _PassArg:
    """Get the pass_arg marker from a function."""
    return getattr(func, "_bengal_pass_arg", _PassArg.none)


def _get_register_as(func: Callable) -> _RegisterAs:
    """Get the register_as marker from a function."""
    return getattr(func, "_bengal_register_as", _RegisterAs.filter)


def _get_register_name(func: Callable) -> str:
    """Get the registration name (defaults to function name)."""
    return getattr(func, "_bengal_register_name", func.__name__)


# =============================================================================
# Context Injection Decorators
# =============================================================================

def pass_site(f: F) -> F:
    """Pass the Site instance as the first argument.

    Example:
        @pass_site
        def get_pages_by_section(site: Site, section: str) -> list[Page]:
            return site.pages.by_section(section)
    """
    f._bengal_pass_arg = _PassArg.site  # type: ignore
    return f


def pass_config(f: F) -> F:
    """Pass the site config dict as the first argument.

    Example:
        @pass_config
        def get_site_name(config: dict) -> str:
            return config.get("name", "Untitled Site")
    """
    f._bengal_pass_arg = _PassArg.config  # type: ignore
    return f


# =============================================================================
# Registration Type Decorators
# =============================================================================

def template_filter(name: str | None = None) -> Callable[[F], F]:
    """Mark function as a Jinja2 filter.

    Example:
        @template_filter("truncate_words")
        def truncate_by_words(text: str, count: int) -> str:
            ...
    """
    def decorator(f: F) -> F:
        f._bengal_register_as = _RegisterAs.filter  # type: ignore
        if name:
            f._bengal_register_name = name  # type: ignore
        return f
    return decorator


def template_function(name: str | None = None) -> Callable[[F], F]:
    """Mark function as a Jinja2 global function.

    Example:
        @template_function()
        @pass_site
        def get_page(site: Site, path: str) -> Page | None:
            return site.pages.get(path)
    """
    def decorator(f: F) -> F:
        f._bengal_register_as = _RegisterAs.function  # type: ignore
        if name:
            f._bengal_register_name = name  # type: ignore
        return f
    return decorator


def template_test(name: str | None = None) -> Callable[[F], F]:
    """Mark function as a Jinja2 test.

    Example:
        @template_test("draft")
        def is_draft(page: Page) -> bool:
            return page.draft
    """
    def decorator(f: F) -> F:
        f._bengal_register_as = _RegisterAs.test  # type: ignore
        if name:
            f._bengal_register_name = name  # type: ignore
        return f
    return decorator


# =============================================================================
# Registration Helper
# =============================================================================

def register_decorated_functions(
    env: Environment,
    site: Site,
    functions: list[Callable],
) -> None:
    """Register all decorated functions with the Jinja2 environment.

    Handles @pass_site, @pass_config injection and @template_filter,
    @template_function, @template_test registration.
    """
    for func in functions:
        pass_arg = _get_pass_arg(func)
        register_as = _get_register_as(func)
        name = _get_register_name(func)

        # Wrap function to inject context if needed
        if pass_arg == _PassArg.site:
            @wraps(func)
            def wrapped(*args, _site=site, _func=func, **kwargs):
                return _func(_site, *args, **kwargs)
            final_func = wrapped
        elif pass_arg == _PassArg.config:
            config = site.config
            @wraps(func)
            def wrapped(*args, _config=config, _func=func, **kwargs):
                return _func(_config, *args, **kwargs)
            final_func = wrapped
        else:
            final_func = func

        # Register with environment
        if register_as == _RegisterAs.filter:
            env.filters[name] = final_func
        elif register_as == _RegisterAs.function:
            env.globals[name] = final_func
        elif register_as == _RegisterAs.test:
            env.tests[name] = final_func
```

### Usage Example (Refactored Module)

```python
# bengal/rendering/template_functions/strings.py (REFACTORED)
"""String manipulation filters and functions."""

from bengal.rendering.template_functions.decorators import (
    template_filter,
    register_decorated_functions,
)


@template_filter()
def truncate(text: str, length: int = 100, suffix: str = "...") -> str:
    """Truncate text to specified length."""
    if len(text) <= length:
        return text
    return text[:length - len(suffix)] + suffix


@template_filter()
def slugify(text: str) -> str:
    """Convert text to URL-safe slug."""
    import re
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    return re.sub(r"[-\s]+", "-", text)


@template_filter("titlecase")
def title_case(text: str) -> str:
    """Convert text to title case."""
    return text.title()


# Collect all decorated functions
_FUNCTIONS = [truncate, slugify, title_case]


def register(env, site) -> None:
    """Register all string functions."""
    register_decorated_functions(env, site, _FUNCTIONS)
```

### Benefits

1. **Self-documenting**: Decorators show intent at definition site
2. **Less boilerplate**: No manual `env.filters[name] = func` repetition
3. **Type-safe**: IDE understands wrapped function signatures
4. **Consistent**: Same pattern as Jinja's own `@pass_context`

---

## Proposal 4: Directive Priority System

### Problem

Bengal directives process in list order, but some directives need to run before others:

```python
# bengal/directives/factory.py (CURRENT)
directives_list = [
    AdmonitionDirective(),   # Order matters but is implicit
    TabSetDirective(),
    IncludeDirective(),      # Should this run first?
    # ...
]
```

### Jinja's Solution

Extensions have explicit numeric priority:

```python
# jinja2/ext.py:84-87
class Extension:
    priority = 100  # Lower = higher priority
```

### Proposed Implementation

```python
# bengal/directives/base.py (MODIFIED)
class BengalDirective(DirectivePlugin):
    """Base class for Bengal directives."""

    # Existing class attributes
    NAMES: ClassVar[list[str]]
    TOKEN_TYPE: ClassVar[str]
    OPTIONS_CLASS: ClassVar[type[DirectiveOptions]] = DirectiveOptions
    CONTRACT: ClassVar[DirectiveContract | None] = None

    # NEW: Priority for processing order (lower = earlier)
    PRIORITY: ClassVar[int] = 100

    # Priority constants for common cases
    PRIORITY_FIRST = 0      # Preprocessing (includes, macros)
    PRIORITY_EARLY = 50     # Before most directives
    PRIORITY_NORMAL = 100   # Default
    PRIORITY_LATE = 150     # After most directives
    PRIORITY_LAST = 200     # Post-processing
```

```python
# bengal/directives/factory.py (MODIFIED)
def _get_directive_instances() -> list[BengalDirective]:
    """Get singleton directive instances sorted by priority."""
    global _DIRECTIVE_INSTANCES
    if _DIRECTIVE_INSTANCES is not None:
        return _DIRECTIVE_INSTANCES

    with _INSTANCE_LOCK:
        if _DIRECTIVE_INSTANCES is not None:
            return _DIRECTIVE_INSTANCES

        instances = [
            AdmonitionDirective(),
            TabSetDirective(),
            IncludeDirective(),
            # ... all directives
        ]

        # Sort by priority (lower = earlier)
        _DIRECTIVE_INSTANCES = sorted(instances, key=lambda d: d.PRIORITY)

        logger.debug(
            "directive_instances_initialized",
            count=len(_DIRECTIVE_INSTANCES),
            order=[f"{d.TOKEN_TYPE}:{d.PRIORITY}" for d in _DIRECTIVE_INSTANCES[:5]],
        )

        return _DIRECTIVE_INSTANCES
```

### Example Usage

```python
# bengal/directives/include.py
class IncludeDirective(BengalDirective):
    """Include external content before other processing."""

    NAMES = ["include"]
    TOKEN_TYPE = "include"
    PRIORITY = BengalDirective.PRIORITY_FIRST  # Process before others


# bengal/directives/toc.py  
class TocDirective(BengalDirective):
    """Generate TOC after headings are processed."""

    NAMES = ["toc", "table-of-contents"]
    TOKEN_TYPE = "toc"
    PRIORITY = BengalDirective.PRIORITY_LATE  # Process after content
```

### Benefits

1. **Explicit ordering**: Clear intent for directive processing order
2. **Composable**: Third-party directives can specify their priority
3. **Debuggable**: Log shows processing order

---

## Proposal 5: Environment Overlay Pattern

### Problem

Bengal's versioned documentation needs separate configurations per version, but currently requires full `Site` instances:

```python
# Current: Create entirely new Site per version
for version in versions:
    version_site = Site(
        root_path=root_path,
        config={**base_config, "version": version},
    )
    build(version_site)
```

### Jinja's Solution

`Environment.overlay()` creates a lightweight variant sharing most state:

```python
# jinja2/environment.py:387-456
def overlay(self, ...) -> "te.Self":
    """Create a new overlay environment that shares all the data with the
    current environment except for cache and the overridden attributes."""
    rv = object.__new__(self.__class__)
    rv.__dict__.update(self.__dict__)  # Share state
    rv.overlayed = True
    rv.linked_to = self
    # Only override specified attributes
    for key, value in args.items():
        if value is not missing:
            setattr(rv, key, value)
    return rv
```

### Proposed Implementation

```python
# bengal/core/site.py (MODIFIED)
class Site:
    """Site configuration and state."""

    # Track if this is an overlay
    _is_overlay: bool = False
    _overlay_parent: "Site | None" = None

    def overlay(
        self,
        *,
        version: str | None = None,
        base_url: str | None = None,
        output_dir: Path | None = None,
        config_overrides: dict | None = None,
    ) -> "Site":
        """Create a lightweight overlay with specific overrides.

        The overlay shares the parent's pages, theme, and expensive state,
        but can override version-specific settings.

        Args:
            version: Version string override
            base_url: Base URL override
            output_dir: Output directory override
            config_overrides: Additional config overrides

        Returns:
            New Site instance linked to this one

        Example:
            base_site = Site(root_path)
            v2_site = base_site.overlay(version="2.0", output_dir=Path("public/v2"))
        """
        # Create new instance without __init__
        overlay = object.__new__(Site)

        # Copy all attributes (shallow)
        overlay.__dict__.update(self.__dict__)

        # Mark as overlay
        overlay._is_overlay = True
        overlay._overlay_parent = self

        # Apply overrides
        if version is not None:
            overlay._version = version
        if base_url is not None:
            overlay._base_url = base_url
        if output_dir is not None:
            overlay._output_dir = output_dir

        # Merge config overrides
        if config_overrides:
            overlay._config = {**self._config, **config_overrides}

        # Create fresh caches for overlay-specific data
        overlay._template_engine = None  # Lazy recreate
        overlay._build_cache = None       # Separate cache per overlay

        return overlay

    @property
    def is_overlay(self) -> bool:
        """Check if this site is an overlay of another."""
        return self._is_overlay

    @property
    def root_site(self) -> "Site":
        """Get the root (non-overlay) site."""
        if self._overlay_parent is not None:
            return self._overlay_parent.root_site
        return self
```

### Usage Example

```python
# bengal/orchestration/versioned_build.py
def build_versioned_docs(site: Site, versions: list[str]) -> None:
    """Build documentation for multiple versions."""

    for version in versions:
        # Create lightweight overlay
        version_site = site.overlay(
            version=version,
            base_url=f"{site.base_url}/{version}/",
            output_dir=site.output_dir / version,
        )

        # Build shares parent's pages but uses version-specific paths
        build_site(version_site)
```

### Benefits

1. **Memory efficient**: Shares expensive state (pages, theme discovery)
2. **Fast creation**: No re-parsing or re-discovery
3. **Clear semantics**: Overlay relationship is explicit

---

## Proposal 6: Async Variant Decorator

### Problem

Some template functions could be async (e.g., remote data fetching), but Bengal currently only supports sync:

```python
# Current: Only sync
def fetch_github_stars(repo: str) -> int:
    response = requests.get(f"https://api.github.com/repos/{repo}")
    return response.json()["stargazers_count"]
```

### Jinja's Solution

`@async_variant` creates a function that works in both sync and async contexts:

```python
# jinja2/async_utils.py:15-56
def async_variant(normal_func):
    def decorator(async_func):
        @wraps(normal_func)
        def wrapper(*args, **kwargs):
            if is_async(args):
                return async_func(*args, **kwargs)
            return normal_func(*args, **kwargs)
        return wrapper
    return decorator
```

### Proposed Implementation

```python
# bengal/utils/async_bridge.py (NEW)
"""Async/sync bridging utilities."""

from __future__ import annotations

import asyncio
import inspect
from functools import wraps
from typing import Any, Awaitable, Callable, TypeVar, Union

T = TypeVar("T")


async def auto_await(value: Union[Awaitable[T], T]) -> T:
    """Await if awaitable, otherwise return directly.

    Optimized to avoid costly isawaitable check for common types.
    """
    # Fast path for common primitives
    if type(value) in {int, float, bool, str, list, dict, tuple, type(None)}:
        return value  # type: ignore

    if inspect.isawaitable(value):
        return await value  # type: ignore

    return value  # type: ignore


def async_variant(sync_func: Callable[..., T]) -> Callable[[Callable[..., Awaitable[T]]], Callable[..., Union[T, Awaitable[T]]]]:
    """Decorator to create a function with sync and async variants.

    The decorated function automatically chooses the right implementation
    based on whether it's called in an async context.

    Example:
        def fetch_sync(url: str) -> str:
            import requests
            return requests.get(url).text

        @async_variant(fetch_sync)
        async def fetch(url: str) -> str:
            import aiohttp
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    return await response.text()

        # In sync context:
        result = fetch("https://example.com")  # Uses requests

        # In async context:
        result = await fetch("https://example.com")  # Uses aiohttp
    """
    def decorator(async_func: Callable[..., Awaitable[T]]) -> Callable[..., Union[T, Awaitable[T]]]:
        @wraps(async_func)
        def wrapper(*args: Any, **kwargs: Any) -> Union[T, Awaitable[T]]:
            # Check if we're in an async context
            try:
                loop = asyncio.get_running_loop()
                is_async = True
            except RuntimeError:
                is_async = False

            if is_async:
                return async_func(*args, **kwargs)
            return sync_func(*args, **kwargs)

        wrapper._sync_variant = sync_func  # type: ignore
        wrapper._async_variant = async_func  # type: ignore
        return wrapper

    return decorator


def run_sync(func: Callable[..., Union[T, Awaitable[T]]], *args: Any, **kwargs: Any) -> T:
    """Run a potentially async function synchronously.

    If already in an async context, raises RuntimeError.
    """
    result = func(*args, **kwargs)
    if inspect.isawaitable(result):
        return asyncio.run(result)
    return result  # type: ignore
```

### Usage Example

```python
# bengal/rendering/template_functions/data.py
from bengal.utils.async_bridge import async_variant


def _fetch_json_sync(url: str) -> dict:
    """Sync implementation using requests."""
    import requests
    response = requests.get(url, timeout=10)
    response.raise_for_status()
    return response.json()


@async_variant(_fetch_json_sync)
async def fetch_json(url: str) -> dict:
    """Fetch JSON from URL (async or sync based on context)."""
    import aiohttp
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            response.raise_for_status()
            return await response.json()
```

### Benefits

1. **Gradual adoption**: Add async support without breaking sync usage
2. **Future-ready**: Prepares for async rendering pipeline
3. **Jinja-compatible**: Same pattern Jinja uses internally

---

## Proposal 7: Clear Caches Utility

### Current State

Bengal has `clear_template_cache()` and `clear_build_cache()`, but Jinja has a unified approach:

```python
# jinja2/utils.py:127-137
def clear_caches() -> None:
    """Jinja keeps internal caches for environments and lexers. These are
    used so that Jinja doesn't have to recreate environments and lexers all
    the time. Normally you don't have to care about that but if you are
    measuring memory consumption you may want to clean the caches.
    """
    from .environment import get_spontaneous_environment
    from .lexer import _lexer_cache

    get_spontaneous_environment.cache_clear()
    _lexer_cache.clear()
```

### Proposed Enhancement

```python
# bengal/cache/utils.py (ENHANCED)
from typing import Literal

CacheType = Literal["all", "build", "templates", "indexes", "output"]


def clear_caches(
    site_root_path: str | Path,
    cache_types: list[CacheType] | Literal["all"] = "all",
    logger: BengalLogger | None = None,
) -> dict[str, bool]:
    """Clear specified Bengal caches.

    Unified cache clearing with fine-grained control.

    Args:
        site_root_path: Path to site root
        cache_types: Which caches to clear ("all" or list of specific types)
        logger: Optional logger for debug output

    Returns:
        Dict mapping cache type to whether it was cleared

    Example:
        # Clear everything
        clear_caches(site.root_path)

        # Clear only template bytecode
        clear_caches(site.root_path, ["templates"])

        # Clear build cache and indexes
        clear_caches(site.root_path, ["build", "indexes"])
    """
    from bengal.cache.paths import BengalPaths

    paths = BengalPaths(Path(site_root_path))
    results: dict[str, bool] = {}

    if cache_types == "all":
        cache_types = ["build", "templates", "indexes", "output"]

    for cache_type in cache_types:
        if cache_type == "build":
            results["build"] = clear_build_cache(site_root_path, logger)
        elif cache_type == "templates":
            results["templates"] = clear_template_cache(site_root_path, logger)
        elif cache_type == "indexes":
            results["indexes"] = _clear_indexes(paths, logger)
        elif cache_type == "output":
            # Only if explicitly requested
            results["output"] = clear_output_directory(
                paths.root_path / "public", logger
            )

    if logger:
        cleared = [k for k, v in results.items() if v]
        if cleared:
            logger.info("caches_cleared", types=cleared)
        else:
            logger.debug("no_caches_to_clear")

    return results


def _clear_indexes(paths: BengalPaths, logger: BengalLogger | None) -> bool:
    """Clear query index cache."""
    import shutil

    if not paths.indexes_dir.exists():
        return False

    try:
        shutil.rmtree(paths.indexes_dir)
        if logger:
            logger.debug("indexes_cleared", dir=str(paths.indexes_dir))
        return True
    except Exception as e:
        if logger:
            logger.warning("indexes_clear_failed", error=str(e))
        return False
```

---

## Implementation Plan

### Proposal Evaluation Summary

| Proposal | Rating | Verdict | Rationale |
|----------|--------|---------|-----------|
| P1: Magic Header Cache Validation | ⭐⭐⭐⭐⭐ | **Implement** | Highest value. Eliminates "did you run `bengal clean`?" debugging. Auto-invalidation on upgrades is table-stakes. |
| P2: MISSING Sentinel | ⭐⭐⭐⭐ | **Implement** | Clean solution to `None` ambiguity. Small, isolated, no risk. |
| P3: Template Function Decorators | ⭐⭐⭐ | **Defer** | Nice ergonomics, but current manual registration isn't painful enough. Revisit when template function count grows significantly. |
| P4: Directive Priority System | ⭐⭐⭐⭐ | **Implement** | Necessary for correctness. `IncludeDirective` must run before `TocDirective`. |
| P5: Site.overlay() | ⭐⭐ | **Defer** | Premature optimization. No versioned docs use case exists yet. Memory savings only matter with 10+ overlays. |
| P6: Async Variant Decorator | ⭐⭐ | **Defer** | Bengal has no async rendering pipeline. Would be dead code. Revisit if async becomes a priority. |
| P7: Clear Caches Utility | ⭐⭐⭐ | **Defer** | Polishing only. Primitives already exist; this just unifies API. |

---

### Implementation Roadmap

#### Phase 1: Cache Robustness (1-2 days)

**Goal**: Eliminate manual cache invalidation pain.

| Task | File | Est. |
|------|------|------|
| 1.1 Create `CacheVersion` and magic header utilities | `bengal/cache/version.py` (NEW) | 1h |
| 1.2 Add `validate_cache_header()` and `prepend_cache_header()` | `bengal/cache/version.py` | 30m |
| 1.3 Integrate header validation in `load_compressed_cache()` | `bengal/cache/compression.py` | 1h |
| 1.4 Integrate header writing in `save_compressed_cache()` | `bengal/cache/compression.py` | 30m |
| 1.5 Add unit tests for version validation | `tests/unit/cache/test_version.py` | 1h |
| 1.6 Integration test: cache auto-invalidates on version bump | `tests/integration/cache/` | 1h |

**Acceptance Criteria**:
- [ ] Upgrading Python minor version auto-rebuilds cache (no errors)
- [ ] Incrementing `CACHE_FORMAT_VERSION` auto-rebuilds cache
- [ ] Log message "cache_version_mismatch" appears on invalidation

---

#### Phase 2: MISSING Sentinel (0.5 day)

**Goal**: Unambiguous missing value detection.

| Task | File | Est. |
|------|------|------|
| 2.1 Create `_MissingType` singleton and `is_missing()` | `bengal/utils/sentinel.py` (NEW) | 30m |
| 2.2 Export from `bengal.utils` | `bengal/utils/__init__.py` | 5m |
| 2.3 Unit tests for sentinel behavior | `tests/unit/utils/test_sentinel.py` | 30m |
| 2.4 Adopt in `BuildCache.get_parsed_content()` | `bengal/cache/build_cache/core.py` | 30m |
| 2.5 Adopt in config value retrieval (if applicable) | `bengal/config/loader.py` | 30m |

**Acceptance Criteria**:
- [ ] `MISSING is MISSING` (singleton)
- [ ] `bool(MISSING) == False`
- [ ] `MISSING is not None`
- [ ] At least one cache method uses `MISSING` instead of `None`

---

#### Phase 3: Directive Priority System (1 day)

**Goal**: Explicit, predictable directive processing order.

| Task | File | Est. |
|------|------|------|
| 3.1 Add `PRIORITY` class attribute to `BengalDirective` | `bengal/directives/base.py` | 15m |
| 3.2 Add priority constants (`PRIORITY_FIRST`, etc.) | `bengal/directives/base.py` | 15m |
| 3.3 Sort directives by priority in factory | `bengal/directives/factory.py` | 30m |
| 3.4 Set `PRIORITY_FIRST` on `IncludeDirective` | `bengal/directives/include.py` | 10m |
| 3.5 Set `PRIORITY_LATE` on `TocDirective` | `bengal/directives/toc.py` | 10m |
| 3.6 Log directive order at DEBUG level | `bengal/directives/factory.py` | 15m |
| 3.7 Unit test: directives sorted by priority | `tests/unit/directives/test_factory.py` | 30m |
| 3.8 Integration test: include runs before toc | `tests/integration/directives/` | 1h |

**Acceptance Criteria**:
- [ ] `IncludeDirective.PRIORITY < TocDirective.PRIORITY`
- [ ] Third-party directives can specify custom priority
- [ ] Debug log shows processing order

---

### Deferred Proposals (Future Work)

These proposals are documented but **not scheduled** until prerequisites are met:

| Proposal | Prerequisite | Trigger to Revisit |
|----------|--------------|-------------------|
| P3: Template Function Decorators | Template function count > 30 | When registration boilerplate becomes painful |
| P5: Site.overlay() | Versioned docs feature request | When multi-version builds are needed |
| P6: Async Variant Decorator | Async rendering roadmap approved | When async template rendering is prioritized |
| P7: Clear Caches Utility | User requests unified cache API | When current `clear_*` functions cause confusion |

---

### Rollout Plan

```
Week 1, Day 1-2:  Phase 1 (Cache Robustness)
Week 1, Day 3:    Phase 2 (MISSING Sentinel)
Week 1, Day 4-5:  Phase 3 (Directive Priority)
Week 2:           Monitoring & bug fixes
```

**Breaking Changes**: None. Cache will auto-rebuild on first build after upgrade (expected behavior).

**Feature Flags**: None required. All changes are internal improvements.

---

## Testing Strategy

### Unit Tests

```python
# tests/unit/utils/test_sentinel.py
def test_missing_is_singleton():
    from bengal.utils.sentinel import MISSING, _MissingType
    assert MISSING is MISSING
    assert isinstance(MISSING, _MissingType)

def test_missing_is_falsy():
    from bengal.utils.sentinel import MISSING
    assert not MISSING
    assert bool(MISSING) is False

def test_missing_distinct_from_none():
    from bengal.utils.sentinel import MISSING, is_missing
    assert MISSING is not None
    assert is_missing(MISSING)
    assert not is_missing(None)

def test_missing_repr():
    from bengal.utils.sentinel import MISSING
    assert repr(MISSING) == "MISSING"
```

```python
# tests/unit/cache/test_version.py
def test_cache_magic_header_validation():
    from bengal.cache.version import validate_cache_header, prepend_cache_header

    data = b"test data"
    versioned = prepend_cache_header(data)

    is_valid, remaining = validate_cache_header(versioned)
    assert is_valid
    assert remaining == data

def test_invalid_header_rejected():
    from bengal.cache.version import validate_cache_header

    is_valid, _ = validate_cache_header(b"invalid data")
    assert not is_valid

def test_old_version_header_rejected():
    """Simulates cache from previous Bengal version."""
    from bengal.cache.version import validate_cache_header, CACHE_MAGIC
    import pickle

    # Create header with different format version
    old_magic = b"bg" + pickle.dumps(0, 2) + pickle.dumps(0, 2)  
    old_cache = old_magic + b"stale data"

    is_valid, _ = validate_cache_header(old_cache)
    assert not is_valid
```

```python
# tests/unit/directives/test_priority.py
def test_directives_sorted_by_priority():
    from bengal.directives.factory import _get_directive_instances

    directives = _get_directive_instances()
    priorities = [d.PRIORITY for d in directives]

    assert priorities == sorted(priorities), "Directives should be sorted by priority"

def test_include_before_toc():
    from bengal.directives.include import IncludeDirective
    from bengal.directives.toc import TocDirective

    assert IncludeDirective.PRIORITY < TocDirective.PRIORITY
```

### Integration Tests

```python
# tests/integration/cache/test_version_upgrade.py
def test_cache_auto_invalidates_on_version_bump(tmp_path, monkeypatch):
    """Cache should auto-rebuild when format version changes."""
    from bengal.cache.version import CACHE_FORMAT_VERSION
    from bengal.cache.compression import save_compressed_cache, load_compressed_cache

    cache_file = tmp_path / "cache.json.zst"

    # Save cache with current version
    save_compressed_cache(cache_file, {"key": "value"})

    # Simulate version bump
    monkeypatch.setattr("bengal.cache.version.CACHE_FORMAT_VERSION", CACHE_FORMAT_VERSION + 1)

    # Load should return None (invalidated)
    result = load_compressed_cache(cache_file)
    assert result is None
```

---

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Cache header breaks existing caches | High | Low | Expected behavior; auto-rebuilds. Document in changelog. |
| Priority changes directive behavior | Medium | Medium | Keep `PRIORITY_NORMAL = 100` as default; existing directives unchanged. |
| MISSING sentinel pickle compatibility | Low | Low | Implement `__reduce__` for serialization. |

---

## Success Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| Cache version mismatches auto-handled | 100% | No manual `bengal clean` needed after Python/Bengal upgrades |
| Directive ordering bugs | 0 | No issues from processing order |
| MISSING sentinel adoption | ≥2 modules | At least cache + config use `MISSING` |
| Implementation time | ≤5 days | Track against rollout plan |

---

## Migration & Changelog Notes

### For Users

Add to `changelog.md`:

```markdown
### Changed

- **Cache auto-invalidation**: Build caches now include version headers. Upgrading Python
  or Bengal will automatically rebuild the cache on first build. No action required.

### Internal

- Added `MISSING` sentinel for unambiguous missing value detection in caches
- Directives now have explicit processing priority (no behavior change for existing sites)
```

### For Plugin Authors

If you've created custom directives, you can now control processing order:

```python
from bengal.directives.base import BengalDirective

class MyPreprocessorDirective(BengalDirective):
    NAMES = ["preprocess"]
    TOKEN_TYPE = "preprocess"
    PRIORITY = BengalDirective.PRIORITY_FIRST  # Runs before other directives

class MyPostprocessorDirective(BengalDirective):
    NAMES = ["postprocess"]
    TOKEN_TYPE = "postprocess"  
    PRIORITY = BengalDirective.PRIORITY_LAST  # Runs after other directives
```

Directives without explicit `PRIORITY` default to `PRIORITY_NORMAL = 100`.

---

## Appendix: Jinja Source References

| Pattern | Jinja File | Lines |
|---------|------------|-------|
| Magic header | `bccache.py` | 33-41 |
| Missing sentinel | `utils.py` | 22-30 |
| Pass context decorators | `utils.py` | 38-82 |
| Extension priority | `ext.py` | 84-87 |
| Environment overlay | `environment.py` | 387-456 |
| Async variant | `async_utils.py` | 15-56 |
| Clear caches | `utils.py` | 127-137 |

---

## Related Documents

- RFC: Directive Processing & Template Rendering Optimization
- RFC: Mistune Pattern Adoption for Bengal
- RFC: Free-Threading Expansion
- Jinja2 Documentation: https://jinja.palletsprojects.com/
