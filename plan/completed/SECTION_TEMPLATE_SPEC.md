# Section-Based Template Auto-Detection - Implementation Spec

**Date:** October 4, 2025  
**Status:** ✅ Approved - Ready for Implementation  
**Complexity:** Low (~1 hour)

---

## 🎯 Goal

Enable automatic template selection based on section names, eliminating repetitive cascade configuration while keeping system simple and predictable.

---

## 📐 Design Principles

1. **Root = Default** - No `_default/` directory needed
2. **Flexible Organization** - Support flat OR directory structure
3. **Progressive Disclosure** - Zero config works, power users can customize
4. **Hugo-Compatible** - Familiar patterns for Hugo users
5. **Simple > Complex** - Fewer layers, clearer behavior

---

## 🗂️ Template Structure

### Supported Patterns

**Pattern 1: Flat (Simple)**
```
templates/
  ├── page.html          ← Default for all pages
  ├── index.html         ← Default for section indexes
  ├── docs.html          ← Used by content/docs/**/*.md
  └── docs-list.html     ← Used by content/docs/**/_index.md
```

**Pattern 2: Directory (Organized)**
```
templates/
  ├── page.html          ← Default for all pages
  ├── index.html         ← Default for section indexes
  └── docs/
      ├── single.html    ← Used by content/docs/**/*.md
      └── list.html      ← Used by content/docs/**/_index.md
```

**Pattern 3: Mixed (Flexible)**
```
templates/
  ├── page.html
  ├── index.html
  ├── blog.html          ← Simple section, flat style
  └── docs/              ← Complex section, directory style
      ├── single.html
      └── list.html
```

---

## 🔍 Template Lookup Order

### For Regular Pages (e.g., `content/docs/page.md`)

```
1. Explicit frontmatter
   template: custom.html
   
2. Section directory (Hugo-style)
   templates/docs/single.html
   
3. Section directory (alternative naming)
   templates/docs/page.html
   
4. Section flat
   templates/docs.html
   
5. Type-based
   type: post → templates/post.html
   
6. Default fallback
   templates/page.html
```

### For Section Indexes (e.g., `content/docs/_index.md`)

```
1. Explicit frontmatter
   template: custom.html
   
2. Section directory (Hugo-style)
   templates/docs/list.html
   
3. Section directory (alternative naming)
   templates/docs/index.html
   
4. Section flat with suffix
   templates/docs-list.html
   
5. Section flat (simple)
   templates/docs.html
   
6. Default fallback
   templates/index.html
```

---

## 💻 Implementation

### File: `bengal/rendering/renderer.py`

**Modify:** `_get_template_name(self, page: Page) -> str`

```python
def _get_template_name(self, page: Page) -> str:
    """
    Determine which template to use for a page.
    
    Priority:
    1. Explicit template in frontmatter
    2. Section-based auto-detection (directory or flat)
    3. Type-based template
    4. Default fallback
    """
    # 1. Explicit template (highest priority)
    if 'template' in page.metadata:
        return page.metadata['template']
    
    # 2. Section-based auto-detection
    if page.section:
        section_name = page.section.name
        is_section_index = page.source_path.stem == '_index'
        
        if is_section_index:
            # Try section index templates
            templates_to_try = [
                f"{section_name}/list.html",      # Hugo-style
                f"{section_name}/index.html",     # Alternative
                f"{section_name}-list.html",      # Flat with suffix
                f"{section_name}.html",           # Flat simple
            ]
        else:
            # Try section page templates
            templates_to_try = [
                f"{section_name}/single.html",    # Hugo-style
                f"{section_name}/page.html",      # Alternative
                f"{section_name}.html",           # Flat
            ]
        
        # Check if any template exists
        for template_name in templates_to_try:
            if self._template_exists(template_name):
                return template_name
    
    # 3. Type-based fallback
    if page.source_path.stem == '_index':
        # Section index without custom template
        return 'index.html'
    
    page_type = page.metadata.get('type', 'page')
    template_map = {
        'post': 'post.html',
        'page': 'page.html',
        'index': 'index.html',
    }
    
    return template_map.get(page_type, 'page.html')

def _template_exists(self, template_name: str) -> bool:
    """
    Check if a template exists in any template directory.
    
    Args:
        template_name: Template filename or path
        
    Returns:
        True if template exists, False otherwise
    """
    try:
        self.template_engine.env.get_template(template_name)
        return True
    except Exception:
        return False
```

---

## 🧪 Test Cases

### Test 1: Zero Config (Defaults)
```
templates/page.html exists
content/docs/page1.md → page.html ✅
content/blog/post1.md → page.html ✅
```

### Test 2: Flat Section Template
```
templates/docs.html exists
content/docs/page1.md → docs.html ✅
content/docs/api/page2.md → docs.html ✅ (inherited!)
```

### Test 3: Directory Structure
```
templates/docs/single.html exists
content/docs/page1.md → docs/single.html ✅
```

### Test 4: Index vs Single
```
templates/docs/list.html exists
templates/docs/single.html exists
content/docs/_index.md → docs/list.html ✅
content/docs/page1.md → docs/single.html ✅
```

### Test 5: Flat with Suffix
```
templates/docs-list.html exists
templates/docs.html exists
content/docs/_index.md → docs-list.html ✅
content/docs/page1.md → docs.html ✅
```

### Test 6: Explicit Override
```
templates/docs.html exists
content/docs/special.md (template: custom.html) → custom.html ✅
```

### Test 7: Cascade Still Works
```yaml
# content/docs/_index.md
---
cascade:
  template: doc-custom.html
---

content/docs/page1.md → doc-custom.html ✅ (cascade wins over auto)
```

