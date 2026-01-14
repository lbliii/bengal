---
description: Full feature development workflow - research → RFC → plan (ready for implementation)
alwaysApply: false
---

# Feature Workflow

Full feature development flow from research through planning.

**Shortcut**: `::workflow-feature`

**Output**: RFC + Plan ready for implementation

---

## When to Use

- Starting a **new feature** from scratch
- Need **full design documentation**
- **Architectural changes** required
- Want to think through before coding

---

## Workflow Chain

```yaml
1. ::research (10-15 min)
   Input: Feature description
   Output: Evidence-backed understanding of current state

2. ::rfc (15-20 min)
   Input: Research findings
   Output: RFC with design options and recommendation

3. Review checkpoint
   Action: User reviews RFC
   Gate: Confidence ≥ 85%

4. ::plan (10 min)
   Input: Approved RFC
   Output: Actionable task list with commits
```

**Total time**: 35-45 minutes

---

## Procedure

### Phase 1: Research

```yaml
command: ::research
focus:
  - Current implementation in affected modules
  - Related tests
  - Architecture patterns in use
  - Similar features for patterns

output:
  - Claims about current state
  - Gaps identified
  - Confidence scores
```

### Phase 2: RFC

```yaml
command: ::rfc
sections:
  - Executive Summary
  - Problem Statement (with evidence)
  - Goals and Non-Goals
  - Design Options (at least 2)
  - Recommended Approach
  - Architecture Impact
  - Risks and Mitigations
  - Implementation Plan outline

gate: Confidence ≥ 85%
```

### Phase 3: User Review

```markdown
## 📋 RFC Review Checkpoint

**RFC**: [Title]
**Confidence**: [N]% [emoji]

Please review:
- [ ] Problem statement accurate?
- [ ] Goals align with your needs?
- [ ] Recommended approach acceptable?
- [ ] Risks understood?

**Options**:
- "Looks good" → Continue to planning
- "Change [X]" → Revise RFC
- "Need more research on [Y]" → Additional research
```

### Phase 4: Plan

```yaml
command: ::plan
output:
  - Task breakdown by subsystem
  - Dependency order
  - Pre-drafted commit messages
  - Test requirements per task
  - Estimated effort
```

---

## Output

At the end of this workflow, you have:

1. **RFC document** in `plan/drafted/rfc-[name].md`
   - Evidence-backed problem statement
   - Analyzed design options
   - Clear recommendation
   - Architecture impact documented

2. **Plan document** in `plan/drafted/plan-[name].md`
   - Atomic tasks
   - Ordered by dependency
   - Ready for `::implement`

---

## Example

```text
User: "::workflow-feature - add pagination to page collections"

AI:
  Phase 1 - Research (12 min):
    - Found: bengal/core/page/collection.py handles collections
    - Found: No existing pagination support
    - Found: Similar pattern in taxonomy_index.py
    - Confidence: 88%

  Phase 2 - RFC (18 min):
    - Problem: Large collections hurt build time and page load
    - Option A: Client-side pagination
    - Option B: Build-time pagination (recommended)
    - Option C: Hybrid approach
    - Architecture impact: New PaginatedCollection type
    - Confidence: 91%

  Checkpoint:
    "RFC ready for review. Confidence 91%. Proceed with planning?"

  Phase 3 - Plan (8 min):
    - Task 1.1: Define PaginatedPage type
    - Task 1.2: Add pagination config to bengal.toml schema
    - Task 2.1: Implement PaginationOrchestrator
    - Task 2.2: Add pagination template helpers
    - Task 3.1: Add unit tests
    - Task 3.2: Add integration tests
```

---

## Next Steps After Workflow

```yaml
ready_for:
  - ::implement (execute tasks from plan)
  - Manual implementation following plan

follow_up:
  - ::validate (after implementation)
  - ::retro (after shipping)
```

---

## Related

- `commands/research` - Evidence extraction
- `commands/rfc` - RFC drafting
- `commands/plan` - Task breakdown
- `workflows/fix` - Simpler workflow for fixes
- `workflows/ship` - Pre-release validation
