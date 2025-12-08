---
Title: Dataclass Improvements for Build Orchestration
Author: AI Assistant
Date: 2025-01-XX
Status: Draft
Confidence: 92%
Evaluation: See `plan/active/rfc-dataclass-improvements-evaluation.md`
---

# RFC: Dataclass Improvements for Build Orchestration

**Proposal**: Replace complex tuple return values with typed dataclasses in build orchestration to improve type safety, readability, and maintainability.

---

## 1. Problem Statement

### Current State

Bengal's build orchestration uses complex tuple return values that are difficult to use correctly:

**Evidence**:

1. **`phase_incremental_filter()`** returns a 5-element tuple:
   ```python
   # bengal/orchestration/build/initialization.py:264
   def phase_incremental_filter(...) -> tuple[list, list, set, set, set | None] | None:
       # Returns: (pages_to_build, assets_to_process, affected_tags,
       #           changed_page_paths, affected_sections)
   ```

2. **`phase_config_check()`** returns a 2-element tuple:
   ```python
   # bengal/orchestration/build/initialization.py:205
   def phase_config_check(...) -> tuple[bool, bool]:
       # Returns: (incremental, config_changed)
   ```

3. **`find_work_early()`** returns a tuple where the third element is a dict with string keys:
   ```python
   # bengal/orchestration/incremental.py:270
   def find_work_early(...) -> tuple[list[Page], list[Asset], dict[str, list]]:
       change_summary: dict[str, list] = {
           "Modified content": [],
           "Modified assets": [],
           "Modified templates": [],
           "Taxonomy changes": [],
       }
       return (pages_to_build, assets_to_process, change_summary)
   ```

   **Call site** (`bengal/orchestration/build/initialization.py:297-299`):
   ```python
   pages_to_build, assets_to_process, change_summary = (
       orchestrator.incremental.find_work_early(verbose=verbose)
   )
   ```

### Pain Points

1. **Type Safety**: Tuple elements are positional and untyped. Easy to access wrong index.
2. **Readability**: Code like `result[0]`, `result[1]` is unclear without comments.
3. **Maintainability**: Adding/removing fields requires updating all call sites.
4. **IDE Support**: No autocomplete or type checking for tuple elements.
5. **Error-Prone**: Easy to swap order or forget which element is which.

**Example of Current Usage**:

**Call site** (`bengal/orchestration/build/__init__.py:221-233`):
```python
# Hard to understand what each element means
filter_result = initialization.phase_incremental_filter(
    self, cli, cache, incremental, verbose, build_start
)
if filter_result is None:
    return self.stats  # Early exit
(
    pages_to_build,      # What is this? (index 0)
    assets_to_process,   # What is this? (index 1)
    affected_tags,       # What is this? (index 2)
    changed_page_paths,  # What is this? (index 3)
    affected_sections,   # What is this? (index 4)
) = filter_result
```

**Config check call site** (`bengal/orchestration/build/__init__.py:216-218`):
```python
# Which bool is which?
incremental, config_changed = initialization.phase_config_check(
    self, cli, cache, incremental
)
```

---

## 2. Goals & Non-Goals

**Goals**:

- Replace complex tuple returns with typed dataclasses
- Improve type safety and IDE support
- Maintain backward compatibility during migration
- Follow Bengal's existing dataclass patterns (`PageCore`, `BuildContext`, etc.)

**Non-Goals**:

- We are not changing the build logic itself
- We won't refactor template context (dicts are required for Jinja2 compatibility)
- We won't change return types of simple functions (e.g., `-> bool` or `-> list[Page]`)

---

## 3. Architecture Impact

**Affected Subsystems**:

- **Orchestration** (`bengal/orchestration/`): Build phase functions and incremental orchestrator
- **Core** (`bengal/core/`): No changes (already uses dataclasses well)
- **Cache** (`bengal/cache/`): No changes

**Files Modified**:

- `bengal/orchestration/build/initialization.py` - Phase functions (`phase_config_check`, `phase_incremental_filter`)
- `bengal/orchestration/incremental.py` - Incremental orchestrator (`find_work_early`)
- `bengal/orchestration/build/__init__.py` - Build orchestrator call sites (lines 216-233)

