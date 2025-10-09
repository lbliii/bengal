# Type System - Immediate Next Steps

**Status**: Core implementation complete ✅  
**Priority**: Get to usable MVP  
**Timeline**: 1-2 weeks

## What We Have Now ✅

1. ✅ Type-based template selection working
2. ✅ Type mappings (python-module, cli-command, doc, tutorial, blog)
3. ✅ Cascade support
4. ✅ API/CLI reference templates with sidebar
5. ✅ Fallback chain working

## What We Need for MVP

The minimum to ship this feature confidently:

### 🎯 Priority 1: Essential Templates (3-4 days)

**Goal**: Every type in the mapping should have working templates.

#### A. Tutorial Templates
- [ ] `templates/tutorial/list.html` - Grid of tutorials with difficulty badges
- [ ] `templates/tutorial/single.html` - Step-by-step layout with prev/next
- [ ] Basic styling in `components/tutorial.css`

**Why**: We say `type: tutorial` works, but there's no `tutorial/` templates yet.

#### B. Blog Templates  
- [ ] `templates/blog/list.html` - Reverse-chrono with featured
- [ ] `templates/blog/single.html` - Article layout
- [ ] Basic styling in `components/blog.css`

**Why**: Blog is a core use case, should have templates.

#### C. Doc Template Refactor
- [ ] Move `doc.html` → `doc/single.html` 
- [ ] Move `docs.html` → `doc/list.html`
- [ ] Create aliases for backward compatibility
- [ ] Test that `type: doc` works

**Why**: Make the naming consistent with the other types.

### 🎯 Priority 2: Documentation (2-3 days)

**Goal**: Users know about and can use the type system.

#### A. User Guide
Create `docs/CONTENT_TYPES.md`:
```markdown
# Content Types in Bengal

## Quick Start
Set content type in _index.md:
...

## Available Types
- doc, tutorial, blog, api-reference, cli-reference

## Cascading Types
...

## Common Patterns
...
```

#### B. Update Existing Docs
- [ ] Add type section to `TEMPLATES.md`
- [ ] Add type examples to `GETTING_STARTED.md`
- [ ] Update `bengal.toml.example` with type examples

#### C. Inline Code Documentation
- [ ] Add docstring examples to `_get_template_name()`
- [ ] Document type_mappings dict

### 🎯 Priority 3: Testing (1-2 days)

**Goal**: Confidence that it works correctly.

#### A. Critical Test Cases
- [ ] Test type → template mapping
- [ ] Test cascade inheritance
- [ ] Test template override beats type
- [ ] Test fallback to section name
- [ ] Test unknown types

#### B. Integration Tests
- [ ] Build a site with `type: doc` cascade
- [ ] Build a site with mixed types
- [ ] Verify correct templates used

### 🎯 Priority 4: Enhanced Showcase (1 day)

**Goal**: Working example people can reference.

#### A. Add Type to Showcase
Update `examples/showcase/`:
- [ ] Add `type: doc` with cascade to docs/_index.md
- [ ] Add tutorials/ section with `type: tutorial`
- [ ] Add blog/ section with `type: blog`
- [ ] Verify build works

#### B. Document Showcase
- [ ] README explaining what each section demonstrates
- [ ] Comments in _index.md files

## What Can Wait

These are important but not blockers:

### Later: CLI Scaffolding
- `bengal new section --type doc`
- Can be added after MVP

### Later: Advanced Templates
- Landing page templates
- Advanced blog features
- Can iterate after release

### Later: Video Tutorial
- Nice to have
- Can create after stable release

### Later: Validation & Warnings
- Helpful but not critical
- Add in maintenance release

## Definition of Done

The type system MVP is ready when:

1. ✅ All 5 types have working templates
2. ✅ Documentation explains the system clearly
3. ✅ Tests verify it works correctly
4. ✅ Showcase demonstrates real usage
5. ✅ Backward compatible (existing sites work)
6. ✅ No major bugs reported

## Action Plan: Next Session

Here's exactly what to do next:

### Session 1: Tutorial Templates (2-3 hours)
1. Create `templates/tutorial/` directory
2. Create `list.html` - copy from archive.html, adapt
3. Create `single.html` - linear layout with prev/next
4. Add basic CSS for tutorial styling
5. Test with example tutorial content

### Session 2: Blog Templates (2-3 hours)
1. Create `templates/blog/` directory
2. Create `list.html` - reverse-chrono with featured
3. Create `single.html` - article layout
4. Add basic CSS for blog styling
5. Test with example blog posts

### Session 3: Doc Refactor (1-2 hours)
1. Move `doc.html` → `doc/single.html`
2. Move `docs.html` → `doc/list.html`
3. Create `doc.html` alias → extends `doc/single.html`
4. Create `docs.html` alias → extends `doc/list.html`
5. Test backward compatibility

### Session 4: Documentation (2-3 hours)
1. Write `CONTENT_TYPES.md`
2. Update `TEMPLATES.md`
3. Add examples to `GETTING_STARTED.md`
4. Update code docstrings

### Session 5: Testing (2 hours)
1. Write template selection tests
2. Write cascade tests
3. Write integration tests
4. Run full test suite

### Session 6: Showcase (1 hour)
1. Update showcase with types
2. Add README documentation
3. Build and verify
4. Take screenshots for docs

## Quick Wins

Start with these for immediate value:

1. **Tutorial list template** - Copy/adapt from archive.html (30 min)
2. **Update TEMPLATES.md** - Add type section (30 min)
3. **Add tests** - Template selection tests (1 hour)

These prove the concept and build momentum.

## Questions Before Starting

1. **Design aesthetic** - Should tutorial/blog templates match default theme style?
   - Recommendation: Yes, consistent with current design system
   
2. **Breaking changes** - OK to move doc.html to doc/single.html?
   - Recommendation: Yes, but keep aliases for compatibility
   
3. **Scope** - Minimal viable templates or full-featured?
   - Recommendation: Minimal for MVP, iterate based on feedback

4. **Testing depth** - Unit tests only or also integration?
   - Recommendation: Both, but prioritize template selection unit tests

## Success Metrics

After MVP launch, measure:
- **Adoption**: How many users set `type:` in frontmatter?
- **Feedback**: What do users say about the feature?
- **Issues**: What bugs/confusion arise?
- **Templates**: Are all types being used or just some?

Use this data to prioritize Phase 2 improvements.

## Communication Plan

When ready to ship:
1. Blog post explaining the feature
2. Update changelog
3. Tweet/social media announcement
4. Example sites
5. Consider "Featured" label in docs

## MVP Target: 1-2 Weeks

**Week 1:**
- Days 1-3: Templates (tutorial, blog, doc refactor)
- Days 4-5: Documentation

**Week 2:**
- Days 1-2: Testing
- Day 3: Showcase updates
- Days 4-5: Polish, bug fixes, release prep

After this, the type system is ready for users! 🚀

