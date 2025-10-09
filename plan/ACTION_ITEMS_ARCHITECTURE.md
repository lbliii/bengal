# Action Items: Architecture Improvements

Based on comprehensive analysis in `ARCHITECTURE_ANALYSIS_2024.md`

## ✅ Completed (Today)

1. **Fixed toc_items temporal coupling bug**
   - Don't cache empty results
   - Allow re-evaluation after toc is set
   - Status: ✅ FIXED + TESTED

2. **Added BUILD LIFECYCLE documentation**
   - Updated Page class docstring
   - Added phase markers in pipeline.py
   - Added usage comments in content.py
   - Status: ✅ COMPLETE

3. **Created comprehensive test suite**
   - 15 tests for TOC extraction
   - Covers mistune, python-markdown, edge cases
   - Status: ✅ COMPLETE

4. **Documented lessons learned**
   - Created LESSONS_LEARNED_TOC_BUG.md
   - Identified anti-patterns to avoid
   - Status: ✅ COMPLETE

5. **Analyzed entire codebase for similar issues**
   - Reviewed all 35-40 @property uses
   - Checked all caching patterns
   - Audited lifecycle dependencies
   - Status: ✅ COMPLETE
   - **Result: No other issues found** 🎉

## 🔄 High Priority (Recommended Next Steps)

### 1. Create BUILD_PIPELINE.md Architecture Document
**Effort**: 1-2 hours  
**Impact**: High (prevents future confusion)  
**Assignee**: TBD

**Content**:
- Visual data flow diagram
- Detailed phase descriptions
- Property availability matrix
- Common patterns and anti-patterns
- Code examples

**Why**: Makes build lifecycle explicit for new contributors and prevents similar bugs.

### 2. Add Integration Tests for Build Lifecycle
**Effort**: 2-3 hours  
**Impact**: High (prevents regressions)  
**Assignee**: TBD

**Tests to add**:
```python
# tests/integration/test_build_lifecycle.py

def test_page_properties_available_after_discovery():
    """Properties from metadata/content available after discovery."""
    page = create_test_page()
    assert page.title
    assert page.slug
    assert page.date

def test_page_properties_available_after_parsing():
    """Properties from parsing available after process_page."""
    page = create_test_page()
    pipeline.process_page(page)
    assert page.toc
    assert page.parsed_ast
    assert len(page.toc_items) > 0

def test_toc_items_not_cached_when_empty():
    """Ensure toc_items doesn't cache empty results."""
    page = create_test_page()
    items1 = page.toc_items  # Should return []
    page.toc = "<div>...</div>"  # Set toc
    items2 = page.toc_items  # Should extract structure
    assert len(items2) > 0
```

**Why**: Catches lifecycle issues before they reach production.

### 3. Add to Contributor Guidelines
**Effort**: 30 minutes  
**Impact**: Medium (helps new contributors)  
**Assignee**: TBD

**Add section**: "Working with Page Properties"
- When properties are available
- How to add new properties safely
- Anti-patterns to avoid
- Link to BUILD_PIPELINE.md

**Why**: Prevents future developers from repeating the same mistake.

## 🔄 Medium Priority (Consider)

### 4. Build Phase Enum (Optional)
**Effort**: 3-4 hours  
**Impact**: Medium (better debugging)  
**Tradeoff**: Adds complexity

```python
class BuildPhase(Enum):
    DISCOVERY = auto()
    PARSING = auto()
    RENDERING = auto()
    COMPLETE = auto()

# Add to Page
_build_phase: BuildPhase = BuildPhase.DISCOVERY

# Use in properties for warnings
if self._build_phase < BuildPhase.PARSING:
    logger.warning("toc_items accessed before parsing")
```

**Pros**:
- Makes phases explicit in code
- Can add runtime checks
- Better debugging/logging

**Cons**:
- Adds state to Page objects
- Requires updates in orchestration
- May impact performance

**Decision**: DEFER - Monitor for additional issues first

