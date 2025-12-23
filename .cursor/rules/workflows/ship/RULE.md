---
description: Pre-release workflow - validate → retro → changelog update
alwaysApply: false
---

# Ship Workflow

Pre-merge/pre-release validation and documentation.

**Shortcut**: `::workflow-ship`

**Output**: Validated changes ready to merge, changelog updated

---

## When to Use

- **Feature complete** - Implementation done
- **Pre-merge check** - Before merging PR
- **Pre-release** - Before version bump
- **Quality gate** - Ensure confidence thresholds met

---

## Workflow Chain

```yaml
1. ::validate (10-15 min)
   Input: Current branch/changes
   Output: Confidence scores and verification
   Gate: Must pass quality gates

2. ::retro (5 min)
   Input: Validation results
   Output: Summary of what was done and lessons learned

3. Changelog update (5 min)
   Input: Retro summary
   Output: changelog.md entry

4. Plan cleanup
   Action: Move plan docs to ready/ or delete
```

**Total time**: 20-30 minutes

---

## Procedure

### Phase 1: Validate

```yaml
command: ::validate
scope: All uncommitted changes or feature branch

checks:
  - Deterministic: mypy, ruff, pytest
  - Claims: 3-path validation for HIGH criticality
  - Confidence: Score all changes

gates:
  core_modules: 90%
  other_modules: 85%

status:
  PASS: All gates met → Continue
  CONDITIONAL: Review warnings → User decision
  FAIL: Must fix issues → Stop
```

### Phase 2: Retrospective

```yaml
command: ::retro
sections:
  - What was implemented
  - Key decisions made
  - Challenges encountered
  - Lessons learned
  - Technical debt introduced (if any)
```

### Phase 3: Changelog Update

```yaml
action: Update changelog.md
format:
  ## [Unreleased]

  ### Added
  - [Feature description] (#PR if applicable)

  ### Changed
  - [Change description]

  ### Fixed
  - [Bug fix description]
```

### Phase 4: Plan Cleanup

```yaml
if plan_docs_exist:
  action: Delete from plan/ready/
  reason: Work is done, tracked in git + changelog

note: "Completed work is documented in changelog, not archived"
```

---

## Output

At the end of this workflow:

1. **Validation report** with passing gates
2. **Retro notes** documenting what was done
3. **Changelog entry** for the release
4. **Clean plan directory** (no stale docs)
5. **Ready to merge/release**

---

## Example

```text
User: "::workflow-ship"

AI:
  Phase 1 - Validate (12 min):
    Scope: feature/incremental-build branch

    Deterministic:
      - mypy: ✅ 0 errors
      - ruff: ✅ 0 issues
      - pytest: ✅ 156/156 passed

    Claims validated: 8
      - HIGH criticality: 3 (avg 94%)
      - MEDIUM criticality: 4 (avg 88%)
      - LOW criticality: 1 (95%)

    Gates:
      - core (90%): ✅ 94%
      - other (85%): ✅ 88%

    Status: ✅ PASS

  Phase 2 - Retro (5 min):
    ## Retro: Incremental Build

    ### What was done
    - Added incremental build mode to Site.build()
    - Implemented change detection via file mtimes
    - Added dependency tracking for cross-page refs

    ### Key decisions
    - Used mtime-based detection (simpler than hash)
    - Stored deps in JSON (not SQLite)

    ### Lessons
    - Dependency tracking more complex than expected
    - Consider hash-based detection for v2

  Phase 3 - Changelog:
    ## [Unreleased]

    ### Added
    - Incremental build mode: `bengal build --incremental`
      rebuilds only changed pages
    - Dependency tracking for cross-page references

  Phase 4 - Cleanup:
    - Deleted: plan/ready/rfc-incremental-build.md
    - Deleted: plan/ready/plan-incremental-build.md

  Status: ✅ Ready to merge
```

---

## Failure Modes

### Validation Fails

```yaml
status: FAIL
action:
  1. Review failures
  2. Fix issues (::implement)
  3. Re-run ::workflow-ship
```

### Conditional Pass

```yaml
status: CONDITIONAL
warnings:
  - [List of warnings]

action:
  User choice:
    - "Fix warnings" → Address issues first
    - "Accept risks" → Continue with known issues documented
```

---

## Quality Gates

| Module | Required | What Happens if Fail |
|--------|----------|---------------------|
| `bengal/core/` | 90% | Must fix before merge |
| `bengal/orchestration/` | 90% | Must fix before merge |
| Other modules | 85% | Review, can accept with justification |

---

## Related

- `commands/validate` - Deep validation
- `commands/retro` - Retrospective
- `workflows/feature` - Full feature workflow
- `workflows/fix` - Bug fix workflow
