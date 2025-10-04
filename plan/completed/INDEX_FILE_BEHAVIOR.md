# Index File Behavior Analysis

**Date:** October 4, 2025  
**Issue:** Conflicting `_index.md` and `index.md` in same directory

---

## 🐛 Current Behavior (Problematic)

### What's Happening

In `/content/docs/`, you have **TWO** index files:
1. `_index.md` - Contains cascade config
2. `index.md` - Contains actual content

**Current code** (`bengal/core/section.py:139-145`):
```python
def add_page(self, page: Page) -> None:
    self.pages.append(page)
    
    # Set as index page if it's named index.md or _index.md
    if page.source_path.stem in ("index", "_index"):
        self.index_page = page
        
        # Extract cascade metadata from index page for inheritance
        if 'cascade' in page.metadata:
            self.metadata['cascade'] = page.metadata['cascade']
```

**Problem:** 
- ❌ **No explicit precedence** - whichever file is processed LAST becomes `section.index_page`
- ❌ Files are processed in filesystem order (typically alphabetical)
- ❌ `_index.md` comes first alphabetically
- ❌ `index.md` comes second → **OVERWRITES** `_index.md` as the index page
- ❌ Result: `index.md` content is used, BUT cascade from `_index.md` is already applied

### Current Output

**What's being rendered:**
- ✅ URL: `/docs/` (correct)
- ✅ Content: From `index.md` (has actual content)
- ✅ Cascade: From `_index.md` (was applied to child pages)
- ⚠️ **BUT** `_index.md` content is **ignored** (overwritten)

---

## 📊 How Other SSGs Handle This

### Hugo's Approach (Standard)

**Files:**
- `_index.md` - **Section index** (list/landing page for section)
- `index.md` - **NOT ALLOWED** in same directory (or treated as regular page)

**Behavior:**
```
content/
  └── docs/
      ├── _index.md        ← Section index at /docs/
      ├── page1.md         ← Regular page at /docs/page1/
      └── page2.md         ← Regular page at /docs/page2/
```

**Rule:** 
- ✅ `_index.md` is ALWAYS the section index
- ✅ `index.md` is typically not used in sections
- ✅ Clear, explicit naming convention

---

### Jekyll's Approach

**Files:**
- `index.md` - Index page
- No `_index.md` concept (prefixed with `_` are ignored)

**Rule:**
- ✅ Simple: `index.md` is the index
- ✅ No conflicts possible

---

### 11ty's Approach

**Files:**
- Both could exist
- Uses template precedence and pagination

**Rule:**
- ⚠️ Complex - multiple files can render to same URL
- ⚠️ Relies on template engine

---

## 🎯 Recommended Solution

### Option 1: **Hugo-Style Precedence** (Recommended)

Establish clear precedence: `_index.md` > `index.md`

```python
def add_page(self, page: Page) -> None:
    self.pages.append(page)
    
    # Set as index page with clear precedence
    if page.source_path.stem == "_index":
        # _index.md is ALWAYS the section index (highest priority)
        self.index_page = page
        
        # Extract cascade metadata
        if 'cascade' in page.metadata:
            self.metadata['cascade'] = page.metadata['cascade']
    
    elif page.source_path.stem == "index" and not self.index_page:
        # index.md is fallback ONLY if no _index.md exists
        self.index_page = page
```

**Benefits:**
- ✅ Clear, explicit precedence
- ✅ Hugo-compatible
- ✅ No surprises
- ✅ `_index.md` always wins
- ✅ Backwards compatible (if only one exists)

---

### Option 2: **Warn on Conflict** (Additional)

Add validation to warn users:

```python
def add_page(self, page: Page) -> None:
    self.pages.append(page)
    
    if page.source_path.stem in ("index", "_index"):
        # Check for conflict
        if self.index_page and self.index_page.source_path.stem != page.source_path.stem:
            print(f"⚠️  Warning: Multiple index files in {self.path}:")
            print(f"   - {self.index_page.source_path.name}")
            print(f"   - {page.source_path.name}")
            print(f"   Using: _index.md (has priority)")
        
        # Apply precedence
        if page.source_path.stem == "_index":
            self.index_page = page
        elif page.source_path.stem == "index" and not self.index_page:
            self.index_page = page
        
        # Extract cascade
        if 'cascade' in page.metadata:
            self.metadata['cascade'] = page.metadata['cascade']
```

