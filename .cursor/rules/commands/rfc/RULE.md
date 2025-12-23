---
description: Draft RFC with evidence-backed design options and recommendations
alwaysApply: false
globs: ["plan/**/*.md"]
---

# RFC Drafting

Draft design proposals with evidence-backed options. Part of the RFC lifecycle:

```
::research → ::rfc → ::rfc-eval → ::plan → ::implement
           (draft)   (evaluate)
```

**Shortcut**: `::rfc`

**Works with**: `modules/evidence-handling`, `modules/output-format`

---

## Prerequisites

Before drafting an RFC, run `::research` to gather evidence. RFCs without evidence are speculation.

---

## Procedure

### Step 1: Create RFC File

```bash
# Create in plan/drafted/
plan/drafted/rfc-[short-kebab-name].md
```

### Step 2: Structure the RFC

Use this template:

```markdown
# RFC: [Title]

**Status**: Draft
**Created**: [date]
**Author**: [name]
**Confidence**: [N]% [emoji]
**Category**: [Core / Orchestration / Rendering / Cache / CLI]

---

## Executive Summary

[2-3 sentences: what problem, what solution, why now]

---

## Problem Statement

### Current State
[What exists today, with evidence from ::research]

**Evidence**:
- `bengal/module/file.py:45` - [what it shows]
- `tests/unit/test_file.py:89` - [what it proves]

### Pain Points
- [Problem 1 with evidence]
- [Problem 2 with evidence]

### Impact
[Who is affected, how often, how severely]

---

## Goals and Non-Goals

### Goals
1. [Goal with measurable outcome]
2. [Goal with measurable outcome]

### Non-Goals
1. [Explicit exclusion and why]
2. [Explicit exclusion and why]

---

## Design Options

### Option A: [Name]

**Approach**: [1-2 sentence description]

**Implementation**:
```python
# Key code showing approach
```

**Pros**:
- [Benefit with evidence]

**Cons**:
- [Drawback with evidence]

**Estimated Effort**: [N] hours

---

### Option B: [Name]

[Same structure as Option A]

---

### Option C: [Name] (if applicable)

[Same structure]

---

## Recommended Approach

**Recommendation**: Option [X]

**Reasoning**:
1. [Reason with evidence]
2. [Reason with evidence]

**Trade-offs accepted**:
- [Accepted downside and mitigation]

---

## Architecture Impact

| Subsystem | Impact | Changes |
|-----------|--------|---------|
| `bengal/core/` | [High/Medium/Low/None] | [What changes] |
| `bengal/orchestration/` | ... | ... |
| `bengal/rendering/` | ... | ... |
| `bengal/cache/` | ... | ... |
| `tests/` | ... | ... |

---

## Risks and Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| [Risk 1] | [H/M/L] | [H/M/L] | [How to mitigate] |

---

## Open Questions

- [ ] [Question that needs resolution before implementation]
- [ ] [Question that can be resolved during implementation]

---

## Implementation Plan (High-Level)

### Phase 1: [Foundation]
- [Key deliverable]

### Phase 2: [Core Implementation]
- [Key deliverable]

### Phase 3: [Integration & Testing]
- [Key deliverable]

**Estimated Total Effort**: [N] hours

---

## References

- **Evidence**: [Links to ::research findings]
- **Related RFCs**: [If any]
- **External**: [If any]
```

### Step 3: Validate Critical Claims

For HIGH criticality claims (API, core behavior):
- Apply 3-path validation (Source + Test + Config)
- Document evidence inline

### Step 4: Calculate Confidence

```yaml
confidence = Evidence(40) + Consistency(30) + Recency(15) + Tests(15)

gate: RFC confidence ≥ 85% to proceed
```

---

## RFC Checklist

Before moving to `plan/evaluated/`:

- [ ] Problem statement has evidence (file:line)
- [ ] At least 2 design options analyzed
- [ ] Recommended option justified with evidence
- [ ] Architecture impact documented
- [ ] Risks identified with mitigations
- [ ] HIGH criticality claims have 3-path validation
- [ ] Confidence ≥ 85%

---

## Next Steps

After drafting:
1. `::rfc-eval` - Evaluate the RFC
2. Move to `plan/evaluated/` when reviewed
3. `::plan` - Convert to tasks when approved
4. Move to `plan/ready/` when ready to implement

---

## Related

- `commands/research` - Gather evidence first
- `commands/rfc-eval` - Evaluate RFC
- `commands/plan` - Convert RFC to tasks
- `workflows/feature` - Full design flow

