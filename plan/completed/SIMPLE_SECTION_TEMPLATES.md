# Simple Section Templates - Ergonomic Design

**Date:** October 4, 2025  
**Goal:** More ergonomic than Hugo, more powerful than cascade  
**Status:** Design exploration

---

## 🎯 The Core Problem

**What we really need:**
1. One config controls entire section tree
2. No repetition in subsections
3. Clear, obvious behavior
4. Simple mental model

**What we DON'T necessarily need:**
- Hugo's 8-level fallback chain
- Complex list/single distinction
- Multiple template directories per section

---

## 💡 Proposal 1: "Deep Cascade" (Simplest)

### Make Cascade Apply to Subsection Indexes

**Change one thing:** Cascade now applies to `_index.md` files in subsections too!

```yaml
# content/docs/_index.md
---
template: docs.html  # This page
cascade:
  template: docs.html  # All children AND subsection indexes!
---
```

**Result:**
```
content/docs/_index.md        → docs.html ✅ (explicit)
content/docs/page1.md         → docs.html ✅ (cascade)
content/docs/api/_index.md    → docs.html ✅ (cascade - NEW!)
content/docs/api/page1.md     → docs.html ✅ (cascade)
```

**Pros:**
- ✅ Minimal change (one line of code)
- ✅ No new concepts
- ✅ Solves repetition problem
- ✅ Obvious behavior

**Cons:**
- ⚠️ Can't distinguish list vs single
- ⚠️ All pages use same template
- ⚠️ What if you want different template for section index?

### Variant: Cascade with Exceptions

```yaml
# content/docs/_index.md
---
template: docs-list.html  # This page only
cascade:
  template: docs.html     # Everything else
  except_index: true      # Don't apply to _index.md
---
```

**Pros:**
- ✅ Simple
- ✅ One file controls tree
- ✅ Can distinguish index pages

**Cons:**
- ⚠️ Still need explicit template on this page
- ⚠️ New concept (except_index)

---

## 💡 Proposal 2: "Template Pairs" (Middle Ground)

### One Setting, Two Templates

```yaml
# content/docs/_index.md
---
templates:
  index: docs-list.html
  page: docs.html
---
```

**That's it!** Applies to entire tree.

**Result:**
```
content/docs/_index.md        → docs-list.html ✅
content/docs/page1.md         → docs.html ✅
content/docs/api/_index.md    → docs-list.html ✅
content/docs/api/page1.md     → docs.html ✅
```

**Pros:**
- ✅ One config file
- ✅ Clear distinction (index vs page)
- ✅ No directory structure needed
- ✅ Easy to understand

**Cons:**
- ⚠️ New frontmatter structure
- ⚠️ More complex than simple cascade

**Shorter syntax:**
```yaml
---
templates: docs-list.html, docs.html  # index, page
---
```

---

## 💡 Proposal 3: "Section Config" (Most Flexible)

### Dedicated Section Config File

**New file:** `content/docs/.section.yaml`

```yaml
# content/docs/.section.yaml
templates:
  index: docs-list.html
  page: docs.html

# Optional metadata
title: "Documentation"
description: "Complete docs"

# Optional cascade for other metadata
cascade:
  author: "Docs Team"
  category: "Documentation"
```

**Pros:**
- ✅ Separate config from content
- ✅ Clear purpose
- ✅ One file per section (like .gitignore)
- ✅ Doesn't clutter _index.md

**Cons:**
- ⚠️ New file type
- ⚠️ More complex
- ⚠️ Another thing to learn

---

## 💡 Proposal 4: "Smart Defaults" (Zero Config)

### Convention Over Configuration

**Simple rule:** If template has same name as section, auto-use it!

```
templates/
  └── docs.html    ← Auto-used by content/docs/**

content/
  └── docs/
      ├── _index.md    → docs.html ✅
      ├── page1.md     → docs.html ✅
      └── api/
          ├── _index.md → docs.html ✅
          └── page1.md  → docs.html ✅
```

**For index pages:** Try `docs-list.html` first, fallback to `docs.html`

