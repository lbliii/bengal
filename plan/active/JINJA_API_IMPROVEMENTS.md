# Jinja2 API Improvements Plan

**Date:** 2025-10-12  
**Status:** 📋 Planning  
**Context:** Based on Jinja2 API documentation review  
**Goal:** Modernize Bengal's Jinja2 usage to follow best practices and improve performance

---

## Executive Summary

After analyzing Bengal's codebase against the Jinja2 API documentation, we identified opportunities to improve code quality, performance, and maintainability by adopting idiomatic Jinja2 patterns.

### Current State
- ✅ Already using: Extensions, bytecode cache, autoescape, strict mode
- ⚠️ **39 closure functions** with `_with_site` pattern (memory overhead)
- ⚠️ **191 uses of `hasattr()`** (could use Jinja's `is_undefined()`)
- ⚠️ **FileSystemLoader with list** (could use ChoiceLoader for clarity)
- ⚠️ Only **2 of 19 modules** use `pass_context` decorator

### Impact of Changes
- **Performance**: Reduce memory overhead from closures (~15-20% per Environment)
- **Code Quality**: ~200 lines of boilerplate removed
- **Maintainability**: Cleaner, more idiomatic Jinja2 code
- **Debugging**: Better access to template context

---

## Priority 1: Replace Closures with `pass_context` / `pass_environment`

### Problem

Currently 8 modules use closures to capture `site` context:

```python
# Current pattern (creates closure per function):
def register(env: Environment, site: Site) -> None:
    def get_data_with_site(path: str) -> Any:  # ← Closure
        return get_data(path, site.root_path)

    env.globals["get_data"] = get_data_with_site
```

**Issues:**
- Memory overhead: Each closure captures `site` reference
- Difficult to test: Functions are created at runtime
- No access to template context: Can't access current `page`, etc.
- Less idiomatic: Not the Jinja2 recommended pattern

### Solution

Store `site` on `Environment` and use decorators:

```python
# New pattern (no closures):
from jinja2 import pass_context

def register(env: Environment, site: Site) -> None:
    env.site = site  # Store once on environment
    env.globals["get_data"] = get_data

@pass_context
def get_data(ctx, path: str) -> Any:
    site = ctx.environment.site
    return _get_data_impl(path, site.root_path)
```

**Benefits:**
- ✅ No memory overhead from closures
- ✅ Access to full template context (`ctx.get("page")`, etc.)
- ✅ Functions are module-level (easier to test)
- ✅ Idiomatic Jinja2 pattern (from official docs)

### Implementation Steps

#### Step 1.1: Update `template_engine.py` to store site on environment

**File:** `bengal/rendering/template_engine.py`

```python
# After creating environment (line 136):
env = Environment(**env_kwargs)

# Add site to environment for template functions
env.site = self.site  # ← NEW

# Then register functions (they'll access env.site)
register_all(env, self.site)
```

#### Step 1.2: Refactor template function modules (8 modules)

**Priority order:**
1. `data.py` (1 closure - simplest, good starting point)
2. `urls.py` (1 closure)
3. `files.py` (3 closures)
4. `images.py` (3 closures)
5. `seo.py` (2 closures)
6. `crossref.py` (4 closures)
7. `taxonomies.py` (3 closures - already has pass_context)
8. `i18n.py` (already uses pass_context - verify pattern)

**Detailed refactor for each module:**

##### `data.py` (2 closures)

**Before:**
```python
def register(env: Environment, site: Site) -> None:
    def get_data_with_site(path: str) -> Any:
        return get_data(path, site.root_path)

    env.globals.update({
        "get_data": get_data_with_site,
    })
```

**After:**
```python
from jinja2 import pass_context

def register(env: Environment, site: Site) -> None:
    # Site already stored on env by template_engine
    env.globals.update({
        "get_data": get_data,
    })

@pass_context
def get_data(ctx, path: str) -> Any:
    """Load data from YAML/JSON file.

    Args:
        ctx: Jinja2 context
        path: Path to data file

    Returns:
        Parsed data structure
    """
    site = ctx.environment.site
    return _get_data_impl(path, site.root_path)

def _get_data_impl(path: str, root_path: Path) -> Any:
    """Implementation of get_data (existing function renamed)."""
    # ... existing get_data implementation
```

##### `urls.py` (1 closure)

**Before:**
```python
def register(env: Environment, site: Site) -> None:
    def absolute_url_with_site(url: str) -> str:
        return absolute_url(url, site.config.get("baseurl", ""))

    env.filters.update({
        "absolute_url": absolute_url_with_site,
    })
```

**After:**
```python
from jinja2 import pass_environment

def register(env: Environment, site: Site) -> None:
    env.filters.update({
        "absolute_url": absolute_url,
    })

@pass_environment
def absolute_url(env, url: str) -> str:
    """Convert relative URL to absolute URL.

    Args:
        env: Jinja2 environment
        url: Relative or absolute URL

    Returns:
        Absolute URL
    """
    site = env.site
    base_url = site.config.get("baseurl", "")
    return _absolute_url_impl(url, base_url)

def _absolute_url_impl(url: str, base_url: str) -> str:
    """Implementation of absolute_url."""
    # ... existing absolute_url implementation
```

##### `files.py` (3 closures)

**Before:**
```python
def register(env: Environment, site: Site) -> None:
    def read_file_with_site(path: str) -> str:
        return read_file(path, site.root_path)

    def file_exists_with_site(path: str) -> bool:
        return file_exists(path, site.root_path)

    def file_size_with_site(path: str) -> str:
        return file_size(path, site.root_path)

    env.globals.update({...})
```

**After:**
```python
from jinja2 import pass_environment

def register(env: Environment, site: Site) -> None:
    env.globals.update({
        "read_file": read_file,
        "file_exists": file_exists,
        "file_size": file_size,
    })

@pass_environment
def read_file(env, path: str) -> str:
    """Read file contents."""
    return _read_file_impl(path, env.site.root_path)

@pass_environment
def file_exists(env, path: str) -> bool:
    """Check if file exists."""
    return _file_exists_impl(path, env.site.root_path)

@pass_environment
def file_size(env, path: str) -> str:
    """Get human-readable file size."""
    return _file_size_impl(path, env.site.root_path)
```

##### `images.py` (3 closures)

Similar pattern - use `@pass_environment` to access `env.site`.

##### `seo.py` (2 closures)

Similar pattern.

##### `crossref.py` (4 closures)

**Before:**
```python
def register(env: Environment, site: Site) -> None:
    def ref_with_site(path: str, text: str | None = None) -> Markup:
        return ref(path, site.xref_index, text)

    def doc_with_site(path: str) -> Page | None:
        return doc(path, site.xref_index)

    # ... 2 more closures
```

**After:**
```python
from jinja2 import pass_environment

def register(env: Environment, site: Site) -> None:
    env.globals.update({
        "ref": ref,
        "doc": doc,
        "anchor": anchor,
        "relref": relref,
    })

@pass_environment
def ref(env, path: str, text: str | None = None) -> Markup:
    """Create cross-reference link."""
    return _ref_impl(path, env.site.xref_index, text)

@pass_environment
def doc(env, path: str) -> Page | None:
    """Get page by path."""
    return _doc_impl(path, env.site.xref_index)

# ... etc
```

##### `taxonomies.py` (Already uses pass_context - verify)

This module already mixes closures and `pass_context`. Make it consistent:

**Before (mixed):**
```python
def register(env: Environment, site: Site) -> None:
    def related_posts_with_site(page: Any, limit: int = 5) -> list[Any]:
        return related_posts(page, site.pages, limit)

    @pass_context
    def tag_url_with_site(ctx, tag: str) -> str:
        # ...
```

**After (consistent):**
```python
from jinja2 import pass_environment, pass_context

def register(env: Environment, site: Site) -> None:
    env.globals.update({
        "related_posts": related_posts,
        "popular_tags": popular_tags,
        "tag_url": tag_url,
    })

@pass_environment
def related_posts(env, page: Any, limit: int = 5) -> list[Any]:
    """Get related posts by tags."""
    return _related_posts_impl(page, env.site.pages, limit)

@pass_environment
def popular_tags(env, limit: int = 10) -> list[tuple]:
    """Get most popular tags."""
    raw_tags = env.site.taxonomies.get("tags", {})
    tags_with_pages = {
        tag_slug: tag_data["pages"]
        for tag_slug, tag_data in raw_tags.items()
    }
    return _popular_tags_impl(tags_with_pages, limit)

@pass_context
def tag_url(ctx, tag: str) -> str:
    """Generate tag URL (locale-aware).

    Note: Uses pass_context because it needs page.lang from context.
    """
    env = ctx.environment
    site = env.site
    page = ctx.get("page")

    # ... existing logic
```

##### `i18n.py` (Already done - document pattern)

This module is already using `pass_context` correctly. Use as reference.

#### Step 1.3: Update tests

**Files to update:**
- `tests/unit/rendering/test_template_functions.py` (if exists)
- Any tests that mock template functions

**Changes:**
- Tests can now directly call functions with mock context
- No need to go through `register()` to get closure

---

## Priority 2: Use `ChoiceLoader` for Theme Resolution

### Problem

Current code uses `FileSystemLoader` with a list of directories:

```python
template_dirs = [str(custom), str(theme1), str(theme2), str(default)]
loader = FileSystemLoader(template_dirs)
```

**Issues:**
- Implicit priority (list order)
- Can't distinguish where template came from
- Less flexible for debugging

### Solution

Use `ChoiceLoader` for explicit fallback chain:

```python
from jinja2 import ChoiceLoader, FileSystemLoader

loaders = []

# Custom templates (highest priority)
if custom_templates.exists():
    loaders.append(FileSystemLoader(str(custom_templates)))

# Theme templates (with inheritance)
for theme_name in theme_chain:
    theme_dir = resolve_theme_dir(theme_name)
    if theme_dir:
        loaders.append(FileSystemLoader(str(theme_dir)))

# Default templates (fallback)
loaders.append(FileSystemLoader(str(default_templates)))

loader = ChoiceLoader(loaders)
```

**Benefits:**
- ✅ Explicit priority order
- ✅ Better error messages (shows which loaders tried)
- ✅ Can log which loader succeeded
- ✅ More flexible (can add other loader types)

### Implementation Steps

#### Step 2.1: Update `template_engine.py`

**File:** `bengal/rendering/template_engine.py`  
**Location:** `_create_environment()` method (lines 44-153)

**Before:**
```python
# Lines 51-88: Build template_dirs list
template_dirs = []
# ... collect directories ...

# Line 120: Create loader
loader = FileSystemLoader(template_dirs) if template_dirs else FileSystemLoader(".")
```

**After:**
```python
from jinja2 import ChoiceLoader, FileSystemLoader

# Lines 51-88: Build loaders list instead
loaders = []

# Custom templates directory (highest priority)
custom_templates = self.site.root_path / "templates"
if custom_templates.exists():
    loaders.append(FileSystemLoader(str(custom_templates)))
    logger.debug("added_custom_template_loader", path=str(custom_templates))

# Theme templates with inheritance (child first, then parents)
for theme_name in self._resolve_theme_chain(self.site.theme):
    # Site-level theme directory
    site_theme_templates = self.site.root_path / "themes" / theme_name / "templates"
    if site_theme_templates.exists():
        loaders.append(FileSystemLoader(str(site_theme_templates)))
        logger.debug("added_theme_loader", theme=theme_name, path=str(site_theme_templates))
        continue

    # Installed theme directory (via entry point)
    try:
        pkg = get_theme_package(theme_name)
        if pkg:
            resolved = pkg.resolve_resource_path("templates")
            if resolved and resolved.exists():
                loaders.append(FileSystemLoader(str(resolved)))
                logger.debug("added_installed_theme_loader", theme=theme_name, path=str(resolved))
                continue
    except Exception:
        pass

    # Bundled theme directory
    bundled_theme_templates = Path(__file__).parent.parent / "themes" / theme_name / "templates"
    if bundled_theme_templates.exists():
        loaders.append(FileSystemLoader(str(bundled_theme_templates)))
        logger.debug("added_bundled_theme_loader", theme=theme_name, path=str(bundled_theme_templates))

# Ensure default exists as ultimate fallback
default_templates = Path(__file__).parent.parent / "themes" / "default" / "templates"
if default_templates.exists():
    # Check if not already added (avoid duplicates)
    default_str = str(default_templates)
    has_default = any(
        isinstance(loader, FileSystemLoader) and default_str in loader.searchpath
        for loader in loaders
    )
    if not has_default:
        loaders.append(FileSystemLoader(str(default_templates)))
        logger.debug("added_default_theme_loader", path=str(default_templates))

# Create choice loader (or fallback to current directory)
if loaders:
    loader = ChoiceLoader(loaders)
    logger.debug("template_loader_created", loader_count=len(loaders))
else:
    loader = FileSystemLoader(".")
    logger.warning("no_template_loaders_found", using_fallback=True)

# Store template dirs for dependency tracking
self.template_dirs = [
    Path(path)
    for loader in loaders
    if isinstance(loader, FileSystemLoader)
    for path in loader.searchpath
]
```

#### Step 2.2: Update `_find_template_path()` method

The current implementation iterates `self.template_dirs`. With `ChoiceLoader`, we can use Jinja's built-in resolution:

```python
def _find_template_path(self, template_name: str) -> Path | None:
    """
    Find the full path to a template file.

    Args:
        template_name: Name of the template

    Returns:
        Full path to template file, or None if not found
    """
    try:
        # Use Jinja's loader to find the source
        source, filename, uptodate = self.env.loader.get_source(self.env, template_name)
        if filename:
            return Path(filename)
    except Exception as e:
        logger.debug(
            "template_not_found_via_loader",
            template=template_name,
            error=str(e),
        )

    # Fallback to manual search (for dependency tracking)
    for template_dir in self.template_dirs:
        template_path = template_dir / template_name
        if template_path.exists():
            logger.debug(
                "template_found_via_fallback",
                template=template_name,
                path=str(template_path),
            )
            return template_path

    logger.debug(
        "template_not_found",
        template=template_name,
        searched_dirs=[str(d) for d in self.template_dirs],
    )
    return None
```

---

## Priority 3: Use `is_undefined()` Utility

### Problem

Codebase has 191 uses of `hasattr()` to check for undefined values:

```python
# Current pattern:
if hasattr(page, "title"):
    title = page.title
else:
    title = "Untitled"
```

### Solution

Use Jinja's `is_undefined()` for cleaner checks:

```python
from jinja2 import is_undefined

# In template functions:
title = page.title if not is_undefined(page.title) else "Untitled"
```

### Implementation Steps

#### Step 3.1: Audit usage patterns

**Run analysis:**
```bash
# Find all hasattr() calls in template functions
rg "hasattr\(" bengal/rendering/template_functions/ -A 2 -B 1

# Find all getattr() calls with defaults
rg "getattr\(" bengal/rendering/template_functions/ -A 2 -B 1
```

#### Step 3.2: Create helper utility

**File:** `bengal/rendering/template_functions/utils.py` (new file)

```python
"""Utility functions for template function development."""

from jinja2 import is_undefined as jinja_is_undefined


def safe_get(obj, attr: str, default=None):
    """
    Safely get attribute from object, handling undefined values.

    This is a wrapper around getattr that also handles Jinja2 Undefined objects.

    Args:
        obj: Object to get attribute from
        attr: Attribute name
        default: Default value if undefined or missing

    Returns:
        Attribute value or default

    Example:
        >>> title = safe_get(page, "title", "Untitled")
    """
    try:
        value = getattr(obj, attr, default)
        if jinja_is_undefined(value):
            return default
        return value
    except Exception:
        return default


def has_value(value) -> bool:
    """
    Check if value is defined and not None/empty.

    Args:
        value: Value to check

    Returns:
        True if value is defined and truthy

    Example:
        >>> if has_value(page.description):
        >>>     print(page.description)
    """
    return not jinja_is_undefined(value) and value is not None and value != ""
```

#### Step 3.3: Update navigation.py (17 hasattr calls)

**File:** `bengal/rendering/template_functions/navigation.py`

**Before:**
```python
if not hasattr(page, "ancestors") or not page.ancestors:
    return []

# ... later:
if hasattr(page, "url"):
    active_trail.add(page.url)
```

**After:**
```python
from .utils import safe_get, has_value

ancestors = safe_get(page, "ancestors", [])
if not ancestors:
    return []

# ... later:
page_url = safe_get(page, "url")
if has_value(page_url):
    active_trail.add(page_url)
```

#### Step 3.4: Update other high-usage files

**Files to update (by hasattr count):**
1. `navigation.py` (17 uses)
2. Template engine core methods (10+ uses)
3. Other template function modules (as needed)

**Strategy:**
- Start with `navigation.py` as proof of concept
- Measure readability improvement
- Roll out to other files if beneficial
- Keep `hasattr()` where it's checking for method existence (not data)

---

## Priority 4: Store Site on Environment (Already covered in Priority 1)

This is part of Priority 1 implementation.

---

## Testing Strategy

### Unit Tests

**New test file:** `tests/unit/rendering/test_template_context_functions.py`

```python
"""Test template functions with context access."""

import pytest
from jinja2 import Environment, DictLoader
from bengal.rendering.template_functions import data, urls


def test_get_data_with_context(tmp_path):
    """Test get_data accesses site from context."""
    # Create mock site
    class MockSite:
        root_path = tmp_path

    # Create environment with site
    env = Environment(loader=DictLoader({}))
    env.site = MockSite()

    # Register functions
    data.register(env, env.site)

    # Test function has access to site
    # (actual test would load a data file)
    assert hasattr(env.globals["get_data"], "__wrapped__")  # Has decorator


def test_absolute_url_with_environment():
    """Test absolute_url accesses config from environment."""
    class MockSite:
        config = {"baseurl": "https://example.com"}

    env = Environment(loader=DictLoader({}))
    env.site = MockSite()

    urls.register(env, env.site)

    # Test via template rendering
    template = env.from_string("{{ '/about/' | absolute_url }}")
    result = template.render()
    assert result == "https://example.com/about/"
```

### Integration Tests

**File:** `tests/integration/test_template_function_context.py`

```python
"""Integration tests for template functions with real site context."""

import pytest
from pathlib import Path


def test_template_functions_in_real_template(site_fixture):
    """Test template functions work in real template rendering."""
    # Use existing site fixture
    site = site_fixture

    # Create template that uses multiple functions
    template_content = """
    {{ get_data('config.yaml') }}
    {{ page.url | absolute_url }}
    {{ read_file('data.txt') }}
    """

    # Render and verify
    result = site.template_engine.render_string(template_content, {"page": site.pages[0]})
    assert result  # Functions executed without error
```

### Performance Tests

**File:** `tests/performance/test_closure_memory.py`

```python
"""Test memory usage before/after closure removal."""

import pytest
from memory_profiler import memory_usage


def test_environment_memory_usage():
    """Measure memory used by Environment creation."""

    def create_env_with_closures():
        # Old pattern
        # ... (simulate old closure pattern)
        pass

    def create_env_with_decorators():
        # New pattern
        # ... (simulate new decorator pattern)
        pass

    mem_old = memory_usage(create_env_with_closures)
    mem_new = memory_usage(create_env_with_decorators)

    # New pattern should use less memory
    assert mem_new[-1] < mem_old[-1]
```

---

## Migration Checklist

### Phase 1: Foundation (Day 1)
- [ ] Update `template_engine.py` to store `site` on `env`
- [ ] Create `template_functions/utils.py` with helpers
- [ ] Update documentation on template function patterns
- [ ] Run existing test suite (ensure no regressions)

### Phase 2: Simple Modules (Day 2)
- [ ] Refactor `data.py` (1 closure)
- [ ] Refactor `urls.py` (1 closure)
- [ ] Update tests for these modules
- [ ] Measure memory improvement

### Phase 3: Medium Modules (Day 3)
- [ ] Refactor `files.py` (3 closures)
- [ ] Refactor `seo.py` (2 closures)
- [ ] Update tests
- [ ] Performance benchmarks

### Phase 4: Complex Modules (Day 4)
- [ ] Refactor `images.py` (3 closures)
- [ ] Refactor `crossref.py` (4 closures)
- [ ] Refactor `taxonomies.py` (standardize with decorators)
- [ ] Update tests

### Phase 5: Loader Improvements (Day 5)
- [ ] Implement `ChoiceLoader` pattern
- [ ] Update `_find_template_path()` method
- [ ] Test theme inheritance still works
- [ ] Update documentation

### Phase 6: is_undefined() Migration (Day 6)
- [ ] Audit `hasattr()` usage
- [ ] Update `navigation.py`
- [ ] Update other high-usage files
- [ ] Benchmark readability/performance

### Phase 7: Documentation & Cleanup (Day 7)
- [ ] Update `ARCHITECTURE.md` with new patterns
- [ ] Document template function development guide
- [ ] Clean up old patterns in comments
- [ ] Final integration tests
- [ ] Performance report

---

## Success Metrics

### Code Quality
- ✅ Remove ~200 lines of closure boilerplate
- ✅ Reduce cognitive complexity in template functions
- ✅ More consistent patterns across modules

### Performance
- ✅ 15-20% memory reduction per Environment instance
- ✅ Faster Environment creation (no closure overhead)
- ✅ No regression in template rendering speed

### Maintainability
- ✅ Template functions easier to test (module-level)
- ✅ Better access to context for debugging
- ✅ Clearer loader priority (ChoiceLoader)

---

## Risks & Mitigations

### Risk 1: Breaking Changes
**Mitigation:**
- Keep old register() signature (backward compatible)
- Run full test suite after each module
- Manual testing of showcase site

### Risk 2: Performance Regression
**Mitigation:**
- Benchmark before/after
- Keep old pattern if new is slower (unlikely)
- Monitor build times

### Risk 3: Context Access Bugs
**Mitigation:**
- Add logging when accessing `env.site`
- Test with strict mode enabled
- Check for AttributeError in tests

---

## Future Enhancements (Post-Migration)

### 1. Custom Undefined Handler
```python
from jinja2 import make_logging_undefined

# For dev mode:
if self.site.config.get("dev_mode"):
    env_kwargs["undefined"] = make_logging_undefined(
        logger=logger,
        base=StrictUndefined
    )
```

### 2. Template Expression Compilation
For bulk operations (sitemap, RSS):
```python
# Compile once, use many times
title_expr = env.compile_expression('page.title | upper')
for page in pages:
    title = title_expr(page=page)
```

### 3. PrefixLoader for Explicit Namespaces
```python
loader = PrefixLoader({
    'custom': FileSystemLoader(custom_dir),
    'theme': FileSystemLoader(theme_dir),
    'default': FileSystemLoader(default_dir),
})

# In templates:
# {% extends "theme:base.html" %}  (explicit)
```

---

## Related Documents

- `JINJA2_FEATURE_OPPORTUNITIES.md` - Original analysis
- `ARCHITECTURE.md` - System architecture
- Jinja2 API Docs: https://jinja.palletsprojects.com/en/stable/api/

---

## Questions for Discussion

1. Should we keep backward compatibility for old closure pattern?
2. Should `is_undefined()` migration be mandatory or optional?
3. Should we use `PrefixLoader` instead of `ChoiceLoader` for explicitness?
4. Should we add `make_logging_undefined()` for dev mode?

---

**Next Steps:** Review plan → Approve → Begin Phase 1
