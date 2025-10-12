# Theme Developer Ergonomics Analysis

**Date:** 2025-10-12  
**Purpose:** Deep analysis of theme developer workflows and tool needs  
**Findings:** CLI architecture issue discovered + better solution identified

---

## Issue #1: CLI Architecture Problem

### Discovery

While adding the `bengal health` command, discovered a critical architecture issue:

**TWO CLI entry points exist:**

1. `/bengal/cli/__init__.py` ✅ **ACTUAL** entry point (used by `pip install`)
2. `/bengal/cli.py` ❌ **LEGACY** file (not used, causes confusion)

**Evidence:**
```bash
$ which bengal
/Users/llane/miniconda3/bin/bengal

$ cat /Users/llane/miniconda3/bin/bengal
from bengal.cli import main  # Imports from bengal/cli/__init__.py

$ bengal --help
# Shows commands from bengal/cli/__init__.py, NOT bengal/cli.py
```

**Problem:** Commands added to `bengal/cli.py` don't appear in actual CLI.

### Solution: CLI Architecture Cleanup

**Option A: Remove Legacy File** (Recommended)
```
1. Delete /bengal/cli.py (2,394 lines)
2. Keep only /bengal/cli/__init__.py (112 lines, clean modular design)
3. All commands already properly modularized in /bengal/cli/commands/
```

**Option B: Consolidate** (More work)
```
1. Merge bengal/cli.py into bengal/cli/__init__.py
2. Risk breaking existing imports
```

**Recommendation:** Option A - The modular structure in `bengal/cli/__init__.py` is already superior.

---

## Issue #2: Do Theme Developers Need `bengal health`?

### Current Workflow Analysis

**Theme developer's typical day:**

1. **Edit template** (`templates/page.html`)
2. **Save** (watchdog detects change)
3. **Auto-rebuild** (with `strict_mode=True` in serve)
4. **See error immediately** in terminal with our enhanced messages
5. **Fix and repeat**

**Time:** ~2 seconds from save to feedback

### What `bengal health` Would Offer

```bash
bengal health
# Takes ~2 seconds
# Shows same errors that strict mode would show
# Requires manual invocation
```

**Value proposition:**
- ✅ Validates ALL templates (even unused ones)
- ✅ Config validation
- ✅ Pre-commit check (CI/CD)
- ❌ NOT faster than serve mode for active development
- ❌ Duplicates what strict mode already does better

### The Real Pain Points

After analyzing theme developer workflows, the **actual** pain points are:

#### 1. **Error Messages Were Confusing** ✅ SOLVED
```diff
- UndefinedError: 'dict object' has no attribute 'image'
+ [red bold]Unsafe dict access detected![/red bold]
+ Replace dict.image with dict.get('image')
+ Common locations: page.metadata, site.config
```

#### 2. **Errors Only Appeared in Serve, Not Build** ✅ DOCUMENTED
```bash
# Now documented clearly:
bengal serve          # Strict mode enabled automatically
bengal build --strict # Enable strict mode for builds
```

#### 3. **No Template Documentation** ⚠️ PARTIALLY SOLVED
- Have `/themes/default/templates/README.md`
- Missing: **Safe template patterns guide**

#### 4. **Template Discovery is Hard** ⚠️ UNSOLVED
```bash
# Current: Must navigate filesystem
ls -R themes/default/templates/

# Better: Built-in discovery
bengal theme discover --templates
bengal theme discover --partials
```

#### 5. **Can't Preview Components in Isolation** ⚠️ UNSOLVED
```bash
# Current: Must build entire site to see one component change
bengal serve  # Rebuilds everything

# Better: Component preview mode
bengal serve --component partials/breadcrumbs.html
```

---

## The REAL Feature Needed: Enhanced Serve Mode

Instead of a separate `health` command, **enhance `bengal serve`** with theme-dev features:

### Proposed: `bengal serve --theme-dev`

```bash
bengal serve --theme-dev
```

**Features:**

1. **Template Validation on Startup** (quick check before watching)
2. **Enhanced Error Display** (already have this)
3. **Template Change Notifications**
   ```
   🔄 Template changed: base.html
   ✓ Validated in 0.3s
   ✓ Rebuilt 12 pages
   ```

4. **Template Dependency Graph**
   ```
   📝 base.html changed
   ↳ Affects: page.html, post.html, doc/single.html (47 pages)
   ```

5. **Component Hot Reload** (stretch goal)
   ```
   🔥 Hot reloaded: partials/breadcrumbs.html
   ↳ Updated 8 pages without full rebuild
   ```

6. **Template Performance Warnings**
   ```
   ⚠️  blog/single.html took 45ms to render (avg: 12ms)
   ```

---

## Recommendations

### Immediate Actions (Phase 1)

1. **✅ Keep Enhanced Error Messages** (already done)
   - The improved Jinja2 error detection is valuable
   - Helps both serve and build modes

2. **❌ Skip `bengal health` Command** (not needed now)
   - Would duplicate serve mode functionality
   - Better to enhance serve mode instead
   - Can reconsider later if CI/CD use case emerges