**Wait, cascade should be checked!** Let me revise...

Actually, looking at the code, cascade is applied to `page.metadata` before template selection, so:
- If cascade sets `template` in metadata → it becomes "explicit" (priority 1)
- Auto-detection only happens if no explicit template in metadata
- ✅ Cascade already works correctly!

---

## 📊 Migration Examples

### Before (Cascade Repetition)

```yaml
# content/docs/_index.md
---
template: doc.html
cascade:
  template: doc.html
---

# content/docs/api/_index.md
---
template: doc.html
cascade:
  template: doc.html
---

# content/docs/guides/_index.md
---
template: doc.html
cascade:
  template: doc.html
---
```

**12 lines of frontmatter!** 😰

### After (Auto-Detection)

```
templates/
  └── docs.html

content/docs/
  ├── _index.md          ← No frontmatter needed! ✨
  ├── api/_index.md      ← No frontmatter needed! ✨
  └── guides/_index.md   ← No frontmatter needed! ✨
```

**0 lines of frontmatter!** 🎉

---

## 🎨 User Experience

### Beginner Flow
```
1. Create content/docs/page.md
2. Run bengal build
3. Uses templates/page.html (default)
→ Works immediately!
```

### Intermediate Flow
```
1. Create templates/docs.html
2. Create content/docs/page.md
3. Run bengal build
4. Uses templates/docs.html (auto-detected!)
→ Zero config needed!
```

### Advanced Flow
```
1. Create templates/docs/single.html
2. Create templates/docs/list.html
3. Create content/docs/_index.md
4. Create content/docs/page.md
5. Run bengal build
6. _index.md uses list.html, page.md uses single.html
→ Full control, still automatic!
```

### Power User Flow
```yaml
# Need special template for one page
---
template: custom.html
---
→ Explicit override always wins!
```

---

## 📋 Implementation Checklist

### Phase 1: Core Implementation
- [ ] Add `_template_exists()` helper method
- [ ] Update `_get_template_name()` with section detection
- [ ] Test all lookup patterns
- [ ] Verify cascade still works
- [ ] Verify explicit templates still work

### Phase 2: Documentation
- [ ] Update architecture docs
- [ ] Add template organization guide
- [ ] Create migration examples
- [ ] Document naming conventions
- [ ] Add troubleshooting section

### Phase 3: Developer Experience
- [ ] Add verbose logging (show which template was selected)
- [ ] Consider `bengal templates list` command
- [ ] Add warning if template expected but not found
- [ ] Update error messages

---

## 🚀 Future Enhancements (Optional)

### Enhancement 1: Template Discovery Command
```bash
bengal templates list

Available templates:
  docs.html          → content/docs/**/*.md (flat style)
  blog/single.html   → content/blog/**/*.md (directory style)
  blog/list.html     → content/blog/**/_index.md (directory style)
  page.html          → default fallback
  index.html         → section index fallback
```

### Enhancement 2: Verbose Build Output
```bash
bengal build --verbose

Rendering content/docs/page1.md
  ✓ Using template: docs.html (section auto-detection)

Rendering content/blog/post.md
  ✓ Using template: post.html (type: post)
```

### Enhancement 3: Template Validation
```bash
bengal check

⚠️  content/api/ has no matching template
    Suggestion: Create templates/api.html or templates/api/single.html
```

---

## ✅ Benefits Summary

**For Users:**
- ✅ Zero config for simple cases
- ✅ No repetitive cascade declarations
- ✅ Intuitive naming (section → template)
- ✅ Flexible organization (flat or directory)
- ✅ Easy to override when needed

**For Bengal:**
- ✅ Competitive with Hugo (better DX)
- ✅ Simpler than Hugo (no 8-level lookup)
- ✅ Backwards compatible (cascade still works)
- ✅ Easy to implement (~30 lines of code)
- ✅ Easy to document (clear convention)

---

## 🎯 Success Criteria

**Must have:**
- ✅ Section name → template name mapping works
- ✅ Directory and flat styles both work
- ✅ Cascade/explicit still override auto-detection
- ✅ Backwards compatible (no breaking changes)
- ✅ Clear, predictable behavior

**Nice to have:**
- ✅ Hugo-compatible naming (list.html, single.html)
- ✅ Alternative naming (index.html, page.html)
- ✅ Verbose logging option
- ✅ Template discovery command

---

## 📝 Documentation Needed

### 1. Template Organization Guide
```markdown
# Template Organization

## Quick Start
Create templates/[section].html to apply to all pages in that section.

## Advanced
Create templates/[section]/single.html for pages
Create templates/[section]/list.html for indexes
```

### 2. Migration Guide
```markdown
# Migrating from Cascade

Before:
```yaml
cascade:
  template: docs.html
```

After:
Just create templates/docs.html - automatic!
```

### 3. Troubleshooting
```markdown
## Template not being used?

Check priority order:
1. Explicit template in frontmatter
2. Section-based auto-detection
3. Type-based
4. Default

Use --verbose to see which template was selected.
```

---

## 🎉 Conclusion

This feature provides:
- **Zero-config** convenience (like Hugo)
- **Simple** mental model (simpler than Hugo)
- **Flexible** organization (user's choice)
- **Backwards compatible** (everything still works)
- **Easy to implement** (minimal code changes)

**Status:** ✅ Ready for implementation

**Estimated effort:** 1-2 hours
- Core implementation: 30 minutes
- Testing: 30 minutes
- Documentation: 30-60 minutes

**Risk:** Low (backwards compatible, additive only)

---

**Let's ship it!** 🚀

