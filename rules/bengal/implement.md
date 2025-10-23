---
description: Guide code edits, test updates, and linting with strict guardrails and verification
globs: ["bengal/**/*.py", "tests/**/*.py"]
alwaysApply: false
---

# Bengal Implementation Driver

**Purpose**: Guide code edits, test updates, and linting with guardrails.

**Shortcut**: `::implement`

**Input**: Plan or direct implementation request.

**Principle**: NEVER invent APIs or behavior. Always verify against code/tests first.

---

## Overview

Executes implementation tasks from plans with strict guardrails: verify before edit, minimal changes, preserve style, maintain tests, run linter.

---

## Guardrails

1. **Verify Before Edit**: Read target files to understand current state
2. **Minimal Edits**: Change only what's necessary for the task
3. **Preserve Style**: Match existing code style, typing, docstrings
4. **Type Safety**: Maintain or improve type hints
5. **Test Coverage**: Update/add tests for changed behavior
6. **Lint Clean**: Fix linter errors introduced by changes

---

## Procedure

### Step 1: Pre-Implementation Verification

Before making any edits:
1. **Read Target Files**: Understand current implementation
2. **Search for Usage**: Find where code is used (grep for imports/calls)
3. **Check Tests**: Identify existing tests for this module
4. **Verify Assumptions**: Confirm RFC/plan claims match reality

If discrepancies found → pause and update RFC/plan.

### Step 2: Focused Editing

**Edit Cycle**:
1. **One Task at a Time**: Focus on single task from plan
2. **Make Minimal Edit**: Use `search_replace` or `write` tool
3. **Preserve Context**: Keep surrounding code intact
4. **Add Comments**: Document non-obvious logic
5. **Update Docstrings**: Reflect any API changes

**Example Edit**:
```python
# Before
def build(self):
    """Build the site."""
    self.render_all_pages()

# After
def build(self, incremental: bool = False):
    """Build the site with optional incremental mode.

    Args:
        incremental: If True, only rebuild changed pages.
    """
    if incremental:
        self.render_changed_pages()
    else:
        self.render_all_pages()
```

### Step 3: Test Updates

For each code change, update tests:

**Unit Tests**: `tests/unit/test_{module}.py`
- Test new behavior
- Update assertions for changed behavior
- Add edge cases

**Integration Tests**: `tests/integration/test_{feature}.py`
- Test end-to-end workflows
- Verify subsystem interactions

**Test Structure**:
```python
def test_incremental_build_only_rebuilds_changed_pages(tmp_path):
    """Incremental build should only rebuild pages that changed."""
    # Arrange
    site = create_test_site(tmp_path)
    site.build()  # Initial build

    # Act
    modify_page(site, "page1.md")
    site.build(incremental=True)

    # Assert
    assert page_was_rebuilt(site, "page1.md")
    assert not page_was_rebuilt(site, "page2.md")
```

### Step 4: Lint and Fix

After each edit:
1. **Run Linter**: `read_lints` on changed files
2. **Fix Issues**: Address errors, warnings
3. **Verify**: Ensure linter passes

### Step 5: Atomic Commit

After completing a task (code + tests + lint):
1. **Stage Changes**: `git add` relevant files
2. **Write Commit**: Use pre-drafted message from plan
3. **Format**: `<scope>(<subscope>): <description>`

Example:
```bash
git add -A && git commit -m "core: add incremental build state tracking; add tests"
```

---

## Output Format

```markdown
## ✅ Implementation: [Task Description]

### Executive Summary
[2-3 sentences: what was implemented, files changed, confidence]

### Changes Made

#### Code Changes
- **File**: `bengal/core/site.py`
  - Added `incremental: bool` parameter to `build()` method
  - Implemented `render_changed_pages()` helper
  - Lines changed: [N]

#### Test Changes
- **File**: `tests/unit/test_site.py`
  - Added `test_incremental_build_only_rebuilds_changed_pages`
  - Added `test_incremental_build_with_dependencies`
  - Lines added: [N]

### Validation
- ✅ Linter passed (no new errors)
- ✅ Unit tests pass ([N]/[N])
- ✅ Integration tests pass ([N]/[N])
- ⚠️ [Any warnings or issues]

### Commit
```bash
git add -A && git commit -m "core: add incremental build state tracking; add tests"
```

**Status**: ✅ Committed

### 📋 Next Steps
- [ ] Continue to next task in plan
- [ ] Or run `::validate` for full audit
```

---

## Error Handling

### If Linter Fails
1. Read lint errors
2. Apply self-critique: analyze root cause
3. Fix issues
4. Re-lint

### If Tests Fail
1. Read test output
2. Diagnose failure (logic error, test error, integration issue)
3. Fix code or test
4. Re-run tests

### If Assumptions Violated
1. Pause implementation
2. Document discrepancy
3. Update RFC/plan
4. Get user confirmation before proceeding

---

## Prompting Techniques

- **ReAct**: Reason → search → edit → validate cycle
- **Self-Critique**: Post-edit analysis if failures occur
- **Chain-of-Thought**: Explicit reasoning for design choices in comments

---

## Quality Checklist

Before committing:
- [ ] Code changes minimal and focused
- [ ] Style matches existing code
- [ ] Type hints maintained/improved
- [ ] Docstrings updated
- [ ] Unit tests added/updated
- [ ] Integration tests pass
- [ ] Linter passes (no new errors)
- [ ] Health validators pass
- [ ] Atomic commit with descriptive message
- [ ] Confidence ≥ 90% (core) or ≥ 85% (other)
