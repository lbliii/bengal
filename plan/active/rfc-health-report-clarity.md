# RFC: Health Check Report Clarity Refactor

**Status**: Draft  
**Author**: AI Assistant  
**Created**: 2025-12-11  
**Updated**: 2025-12-11  
**Related**: `bengal/health/report.py`, `bengal/health/base.py`

---

## Problem Statement

The health check data model has a conceptual mismatch between what it tracks internally and what users/developers care about. While **console output has been improved**, the underlying data model still causes confusion.

### Current Console Output (Already Improved)

The console output now correctly shows validator-level status:

```
🏥 Health Check Summary
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Issues:

  ❌ Links (1 error(s))
    • 6 broken internal link(s)
      content/docs/building/troubleshooting/_index.md: template-errors.md

  ⚠️ Directives (1 warning(s))
    • 3 page(s) have heavy directive usage (>10 directives)

✓ 1 validator(s) passed
   Output

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Summary: 1 error(s), 1 warning(s)
Build Quality: 75% (Good)
```

### Remaining Data Model Issues

**1. Confusing `passed_count` property:**

```python
# ValidatorReport.passed_count (report.py:301-303)
@property
def passed_count(self) -> int:
    """Count of successful checks."""
    return sum(1 for r in self.results if r.status == CheckStatus.SUCCESS)
```

This counts `CheckStatus.SUCCESS` results, which are **rarely emitted** due to the "silence is golden" pattern. Result: `passed_count` is usually 0, even for validators that found no problems.

**2. JSON output includes misleading `passed` field:**

```json
{
  "summary": {
    "passed": 0,  // Confusing: 0 passed but no errors?
    "warnings": 1,
    "errors": 0
  },
  "validators": [
    {
      "name": "Output",
      "summary": {
        "passed": 0,  // Did Output pass or not?
        "warnings": 0,
        "errors": 0
      }
    }
  ]
}
```

**3. No formal `ValidatorStatus` enum:**

Developers must infer validator status from `has_problems` boolean or check error/warning counts manually. No explicit enum for "this validator is clean/has-warnings/has-errors".

---

## Root Cause Analysis

The data model conflates two different concepts:

### Concept 1: Validator Status (What Users Care About)
- Does this validator have problems? (clean vs has-warnings vs has-errors)
- This is the **validator-level** view

### Concept 2: Individual Check Results  
- Each validator emits `CheckResult` objects with `CheckStatus`
- `CheckStatus.SUCCESS` exists but is **rarely used**
- `passed_count` counts SUCCESS results → usually 0

### Evidence: "Silence is Golden" Pattern

**BaseValidator docstring** (`bengal/health/base.py:40`):
```python
# No success message - if no errors, silence is golden
```

**25 instances across validators** following this pattern:
- `sitemap.py` (4 instances)
- `rss.py` (3 instances)
- `output.py` (4 instances)
- `links.py` (1 instance)
- `fonts.py` (3 instances)
- `directives/checkers.py` (3 instances)
- `config.py` (2 instances)
- `assets.py` (3 instances)
- `base.py` (2 instances)

**All 18 validators** follow this pattern - they only report issues, not successes.

### The Terminology Problem

| Term | Location | Meaning | Problem |
|------|----------|---------|---------|
| `passed_count` | `ValidatorReport` | Count of SUCCESS results | Usually 0 |
| `total_passed` | `HealthReport` | Sum of `passed_count` | Usually 0 |
| `has_problems` | `ValidatorReport` | Has warnings/errors | What users care about |
| `validators_passed` | Console output | Validators without problems | Different from `passed_count`! |
| `"passed"` | JSON output | `total_passed` value | Confusing (usually 0) |

---

## Goals

1. **Clear data model** - Terminology matches user mental model
2. **Consistent terminology** - "passed" means the same thing everywhere
3. **Validator-centric API** - Formal `ValidatorStatus` enum for programmatic use
4. **JSON output clarity** - Remove or rename misleading `passed` field
5. **Backward compatibility** - Deprecate rather than remove existing properties

## Non-Goals

- Changing how validators produce results (keep "silence is golden")
- Changing console output format (already good)
- Adding new validator functionality

---

## Design Options

### Option A: Add ValidatorStatus Enum (Recommended)

**Add formal validator-level status without removing existing properties.**

#### New Data Model Additions

```python
class ValidatorStatus(Enum):
    """High-level status of a validator run."""
    CLEAN = "clean"           # No warnings or errors
    HAS_WARNINGS = "warnings" # Has warnings but no errors
    HAS_ERRORS = "errors"     # Has errors

@dataclass
class ValidatorReport:
    # ... existing fields unchanged ...

    @property
    def status(self) -> ValidatorStatus:
        """Overall validator status (clean/warnings/errors)."""
        if self.error_count > 0:
            return ValidatorStatus.HAS_ERRORS
        elif self.warning_count > 0:
            return ValidatorStatus.HAS_WARNINGS
        return ValidatorStatus.CLEAN

    @property
    def is_clean(self) -> bool:
        """True if validator found no warnings or errors."""
        return self.status == ValidatorStatus.CLEAN

@dataclass
class HealthReport:
    # ... existing fields unchanged ...

    @property
    def validators_clean(self) -> int:
        """Count of validators with no problems."""
        return sum(1 for vr in self.validator_reports if vr.is_clean)

    @property
    def validators_with_warnings(self) -> int:
        """Count of validators with warnings (but no errors)."""
        return sum(1 for vr in self.validator_reports
                   if vr.status == ValidatorStatus.HAS_WARNINGS)

    @property
    def validators_with_errors(self) -> int:
        """Count of validators with errors."""
        return sum(1 for vr in self.validator_reports
                   if vr.status == ValidatorStatus.HAS_ERRORS)
```

