# RFC: Zensical-Inspired Build & Cache Patterns (Rev 2)

**Status**: Implemented
**Created**: 2025-12-02
**Last Updated**: 2025-12-02
**Author**: AI Assistant
**Priority**: High
**Confidence**: 95% 🟢
**Est. Impact**: Robust correctness for incremental builds, zero-config cache invalidation

---

## Executive Summary

This RFC proposes adopting **Global Config Hashing** to ensure build correctness when configuration changes.

Analysis of the current codebase reveals that **Content-Hash Caching** is largely *already implemented* in `BuildCache` (using SHA256), contrary to initial assumptions. However, **Config Invalidation** remains brittle, relying on manual file tracking that misses environment variables, build profiles, and split config files.

We will focus on implementing a **Config-Hash** strategy that invalidates the cache whenever the *effective* configuration state changes, ensuring reliable incremental builds.

---

## Problem Statement

### Current State Analysis

1.  **Content Hashing Exists**: `bengal/cache/build_cache.py` already implements `hash_file()` using SHA256 and stores `file_hashes`. `PageCore` also includes a `file_hash` field.
    *   *Correction*: The system does *not* rely solely on mtime for validity, but `DependencyTracker` logic for *what* to check could be optimized.

2.  **Config Tracking is Brittle**: The current system tracks `bengal.toml` as a file dependency.
    *   **Issue 1**: Ignores `config/` directory structure (split configs).
    *   **Issue 2**: Ignores environment variable overrides (`BENGAL_ENV`).
    *   **Issue 3**: Ignores build profiles (e.g., `--profile writer`).
    *   **Result**: Changing a value in `config/environments/local.yaml` or setting an env var does *not* trigger a rebuild if the main `bengal.toml` file is untouched.

### Pain Points

1.  **Stale Builds on Config Change**: Developers must manually run `bengal site clean` when changing configuration settings that aren't in the main file.
2.  **CI/CD Unreliability**: Builds using different profiles (e.g., staging vs prod) might reuse a cache generated for the wrong profile if the cache key doesn't account for the full config state.

---

## Goals

1.  **G1: Global Config Hashing**: Compute a deterministic hash of the *final, resolved* configuration dictionary (including env vars and profiles).
2.  **G2: Auto-Invalidation**: Automatically invalidate the entire `BuildCache` if the config hash changes.
3.  **G3: Verify Content Hash Usage**: Ensure `PageCore.file_hash` is effectively utilized for all asset types.

---

## Design Proposal: Config-Hash Invalidation

### 1. Compute Effective Config Hash

We will move away from tracking config *files* and instead track the config *state*.

**Module**: `bengal/config/loader.py`

```python
def compute_config_hash(config: dict[str, Any]) -> str:
    """
    Compute deterministic hash of the resolved configuration.

    Handles:
    - Recursive sorting of keys
    - Serialization of non-JSON types (Path objects, etc.)
    - Exclusion of runtime-only volatile keys (if any)
    """
    # Implementation details in "Detailed Design" below
```

### 2. Store & Validate in BuildCache

**Module**: `bengal/cache/build_cache.py`

```python
@dataclass
class BuildCache:
    # ... existing fields ...
    config_hash: str | None = None

    def validate_config(self, current_hash: str) -> bool:
        """
        Check if cache is valid for the current configuration.
        Returns True if valid, False if cache should be cleared.
        """
        if self.config_hash != current_hash:
            logger.info(f"Config changed ({self.config_hash[:8]} -> {current_hash[:8]}). Invalidating cache.")
            self.clear()
            self.config_hash = current_hash
            return False
        return True
```

### 3. Integration in Site

**Module**: `bengal/core/site.py`

```python
class Site:
    def __init__(self, ...):
        # ...
        self.config_hash = compute_config_hash(self.config)

    def build(self, ...):
        # Pass config_hash to orchestrator/cache
```

---

## Detailed Design

### Hashing Algorithm

The hash function must be robust against dictionary ordering and non-standard types.

```python
# bengal/config/hash.py (New Utility)

import hashlib
import json
from pathlib import Path
from typing import Any

def _json_default(obj: Any) -> str:
    """Handle non-JSON types for hashing."""
    if isinstance(obj, Path):
        return str(obj.as_posix())
    if isinstance(obj, set):
        return str(sorted(list(obj)))
    return str(obj)

def compute_config_hash(config: dict[str, Any]) -> str:
    """
    Compute SHA-256 hash of configuration state.
    """
    # 1. Sort keys for determinism
    # 2. Use custom serializer for Paths/Sets
    serialized = json.dumps(
        config,
        sort_keys=True,
        default=_json_default,
        ensure_ascii=True
    )
    return hashlib.sha256(serialized.encode('utf-8')).hexdigest()[:16]
```

---

## Implementation Plan

### Phase 1: Config Hashing (Day 1)
1.  Create `bengal/config/hash.py`.
2.  Update `ConfigLoader` to use this utility.
3.  Add unit tests ensuring:
    *   Same config = same hash.
    *   Different env vars = different hash.
    *   Different key order = same hash.

### Phase 2: Cache Integration (Day 1)
1.  Modify `BuildCache` to accept `current_config_hash` in `load()` or `__init__`.
2.  Implement the invalidation logic (clear cache if hash mismatch).
3.  Update `BuildCache` serialization to save the `config_hash`.

### Phase 3: Site & Orchestration (Day 2)
1.  Update `Site` to compute hash on init.
2.  Pass hash to `BuildOrchestrator`.
3.  Verify in integration tests that changing a config value triggers a full rebuild.

---

## Tradeoffs & Risks

| Tradeoff | Impact | Mitigation |
| :--- | :--- | :--- |
| **Full Rebuilds** | Changing *any* config triggers full rebuild. | Acceptable for correctness. Most config changes affect global state (templates, baseurl). |
| **Hash Overhead** | Tiny penalty at startup. | Negligible (< 2ms) compared to build time. |
| **Volatile Configs** | If config contains timestamps/random values, cache thrashes. | Ensure `config` object only contains stable build configuration. |

---

## Future Considerations (Deferred)

*   **Reactive Dataflow**: While interesting, the immediate need is correctness. We will defer the "Zensical-style" reactive pipeline until the config-hash foundation is stable.
*   **Granular Invalidation**: Later, we could hash specific sections (e.g., `[markdown]`) and only invalidate relevant parts of the cache (e.g., `parsed_content`), but this adds significant complexity for marginal gain on small sites.

---

## Approval

- [x] RFC Reviewed
- [x] Implementation Plan Approved
- [x] Implementation Complete (2025-12-02)