```
templates/
  ├── docs-list.html  ← Used by _index.md files
  └── docs.html       ← Used by regular pages

# OR just use one template for both!
templates/
  └── docs.html       ← Used by everything
```

**Pros:**
- ✅ ZERO config needed
- ✅ Convention-based (obvious)
- ✅ Simple naming pattern
- ✅ Easy to override (cascade still works)

**Cons:**
- ⚠️ Implicit behavior (magic)
- ⚠️ What if template doesn't match section name?

---

## 💡 Proposal 5: "Glob Patterns in Config" (Power Users)

### Use bengal.toml for Section Rules

```toml
# bengal.toml
[[sections]]
path = "docs/**"
templates = { index = "docs-list.html", page = "docs.html" }

[[sections]]
path = "docs/api/**"
templates = { index = "api-list.html", page = "api.html" }  # Override

[[sections]]
path = "blog/**"
templates = { page = "post.html" }
```

**Pros:**
- ✅ Centralized config
- ✅ Powerful glob patterns
- ✅ Easy to see all rules
- ✅ Override subsections easily

**Cons:**
- ⚠️ Config file grows
- ⚠️ Separated from content
- ⚠️ More to learn

---

## 🎯 My Recommendation: Proposal 2 + 4

### Combine "Template Pairs" + "Smart Defaults"

**For zero-config cases:**
```
templates/
  └── docs.html    ← Auto-used by content/docs/**
```

**For control:**
```yaml
# content/docs/_index.md
---
templates:
  index: docs-list.html
  page: docs.html
---
```

### Implementation

```python
def _get_template_name(self, page: Page) -> str:
    # 1. Explicit template in frontmatter
    if 'template' in page.metadata:
        return page.metadata['template']
    
    # 2. Template pairs in section _index.md
    if page.section and page.section.metadata.get('templates'):
        templates = page.section.metadata['templates']
        
        # Support both dict and string formats
        if isinstance(templates, dict):
            if page.source_path.stem == '_index':
                return templates.get('index', templates.get('page'))
            else:
                return templates.get('page', templates.get('index'))
        elif isinstance(templates, str):
            # Simple case: one template for all
            return templates
    
    # 3. Smart default: section name
    if page.section:
        section_name = page.section.name
        
        # Try index-specific template first
        if page.source_path.stem == '_index':
            index_template = f"{section_name}-list.html"
            if self._template_exists(index_template):
                return index_template
        
        # Try section template
        section_template = f"{section_name}.html"
        if self._template_exists(section_template):
            return section_template
    
    # 4. Type-based fallback
    # ... existing logic
```

### Usage Examples

**Example 1: Zero Config (Simple Site)**
```
templates/
  ├── docs.html
  └── blog.html

content/
  ├── docs/    ← Auto-uses docs.html
  └── blog/    ← Auto-uses blog.html
```

**No frontmatter needed!** ✨

**Example 2: Index vs Page Distinction**
```
templates/
  ├── docs-list.html
  └── docs.html

content/docs/_index.md  → docs-list.html (auto!)
content/docs/page.md    → docs.html (auto!)
```

**Still no frontmatter!** ✨

**Example 3: Explicit Control**
```yaml
# content/docs/_index.md
---
templates:
  index: custom-list.html
  page: docs.html
---
```

**Example 4: Override Subsection**
```yaml
# content/docs/api/_index.md
---
templates:
  index: api-list.html
  page: api.html
---
```

---

## 📊 Comparison

| Approach | Config Lines | Flexibility | Simplicity | Hugo-like |
|----------|-------------|-------------|------------|-----------|
| Current Cascade | 4 per subsection | Medium | High | No |
| Deep Cascade | 3 total | Low | Very High | No |
| Template Pairs | 4 total | High | Medium | Somewhat |
| Section Config | N/A (separate file) | Very High | Medium | No |
| Smart Defaults | 0 | Medium | Very High | Somewhat |
| Glob Config | N/A (toml) | Very High | Medium | No |
| **Hybrid (2+4)** | **0-4** | **High** | **High** | **Yes** |

---

## 🎨 Mental Model Comparison