3. **📝 Document Safe Template Patterns**
   - Create `/themes/default/templates/SAFE_PATTERNS.md`
   - Document `.get()` usage
   - Document `with context` pattern
   - Link from theme README

4. **🔧 Fix CLI Architecture**
   - Delete `/bengal/cli.py` (legacy file)
   - Keep only `/bengal/cli/__init__.py`
   - Update imports if needed

### Future Enhancements (Phase 2)

5. **`bengal serve --theme-dev`** Mode
   - Pre-flight template validation
   - Enhanced change notifications
   - Template dependency tracking
   - Performance warnings

6. **`bengal theme discover`** Command
   - List all templates in theme chain
   - Show which templates are being used
   - Identify swizzle candidates

7. **Component Preview** (Stretch Goal)
   - Isolated component rendering
   - Hot reload for single components
   - Reduces full rebuild time

---

## Workflow Comparison

### Current Workflow ✅

```bash
# Developer edits template
$ vim themes/default/templates/base.html

# Serve mode catches error immediately
$ bengal serve
🚀 Server running at http://localhost:5173
...
❌ UndefinedError: 'dict object' has no attribute 'og_image'
   [red bold]Unsafe dict access detected![/red bold]
   Replace site.config.og_image with site.config.get('og_image')
```

**Time to feedback:** 2 seconds  
**Experience:** ✅ Good (with enhanced error messages)

### With `bengal health` ❌

```bash
# Developer edits template
$ vim themes/default/templates/base.html

# Must manually run health check
$ bengal health
🏥 Running Bengal health check...
❌ Unsafe dict access
   File: templates/base.html
   Line: 45
   Fix: Replace with site.config.get('og_image')

# Then run serve
$ bengal serve
# (Would show same error)
```

**Time to feedback:** 5+ seconds (extra command)  
**Experience:** ❌ Worse (redundant step)

### With Enhanced Serve Mode ✅✅

```bash
# Developer runs enhanced serve mode
$ bengal serve --theme-dev
🏥 Pre-flight validation...
   ✓ 42 templates checked
   ✓ Config valid
🚀 Server running at http://localhost:5173
📋 Theme developer mode enabled
   • Enhanced error messages
   • Template dependency tracking
   • Performance warnings

# Edit template
$ vim themes/default/templates/base.html

# Auto-detected with context
🔄 base.html changed
   ↳ Affects: page.html, post.html, doc/single.html
   ✓ Validated in 0.3s
   ✓ Rebuilt 12 affected pages

❌ Error in base.html:45
   [red bold]Unsafe dict access detected![/red bold]
   Replace site.config.og_image with site.config.get('og_image')
```

**Time to feedback:** 2 seconds (same as current)  
**Experience:** ✅✅ Best (more context, better UX)

---

## Decision Matrix

| Feature | Current | With `health` | With Enhanced Serve |
|---------|---------|---------------|---------------------|
| Fast feedback | ✅ 2s | ❌ 5s+ | ✅ 2s |
| Error context | ✅ Good | ✅ Good | ✅✅ Better |
| Validates all templates | ❌ No | ✅ Yes | ✅ Yes (on startup) |
| Automatic | ✅ Yes | ❌ No | ✅ Yes |
| Dependency awareness | ❌ No | ❌ No | ✅ Yes |
| Performance insights | ❌ No | ❌ No | ✅ Yes |
| Extra commands to learn | ✅ No | ❌ Yes | ✅ No (flag only) |

**Winner:** Enhanced Serve Mode (best of both worlds)

---

## Implementation Plan

### Phase 1: Cleanup & Document (Now)

1. **Delete `/bengal/cli.py`** ✅ High priority
   - Prevents future confusion
   - Already have better structure

2. **Document safe patterns** ✅ High priority
   - Create `SAFE_PATTERNS.md`
   - Link from theme README

3. **Update `SERVER_FREEZE_FIX` document** ✅ Medium priority
   - Add "use `bengal serve` for validation" section
   - Remove references to `bengal health`

### Phase 2: Enhanced Serve (Future)

4. **Add `--theme-dev` flag to serve** ⚠️ Future
   - Pre-flight validation
   - Enhanced notifications
   - Template dependency tracking

5. **Add `bengal theme discover`** ⚠️ Future
   - List templates in chain
   - Show usage statistics

---

## Conclusion

**The `bengal health` command isn't needed** because:

1. `bengal serve` already does this better (automatic + fast)
2. Would add cognitive load (another command to remember)
3. Doesn't solve the actual pain points

**What theme developers actually need:**

1. ✅ **Better error messages** (DONE)
2. ✅ **Documentation on safe patterns** (NEEDED)
3. ⚠️ **Enhanced serve mode with more context** (FUTURE)
4. ⚠️ **Template discovery tools** (FUTURE)

**Next Steps:**

1. Delete `/bengal/cli.py` (fix architecture issue)
2. Create `SAFE_PATTERNS.md` guide
3. Consider `bengal serve --theme-dev` for Phase 2
