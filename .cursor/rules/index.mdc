---
description: Bengal command dispatcher with shortcuts, natural language routing, and intelligent orchestration
alwaysApply: true
---

# Bengal Operating System (v2)

Central command interface for Bengal's development workflow. Supports shortcut commands, natural language understanding, and intelligent routing through **research → RFC → plan → implement → validate → ship** cycles.

Grounded in Bengal's architecture and test suite. Incorporates advanced prompting techniques from [promptingguide.ai](https://www.promptingguide.ai/techniques).

---

## Command Shortcuts

When user provides one of the following commands, perform its associated task:

```yaml
# Core Development Workflow
"::research": research          # Evidence-first research from codebase
"::rfc": rfc                    # Draft RFC from verified evidence
"::plan": plan                  # Convert RFC into actionable plan/to-dos
"::implement": implement        # Drive implementation (edits, tests, lints)
"::validate": validate          # Deep audit with self-consistency + confidence scoring
"::retro": retro                # Summarize impact; update changelog

# Utilities
"::analyze": context-analyzer   # Deep context analysis (code, tests, git, architecture)
"::improve": improve            # Reflexion loop: iterative improvement
"::?": help (context-aware)     # Context-aware help ("what should I do here?")
"::help": help (full reference) # Full command reference
"::auto": orchestrator          # Intelligent rule selection (AI decides)

# Workflow Chains
"::workflow-feature": workflows     # Full feature: research → RFC → plan
"::workflow-fix": workflows         # Quick fix: research → plan → implement
"::workflow-ship": workflows        # Pre-release: validate → retro → changelog
"::workflow-full": workflows        # Complete cycle: research → ... → retro
```

---

## Natural Language Support

System understands plain English requests and routes intelligently:

### Research Requests
```yaml
triggers: [investigate, explore, understand, find, how does, what is, where is]
examples:
  - "How does the rendering pipeline work?"
  - "Understand the cache dependency tracker"
  - "Where is incremental build implemented?"
routing: ::research (evidence extraction from codebase)
```

### Design Requests (RFC)
```yaml
triggers: [should we, design, architecture, options, propose, approach, tradeoffs]
examples:
  - "Should we add caching to taxonomy?"
  - "Design options for incremental assets"
  - "Architecture for plugin system"
routing: ::rfc (evidence-backed design proposal)
```

### Planning Requests
```yaml
triggers: [break down, tasks, steps, organize, structure, divide, checklist]
examples:
  - "Break down the incremental build implementation"
  - "Create a plan for refactoring the cache"
  - "What tasks are needed for this feature?"
routing: ::plan (actionable task breakdown)
```

### Implementation Requests
```yaml
triggers: [add, fix, implement, change, build, create, modify, refactor, update]
examples:
  - "Implement incremental asset processing"
  - "Fix the taxonomy index bug"
  - "Add support for custom validators"
routing: ::implement (guided code changes)
```

### Validation Requests
```yaml
triggers: [verify, check, test, validate, audit, confidence, accuracy, correct]
examples:
  - "Verify my core module changes"
  - "Validate the rendering pipeline"
  - "Check confidence of this RFC"
routing: ::validate (deep audit with confidence scoring)
```

### Improvement Requests
```yaml
triggers: [improve, enhance, refine, better, iterate, polish, fix issues]
examples:
  - "Improve this low-confidence RFC"
  - "Refine the validation results"
  - "Make this plan better"
routing: ::improve (reflexion loop)
```

### Help Requests
```yaml
triggers: [help, how, what, explain, guide, show, ?, assist]
examples:
  - "What should I do with these uncommitted changes?"
  - "Help me with this"
  - "What can I do here?"
routing: ::? (context-aware suggestions)
```

---

## Intelligent Routing

When user's intent is detected from natural language:

### Step 1: Classify Intent
- Research, RFC, Plan, Implement, Validate, Improve, or Help?
- High confidence: Route directly
- Low confidence: Ask for clarification

### Step 2: Context Detection (via context-analyzer)
- What files are open? Git status?
- Which subsystems affected (Core/Orchestration/Rendering/Cache/Health/CLI)?
- Uncommitted changes? Test coverage?
- Document age and recency?

