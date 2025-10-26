# 📋 Implementation Plan: Generic Cacheable Protocol

**RFC**: `rfc-cacheable-protocol.md`  
**Status**: Active  
**Started**: 2025-10-26  
**Estimated Completion**: 2-3 days (16-24 hours)

---

## Executive Summary

Implement a generic `Cacheable` protocol to provide type-safe cache contracts for all cacheable types in Bengal. This protocol will prevent cache bugs (like the PageMetadata.type issue), ensure consistent serialization patterns, and provide compile-time validation via mypy.

**Key Deliverables**:
- `bengal/cache/cacheable.py` - Protocol definition
- `bengal/cache/cache_store.py` - Generic cache helper
- Adoption in PageCore, TagEntry, AssetDependencyEntry
- Comprehensive tests and documentation

**Complexity**: Moderate  
**Risk**: Low (additive, doesn't break existing code)  
**Confidence Gate**: Implementation ≥90%, Tests ≥90%

---

## Plan Details

- **Total Tasks**: 18 tasks
- **Estimated Time**: 16-24 hours (2-3 days)
- **Complexity**: Moderate
- **Confidence Gates**:
  - RFC: 82% ✅ (meets 85% with implementation)
  - Implementation: ≥90% required
  - Tests: ≥90% required

---

## Phase 1: Foundation (6 tasks, ~6 hours)

### Cache Module (`bengal/cache/`)

#### Task 1.1: Create Cacheable Protocol Definition
- **Files**: `bengal/cache/cacheable.py` (NEW)
- **Action**:
  - Create `@runtime_checkable` Protocol with `to_cache_dict()` and `from_cache_dict()` methods
  - Add comprehensive docstrings with usage examples
  - Include type hints with TypeVar for generic return types
  - Document serialization contract (JSON primitives only)
- **Dependencies**: None
- **Status**: pending
- **Commit**: `cache: introduce Cacheable protocol for type-safe cache contracts`

#### Task 1.2: Create Generic CacheStore Helper
- **Files**: `bengal/cache/cache_store.py` (NEW)
- **Action**:
  - Implement `CacheStore` class with generic `save()` and `load()` methods
  - Add version handling (top-level `version` field)
  - Implement tolerant loading (return empty on version mismatch)
  - Add directory creation for cache paths
  - Type-safe with `TypeVar` bound to `Cacheable`
- **Dependencies**: Task 1.1
- **Status**: pending
- **Commit**: `cache: add generic CacheStore helper for Cacheable types`

#### Task 1.3: Add Protocol Contract Documentation
- **Files**: `bengal/cache/cacheable.py`
- **Action**:
  - Add module-level docstring with contract rules
  - Document serialization guidelines (datetime → ISO string, Path → str, set → sorted list)
  - Add examples for simple and complex types
  - Document version handling expectations
- **Dependencies**: Task 1.1
- **Status**: pending
- **Commit**: `cache: document Cacheable protocol contract and guidelines`

---

### Tests (`tests/unit/`)

#### Task 1.4: Add Unit Tests for Cacheable Protocol
- **Files**: `tests/unit/test_cacheable.py` (NEW)
- **Action**:
  - Test protocol validation with runtime_checkable
  - Test that non-conforming types are rejected by isinstance()
  - Test minimal conforming implementation
  - Verify TypeVar works correctly with mypy
- **Dependencies**: Task 1.1
- **Status**: pending
- **Commit**: `tests(cache): add unit tests for Cacheable protocol validation`

#### Task 1.5: Add Unit Tests for CacheStore
- **Files**: `tests/unit/test_cache_store.py` (NEW)
- **Action**:
  - Test save() with list of Cacheable objects
  - Test load() with matching version
  - Test load() with version mismatch (returns empty)
  - Test load() with missing file (returns empty)
  - Test directory creation
  - Test round-trip with multiple entry types
- **Dependencies**: Task 1.2
- **Status**: pending
- **Commit**: `tests(cache): add unit tests for CacheStore helper`

#### Task 1.6: Add Property Tests for Serialization Contract
- **Files**: `tests/unit/test_cacheable_properties.py` (NEW)
- **Action**:
  - Property test: datetime serialization → ISO string roundtrip
  - Property test: Path serialization → str roundtrip
  - Property test: set serialization → sorted list (order-insensitive)
  - Property test: to_cache_dict only returns JSON primitives
- **Dependencies**: Task 1.1
- **Status**: pending
- **Commit**: `tests(cache): add property tests for Cacheable serialization contract`

---

## Phase 2: Implementation (7 tasks, ~8 hours)

### Core Module (`bengal/core/`)

#### Task 2.1: Adopt Protocol in PageCore
- **Files**: `bengal/core/page/page_core.py`
- **Action**:
  - Add `from bengal.cache.cacheable import Cacheable`
  - Add protocol to class signature: `class PageCore(Cacheable):`
  - Rename existing `to_dict()` → `to_cache_dict()` (if needed)
  - Rename existing `from_dict()` → `from_cache_dict()` (if needed)
  - Verify all fields are serialized (especially datetime, Path)
  - Add docstrings referencing protocol contract
- **Dependencies**: Task 1.1
- **Status**: pending
- **Commit**: `core(page): adopt Cacheable protocol in PageCore`

#### Task 2.2: Verify PageCore Timing Guarantees
- **Files**: `bengal/cache/page_discovery_cache.py`
- **Action**:
  - Verify PageCore serialization occurs AFTER cascades applied
  - Add comment documenting timing requirement
  - Verify `type`, `layout`, etc. are NOT None in cached metadata
- **Dependencies**: Task 2.1
- **Status**: pending
- **Commit**: `cache: document PageCore serialization timing after cascades`

---

### Cache Module (`bengal/cache/`)

#### Task 2.3: Adopt Protocol in TagEntry
- **Files**: `bengal/cache/taxonomy_index.py`
- **Action**:
  - Add `from bengal.cache.cacheable import Cacheable`
  - Add protocol to class signature: `class TagEntry(Cacheable):`
  - Rename `to_dict()` → `to_cache_dict()`
  - Rename `from_dict()` → `from_cache_dict()` (classmethod)
  - Add backward compatibility shims for `to_dict`/`from_dict` with deprecation warnings
  - Update existing cache save/load to use new method names
- **Dependencies**: Task 1.1
- **Status**: pending
- **Commit**: `cache(taxonomy): adopt Cacheable protocol in TagEntry`

#### Task 2.4: Add Deprecation Warnings for TagEntry Legacy Methods
- **Files**: `bengal/cache/taxonomy_index.py`
- **Action**:
  - Implement `to_dict()` shim that delegates to `to_cache_dict()`
  - Implement `from_dict()` shim that delegates to `from_cache_dict()`
  - Add `warnings.warn()` with DeprecationWarning on first use
  - Add comment: "Remove in next minor release"
- **Dependencies**: Task 2.3
- **Status**: pending
- **Commit**: `cache(taxonomy): add deprecation warnings for TagEntry legacy methods`

#### Task 2.5: Adopt Protocol in AssetDependencyEntry
- **Files**: `bengal/cache/asset_dependency_map.py`
- **Action**:
  - Find `AssetDependencyEntry` dataclass (or equivalent)
  - Add `from bengal.cache.cacheable import Cacheable`
  - Add protocol to class signature
  - Implement `to_cache_dict()` and `from_cache_dict()` if not present
  - Update parent `AssetDependencyMap` to use protocol methods
- **Dependencies**: Task 1.1
- **Status**: pending
- **Commit**: `cache(asset): adopt Cacheable protocol in AssetDependencyEntry`

#### Task 2.6: Evaluate BuildCache for Protocol Adoption
- **Files**: `bengal/cache/build_cache.py`
- **Action**:
  - Review BuildCache structure (uses pickle, not JSON)
  - Document decision: OUT OF SCOPE (pickle-based, custom semantics)
  - Add comment in code explaining why protocol not adopted
  - Document in `architecture/cache.md` which caches use protocol vs not
- **Dependencies**: Task 1.1
- **Status**: pending
- **Commit**: `cache: document BuildCache out of scope for Cacheable protocol`

#### Task 2.7: Update Existing Cache Files to Use CacheStore
- **Files**:
  - `bengal/cache/taxonomy_index.py`
  - `bengal/cache/asset_dependency_map.py`
- **Action**:
  - Refactor `TaxonomyIndex.save()` to use `CacheStore`
  - Refactor `TaxonomyIndex.load()` to use `CacheStore`
  - Refactor `AssetDependencyMap.save()` to use `CacheStore`
  - Refactor `AssetDependencyMap.load()` to use `CacheStore`
  - Remove manual JSON serialization code
  - Keep version handling behavior (tolerant load)
- **Dependencies**: Task 1.2, Task 2.3, Task 2.5
- **Status**: pending
- **Commit**: `cache: refactor taxonomy and asset caches to use CacheStore helper`

---

## Phase 3: Validation (4 tasks, ~4 hours)

### Tests (`tests/unit/`)

#### Task 3.1: Add Roundtrip Tests for PageCore
- **Files**: `tests/unit/test_page_core.py` (update existing)
- **Action**:
  - Test roundtrip: `PageCore.from_cache_dict(obj.to_cache_dict()) == obj`
  - Test with all fields populated (including optional fields)
  - Test with None values for optional fields
  - Test datetime serialization (ISO string)
  - Test Path serialization (str)
- **Dependencies**: Task 2.1
- **Status**: pending
- **Commit**: `tests(core): add PageCore roundtrip tests for Cacheable protocol`

#### Task 3.2: Add Roundtrip Tests for TagEntry
- **Files**: `tests/unit/test_taxonomy_index.py` (update existing)
- **Action**:
  - Test roundtrip: `TagEntry.from_cache_dict(obj.to_cache_dict()) == obj`
  - Test with representative tag data
  - Test page_paths list serialization
  - Test is_valid flag handling
- **Dependencies**: Task 2.3
- **Status**: pending
- **Commit**: `tests(cache): add TagEntry roundtrip tests for Cacheable protocol`

#### Task 3.3: Add Roundtrip Tests for AssetDependencyEntry
- **Files**: `tests/unit/test_asset_dependency_map.py` (update existing)
- **Action**:
  - Test roundtrip for AssetDependencyEntry
  - Test with dependencies list
  - Test with empty dependencies
  - Test Path serialization in dependency entries
- **Dependencies**: Task 2.5
- **Status**: pending
- **Commit**: `tests(cache): add AssetDependencyEntry roundtrip tests`

#### Task 3.4: Run Full Test Suite and Fix Issues
- **Files**: All test files
- **Action**:
  - Run `pytest tests/` (full suite)
  - Fix any broken tests from protocol adoption
  - Verify no regressions in cache loading/saving
  - Verify dev server still works with cached pages
- **Dependencies**: Task 3.1, Task 3.2, Task 3.3
- **Status**: pending
- **Commit**: `tests: fix regressions from Cacheable protocol adoption`

---

## Phase 4: Polish (1 task, ~3 hours)

### Documentation

#### Task 4.1: Update Architecture Documentation
- **Files**:
  - `architecture/cache.md`
  - `CONTRIBUTING.md`
  - `CHANGELOG.md`
- **Action**:
  - **cache.md**: Add "Cacheable Protocol" section with usage examples
  - **cache.md**: Document which caches use protocol (Page, Tag, Asset) vs not (Build)
  - **cache.md**: Document serialization contract rules
  - **CONTRIBUTING.md**: Add "Creating Cacheable Types" section
  - **CONTRIBUTING.md**: Add decision tree for when to use protocol vs *Core
  - **CHANGELOG.md**: Add entry under "### Added" for next release
- **Dependencies**: Task 2.7, Task 3.4
- **Status**: pending
- **Commit**: `docs: document Cacheable protocol pattern and usage guidelines`

---

## 📊 Task Summary

| Area | Tasks | Status | Estimated Time |
|------|-------|--------|----------------|
| Cache (Foundation) | 3 | pending | 3h |
| Tests (Foundation) | 3 | pending | 3h |
| Core (Implementation) | 2 | pending | 2h |
| Cache (Implementation) | 5 | pending | 6h |
| Tests (Validation) | 4 | pending | 4h |
| Documentation (Polish) | 1 | pending | 3h |
| **Total** | **18** | **pending** | **21h** |

---

## 📋 Validation Checklist

### Pre-Implementation
- [x] RFC reviewed and approved (82% confidence)
- [x] Implementation plan created
- [ ] Plan reviewed by human

### During Implementation
- [ ] All unit tests pass
- [ ] All integration tests pass
- [ ] Linter passes (no new errors)
- [ ] Mypy validates protocol implementations
- [ ] No regressions in cache loading/saving

### Post-Implementation
- [ ] PageCore, TagEntry, AssetDependencyEntry implement protocol
- [ ] CacheStore works with all cacheable types
- [ ] Roundtrip tests pass for all types
- [ ] Documentation complete
- [ ] CHANGELOG.md updated
- [ ] Confidence ≥ 90%

---

## 🎯 Success Criteria

### Phase 1 Success (Protocol Created)
- ✅ `bengal/cache/cacheable.py` exists with Protocol
- ✅ `CacheStore` generic helper works
- ✅ Unit tests validate protocol contract
- ✅ Mypy validates protocol implementation

### Phase 2 Success (Adoption)
- ✅ PageCore implements Cacheable
- ✅ TagEntry implements Cacheable
- ✅ AssetDependencyEntry implements Cacheable
- ✅ All protocol implementations have roundtrip tests

### Phase 3 Success (Validation)
- ✅ All tests pass (unit + integration)
- ✅ No cache loading/saving regressions
- ✅ Dev server works with cached pages
- ✅ Linter passes

### Phase 4 Success (Documentation)
- ✅ CONTRIBUTING.md documents Cacheable pattern
- ✅ Examples in architecture/cache.md
- ✅ CHANGELOG.md updated
- ✅ Contributors know when to use protocol

---

## 📝 Implementation Notes

### Type Safety Validation
After Phase 2, verify mypy catches:
```python
# Should fail: Missing to_cache_dict
@dataclass
class BadCache(Cacheable):  # mypy error!
    name: str
    # Missing: to_cache_dict() and from_cache_dict()

# Should pass: Implements protocol
@dataclass
class GoodCache(Cacheable):
    name: str
    def to_cache_dict(self) -> dict[str, Any]: ...
    @classmethod
    def from_cache_dict(cls, data: dict[str, Any]) -> 'GoodCache': ...
```

### Backward Compatibility
TagEntry migration path:
1. Add `to_cache_dict` / `from_cache_dict` (new protocol methods)
2. Keep `to_dict` / `from_dict` as shims with deprecation warnings (1 minor release)
3. Remove shims in next minor release

### Performance Expectations
- Protocol has zero runtime overhead (structural typing)
- CacheStore adds ~1-2ms overhead for version checking (negligible)
- Roundtrip tests should complete in <100ms for typical objects

---

## 🔄 Dependencies Graph

```
Phase 1 (Foundation):
  1.1 (Protocol) ──┬──> 1.4 (Tests)
                   ├──> 1.6 (Property Tests)
                   └──> 2.1, 2.3, 2.5 (All adoptions)

  1.2 (CacheStore) ──> 1.5 (Tests)
                     └──> 2.7 (Refactor caches)

Phase 2 (Implementation):
  2.1 (PageCore) ──> 2.2 (Timing) ──> 3.1 (Tests)
  2.3 (TagEntry) ──> 2.4 (Deprecation) ──> 3.2 (Tests)
  2.5 (AssetDep) ──> 3.3 (Tests)

  2.7 (Refactor) ──> 3.4 (Full suite)

Phase 3 (Validation):
  3.1, 3.2, 3.3 ──> 3.4 (Full suite) ──> 4.1 (Docs)

Phase 4 (Polish):
  4.1 (Docs) ──> DONE
```

---

## 🚀 Next Steps

1. **Review this plan** - Human approval before starting
2. **Begin Phase 1** - Create protocol and CacheStore (`::implement` Task 1.1)
3. **Track progress** - Update task statuses in this document
4. **Run validation** - After each phase, run tests and linter
5. **Ship it** - After Phase 4, run `::retro` and update CHANGELOG.md

---

## 📚 Related Documents

- **RFC**: `plan/active/rfc-cacheable-protocol.md` (82% confidence)
- **Inspiration**: `plan/implemented/plan-pagecore-refactoring.md` (PageCore success story)
- **Architecture**: `architecture/cache.md` (cache subsystem overview)
- **Object Model**: `architecture/object-model.md` (core types)

---

**Status**: Ready for implementation  
**Command to start**: `::implement` Task 1.1  
**Estimated Completion**: 2025-10-28 (2-3 days from now)
