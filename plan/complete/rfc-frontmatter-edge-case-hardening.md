# RFC: Frontmatter Edge Case Hardening

**Status**: Implemented  
**Created**: 2026-01-04  
**Author**: AI Assistant  
**Related**: Graph placeholder flicker fix, Rosettes build failure

## Summary

This RFC documents the hardening of Bengal's frontmatter parsing to handle YAML edge cases that can cause runtime crashes. The primary fix sanitizes list fields (tags, aliases, keywords) at the source in `PageCore.__post_init__`, preventing `AttributeError` and `TypeError` exceptions throughout the codebase.

## Problem Statement

### Root Cause

YAML has special keywords that parse to non-string Python types:

```yaml
tags:
- null        # Python None
- ~           # Python None (YAML alias)
- true        # Python bool
- false       # Python bool
- 404         # Python int
- 3.14        # Python float
- 2024-01-01  # Python datetime.date
- [a, b]      # Python list
- {key: val}  # Python dict
```

When code later calls `.lower()` or `.replace()` on these values, it crashes:

```python
# This crashes if tag is None
tag_key = tag.lower().replace(" ", "-")
# AttributeError: 'NoneType' object has no attribute 'lower'
```

### Discovery

The issue was discovered when the Rosettes documentation site failed to build with:

```
Error: [taxonomies] phase_error error='NoneType' object has no attribute 'lower'
```

Investigation revealed `site/content/docs/formatters/null.md` contained:

```yaml
tags:
- null   # ← YAML keyword, parsed as Python None
- raw
```

### Scope of Impact

Searching the codebase found 34+ locations iterating over tags with `.lower()` calls, plus similar patterns for categories, keywords, and aliases.

```bash
# Verify: count locations that iterate over tags with .lower()
rg "for.*tag.*in.*tags" --type py -l | wc -l
rg "\.lower\(\)" bengal/ --type py -C 2 | grep -i tag | wc -l
```

## Solution

### Design Principles

1. **Sanitize at source** - Fix once in `PageCore.__post_init__`, not 34 times
2. **Fail gracefully** - Filter invalid values, don't crash
3. **Log for debugging** - Emit debug logs when values are filtered
4. **Preserve valid data** - Convert types where sensible (int → str)

### Implementation

#### 1. Source-Level Sanitization (`PageCore.__post_init__`)

```python
def __post_init__(self) -> None:
    # Sanitize list fields
    self.tags, tags_filtered = self._sanitize_string_list_with_report(self.tags)
    self.aliases, aliases_filtered = self._sanitize_string_list_with_report(self.aliases)

    # Log warnings for filtered values
    if tags_filtered:
        logger.debug(
            "frontmatter_tags_filtered",
            source_path=self.source_path,
            filtered=tags_filtered,
        )

@staticmethod
def _sanitize_string_list_with_report(items: list | None) -> tuple[list[str], list[str]]:
    """Sanitize list items to valid non-empty strings."""
    if items is None:
        return [], []

    sanitized = []
    filtered = []

    for item in items:
        if item is None:
            filtered.append("null/None")
        elif isinstance(item, (list, dict)):
            filtered.append(f"nested {type(item).__name__}")
        elif not str(item).strip():
            filtered.append("empty string")
        else:
            sanitized.append(str(item).strip())

    return sanitized, filtered
```

#### 2. Defensive Checks (Belt & Suspenders)

Added `if tag is not None` checks in 7 additional locations:

| File | Function |
|------|----------|
| `orchestration/build/initialization.py` | `phase_incremental_filter` |
| `orchestration/related_posts.py` | `_build_tag_map` |
| `orchestration/incremental/taxonomy_detector.py` | `detect_taxonomy_changes` |
| `cache/build_cache/taxonomy_index_mixin.py` | `update_page_tags` |
| `cache/dependency_tracker.py` | `track_taxonomy_dependency` |
| `analysis/link_suggestions.py` | `_build_tag_map`, `_build_category_map` |
| `analysis/graph_reporting.py` | tag clustering |

#### 3. Keywords Sanitization

```python
# core/page/metadata.py
@property
def keywords(self) -> list[str]:
    keywords = self.metadata.get("keywords", [])
    if isinstance(keywords, list):
        return [
            str(k).strip()
            for k in keywords
            if k is not None and str(k).strip()
        ]
    return []
```

## Behavior Matrix

