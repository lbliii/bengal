---
description: Context-aware help system and comprehensive command reference (invoked via ::? or ::help from main OS)
globs: ["**/*"]
alwaysApply: false
---

# Bengal Help System

**Purpose**: Context-aware guidance and command reference.

**Shortcuts**:
- `::?` - Context-aware help ("what should I do here?")
- `::help` - Full command reference

---

## Overview

Provides intelligent assistance based on current context. Analyzes open files, git status, and subsystems to suggest relevant actions.

---

## Context-Aware Help (`::?`)

Analyzes current context and suggests relevant actions.

### Step 1: Gather Context

Use Context Analyzer to understand:
- Open files
- Git status (uncommitted changes, current branch)
- Recent activity
- Subsystems involved

### Step 2: Generate Suggestions

Based on context, suggest 3-5 relevant actions.

**Example Context**: User has uncommitted changes in `bengal/core/site.py` and `tests/unit/test_site.py`

**Output**:
```markdown
## 💡 Context-Aware Suggestions

### Current Context
- **Modified**: `bengal/core/site.py` (+50 lines), `tests/unit/test_site.py` (+30 lines)
- **Subsystem**: Core
- **Branch**: `feature/incremental-build`
- **Status**: Uncommitted changes

---

### Recommended Actions

1. **Validate Changes** (`::validate`)
   - Verify your core module changes with self-consistency
   - Check test coverage and confidence
   - Best for: Ensuring quality before commit

2. **Complete Implementation** (`::implement`)
   - Continue with implementation tasks from plan
   - Ensure linter passes, tests complete
   - Best for: If you're mid-implementation

3. **Create Retrospective** (`::retro`)
   - Document changes and update changelog
   - Move planning docs to implemented/
   - Best for: If implementation is complete

4. **Research Context** (`::research`)
   - Understand current Site class design
   - Find related code and dependencies
   - Best for: If you need more context before proceeding

5. **Get Full Plan** (`::plan`)
   - Generate detailed task breakdown
   - Structure remaining work
   - Best for: If you don't have a plan yet

---

### Quick Checks

- Run linter: `read_lints` on changed files
- Check tests: Run `pytest tests/unit/test_site.py`
- View plan: `cat plan/active/plan-*.md` (if exists)

Type the command shortcut (e.g., `::validate`) or describe what you want to do.
```

---

## Full Command Reference (`::help`)

Displays comprehensive command reference.

