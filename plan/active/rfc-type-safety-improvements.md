---
Title: Type Safety Improvements for Bengal
Author: AI Assistant
Date: 2025-01-XX
Status: Draft
Confidence: 88%
---

# RFC: Type Safety Improvements for Bengal

**Proposal**: Enhance type safety across the Bengal codebase by addressing missing type annotations, reducing `Any` usage, enabling stricter mypy checks, and improving type coverage.

---

## 1. Problem Statement

### Current State

Bengal has basic type checking enabled (`disallow_untyped_defs = true`), but several type safety gaps remain:

**Evidence**:

1. **Missing `py.typed` marker**:
   - Declared in `pyproject.toml` (`bengal/py.typed` in package-data)
   - File doesn't actually exist in `bengal/` directory
   - Impact: Type checkers won't recognize Bengal as a typed package

2. **Excessive `Any` usage**:
   - Found **220 uses** of `Any` across codebase
   - Critical functions return `Any`:
     ```python
     # bengal/utils/file_io.py:348-350
     def load_toml(...) -> Any:  # Should return dict[str, Any] | None
     def load_yaml(...) -> Any:   # Should return dict[str, Any] | None
     def load_data_file(...) -> Any:  # Should return dict[str, Any] | None
     ```

3. **Missing type annotations**:
   - **~50+ functions** missing return/parameter types (from mypy output)
   - Examples:
     ```python
     # bengal/utils/dotdict.py:183-191
     def keys(self):  # Missing -> KeysView[str]
     def values(self):  # Missing -> ValuesView[Any]
     def items(self):  # Missing -> ItemsView[str, Any]

# bengal/utils/performance_report.py: Multiple functions missing annotations
     ```

4. **Type errors from mypy**:
   - **~100+ type errors** currently present
   - Categories:
     - `no-any-return`: 15+ functions returning `Any` when they shouldn't
     - `assignment`: Type mismatches (e.g., `bengal/utils/progress.py:156`)
     - `attr-defined`: Missing attributes (e.g., `PageComputedMixin` missing `metadata`, `content`)
     - `union-attr`: Accessing attributes on `None` unions
     - `override`: Return type incompatibilities

5. **Missing type stubs**:
   - `yaml` library stubs not installed
   - Affects: `bengal/cli/skeleton/schema.py`, `bengal/cli/helpers/config_validation.py`
   - Error: `Library stubs not installed for "yaml"`

6. **Missing TypedDict usage**:
   - Many `dict[str, Any]` return types could use `TypedDict`:
     ```python
     # bengal/rendering/template_functions/i18n.py:128
     def _languages(site: Site) -> list[dict[str, Any]]:  # Could be TypedDict

     # bengal/orchestration/incremental.py:270
     def find_work_early(...) -> tuple[..., dict[str, list]]:  # Could be TypedDict
     ```

7. **Missing strict mypy settings**:
   - Current config only has basic checks
   - Missing: `disallow_any_generics`, `disallow_incomplete_defs`, `strict_optional`, etc.

### Pain Points

1. **Type Safety**: Functions returning `Any` lose type information, making code harder to understand and maintain
2. **IDE Support**: Missing annotations reduce autocomplete and type checking in IDEs
3. **Runtime Errors**: Type mismatches can cause runtime errors that could be caught at type-check time
4. **Maintainability**: Unclear types make refactoring risky and error-prone
5. **Documentation**: Type hints serve as inline documentation; missing hints reduce code clarity
6. **Third-Party Integration**: Missing `py.typed` marker prevents proper type checking for Bengal users

**Example of Current Issues**:

```python
# bengal/utils/file_io.py:409-411
def load_data_file(...) -> Any:
    # Callers don't know what type they'll get
    data = load_data_file("config.yaml")  # What is data? dict? list? None?
    data["key"]  # Type checker can't verify this is safe

# bengal/utils/profile.py:269
def should_show_debug() -> bool:
    profile = get_current_profile()
    config = profile.get_config()  # Returns Any
    return config.get("enable_debug_output", False)  # no-any-return error
```

---

## 2. Goals & Non-Goals

**Goals**:

