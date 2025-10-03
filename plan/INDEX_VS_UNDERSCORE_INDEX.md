# index.md vs _index.md - Bengal's Approach

## Current Behavior

Bengal currently treats **both** `index.md` and `_index.md` identically:

```python
# bengal/core/section.py:131
if page.source_path.stem in ("index", "_index"):
    self.index_page = page
    
    # Extract cascade metadata from index page for inheritance
    if 'cascade' in page.metadata:
        self.metadata['cascade'] = page.metadata['cascade']
```

Both files:
- ✅ Become the section's index page
- ✅ Can define cascade metadata
- ✅ Render to `index.html`
- ✅ Inherit from parent cascades

## Hugo's Convention (for reference)

In Hugo, there's a semantic difference:

| File | Purpose | Behavior |
|------|---------|----------|
| `index.md` | **Page bundle** (leaf bundle) | Regular content page, NOT a section |
| `_index.md` | **Section index** (branch bundle) | Section with children, supports cascade |

**Hugo Example:**
```
content/
  docs/
    _index.md        # Section index with cascade
    installation/
      index.md       # Leaf page (no children)
    configuration/
      _index.md      # Section with subsections
      basic.md
      advanced.md
```

## Bengal's Simpler Approach

**Bengal doesn't enforce this distinction** - both work the same way. This is simpler but potentially confusing for Hugo users.

### Current Usage in Examples

```
examples/quickstart/content/
  index.md                    # Root index
  docs/
    index.md                  # Docs section index
  api/
    v2/
      _index.md              # API v2 section (with cascade)
```

**We've been inconsistent!** Some use `index.md`, some use `_index.md`, but both work.

## Recommendation

### Option 1: Keep Simple (Current Behavior) ✅

**Pros:**
- Simpler for users
- Both files work identically
- Less to document

**Cons:**
- Inconsistent with Hugo
- May confuse Hugo migrants
- No clear convention

### Option 2: Enforce Hugo Convention

Make `_index.md` required for sections with cascade:

```python
if page.source_path.stem == "_index":
    # This is a section index - enable cascade
    self.index_page = page
    if 'cascade' in page.metadata:
        self.metadata['cascade'] = page.metadata['cascade']
        
elif page.source_path.stem == "index":
    # This is a regular page, not a section
    self.index_page = page
    # Don't process cascade
```

**Pros:**
- Consistent with Hugo
- Clear semantic meaning
- Better for documentation structure

**Cons:**
- Breaking change
- More rules to learn
- Not necessary for Bengal's architecture

### Option 3: Document Current Behavior ✅ (BEST)

**Keep both working** but establish a convention in docs:

**Convention:**
- Use `_index.md` for **section indexes** (especially with cascade)
- Use `index.md` for **standalone pages** or **simple sections**

**Rationale:**
- Backwards compatible
- Works like users expect
- Adds clarity without breaking changes
- Hugo users feel at home

## Decision

**✅ Keep current behavior, document the convention**

### Documentation Update Needed:

1. **Cascading Frontmatter docs** - Show `_index.md` for sections
2. **Getting Started** - Clarify when to use each
3. **Examples** - Use `_index.md` consistently for cascade sections

### Example Documentation:

```markdown
## Section Index Files

Bengal supports two types of index files:

### `_index.md` - Section Index (Recommended for Sections)
Use for sections that contain other pages or define cascades:

```
content/
  docs/
    _index.md     # Section index with cascade
    page1.md
    page2.md
```

### `index.md` - Page Index (Standalone Pages)
Use for the site root or standalone pages:

```
content/
  index.md        # Site homepage
  about.md
```

**Both work identically in Bengal** - use whichever you prefer, but `_index.md` 
is recommended for sections with cascade to match Hugo conventions.
```

## Action Items

- [x] Clarify current behavior
- [ ] Update cascading frontmatter docs
- [ ] Update examples to use `_index.md` for cascade sections
- [ ] Add to documentation guide