**Benefits:**
- ✅ Users are informed
- ✅ Clear what's happening
- ✅ Helps debugging

---

### Option 3: **Treat as Separate** (Alternative)

Treat `_index.md` as section config only, not a page:

```python
def add_page(self, page: Page) -> None:
    if page.source_path.stem == "_index":
        # _index.md is section metadata/config only
        # Extract metadata and cascade but don't render as a page
        self.metadata.update(page.metadata)
        if 'cascade' in page.metadata:
            self.metadata['cascade'] = page.metadata['cascade']
        
        # Don't add to pages list (it's config, not content)
        return
    
    # Add regular pages (including index.md)
    self.pages.append(page)
    
    if page.source_path.stem == "index":
        self.index_page = page
```

**Benefits:**
- ✅ Clear separation of concerns
- ✅ `_index.md` = config
- ✅ `index.md` = content
- ⚠️ Breaking change (if people expect `_index.md` to render)

---

## 💡 Immediate Fix for Your Site

### Recommended: Keep Only `index.md`

Since `index.md` has the actual content:

```bash
# Move cascade to index.md
# Delete _index.md
```

**Update `index.md`:**
```yaml
---
title: "Documentation"
type: page
template: doc.html
description: "Complete documentation for Bengal SSG features and capabilities"
cascade:
  template: doc.html  # ← Add this
---
```

Then delete `_index.md`.

---

### Alternative: Use Only `_index.md`

If you prefer the Hugo pattern:

```bash
# Copy content from index.md to _index.md
# Delete index.md
```

**Benefit:** Clear Hugo-compatible pattern

---

## 🎯 Long-term Solution

### Implement Clear Precedence

**Update `bengal/core/section.py`:**

```python
def add_page(self, page: Page) -> None:
    """
    Add a page to this section.
    
    Index page precedence:
    1. _index.md (highest - section index)
    2. index.md (fallback - if no _index.md)
    """
    self.pages.append(page)
    
    # Handle index pages with explicit precedence
    if page.source_path.stem == "_index":
        # _index.md ALWAYS becomes the section index
        if self.index_page and self.index_page.source_path.stem == "index":
            # Warn if overriding index.md
            print(f"ℹ️  Using _index.md as section index (ignoring index.md)")
        
        self.index_page = page
        
        # Extract cascade metadata
        if 'cascade' in page.metadata:
            self.metadata['cascade'] = page.metadata['cascade']
    
    elif page.source_path.stem == "index":
        # index.md is fallback ONLY if no _index.md
        if not self.index_page:
            self.index_page = page
        elif self.index_page.source_path.stem != "_index":
            # Another index.md? This shouldn't happen
            print(f"⚠️  Warning: Multiple index files without _index.md")
```

---

## 📊 Summary

| Scenario | Current Behavior | Recommended Behavior |
|----------|-----------------|---------------------|
| Only `_index.md` | ✅ Works | ✅ Works (section index) |
| Only `index.md` | ✅ Works | ✅ Works (fallback) |
| Both files | ⚠️ Last one wins | ✅ `_index.md` wins |
| Cascade in `_index.md` | ✅ Applied | ✅ Applied |
| Content in `index.md` | ✅ Rendered | ⚠️ Ignored if `_index.md` exists |

---

## ✅ Recommendation

### Immediate (Your Site):
**Merge the files** - Put cascade in `index.md` and delete `_index.md`

```yaml
# content/docs/index.md
---
title: "Documentation"
type: page
template: doc.html
description: "Complete documentation for Bengal SSG features and capabilities"
cascade:
  template: doc.html  # ← Moved from _index.md
---

# Content here...
```

### Long-term (Bengal Core):
**Implement clear precedence** - `_index.md` always wins (Hugo-compatible)

This makes the behavior:
- ✅ Predictable
- ✅ Hugo-compatible
- ✅ Well-documented
- ✅ No surprises

---

**Current Status:** 
- ⚠️ Your site has conflicting files
- ⚠️ `index.md` is being used (alphabetical order)
- ⚠️ `_index.md` content is ignored
- ✅ Cascade from `_index.md` is applied (works by chance)

**Action Required:**
Merge the files or implement precedence logic.

