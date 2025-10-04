# Architecture Recommendation - Section Index System

**Date:** October 4, 2025  
**Status:** Recommendation for long-term fix

---

## 🎯 TL;DR

**Current Problem:** Section index generation is brittle due to architectural issues  
**Root Cause:** Mixing concerns (taxonomies vs structure) + implicit contracts + no validation  
**Recommendation:** Add `SectionOrchestrator` with explicit lifecycle phases

---

## 📊 Current Architecture Issues

### 1. **Semantic Misplacement**
Archives (section indexes) live in `TaxonomyOrchestrator` alongside tags/categories.
- ❌ Archives are **structural** (part of section hierarchy)
- ❌ Tags are **cross-cutting** (span multiple sections)
- ❌ These are fundamentally different concerns mixed together

### 2. **Implicit Contracts**
No explicit guarantee that sections are navigable:
```python
section.url  # Might work, might return 404!
```

### 3. **Discovery vs Rendering Gap**
```
Discovery → Sections created (incomplete)
    ↓
??? (gap where sections fall through)
    ↓
Taxonomy → Maybe creates archives (wrong logic!)
    ↓
Render → Too late to fix
```

### 4. **No Validation**
Build succeeds even with broken URLs. Silent failures everywhere.

---

## ✅ Recommended Architecture: Hybrid Approach

### The Pattern

**Orchestrators coordinate, Objects manage themselves:**

```python
class Section:
    """Sections know HOW to validate/complete themselves."""
    
    def needs_auto_index(self) -> bool:
        """Section decides if it needs an index."""
        return self.name != 'root' and not self.index_page
    
    def create_auto_index(self, site) -> Page:
        """Section knows HOW to create its index."""
        # ...
    
    def validate(self) -> List[str]:
        """Section knows HOW to validate itself."""
        # ...


class SectionOrchestrator:
    """Orchestrator coordinates WHEN to do things."""
    
    def finalize_sections(self):
        """Coordinate section completion."""
        for section in self.site.sections:
            if section.needs_auto_index():
                index = section.create_auto_index(self.site)
                self.site.pages.append(index)
    
    def validate_sections(self) -> List[str]:
        """Coordinate validation."""
        errors = []
        for section in self.site.sections:
            errors.extend(section.validate())
        return errors


class BuildOrchestrator:
    """Explicit lifecycle phases."""
    
    def build(self):
        # Phase 1: Discovery
        self.content.discover()
        
        # Phase 2: Complete sections (NEW!)
        self.sections.finalize_sections()
        
        # Phase 3: Validate (NEW!)
        errors = self.sections.validate_sections()
        if errors and strict_mode:
            raise BuildValidationError(errors)
        
        # Phase 4: Taxonomies (only tags now!)
        self.taxonomy.collect_and_generate_taxonomies()
        
        # Phase 5: Render
        self.render.process(self.site.pages)
```

---

## 🏗️ New Build Pipeline

```
┌─────────────────────────────────────────┐
│ Phase 1: Discovery                      │
│ - Find content files                    │
│ - Create Section/Page objects          │
│ - Sections may not have index_page yet │
└─────────────────────────────────────────┘
                  ↓
┌─────────────────────────────────────────┐
│ Phase 2: Section Finalization (NEW!)   │
│ - For each section:                     │
│   - If no index_page, create archive    │
│   - Recursively finalize subsections    │
│ - All sections now have index_page      │
└─────────────────────────────────────────┘
                  ↓
┌─────────────────────────────────────────┐
│ Phase 3: Validation (NEW!)              │
│ - Verify all sections have indexes      │
│ - Check URLs resolve correctly          │
│ - Fail fast in --strict mode            │
└─────────────────────────────────────────┘
                  ↓
┌─────────────────────────────────────────┐
│ Phase 4: Taxonomies                     │
│ - Collect tags/categories               │
│ - Generate tag pages (ONLY tags now!)   │
│ - No more archive generation here       │
└─────────────────────────────────────────┘
                  ↓
┌─────────────────────────────────────────┐
│ Phase 5: Render                         │
│ - Render all pages (including archives) │
│ - All section URLs guaranteed valid     │
└─────────────────────────────────────────┘
```

---

## 💡 Why This Architecture?

### Principles Applied

