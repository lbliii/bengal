# Bengal Documentation & Delivery Rule System (v2)

## Purpose

Tailored AI-assisted rules for Bengal's **research → RFC → plan → implement → validate → ship** workflow. Grounded in Bengal's architecture (`bengal/core`, orchestrators, rendering, cache, health) and test suite. Incorporates advanced prompting techniques from [promptingguide.ai/techniques](https://www.promptingguide.ai/techniques).

This system matches the sophistication of the documentation framework with context analysis, reflexion loops, workflow chains, natural language support, and transparent confidence scoring.

---

## Command Shortcuts

### Core Commands

```yaml
::b-auto       # Intelligent orchestration based on intent and context
::b-analyze    # Deep context analysis (code, tests, git, architecture)
::b-research   # Evidence-first research from codebase
::b-rfc        # Draft RFC from verified evidence
::b-plan       # Convert RFC into actionable plan/to-dos
::b-impl       # Drive implementation (edits, tests, lints)
::b-validate   # Deep audit with self-consistency + confidence scoring
::b-retro      # Summarize impact; update changelog
::b-improve    # Reflexion loop: iterative improvement
::b?           # Context-aware help ("what should I do here?")
::bh           # Full command reference
```

### Workflow Chains

```yaml
::b-feature    # Full feature: research → RFC → plan
::b-fix        # Quick fix: research → plan → implement
::b-ship       # Pre-release: validate → retro → changelog
::b-full       # Complete cycle: research → ... → retro
```

---

## Natural Language Support

The Bengal Orchestrator understands plain English and routes intelligently.

### Trigger Patterns

```yaml
research_triggers:
  - investigate, explore, understand, find
  - "how does X work", "what is", "where is"

rfc_triggers:
  - should we, design, architecture, options
  - propose, approach, tradeoffs

plan_triggers:
  - break down, tasks, steps, checklist
  - organize, structure, divide

implement_triggers:
  - add, fix, implement, change, build
  - create, modify, refactor, update

validate_triggers:
  - verify, check, test, validate, audit
  - confidence, accuracy, correct

improve_triggers:
  - improve, enhance, refine, better
  - iterate, polish, fix issues

help_triggers:
  - help, how, what, guide, show
  - "?", explain, assist
```

### Example Queries

```text
"How does the rendering pipeline handle Jinja templates?"
  → Routes to ::b-research (rendering subsystem)

"Should we cache taxonomy index results?"
  → Routes to ::b-rfc (cache + taxonomy)

"Implement incremental asset builds"
  → Routes to ::b-plan → ::b-impl chain

"Verify the health validator changes"
  → Routes to ::b-validate (health subsystem)

"What should I do with these uncommitted changes?"
  → Routes to ::b? (context-aware help)
```

---

## Rule 0: Bengal Orchestrator

**Purpose**: Central command interface for intelligent routing and task orchestration.

### Routing Logic

#### Step 1: Context Analysis
Automatically invoke **Rule 1: Context Analyzer** to gather:
- Code context (changed files, imports, dependents)
- Test context (coverage, related tests)
- Git context (recent commits, branch, diff)
- Architecture context (subsystems affected)

#### Step 2: Intent Classification
Classify user request into primary intent:
- **RESEARCH**: Understanding existing code/behavior
- **RFC**: Design proposal or architectural decision
- **PLAN**: Task breakdown and organization
- **IMPLEMENT**: Code changes and edits
- **VALIDATE**: Verification and testing
- **IMPROVE**: Iterative enhancement
- **HELP**: Guidance and assistance

Use natural language triggers (above) and context signals.

#### Step 3: Smart Routing

```yaml
if intent == RESEARCH:
  if broad_exploratory:
    use: ::b-research (full scan)
  elif focused_on_module:
    use: ::b-research (scoped to module)

if intent == RFC:
  if has_evidence:
    use: ::b-rfc (draft from evidence)
  else:
    chain: ::b-research → ::b-rfc

if intent == PLAN:
  if has_rfc:
    use: ::b-plan (convert RFC to tasks)
  elif simple_task:
    use: ::b-plan (direct task breakdown)
  else:
    chain: ::b-research → ::b-rfc → ::b-plan

if intent == IMPLEMENT:
  if has_plan:
    use: ::b-impl (execute plan)
  else:
    chain: ::b-plan → ::b-impl

if intent == VALIDATE:
  if critical_changes_or_api:
    use: ::b-validate (deep audit with self-consistency)
  else:
    use: ::b-validate (standard verification)

if intent == IMPROVE:
  use: ::b-improve (reflexion loop)

if intent == HELP:
  use: ::b? or ::bh (help system)
```

#### Step 4: Confirmation (Destructive Actions)

For actions that modify multiple files or are irreversible:

```markdown
⚠️ **Confirm Action**

You've requested: "[user query]"

This will:
- [Action 1]
- [Action 2]
- [Action 3]

**Affected files**: [list]

Proceed? (yes/no)
```

### Output Format

```markdown
## 🎯 Execution Plan

### Context Summary
[Brief context from Rule 1]

### Detected Intent
**Primary**: [RESEARCH/RFC/PLAN/IMPLEMENT/VALIDATE/IMPROVE/HELP]
**Confidence**: [HIGH/MEDIUM/LOW]

### Routing Decision
**Selected Rule**: [rule name]
**Reasoning**: [why this rule fits]

### Execution
[Immediately proceed to selected rule unless confirmation required]
```

### Prompting Techniques
- **ReAct**: Reason about intent, search context, route to rule
- **RAG**: Pull from `architecture/` docs and recent context
- **Chain-of-Thought**: Explicit reasoning for routing decision

---

## Rule 1: Bengal Context Analyzer

**Purpose**: Deep context understanding before rule execution.

**Shortcut**: `::b-analyze`

### Analysis Dimensions

#### 1. Code Context
- **Changed Files**: Git status/diff, uncommitted changes
- **Imports**: What modules import the changed code
- **Dependents**: What code depends on changed modules
- **Module Type**: Core / Orchestration / Rendering / Cache / Health / CLI
- **Complexity**: Lines changed, cyclomatic complexity

#### 2. Test Context
- **Existing Tests**: Related test files in `tests/unit/`, `tests/integration/`
- **Coverage**: Current test coverage for changed modules
- **Recent Test Runs**: Pass/fail status, recent failures
- **Missing Tests**: Areas without coverage

#### 3. Git Context
- **Branch**: Current branch name and type (feature/fix/refactor)
- **Recent Commits**: Last 5 commits in this area
- **Uncommitted Changes**: Staged vs unstaged
- **Merge Base**: Commits since divergence from main

#### 4. Architecture Context
- **Subsystems Affected**: Which Bengal components touched
  - Core (Site, Page, Section, Asset, Theme)
  - Orchestration (render, build, incremental)
  - Rendering (Jinja, Markdown, shortcodes, filters)
  - Cache (discovery, dependency, indexes, query)
  - Health (validators, checks, reporting)
  - CLI (commands, helpers, templates)
- **Integration Points**: How subsystems interact
- **Performance Considerations**: Cache invalidation, incremental builds

#### 5. Document Context (if applicable)
- **Open Files**: Currently open/visible in IDE
- **File Type**: Python module, test, config, docs
- **File Age**: Last modified date
- **File Size**: Lines of code, complexity

### Procedure

1. **Gather Data**
   - Run `git status`, `git diff`, `git log`
   - Scan imports with `grep -r "from bengal.X import"` or `grep -r "import bengal.X"`
   - Check test files: `tests/unit/test_{module}.py`, `tests/integration/test_{feature}.py`
   - Read `architecture/{subsystem}.md` for context

2. **Analyze Patterns**
   - Identify primary subsystem(s)
   - Detect cross-cutting concerns (cache invalidation, error handling)
   - Flag high-risk areas (core.site, orchestration pipeline)

3. **Assess Complexity**
   - Simple: Single module, < 50 lines, isolated
   - Moderate: Multiple files, < 200 lines, some dependencies
   - Complex: Cross-subsystem, > 200 lines, many dependents

### Output Format

```markdown
## 🔍 Context Analysis

### Summary
[2-3 sentence overview of context]

### Code Context
- **Changed Files**: [list with line counts]
- **Primary Subsystem**: [Core/Orchestration/Rendering/Cache/Health/CLI]
- **Imports**: [N] modules import this code
- **Dependents**: [list of dependent modules]

### Test Context
- **Existing Tests**: [list of test files]
- **Coverage**: [percentage or "unknown"]
- **Gaps**: [areas without tests]

### Git Context
- **Branch**: `[branch name]` (type: [feature/fix/refactor])
- **Recent Commits**: [last 3-5 relevant commits]
- **Uncommitted**: [N] staged, [N] unstaged files

### Architecture Context
- **Subsystems**: [list with brief descriptions]
- **Integration Points**: [how they connect]
- **Performance Notes**: [cache implications, build impact]

### Complexity Assessment
**Level**: [Simple/Moderate/Complex]
**Reasoning**: [why this complexity level]

### 💡 Recommendations
- [Recommendation 1 based on context]
- [Recommendation 2]
```

### Integration with Orchestrator

Context Analyzer runs **automatically** before routing in Orchestrator when:
- User query is complex or ambiguous
- Multiple subsystems potentially affected
- Git status shows many changes

Can also be invoked explicitly via `::b-analyze`.

---

## Rule 2: Bengal Research & Evidence Extraction

**Purpose**: Extract verifiable claims from source code and tests for features or changes.

**Shortcut**: `::b-research`

**Principle**: NEVER invent facts. Only make claims backed by code references (`file:line`).

### Procedure

#### Step 1: Scope Definition
- Identify target modules/subsystems from context or user query
- Example: "Research rendering pipeline" → `bengal/rendering/`, `architecture/rendering.md`

#### Step 2: Evidence Collection

**Sources** (in priority order):
1. **Source Code**: `bengal/` modules (primary truth)
2. **Tests**: `tests/unit/`, `tests/integration/` (behavior verification)
3. **Architecture Docs**: `architecture/*.md` (design intent)
4. **Config**: `bengal.toml` schema, defaults in code

**Tools**:
- `codebase_search`: Semantic search for concepts
- `grep`: Exact symbol/function searches
- `read_file`: Read identified files

**Process**:
1. Start broad: semantic search for main concepts
2. Narrow down: grep for specific classes/functions
3. Read code: extract signatures, docstrings, logic
4. Cross-reference: verify in tests
5. Check config: find defaults and schema

#### Step 3: Claim Extraction

For each finding, produce a **structured claim**:

```yaml
claim:
  description: "[What the code does/provides]"
  evidence:
    - source: "bengal/module/file.py:45-52"
      type: "code"
      excerpt: "[brief code snippet or signature]"
    - source: "tests/unit/test_module.py:120"
      type: "test"
      excerpt: "[test name or assertion]"
  criticality: [HIGH | MEDIUM | LOW]
  confidence: [0-100%]
  reasoning: "[Why this claim is justified]"
```

**Criticality Levels**:
- **HIGH**: API contracts, core behavior, user-facing features
- **MEDIUM**: Internal implementation, performance characteristics
- **LOW**: Code style, optional features

#### Step 4: Cross-Validation

For **HIGH** criticality claims, apply **self-consistency** (3 paths):
- **Path A**: Source code evidence
- **Path B**: Test evidence (does test verify the claim?)
- **Path C**: Config/schema evidence (is it configurable?)

Agreement across 2+ paths → high confidence.

### Output Format

```markdown
## 📚 Research: [Topic/Module]

### Executive Summary
[2-3 sentences: what was researched, key findings, confidence level]

### Evidence Summary
- **Claims Extracted**: [N]
- **High Criticality**: [N]
- **Medium Criticality**: [N]
- **Low Criticality**: [N]
- **Average Confidence**: [N]%

---

### 🔴 High Criticality Claims

#### Claim 1: [Description]
**Evidence**:
- ✅ **Source**: `bengal/core/site.py:145-150`
  ```python
  def build(self, incremental: bool = False):
      """Build the site with optional incremental mode."""
  ```
- ✅ **Test**: `tests/unit/test_site.py:89`
  - Test: `test_incremental_build_only_rebuilds_changed_pages`
- ✅ **Config**: `bengal.toml` schema allows `build.incremental = true`

**Confidence**: 95% 🟢  
**Reasoning**: All three paths agree; API is stable and tested.

---

#### Claim 2: [Description]
[Similar structure]

---

### 🟡 Medium Criticality Claims
[Similar structure, may skip 3-path validation]

---

### 🟢 Low Criticality Claims
[Brief list format]

---

### 📋 Next Steps
- [ ] Use findings for RFC (run `::b-rfc`)
- [ ] Identify gaps requiring SME input
- [ ] Update architecture docs if drift detected
```

### Prompting Techniques
- **ReAct**: Reason → search → read → refine loop
- **Chain-of-Thought**: Explicit reasoning per claim
- **Self-Consistency**: 3-path validation for HIGH criticality
- **Example-guided**: Use claim schema template

---

## Rule 3: Bengal RFC Drafting

**Purpose**: Draft evidence-backed Request for Comments (RFC) for design decisions.

**Shortcut**: `::b-rfc`

**Input**: Verified claims from Rule 2 (Research) or existing research artifacts.

### RFC Structure

#### 1. Metadata
```yaml
Title: [Brief, descriptive title]
Author: [AI + Human reviewer]
Date: [YYYY-MM-DD]
Status: [Draft | Review | Accepted | Implemented]
Confidence: [0-100%]
```

#### 2. Problem Statement
- **Current State**: What exists today (with evidence)
- **Pain Points**: Issues, limitations, technical debt
- **User Impact**: Who is affected and how

#### 3. Goals & Non-Goals

**Goals**:
- [Goal 1: Specific, measurable]
- [Goal 2]

**Non-Goals** (explicit scope boundaries):
- [What we're NOT solving]

#### 4. Architecture Impact

Reference Bengal subsystems:

```markdown
**Affected Subsystems**:
- **Core** (`bengal/core/`): [specific impact]
  - Modules: `site.py`, `page.py`, etc.
- **Orchestration** (`bengal/orchestration/`): [specific impact]
- **Rendering** (`bengal/rendering/`): [specific impact]
- **Cache** (`bengal/cache/`): [specific impact]
- **Health** (`bengal/health/`): [specific impact]
- **CLI** (`bengal/cli/`): [specific impact]

**Integration Points**:
[How subsystems interact in this design]
```

#### 5. Design Options

**Option A: [Approach Name]**
- **Description**: [How it works]
- **Pros**:
  - [Advantage 1]
  - [Advantage 2]
- **Cons**:
  - [Limitation 1]
  - [Limitation 2]
- **Complexity**: [Simple/Moderate/Complex]
- **Evidence**: [Reference research claims]

**Option B: [Alternative Approach]**
[Similar structure]

**Recommended**: [Option X] because [reasoning]

#### 6. Detailed Design (Selected Option)

```markdown
### API Changes
[Function signatures, class changes]

### Data Flow
[How data moves through the system]

### Error Handling
[New exceptions, error messages]

### Configuration
[New config options, defaults]

### Testing Strategy
[How to test this change]
```

#### 7. Tradeoffs & Risks

**Tradeoffs**:
- [Tradeoff 1: what we gain vs lose]

**Risks**:
- **Risk 1**: [Description]
  - **Likelihood**: [Low/Medium/High]
  - **Impact**: [Low/Medium/High]
  - **Mitigation**: [How to address]

#### 8. Performance & Compatibility

**Performance Impact**:
- Build time: [expected change]
- Memory: [expected change]
- Cache implications: [invalidation, new indexes]

**Compatibility**:
- Breaking changes: [yes/no, details]
- Migration path: [how users upgrade]
- Deprecation timeline: [if applicable]

#### 9. Migration & Rollout

**Implementation Phases**:
1. [Phase 1: Foundation]
2. [Phase 2: Core functionality]
3. [Phase 3: Polish & documentation]

**Rollout Strategy**:
- Feature flag: [yes/no]
- Beta period: [duration]
- Documentation updates: [list]

#### 10. Open Questions

- [ ] **Question 1**: [Needs SME input or research]
- [ ] **Question 2**: [Requires benchmarking]

### Procedure

1. **Gather Evidence**: Ensure research is complete (or run `::b-research`)
2. **Draft Sections**: Use RFC template, fill with evidence
3. **Apply Chain-of-Thought**: For design options, show explicit reasoning
4. **Self-Consistency Check**: Validate critical claims (API, behavior, config) via 3 paths
5. **Confidence Scoring**: Apply Rule 11 formula

### Output Format

RFC saved to `plan/active/rfc-[short-name].md`

```markdown
## 📄 RFC Draft Complete

### Executive Summary
[2-3 sentences: what the RFC proposes, confidence level]

### RFC Details
- **File**: `plan/active/rfc-[name].md`
- **Confidence**: [N]% [🟢/🟡/🟠/🔴]
- **Status**: Draft (ready for review)

### Key Sections
1. ✅ Problem statement with evidence
2. ✅ Goals & non-goals defined
3. ✅ [N] design options analyzed
4. ✅ Recommended approach: [Option X]
5. ✅ Risks and mitigations identified
6. ⚠️ [N] open questions flagged

### 📋 Next Steps
- [ ] Review RFC with team/SME
- [ ] Resolve open questions
- [ ] Run `::b-plan` to convert to implementation tasks
```

### Prompting Techniques
- **Chain-of-Thought**: Explicit reasoning for design tradeoffs
- **Self-Consistency**: 3-path validation for critical API/behavior claims
- **Example-guided**: Use RFC template structure

---

## Rule 4: Bengal Planning & Breakdown

**Purpose**: Convert RFCs or high-level requests into actionable task lists with clear outcomes.

**Shortcut**: `::b-plan`

**Input**: RFC from Rule 3, or direct user request.

**Output**: Structured plan in `plan/active/plan-[name].md` and/or TODO items.

### Planning Principles

1. **Atomic Tasks**: Each task maps to one atomic commit
2. **Grouped by Area**: Organize by Bengal subsystem or module
3. **Dependencies Clear**: Sequential vs parallel tasks
4. **Validation Built-in**: Include test, lint, health check tasks
5. **Confidence Gates**: Define quality thresholds

### Procedure

#### Step 1: Parse Input
- If RFC exists, extract implementation phases and details
- If direct request, use context analysis to scope

#### Step 2: Task Breakdown

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

#### Step 3: Group and Sequence

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

#### Step 4: Add Validation Tasks

For each implementation task, add:
- **Test Task**: Write/update tests
- **Lint Task**: Run linter, fix issues
- **Health Check**: Verify subsystem validators pass

### Output Format

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
- [ ] Begin Phase 1 with `::b-impl`
- [ ] Track progress in this document (update task statuses)
```

**Also create TODO items** (if using todo_write tool):
```yaml
todos:
  - id: "bengal-impl-1-1"
    content: "core: add incremental build state tracking"
    status: "pending"
  - id: "bengal-impl-1-2"
    content: "orchestration: wire incremental state through render pipeline"
    status: "pending"
  [...]
```

### Prompting Techniques
- **Example-guided**: Use task structure template
- **Chain-of-Thought**: Explicit dependencies and sequencing reasoning

---

## Rule 5: Bengal Implementation Driver

**Purpose**: Guide code edits, test updates, and linting with guardrails.

**Shortcut**: `::b-impl`

**Input**: Plan from Rule 4, or direct implementation request.

**Principle**: NEVER invent APIs or behavior. Always verify against code/tests first.

### Guardrails

1. **Verify Before Edit**: Read target files to understand current state
2. **Minimal Edits**: Change only what's necessary for the task
3. **Preserve Style**: Match existing code style, typing, docstrings
4. **Type Safety**: Maintain or improve type hints
5. **Test Coverage**: Update/add tests for changed behavior
6. **Lint Clean**: Fix linter errors introduced by changes

### Procedure

#### Step 1: Pre-Implementation Verification

Before making any edits:
1. **Read Target Files**: Understand current implementation
2. **Search for Usage**: Find where code is used (grep for imports/calls)
3. **Check Tests**: Identify existing tests for this module
4. **Verify Assumptions**: Confirm RFC/plan claims match reality

If discrepancies found → pause and update RFC/plan.

#### Step 2: Focused Editing

**Edit Cycle**:
1. **One Task at a Time**: Focus on single task from plan
2. **Make Minimal Edit**: Use `search_replace` or `write` tool
3. **Preserve Context**: Keep surrounding code intact
4. **Add Comments**: Document non-obvious logic
5. **Update Docstrings**: Reflect any API changes

**Example Edit**:
```python
# Before
def build(self):
    """Build the site."""
    self.render_all_pages()

# After
def build(self, incremental: bool = False):
    """Build the site with optional incremental mode.

    Args:
        incremental: If True, only rebuild changed pages.
    """
    if incremental:
        self.render_changed_pages()
    else:
        self.render_all_pages()
```

#### Step 3: Test Updates

For each code change, update tests:

1. **Unit Tests**: `tests/unit/test_{module}.py`
   - Test new behavior
   - Update assertions for changed behavior
   - Add edge cases

2. **Integration Tests**: `tests/integration/test_{feature}.py`
   - Test end-to-end workflows
   - Verify subsystem interactions

**Test Structure**:
```python
def test_incremental_build_only_rebuilds_changed_pages(tmp_path):
    """Incremental build should only rebuild pages that changed."""
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

#### Step 4: Lint and Fix

After each edit:
1. **Run Linter**: `read_lints` on changed files
2. **Fix Issues**: Address errors, warnings
3. **Verify**: Ensure linter passes

#### Step 5: Atomic Commit

After completing a task (code + tests + lint):
1. **Stage Changes**: `git add` relevant files
2. **Write Commit**: Use pre-drafted message from plan
3. **Format**: `<scope>(<subscope>): <description>`

Example: `git add -A && git commit -m "core: add incremental build state tracking; add tests"`

### Output Format

```markdown
## ✅ Implementation: [Task Description]

### Executive Summary
[2-3 sentences: what was implemented, files changed, confidence]

### Changes Made

#### Code Changes
- **File**: `bengal/core/site.py`
  - Added `incremental: bool` parameter to `build()` method
  - Implemented `render_changed_pages()` helper
  - Lines changed: [N]

#### Test Changes
- **File**: `tests/unit/test_site.py`
  - Added `test_incremental_build_only_rebuilds_changed_pages`
  - Added `test_incremental_build_with_dependencies`
  - Lines added: [N]

### Validation
- ✅ Linter passed (no new errors)
- ✅ Unit tests pass ([N]/[N])
- ✅ Integration tests pass ([N]/[N])
- ⚠️ [Any warnings or issues]

### Commit
```bash
git add -A && git commit -m "core: add incremental build state tracking; add tests"
```

**Status**: ✅ Committed

### 📋 Next Steps
- [ ] Continue to next task in plan
- [ ] Or run `::b-validate` for full audit
```

### Error Handling

**If linter fails**:
1. Read lint errors
2. Apply self-critique: analyze root cause
3. Fix issues
4. Re-lint

**If tests fail**:
1. Read test output
2. Diagnose failure (logic error, test error, integration issue)
3. Fix code or test
4. Re-run tests

**If assumptions violated**:
1. Pause implementation
2. Document discrepancy
3. Update RFC/plan
4. Get user confirmation before proceeding

### Prompting Techniques
- **ReAct**: Reason → search → edit → validate cycle
- **Self-Critique**: Post-edit analysis if failures occur
- **Chain-of-Thought**: Explicit reasoning for design choices in comments

---

## Rule 6: Bengal Validation & Confidence Scoring

**Purpose**: Deep audit with self-consistency and transparent confidence scores.

**Shortcut**: `::b-validate`

**Use Cases**:
- Pre-commit validation
- Post-implementation verification
- RFC/plan accuracy audit
- Critical path changes (core, orchestration)

### Validation Method

#### Level 1: Standard Validation

For **non-critical** changes or quick checks:

1. **Code Review**:
   - Read changed files
   - Check for obvious errors (undefined vars, type mismatches)
   - Verify imports and dependencies

2. **Test Check**:
   - Confirm tests exist for changed behavior
   - Check test pass/fail status

3. **Lint Check**:
   - Run linter on changed files
   - Verify no new errors

**Output**: Pass/Fail with brief notes

#### Level 2: Deep Validation (Self-Consistency)

For **HIGH criticality** changes (API, core behavior, user-facing):

Apply **3-path self-consistency** for each critical claim:

**Path A: Source Code**
- Verify claim by reading implementation
- Find function/class signatures
- Check logic and error handling

**Path B: Tests**
- Find tests that cover the claimed behavior
- Verify assertions match the claim
- Check edge cases are tested

**Path C: Config/Schema**
- Check if behavior is configurable
- Verify defaults match claim
- Review validation rules

**Scoring**:
- All 3 paths agree: HIGH confidence (90-100%)
- 2 paths agree: MODERATE confidence (70-89%)
- 1 path or conflicts: LOW confidence (< 70%)

### Confidence Scoring Formula

For each claim or change, compute confidence score:

```yaml
confidence_score = (
    evidence_strength +      # 0-40 points
    self_consistency +       # 0-30 points
    recency +                # 0-15 points
    test_coverage            # 0-15 points
) # Total: 0-100%
```

**Evidence Strength (0-40)**:
- Direct code reference: 40
- Docstring/comment only: 20
- Inferred from context: 10
- No evidence: 0

**Self-Consistency (0-30)**:
- 3 paths agree: 30
- 2 paths agree: 20
- 1 path only: 10
- Conflicts: 0

**Recency (0-15)**:
- Modified in last month: 15
- Modified in last 6 months: 10
- Modified in last year: 5
- Older than 1 year: 0

**Test Coverage (0-15)**:
- Explicit tests exist and pass: 15
- Tests exist but incomplete: 10
- Inferred from integration tests: 5
- No tests: 0

**Interpretation**:
- 90-100%: HIGH confidence 🟢 (ship it)
- 70-89%: MODERATE confidence 🟡 (review recommended)
- 50-69%: LOW confidence 🟠 (needs work)
- < 50%: UNCERTAIN 🔴 (do not ship)

### Procedure

#### Step 1: Identify Claims

Extract claims from:
- RFC/plan documents
- Code comments/docstrings
- Changed behavior

#### Step 2: Validate Each Claim

For each claim:
1. Determine criticality (HIGH/MEDIUM/LOW)
2. If HIGH: apply 3-path self-consistency
3. If MEDIUM/LOW: apply path A (source code) only
4. Compute confidence score

#### Step 3: Aggregate Results

Compute overall confidence:
```python
overall_confidence = weighted_average([
    (claim.confidence, claim.criticality_weight)
    for claim in claims
])

criticality_weights = {
    "HIGH": 3,
    "MEDIUM": 2,
    "LOW": 1
}
```

### Output Format

```markdown
## 🔍 Validation Results: [Topic/Module]

### Executive Summary
[2-3 sentences: what was validated, overall confidence, key findings]

### Summary
- **Claims Validated**: [N]
- **High Criticality**: [N]
- **Medium Criticality**: [N]
- **Low Criticality**: [N]
- **Overall Confidence**: [N]% [🟢/🟡/🟠/🔴]

---

### ✅ Verified Claims ([N])

#### Claim 1: [Description]
**Criticality**: HIGH  
**Confidence**: 95% 🟢

**Evidence**:
- ✅ **Path A (Source)**: `bengal/core/site.py:145-150`
  ```python
  def build(self, incremental: bool = False):
      """Build with optional incremental mode."""
  ```
- ✅ **Path B (Tests)**: `tests/unit/test_site.py:89`
  - `test_incremental_build_only_rebuilds_changed_pages`
  - Assertion verifies only changed pages rebuilt
- ✅ **Path C (Config)**: No configuration needed (API parameter)

**Scoring**:
- Evidence: 40/40 (direct code)
- Consistency: 30/30 (all paths agree)
- Recency: 15/15 (modified today)
- Tests: 15/15 (explicit tests pass)
- **Total**: 100/100

---

### ⚠️ Moderate Confidence Claims ([N])

#### Claim 2: [Description]
**Criticality**: MEDIUM  
**Confidence**: 75% 🟡

**Evidence**:
- ✅ **Path A (Source)**: `bengal/cache/build_cache.py:200`
  - Method exists, logic seems correct
- ❌ **Path B (Tests)**: No direct tests found
  - Only integration tests cover this indirectly
- N/A **Path C (Config)**: Not applicable

**Scoring**: [breakdown]

**Recommendation**: Add unit tests for this method

---

### 🔴 Low Confidence / Issues ([N])

#### Issue 1: [Description]
**Criticality**: HIGH  
**Confidence**: 45% 🔴

**Problem**: [What's wrong]

**Evidence**:
- ⚠️ **Path A (Source)**: `bengal/rendering/jinja_env.py:78`
  - Method signature doesn't match claimed behavior
- ❌ **Path B (Tests)**: No tests found
- ❌ **Path C (Config)**: Config schema missing

**Action Required**: [How to fix]

---

### 📊 Confidence Breakdown

| Category | Claims | Avg Confidence |
|----------|--------|----------------|
| High Criticality | [N] | [N]% |
| Medium Criticality | [N] | [N]% |
| Low Criticality | [N] | [N]% |
| **Overall** | **[N]** | **[N]%** |

---

### 📋 Action Items

**Critical (must fix)**:
- [ ] [Action 1 for red/low confidence items]
- [ ] [Action 2]

**Recommended (improve confidence)**:
- [ ] [Action 1 for yellow/moderate items]
- [ ] [Action 2]

**Optional (nice to have)**:
- [ ] [Improvements for green items]

---

### ✅ Validation Gates

- [✅/❌] **RFC Gate**: Confidence ≥ 85% → [status]
- [✅/❌] **Implementation Gate**: Confidence ≥ 90% → [status]
- [✅/❌] **Core Module Gate**: Confidence ≥ 90% → [status]

**Overall Status**: [PASS / CONDITIONAL / FAIL]
```

### Prompting Techniques
- **Self-Consistency**: 3-path validation for HIGH criticality
- **Chain-of-Thought**: Explicit reasoning per claim
- **Self-Critique**: Post-validation analysis to identify gaps

---

## Rule 7: Bengal Retrospective & Changelog

**Purpose**: Summarize impact, document changes, update changelog.

**Shortcut**: `::b-retro`

**When to Use**:
- After completing feature implementation
- Before merging to main
- Pre-release preparation

### Procedure

#### Step 1: Impact Summary

Write 1-2 paragraph summary:
- What was built/changed
- Why it matters (user/developer benefit)
- Confidence level of implementation

#### Step 2: Code References

Create itemized list of key changes:

```markdown
### Key Changes

**Core** (`bengal/core/`):
- `site.py:145-150`: Added incremental build support
- `page.py:200`: Added change detection logic

**Orchestration** (`bengal/orchestration/`):
- `render_orchestrator.py:50-75`: Wire incremental flag through pipeline

**Tests** (`tests/`):
- `unit/test_site.py:89-120`: Added incremental build tests
- `integration/test_build.py:200-250`: Added end-to-end incremental test

**Documentation** (`architecture/`):
- `cache.md`: Updated to reflect incremental build cache usage
```

#### Step 3: Update Changelog

Update `CHANGELOG.md` in the **Unreleased** section:

```markdown
## [Unreleased]

### Added
- Incremental build support: only rebuild pages that changed
- `Site.build(incremental=True)` API for selective rebuilds
- Change detection in `Page` and `Asset` classes

### Changed
- Build orchestrator now supports incremental mode
- Cache indexes updated to track modification times

### Fixed
- [Any bugs fixed as part of this work]

### Performance
- Incremental builds reduce build time by 70-90% for small changes
```

Follow **Keep a Changelog** format:
- **Added**: New features
- **Changed**: Changes to existing functionality
- **Deprecated**: Soon-to-be-removed features
- **Removed**: Removed features
- **Fixed**: Bug fixes
- **Security**: Vulnerability fixes
- **Performance**: Performance improvements

#### Step 4: Move Planning Documents

Move completed plans to archive:
```bash
mv plan/active/plan-incremental-build.md plan/implemented/
mv plan/active/rfc-incremental-build.md plan/implemented/
```

Update moved files with:
- **Implemented Date**: [YYYY-MM-DD]
- **Final Confidence**: [N]%
- **Actual vs Estimated**: [time comparison]

#### Step 5: Lessons Learned (Optional)

If applicable, add a brief lessons learned section:

```markdown
### Lessons Learned
- **Surprise 1**: Cache invalidation was more complex than expected
- **Success 1**: Test-first approach caught edge cases early
- **Future**: Consider generalizing change detection for assets
```

### Output Format

```markdown
## 📝 Retrospective: [Feature/Change Name]

### Impact Summary

[1-2 paragraphs describing what was built, why it matters, confidence level]

---

### Key Changes

[Itemized list by subsystem with file:line references]

---

### Changelog Entry

```markdown
## [Unreleased]

### Added
- [Feature description]
- [API additions]

### Changed
- [Behavior changes]

### Performance
- [Performance improvements with metrics if available]
```

---

### Planning Documents

- ✅ Moved `plan/active/plan-[name].md` → `plan/implemented/`
- ✅ Moved `plan/active/rfc-[name].md` → `plan/implemented/`
- ✅ Updated `CHANGELOG.md`

---

### Lessons Learned

[Optional section with insights]

---

### 📊 Metrics

- **Tasks Completed**: [N]/[N]
- **Files Changed**: [N]
- **Lines Added**: [+N]
- **Lines Removed**: [-N]
- **Tests Added**: [N]
- **Final Confidence**: [N]% 🟢

---

### ✅ Ready to Ship

- [✅] All tasks completed
- [✅] Tests passing
- [✅] Documentation updated
- [✅] Changelog updated
- [✅] Confidence ≥ 90%

**Status**: Ready for merge to `main`
```

### Prompting Techniques
- **Chain-of-Thought**: Explicit reasoning about impact and lessons
- **RAG**: Pull from plan/RFC documents and git history

---

## Rule 8: Bengal Reflexion Loop

**Purpose**: Iterative improvement through self-assessment and regeneration.

**Shortcut**: `::b-improve`

**When to Use**:
- When validation reveals low confidence (< 70%)
- When initial RFC/plan has gaps or inconsistencies
- When implementation encounters unexpected issues
- For continuous refinement of artifacts

### Reflexion Process

The reflexion loop follows: **Attempt → Evaluate → Reflect → Improve → Retry**

#### Step 1: Initial Attempt

Produce initial output (RFC, plan, implementation) via standard rules.

#### Step 2: Self-Evaluation

Run validation (Rule 6) to assess:
- **Confidence Score**: Compute using formula
- **Gap Analysis**: What's missing or incorrect?
- **Inconsistencies**: Where do paths disagree?
- **Coverage**: Are all critical paths validated?

#### Step 3: Reflection

Apply **self-critique** by asking:

```markdown
### Reflection Questions

1. **Completeness**: What information is missing?
   - Missing code references?
   - Untested edge cases?
   - Unclear dependencies?

2. **Accuracy**: Where might claims be wrong?
   - Assumptions not verified?
   - Outdated information?
   - Misinterpreted code?

3. **Consistency**: Where do sources disagree?
   - Code vs tests mismatch?
   - Config vs behavior mismatch?
   - Documentation drift?

4. **Confidence**: Why is confidence low?
   - Weak evidence?
   - No tests?
   - Multiple interpretation paths?

5. **Improvement Path**: What specific actions would raise confidence?
   - Additional research needed?
   - More tests required?
   - SME clarification needed?
```

#### Step 4: Targeted Improvement

Based on reflection, take specific actions:

**If missing evidence**:
- Run deeper codebase search
- Check additional test files
- Review architecture docs

**If inconsistencies found**:
- Re-read conflicting sources
- Trace actual data flow
- Add integration test to verify

**If tests missing**:
- Implement tests (if `::b-impl` phase)
- Flag for test addition (if `::b-rfc` phase)

**If claims unclear**:
- Rephrase with more specificity
- Add code examples
- Cite exact line numbers

#### Step 5: Regenerate

Produce improved version of artifact:
- Update RFC with new evidence
- Refine plan with clearer tasks
- Fix implementation issues

#### Step 6: Re-Evaluate

Run validation again (Rule 6). Compare:
- **Before Confidence**: [N]%
- **After Confidence**: [N]%
- **Improvement**: [+N]%

If confidence now meets threshold → success!  
If still low → iterate again or escalate for SME input.

### Iteration Limits

- **Max Iterations**: 3 cycles
- **Convergence Check**: If improvement < 5% between iterations, stop and flag for human review
- **Divergence Check**: If confidence decreases, revert and flag issue

### Output Format

```markdown
## 🔄 Reflexion Loop: [Artifact Name]

### Executive Summary
[2-3 sentences: what was improved, confidence change, iterations needed]

---

### Iteration 1

#### Initial State
- **Confidence**: [N]% 🟠
- **Key Issues**:
  - [Issue 1]
  - [Issue 2]

#### Reflection
[Answers to reflection questions]

#### Actions Taken
- [Action 1: e.g., deeper research on cache invalidation]
- [Action 2: e.g., added integration test]

#### Result
- **New Confidence**: [N]% 🟡
- **Improvement**: +[N]%

---

### Iteration 2

[Similar structure if needed]

---

### Final Result

- **Starting Confidence**: [N]% 🟠
- **Final Confidence**: [N]% 🟢
- **Total Improvement**: +[N]%
- **Iterations**: [N]

**Status**: ✅ Confidence threshold met ([≥85% or ≥90%])

---

### Updated Artifact

[Link to improved RFC/plan/implementation]

**Key Improvements**:
- [Improvement 1]
- [Improvement 2]

---

### 📋 Next Steps

- [ ] Review improved artifact
- [ ] Proceed to next phase ([RFC → plan → impl])
- [ ] Or if still low confidence: [escalation path]
```

### Prompting Techniques
- **Self-Critique**: Systematic self-assessment
- **Reflexion**: Learn from mistakes and iterate
- **Chain-of-Thought**: Explicit reasoning about improvements

---

## Rule 9: Bengal Help System

**Purpose**: Context-aware guidance and command reference.

**Shortcuts**:
- `::b?` - Context-aware help ("what should I do here?")
- `::bh` - Full command reference

### Context-Aware Help (`::b?`)

Analyzes current context and suggests relevant actions.

#### Step 1: Gather Context

Use Rule 1 (Context Analyzer) to understand:
- Open files
- Git status (uncommitted changes, current branch)
- Recent activity
- Subsystems involved

#### Step 2: Generate Suggestions

Based on context, suggest 3-5 relevant actions:

**Example Context**: User has uncommitted changes in `bengal/core/site.py` and `tests/unit/test_site.py`

**Suggestions**:
```markdown
## 💡 Context-Aware Suggestions

### Current Context
- **Modified**: `bengal/core/site.py` (+50 lines), `tests/unit/test_site.py` (+30 lines)
- **Subsystem**: Core
- **Branch**: `feature/incremental-build`
- **Status**: Uncommitted changes

---

### Recommended Actions

1. **Validate Changes** (`::b-validate`)
   - Verify your core module changes with self-consistency
   - Check test coverage and confidence
   - Best for: Ensuring quality before commit

2. **Complete Implementation** (`::b-impl`)
   - Continue with implementation tasks from plan
   - Ensure linter passes, tests complete
   - Best for: If you're mid-implementation

3. **Create Retrospective** (`::b-retro`)
   - Document changes and update changelog
   - Move planning docs to implemented/
   - Best for: If implementation is complete

4. **Research Context** (`::b-research`)
   - Understand current Site class design
   - Find related code and dependencies
   - Best for: If you need more context before proceeding

5. **Get Full Plan** (`::b-plan`)
   - Generate detailed task breakdown
   - Structure remaining work
   - Best for: If you don't have a plan yet

---

### Quick Checks

- Run linter: `read_lints` on changed files
- Check tests: Run `pytest tests/unit/test_site.py`
- View plan: `cat plan/active/plan-*.md` (if exists)

Type the command shortcut (e.g., `::b-validate`) or describe what you want to do.
```

### Full Command Reference (`::bh`)

Displays comprehensive command reference:

```markdown
## 📚 Bengal Rule System - Full Reference

### Core Commands

#### `::b-auto` - Intelligent Orchestration
Routes your request to the appropriate rule based on intent and context.

**Use when**: You're not sure which command to use, or want AI to decide.

**Example**: "Should we add caching to the taxonomy index?" → AI routes to `::b-rfc`

---

#### `::b-analyze` - Deep Context Analysis
Analyzes code, tests, git, and architecture context.

**Use when**: You need to understand the current state before planning or implementing.

**Output**: Detailed context report with subsystems, dependencies, complexity assessment.

---

#### `::b-research` - Evidence-First Research
Extracts verifiable claims from source code and tests.

**Use when**: You need to understand how a feature works or gather evidence for an RFC.

**Output**: Structured claims with code references, criticality, confidence scores.

**Example**: `::b-research` → "Research the rendering pipeline"

---

#### `::b-rfc` - Draft RFC
Produces evidence-backed Request for Comments (RFC) for design decisions.

**Use when**: You need to propose a design or architectural change.

**Input**: Requires research evidence (run `::b-research` first or AI will do it automatically).

**Output**: RFC document in `plan/active/rfc-[name].md` with problem statement, options, tradeoffs, risks.

---

#### `::b-plan` - Planning & Task Breakdown
Converts RFCs or requests into actionable task lists.

**Use when**: You have an RFC and need to break it into implementation tasks.

**Output**: Plan document in `plan/active/plan-[name].md` with phased tasks, dependencies, commit messages.

---

#### `::b-impl` - Implementation Driver
Guides code edits, test updates, and linting with guardrails.

**Use when**: You're ready to implement tasks from a plan.

**Guardrails**: Verifies before editing, preserves style, maintains tests, runs linter.

**Output**: Code changes + tests + lint fixes + atomic commit.

---

#### `::b-validate` - Deep Validation
Audits changes/claims with self-consistency and confidence scoring.

**Use when**:
- Pre-commit validation
- Post-implementation verification
- Critical changes to core/orchestration

**Method**: 3-path self-consistency for HIGH criticality claims (code + tests + config).

**Output**: Confidence scores, evidence, action items.

---

#### `::b-retro` - Retrospective & Changelog
Summarizes impact, updates changelog, archives planning docs.

**Use when**: Feature/change is complete and ready to merge.

**Output**: Impact summary, code references, updated `CHANGELOG.md`, moved planning docs.

---

#### `::b-improve` - Reflexion Loop
Iterative improvement through self-assessment and regeneration.

**Use when**: Validation reveals low confidence or artifacts have gaps.

**Process**: Validate → reflect → improve → re-validate (up to 3 iterations).

**Output**: Improved artifact with confidence improvement metrics.

---

### Workflow Chains

#### `::b-feature` - Full Feature Workflow
**Chain**: `research → RFC → plan`

**Use when**: Starting a new feature from scratch.

**Output**: Complete design package ready for implementation.

---

#### `::b-fix` - Quick Fix Workflow
**Chain**: `research → plan → implement`

**Use when**: Fixing a bug or making a small improvement.

**Output**: Focused plan + implementation + validation.

---

#### `::b-ship` - Pre-Release Workflow
**Chain**: `validate → retro → changelog`

**Use when**: Preparing completed work for merge/release.

**Output**: Validation report + retrospective + updated changelog.

---

#### `::b-full` - Complete Cycle
**Chain**: `research → RFC → plan → implement → validate → retro`

**Use when**: End-to-end feature development with AI assistance.

**Output**: Complete cycle from research to shipped feature.

---

### Help Commands

#### `::b?` - Context-Aware Help
Analyzes your current context and suggests relevant actions.

**Use when**: You're not sure what to do next.

**Output**: 3-5 tailored suggestions based on open files, git status, subsystems.

---

#### `::bh` - Full Reference
Displays this complete command reference.

---

### Natural Language Support

You can also describe what you want in plain English:

**Examples**:
- "How does the cache invalidation work?" → `::b-research`
- "Should we refactor the menu builder?" → `::b-rfc`
- "Break down the incremental build implementation" → `::b-plan`
- "Verify my rendering changes" → `::b-validate`
- "What should I do with these uncommitted changes?" → `::b?`

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

When working with Bengal, commands are aware of these subsystems:

- **Core** (`bengal/core/`): Site, Page, Section, Asset, Theme
- **Orchestration** (`bengal/orchestration/`): Build, render, incremental
- **Rendering** (`bengal/rendering/`): Jinja, Markdown, shortcodes, filters
- **Cache** (`bengal/cache/`): Discovery, dependency tracking, indexes
- **Health** (`bengal/health/`): Validators, checks, reporting
- **CLI** (`bengal/cli/`): Commands, helpers, templates

---

### Tips

1. **Start with Research**: Use `::b-research` to understand before planning
2. **Use Workflows**: `::b-feature`, `::b-fix`, `::b-ship` save time
3. **Validate Often**: Run `::b-validate` before committing critical changes
4. **Let AI Decide**: Use `::b-auto` when unsure which command to use
5. **Iterate**: Use `::b-improve` to refine low-confidence outputs
6. **Get Help**: Type `::b?` anytime you're stuck

---

Need help? Just ask in plain English or type `::b?` for context-aware suggestions!
```

### Prompting Techniques
- **RAG**: Pull from rule definitions and context
- **Example-guided**: Show concrete command examples

---

## Rule 10: Bengal Workflow Templates

**Purpose**: Pre-built workflow chains for common scenarios.

**Shortcuts**: `::b-feature`, `::b-fix`, `::b-ship`, `::b-full`

### Workflow 1: Full Feature (`::b-feature`)

**Chain**: Context Analysis → Research → RFC → Plan

**Use Case**: Designing a new feature from scratch

**Steps**:

1. **Context Analysis** (Rule 1)
   - Understand current subsystems
   - Identify integration points

2. **Research** (Rule 2)
   - Gather evidence from codebase
   - Extract claims about related functionality
   - Identify extension points

3. **RFC** (Rule 3)
   - Draft design proposal
   - Analyze options and tradeoffs
   - 3-path validation for critical claims

4. **Plan** (Rule 4)
   - Break down into tasks
   - Group by subsystem and phase
   - Add validation tasks

**Output**: Complete design package ready for `::b-impl`

**Estimated Time**: 20-40 minutes (depending on feature complexity)

---

### Workflow 2: Quick Fix (`::b-fix`)

**Chain**: Research (focused) → Plan → Implement → Validate

**Use Case**: Fixing a bug or small improvement

**Steps**:

1. **Research** (Rule 2, focused)
   - Understand bug context
   - Find related code and tests
   - Scope: 5-10 minutes

2. **Plan** (Rule 4, simplified)
   - 3-5 tasks: fix + test + lint
   - No formal RFC needed
   - Scope: 5 minutes

3. **Implement** (Rule 5)
   - Apply fix
   - Update/add tests
   - Run linter
   - Atomic commit
   - Scope: 10-20 minutes

4. **Validate** (Rule 6, standard)
   - Quick validation (not deep)
   - Ensure tests pass
   - Confidence check
   - Scope: 5 minutes

**Output**: Fixed bug with tests and commit

**Estimated Time**: 25-40 minutes

---

### Workflow 3: Pre-Release (`::b-ship`)

**Chain**: Validate (deep) → Retrospective → Changelog

**Use Case**: Preparing completed work for merge/release

**Steps**:

1. **Validate** (Rule 6, deep)
   - Full confidence scoring
   - 3-path self-consistency for critical changes
   - Comprehensive test check
   - Scope: 10-15 minutes

2. **Retrospective** (Rule 7)
   - Impact summary
   - Code references
   - Lessons learned
   - Scope: 5-10 minutes

3. **Changelog** (Rule 7)
   - Update `CHANGELOG.md`
   - Move planning docs to `plan/implemented/`
   - Scope: 5 minutes

**Output**: Ready-to-merge feature with documentation

**Estimated Time**: 20-30 minutes

---

### Workflow 4: Complete Cycle (`::b-full`)

**Chain**: Context → Research → RFC → Plan → Implement → Validate → Retro

**Use Case**: End-to-end feature development with full AI assistance

**Steps**: All rules in sequence

**Output**: Complete cycle from research to shipped feature

**Estimated Time**: 2-4 hours (depending on feature scope)

**Note**: This is a long workflow. Consider breaking it up with user checkpoints after RFC and after Plan.

---

### Workflow Execution

When user invokes a workflow:

1. **Confirm Scope**:
   ```markdown
   ## 🎯 Workflow: [Name]

   **Steps**: [list]
   **Estimated Time**: [duration]
   **Output**: [description]

   Proceed? (yes/no)
   ```

2. **Execute Chain**:
   - Run each rule in sequence
   - Pass output of one rule as input to next
   - Show progress: "Step 1/4: Research..."

3. **Checkpoints**:
   - Pause after major steps (RFC, Plan) for user review
   - Allow user to adjust before continuing

4. **Final Summary**:
   ```markdown
   ## ✅ Workflow Complete: [Name]

   **Completed Steps**: [list]
   **Outputs**: [files created]
   **Overall Confidence**: [N]% 🟢

   **Next Steps**: [recommendations]
   ```

### Prompting Techniques
- **Chain-of-Thought**: Explicit reasoning between workflow steps
- **ReAct**: Reason about workflow progress, adapt if issues arise

---

## Rule 11: Confidence Scoring System

**Purpose**: Transparent, reproducible confidence quantification.

**Used By**: All validation rules (especially Rule 6)

### Scoring Formula

```yaml
confidence_score = (
    evidence_strength +      # 0-40 points
    self_consistency +       # 0-30 points
    recency +                # 0-15 points
    test_coverage            # 0-15 points
) # Total: 0-100%
```

### Component Definitions

#### Evidence Strength (0-40 points)

Measures quality of code references:

- **40 points**: Direct code reference with file:line and excerpt
  - Example: `bengal/core/site.py:145-150` with quoted code
- **30 points**: Direct code reference without excerpt
  - Example: `bengal/core/site.py:145` (line only)
- **20 points**: Docstring or comment only (no implementation verified)
- **10 points**: Inferred from context or indirect evidence
- **0 points**: No evidence or assumption only

#### Self-Consistency (0-30 points)

Measures agreement across validation paths:

- **30 points**: All 3 paths agree (code + tests + config/schema)
- **20 points**: 2 paths agree, 1 path not applicable
- **10 points**: 1 path only (e.g., code only, no tests)
- **5 points**: Paths partially agree (minor discrepancies)
- **0 points**: Paths conflict (code says X, tests expect Y)

**Note**: Only apply 3-path for HIGH criticality claims. For MEDIUM/LOW, use code path only (assign 20 points if code verified, 10 if not).

#### Recency (0-15 points)

Measures staleness of evidence:

- **15 points**: Modified in last 30 days
- **10 points**: Modified in last 6 months
- **5 points**: Modified in last 12 months
- **0 points**: Older than 1 year or unknown

Use `git log` to check last modification date of evidence files.

#### Test Coverage (0-15 points)

Measures test quality:

- **15 points**: Explicit unit/integration tests exist and pass
  - Example: `test_incremental_build()` directly tests claimed behavior
- **10 points**: Tests exist but incomplete (edge cases missing)
- **5 points**: Indirectly tested via integration tests only
- **0 points**: No tests found

### Interpretation Thresholds

#### Confidence Levels

- **90-100%**: HIGH confidence 🟢
  - **Action**: Ship it
  - **Gate**: Required for core implementation

- **70-89%**: MODERATE confidence 🟡
  - **Action**: Review recommended, acceptable for non-critical
  - **Gate**: Required for RFC/plan

- **50-69%**: LOW confidence 🟠
  - **Action**: Needs improvement before shipping
  - **Gate**: Run `::b-improve` reflexion loop

- **< 50%**: UNCERTAIN 🔴
  - **Action**: Do not ship, requires major work
  - **Gate**: Block until evidence/tests added

### Quality Gates

Different thresholds for different artifact types:

```yaml
gates:
  rfc_confidence: 85%      # RFC must have strong evidence
  plan_confidence: 85%     # Plan must be well-grounded
  implementation_core: 90% # Core modules require highest confidence
  implementation_other: 85% # Other modules slightly lower
  documentation: 70%       # Docs can be moderate (user-facing)
```

### Example Calculations

#### Example 1: High Confidence Claim

**Claim**: "Site.build() supports incremental mode via `incremental` parameter"

**Scoring**:
- **Evidence**: 40/40 (direct code: `bengal/core/site.py:145` with signature)
- **Consistency**: 30/30 (code has param, tests verify behavior, config not needed)
- **Recency**: 15/15 (modified today)
- **Tests**: 15/15 (`test_incremental_build_only_rebuilds_changed_pages` passes)
- **Total**: **100/100** 🟢

**Interpretation**: HIGH confidence, ship it.

---

#### Example 2: Moderate Confidence Claim

**Claim**: "Cache invalidation uses file modification timestamps"

**Scoring**:
- **Evidence**: 30/40 (code reference but no excerpt: `bengal/cache/build_cache.py:200`)
- **Consistency**: 20/30 (code verified, tests indirect, config N/A)
- **Recency**: 10/15 (modified 3 months ago)
- **Tests**: 5/15 (only integration tests cover this indirectly)
- **Total**: **65/100** 🟠

**Interpretation**: LOW confidence, needs unit tests and fresher evidence.

**Action**: Run `::b-improve` to add unit tests and verify logic.

---

#### Example 3: Low Confidence Claim

**Claim**: "Rendering pipeline caches compiled Jinja templates"

**Scoring**:
- **Evidence**: 10/40 (inferred from performance, no direct code reference)
- **Consistency**: 10/30 (code not checked, no tests)
- **Recency**: 0/15 (unknown)
- **Tests**: 0/15 (no tests found)
- **Total**: **20/100** 🔴

**Interpretation**: UNCERTAIN, do not ship.

**Action**: Run `::b-research` to find actual implementation, then re-score.

### Usage in Rules

#### In Research (Rule 2)
- Compute confidence per claim
- Flag low-confidence claims for additional research

#### In RFC (Rule 3)
- Compute overall RFC confidence (weighted average of claim confidences)
- Gate: RFC requires ≥85% to proceed to planning

#### In Validation (Rule 6)
- Compute confidence for each validated claim
- Aggregate to overall validation confidence
- Gate: Core changes require ≥90%, other changes ≥85%

#### In Reflexion (Rule 8)
- Track confidence improvement across iterations
- Stop if improvement < 5% between iterations

### Prompting Techniques
- **Explicit Scoring**: Show formula and component scores
- **Transparency**: Always explain why a score was assigned
- **Self-Critique**: If score is low, analyze why and suggest improvements

---

## Rule 12: Communication Style (Bengal Adaptation)

**Purpose**: Consistent, scannable, professional output formatting for all rules.

Adapted from the documentation framework's communication style, tailored for Bengal's software development context.

### Universal Output Structure

All rule outputs follow this structure:

```markdown
## [Icon] [Response Title/Summary]

### Executive Summary (2-3 sentences)
- What was done
- Key finding or outcome
- Next recommended action

### Main Content
[Structured content based on rule type]

### Evidence Trail (for validation rules)
[Structured findings with sources]

### Action Items
[Clear next steps and recommendations]
```

### Visual Indicators

#### Status Icons

```yaml
status:
  verified: "✅"
  warning: "⚠️"
  error: "❌"
  info: "ℹ️"

confidence:
  high: "🟢"        # 90-100%
  moderate: "🟡"    # 70-89%
  low: "🟠"         # 50-69%
  uncertain: "🔴"   # < 50%

priority:
  critical: "🔴"
  important: "🟡"
  optional: "🔵"

section:
  research: "📚"
  rfc: "📄"
  plan: "📋"
  implementation: "⚙️"
  validation: "🔍"
  retrospective: "📝"
  improvement: "🔄"
  help: "💡"
  analysis: "🎯"
  workflow: "🔗"
```

### Formatting Principles

#### 1. Start with Most Important Information

Put conclusions first, details later.

**Good**:
```markdown
## ✅ Validation Complete: Incremental Build

### Executive Summary
Validated 18 claims across core and orchestration. All HIGH criticality claims verified (95% confidence). Ready to merge.
```

**Bad**:
```markdown
I started by reading the files. First I checked site.py. Then I looked at the tests. After reviewing everything, I found that the implementation is good.
```

#### 2. Use Code References with `file:line` Format

Always cite evidence with specific locations:

**Good**: `bengal/core/site.py:145-150`  
**Bad**: "the Site class" or "in the core module"

#### 3. Group by Subsystem, Not by Rule Step

Organize content by Bengal subsystems (Core, Orchestration, Rendering, etc.) rather than by process steps.

#### 4. Use Tables for Structured Comparisons

When comparing options, risks, or metrics:

```markdown
| Option | Complexity | Performance | Testability |
|--------|-----------|-------------|-------------|
| A: Timestamp-based | Simple | Fast | Easy |
| B: Hash-based | Moderate | Slower | Moderate |
| **C: Hybrid** | **Moderate** | **Fast** | **Easy** |
```

#### 5. Provide Executable Commands

For actions, show actual commands:

```bash
git add -A && git commit -m "core: add incremental build state tracking"
pytest tests/unit/test_site.py
```

#### 6. End with Clear Next Steps

Always finish with actionable recommendations:

```markdown
### 📋 Next Steps

**Immediate**:
- [ ] Run `::b-validate` to verify changes
- [ ] Merge feature branch to main

**Follow-up**:
- [ ] Monitor performance in production
- [ ] Add benchmarks for incremental build
```

### Tone and Voice (PACE)

- **Professional**: Competent and reliable, not casual
- **Active**: Active voice, present tense, direct language
- **Conversational**: Clear and accessible, not academic
- **Engaging**: Scannable and purposeful, not dry

**Good**: "The incremental build reduces build time by 80% for small changes."

**Bad (too casual)**: "Incremental build is super fast! 🚀 You'll love it lol"

**Bad (too academic)**: "Upon conducting a comprehensive evaluation of the temporal performance characteristics, the proposed incremental methodology demonstrates a reduction in compilation duration..."

### Accessibility

- Use "refer to" instead of "see" (better for screen readers)
- Avoid directional language: use "previous section" not "above"
- Provide text descriptions for diagrams (if applicable)
- Use descriptive link text: "refer to the Site API docs" not "click here"

### File References in Output

When citing code, use this format:

```markdown
**Evidence**: `bengal/core/site.py:145-150`
```python
def build(self, incremental: bool = False):
    """Build the site with optional incremental mode."""
    if incremental:
        self.render_changed_pages()
```
```

### Error and Warning Messages

#### Error Format

```markdown
❌ **[Error Type]**: [Brief description]

**Location**: [where it occurred]
**Cause**: [why it happened]
**Fix**: [how to resolve]

**Example**:
```python
# Incorrect
site.build(incremental="yes")  # TypeError: expected bool, got str
```

**Corrected**:
```python
# Correct
site.build(incremental=True)
```
```

#### Warning Format

```markdown
⚠️ **Warning**: [Issue description]

**Severity**: [Low/Medium/High]
**Recommendation**: [what to do]
```

### Integration Across All Rules

Every Bengal rule output should:

1. ✅ Start with executive summary (2-3 sentences)
2. ✅ Use consistent visual indicators (✅ ⚠️ ❌ 🟢 🟡 🟠 🔴)
3. ✅ Cite evidence with `file:line` format
4. ✅ Group content by subsystem when applicable
5. ✅ End with clear action items
6. ✅ Apply PACE tone principles
7. ✅ Use code blocks for technical content
8. ✅ Provide confidence/status indicators

---

## Appendix A: Bengal Integration Notes

### Core Entry Points

- **Site**: `bengal/core/site.py` - Central orchestrator
- **Page**: `bengal/core/page/*.py` - Content model
- **Theme**: `bengal/core/theme.py` - Theme resolution
- **Asset**: `bengal/core/asset.py` - Static assets

### Orchestration Pipeline

- `bengal/orchestration/render_orchestrator.py` - Main render loop
- `bengal/orchestration/build_orchestrator.py` - Build coordination
- `bengal/orchestration/incremental_builder.py` - Incremental builds

### Rendering System

- `bengal/rendering/jinja_env.py` - Jinja environment setup
- `bengal/rendering/markdown/*.py` - Markdown processing
- `bengal/rendering/shortcodes/*.py` - Custom shortcodes
- `bengal/rendering/filters/*.py` - Jinja filters

### Cache System

- `bengal/cache/build_cache.py` - Build cache
- `bengal/cache/page_discovery_cache.py` - Discovery cache
- `bengal/cache/indexes/*.py` - Query indexes
- `bengal/cache/dependency_tracker.py` - Dependency tracking

### Health Validators

- `bengal/health/validators/*.py` - Validation rules
- `bengal/health/checks/*.py` - Health checks
- `bengal/health/reporting/*.py` - Report generation

### CLI Commands

- `bengal/cli/commands/*.py` - CLI commands
- `bengal/cli/helpers/*.py` - CLI helpers
- `bengal/cli/templates/*.py` - Project templates

### Testing

- `tests/unit/` - Unit tests (one per module)
- `tests/integration/` - Integration tests (feature-level)
- `tests/performance/` - Performance benchmarks
- `tests/_testing/` - Test utilities

---

## Appendix B: Prompting Techniques Reference

Quick reference to techniques used in Bengal rules:

### Zero-Shot Prompting
Used in: All rules (base capability)
- Provide task without examples
- Rely on model's pre-training

### Example-Guided Prompting
Used in: Research, RFC, Planning
- Use templates (claim schema, RFC structure, task structure)
- Show format, not full examples

### Chain-of-Thought (CoT)
Used in: RFC (tradeoffs), Validation, Reflexion
- Explicit reasoning steps
- Show "thinking" process
- Example: "Option A is better because [reason 1], [reason 2]"

### Self-Consistency
Used in: Research (HIGH criticality), RFC (critical claims), Validation
- Validate via multiple paths (code + tests + config)
- Check agreement across paths
- High confidence when 2+ paths agree

### ReAct (Reason + Act)
Used in: Orchestrator, Research, Implementation
- Interleave reasoning with tool use
- Pattern: Reason → Search → Read → Refine → Repeat
- Example: "I need to find the build method [reason] → search for 'def build' [act] → found in site.py [observe] → read file [act] → now I understand [reason]"

### RAG (Retrieval-Augmented Generation)
Used in: Orchestrator, Research, Help System
- Pull from `architecture/` docs
- Reference existing plans/RFCs
- Ground responses in codebase

### Self-Critique
Used in: Implementation (on errors), Reflexion
- Analyze own output
- Identify weaknesses
- Propose improvements
- Example: "My confidence is low because [analysis] → I should [improvement]"

### Reflexion
Used in: Reflexion Loop (Rule 8)
- Attempt → Evaluate → Reflect → Improve → Retry
- Learn from mistakes
- Iterative refinement

---

## Appendix C: Quality Checklist

Before shipping any artifact (RFC, plan, implementation), verify:

### RFC Checklist
- [ ] Problem statement clear with evidence
- [ ] Goals and non-goals explicit
- [ ] At least 2 design options analyzed
- [ ] Recommended option justified
- [ ] Architecture impact documented (subsystems)
- [ ] Risks identified with mitigations
- [ ] Performance and compatibility addressed
- [ ] All HIGH criticality claims validated (3-path)
- [ ] Confidence ≥ 85%
- [ ] Open questions flagged

### Plan Checklist
- [ ] Tasks grouped by subsystem and phase
- [ ] Dependencies clear (sequential vs parallel)
- [ ] Each task maps to atomic commit
- [ ] Commit messages pre-drafted
- [ ] Validation tasks included (tests, lints, health)
- [ ] Confidence gates defined
- [ ] Estimated time reasonable
- [ ] Confidence ≥ 85%

### Implementation Checklist
- [ ] Code changes minimal and focused
- [ ] Style matches existing code
- [ ] Type hints maintained/improved
- [ ] Docstrings updated
- [ ] Unit tests added/updated
- [ ] Integration tests pass
- [ ] Linter passes (no new errors)
- [ ] Health validators pass
- [ ] Atomic commit with descriptive message
- [ ] Confidence ≥ 90% (core) or ≥ 85% (other)

### Validation Checklist
- [ ] HIGH criticality claims validated via 3 paths
- [ ] Confidence scores computed with formula
- [ ] Evidence includes file:line references
- [ ] Inconsistencies identified and resolved
- [ ] Low-confidence items flagged for improvement
- [ ] Quality gates checked
- [ ] Action items clear and prioritized

### Retrospective Checklist
- [ ] Impact summary written (1-2 paragraphs)
- [ ] Key changes itemized with file:line refs
- [ ] `CHANGELOG.md` updated (Unreleased section)
- [ ] Planning docs moved to `plan/implemented/`
- [ ] Lessons learned captured (if applicable)
- [ ] Metrics included (tasks, files, lines, tests)
- [ ] Final confidence ≥ 90%
- [ ] Ready-to-ship status confirmed

---

## Conclusion

The Bengal Rule System (v2) provides a comprehensive, evidence-based framework for research, design, planning, implementation, and validation. By integrating advanced prompting techniques and maintaining strict guardrails against invented facts, the system ensures high-quality, confident outputs grounded in Bengal's codebase.

**Key Principles**:
1. **Never invent facts** - Always verify against code/tests
2. **Evidence-first** - Claims require code references
3. **Self-consistency** - Validate critical claims via 3 paths
4. **Transparent confidence** - Explicit scoring with formula
5. **Iterative improvement** - Reflexion loop for low confidence
6. **Bengal-aware** - Understands subsystems and architecture

**Next Steps**:
1. Convert this file to `.mdc` format (manually)
2. Test with first use case (e.g., cache optimization RFC)
3. Iterate based on real-world usage
4. Refine confidence thresholds and templates as needed

---

**Version**: 2.0  
**Last Updated**: 2025-10-23  
**Status**: Ready for Testing
