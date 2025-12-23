---
description: Draft RFC with evidence-backed design options and recommendations
alwaysApply: false
globs: ["plan/**/*.md"]
---

# RFC

Draft design proposals with evidence-backed options.

**Shortcut**: `::rfc`

**Works with**: `modules/evidence-handling`, `modules/output-format`

---

## Output Structure

```markdown
# RFC: [Title]

**Status**: Draft
**Confidence**: [N]% [emoji]

---

## Executive Summary
[2-3 sentences]

## Problem Statement
[With evidence from ::research]

## Goals and Non-Goals

### Goals
- [Goal with evidence]

### Non-Goals
- [Explicit exclusions]

## Design Options

### Option A: [Name]
**Approach**: [Description]
**Pros**: [List]
**Cons**: [List]
**Evidence**: [file:line references]

### Option B: [Name]
[Same structure]

## Recommended Approach
[Option X] because [reasoning with evidence]

## Architecture Impact
| Subsystem | Impact | Changes |
|-----------|--------|---------|

## Risks and Mitigations
| Risk | Likelihood | Mitigation |

## Implementation Plan
[High-level phases]
```

---

## Confidence Gate

RFC must achieve **≥ 85%** confidence before proceeding to plan.

---

## Related

- `commands/research` - Gather evidence first
- `commands/plan` - Convert RFC to tasks
- `workflows/feature` - Full design flow

