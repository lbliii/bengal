# RFC: Utility Consolidation

**Status**: Draft  
**Created**: 2025-12-08  
**Author**: AI Assistant  
**Priority**: P2 (Medium)  
**Subsystems**: utils, rendering, config, discovery, cli

---

## Summary

Consolidate 6 patterns of duplicate/similar functionality into shared utilities to reduce maintenance burden, improve testability, and establish single sources of truth.

---

## Problem Statement

Analysis of the Bengal codebase revealed duplicate implementations of common operations:

| Pattern | Locations | Impact |
|---------|-----------|--------|
| File hashing | 3 implementations | Inconsistent APIs, redundant code |
| Title humanization | 13+ locations | Copy-paste code, no central tests |
| URL generation | 3 implementations | Near-identical code, maintenance burden |
| Frontmatter parsing | 2 implementations | Different error handling |
| Deep merge | 2 implementations | Identical logic duplicated |

**Total duplicate code**: ~150-200 lines across 25+ locations.

---

## Goals

1. **Single source of truth** for each utility pattern
2. **Consistent behavior** across all usages
3. **Centralized testing** for utility functions
4. **Reduced maintenance** when behavior needs to change

## Non-Goals

- Changing external APIs or behavior
- Breaking existing functionality
- Over-abstracting simple patterns

---

## Design

### Phase 1: Title Humanization (HIGH PRIORITY)

**Current state**: Pattern `.replace("-", " ").replace("_", " ").title()` in 13+ locations.

**Proposed utility** in `bengal/utils/text.py`:

```python
def humanize_slug(slug: str) -> str:
    """
    Convert slug or filename stem to human-readable title.

    Transforms kebab-case and snake_case identifiers into
    Title Case strings suitable for display.

    Args:
        slug: Slug or filename stem (e.g., "my-page-name", "data_model")

    Returns:
        Human-readable title (e.g., "My Page Name", "Data Model")

    Examples:
        >>> humanize_slug("my-page-name")
        "My Page Name"
        >>> humanize_slug("data_model_v2")
        "Data Model V2"
        >>> humanize_slug("_index")
        "Index"
    """
    return slug.replace("-", " ").replace("_", " ").title()
```

**Jinja2 filter** in `bengal/rendering/template_engine.py`:

```python
# Add to _register_filters()
env.filters["humanize"] = humanize_slug
```

**Migration**: Update all 13+ locations to use `humanize_slug()` or `| humanize` filter.

**Files affected**:
- `bengal/utils/text.py` (add function)
- `bengal/core/page/metadata.py` (2 usages)
- `bengal/discovery/content_discovery.py` (2 usages)
- `bengal/rendering/template_functions/navigation.py` (6 usages)
- `bengal/cli/helpers/menu_config.py` (1 usage)
- `bengal/rendering/template_functions/images.py` (1 usage)
- `bengal/themes/default/templates/partials/docs-nav-section.html` (1 usage)
- `bengal/themes/default/templates/partials/docs-nav.html` (1 usage)
- `bengal/rendering/template_engine.py` (add filter)
- `tests/unit/utils/test_text.py` (add tests)

---

### Phase 2: File Hashing (HIGH PRIORITY)

**Current state**: 3 implementations of file hashing.

| File | Function | Features |
|------|----------|----------|
| `utils/file_utils.py` | `hash_file()` | Basic SHA256 |
| `utils/hashing.py` | `hash_file()` | Algorithm choice, truncate |
| `utils/swizzle.py` | `_checksum_file()` | SHA256, truncate=16 |

**Proposed changes**:

1. **Keep** `bengal/utils/hashing.py` as canonical (already feature-complete)
2. **Deprecate** `bengal/utils/file_utils.py` entirely
3. **Replace** `swizzle.py` private functions with imports

**Migration in `swizzle.py`**:

```python
# Before
def _checksum_file(path: Path) -> str:
    try:
        content = path.read_bytes()
        return sha256(content).hexdigest()[:16]
    except Exception:
        return ""

def _checksum_str(content: str) -> str:
    return sha256(content.encode("utf-8")).hexdigest()[:16]

# After
from bengal.utils.hashing import hash_file, hash_str

def _checksum_file(path: Path) -> str:
    try:
        return hash_file(path, truncate=16)
    except Exception:
        return ""

def _checksum_str(content: str) -> str:
    return hash_str(content, truncate=16)
```