### Step 3: Smart Routing
```yaml
if intent == RESEARCH:
  if broad_exploratory:
    use: ::research (full scan of bengal/)
  elif focused_on_module:
    use: ::research (scoped to specific subsystem)

if intent == RFC:
  if has_evidence:
    use: ::rfc (draft from evidence)
  else:
    chain: ::research → ::rfc (gather evidence first)

if intent == PLAN:
  if has_rfc:
    use: ::plan (convert RFC to tasks)
  elif simple_task:
    use: ::plan (direct task breakdown)
  else:
    chain: ::research → ::rfc → ::plan (full design flow)

if intent == IMPLEMENT:
  if has_plan:
    use: ::implement (execute plan)
  else:
    chain: ::plan → ::implement (create plan first)

if intent == VALIDATE:
  if critical_changes_core_or_api:
    use: ::validate (deep audit, 3-path self-consistency)
  else:
    use: ::validate (standard verification)

if intent == IMPROVE:
  if validation_shows_low_confidence:
    use: ::improve (reflexion loop, up to 3 iterations)
  else:
    suggest: "Confidence already high, manual review recommended"

if intent == HELP:
  use: ::? (context-aware suggestions based on open files and git status)
```

### Step 4: Confirmation (for Destructive Actions)
```markdown
⚠️ **Confirm Action**

You've requested: "[user query]"

This will:
- Modify [N] files in bengal/core/
- Update [N] test files
- Run linter and fix issues

**Affected files**: [list]

Proceed? (yes/no)
```

---

## Key Principles

1. **Never Invent Facts** - Always verify against code/tests
2. **Evidence-First** - Claims require code references (`file:line`)
3. **Self-Consistency** - Validate critical claims via 3 paths (code, tests, config)
4. **Transparent Confidence** - Explicit scoring with formula
5. **Iterative Improvement** - Reflexion loop for low confidence
6. **Bengal-Aware** - Understands all subsystems and architecture

---

## Quick Reference

### Most Common Commands

**Research & Design**:
- `::research` - Extract evidence from codebase (10-15 min)
- `::rfc` - Draft design proposal with options (15-20 min)

**Planning & Implementation**:
- `::plan` - Break down into atomic tasks (10 min)
- `::implement` - Guided code changes + tests (varies)

**Quality Assurance**:
- `::validate` - Deep validation with confidence scoring (10-15 min)
- `::improve` - Iterative refinement (5-15 min)

**Workflows**:
- `::workflow-feature` - Full design flow (30-45 min)
- `::workflow-fix` - Quick fix cycle (25-40 min)
- `::workflow-ship` - Pre-merge validation (20-30 min)

**Help**:
- `::?` - "What can I do here?" (context-aware)
- `::help` - Full command reference
- `::auto` - Let AI choose best action

---

## Command Decision Guide

### "Which workflow should I use?"

**Use `::workflow-feature`** when:
- Starting a new feature from scratch
- Need full design documentation
- Architectural changes required
- Output: Research → RFC → Plan (ready for implementation)

**Use `::workflow-fix`** when:
- Fixing a bug or small improvement
- Changes are straightforward
- No RFC needed
- Output: Research → Plan → Implementation → Validation

**Use `::workflow-ship`** when:
- Feature is implemented
- Pre-merge validation needed
- Ready to update changelog
- Output: Validation → Retrospective → Changelog

### "Should I validate before or after implementation?"

**Validate Before (::validate on RFC/Plan)** when:
- Critical API changes
- Core module modifications (bengal/core/, bengal/orchestration/)
- Need confidence before investing time in implementation

**Validate After (::validate on code)** when:
- Implementation complete
- Pre-commit check
- Ensure tests and confidence meet gates

### "Should I use shortcuts or natural language?"

**Use Shortcuts** when:
- You know exactly what you want
- Want fastest execution
- Familiar with the system

**Use Natural Language** when:
- Not sure which command to use
- Describing a goal rather than a specific action
- Want the system to figure out best approach

**Use `::auto`** when:
- Want AI to analyze context and decide
- Complex scenario with multiple possible approaches
- Learning the system

---

## Confidence Scoring

### Formula
```yaml
confidence = Evidence(40) + Consistency(30) + Recency(15) + Tests(15) = 0-100%
```

### Interpretation
- **90-100%**: HIGH 🟢 (ship it)
- **70-89%**: MODERATE 🟡 (review recommended)
- **50-69%**: LOW 🟠 (needs work)
- **< 50%**: UNCERTAIN 🔴 (do not ship)

