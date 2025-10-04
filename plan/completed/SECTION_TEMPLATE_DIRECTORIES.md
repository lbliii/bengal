# Section-Based Template Directories - Design Proposal

**Date:** October 4, 2025  
**Issue:** Cascade requires repeating config in subsections  
**Status:** Design Proposal

---

## 🐛 The Problem

User: **"I think they'd have to declare it all the way down the tree? Whereas docs/list.html tells the system every list for docs type = that layout"**

### Scenario

You want:
- Different template for section indexes (list pages)
- Different template for regular pages (single pages)
- Applied to ENTIRE section tree (including subsections)

### Current Solution (Cascade)

```yaml
# content/docs/_index.md
---
template: docs-list.html
cascade:
  template: docs-single.html
---

# content/docs/api/_index.md
---
template: docs-list.html      # ⚠️ Must repeat!
cascade:
  template: docs-single.html  # ⚠️ Must repeat!
---

# content/docs/api/v2/_index.md
---
template: docs-list.html      # ⚠️ Must repeat again!
cascade:
  template: docs-single.html  # ⚠️ Must repeat again!
---
```

**Problem:** 
- ❌ Repetitive
- ❌ Error-prone
- ❌ Hard to maintain
- ❌ Doesn't cascade to subsection indexes

---

## 🎯 Hugo's Solution

### Directory Structure
```
templates/
  └── docs/
      ├── list.html      ← Used for ALL _index.md in docs/**
      └── single.html    ← Used for ALL pages in docs/**
```

### How It Works

```python
def _get_template_name(self, page: Page) -> str:
    # 1. Check if in a section
    if page.section:
        section_name = page.section.name  # e.g., "docs"
        
        # 2. Determine page type
        if page.source_path.stem == "_index":
            # Section index
            template = f"{section_name}/list.html"
        else:
            # Regular page
            template = f"{section_name}/single.html"
        
        # 3. Check if template exists
        if template_exists(template):
            return template
    
    # 4. Fall back to current logic
    return current_logic()
```

### Result

```
content/docs/_index.md           → docs/list.html ✅
content/docs/page1.md            → docs/single.html ✅
content/docs/api/_index.md       → docs/list.html ✅ (automatic!)
content/docs/api/page1.md        → docs/single.html ✅ (automatic!)
content/docs/api/v2/_index.md    → docs/list.html ✅ (automatic!)
```

**No repetition needed!** 🎉

---

## 🎨 Proposed Implementation

### Enhanced Template Lookup

**New Priority Order:**

```
1. Explicit frontmatter (template: custom.html)
2. Cascade from _index.md
3. Section-based directory lookup ← NEW!
   - For _index.md: templates/[section]/list.html
   - For pages: templates/[section]/single.html
4. Type-based (type: post → post.html)
5. Default fallback (page.html)
```

### Code Changes

**File:** `bengal/rendering/renderer.py`

```python
def _get_template_name(self, page: Page) -> str:
    """
    Determine which template to use for a page.
    
    Priority:
    1. Explicit template in frontmatter
    2. Cascade from section _index.md
    3. Section-based template directory
    4. Type-based template
    5. Default fallback
    """
    # 1. Explicit template (highest priority)
    if 'template' in page.metadata:
        return page.metadata['template']
    
    # 2. Check if this is an _index.md file
    is_section_index = page.source_path.stem == '_index'
    
    # 3. NEW: Section-based template directory lookup
    if page.section:
        section_name = page.section.name
        
        # Determine template name based on page type
        if is_section_index:
            section_template = f"{section_name}/list.html"
        else:
            section_template = f"{section_name}/single.html"
        
        # Check if template exists
        if self._template_exists(section_template):
            return section_template
    
    # 4. Legacy: Direct section template (backward compat)
    if page.section:
        legacy_template = f"{page.section.name}.html"
        if self._template_exists(legacy_template):
            return legacy_template
    
    # 5. Type-based fallback
    if is_section_index:
        return 'index.html'
    
    page_type = page.metadata.get('type', 'page')
    template_map = {
        'post': 'post.html',
        'page': 'page.html',
        'index': 'index.html',
        'doc': 'doc.html',
    }
    
    type_template = template_map.get(page_type, 'page.html')
    return type_template

def _template_exists(self, template_name: str) -> bool:
    """Check if a template exists in any template directory."""
    try:
        self.template_engine.env.get_template(template_name)
        return True
    except Exception:
        return False
```

---

## 📊 Comparison

### Example Site Structure

```
content/
  └── docs/
      ├── _index.md
      ├── getting-started.md
      └── api/
          ├── _index.md
          ├── authentication.md
          └── v2/
              ├── _index.md
              └── endpoints.md
```

### Approach 1: Current (Cascade)

**Config needed:**
```yaml
# content/docs/_index.md (4 lines)
---
template: docs-list.html
cascade:
  template: docs-single.html
---

# content/docs/api/_index.md (4 lines)
---
template: docs-list.html
cascade:
  template: docs-single.html
---

# content/docs/api/v2/_index.md (4 lines)
---
template: docs-list.html
cascade:
  template: docs-single.html
---
```

**Total: 12 lines of frontmatter**

### Approach 2: Section-Based Directories

**Templates:**
```
templates/
  └── docs/
      ├── list.html    ← Define once
      └── single.html  ← Define once
```

**Config needed:**
```yaml
# content/docs/_index.md (0 lines)
# content/docs/api/_index.md (0 lines)
# content/docs/api/v2/_index.md (0 lines)
```

**Total: 0 lines of frontmatter** ✨

---

## 💡 Hybrid Approach (Best of Both)

### Use Both Systems!

