---
description: Guide code edits with strict guardrails - verify before edit, minimal changes, run linter
alwaysApply: false
globs: ["bengal/**/*.py", "tests/**/*.py"]
---

# Implement

Execute implementation tasks with strict guardrails: verify → edit → test → lint → commit.

**Shortcut**: `::implement`

**Works with**: `modules/types-as-contracts`, `modules/architecture-patterns`, `modules/evidence-handling`

---

## Principle

> **NEVER invent APIs or behavior. Always verify against code/tests first.**

---

## Guardrails

1. **Verify Before Edit** - Read target files first
2. **Minimal Edits** - Change only what's necessary
3. **Preserve Style** - Match existing code patterns
4. **Type Safety** - Maintain or improve type hints
5. **Test Coverage** - Update/add tests for changes
6. **Lint Clean** - Fix all linter errors

---

## Procedure

### Step 1: Pre-Implementation Verification

**Before any edits**:

```yaml
1. Read target files:
   - Understand current implementation
   - Note existing patterns and style

2. Search for usages:
   grep -rn "function_name" bengal/

3. Check existing tests:
   grep -rn "test.*function_name" tests/

4. Verify assumptions:
   - Does RFC/plan match reality?
   - If not, STOP and update plan
```

### Step 2: Focused Editing

**Edit cycle**:

```yaml
1. One task at a time:
   - Focus on single task from plan
   - Complete before moving on

2. Minimal edit:
   - Use search_replace for targeted changes
   - Keep surrounding code intact

3. Type hints:
   - Add/update type hints
   - Use modern syntax (str | None, not Optional[str])

4. Docstrings:
   - Update if API changes
   - Google style format
```

**Example edit**:
```python
# Before
def build(self):
    """Build the site."""
    self.render_all_pages()

# After
def build(self, incremental: bool = False) -> None:
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

**For each code change**:

```yaml
unit_tests: tests/unit/test_{module}.py
  - Test new behavior
  - Update assertions for changed behavior
  - Add edge cases

integration_tests: tests/integration/test_{feature}.py
  - Test end-to-end workflows
  - Verify subsystem interactions
```

**Test structure**:
```python
def test_incremental_build_only_rebuilds_changed(tmp_path):
    """Incremental build should only rebuild changed pages."""
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

### Step 4: Lint and Type Check

**After each edit**:

```bash
# Check for lint errors
read_lints bengal/path/to/file.py

# Run mypy on changed files
mypy bengal/path/to/file.py

# Fix any issues before continuing
```

### Step 5: Atomic Commit

**After task complete (code + tests + lint)**:

```bash
git add -A && git commit -m "<scope>: <description>"
```

**Commit format**:
```yaml
scope: core, orchestration, rendering, cache, health, cli, tests, docs
examples:
  - "core: add incremental build state tracking"
  - "orchestration: parallelize asset processing"
  - "tests: add integration tests for taxonomy index"
```

---

## Output Format

```markdown
## ✅ Implementation: [Task]

### Executive Summary
[2-3 sentences: what was implemented, files changed, confidence]

### Changes Made

#### Code Changes
- **File**: `bengal/core/site.py`
  - Added `incremental: bool` parameter to `build()`
  - Implemented conditional rendering logic
  - Lines changed: 15

#### Test Changes
- **File**: `tests/unit/test_site.py`
  - Added `test_incremental_build_only_rebuilds_changed`
  - Added `test_incremental_build_with_dependencies`
  - Lines added: 45

### Validation
- ✅ Linter passed
- ✅ mypy passed
- ✅ Unit tests pass (42/42)
- ✅ Integration tests pass (12/12)

### Commit
```bash
git add -A && git commit -m "core: add incremental build mode"
```

**Status**: ✅ Ready to commit

### 📋 Next Steps
- [ ] Continue to next task in plan
- [ ] Or run `::validate` for full audit
```

---

## Error Handling

### Linter Fails

```yaml
1. Read lint errors
2. Analyze root cause
3. Fix issues
4. Re-lint
5. Continue
```

### Tests Fail

```yaml
1. Read test output
2. Diagnose: logic error? test error? integration issue?
3. Fix code or test
4. Re-run tests
5. Continue
```

### Assumptions Violated

```yaml
1. STOP implementation
2. Document discrepancy
3. Update RFC/plan
4. Get confirmation before proceeding
```

---

## Quality Checklist

Before committing:

- [ ] **Code changes minimal** - Only what's needed
- [ ] **Style matches** - Consistent with existing code
- [ ] **Type hints** - All new code typed
- [ ] **Docstrings** - Updated for API changes
- [ ] **Unit tests** - Added/updated
- [ ] **Integration tests** - Pass
- [ ] **Linter** - No new errors
- [ ] **mypy** - No new errors
- [ ] **Commit message** - Descriptive, scoped

---

## Confidence Requirements

| Module | Required Confidence |
|--------|---------------------|
| `bengal/core/` | 90% |
| `bengal/orchestration/` | 90% |
| Other modules | 85% |

If confidence < requirement, run `::validate` before committing.

---

## Related

- `modules/types-as-contracts` - Type-first approach
- `modules/architecture-patterns` - Model/orchestrator split
- `implementation/type-first` - Type-first development
- `implementation/core-model` - Core model changes
- `commands/validate` - Full validation
