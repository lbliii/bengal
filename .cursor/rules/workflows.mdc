---
description: Pre-built workflow chains for common development scenarios
globs: ["**/*.py", "**/*.md"]
alwaysApply: false
---

# Bengal Workflow Templates

**Purpose**: Pre-built workflow chains for common scenarios.

**Shortcuts**: `::workflow-feature`, `::workflow-fix`, `::workflow-ship`, `::workflow-full`

---

## Overview

Pre-built sequences of rules for common development workflows. Chains multiple rules together with checkpoints and progress tracking.

---

## Workflow 1: Full Feature (`::workflow-feature`)

**Chain**: Context Analysis → Research → RFC → Plan

**Use Case**: Designing a new feature from scratch

**Estimated Time**: 20-40 minutes (depending on feature complexity)

### Steps

1. **Context Analysis**
   - Understand current subsystems
   - Identify integration points
   - Duration: ~3 minutes

2. **Research**
   - Gather evidence from codebase
   - Extract claims about related functionality
   - Identify extension points
   - Duration: ~10 minutes

3. **RFC**
   - Draft design proposal
   - Analyze options and tradeoffs
   - 3-path validation for critical claims
   - Duration: ~15 minutes

4. **Plan**
   - Break down into tasks
   - Group by subsystem and phase
   - Add validation tasks
   - Duration: ~10 minutes

### Output

Complete design package ready for `::implement`:
- Context report
- Research claims
- RFC document in `plan/active/rfc-[name].md`
- Implementation plan in `plan/active/plan-[name].md`

---

## Workflow 2: Quick Fix (`::workflow-fix`)

**Chain**: Research (focused) → Plan → Implement → Validate

**Use Case**: Fixing a bug or small improvement

**Estimated Time**: 25-40 minutes

### Steps

1. **Research** (focused)
   - Understand bug context
   - Find related code and tests
   - Duration: ~5 minutes

2. **Plan** (simplified)
   - 3-5 tasks: fix + test + lint
   - No formal RFC needed
   - Duration: ~5 minutes

3. **Implement**
   - Apply fix
   - Update/add tests
   - Run linter
   - Atomic commit
   - Duration: ~15 minutes

4. **Validate** (standard)
   - Quick validation (not deep)
   - Ensure tests pass
   - Confidence check
   - Duration: ~5 minutes

### Output

Fixed bug with tests and commit:
- Updated code files
- Test coverage
- Validation report
- Atomic commit

---

## Workflow 3: Pre-Release (`::workflow-ship`)

**Chain**: Validate (deep) → Retrospective → Changelog

**Use Case**: Preparing completed work for merge/release

**Estimated Time**: 20-30 minutes

### Steps

1. **Validate** (deep)
   - Full confidence scoring
   - 3-path self-consistency for critical changes
   - Comprehensive test check
   - Duration: ~10 minutes

2. **Retrospective**
   - Impact summary
   - Code references
   - Lessons learned
   - Duration: ~5 minutes

3. **Changelog**
   - Update `CHANGELOG.md`
   - Move planning docs to `plan/implemented/`
   - Duration: ~5 minutes

### Output

Ready-to-merge feature with documentation:
- Validation report (confidence ≥90%)
- Retrospective document
- Updated `CHANGELOG.md`
- Archived planning docs

---

## Workflow 4: Complete Cycle (`::workflow-full`)

**Chain**: Context → Research → RFC → Plan → Implement → Validate → Retro

**Use Case**: End-to-end feature development with full AI assistance

**Estimated Time**: 2-4 hours (depending on feature scope)

**Note**: This is a long workflow. Consider breaking it up with user checkpoints after RFC and after Plan.

### Steps

All rules executed in sequence:
1. Context Analysis (~3 min)
2. Research (~10 min)
3. RFC (~15 min)
4. Plan (~10 min)
5. **Checkpoint**: User reviews plan
6. Implement (~30-60 min per task)
7. Validate (~10 min)
8. Retrospective (~10 min)

### Output

Complete cycle from research to shipped feature:
- Full documentation package
- Implemented and tested code
- Validated with high confidence
- Changelog updated
- Ready for merge

---

## Workflow Execution

### Step 1: Confirmation

When user invokes a workflow:

```markdown
## 🎯 Workflow: [Name]

**Steps**: [list]
**Estimated Time**: [duration]
**Output**: [description]

Proceed? (yes/no)
```

### Step 2: Execute Chain

- Run each rule in sequence
- Pass output of one rule as input to next
- Show progress: "Step 1/4: Research..."

### Step 3: Checkpoints

Pause after major steps (RFC, Plan) for user review:

```markdown
## ⏸️ Checkpoint: RFC Complete

**Confidence**: 87% 🟢
**File**: `plan/active/rfc-incremental-build.md`

**Key Findings**:
- [Summary point 1]
- [Summary point 2]

Continue to Planning? (yes/no/revise)
```

### Step 4: Final Summary

```markdown
## ✅ Workflow Complete: [Name]

**Completed Steps**: [list]
**Outputs**: [files created]
**Overall Confidence**: [N]% 🟢

**Next Steps**: [recommendations]
```

---

## Custom Workflows

Users can also create custom workflow chains:

```text
::auto "research the cache system, then draft an RFC for optimization"
```

The orchestrator will:
1. Parse the request
2. Identify rule sequence: `research → rfc`
3. Execute chain with checkpoints

---

## Prompting Techniques

- **Chain-of-Thought**: Explicit reasoning between workflow steps
- **ReAct**: Reason about workflow progress, adapt if issues arise
- **Self-Monitoring**: Track progress and adjust if needed

---

## Integration

Workflows integrate with:
- **Orchestrator**: Routes workflow requests
- **All Rules**: Workflows chain individual rules
- **Context Analyzer**: Provides context at workflow start
- **Validation**: Gates between steps

Can be invoked:
- Explicitly via `::workflow-[name]`
- Via natural language: "walk me through building a feature"
- Via orchestrator when complex multi-step tasks detected