### 5. Property Access Logging (Dev Mode)
**Effort**: 2-3 hours  
**Impact**: Low (debugging only)

Add logging to properties when accessed at unexpected times:
```python
@property
def toc_items(self):
    if not self.toc and os.getenv('BENGAL_DEBUG'):
        logger.warning(f"toc_items accessed before toc set: {self.source_path}")
    # ... rest of property
```

**Why**: Helps catch issues during development without adding production overhead.

**Decision**: DEFER - Wait for more data

## 🟢 Low Priority (Nice to Have)

### 6. Visual Property Access Matrix
**Effort**: 1-2 hours  
**Impact**: Low (documentation only)

Create table/diagram showing:
```
Property          | Discovery | Parsing | Rendering
------------------|-----------|---------|----------
title             | ✅        | ✅      | ✅
content           | ✅        | ✅      | ✅
toc               | ❌        | ✅      | ✅
toc_items         | 🟡 empty  | ✅      | ✅
parsed_ast        | ❌        | ✅      | ✅
rendered_html     | ❌        | ❌      | ✅
```

**Why**: Quick reference for developers.

**Decision**: DEFER - Include in BUILD_PIPELINE.md if time permits

### 7. Property Naming Convention
**Effort**: Minimal (documentation)  
**Impact**: Low (clarity)

Establish convention:
- `computed_X` = Recomputes each access
- `cached_X` = Uses @cached_property
- `lazy_X` = May re-evaluate based on deps

**Why**: Makes behavior more predictable.

**Decision**: DEFER - Current names are clear enough

## 📊 Summary

### Work Status
- ✅ **Completed**: 5 items (critical bug fix + documentation)
- 🔄 **Recommended**: 3 items (2-4 hours total)
- 🟢 **Optional**: 4 items (5-8 hours total)

### Priority Matrix
```
Impact ↑
  │
H │  ✅ Fix bug         🔄 BUILD_PIPELINE.md
  │  ✅ Document        🔄 Integration tests
  │
M │                     🟢 Build phase enum
  │                     🟢 Dev mode logging
  │
L │                     🟢 Access matrix
  │                     🟢 Naming convention
  │
  └─────────────────────────────────────→ Effort
     Low (< 2h)        Medium (2-4h)     High (4h+)
```

### Recommendation
**Do the 3 high-priority items (4-5 hours total) in next sprint.**

The analysis found **no additional bugs**, so the urgency is low. The recommended items are preventative measures that will improve long-term maintainability.

## 🎯 Success Criteria

### Short Term (Next Sprint)
- [ ] CREATE: `docs/architecture/BUILD_PIPELINE.md`
- [ ] ADD: Integration tests for build lifecycle
- [ ] UPDATE: Contributor guidelines with property patterns

### Medium Term (Next Quarter)
- [ ] DECIDE: Whether to add build phase enum
- [ ] REVIEW: Any new property patterns
- [ ] MEASURE: Zero lifecycle-related bugs

### Long Term (Ongoing)
- [ ] MAINTAIN: Documentation stays current
- [ ] REVIEW: New properties follow patterns
- [ ] MONITOR: No temporal coupling issues

## 📈 Expected Outcomes

1. **Fewer Bugs**: Integration tests catch lifecycle issues
2. **Faster Onboarding**: Clear documentation helps new contributors
3. **Better Debugging**: When issues occur, easier to diagnose
4. **Maintainability**: Codebase easier to reason about
5. **Confidence**: Changes less likely to introduce subtle bugs

## 🔗 Related Documents

- `ARCHITECTURE_ANALYSIS_2024.md` - Full analysis
- `LESSONS_LEARNED_TOC_BUG.md` - Detailed lessons from bug
- `TOC_ENHANCEMENT_COMPLETE.md` - What was built
- `tests/unit/rendering/test_toc_extraction.py` - Test suite

---

**Last Updated**: 2024-10-08  
**Next Review**: After completing high-priority items