**Priority:**
1. Explicit template → Full control
2. Cascade → Section-level override
3. **Section directory** → Automatic for whole tree
4. Type → Fallback
5. Default → Final fallback

### Example

**Case 1: Simple site (use directories)**
```
templates/
  ├── docs/
  │   ├── list.html
  │   └── single.html
  └── blog/
      ├── list.html
      └── single.html

content/
  ├── docs/...    ← Auto-uses docs/* templates
  └── blog/...    ← Auto-uses blog/* templates
```

**Zero config!** ✨

**Case 2: Need override (use cascade)**
```yaml
# content/docs/api/_index.md
---
cascade:
  template: api-doc.html  # Override for this subsection only
---
```

**Case 3: One-off (use explicit)**
```yaml
# content/docs/special.md
---
template: landing.html  # This page only
---
```

**All three work together!** 🎉

---

## 🚀 Migration Path

### Backwards Compatible

**Existing sites keep working:**
```yaml
# Old approach still works
---
cascade:
  template: doc.html
---
```

**New approach is optional:**
```
# Add these for automatic behavior
templates/docs/list.html
templates/docs/single.html
```

**No breaking changes!**

---

## 📋 Implementation Checklist

### Phase 1: Core Logic (1 hour)
- [ ] Add `_template_exists()` helper
- [ ] Add section directory lookup
- [ ] Add list/single detection
- [ ] Maintain backward compatibility

### Phase 2: Testing (30 min)
- [ ] Test with section directories
- [ ] Test with cascade (still works)
- [ ] Test with explicit (still works)
- [ ] Test priority order

### Phase 3: Documentation (30 min)
- [ ] Update template selection docs
- [ ] Add section directory examples
- [ ] Migration guide from cascade
- [ ] Best practices guide

---

## 🎯 Benefits

### For Users

✅ **Zero config for simple cases**
```
Just create templates/docs/single.html
All docs pages automatically use it!
```

✅ **No repetition in subsections**
```
One template pair controls entire tree
```

✅ **Still explicit when needed**
```
Can override with cascade or frontmatter
```

✅ **Hugo-compatible**
```
Familiar pattern for Hugo users
```

### For Bengal

✅ **Additive, not breaking**
```
Existing sites keep working
```

✅ **Reduces support burden**
```
Less "how do I apply templates to all pages?" questions
```

✅ **Competitive with Hugo**
```
Matches Hugo's convenience
```

✅ **Simple to implement**
```
~30 lines of code
```

---

## 🤔 Potential Issues

### Issue 1: Section Nesting

**Question:** What if subsection should use different template?

**Answer:** Use cascade override
```yaml
# content/docs/api/_index.md
---
cascade:
  template: api-specific.html  # Overrides section default
---
```

### Issue 2: Template Discovery

**Question:** How do users know what templates are available?

**Answer:** Add CLI command
```bash
bengal templates list

Available templates:
  docs/list.html    → Used by: content/docs/**/_index.md
  docs/single.html  → Used by: content/docs/**/page.md
  blog/list.html    → Used by: content/blog/**/_index.md
  blog/single.html  → Used by: content/blog/**/page.md
  page.html         → Default fallback
```

### Issue 3: Naming Conventions

**Question:** Why list.html and single.html?

**Answer:** Hugo convention, but we could also support:
- `list.html` / `single.html` (Hugo-style)
- `index.html` / `page.html` (Jekyll-style)
- `section.html` / `page.html` (Alternative)

---

## ✅ Recommendation

### YES - Implement Section Directories

**Reasons:**
1. ✅ Solves real problem (subsection repetition)
2. ✅ Hugo-compatible pattern
3. ✅ Reduces config burden
4. ✅ Backwards compatible
5. ✅ Simple to implement
6. ✅ Natural progression from cascade

### Priority Order (Final)

```
1. Explicit template (template: custom.html)
   ↓
2. Cascade from _index.md (cascade.template)
   ↓
3. Section directory templates (docs/list.html, docs/single.html) ← NEW!
   ↓
4. Type-based (type: post → post.html)
   ↓
5. Default (page.html)
```

---

## 🎉 Example in Action

### Before (Current - Repetitive)

```yaml
# content/docs/_index.md
---
template: docs-list.html
cascade:
  template: docs-single.html
---

# content/docs/api/_index.md
---
template: docs-list.html      # Repeat!
cascade:
  template: docs-single.html  # Repeat!
---

# content/docs/guides/_index.md
---
template: docs-list.html      # Repeat!
cascade:
  template: docs-single.html  # Repeat!
---
```

### After (With Section Directories - Zero Config)

```
templates/
  └── docs/
      ├── list.html
      └── single.html

content/
  └── docs/
      ├── _index.md            ← Uses docs/list.html ✨
      ├── page1.md             ← Uses docs/single.html ✨
      ├── api/
      │   ├── _index.md        ← Uses docs/list.html ✨
      │   └── endpoints.md     ← Uses docs/single.html ✨
      └── guides/
          ├── _index.md        ← Uses docs/list.html ✨
          └── tutorial.md      ← Uses docs/single.html ✨
```

**Zero frontmatter needed!** 🎉

---

## 💭 Conclusion

**You're absolutely right!** The cascade approach requires repetition in subsections. Section-based template directories solve this elegantly.

**My revised position:**
- ✅ **Implement section directories** (solves real problem)
- ✅ **Keep cascade** (works great for overrides)
- ✅ **Keep explicit** (full control when needed)
- ✅ **All three work together** (progressive disclosure)

**This is actually a good addition** that solves a real pain point without adding much complexity.

**Worth implementing?** I think so! 🚀