### Quality Gates
```yaml
rfc_confidence: 85%           # RFC must have strong evidence
plan_confidence: 85%          # Plan must be well-grounded
implementation_core: 90%      # Core modules require highest confidence
implementation_other: 85%     # Other modules slightly lower
```

---

## Bengal Architecture

The system is aware of Bengal's subsystems:

### Core (`bengal/core/`)
- **Site**: Central orchestrator
- **Page**: Content model
- **Section**: Content organization
- **Asset**: Static assets
- **Theme**: Theme resolution

### Orchestration (`bengal/orchestration/`)
- **Render Orchestrator**: Main render loop
- **Build Orchestrator**: Build coordination
- **Incremental Builder**: Incremental builds

### Rendering (`bengal/rendering/`)
- **Jinja Environment**: Template engine setup
- **Markdown**: Markdown processing
- **Shortcodes**: Custom shortcodes
- **Filters**: Jinja filters

### Cache (`bengal/cache/`)
- **Build Cache**: Build state
- **Discovery Cache**: Content discovery
- **Indexes**: Query indexes
- **Dependency Tracker**: Dependency tracking

### Health (`bengal/health/`)
- **Validators**: Content validators
- **Checks**: Health checks
- **Reporting**: Report generation

### CLI (`bengal/cli/`)
- **Commands**: CLI commands
- **Helpers**: CLI utilities
- **Templates**: Project templates

---

## Error Handling

### Command Not Recognized
```markdown
❌ **Command Not Recognized**

I didn't understand: "[user input]"

**Did you mean**:
- `::research` - Investigate codebase
- `::validate` - Check quality and confidence
- `::workflow-fix` - Quick fix workflow

Or describe what you're trying to do in plain language.

**Need help?** Type `::?` for suggestions or `::help` for full reference.
```

### Ambiguous Intent
```markdown
🤔 **Multiple Options Available**

Based on your request "[user query]", I can:

1. **Research existing implementation** (Recommended)
   - Command: `::research`
   - Best for: Understanding how it currently works

2. **Draft design proposal**
   - Command: `::rfc`
   - Best for: Proposing changes or new features

3. **Validate existing code**
   - Command: `::validate`
   - Best for: Checking quality and confidence

Which would you like? (Or say `::auto` and I'll choose)
```

---

## Prompting Techniques