- Fix critical type safety gaps (missing annotations, `py.typed` marker)
- Reduce `Any` usage in public APIs and critical paths
- Enable stricter mypy checks gradually (not all at once)
- Fix existing type errors identified by mypy
- Improve type coverage for better IDE support and maintainability
- Install missing type stubs for dependencies

**Non-Goals**:

- **100% type coverage**: Some `Any` usage is acceptable for dynamic code (templates, config loading)
- **Strict mode immediately**: Enable strict checks gradually to avoid breaking changes
- **Refactor all dict returns**: Only convert `dict[str, Any]` to `TypedDict` where structure is well-defined
- **Remove all type ignores**: Some `# type: ignore` comments are necessary for third-party library limitations

---

## 3. Scope & Impact

**Subsystems Affected**:

- **Core** (`bengal/core/`): Fix `PageComputedMixin` attribute issues
- **Utils** (`bengal/utils/`): Add missing annotations, reduce `Any` usage
- **Rendering** (`bengal/rendering/`): Fix type errors, add missing annotations
- **CLI** (`bengal/cli/`): Install yaml stubs, fix type errors
- **Autodoc** (`bengal/autodoc/`): Add missing return types
- **Config** (`bengal/config/`): Fix `no-any-return` errors
- **Server** (`bengal/server/`): Add missing type annotations

**Files Modified**:

- `bengal/py.typed` - **NEW FILE** (create empty marker)
- `bengal/pyproject.toml` - Add `types-PyYAML` to dev dependencies, add stricter mypy settings
- `bengal/utils/file_io.py` - Fix return types (`Any` → `dict[str, Any] | None`)
- `bengal/utils/dotdict.py` - Add return type annotations
- `bengal/utils/profile.py` - Fix `no-any-return` errors
- `bengal/utils/performance_report.py` - Add missing type annotations
- `bengal/core/page/computed.py` - Fix `attr-defined` errors
- `bengal/rendering/pipeline/toc.py` - Add missing type annotations
- `bengal/server/utils.py` - Add missing type annotations
- `bengal/config/defaults.py` - Fix `no-any-return` errors
- ~20+ additional files with type fixes

**Breaking Changes**: None (all changes are additive or internal improvements)

---

## 4. Design Options

### Option A: Comprehensive Type Safety Overhaul (Recommended)

Fix all critical issues in phases:

**Phase 1: Foundation** (Low risk, high value):
- Create `py.typed` marker
- Install `types-PyYAML`
- Add missing return type annotations (no behavior changes)
- Fix `no-any-return` errors in utils

**Phase 2: Stricter Checks** (Medium risk):
- Enable additional mypy strict settings gradually
- Fix resulting type errors
- Replace `dict[str, Any]` with `TypedDict` where structure is known

**Phase 3: Advanced** (Lower priority):
- Reduce `Any` usage in internal code
- Add type narrowing where beneficial
- Consider `Protocol` types for structural typing

**Pros**:
- Incremental approach reduces risk
- Can stop at any phase if needed
- High-value fixes first (foundation)
- Maintains backward compatibility

**Cons**:
- Takes multiple phases to complete
- Requires ongoing maintenance

### Option B: Minimal Fixes Only

Only fix critical issues:
- Create `py.typed` marker
- Install `types-PyYAML`
- Fix blocking type errors

**Pros**:
- Minimal effort
- Low risk
- Quick wins

**Cons**:
- Leaves many type safety gaps
- Doesn't improve IDE support significantly
- Misses opportunity for better maintainability

**Recommended**: **Option A** - Comprehensive approach provides better long-term value.

---

## 5. Detailed Design

### 5.1 Phase 1: Foundation

#### 5.1.1 Create `py.typed` Marker

**File**: `bengal/py.typed` (new file)

**Content**: Empty file (marker only)

**Rationale**: Signals to type checkers that Bengal is a typed package.

#### 5.1.2 Install Type Stubs

**File**: `bengal/pyproject.toml`

**Change**:
```toml
[project.optional-dependencies]
dev = [
    # ... existing ...
    "types-PyYAML>=6.0.12",  # Add yaml type stubs
]
```

#### 5.1.3 Fix Missing Return Type Annotations

**Priority Files**:

1. **`bengal/utils/dotdict.py`**:
   ```python
   # Current
   def keys(self):
       return self._data.keys()

   # Fixed
   from collections.abc import KeysView
   def keys(self) -> KeysView[str]:
       return self._data.keys()
   ```

2. **`bengal/utils/performance_report.py`**:
   - Add return types to all 7 functions missing annotations
   - Use `-> None` for functions that don't return values

#### 5.1.4 Fix `no-any-return` Errors

**Priority**: Functions in public APIs or critical paths

**Example**: `bengal/utils/file_io.py`:
```python
# Current
def load_toml(...) -> Any:
    # ...
    return data  # data is dict[str, Any] | None

# Fixed
def load_toml(...) -> dict[str, Any] | None:
    # ...
    return data
```

**Example**: `bengal/utils/profile.py`:
```python
# Current
def should_show_debug() -> bool:
    config = profile.get_config()  # Returns Any
    return config.get("enable_debug_output", False)  # no-any-return

# Fixed
def should_show_debug() -> bool:
    config: dict[str, Any] = profile.get_config()
    return bool(config.get("enable_debug_output", False))
```

### 5.2 Phase 2: Stricter Checks

#### 5.2.1 Enable Additional Mypy Settings

**File**: `bengal/pyproject.toml`

**Add** (gradually):
```toml
[tool.mypy]
# Existing
python_version = "3.14"
warn_return_any = true
warn_unused_configs = true
disallow_untyped_defs = true

# Add these gradually
disallow_any_generics = true      # Prevents Any in generics
disallow_incomplete_defs = true   # Requires complete annotations
disallow_untyped_calls = true     # Prevents calling untyped functions
strict_optional = true            # Better None handling
warn_redundant_casts = true       # Warns about unnecessary casts
warn_unused_ignores = true        # Warns about unused type: ignore
```

**Strategy**: Enable one setting at a time, fix errors, then enable next.

#### 5.2.2 Fix Attribute Errors

**Example**: `bengal/core/page/computed.py`:
```python
# Current - PageComputedMixin missing metadata/content attributes
class PageComputedMixin:
    def slug(self) -> str:
        return self.metadata.get("slug", "")  # attr-defined error

# Fixed - Add proper type hints or use Protocol
from typing import Protocol

class HasMetadata(Protocol):
    metadata: dict[str, Any]
    content: str

class PageComputedMixin:
    def slug(self: HasMetadata) -> str:
        return self.metadata.get("slug", "")
```

#### 5.2.3 Introduce TypedDict for Known Structures

**Example**: `bengal/rendering/template_functions/i18n.py`:
```python
# Current
def _languages(site: Site) -> list[dict[str, Any]]:

# Fixed
from typing import TypedDict

class LanguageInfo(TypedDict):
    code: str
    name: str
    weight: int

def _languages(site: Site) -> list[LanguageInfo]:
```

### 5.3 Phase 3: Advanced Improvements

#### 5.3.1 Reduce `Any` Usage

- Replace `Any` with more specific types where possible
- Use `object` for truly dynamic content
- Use `Protocol` for structural types

#### 5.3.2 Add Type Narrowing

**Example**: `bengal/rendering/asset_extractor.py:66`:
```python
# Current
if item is not None:
    item.lower()  # union-attr error

# Fixed
if item is not None:
    assert isinstance(item, str)  # Type narrowing
    item.lower()  # Now type-safe
```

---

## 6. Implementation Plan

### Phase 1: Foundation (Week 1)

**Tasks**:
1. ✅ Create `bengal/py.typed` marker file
2. ✅ Add `types-PyYAML` to dev dependencies
3. ✅ Fix missing return type annotations in `dotdict.py`, `performance_report.py`
4. ✅ Fix `no-any-return` errors in `file_io.py`, `profile.py`, `config/defaults.py`
5. ✅ Run mypy and verify Phase 1 fixes

**Success Criteria**:
- `py.typed` file exists
- `types-PyYAML` installed
- ~20-30 type errors fixed
- No new type errors introduced

### Phase 2: Stricter Checks (Week 2-3)

**Tasks**:
1. Enable `strict_optional = true`, fix resulting errors
2. Enable `disallow_any_generics = true`, fix resulting errors
3. Enable `disallow_incomplete_defs = true`, fix resulting errors
4. Fix `attr-defined` errors (e.g., `PageComputedMixin`)
5. Fix `union-attr` errors with type narrowing
6. Fix `override` errors

