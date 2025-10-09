# Template System Cleanup

**Date**: 2025-10-09  
**Type**: Code Cleanup  
**Status**: ✅ Complete

## What Was Done

Removed deprecated template aliases now that the type system is implemented and we haven't released yet.

### Files Deleted

1. **`templates/doc.html`** - Removed (use `doc/single.html` or `type: doc`)
2. **`templates/docs.html`** - Removed (use `doc/list.html` or `type: doc`)

### Rationale

Since Bengal hasn't been released yet:
- ✅ No backward compatibility concerns
- ✅ Cleaner template structure
- ✅ Only one way to do things (Zen of Python)
- ✅ Showcase site is the only test site

### New Structure

```
templates/
  doc/
    list.html      # Section index (type: doc)
    single.html    # Individual pages (type: doc)
  
  tutorial/
    list.html      # Section index (type: tutorial)
    single.html    # Individual pages (type: tutorial)
  
  blog/
    list.html      # Section index (type: blog)
    single.html    # Individual pages (type: blog)
  
  api-reference/
    list.html      # Section index
    single.html    # Individual pages
  
  cli-reference/
    list.html      # Section index
    single.html    # Individual pages
```

### Usage

**Before (deprecated):**
```yaml
---
template: docs.html    # DON'T DO THIS
---
```

**After (correct):**
```yaml
---
type: doc              # ✅ Use type system
cascade:
  type: doc
---
```

Or explicit:
```yaml
---
template: doc/list.html    # ✅ Explicit path
---
```

## Showcase Site Updates

### Updated Files

1. **`examples/showcase/content/docs/_index.md`**
   - Changed from `template: docs.html`
   - To `type: doc` with cascade

2. **`examples/showcase/content/tutorials/_index.md`**
   - Created new file with `type: tutorial`

3. **`examples/showcase/content/tutorials/migration/from-hugo.md`**
   - Enhanced with tutorial metadata:
     - `type: tutorial`
     - `difficulty: intermediate`
     - `time: 30 minutes`
     - `icon: 🔄`
     - `learning_objectives: [...]`
     - `prerequisites: [...]`

## Verification

### Build Tests

```bash
$ bengal build --quiet
✅ Build complete!

$ cd examples/showcase && bengal build --quiet
✅ Build complete!
```

### Template Usage Verification

```bash
# Docs pages using doc templates
$ grep "docs-layout" public/docs/**/*.html
✓ Found in all doc pages

# Tutorial index using tutorial/list.html
$ grep "tutorial-container" public/tutorials/index.html
✓ Found: tutorial-container class

# Tutorial pages using tutorial/single.html
$ grep "tutorial-page-layout" public/tutorials/migration/from-hugo/index.html
✓ Found: tutorial-page-layout class
```

## Benefits

1. **Cleaner** - One template per purpose, no aliases
2. **Clearer** - Type system is the primary interface
3. **Consistent** - All templates follow same pattern
4. **Maintainable** - Less templates to maintain
5. **Educational** - Showcase demonstrates best practices

## Impact

**Breaking Changes**: None (haven't released yet)

**Migration Required**: Only for showcase site (done)

**Future**: When v1.0 releases, this is the clean state we ship with.

## Related

- `plan/completed/TYPE_SYSTEM_IMPLEMENTATION.md` - Type system implementation
- `plan/completed/AUTODOC_SIDEBAR_NAVIGATION.md` - API/CLI sidebar navigation
- `docs/CONTENT_TYPES.md` - User documentation for type system