The system uses advanced prompting techniques from [promptingguide.ai](https://www.promptingguide.ai/techniques):

- **Zero-Shot**: Base capability for all rules
- **Example-Guided**: Templates and schemas (Research, RFC, Plan)
- **Chain-of-Thought**: Explicit reasoning (RFC tradeoffs, Validation)
- **Self-Consistency**: 3-path validation (Research HIGH criticality, RFC, Validate)
- **ReAct**: Reason + act cycles (Orchestrator, Research, Implement)
- **RAG**: Retrieval from `architecture/` and codebase (Orchestrator, Research)
- **Self-Critique**: Post-analysis (Implement errors, Improve)
- **Reflexion**: Iterative refinement (Improve rule)

---

## Usage Examples

### Example 1: Research a Feature

```text
User: "How does the cache dependency tracker work?"

System:
  1. Routes to ::research
  2. Scans bengal/cache/dependency_tracker.py
  3. Finds tests in tests/unit/test_dependency_tracker.py
  4. Extracts claims with code references
  5. Applies 3-path validation for HIGH criticality
  6. Returns structured claims with confidence scores
```

### Example 2: Design a Feature

```text
User: "Should we add incremental asset processing?"

System:
  1. Routes to ::rfc (via ::auto)
  2. First runs ::research on asset system
  3. Drafts RFC with:
     - Current state (with evidence)
     - Design options (with tradeoffs)
     - Recommended approach
     - Architecture impact
  4. Validates critical claims (3-path)
  5. Returns RFC with 87% confidence
```

### Example 3: Implement from Plan

```text
User: "Implement task 1.1 from the incremental build plan"

System:
  1. Routes to ::implement
  2. Reads plan/active/plan-incremental-build.md
  3. Verifies current code state
  4. Makes minimal edits to bengal/core/site.py
  5. Updates tests/unit/test_site.py
  6. Runs linter
  7. Creates atomic commit with pre-drafted message
```

### Example 4: Validate Before Merge

```text
User: "::validate"

System:
  1. Analyzes uncommitted changes
  2. Identifies affected subsystems (Core, Orchestration)
  3. Extracts claims from changes
  4. Applies 3-path validation for HIGH criticality
  5. Computes confidence: 92% 🟢
  6. Returns detailed validation report
  7. Confirms ready to merge
```

### Example 5: Full Feature Workflow

```text
User: "::workflow-feature - design pagination system"

System:
  1. ::analyze - understand current rendering pipeline
  2. ::research - extract evidence about page rendering
  3. ::rfc - draft pagination design with options
  4. Checkpoint: review RFC (confidence 88%)
  5. ::plan - break down into 12 tasks across 4 phases
  6. Ready for ::implement
```

---

## Getting Started

### First Time Use

1. **Start with Help**: Type `::?` to get context-aware suggestions
2. **Try Natural Language**: "How does the Site class work?"
3. **Use Workflows**: `::workflow-fix` for small changes

### Common Workflows

**Fixing a Bug**:
```text
::workflow-fix → Research → Plan → Implement → Validate
```

**Adding a Feature**:
```text
::workflow-feature → Research → RFC → Plan
[User implements]
::validate
::retro
```

**Pre-Release Check**:
```text
::workflow-ship → Validate → Retro → Changelog
```

---

## Quality Checklists

### RFC Checklist
- [ ] Problem statement clear with evidence
- [ ] Goals and non-goals explicit
- [ ] At least 2 design options analyzed
- [ ] Recommended option justified
- [ ] Architecture impact documented
- [ ] Risks identified with mitigations
- [ ] All HIGH criticality claims validated (3-path)
- [ ] Confidence ≥ 85%

### Implementation Checklist
- [ ] Code changes minimal and focused
- [ ] Style matches existing code
- [ ] Type hints maintained/improved
- [ ] Docstrings updated
- [ ] Unit tests added/updated
- [ ] Integration tests pass
- [ ] Linter passes
- [ ] Confidence ≥ 90% (core) or ≥ 85% (other)

### Validation Checklist
- [ ] HIGH criticality claims validated via 3 paths
- [ ] Confidence scores computed
- [ ] Evidence includes file:line references
- [ ] Low-confidence items flagged
- [ ] Quality gates checked

---

## Rule System Components

This OS routes commands to specialized rule files:

- **[context-analyzer.md](context-analyzer.md)** - Deep context analysis (code, tests, git, architecture)
- **[research.md](research.md)** - Evidence extraction from codebase
- **[rfc.md](rfc.md)** - RFC drafting with design options
- **[plan.md](plan.md)** - Task breakdown and sequencing
- **[implement.md](implement.md)** - Guided code changes with guardrails
- **[validate.md](validate.md)** - Deep validation with confidence scoring
- **[improve.md](improve.md)** - Reflexion loop for iterative refinement
- **[retro.md](retro.md)** - Retrospectives and changelog updates
- **[workflows.md](workflows.md)** - Pre-built workflow chains
- **[confidence-scoring.md](confidence-scoring.md)** - Transparent scoring formula
- **[communication-style.md](communication-style.md)** - Output formatting standards

Each rule file is automatically activated when working with relevant file types (see frontmatter globs).

---

## Tips

1. **Start with Research**: Use `::research` to understand before planning
2. **Use Workflows**: Pre-built chains save time (`::workflow-feature`, `::workflow-fix`)
3. **Validate Often**: Run `::validate` before committing critical changes
4. **Let AI Decide**: Use `::auto` when unsure which command to use
5. **Iterate**: Use `::improve` to refine low-confidence outputs
6. **Get Help**: Type `::?` anytime you're stuck

---

## Success Criteria

✅ **Discoverability**: Users find right command easily (shortcuts + natural language)
✅ **Flexibility**: Multiple ways to achieve goals (direct commands, natural language, `::auto`)
✅ **Intelligence**: System understands context and intent (smart routing)
✅ **Quality**: High-confidence outputs with transparent scoring
✅ **Speed**: Efficient workflows for common tasks (feature, fix, ship)
✅ **Simplicity**: Clear, uncluttered command set
✅ **Power**: Advanced features available when needed (reflexion, self-consistency)

---

**Version**: 2.0
**Last Updated**: 2025-10-23
**Status**: Production Ready
