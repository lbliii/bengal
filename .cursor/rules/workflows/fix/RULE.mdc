---
description: Quick fix workflow - research → plan → implement → validate
alwaysApply: false
---

# Fix Workflow

Quick fix cycle for bugs and small improvements.

**Shortcut**: `::workflow-fix`

**Output**: Validated fix with tests and commit

---

## When to Use

- **Bug fixes** - Something is broken
- **Small improvements** - Clear, scoped changes
- **No RFC needed** - Changes are straightforward
- **Time-sensitive** - Need to ship quickly

---

## Workflow Chain

```yaml
1. ::research (5-10 min)
   Input: Bug description or improvement request
   Output: Understanding of current behavior and root cause

2. ::plan (5 min)
   Input: Research findings
   Output: Simple task list (often 1-3 tasks)

3. ::implement (varies)
   Input: Plan
   Output: Code changes + tests + commit

4. ::validate (5-10 min)
   Input: Implementation
   Output: Confidence score and verification
```

**Total time**: 25-40 minutes (varies with fix complexity)

---

## Procedure

### Phase 1: Quick Research

```yaml
command: ::research
focus:
  - Where is the bug/code located?
  - What's the current behavior?
  - What's the expected behavior?
  - Are there existing tests?

depth: Targeted, not exhaustive
output: Root cause identification
```

### Phase 2: Quick Plan

```yaml
command: ::plan
format: Simple task list

example:
  - [ ] Fix: [specific code change]
  - [ ] Test: Add test for [scenario]
  - [ ] Verify: Run existing tests
```

### Phase 3: Implement

```yaml
command: ::implement
guardrails:
  - Minimal changes
  - Add regression test
  - Run linter
  - Run related tests

commit: Atomic commit with fix description
```

### Phase 4: Validate

```yaml
command: ::validate
checks:
  - Tests pass (especially new test)
  - No regressions
  - Linter clean
  - Type check passes

gate: Confidence ≥ 85% (or 90% for core)
```

---

## Output

At the end of this workflow:

1. **Fix committed** with descriptive message
2. **Regression test** added
3. **Validation report** with confidence
4. **Ready to push/merge**

---

## Example

```text
User: "::workflow-fix - PageCore.to_dict() doesn't serialize date properly"

AI:
  Phase 1 - Research (6 min):
    - Found: bengal/core/page/page_core.py:145
    - Issue: datetime not converted to ISO string
    - Test gap: test_page_core.py tests to_dict but not date field
    - Confidence: 92%

  Phase 2 - Plan (3 min):
    - [ ] Fix date serialization in to_dict()
    - [ ] Add test for date in to_dict()
    - [ ] Verify cache round-trip works

  Phase 3 - Implement (15 min):
    - Modified: page_core.py:147 - date.isoformat() if date
    - Added: test_page_core.py - test_to_dict_serializes_date
    - Linter: ✅
    - Tests: ✅ 42/42

  Phase 4 - Validate (5 min):
    - Path A (Source): ✅ Fix verified
    - Path B (Tests): ✅ New test covers it
    - Path C (Config): N/A
    - Confidence: 95% 🟢

  Commit:
    git add -A && git commit -m "core: fix datetime serialization in PageCore.to_dict()"

  Status: ✅ Ready to push
```

---

## Skip Planning?

For **trivial fixes**, you can skip directly to implement:

```yaml
trivial_criteria:
  - One-line fix
  - Obvious root cause
  - Clear what to test

command: ::implement (skip ::research ::plan)
```

---

## Escalate to Feature Workflow?

If during research you discover:
- **Larger scope** than expected
- **Design decisions** needed
- **Multiple approaches** possible

Then escalate:
```yaml
escalate: ::workflow-feature
reason: "Discovered [X] requires design decision"
```

---

## Related

- `commands/research` - Evidence extraction
- `commands/plan` - Task breakdown
- `commands/implement` - Code changes
- `commands/validate` - Validation
- `workflows/feature` - Full feature workflow
