---
description: Convert RFCs into actionable, atomic task lists grouped by subsystem with pre-drafted commits
globs: ["plan/active/*.md"]
alwaysApply: false
---

# Bengal Planning & Breakdown

**Purpose**: Convert RFCs or high-level requests into actionable task lists with clear outcomes.

**Shortcut**: `::plan`

**Input**: RFC or direct user request.

**Output**: Structured plan in `plan/active/plan-[name].md` and/or TODO items.

---

## Overview

Breaks down design proposals into atomic, executable tasks grouped by Bengal subsystem. Each task maps to one atomic commit with pre-drafted commit messages.

---

## Planning Principles

1. **Atomic Tasks**: Each task maps to one atomic commit
2. **Grouped by Area**: Organize by Bengal subsystem or module
3. **Dependencies Clear**: Sequential vs parallel tasks
4. **Validation Built-in**: Include test, lint, health check tasks
5. **Confidence Gates**: Define quality thresholds

---

## Procedure

### Step 1: Parse Input

- If RFC exists, extract implementation phases and details
- If direct request, use context analysis to scope

### Step 2: Task Breakdown

**Task Structure**:
```yaml
task:
  id: "[unique-id]"
  description: "[Action-oriented description]"
  area: "[Core/Orchestration/Rendering/Cache/Health/CLI/Tests/Docs]"
  files: ["bengal/module/file.py", ...]
  dependencies: ["[task-id]", ...]
  status: "[pending/in_progress/completed/cancelled]"
  confidence_gate: [percentage threshold for completion]
  commit_message: "[scope]: [description]"  # Pre-drafted atomic commit
```

### Step 3: Group and Sequence

**Phases**:
1. **Foundation**: Core infrastructure, breaking changes
2. **Implementation**: Primary functionality
3. **Validation**: Tests, lints, health checks
4. **Polish**: Documentation, examples, refinements

**Within each phase**, group by:
- **Core Changes**: `bengal/core/`
- **Orchestration Changes**: `bengal/orchestration/`
- **Rendering Changes**: `bengal/rendering/`
- **Cache Changes**: `bengal/cache/`
- **Health Changes**: `bengal/health/`
- **CLI Changes**: `bengal/cli/`
- **Tests**: `tests/unit/`, `tests/integration/`
- **Documentation**: `architecture/`, `README.md`, etc.

### Step 4: Add Validation Tasks

For each implementation task, add:
- **Test Task**: Write/update tests
- **Lint Task**: Run linter, fix issues
- **Health Check**: Verify subsystem validators pass

---

## Output Format

Plan saved to `plan/active/plan-[name].md`:

```markdown
## 📋 Implementation Plan: [Name]

### Executive Summary
[2-3 sentences: what we're building, estimated complexity, timeline]

### Plan Details
- **Total Tasks**: [N]
- **Estimated Time**: [hours/days]
- **Complexity**: [Simple/Moderate/Complex]
- **Confidence Gates**: RFC ≥85%, Implementation ≥90%

---

## Phase 1: Foundation ([N] tasks)

### Core Changes (`bengal/core/`)

#### Task 1.1: [Description]
- **Files**: `bengal/core/site.py`
- **Action**: [Specific changes]
- **Dependencies**: None
- **Status**: pending
- **Commit**: `core: add incremental build state tracking`

#### Task 1.2: [Description]
[Similar structure]

---

### Tests (`tests/unit/`)

#### Task 1.3: Add unit tests for incremental build state
- **Files**: `tests/unit/test_site.py`
- **Dependencies**: Task 1.1
- **Status**: pending
- **Commit**: `tests(core): add unit tests for incremental build state`

---

## Phase 2: Implementation ([N] tasks)

[Similar structure for remaining tasks]

---

## Phase 3: Validation ([N] tasks)

### Validation Checklist
- [ ] All unit tests pass
- [ ] All integration tests pass
- [ ] Linter passes (no new errors)
- [ ] Health validators pass
- [ ] Performance benchmarks within tolerance

---

## Phase 4: Polish ([N] tasks)

### Documentation
- [ ] Update `architecture/[subsystem].md`
- [ ] Update `CHANGELOG.md`
- [ ] Add examples if user-facing

---

## 📊 Task Summary

| Area | Tasks | Status |
|------|-------|--------|
| Core | [N] | pending |
| Orchestration | [N] | pending |
| Rendering | [N] | pending |
| Cache | [N] | pending |
| Health | [N] | pending |
| CLI | [N] | pending |
| Tests | [N] | pending |
| Docs | [N] | pending |

---

## 📋 Next Steps
- [ ] Review plan for completeness
- [ ] Begin Phase 1 with `::implement`
- [ ] Track progress in this document (update task statuses)
```

**Also create TODO items** (if using todo_write tool):
```yaml
todos:
  - id: "impl-1-1"
    content: "core: add incremental build state tracking"
    status: "pending"
  - id: "impl-1-2"
    content: "orchestration: wire incremental state through render pipeline"
    status: "pending"
  [...]
```

---

## Prompting Techniques

- **Example-guided**: Use task structure template
- **Chain-of-Thought**: Explicit dependencies and sequencing reasoning

---

## Quality Checklist

Before finalizing plan:
- [ ] Tasks grouped by subsystem and phase
- [ ] Dependencies clear (sequential vs parallel)
- [ ] Each task maps to atomic commit
- [ ] Commit messages pre-drafted
- [ ] Validation tasks included (tests, lints, health)
- [ ] Confidence gates defined
- [ ] Estimated time reasonable
- [ ] Confidence ≥ 85%