**Call Sites Identified**:

1. `phase_config_check`: 1 call site (`build/__init__.py:216`)
2. `phase_incremental_filter`: 1 call site (`build/__init__.py:221`)
3. `find_work_early`: 1 call site (`initialization.py:297`, internal to `phase_incremental_filter`)

**Total**: 3 call sites to update (low migration effort)

---

## 4. Design Options

### Option A: Dataclasses for All Complex Returns (Recommended)

Create dedicated dataclasses for each complex return type.

**Pros**:
- Type-safe with full IDE support
- Self-documenting (field names explain purpose)
- Easy to extend (add fields without breaking call sites)
- Follows Bengal's existing patterns (`BuildContext`, `PageCore`)

**Cons**:
- Requires updating all call sites
- Slight overhead (dataclass creation vs tuple)

### Option B: TypedDict for Return Values

Use TypedDict for return values.

**Pros**:
- Backward compatible (still a dict)
- Type hints available

**Cons**:
- Still uses string keys (error-prone)
- No field validation
- Doesn't match Bengal's dataclass conventions

**Recommended**: **Option A** - Dataclasses align with Bengal's architecture and provide better type safety.

---

## 5. Detailed Design

### 5.1 FilterResult Dataclass

**Location**: `bengal/orchestration/build/initialization.py`

**Current**:
```python
def phase_incremental_filter(...) -> tuple[list, list, set, set, set | None] | None:
    return (pages_to_build, assets_to_process, affected_tags,
            changed_page_paths, affected_sections)
```

**Proposed**:
```python
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from bengal.core.asset import Asset
    from bengal.core.page import Page

@dataclass
class FilterResult:
    """
    Result of incremental filtering phase.

    Contains the work items and change information determined during
    Phase 5: Incremental Filtering.

    Attributes:
        pages_to_build: Pages that need rendering (changed or dependent)
        assets_to_process: Assets that need processing
        affected_tags: Tags that have changed (triggers taxonomy rebuild)
        changed_page_paths: Source paths of changed pages
        affected_sections: Sections with changes (None if all sections affected)
    """
    pages_to_build: list[Page]
    assets_to_process: list[Asset]
    affected_tags: set[str]
    changed_page_paths: set[Path]
    affected_sections: set[str] | None
```

**Usage**:
```python
filter_result = phase_incremental_filter(...)
if filter_result:
    pages_to_build = filter_result.pages_to_build  # Clear!
    assets_to_process = filter_result.assets_to_process  # Clear!
    affected_tags = filter_result.affected_tags  # Clear!
```

### 5.2 ConfigCheckResult Dataclass

**Location**: `bengal/orchestration/build/initialization.py`

**Current**:
```python
def phase_config_check(...) -> tuple[bool, bool]:
    return (incremental, config_changed)
```

**Proposed**:
```python
@dataclass
class ConfigCheckResult:
    """
    Result of configuration check phase.

    Determines whether incremental builds are still valid after
    checking for configuration changes.

    Attributes:
        incremental: Whether incremental build should proceed (False if config changed)
        config_changed: Whether configuration file was modified
    """
    incremental: bool
    config_changed: bool
```

**Usage**:
```python
result = phase_config_check(...)
if result.config_changed:
    # Clear what we're checking!
    incremental = False
```

### 5.3 ChangeSummary Dataclass

**Location**: `bengal/orchestration/incremental.py`

**Current**:
```python
change_summary: dict[str, list] = {
    "Modified content": [],
    "Modified assets": [],
    "Modified templates": [],
    "Taxonomy changes": [],
}
```

**Proposed**:
```python
from dataclasses import dataclass, field
from pathlib import Path

@dataclass
class ChangeSummary:
    """
    Summary of changes detected during incremental build.

    Used for verbose logging and debugging. Contains lists of paths
    that changed, organized by change type.

    Attributes:
        modified_content: Source paths of modified content files
        modified_assets: Paths of modified asset files
        modified_templates: Paths of modified template files
        taxonomy_changes: Tag slugs that have taxonomy changes
    """
    modified_content: list[Path] = field(default_factory=list)
    modified_assets: list[Path] = field(default_factory=list)
    modified_templates: list[Path] = field(default_factory=list)
    taxonomy_changes: list[str] = field(default_factory=list)
```