#### JSON Output Changes

```json
{
  "summary": {
    "validators_clean": 1,
    "validators_with_warnings": 1,
    "validators_with_errors": 1,
    "total_warnings": 3,
    "total_errors": 2,
    "quality_score": 75,
    "quality_rating": "Good",
    // Deprecated fields (kept for compatibility):
    "passed": 0,
    "total_checks": 5
  },
  "validators": [
    {
      "name": "Output",
      "status": "clean",  // NEW: clear validator status
      "summary": {
        "warnings": 0,
        "errors": 0,
        // Deprecated:
        "passed": 0
      }
    }
  ]
}
```

#### Pros
- Clear, unambiguous API
- Aligns with how validators actually work
- Backward compatible (existing properties unchanged)
- Supports both console and programmatic use

#### Cons
- Adds new properties (minor complexity)
- Deprecated fields still present in JSON

---

### Option B: Deprecate and Document

**Keep existing model, add documentation and deprecation warnings.**

#### Changes
- Add deprecation docstrings to `passed_count`, `total_passed`
- Add code comments explaining the "silence is golden" pattern
- Update JSON output docs to explain `passed` field

#### Pros
- Minimal code changes
- No breaking changes

#### Cons
- Doesn't fix the conceptual mismatch
- JSON output still confusing
- No `ValidatorStatus` for programmatic use

---

### Option C: Full Refactor (Breaking)

**Remove SUCCESS tracking entirely, rename properties.**

#### Changes
- Remove `CheckStatus.SUCCESS`
- Remove `passed_count`, `total_passed`
- Remove `passed` from JSON output
- Rename to issue-only model

#### Pros
- Cleanest conceptual model
- No confusing terminology

#### Cons
- Breaking changes to API and JSON output
- May break external tooling
- SUCCESS could be useful for future validators

---

## Recommendation

**Option A: Add ValidatorStatus Enum**

Rationale:
1. Provides clear validator-level API without breaking changes
2. `ValidatorStatus` enum enables clean programmatic checks
3. JSON output gains meaningful `status` field
4. Existing properties deprecated gracefully
5. Console output already uses validator-centric language

---

## Implementation Plan

### Phase 1: Add ValidatorStatus (Non-Breaking)

**Files**: `bengal/health/report.py`

1. Add `ValidatorStatus` enum (CLEAN, HAS_WARNINGS, HAS_ERRORS)
2. Add `ValidatorReport.status` property
3. Add `ValidatorReport.is_clean` property
4. Add `HealthReport.validators_clean` property
5. Add `HealthReport.validators_with_warnings` property
6. Add `HealthReport.validators_with_errors` property

### Phase 2: Update JSON Output

**Files**: `bengal/health/report.py`

1. Add `status` field to validator JSON
2. Add `validators_clean/warnings/errors` to summary
3. Keep deprecated fields for compatibility

### Phase 3: Add Deprecation Notices

**Files**: `bengal/health/report.py`

1. Add deprecation docstrings to:
   - `ValidatorReport.passed_count`
   - `HealthReport.total_passed`
2. Add code comments explaining "silence is golden"

### Phase 4: Update Tests

**Files**: `tests/unit/test_health_report.py`

1. Add tests for `ValidatorStatus` enum
2. Add tests for new properties
3. Add tests for JSON output changes
4. Verify deprecated properties still work

---

## Files Affected

| File | Changes |
|------|---------|
| `bengal/health/report.py` | Add `ValidatorStatus`, new properties, update JSON |
| `tests/unit/test_health_report.py` | Add tests for new API |

---

## Migration Notes

### For Console Users
- No changes needed (output already improved)

### For JSON Consumers
- New fields available: `status`, `validators_clean`, etc.
- Existing `passed` fields still work (deprecated)
- Recommend migrating to `status` field

### For Python API Users
- New `ValidatorStatus` enum available
- New properties: `is_clean`, `validators_clean`, etc.
- Existing `passed_count` still works (deprecated)

---

## Open Questions

1. **Should we remove `passed` from JSON in v1.0?**
   - Keep deprecated for 0.x releases
   - Consider removal in major version bump

2. **Should `CheckStatus.SUCCESS` be removed entirely?**
   - Currently rarely used
   - Could keep for future validators that want explicit success messages
   - Recommend: Keep but document as optional

3. **Should verbose mode show validator status badges?**
   - E.g., `✅ Output [CLEAN]` vs `❌ Links [ERRORS]`
   - Current format already clear, may be redundant

---

## Success Criteria

- [ ] `ValidatorStatus` enum exists with CLEAN/HAS_WARNINGS/HAS_ERRORS
- [ ] `ValidatorReport.status` returns appropriate enum value
- [ ] `HealthReport.validators_clean` counts validators without problems
- [ ] JSON output includes `status` field per validator
- [ ] Existing `passed_count` still works (backward compatible)
- [ ] Tests cover all new properties
- [ ] Deprecation docstrings added

---

## References

- `bengal/health/report.py` - Current implementation
- `bengal/health/base.py:40` - "silence is golden" pattern
- `bengal/health/validators/*.py` - 18 validators following pattern
