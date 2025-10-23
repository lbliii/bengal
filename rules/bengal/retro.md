---
description: Summarize impact, update changelog, archive planning docs for completed work
globs: ["CHANGELOG.md", "plan/**/*.md"]
alwaysApply: false
---

# Bengal Retrospective & Changelog

**Purpose**: Summarize impact, document changes, update changelog.

**Shortcut**: `::retro`

**When to Use**:
- After completing feature implementation
- Before merging to main
- Pre-release preparation

---

## Overview

Creates comprehensive summary of completed work, updates changelog, and archives planning documents. Provides clear impact assessment and lessons learned.

---

## Procedure

### Step 1: Impact Summary

Write 1-2 paragraph summary:
- What was built/changed
- Why it matters (user/developer benefit)
- Confidence level of implementation

### Step 2: Code References

Create itemized list of key changes:

```markdown
### Key Changes

**Core** (`bengal/core/`):
- `site.py:145-150`: Added incremental build support
- `page.py:200`: Added change detection logic

**Orchestration** (`bengal/orchestration/`):
- `render_orchestrator.py:50-75`: Wire incremental flag through pipeline

**Tests** (`tests/`):
- `unit/test_site.py:89-120`: Added incremental build tests
- `integration/test_build.py:200-250`: Added end-to-end incremental test

**Documentation** (`architecture/`):
- `cache.md`: Updated to reflect incremental build cache usage
```

### Step 3: Update Changelog

Update `CHANGELOG.md` in the **Unreleased** section:

```markdown
## [Unreleased]

### Added
- Incremental build support: only rebuild pages that changed
- `Site.build(incremental=True)` API for selective rebuilds
- Change detection in `Page` and `Asset` classes

### Changed
- Build orchestrator now supports incremental mode
- Cache indexes updated to track modification times

### Fixed
- [Any bugs fixed as part of this work]

### Performance
- Incremental builds reduce build time by 70-90% for small changes
```

Follow **Keep a Changelog** format:
- **Added**: New features
- **Changed**: Changes to existing functionality
- **Deprecated**: Soon-to-be-removed features
- **Removed**: Removed features
- **Fixed**: Bug fixes
- **Security**: Vulnerability fixes
- **Performance**: Performance improvements

### Step 4: Move Planning Documents

Move completed plans to archive:
```bash
mv plan/active/plan-[name].md plan/implemented/
mv plan/active/rfc-[name].md plan/implemented/
```

Update moved files with:
- **Implemented Date**: [YYYY-MM-DD]
- **Final Confidence**: [N]%
- **Actual vs Estimated**: [time comparison]

### Step 5: Lessons Learned (Optional)

If applicable, add a brief lessons learned section:

```markdown
### Lessons Learned
- **Surprise 1**: Cache invalidation was more complex than expected
- **Success 1**: Test-first approach caught edge cases early
- **Future**: Consider generalizing change detection for assets
```

---

## Output Format

```markdown
## 📝 Retrospective: [Feature/Change Name]

### Impact Summary

[1-2 paragraphs describing what was built, why it matters, confidence level]

---

### Key Changes

[Itemized list by subsystem with file:line references]

---

### Changelog Entry

```markdown
## [Unreleased]

### Added
- [Feature description]
- [API additions]

### Changed
- [Behavior changes]

### Performance
- [Performance improvements with metrics if available]
```

---

### Planning Documents

- ✅ Moved `plan/active/plan-[name].md` → `plan/implemented/`
- ✅ Moved `plan/active/rfc-[name].md` → `plan/implemented/`
- ✅ Updated `CHANGELOG.md`

---

### Lessons Learned

[Optional section with insights]

---

### 📊 Metrics

- **Tasks Completed**: [N]/[N]
- **Files Changed**: [N]
- **Lines Added**: [+N]
- **Lines Removed**: [-N]
- **Tests Added**: [N]
- **Final Confidence**: [N]% 🟢

---

### ✅ Ready to Ship

- [✅] All tasks completed
- [✅] Tests passing
- [✅] Documentation updated
- [✅] Changelog updated
- [✅] Confidence ≥ 90%

**Status**: Ready for merge to `main`
```

---

## Prompting Techniques

- **Chain-of-Thought**: Explicit reasoning about impact and lessons
- **RAG**: Pull from plan/RFC documents and git history

---

## Integration

Used by:
- **Workflows**: `::workflow-ship` includes retrospective
- **Manual**: Invoke via `::retro` when implementation complete

Prepares work for:
- Code review
- Merge to main
- Release notes
