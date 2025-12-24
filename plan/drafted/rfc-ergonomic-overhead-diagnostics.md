# RFC: Ergonomic Overhead Diagnostics

**Status**: Draft  
**Created**: 2025-01-23  
**Author**: AI Assistant  
**Related**: rfc-docs-nav-rendering-optimization.md

## Summary

This RFC documents patterns for identifying and fixing "ergonomic overhead" - performance costs hidden in convenience abstractions like context wrappers, proxies, and smart accessors. These issues are hard to find because the code looks clean and the overhead is distributed across many small allocations.

## Problem Statement

Bengal uses many ergonomic abstractions to make template development pleasant:

```python
# Templates can write this...
{{ site.params.repo_url }}
{{ theme.config.hero_style }}
{{ section.params.author }}

# ...instead of this
{{ site.config.get('params', {}).get('repo_url', '') }}
```

These abstractions have hidden costs:

1. **Object allocation per access** - Creating wrapper objects on every property access
2. **Object allocation per page** - Creating context objects for every page render
3. **Repeated computation** - Re-computing the same values without caching

For a 1000-page site, these small costs compound:
- 4 context wrappers × 1000 pages = 4000 allocations
- `site.params` accessed 5× per page × 1000 pages = 5000 `ParamsContext` objects
- Nav node wrappers × 50 nodes × 1000 pages = 50,000 proxy objects

## Anti-Patterns to Watch For

### 1. Properties That Create Objects

**Anti-pattern:**
```python
@property
def params(self) -> ParamsContext:
    return ParamsContext(self._data.get("params", {}))  # New object every access!
```

**Fix:**
```python
@property
def params(self) -> ParamsContext:
    if self._params_cache is None:
        self._params_cache = ParamsContext(self._data.get("params", {}))
    return self._params_cache
```

**Detection:** Search for `return [A-Z][a-zA-Z]+\(` inside `@property` decorated methods.

### 2. Per-Page Context Creation

**Anti-pattern:**
```python
def build_page_context(page, site):
    return {
        "site": SiteContext(site),      # New per page!
        "config": ConfigContext(config), # New per page!
        "theme": ThemeContext(theme),    # New per page!
    }
```

**Fix:**
```python
_global_context_cache: dict[int, dict] = {}

def _get_global_contexts(site):
    site_id = id(site)
    if site_id not in _global_context_cache:
        _global_context_cache[site_id] = {
            "site": SiteContext(site),
            "config": ConfigContext(site.config),
            "theme": ThemeContext(site.theme_config),
        }
    return _global_context_cache[site_id]
```

**Detection:** Look at functions called per-page (render loops) and check for constructor calls inside.

### 3. Uncached `.get()` Methods

**Anti-pattern:**
```python
def get(self, key, default=""):
    value = self._data.get(key)
    if isinstance(value, dict):
        return ParamsContext(value)  # New object, not cached!
    return value
```

**Fix:**
```python
def get(self, key, default=""):
    value = self._data.get(key)
    if isinstance(value, dict):
        if key not in self._cache:
            self._cache[key] = ParamsContext(value)
        return self._cache[key]
    return value
```

**Detection:** Compare `__getattr__` and `get()` implementations - they should use the same caching.

### 4. Proxy Objects in Loops

**Anti-pattern:**
```python
def get_children(self):
    return [NavNodeProxy(child, self.page) for child in self._node.children]
    # Creates new proxies EVERY time get_children is called!
```

**Fix:**
```python
def get_children(self):
    if self._children_cache is None:
        self._children_cache = [NavNodeProxy(child, self.page) for child in self._node.children]
    return self._children_cache
```

**Detection:** Search for list comprehensions that create class instances: `\[.*[A-Z][a-zA-Z]+\(.*for.*in.*\]`

### 5. `.to_dict()` in Hot Paths

**Anti-pattern:**
```python
def get_menu(self, name):
    menu = self._site.menu.get(name, [])
    return [item.to_dict() for item in menu]  # Creates new dicts every call!
```

**Fix:**
```python
def get_menu(self, name):
    if name not in self._menu_cache:
        menu = self._site.menu.get(name, [])
        self._menu_cache[name] = [item.to_dict() for item in menu]
    return self._menu_cache[name]
```

**Detection:** Search for `\.to_dict\(\)` in list comprehensions.

### 6. String Operations in Properties

**Anti-pattern:**
```python
@property
def href(self):
    return f"{self.baseurl}/{self.path}".rstrip("/") + "/"  # String ops every access
```

**Fix:**
```python
@cached_property
def href(self):
    return f"{self.baseurl}/{self.path}".rstrip("/") + "/"
```

**Detection:** Look for `@property` that could be `@cached_property`.

## Diagnostic Techniques

### 1. Instantiation Frequency Analysis

Ask: "How many times is this constructor called per build?"