**Files affected**:
- `bengal/utils/file_utils.py` (delete or deprecate)
- `bengal/utils/swizzle.py` (use hashing imports)
- `bengal/cache/build_cache/fingerprint.py` (verify using hashing.py)
- `bengal/cache/build_cache/file_tracking.py` (verify using hashing.py)
- `bengal/cache/dependency_tracker.py` (verify using hashing.py)
- `bengal/server/reload_controller.py` (verify using hashing.py)
- `tests/unit/utils/test_file_utils.py` (migrate to test_hashing.py)

---

### Phase 3: URL Helpers (MEDIUM PRIORITY)

**Current state**: Near-identical code in 3 locations.

**Proposed changes**:

1. **Keep** `bengal/rendering/template_engine/url_helpers.py` as canonical
2. **Delegate** from `TemplateEngine` methods to url_helpers functions
3. **Consolidate** `postprocess/output_formats/utils.py` URL functions

**Migration in `template_engine.py`**:

```python
# Before (methods duplicating url_helpers.py)
def _url_for(self, page: Any) -> str:
    # ~55 lines of duplicate code
    ...

# After
from bengal.rendering.template_engine.url_helpers import url_for, with_baseurl

def _url_for(self, page: Any) -> str:
    return url_for(page, self.site)

def _with_baseurl(self, path: str) -> str:
    return with_baseurl(path, self.site)
```

**Migration in `postprocess/output_formats/utils.py`**:

```python
# Before
def get_page_relative_url(page: Page, site: Any) -> str:
    # ~75 lines with similar logic
    ...

# After
from bengal.rendering.template_engine.url_helpers import url_for

def get_page_relative_url(page: Page, site: Any) -> str:
    """Get relative URL (without baseurl) for postprocessing."""
    # Use url_for but strip baseurl for relative path
    full_url = url_for(page, site)
    baseurl = (site.config.get("baseurl", "") or "").rstrip("/")
    if baseurl and full_url.startswith(baseurl):
        return full_url[len(baseurl):] or "/"
    return full_url
```

**Files affected**:
- `bengal/rendering/template_engine.py` (delegate to url_helpers)
- `bengal/postprocess/output_formats/utils.py` (use url_helpers)

---

### Phase 4: Frontmatter Parsing (MEDIUM PRIORITY)

**Current state**: 2 implementations with different approaches.

| File | Approach | Error Handling |
|------|----------|----------------|
| `discovery/content_discovery.py` | `frontmatter` library | Full with fallback |
| `content_layer/sources/local.py` | Manual YAML parsing | Basic |

**Proposed utility** in `bengal/utils/frontmatter.py`:

```python
"""
Frontmatter parsing utilities.

Provides consistent frontmatter extraction from markdown files.
"""

from __future__ import annotations

from typing import Any

import yaml

from bengal.utils.logger import get_logger

logger = get_logger(__name__)


def parse_frontmatter(
    content: str,
    on_error: str = "return_empty",
) -> tuple[dict[str, Any], str]:
    """
    Parse YAML frontmatter from markdown content.

    Handles content with or without frontmatter delimiters (---).

    Args:
        content: Raw file content with optional frontmatter
        on_error: Error handling strategy:
            - 'return_empty': Return empty dict on error (default)
            - 'raise': Raise exception on error

    Returns:
        Tuple of (metadata dict, body content)

    Examples:
        >>> content = '''---
        ... title: Hello
        ... ---
        ... Body text here'''
        >>> meta, body = parse_frontmatter(content)
        >>> meta
        {'title': 'Hello'}
        >>> body
        'Body text here'
    """
    # No frontmatter delimiter
    if not content.startswith("---"):
        return {}, content

    try:
        # Find end of frontmatter
        end_idx = content.find("---", 3)
        if end_idx == -1:
            return {}, content

        frontmatter_str = content[3:end_idx].strip()
        body = content[end_idx + 3:].lstrip("\n")

        # Parse YAML
        metadata = yaml.safe_load(frontmatter_str) or {}
        return metadata, body

    except yaml.YAMLError as e:
        logger.debug(
            "frontmatter_parse_error",
            error=str(e),
            error_type="yaml_syntax",
        )
        if on_error == "raise":
            raise
        return {}, content

    except Exception as e:
        logger.warning(
            "frontmatter_parse_unexpected_error",
            error=str(e),
            error_type=type(e).__name__,
        )
        if on_error == "raise":
            raise
        return {}, content
```