**Success Criteria**:
- All new mypy settings enabled
- ~50-70 type errors fixed
- Type coverage improved significantly

### Phase 3: Advanced (Week 4+)

**Tasks**:
1. Introduce `TypedDict` for known dictionary structures
2. Reduce `Any` usage in internal code
3. Add `Protocol` types where beneficial
4. Review and reduce `# type: ignore` comments

**Success Criteria**:
- TypedDict used for 5+ dictionary return types
- `Any` usage reduced by ~20%
- Type safety improved across codebase

---

## 7. Testing Strategy

### Type Checking

**Before each commit**:
```bash
mypy bengal/ --show-error-codes
```

**CI Integration**:
- Add mypy to pre-commit hooks
- Fail CI if mypy errors introduced
- Track type coverage over time

### Regression Testing

- Run full test suite after each phase
- Verify no runtime behavior changes
- Check that type improvements don't break existing code

---

## 8. Risks & Mitigations

**Risk 1**: Enabling strict mypy settings reveals many errors
- **Mitigation**: Enable settings gradually, one at a time
- **Mitigation**: Use `# type: ignore` temporarily for complex cases, fix later

**Risk 2**: Type annotations reveal incorrect assumptions about types
- **Mitigation**: Review each change carefully, add tests if needed
- **Mitigation**: Use `reveal_type()` during development to verify types

**Risk 3**: Performance impact of type checking
- **Mitigation**: Type checking is compile-time only, no runtime impact
- **Mitigation**: Use `--incremental` mode for faster checks

**Risk 4**: Breaking changes for users
- **Mitigation**: All changes are internal or additive
- **Mitigation**: `py.typed` marker is backward compatible

---

## 9. Alternatives Considered

### Alternative 1: Use pyright instead of mypy

**Pros**: Faster, better error messages, better Python 3.14 support
**Cons**: Different tool, would need to migrate configuration
**Decision**: Keep mypy (already configured, team familiar)

### Alternative 2: Use Pydantic for all data structures

**Pros**: Runtime validation, better type safety
**Cons**: Heavy dependency, performance overhead, not needed for all cases
**Decision**: Use TypedDict for simple cases, keep Pydantic for complex validation

### Alternative 3: Ignore type errors with `# type: ignore`

**Pros**: Quick fix
**Cons**: Hides real issues, reduces type safety benefits
**Decision**: Fix root causes, use `# type: ignore` only when necessary

---

## 10. Success Metrics

**Quantitative**:
- Type errors reduced from ~100+ to <20
- `Any` usage reduced from 220 to <150
- Functions with missing annotations: 50+ → 0
- Type coverage: ~75% → ~90%

**Qualitative**:
- Better IDE autocomplete and type checking
- Easier refactoring with type safety
- Better code documentation via type hints
- Improved developer experience

---

## 11. References

- [PEP 561 - Distributing and Packaging Type Information](https://peps.python.org/pep-0561/)
- [PEP 484 - Type Hints](https://peps.python.org/pep-0484/)
- [PEP 544 - Protocols: Structural subtyping](https://peps.python.org/pep-0544/)
- [PEP 589 - TypedDict: Type Hints for Dictionaries with a Fixed Set of Keys](https://peps.python.org/pep-0589/)
- [mypy Documentation](https://mypy.readthedocs.io/)
- Bengal Python Style Guide: `.cursor/rules/python-style.mdc`

---

## 12. Open Questions

1. **Should we enable `strict = true` eventually?**
   - Answer: Yes, but gradually. Enable individual strict settings first.

2. **How to handle third-party libraries without type stubs?**
   - Answer: Use `# type: ignore[import-untyped]` for now, consider contributing stubs later.

3. **Should we add type checking to CI?**
   - Answer: Yes, add mypy to pre-commit hooks and CI pipeline.

4. **How to prioritize which `Any` usages to fix?**
   - Answer: Focus on public APIs first, then critical paths, then internal code.

---

**Status**: Draft  
**Next Steps**: Review and approve, then begin Phase 1 implementation