| YAML Input | Python Type | Before | After |
|------------|-------------|--------|-------|
| `- null` | `None` | ❌ Crash | ✅ Filtered |
| `- ~` | `None` | ❌ Crash | ✅ Filtered |
| `- true` | `bool` | ⚠️ Unexpected | ✅ `"True"` |
| `- false` | `bool` | ⚠️ Unexpected | ✅ `"False"` |
| `- 404` | `int` | ⚠️ May work | ✅ `"404"` |
| `- 3.14` | `float` | ⚠️ May work | ✅ `"3.14"` |
| `- 2024-01-01` | `date` | ⚠️ May work | ✅ `"2024-01-01"` |
| `- ""` | `str` | ⚠️ Empty slug | ✅ Filtered |
| `- "   "` | `str` | ⚠️ Empty slug | ✅ Filtered |
| `- [a, b]` | `list` | ❌ Crash | ✅ Filtered |
| `- {k: v}` | `dict` | ❌ Crash | ✅ Filtered |
| `- valid-tag` | `str` | ✅ Works | ✅ Works |

## Testing

### Unit Tests Added

File: `tests/unit/core/page/test_yaml_edge_cases.py`

```
17 passed in 3.69s
```

Test classes:
- `TestTagsSanitization` - 12 tests for various YAML edge cases
- `TestAliasesSanitization` - 2 tests for alias field
- `TestSanitizationReporting` - 3 tests for filtered value reporting

### Test Fixtures Added

- `tests/fixtures/edge_cases/yaml_special_values.md`
- `tests/fixtures/edge_cases/yaml_nested_values.md`

## Already Robust (No Changes Needed)

| Field | Mechanism | Location |
|-------|-----------|----------|
| `date` | `parse_date()` returns `None` on error | `utils/dates.py` |
| `weight` | `try/except (ValueError, TypeError)` | `page/metadata.py` |
| `draft` | `bool()` coercion | `page/metadata.py` |
| `author(s)` | `Author.from_frontmatter()` handles all types | `core/author.py` |
| `series` | `try/except` for part/total | `cache/indexes/series_index.py` |
| `title` | Defaults to "Untitled" | `page/page_core.py` |

## Optional Future Enhancements

These are low-priority items that could be added if issues arise:

### 1. Slug Length Limit

```python
# In utils/text.py slugify()
def slugify(text: str, max_length: int = 200) -> str:
    slug = # ... existing logic ...
    if max_length and len(slug) > max_length:
        slug = slug[:max_length].rsplit('-', 1)[0]
    return slug
```

### 2. Frontmatter Size Warning

```python
# In content parser
if len(frontmatter_yaml) > 65536:  # 64KB
    logger.warning("large_frontmatter", path=path, size=len(frontmatter_yaml))
```

### 3. Nested Depth Limit

```python
def check_nesting_depth(obj, max_depth=10, current=0):
    if current > max_depth:
        raise ValueError(f"Frontmatter nesting exceeds {max_depth} levels")
    if isinstance(obj, dict):
        for v in obj.values():
            check_nesting_depth(v, max_depth, current + 1)
    elif isinstance(obj, list):
        for item in obj:
            check_nesting_depth(item, max_depth, current + 1)
```

## Security Considerations

| Risk | Status |
|------|--------|
| Path traversal | ✅ `Path.resolve()` used throughout |
| YAML bombs | ✅ PyYAML's `safe_load` (no arbitrary objects) |
| ReDoS in slugify | ✅ Simple regex patterns, no backtracking |
| XSS in frontmatter | ✅ HTML escaping in Kida templates |

## Migration Guide

No migration needed. Changes are backward compatible:
- Valid frontmatter continues to work unchanged
- Invalid values are now silently filtered (with debug log)
- No configuration required

## Files Changed

### Bengal Core (10 files)

```
bengal/core/page/page_core.py          # Source sanitization
bengal/core/page/metadata.py           # Keywords sanitization
bengal/orchestration/build/initialization.py
bengal/orchestration/related_posts.py
bengal/orchestration/incremental/taxonomy_detector.py
bengal/orchestration/taxonomy.py       # Already had str()
bengal/cache/build_cache/taxonomy_index_mixin.py
bengal/cache/dependency_tracker.py
bengal/analysis/link_suggestions.py
bengal/analysis/graph_reporting.py
```

### Tests (1 file)

```
tests/unit/core/page/test_yaml_edge_cases.py   # 17 tests
```

### Fixtures (2 files)

```
tests/fixtures/edge_cases/yaml_special_values.md
tests/fixtures/edge_cases/yaml_nested_values.md
```

### Rosettes Fix (1 file)

```
site/content/docs/formatters/null.md   # "null" → quoted string
```

## Verification

Confirm the implementation with these commands:

```bash
# Run the edge case tests
uv run pytest tests/unit/core/page/test_yaml_edge_cases.py -v

# Verify source sanitization exists
rg "_sanitize_string_list_with_report" bengal/

# Verify defensive checks in place
rg "if tag is not None" bengal/ --type py

# Build Rosettes site (previously crashed on null.md)
cd ../rosettes && uv run bengal build
```

## Conclusion

This hardening ensures Bengal gracefully handles YAML edge cases that previously caused cryptic runtime errors. The fix is minimal, well-tested, and backward compatible. Users with existing valid frontmatter will see no change in behavior.