### Hugo
```
"Where's my template coming from?"
→ Check 8 places
→ Complex lookup order
→ Directory structure matters
→ Naming conventions matter
→ Hard to debug
```

### Proposed (Smart Defaults + Pairs)
```
"Where's my template coming from?"
→ Check frontmatter? No
→ Section has templates config? No
→ templates/[section].html exists? Yes!
→ Done! ✅

Simple, clear, obvious.
```

---

## ✅ Implementation Plan

### Phase 1: Smart Defaults (Zero Config)

```python
# Try section-name.html and section-name-list.html
if page.section:
    if is_index and template_exists(f"{section}-list.html"):
        return f"{section}-list.html"
    if template_exists(f"{section}.html"):
        return f"{section}.html"
```

**Result:** Most sites need ZERO config!

### Phase 2: Template Pairs (Control)

```python
# Support templates in section metadata
if page.section.metadata.get('templates'):
    return resolve_template_pair(...)
```

**Result:** Power users can control index vs page!

### Phase 3: Documentation

```markdown
# Template Selection

## Zero Config (Just Works!)
Create: templates/docs.html
Result: All /docs/ pages use it automatically!

## Index vs Page (Optional)
Create: templates/docs-list.html (for _index.md)
Create: templates/docs.html (for pages)

## Manual Control (If Needed)
# _index.md
---
templates:
  index: custom.html
  page: docs.html
---
```

---

## 🎯 Key Advantages

### 1. **Progressive Disclosure**
```
Beginner: Zero config → works!
Intermediate: Add -list.html variant → works!
Advanced: Explicit templates in frontmatter → full control!
```

### 2. **Clear Naming Convention**
```
docs.html        → Regular pages in /docs/
docs-list.html   → Index pages in /docs/
docs-api.html    → Override for specific section
```

### 3. **No Hidden Magic**
```
Template name matches section name
└─ Obvious!
```

### 4. **Flexible When Needed**
```
Can override at any level:
- Whole section (templates config)
- Subsection (templates config)
- Single page (template: explicit)
```

---

## 💭 Addressing Concerns

### "Is this too implicit?"

**Answer:** No more than CSS!
```
.docs { ... }  ← Applies to class="docs"
docs.html      ← Applies to content/docs/
```

Both are convention-based and obvious.

### "What if I don't want this behavior?"

**Answer:** Just use explicit templates or cascade!
```yaml
---
template: custom.html  # Always works
---
```

### "How do I debug template selection?"

**Answer:** Add logging!
```bash
bengal build --verbose

docs/page1.md → docs.html (smart default)
docs/_index.md → docs-list.html (smart default)
docs/special.md → custom.html (explicit)
```

---

## 🎉 Final Proposal

### Smart Defaults + Template Pairs

**Priority Order:**
```
1. Explicit (template: custom.html)
2. Template Pairs (templates: {...})
3. Smart Defaults (section-name.html)
4. Type-based (type: post)
5. Default (page.html)
```

**Zero Config Example:**
```
templates/
  ├── docs.html
  └── docs-list.html

content/docs/
  ├── _index.md    → docs-list.html ✨
  ├── page1.md     → docs.html ✨
  └── api/
      ├── _index.md → docs-list.html ✨
      └── page1.md  → docs.html ✨
```

**Controlled Example:**
```yaml
# content/docs/_index.md
---
templates:
  index: toc.html
  page: article.html
---
```

**One-off Example:**
```yaml
# content/docs/special.md
---
template: landing.html
---
```

---

## ✅ Summary

**Simpler than Hugo:**
- ✅ No 8-level fallback chain
- ✅ Obvious naming convention
- ✅ Clear mental model

**More powerful than cascade:**
- ✅ No repetition in subsections
- ✅ Can distinguish index vs page
- ✅ Zero config for common cases

**More ergonomic than both:**
- ✅ Progressive disclosure
- ✅ Convention-based with escape hatches
- ✅ Clear, debuggable

**What do you think?** 🎯

This gives you:
1. Zero config for simple cases
2. Simple override for control
3. Full power when needed
4. Clear, obvious behavior

Is this the sweet spot? 🤔

