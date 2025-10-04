# Autodoc: Build-Time vs Static File Generation

**Date:** October 4, 2025  
**Status:** 🤔 Design Decision Needed

## The Question

Should autodoc generate markdown files as **static artifacts** (current) or **build-time content** (proposed)?

## Current Approach: Static File Generation

**How it works:**
```bash
$ bengal autodoc              # Generates content/api/*.md
$ bengal autodoc-cli          # Generates content/cli/*.md
$ git add content/api         # Files are committed
$ bengal build                # Builds from committed files
```

### Pros ✅

1. **Reviewable in PRs**
   - Docs show up in diffs
   - Can review generated output
   - See what changed when code changes

2. **Build Separation**
   - Docs generation separate from site building
   - Don't need source code at build time
   - Can generate docs on dev machine, deploy anywhere

3. **Incremental Builds**
   - Bengal's incremental system works automatically
   - Only rebuild changed markdown files
   - Fast dev experience

4. **Manual Override**
   - Can hand-edit generated docs if needed
   - Add custom examples or notes
   - Though this breaks on regeneration...

5. **CI/CD Flexibility**
   - Can generate docs in one CI job
   - Build site in another
   - Different machines, different requirements

### Cons ❌

1. **Git Noise**
   - Large diffs when code changes
   - 100+ files for a simple API change
   - Clutters PR reviews with generated content

2. **Accidental Edits**
   - Devs might manually edit `content/api/foo.md`
   - Changes lost on next `bengal autodoc`
   - No warning system

3. **Stale Docs**
   - Easy to forget to regenerate
   - Code changes but docs don't
   - Need to remember to run autodoc

4. **Repo Bloat**
   - Generated files take up space
   - Every historical version stored
   - Increases clone time

5. **Two-Step Process**
   - `bengal autodoc` then `bengal build`
   - Easy to forget the first step
   - No single "build everything" command

## Proposed Approach: Build-Time Generation

**How it would work:**
```bash
$ bengal build                # Generates + builds in one step
# No content/api or content/cli directories committed
```

### Pros ✅

1. **Clean Git History**
   - Only source code in repo
   - No generated file diffs
   - PRs show actual changes only

2. **Always Fresh**
   - Docs always match current code
   - Can't have stale docs
   - One source of truth

3. **Single Command**
   - `bengal build` does everything
   - No two-step process
   - Simpler mental model

4. **No Accidental Edits**
   - Can't edit generated files (they don't exist)
   - Forces docs to come from code
   - Clearer separation

5. **Smaller Repos**
   - No generated content bloat
   - Faster clones
   - Less storage

### Cons ❌

1. **Slower Builds**
   - Must regenerate every build
   - 0.5-1s for Python extraction
   - Can't leverage incremental builds for autodoc content

2. **Requires Source Code**
   - Need Python source at build time
   - Need CLI app importable
   - Can't build docs-only site from markdown

3. **Harder to Review**
   - Can't see doc changes in PRs
   - Must build locally to preview
   - "Trust the generator" approach

4. **Complex Build Pipeline**
   - Build process more complex
   - Need to inject virtual content
   - Harder to debug issues

5. **No Manual Override**
   - Can't tweak generated docs
   - All-or-nothing approach
   - Less flexibility

## The Spectrum: Hybrid Approaches

### Option 1: **Git-Ignored Static Files** (Middle Ground)
```bash
$ bengal autodoc              # Generates to content/api (gitignored)
$ bengal build                # Uses generated files
# Files exist locally but not in git
```

**Pros:**
- Clean git history (not committed)
- Fast builds (incremental works)
- Can preview locally before build
- Two-step process optional

**Cons:**
- Must run autodoc before build (or have hook)
- Easy to forget if files don't exist
- Still have accidental edit risk locally

### Option 2: **Build Hook with Cache**
```bash
$ bengal build                # Checks if autodoc needed, generates if stale
# Caches generated files in .bengal/cache/autodoc
```

**Pros:**
- Single command
- Only regenerates when source changes
- Clean git (cache gitignored)
- Fast most of the time

**Cons:**
- Need to detect source changes (file hashing)
- Cache invalidation complexity
- Still requires source at build time

### Option 3: **Virtual Pages (In-Memory)**
```python
# During build, inject Page objects without files
site.pages.extend(autodoc_generator.generate_virtual_pages())
```

**Pros:**
- No files at all (cleanest)
- Always fresh
- Single command

**Cons:**
- Most complex implementation
- Can't preview files directly
- Need to refactor Bengal's Page model

## Comparison Matrix

| Aspect | Static Files | Build-Time | Git-Ignored | Build Hook | Virtual |
|--------|-------------|-----------|-------------|-----------|---------|
| **Git cleanliness** | ❌ Large diffs | ✅ Clean | ✅ Clean | ✅ Clean | ✅ Clean |
| **Build speed** | ✅ Fast (incremental) | ❌ Slow (always regen) | ✅ Fast | ⚠️ Conditional | ✅ Fast |
| **Always fresh** | ❌ Can be stale | ✅ Always | ❌ Manual | ✅ Smart | ✅ Always |
| **PR reviewability** | ✅ See in diffs | ❌ No diffs | ❌ No diffs | ❌ No diffs | ❌ No diffs |
| **Simplicity** | ✅ Simple | ⚠️ Medium | ✅ Simple | ❌ Complex | ❌ Very complex |
| **Manual override** | ⚠️ Risky | ❌ No | ⚠️ Risky | ❌ No | ❌ No |
| **Deploy anywhere** | ✅ Yes | ❌ Need source | ✅ Yes | ❌ Need source | ❌ Need source |