**Usage**:
```python
# In find_work_early()
change_summary = ChangeSummary()
change_summary.modified_content.append(page.source_path)  # Type-safe!

# Return as part of tuple (for now, see migration plan)
return (pages_to_build, assets_to_process, change_summary)
```

---

## 6. Migration Plan

### Phase 1: Add Dataclasses (Non-Breaking)

1. Add dataclass definitions to appropriate modules
2. Update function signatures to return dataclasses
3. **Keep old tuple unpacking working** via `__iter__` method:

```python
@dataclass
class FilterResult:
    pages_to_build: list[Page]
    assets_to_process: list[Asset]
    # ... other fields

    def __iter__(self):
        """Allow tuple unpacking for backward compatibility."""
        return iter((
            self.pages_to_build,
            self.assets_to_process,
            self.affected_tags,
            self.changed_page_paths,
            self.affected_sections,
        ))
```

### Phase 2: Update Call Sites (Gradual)

1. Update call sites to use dataclass attributes:
   ```python
   # Old
   pages, assets, tags, paths, sections = phase_incremental_filter(...)

   # New
   result = phase_incremental_filter(...)
   if result:
       pages = result.pages_to_build
       assets = result.assets_to_process
   ```

2. Update call sites (only 3 total):
   - `bengal/orchestration/build/__init__.py:216` - `phase_config_check` call site
   - `bengal/orchestration/build/__init__.py:221-233` - `phase_incremental_filter` call site
   - `bengal/orchestration/build/initialization.py:297-299` - `find_work_early` call site (internal)

   **Note**: The call sites in `content.py` and `rendering.py` mentioned in original RFC are not affected - they don't call these functions directly.

### Phase 3: Remove Tuple Compatibility (Breaking)

After all call sites updated:
1. Remove `__iter__` methods from dataclasses
2. Update type hints to be explicit about dataclass returns
3. Add tests to ensure no tuple unpacking remains

---

## 7. Implementation Details

### 7.1 File Organization

**Option A: Centralized (Recommended)**
- `bengal/orchestration/build/results.py` - All result dataclasses in one place
- **Pros**: Single location, easy to find all result types
- **Cons**: Separate from functions that use them

**Option B: Co-located**
- Place each dataclass in the same module as the function that returns it
- **Pros**: Keeps related code together
- **Cons**: Multiple locations

**Recommended**: **Option A** - Centralized location matches Bengal's pattern of grouping related types (e.g., `bengal/core/page/page_core.py`).

**Modified Files**:
- `bengal/orchestration/build/results.py` - **NEW**: All result dataclasses
- `bengal/orchestration/build/initialization.py` - Import and use result dataclasses
- `bengal/orchestration/incremental.py` - Import and use ChangeSummary
- `bengal/orchestration/build/__init__.py` - Update call sites (lines 216-233)

### 7.2 Type Hints

Use `TYPE_CHECKING` to avoid circular imports:

```python
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from bengal.core.page import Page
    from bengal.core.asset import Asset
```

### 7.3 Backward Compatibility

During migration, support both tuple unpacking and attribute access:

```python
result = phase_incremental_filter(...)

# Old way (still works)
pages, assets, tags, paths, sections = result

# New way (preferred)
pages = result.pages_to_build
```

---

## 8. Testing Strategy

### Unit Tests

1. Test dataclass creation and field access
2. Test tuple unpacking compatibility (Phase 1)
3. Test `None` return from `phase_incremental_filter` (early exit case)
4. Test all call sites use new API (Phase 2)

### Integration Tests

1. Verify incremental builds still work correctly
2. Verify config change detection still works
3. Verify change summary logging still works

### Test Examples

**Test 1: Dataclass and tuple compatibility**
```python
def test_filter_result_dataclass():
    """Test FilterResult can be used as dataclass and tuple."""
    result = FilterResult(
        pages_to_build=[page1, page2],
        assets_to_process=[asset1],
        affected_tags={"python", "web"},
        changed_page_paths={Path("content/post.md")},
        affected_sections={"blog"},
    )

    # Attribute access (new way)
    assert len(result.pages_to_build) == 2
    assert "python" in result.affected_tags

    # Tuple unpacking (backward compatibility)
    pages, assets, tags, paths, sections = result
    assert len(pages) == 2
    assert "python" in tags
```

