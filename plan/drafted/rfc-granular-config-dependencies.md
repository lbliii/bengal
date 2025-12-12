---
Title: Granular Configuration Dependency Tracking
Author: AI Assistant
Date: 2025-12-08
Status: Draft
Confidence: 90%
Priority: P2 (Medium)
---

# RFC: Granular Configuration Dependency Tracking

**Proposal**: Implement granular dependency tracking for configuration keys to prevent unnecessary full site rebuilds when non-content settings change.

---

## 1. Problem Statement

### Current State

Currently, `DependencyTracker` tracks configuration as a **single file dependency** (`bengal.toml`).

**Evidence**:

- `bengal/cache/dependency_tracker.py:158`: `hash_file(config_path)` hashes the entire file.
- `bengal/cache/dependency_tracker.py:211`: `self.cache.add_dependency(..., config_path)` adds the whole file as a dependency.

### Pain Points

- **Over-invalidation**: Changing `cli.verbose` or `dev_server.port` changes the file hash.
- **Full Rebuilds**: Since almost every page "depends" on config (implicitly or explicitly), a change to *any* setting invalidates *all* pages.
- **Developer Experience**: Tweaking dev tools triggers 100% rebuilds, slowing down the loop.

---

## 2. Goals & Non-Goals

**Goals**:

- Track dependencies at the **key level** (e.g., `config['site']['title']`) rather than file level.
- Only invalidate pages that actually use the changed config keys.
- Maintain backward compatibility for templates accessing `site.config`.

**Non-Goals**:

- We are not changing the config file format (TOML).
- We won't track dynamic dictionary keys accessed via `__getitem__` with variable arguments (too complex).

---

## 3. Architecture Impact

**Affected Subsystems**:

- **Cache** (`bengal/cache/`): `DependencyTracker` needs to record key-level deps.
- **Core** (`bengal/core/`): `Site.config` needs to be wrapped in a proxy to intercept access.
- **Rendering** (`bengal/rendering/`): Templates accessing `config` will trigger the proxy.

---

## 4. Design Options

### Option A: Config Proxy Wrapper (Recommended)

Wrap the `config` dictionary in a `TrackingDict` proxy during rendering.

- **Description**:
  - Create a `ConfigProxy` class that inherits from `UserDict` or wraps `dict`.
  - In `__getitem__`, record the accessed key to the active `DependencyTracker`.
  - Pass this proxy to Jinja2 templates instead of the raw dict.
- **Pros**:
  - Automatic tracking: Template authors don't change anything.
  - Fine-grained: Can track nested keys (`site.title`).
- **Cons**:
  - Performance overhead for every config access (function call).
  - Complexity in handling nested dictionaries (need recursive proxies).

### Option B: Explicit Dependency Registration

Require templates/code to register config deps manually.

- **Description**: `{{ track_config('site.title') }}` in templates.
- **Pros**:
  - Zero overhead for untracked access.
  - Explicit.
- **Cons**:
  - Developer burden: Easy to forget.
  - Prone to bugs (stale dependencies).

**Recommended**: **Option A** for developer experience and correctness. The overhead of dictionary lookups is negligible compared to rendering/parsing.

---

## 5. Detailed Design (Option A)

### Config Proxy

```python
class ConfigProxy(dict):
    def __init__(self, data, tracker, prefix=""):
        super().__init__(data)
        self._tracker = tracker
        self._prefix = prefix

    def __getitem__(self, key):
        full_key = f"{self._prefix}.{key}" if self._prefix else key

        # Record dependency
        if self._tracker:
            self._tracker.track_config_key(full_key)

        value = super().__getitem__(key)

        # Return nested proxy for dicts
        if isinstance(value, dict):
            return ConfigProxy(value, self._tracker, full_key)
        return value
```

### Invalidation Logic

In `CacheInvalidator` (or `IncrementalOrchestrator`):
1. Load old config and new config.
2. Compute diff (set of changed keys).
3. `dependency_tracker.get_pages_depending_on(changed_keys)`.
4. Invalidate only those pages.

### Dependency Storage

Store dependencies as virtual paths: `config:site.title`.

---

## 6. Tradeoffs & Risks

**Tradeoffs**:

- **Granularity vs Storage**: Storing deps for every config key increases cache size.
- **Optimization**: We might only track top-level keys initially to save space.

**Risks**:

- **Missed Dependencies**: If a value is accessed via `get()` without tracking, or copied before tracking.
  - **Mitigation**: Override `get()`, `items()`, `values()`.
- **Performance**: Recursive proxy creation might add up.
  - **Mitigation**: Cache proxies or use `__getattr__` lazy wrapping.

---

## 7. Performance Impact

- **Build Time**: Slight overhead during rendering (tracking access).
- **Incremental Build**: **Massive speedup**. Changing a non-content config key (like `port`) goes from $O(N)$ rebuild to $O(0)$ rebuild.

---

## 8. Open Questions

- [ ] **Q1**: How deep do we track? (Proposal: unbounded, but practically mostly 2-3 levels).
- [ ] **Q2**: How to handle list access? (e.g., `config.menus[0]`). (Proposal: Track `config.menus` as a whole unit for lists).
