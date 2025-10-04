# Template Selection Analysis & Proposal

**Date:** October 4, 2025  
**Status:** Analysis & Recommendations

---

## 🎯 Current State

### Bengal's Current Template Selection Logic

Located in `bengal/rendering/renderer.py` → `_get_template_name()`:

```python
def _get_template_name(self, page: Page) -> str:
    # 1. Check page metadata for custom template
    if 'template' in page.metadata:
        return page.metadata['template']
    
    # 2. Check if this is an _index.md file (section index)
    if page.source_path.stem == '_index':
        return 'index.html'
    
    # 3. Check page type
    page_type = page.metadata.get('type', 'page')
    
    # 4. Map types to templates
    template_map = {
        'post': 'post.html',
        'page': 'page.html',
        'index': 'index.html',
    }
    
    return template_map.get(page_type, 'page.html')
```

### Current Priority Order
1. **Explicit template** (`template: doc.html`) - Highest priority
2. **File type** (`_index.md` → `index.html`)
3. **Content type** (`type: post` → `post.html`)
4. **Default** (`page.html`) - Fallback

---

## 📊 Comparison with Other SSGs

### Hugo's Approach (Most Sophisticated)

**Lookup Order:**
```
1. /layouts/[section]/[layout].[type].html
2. /layouts/[section]/[type].html
3. /layouts/[section]/list.html (for section indexes)
4. /layouts/[section]/single.html (for pages)
5. /layouts/_default/[type].html
6. /layouts/_default/list.html
7. /layouts/_default/single.html
```

**Features:**
- ✅ Section-based auto-selection (`/docs/` → `layouts/docs/single.html`)
- ✅ Type fallback (`type: post` → `layouts/post/single.html`)
- ✅ Default fallback (`layouts/_default/single.html`)
- ✅ List vs Single distinction
- ✅ Custom layouts (`layout: special`)
- ⚠️ Complex - can be hard to debug
- ⚠️ Lots of magic

**Example:**
```
content/docs/getting-started.md
  ↓
1. Check: layouts/docs/single.html ✅ FOUND
2. Use this template
```

---

### Jekyll's Approach (Simple + Config)

**Lookup Order:**
```
1. Frontmatter: layout: my-layout
2. Default from _config.yml
3. Fallback to default layout
```

**Configuration:**
```yaml
# _config.yml
defaults:
  - scope:
      path: "docs"
    values:
      layout: "documentation"
  - scope:
      path: ""
      type: "posts"
    values:
      layout: "post"
```

**Features:**
- ✅ Simple, explicit
- ✅ Configuration-driven
- ✅ Path-based defaults
- ⚠️ Less automatic
- ⚠️ Requires configuration

---

### 11ty's Approach (Data Cascade)

**Lookup Order:**
```
1. Frontmatter: layout: my-layout
2. Directory data file (docs/docs.json)
3. Template chain data
4. Default
```

**Directory Data:**
```json
// content/docs/docs.json
{
  "layout": "documentation",
  "tags": ["docs"]
}
```

**Features:**
- ✅ Very flexible
- ✅ Cascading data files
- ✅ Can be per-directory
- ⚠️ Complex mental model
- ⚠️ Multiple files to manage

---

### VitePress / Astro (Modern Approach)

**Lookup Order:**
```
1. Explicit layout in frontmatter
2. Directory-based layout detection
3. Default layout
```

**Features:**
- ✅ Simple, automatic
- ✅ Convention over configuration
- ✅ Fast to use
- ⚠️ Less flexible

---

## 💡 Proposed Enhancement for Bengal

### Option 1: **Section-Based Auto-Selection** (Hugo-lite)

Add section detection before type checking:

```python
def _get_template_name(self, page: Page) -> str:
    # 1. Explicit template (highest priority)
    if 'template' in page.metadata:
        return page.metadata['template']
    
    # 2. Section index files
    if page.source_path.stem == '_index':
        # Try section-specific index
        if page.section:
            section_template = f"{page.section.slug}-index.html"
            if self._template_exists(section_template):
                return section_template
        return 'index.html'
    
    # 3. NEW: Section-based templates
    if page.section:
        section_template = f"{page.section.slug}.html"
        if self._template_exists(section_template):
            return section_template
    
    # 4. Type-based templates
    page_type = page.metadata.get('type', 'page')
    template_map = {
        'post': 'post.html',
        'page': 'page.html',
        'index': 'index.html',
        'doc': 'doc.html',  # explicit type
    }
    
    type_template = template_map.get(page_type)
    if type_template and self._template_exists(type_template):
        return type_template
    
    # 5. Default fallback
    return 'page.html'

def _template_exists(self, template_name: str) -> bool:
    """Check if a template exists in any template directory."""
    try:
        self.template_engine.env.get_template(template_name)
        return True
    except Exception:
        return False
```

**Result:**
```
content/docs/getting-started.md
  ↓
1. Check: template in frontmatter? NO
2. Check: _index.md? NO
3. Check: docs.html exists? YES ✅
4. Use: docs.html
```

**Benefits:**
- ✅ Automatic - no frontmatter needed
- ✅ Flexible - can override per-page
- ✅ Simple - just name template after section
- ✅ Backwards compatible - falls back to current logic
- ✅ Hugo-like but simpler

---

### Option 2: **Cascade-Based** (Current Feature)

Use Bengal's existing cascade system:

```yaml
# content/docs/_index.md
---
title: "Documentation"
cascade:
  template: doc.html
  type: doc
---
```

**Benefits:**
- ✅ Already implemented
- ✅ Explicit and clear
- ✅ Works today
- ✅ No code changes needed
- ⚠️ Requires _index.md in every section
- ⚠️ Manual setup

---

### Option 3: **Config-Based** (Jekyll-style)

Add to `bengal.toml`:

```toml
[templates]
# Path-based template selection
[[templates.rules]]
path = "docs/**"
template = "doc.html"

[[templates.rules]]
path = "blog/**"
template = "post.html"

[[templates.rules]]
type = "post"
template = "post.html"
```

**Benefits:**
- ✅ Centralized configuration
- ✅ Glob pattern support
- ✅ Clear and explicit
- ⚠️ Requires config for everything
- ⚠️ Less convention-based

---

## 🎯 Recommended Approach

### **Hybrid: Section-Based + Cascade**

Combine the best of both worlds:

1. **Section-Based Auto-Detection** (new)
   - `content/docs/` → auto-tries `docs.html`
   - `content/blog/` → auto-tries `blog.html`
   - Convention over configuration

2. **Cascade Override** (existing)
   - `_index.md` with `cascade.template`
   - Explicit when needed

3. **Page Override** (existing)
   - `template:` in frontmatter
   - Highest priority

### Implementation Priority Order

```
1. Frontmatter: template: my-template.html  [EXPLICIT]
2. Cascade: from _index.md                  [SECTION-LEVEL]
3. Section: /docs/ → docs.html             [CONVENTION] ← NEW!
4. Type: type: post → post.html             [TYPE-BASED]
5. Default: page.html                       [FALLBACK]
```

### Example Usage

**No configuration needed:**
```
themes/default/templates/
  ├── docs.html         ← Create this
  ├── blog.html         ← Create this
  └── page.html         ← Default

content/
  ├── docs/
  │   ├── page1.md      ← Auto-uses docs.html ✨
  │   └── page2.md      ← Auto-uses docs.html ✨
  └── blog/
      └── post1.md      ← Auto-uses blog.html ✨
```

**With cascade (for exceptions):**
```yaml
# content/docs/_index.md
---
cascade:
  template: custom-doc.html  # Override auto-detection
---
```

**With page override (for one-offs):**
```yaml
# content/docs/special.md
---
template: landing.html  # This page only
---
```

---

## 🔧 Implementation Plan

### Phase 1: Section-Based Detection (30 min)

1. Add `_template_exists()` helper
2. Add section-based lookup after cascade
3. Update tests

### Phase 2: Documentation (15 min)

1. Update architecture docs
2. Add examples
3. Migration guide

### Phase 3: Migration Path (Optional)

For existing sites:
```bash
# Remove explicit templates if desired
find content/docs -name "*.md" -exec sed -i '' '/^template: doc.html$/d' {} \;

# Create section template
cp themes/default/templates/page.html themes/default/templates/docs.html
```

---

## 📊 Comparison Matrix

| Feature | Current | Option 1 (Section) | Option 2 (Cascade) | Option 3 (Config) |
|---------|---------|-------------------|-------------------|-------------------|
| Automatic | ⚠️ Partial | ✅ Yes | ❌ No | ⚠️ Partial |
| Explicit | ✅ Yes | ✅ Yes | ✅ Yes | ✅ Yes |
| Simple | ✅ Yes | ✅ Yes | ✅ Yes | ⚠️ Moderate |
| Flexible | ⚠️ Moderate | ✅ High | ✅ High | ✅ High |
| Convention-based | ❌ No | ✅ Yes | ❌ No | ⚠️ Partial |
| Config-free | ✅ Yes | ✅ Yes | ⚠️ Needs _index | ❌ No |
| Hugo-like | ❌ No | ✅ Yes | ⚠️ Partial | ❌ No |
| Code changes | - | ⚠️ Small | ✅ None | ⚠️ Medium |

---

## 🎉 Immediate Solution (Today)

**Use cascade + manual template names:**

```yaml
# content/docs/_index.md
---
title: "Documentation"
cascade:
  template: doc.html
---
```

This works **right now** with zero code changes! ✅

---

## 🚀 Future Enhancement (Recommended)

**Implement Option 1: Section-Based Auto-Selection**

1. Simple code change (~30 lines)
2. Backwards compatible
3. Hugo-like convenience
4. Convention over configuration
5. Falls back gracefully

---

## 💭 User's Question Answered

> "Can't you cascade this?"  
**YES!** Use `_index.md` with `cascade.template` (works today)

> "Is there a more automated way?"  
**YES!** Implement section-based auto-selection (30 min of work)

> "Let's analyze how all SSGs handle layouts"  
**Done!** See comparison above. Hugo's approach is powerful but complex. A simplified version would be perfect for Bengal.

---

## 🎯 Recommendation

### Short-term (Now):
Use cascade via `_index.md` - works immediately

### Long-term (Next iteration):
Implement section-based auto-selection for Hugo-like convenience

### Keep:
- Simple, understandable
- Convention over configuration
- Backwards compatible
- Explicit overrides always work

---

**Would you like me to:**
1. ✅ Implement cascade solution now (5 min)
2. 🚀 Implement section-based auto-selection (30 min)
3. 📚 Just document current approach

Your call! 🎯

