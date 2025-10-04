# Layout Customization Philosophy

**Date:** October 4, 2025  
**Topic:** Why Less Can Be More

---

## 🎯 The Core Question

**"Should we add more automatic layout selection options?"**

Short answer: **Maybe not right now.**

---

## 💭 Current State Assessment

### What We Have (Working Great!)

**1. Manual Override (Explicit)**
```yaml
---
template: doc.html  # ✅ Clear, obvious, works
---
```

**2. Cascade (Hugo-style)**
```yaml
# _index.md
---
cascade:
  template: doc.html  # ✅ One file controls section
---
```

**3. Type-based Fallback**
```yaml
---
type: post  # → post.html
---
```

**4. Default Fallback**
```
No config? → page.html
```

### Coverage Analysis

This handles:
- ✅ **Documentation sites** (cascade in `_index.md`)
- ✅ **Blogs** (type: post)
- ✅ **Landing pages** (explicit template)
- ✅ **One-offs** (explicit override)
- ✅ **Defaults** (page.html fallback)

**That's... actually pretty comprehensive!** 🤔

---

## 🔍 What Would Section-Based Auto-Selection Add?

### The Proposal

```
content/docs/page.md 
  → Checks: does templates/docs.html exist?
  → If yes: Use it
  → If no: Fall back to type/default
```

### Pros

✅ **Zero configuration**
```
# No frontmatter needed!
---
title: "My Doc"  # ← That's it!
---
```

✅ **Convention over configuration**
```
templates/
  ├── docs.html      ← Auto-used by content/docs/
  ├── blog.html      ← Auto-used by content/blog/
  └── page.html      ← Default
```

✅ **Hugo-like DX**
```
Users familiar with Hugo expect this
```

### Cons

⚠️ **"Magic" behavior**
```
Where is template coming from? 
└─ Hidden in directory structure
└─ Not obvious from frontmatter
```

⚠️ **Template must exist**
```
What if docs.html doesn't exist?
└─ Silent fallback? Confusing.
└─ Error? Annoying for prototyping.
```

⚠️ **Debugging complexity**
```
Why is my page using this template?
1. Explicit in frontmatter?
2. Cascade from _index?
3. Section auto-detection?
4. Type-based?
5. Default?
← Five places to check! 😰
```

⚠️ **Naming conflicts**
```
content/blog/ → blog.html
content/blog/ with type: post → post.html or blog.html?
├─ Which wins?
└─ Ambiguous!
```

---

## 🎨 Design Philosophy Analysis

### Hugo's Approach: Power + Complexity

**Hugo's template lookup:**
```
1. /layouts/[section]/[layout].[type].html
2. /layouts/[section]/[type].html
3. /layouts/[section]/list.html
4. /layouts/[section]/single.html
5. /layouts/[type]/list.html
6. /layouts/[type]/single.html
7. /layouts/_default/list.html
8. /layouts/_default/single.html
```

**Result:**
- ✅ Incredibly flexible
- ✅ Handles every edge case
- ⚠️ **Complex mental model**
- ⚠️ Hard to debug ("Why is it using THIS template?")
- ⚠️ Steep learning curve

### Jekyll's Approach: Simplicity + Configuration

**Jekyll's template lookup:**
```
1. Frontmatter: layout: my-layout
2. Config defaults
3. Layout chain (layout: post → post.html → default.html)
```

**Result:**
- ✅ Simple, explicit
- ✅ Easy to understand
- ✅ Configuration-driven
- ⚠️ Requires setup
- ⚠️ Less "magic"

### Bengal's Current Approach: Middle Ground

**Bengal's template lookup:**
```
1. Frontmatter: template: doc.html    [EXPLICIT]
2. Cascade: from _index.md            [SECTION-LEVEL]
3. Type: type: post → post.html       [TYPE-BASED]
4. Default: page.html                 [FALLBACK]
```