| Frequency | Risk Level | Example |
|-----------|------------|---------|
| Once per build | ✅ Safe | `Site()`, `Theme()` |
| Once per section | ⚠️ Watch | `SectionContext()` |
| Once per page | 🔴 High | `SiteContext()`, `ParamsContext()` |
| Multiple per page | 🔴 Critical | `NavNodeProxy()` per nav item |

### 2. Template Access Pattern Analysis

Trace what happens when a template accesses a value:

```jinja
{{ site.params.social.twitter }}
```

Trace:
1. `site` → Lookup `SiteContext` (cached? ✅)
2. `.params` → Create `ParamsContext`? (cached? ❓)
3. `.social` → Create nested `ParamsContext`? (cached? ❓)
4. `.twitter` → Return value

Each `❓` is a potential allocation that happens on EVERY page.

### 3. grep Patterns for Detection

```bash
# Properties that return new objects
grep -rn "return [A-Z][a-zA-Z]*\(" --include="*.py" | grep -E "@property" -A5

# List comprehensions with constructors
grep -rn "\[.*[A-Z][a-zA-Z]*\(.*for.*in" --include="*.py"

# .to_dict() in list comprehensions
grep -rn "\.to_dict().*for.*in\|for.*in.*\.to_dict()" --include="*.py"

# Per-page function calls (look for what's inside)
grep -rn "for page in\|for p in pages" --include="*.py" -A10

# __slots__ without cache fields (might need caching)
grep -rn "__slots__.*=.*\(" --include="*.py" -B5 -A10
```

### 4. Profiling Template Time

```bash
bengal build site/ --profile-templates
```

Look for:
- High average time per render (>50ms suggests overhead)
- Templates that should be fast but aren't
- Total template time vs total build time ratio

### 5. Memory Profiling (Advanced)

```python
# Add to hot path for counting allocations
import sys

_allocation_counts = {}

def track_allocation(cls):
    name = cls.__name__
    _allocation_counts[name] = _allocation_counts.get(name, 0) + 1
    return cls

# Use: track_allocation(ParamsContext)(data)
```

## Code Review Checklist

When reviewing code that adds ergonomic abstractions:

### Constructor Calls
- [ ] Is this constructor called in a per-page hot path?
- [ ] Could the result be cached and reused?
- [ ] Is there already a cache that should be used?

### Properties
- [ ] Does this `@property` create any objects?
- [ ] Should it be `@cached_property` instead?
- [ ] If it wraps nested data, does it cache the wrappers?

### Context Objects
- [ ] Are global contexts (site, theme, config) created once or per-page?
- [ ] Do context properties cache their nested wrappers?
- [ ] Do both `__getattr__` and `get()` use the same cache?

### Template Functions
- [ ] Does this function create objects per call?
- [ ] Is there an opportunity for memoization?
- [ ] Could results be cached by (page, key) or similar?

### Proxy/Wrapper Classes
- [ ] How many instances are created per page?
- [ ] Are child collections cached after first access?
- [ ] Is there a shared cache that could be used?

## Implementation Priority

When fixing ergonomic overhead:

1. **Highest Impact**: Per-page context wrappers (affects every page)
2. **High Impact**: Nested property wrappers (compounds with nesting depth)
3. **Medium Impact**: List comprehension allocations (scales with list size)
4. **Lower Impact**: One-off allocations in rarely-called code

## Case Study: NavNodeProxy

### Problem
Navigation rendering created `NavNodeProxy` objects for every node on every page:
- 50 nav nodes × 1000 pages = 50,000 proxy objects per build
- Each proxy wrapped the same underlying `NavNode`

### Detection
- Template profiling showed `doc/single.html` taking 100ms+ per page
- Code review found `NavNodeProxy` created in property without caching
- grep found: `return NavNodeProxy(` inside frequently-called method

### Fix
- Added `_proxy_cache` dictionary keyed by `(node_id, page_id)`
- Proxy objects now reused when same node accessed for same page
- Result: Template time dropped from 100ms to 15ms per page

## Related Patterns in Other Systems

| System | Pattern | Bengal Equivalent |
|--------|---------|-------------------|
| React | `useMemo` for expensive computations | `@cached_property` |
| Django | `@cached_property` on models | Same pattern |
| SQLAlchemy | `lazy="joined"` to prevent N+1 | Pre-compute nav trees |
| Vue | Computed properties with caching | Context wrapper caching |

## Success Metrics

After applying optimizations:
- Template render time per page: <20ms (was 100ms+)
- Total build time for 1000 pages: <60s
- Object allocations per page: <100 (was 500+)

## Conclusion

Ergonomic overhead is insidious because:
1. The code looks clean and correct
2. Each individual allocation is tiny
3. The cost only appears at scale

The key questions to ask:
- **"How often?"** - Is this per-build, per-page, or per-access?
- **"Can we cache?"** - Is the result stable enough to reuse?
- **"Who else?"** - If one wrapper needs caching, do similar ones too?

By systematically applying these patterns, Bengal can maintain its ergonomic API while avoiding the hidden performance costs.