**Files affected**:
- `bengal/utils/frontmatter.py` (new file)
- `bengal/discovery/content_discovery.py` (use utility)
- `bengal/content_layer/sources/local.py` (use utility)
- `tests/unit/utils/test_frontmatter.py` (new tests)

---

### Phase 5: Deep Merge (LOW PRIORITY)

**Current state**: Identical logic in 2 locations.

**Proposed changes**:

Have `rendering/template_functions/data.py:merge()` delegate to `config/merge.py:deep_merge()`.

```python
# In bengal/rendering/template_functions/data.py

from bengal.config.merge import deep_merge as _deep_merge


def merge(dict1: dict[str, Any], dict2: dict[str, Any], deep: bool = True) -> dict[str, Any]:
    """
    Merge two dictionaries.

    Args:
        dict1: First dictionary
        dict2: Second dictionary (takes precedence)
        deep: Perform deep merge (default: True)

    Returns:
        Merged dictionary

    Example:
        {% set config = defaults | merge(custom_config) %}
    """
    if not isinstance(dict1, dict):
        dict1 = {}
    if not isinstance(dict2, dict):
        dict2 = {}

    if not deep:
        # Shallow merge
        result = dict1.copy()
        result.update(dict2)
        return result

    # Deep merge - delegate to config utility
    return _deep_merge(dict1, dict2)
```

**Files affected**:
- `bengal/rendering/template_functions/data.py` (delegate to config/merge)

---

## Implementation Plan

### Phase 1: Title Humanization (Day 1)

1. Add `humanize_slug()` to `bengal/utils/text.py`
2. Add tests to `tests/unit/utils/test_text.py`
3. Add Jinja2 `humanize` filter
4. Update all 13+ locations to use utility
5. Update templates to use `| humanize` filter

### Phase 2: File Hashing (Day 1-2)

1. Verify all usages of `utils/file_utils.py:hash_file()`
2. Replace with `utils/hashing.py:hash_file()`
3. Update `swizzle.py` to use hashing imports
4. Delete `bengal/utils/file_utils.py`
5. Migrate tests from `test_file_utils.py` to `test_hashing.py`

### Phase 3: URL Helpers (Day 2)

1. Update `template_engine.py` to delegate to `url_helpers.py`
2. Update `postprocess/output_formats/utils.py` to use `url_helpers`
3. Verify all URL generation still works

### Phase 4: Frontmatter Parsing (Day 2-3)

1. Create `bengal/utils/frontmatter.py`
2. Add tests for frontmatter parsing
3. Update `content_discovery.py` to use utility
4. Update `content_layer/sources/local.py` to use utility

### Phase 5: Deep Merge (Day 3)

1. Update `data.py:merge()` to delegate to `config/merge.py`
2. Verify merge filter still works in templates

---

## Testing Strategy

1. **Unit tests** for each new/modified utility
2. **Integration tests** verify existing behavior unchanged
3. **Template tests** verify Jinja2 filters work
4. **Build tests** run full site build before/after

---

## Rollback Plan

Each phase is independent and can be rolled back by reverting the commit. No database migrations or external dependencies.

---

## Risks & Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Behavior change in edge cases | Low | Medium | Comprehensive tests before/after |
| Import cycles | Low | Low | Utilities have no internal dependencies |
| Performance regression | Very Low | Low | Utilities are simple string/file ops |

---

## Success Metrics

- [ ] All 13+ title humanization usages use single utility
- [ ] Zero duplicate hash_file implementations
- [ ] URL generation delegated from template_engine to url_helpers
- [ ] Single frontmatter parser used everywhere
- [ ] deep_merge logic in one place
- [ ] All existing tests pass
- [ ] Full site build succeeds

---

## Open Questions

1. Should `humanize_slug()` handle special cases like acronyms (API → API, not Api)?
2. Should we add deprecation warnings to old functions before removing them?

---

## References

- `bengal/utils/hashing.py` - Existing canonical hashing utility
- `bengal/utils/text.py` - Existing text utilities (has `slugify`)
- `bengal/config/merge.py` - Existing deep merge utility
- `plan/completed/rfc-utility-extraction.md` - Previous utility extraction work