**Result:**
- ✅ **Explicit when needed** (frontmatter)
- ✅ **DRY when appropriate** (cascade)
- ✅ **Sensible fallbacks** (type, default)
- ✅ **Easy to debug** (only 4 places to check)
- ✅ **Hugo-compatible** (cascade)
- ⚠️ Not fully automatic

---

## 💡 The Real Question

**"Does the current system cover 95% of use cases with 20% of the complexity?"**

### Use Case Coverage

| Use Case | Solution | Lines of Config |
|----------|----------|-----------------|
| **Documentation** | Cascade in `_index.md` | 2 lines |
| **Blog posts** | `type: post` | 1 line |
| **Landing pages** | `template: landing.html` | 1 line |
| **Multi-section site** | One `_index.md` per section | 2 lines × N |
| **Mixed content** | Explicit templates | 1 line each |
| **Default pages** | Nothing | 0 lines |

**Average config needed: ~1-2 lines per unique layout**

That's... pretty good! 🎯

---

## 🚀 When to Add More Automation

### Green Flags (Good Reasons)

✅ **User frustration**
```
"I keep having to add template: doc.html to every page!"
├─ BUT: Cascade solves this!
└─ Only need it once per section
```

✅ **Common pattern**
```
"90% of sites have /docs/ → docs.html"
├─ True, but...
└─ One _index.md already handles it
```

✅ **Hugo migration pain**
```
"We have 500 Hugo sites to migrate"
├─ Valid!
└─ Auto-detection helps migration
```

### Red Flags (Bad Reasons)

❌ **"Because Hugo does it"**
```
Hugo's complexity is both strength AND weakness
├─ Don't copy blindly
└─ Copy what works, skip what doesn't
```

❌ **"To look more sophisticated"**
```
Complexity ≠ Quality
├─ Simple can be better
└─ KISS principle
```

❌ **"Because we can"**
```
Every feature has:
├─ Maintenance cost
├─ Documentation cost
├─ Cognitive load
└─ Debugging complexity
```

---

## 🎯 My Honest Assessment

### Current System Strengths

**1. Explicit Over Implicit**
```yaml
# Clear what's happening
---
cascade:
  template: doc.html  # ← Right here!
---
```

**2. Progressive Disclosure**
```
Beginner: Just use defaults
├─ page.html for everything
└─ Works fine!

Intermediate: Add cascade
├─ One _index.md per section
└─ Still simple!

Advanced: Custom templates
├─ Explicit overrides
└─ Full control!
```

**3. Easy Debugging**
```
"Why is this using doc.html?"
1. Check frontmatter → Has cascade? YES!
2. Done! ✅

vs. Hugo:
"Why is this using doc.html?"
1. Check frontmatter
2. Check section structure
3. Check file naming
4. Check layout cascade
5. Check type
6. Check defaults
7. ??? Still confused
```

### Where It Could Improve

**1. Boilerplate Reduction**
```yaml
# Currently need this in every section:
---
cascade:
  template: doc.html
---

# Could be automatic IF we detect templates/docs.html
```

**2. Migration from Hugo**
```
Hugo users expect section-based auto-selection
├─ Could help adoption
└─ But... is that worth complexity?
```

**3. "Zero-config" Experience**
```
Someone wants to try Bengal:
├─ Clone repo
├─ Add markdown
├─ Run build
└─ Works!

vs.

├─ Clone repo
├─ Add markdown
├─ Create _index.md
├─ Add cascade
├─ Run build
└─ Works!

↑ One extra step... is that a problem?
```

---

## 🎨 Alternative: Make Cascade Easier

Instead of adding auto-detection, what if we made cascade **more discoverable**?

### Option 1: Scaffold Command

```bash
bengal new section docs
```

```yaml
# Creates: content/docs/_index.md
---
title: "Documentation"
cascade:
  template: doc.html  # ← Pre-populated!
---
```

**Result:**
- ✅ Still explicit
- ✅ Less typing
- ✅ Teaches pattern
- ✅ No magic