**Test 2: None return (early exit)**
```python
def test_filter_result_none_return():
    """Test that None return still works for early exit."""
    # Simulate no changes detected
    result = phase_incremental_filter(...)
    assert result is None  # Early exit case

    # Should not raise error
    if result is None:
        return  # Early exit works
```

**Test 3: ConfigCheckResult**
```python
def test_config_check_result():
    """Test ConfigCheckResult dataclass."""
    result = ConfigCheckResult(
        incremental=True,
        config_changed=False,
    )

    # Attribute access
    assert result.incremental is True
    assert result.config_changed is False

    # Tuple unpacking (backward compatibility)
    incremental, config_changed = result
    assert incremental is True
    assert config_changed is False
```

---

## 9. Risks & Mitigations

### Risk 1: Breaking Changes During Migration

**Mitigation**: Use `__iter__` method for backward compatibility during Phase 1-2.

### Risk 2: Performance Overhead

**Mitigation**: Dataclass creation overhead is negligible (<1µs) compared to build operations (seconds).

### Risk 3: Call Site Updates Missed

**Mitigation**:
- Use type checker (mypy/pyright) to find all call sites
- Add tests that verify no tuple unpacking remains
- Gradual migration allows testing at each step

---

## 10. Success Criteria

- [ ] All complex tuple returns replaced with dataclasses
- [ ] Type hints provide full IDE autocomplete
- [ ] All call sites updated to use attribute access
- [ ] Tests verify backward compatibility during migration
- [ ] No performance regression (measure build times)
- [ ] Code review confirms improved readability

---

## 11. Related Work

- `BuildContext` dataclass (`bengal/utils/build_context.py`) - Similar pattern already in use
- `PageCore` dataclass (`bengal/core/page/page_core.py`) - Example of well-designed dataclass
- Python dataclasses documentation - Standard library patterns

---

## 12. Open Questions

1. **Should we add `__repr__` methods** for better debugging?
   - **Answer**: No - dataclasses provide this by default, and default is usually sufficient. Only customize if debugging needs require it.

2. **Should we add validation** in `__post_init__`?
   - **Answer**: Maybe - depends on if we need to validate field relationships. For example, could validate that `affected_sections` is not None when `affected_tags` is non-empty. Start without validation, add if needed.

3. **Should ChangeSummary be part of FilterResult**?
   - **Answer**: No - separate concerns. `ChangeSummary` is optional/verbose logging data, while `FilterResult` contains required build state. Keeping them separate maintains clear separation of concerns.

4. **File organization: centralized vs co-located?**
   - **Answer**: Centralized (`results.py`) - matches Bengal's pattern of grouping related types, easier to find all result types in one place.

---

## 13. Appendix: Code Examples

### Before (Current)

```python
# Hard to understand
filter_result = phase_incremental_filter(...)
if filter_result:
    pages_to_build = filter_result[0]
    assets_to_process = filter_result[1]
    affected_tags = filter_result[2]
    changed_page_paths = filter_result[3]
    affected_sections = filter_result[4]
```

### After (Proposed)

```python
# Clear and type-safe
filter_result = phase_incremental_filter(...)
if filter_result:
    pages_to_build = filter_result.pages_to_build
    assets_to_process = filter_result.assets_to_process
    affected_tags = filter_result.affected_tags
    changed_page_paths = filter_result.changed_page_paths
    affected_sections = filter_result.affected_sections
```

---

**Status**: Ready for implementation  
**Confidence**: 92% 🟢 (High)  
**Evaluation**: See `plan/active/rfc-dataclass-improvements-evaluation.md` for detailed codebase verification

**Next Steps**:
1. ✅ RFC evaluated against codebase (all claims verified)
2. Create implementation plan
3. Begin Phase 1 implementation (add dataclasses with `__iter__` compatibility)
4. Update call sites (Phase 2)
5. Remove tuple compatibility (Phase 3)