```markdown
## 📚 Bengal Rule System - Command Reference

### Core Commands

#### `::auto` - Intelligent Orchestration
Routes your request to the appropriate rule based on intent and context.

**Use when**: You're not sure which command to use, or want AI to decide.

**Example**: "Should we add caching to the taxonomy index?" → AI routes to `::rfc`

---

#### `::analyze` - Deep Context Analysis
Analyzes code, tests, git, and architecture context.

**Use when**: You need to understand the current state before planning or implementing.

**Output**: Detailed context report with subsystems, dependencies, complexity assessment.

---

#### `::research` - Evidence-First Research
Extracts verifiable claims from source code and tests.

**Use when**: You need to understand how a feature works or gather evidence for an RFC.

**Output**: Structured claims with code references, criticality, confidence scores.

---

#### `::rfc` - Draft RFC
Produces evidence-backed Request for Comments (RFC) for design decisions.

**Use when**: You need to propose a design or architectural change.

**Input**: Requires research evidence (run `::research` first or AI will do it automatically).

**Output**: RFC document in `plan/active/rfc-[name].md`

---

#### `::plan` - Planning & Task Breakdown
Converts RFCs or requests into actionable task lists.

**Use when**: You have an RFC and need to break it into implementation tasks.

**Output**: Plan document in `plan/active/plan-[name].md` with phased tasks

---

#### `::implement` - Implementation Driver
Guides code edits, test updates, and linting with guardrails.

**Use when**: You're ready to implement tasks from a plan.

**Guardrails**: Verifies before editing, preserves style, maintains tests, runs linter.

**Output**: Code changes + tests + lint fixes + atomic commit

---

#### `::validate` - Deep Validation
Audits changes/claims with self-consistency and confidence scoring.

**Use when**:
- Pre-commit validation
- Post-implementation verification
- Critical changes to core/orchestration

**Method**: 3-path self-consistency for HIGH criticality claims

**Output**: Confidence scores, evidence, action items

---

#### `::retro` - Retrospective & Changelog
Summarizes impact, updates changelog, archives planning docs.

**Use when**: Feature/change is complete and ready to merge.

**Output**: Impact summary, updated `CHANGELOG.md`, moved planning docs

---

#### `::improve` - Reflexion Loop
Iterative improvement through self-assessment and regeneration.

**Use when**: Validation reveals low confidence or artifacts have gaps.

**Process**: Validate → reflect → improve → re-validate (up to 3 iterations)

**Output**: Improved artifact with confidence improvement metrics

---

### Workflow Commands

#### `::workflow-feature` - Full Feature Workflow
**Chain**: `research → RFC → plan`

**Use when**: Starting a new feature from scratch

**Output**: Complete design package ready for implementation

---

#### `::workflow-fix` - Quick Fix Workflow
**Chain**: `research → plan → implement`

**Use when**: Fixing a bug or making a small improvement

**Output**: Focused plan + implementation + validation

---

#### `::workflow-ship` - Pre-Release Workflow
**Chain**: `validate → retro → changelog`

**Use when**: Preparing completed work for merge/release

**Output**: Validation report + retrospective + updated changelog

---

#### `::workflow-full` - Complete Cycle
**Chain**: `research → RFC → plan → implement → validate → retro`

**Use when**: End-to-end feature development with AI assistance

**Output**: Complete cycle from research to shipped feature

---

### Help Commands

#### `::?` - Context-Aware Help
Analyzes your current context and suggests relevant actions.

**Use when**: You're not sure what to do next

**Output**: 3-5 tailored suggestions

---

#### `::help` - Full Reference
Displays this complete command reference

---

### Natural Language Support

You can also describe what you want in plain English:

**Examples**:
- "How does the rendering pipeline handle Jinja templates?" → `::research`
- "Should we refactor the menu builder?" → `::rfc`
- "Break down the incremental build implementation" → `::plan`
- "Verify my rendering changes" → `::validate`
- "What should I do with these uncommitted changes?" → `::?`

---

### Quality Gates

- **RFC Confidence**: ≥ 85%
- **Plan Confidence**: ≥ 85%
- **Core Implementation**: ≥ 90%
- **Other Implementation**: ≥ 85%

---

### Confidence Scoring

**Formula**: Evidence (40) + Consistency (30) + Recency (15) + Tests (15) = 0-100%

**Interpretation**:
- 90-100%: HIGH 🟢 (ship it)
- 70-89%: MODERATE 🟡 (review recommended)
- 50-69%: LOW 🟠 (needs work)
- < 50%: UNCERTAIN 🔴 (do not ship)

---

### Bengal Subsystems

Commands are aware of these subsystems:

- **Core** (`bengal/core/`): Site, Page, Section, Asset, Theme
- **Orchestration** (`bengal/orchestration/`): Build, render, incremental
- **Rendering** (`bengal/rendering/`): Jinja, Markdown, shortcodes, filters
- **Cache** (`bengal/cache/`): Discovery, dependency tracking, indexes
- **Health** (`bengal/health/`): Validators, checks, reporting
- **CLI** (`bengal/cli/`): Commands, helpers, templates

---

### Tips

1. **Start with Research**: Use `::research` to understand before planning
2. **Use Workflows**: `::workflow-feature`, `::workflow-fix`, `::workflow-ship` save time
3. **Validate Often**: Run `::validate` before committing critical changes
4. **Let AI Decide**: Use `::auto` when unsure which command to use
5. **Iterate**: Use `::improve` to refine low-confidence outputs
6. **Get Help**: Type `::?` anytime you're stuck

---

Need help? Just ask in plain English or type `::?` for context-aware suggestions!
```

---

## Prompting Techniques

- **RAG**: Pull from rule definitions and context
- **Example-guided**: Show concrete command examples
- **ReAct**: Reason about context → suggest actions

---

## Integration

Used by:
- **Orchestrator**: Routes help requests
- **Manual**: Invoke via `::?` or `::help`
- **All Rules**: Can reference help system in suggestions