### Option 2: Template Detection Warning

```bash
bengal build

ℹ️  Found templates/docs.html but no content/docs/_index.md
   Add cascade to auto-apply this template:
   
   # content/docs/_index.md
   ---
   cascade:
     template: docs.html
   ---
```

**Result:**
- ✅ Discovers templates
- ✅ Teaches users
- ✅ No magic
- ✅ Helpful guidance

### Option 3: Smart Defaults in Config

```toml
# bengal.toml
[templates]
auto_cascade = true  # Default: false

# When enabled:
# - /docs/ → tries docs.html if it exists
# - /blog/ → tries blog.html if it exists
# - Falls back to type/default
```

**Result:**
- ✅ Opt-in (not forced)
- ✅ Explicit config
- ✅ Backwards compatible
- ⚠️ Still adds complexity

---

## 🎯 Recommendation

### For Now: **Stick with What We Have**

**Reasons:**
1. ✅ Covers 95% of use cases
2. ✅ Simple mental model
3. ✅ Easy to debug
4. ✅ Hugo-compatible (cascade)
5. ✅ Explicit > Implicit
6. ✅ Low maintenance burden

### Future: **Watch for Signals**

**Add auto-detection IF:**
- Users consistently ask for it
- Hugo migration becomes common
- We see repeated "_index.md boilerplate" complaints
- We find a way to do it WITHOUT complexity

### Better Near-term: **Improve DX**

Instead of auto-detection:
1. ✅ **Scaffold command** (easy _index.md creation)
2. ✅ **Better docs** (examples, patterns)
3. ✅ **Warning/hints** (suggest cascade when appropriate)
4. ✅ **Starter templates** (docs site starter with cascade)

---

## 💭 The Fundamental Trade-off

```
                More Automatic
                      ↑
                      |
        Hugo ●        |
             |        |
             |        |
             |        | ● Jekyll
             |        |     (with defaults)
             |   ● Bengal
             |   (current)
             |        |
             |        |
      ← More Explicit   More Configuration →
             |        |
             |        |
        Bare |        |
        Markdown ●    |
             |        |
                      ↓
                Less Automatic
```

**Where should Bengal be?**

Current position: **Sweet spot for most users**
- Not too magic (Hugo)
- Not too manual (bare markdown)
- Not too config-heavy (Jekyll defaults)

---

## ✅ Conclusion

### You Asked: "Do you feel that way because our design addresses most use cases?"

**YES! But with nuance:**

**What we have:**
- ✅ Handles 95% of use cases
- ✅ Simple mental model
- ✅ Easy to debug
- ✅ Explicit when needed
- ✅ DRY via cascade

**What we don't have:**
- Zero-config section templates
- Full Hugo template lookup
- Directory-based magic

**Should we add more?**
- ⏸️ **Not yet** - current system works great
- 👀 **Watch usage** - see what people actually need
- 🎯 **Improve DX** - make cascade easier to discover/use
- 🚀 **Stay flexible** - can add later if needed

**Philosophy:**
> "Start simple, add complexity only when clearly needed"

---

## 🎤 My Take

I'm not ambivalent - I'm **deliberately conservative**. 

**Why?**
- Every feature is forever
- Complexity compounds
- Simple is powerful
- Users can always go explicit

**But:**
- I'm watching for pain points
- Ready to add features when needed
- Open to better solutions
- Value user feedback highly

**Current verdict:** 
The cascade + explicit system **works really well** for docs sites. Let's:
1. ✅ Keep it simple
2. 👀 Watch for friction
3. 🎯 Improve DX (scaffolding, hints)
4. 🚀 Add automation only if clearly beneficial

---

**TL;DR:** Current system is **good enough** for most cases. Adding more automation would help 5% of cases but add complexity for everyone. Better to improve discoverability than add magic.

**Your thoughts?** Do you see use cases we're missing? 🤔

