---
description: Bengal AI rule system for research, RFC, planning, implementation, validation, and shipping workflows
alwaysApply: true
---

# Bengal Rule System (v2)

## Purpose

AI-assisted rules for Bengal's **research → RFC → plan → implement → validate → ship** workflow. Grounded in Bengal's architecture and test suite. Incorporates advanced prompting techniques from [promptingguide.ai](https://www.promptingguide.ai/techniques).

---

## Quick Reference

### Core Commands

```yaml
::auto           # Intelligent orchestration based on intent and context
::analyze        # Deep context analysis (code, tests, git, architecture)
::research       # Evidence-first research from codebase
::rfc            # Draft RFC from verified evidence
::plan           # Convert RFC into actionable plan/to-dos
::implement      # Drive implementation (edits, tests, lints)
::validate       # Deep audit with self-consistency + confidence scoring
::retro          # Summarize impact; update changelog
::improve        # Reflexion loop: iterative improvement
::?              # Context-aware help ("what should I do here?")
::help           # Full command reference
```

### Workflow Chains

```yaml
::workflow-feature    # Full feature: research → RFC → plan
::workflow-fix        # Quick fix: research → plan → implement
::workflow-ship       # Pre-release: validate → retro → changelog
::workflow-full       # Complete cycle: research → ... → retro
```

---

## Rule System Components

### 1. Core Orchestration
- **[Orchestrator](orchestrator.md)** - Central command interface for routing
- **[Context Analyzer](context-analyzer.md)** - Deep context understanding

### 2. Development Workflow
- **[Research](research.md)** - Evidence-first codebase research
- **[RFC](rfc.md)** - Evidence-backed design proposals
- **[Plan](plan.md)** - Task breakdown and sequencing
- **[Implement](implement.md)** - Guided code changes with guardrails

### 3. Quality & Validation
- **[Validate](validate.md)** - Deep validation with confidence scoring
- **[Confidence Scoring](confidence-scoring.md)** - Transparent scoring formula
- **[Improve](improve.md)** - Reflexion loop for iterative refinement

### 4. Documentation & Support
- **[Retro](retro.md)** - Retrospectives and changelog updates
- **[Help](help.md)** - Context-aware assistance
- **[Communication Style](communication-style.md)** - Output formatting standards

### 5. Workflows
- **[Workflows](workflows.md)** - Pre-built workflow chains

---

## Natural Language Support

The system understands plain English and routes intelligently:

```text
"How does the rendering pipeline work?"
  → Routes to ::research

"Should we add caching to taxonomy?"
  → Routes to ::rfc

"Break down the incremental build implementation"
  → Routes to ::plan

"Verify my core module changes"
  → Routes to ::validate

"What should I do with these uncommitted changes?"
  → Routes to ::? (context-aware help)
```

**Trigger Keywords**:
- **Research**: investigate, explore, how does, understand, find
- **RFC**: should we, design, architecture, options, propose
- **Plan**: break down, tasks, steps, organize, structure
- **Implement**: add, fix, implement, change, build, create
- **Validate**: verify, check, test, validate, audit, confidence
- **Improve**: improve, enhance, refine, better, iterate
- **Help**: help, how, what, guide, show, ?, explain

---

## Key Principles

1. **Never Invent Facts** - Always verify against code/tests
2. **Evidence-First** - Claims require code references (`file:line`)
3. **Self-Consistency** - Validate critical claims via 3 paths (code, tests, config)
4. **Transparent Confidence** - Explicit scoring with formula
5. **Iterative Improvement** - Reflexion loop for low confidence
6. **Bengal-Aware** - Understands all subsystems and architecture

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

## Prompting Techniques

The system uses advanced prompting techniques:

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

## Tips

1. **Start with Research**: Use `::research` to understand before planning
2. **Use Workflows**: Pre-built chains save time
3. **Validate Often**: Run `::validate` before committing critical changes
4. **Let AI Decide**: Use `::auto` when unsure which command to use
5. **Iterate**: Use `::improve` to refine low-confidence outputs
6. **Get Help**: Type `::?` anytime you're stuck

---

## Version & Status

**Version**: 2.0
**Last Updated**: 2025-10-23
**Status**: Production Ready

---

For detailed information on each rule, refer to the individual rule files linked above.