1. **Separation of Concerns**
   - `SectionOrchestrator`: Structural hierarchy
   - `TaxonomyOrchestrator`: Cross-cutting taxonomies
   - Clear boundaries

2. **Explicit Contracts**
   - Every section MUST have index page
   - Enforced by finalization phase
   - Validated before rendering

3. **Fail Fast**
   - Validation between phases
   - Errors caught early (not at runtime)
   - --strict mode for CI/CD

4. **Object Responsibility**
   - Sections know how to validate themselves
   - Orchestrators coordinate when
   - Clear division of labor

5. **No Gaps**
   - Explicit lifecycle: discover → finalize → validate → render
   - No incomplete intermediate states
   - All pages accounted for

---

## 📋 Implementation Checklist

### Week 1: Core Implementation
- [ ] Create `bengal/orchestration/section.py`
- [ ] Implement `SectionOrchestrator` class
- [ ] Add `finalize_sections()` method
- [ ] Add `validate_sections()` method
- [ ] Move archive generation from `TaxonomyOrchestrator`
- [ ] Update `BuildOrchestrator` to use new orchestrator
- [ ] Add validation phase with --strict mode support

### Week 2: Testing & Documentation
- [ ] Add unit tests for `SectionOrchestrator`
- [ ] Add integration tests for section lifecycle
- [ ] Test validation and error reporting
- [ ] Update `ARCHITECTURE.md`
- [ ] Update user documentation
- [ ] Add examples of section behavior

### Week 3: Polish & Deploy
- [ ] Add health check for section indexes
- [ ] Performance testing
- [ ] Code review
- [ ] Merge to main
- [ ] Release notes

---

## 📐 Code Organization

```
bengal/
  orchestration/
    build.py              ← Update: add section phase
    content.py            ← Unchanged
    section.py            ← NEW: Section lifecycle
    taxonomy.py           ← Update: remove archive generation
    menu.py               ← Unchanged
    render.py             ← Unchanged
    ...
  
  core/
    section.py            ← Update: add needs_auto_index(), validate()
    page.py               ← Unchanged
    ...
```

---

## 🎯 Success Metrics

After implementation:

- [ ] ✅ No sections without index pages
- [ ] ✅ All section URLs resolve correctly
- [ ] ✅ Build fails fast in --strict mode if issues found
- [ ] ✅ Clear separation: structural vs taxonomies
- [ ] ✅ 100% test coverage for section lifecycle
- [ ] ✅ Hugo-compatible behavior
- [ ] ✅ Zero silent failures

---

## 🔄 Migration Impact

### Breaking Changes
- **None for users** - Internal architecture only

### New Features
- ✅ All sections get index pages automatically
- ✅ --strict mode validates section structure
- ✅ Better error messages for missing indexes
- ✅ Health check for section validity

### Performance Impact
- **Negligible** - One extra pass over sections during build
- Validation is O(n) where n = number of sections
- Typical sites: < 100 sections = < 1ms overhead

---

## 🎓 Architectural Benefits

### Maintainability
- Clear separation of concerns
- Each orchestrator has one job
- Easy to understand and modify

### Testability
- Sections validate themselves (unit testable)
- Orchestrators coordinate (integration testable)
- Mock-friendly design

### Extensibility
- Easy to add new section types
- Plugin hooks for section finalization
- Custom validation rules possible

### Robustness
- Fail fast with validation
- Explicit lifecycle phases
- No silent failures

### Hugo Compatibility
- Matches Hugo's behavior
- All sections get list pages
- Migration from Hugo works correctly

---

## 🚀 Next Steps

1. **Review this recommendation** - Does the architecture make sense?
2. **Approve implementation** - Green light to proceed?
3. **Set priority** - Immediate fix or next sprint?

**Timeline:** 2-3 weeks total (1 week implementation, 1 week testing, 1 week polish)

**Effort:** ~40-60 hours total

**Risk:** Low (internal refactoring, no breaking changes)

**Value:** High (fixes critical bug + improves architecture long-term)

---

## 📚 Related Documents

- `/plan/SECTION_INDEX_MISSING_ISSUE.md` - Bug analysis and immediate fix
- `/plan/BRITTLENESS_ANALYSIS.md` - Why the current design is brittle
- `/plan/SECTION_ARCHITECTURE_ANALYSIS.md` - Detailed architecture comparison
- `/ARCHITECTURE.md` - Current system architecture overview