## Industry Examples

### Sphinx (Static Files)
```bash
$ make html                   # Generates _build/html
# Usually gitignored, but CAN commit
```
- Default: build-time, gitignore output
- Flexibility: can commit if desired
- ReadTheDocs: generates on their servers

### MkDocs (Build-Time)
```bash
$ mkdocs build                # Generates site/
# Always generated, never commit
```
- Pure build-time approach
- Gitignore `site/`
- Simple, opinionated

### Docusaurus (Static with Versioning)
```bash
$ npm run docusaurus docs:version 1.0
# Snapshots docs to versioned_docs/version-1.0/
# THESE get committed for version history
```
- Hybrid: generated docs committed for versions
- Working docs can be either way
- Flexibility for different needs

### Hugo (Static Content Model)
```bash
# All content/*.md committed (manually written)
$ hugo                        # Builds from committed files
```
- Purely static content
- No generation (unless custom scripts)
- Bengal follows this model currently

## Recommendations by Use Case

### For Bengal's Own Docs
**Recommendation:** Git-Ignored Static Files + Build Hook

**Rationale:**
1. Clean git history (important for open source)
2. Fast dev experience (incremental builds)
3. Single command for users (`bengal build` runs autodoc if needed)
4. Can preview markdown files locally

**Implementation:**
```toml
# bengal.toml
[autodoc]
mode = "auto"  # "manual", "auto", or "build-time"

[autodoc.python]
output_dir = "content/api"  # Add to .gitignore
```

```bash
# .gitignore
content/api/
content/cli/
```

```python
# During build
if autodoc_config.get('mode') == 'auto':
    if needs_autodoc_refresh():  # Check source timestamps
        run_autodoc()
```

### For Library Docs (Other Users)
**Recommendation:** Make it Configurable

Let users choose via config:

```toml
[autodoc]
mode = "manual"      # Explicit command, user commits files
# mode = "auto"      # Build checks and runs if needed
# mode = "build-time" # Always regenerate at build
```

**Rationale:**
- Some projects want reviewable diffs
- Some want build-time freshness
- Some want deployment flexibility
- Different teams, different workflows

## Implementation Plan

### Phase 1: Current (v0.3.0) ✅
- Static file generation
- Manual commands
- Files committed

### Phase 2: Gitignore + Warning (v0.3.1)
- Update docs to recommend gitignoring
- Add warning if generated files are edited
- Document the tradeoffs

### Phase 3: Build Hook (v0.4.0)
- Add `mode = "auto"` support
- `bengal build` runs autodoc if sources changed
- Smart caching based on source timestamps
- Still write files (for preview)

### Phase 4: Configurable (v0.5.0)
- Support all modes: manual, auto, build-time
- Let users choose their workflow
- Document pros/cons of each

### Phase 5: Virtual Pages? (v1.0?)
- If demand exists, implement pure in-memory
- Most complex, least priority
- Would need Page model refactor

## My Recommendation

**Ship v0.3.1 with:**
1. Update docs to add `content/api/` and `content/cli/` to `.gitignore`
2. Add `--check-edits` flag that warns if generated files were modified
3. Add `bengal autodoc --all` that runs both python and cli extraction
4. Document the tradeoff clearly in ARCHITECTURE.md

**Plan for v0.4.0:**
```toml
[autodoc]
mode = "auto"  # Default: smart build-time generation
cache_dir = ".bengal/autodoc"
```

This gives you clean git NOW while keeping incremental builds working, and sets up for build-time automation later.

## Questions to Answer

1. **For Bengal's showcase:** Do we want autodoc'd content in git?
2. **For Bengal users:** What's the default experience we want?
3. **For Sphinx migration:** What do Sphinx users expect?

---

## ✅ DECISION (October 4, 2025)

**Approach:** Git-Ignored Static Files (Phase 1)

**Implementation:**
1. Added `**/content/api/` and `**/content/cli/` to `.gitignore`
2. Untracked existing generated files from git (`git rm --cached`)
3. Created `examples/showcase/README.md` with workflow docs
4. Files still exist locally for fast incremental builds

**Rationale:**
- Clean git history (no 101-file diffs in PRs) ✅
- Fast incremental builds (files exist locally) ✅
- Simple workflow (no complex build hooks yet) ✅
- Flexibility for future build-time automation ✅

**Next Steps:**
- Phase 2 (v0.3.1): Add `--check-edits` warning flag
- Phase 3 (v0.4.0): Implement `mode = "auto"` with build hooks
- Phase 4 (v0.5.0): Make fully configurable for users

**Status:** Implemented and documented.

