---
description: Central command dispatcher for Bengal development with shortcuts, natural language, and intelligent routing
alwaysApply: true
---

# Bengal Operating System (v3)

Central command interface for Bengal development. Routes commands to specialized rules through the **research → RFC → plan → implement → validate → ship** cycle.

**Works with**: All modules (inherited automatically)

---

## Command Shortcuts

```yaml
# Core Development Workflow
"::research": commands/research      # Evidence extraction from codebase
"::rfc": commands/rfc                # Draft RFC with design options
"::plan": commands/plan              # Convert RFC into actionable tasks
"::implement": commands/implement    # Guided code changes with guardrails
"::validate": commands/validate      # Deep validation with confidence scoring
"::retro": commands/retro            # Summarize impact, update changelog

# Validation Commands
"::types": validation/type-audit     # Audit type system (run mypy, check Any)
"::arch": validation/architecture-audit  # Check architecture compliance
"::coverage": validation/test-coverage   # Analyze test coverage

# Implementation Guides
"::new-directive": implementation/add-directive  # Guide: add MyST directive
"::new-filter": implementation/add-filter        # Guide: add Jinja filter
"::modify-core": implementation/core-model       # Guide: modify core model

# Utilities
"::?": commands/help                 # Context-aware help
"::help": commands/help              # Full command reference
"::auto": system/bengal-os           # Intelligent routing (AI decides)

# Workflow Chains
"::workflow-feature": workflows/feature   # research → RFC → plan
"::workflow-fix": workflows/fix           # research → plan → implement → validate
"::workflow-ship": workflows/ship         # validate → retro → changelog
```

---

## Natural Language Routing

### Research Intent
```yaml
triggers: [investigate, explore, understand, find, "how does", "what is", "where is"]
examples:
  - "How does PageCore work?"
  - "Where is incremental build implemented?"
  - "Understand the directive validation system"
routing: ::research
```

### Design Intent (RFC)
```yaml
triggers: [should we, design, architecture, options, propose, approach, tradeoffs]
examples:
  - "Should we add a plugin system?"
  - "Design options for lazy loading"
  - "Architecture for multi-language support"
routing: ::rfc (or ::research → ::rfc if no prior evidence)
```

### Implementation Intent
```yaml
triggers: [add, fix, implement, create, modify, refactor, update, change]
examples:
  - "Add a new directive for cards"
  - "Fix the taxonomy index bug"
  - "Implement lazy asset loading"
routing: ::implement (or ::plan → ::implement if complex)
```

### Validation Intent
```yaml
triggers: [verify, check, test, validate, audit, confidence, correct]
examples:
  - "Check my changes are correct"
  - "Validate the type signatures"
  - "Audit the architecture compliance"
routing: ::validate (or ::types / ::arch for specific audits)
```

---

## Intelligent Routing Logic

```yaml
if intent == RESEARCH:
  if focused_on_module:
    use: ::research (scoped to subsystem)
  else:
    use: ::research (broad scan)

if intent == RFC:
  if has_research_evidence:
    use: ::rfc
  else:
    chain: ::research → ::rfc

if intent == IMPLEMENT:
  if modifying_core:
    use: ::modify-core → ::implement
  elif adding_directive:
    use: ::new-directive → ::implement
  elif simple_change:
    use: ::implement
  else:
    chain: ::plan → ::implement

if intent == VALIDATE:
  if type_related:
    use: ::types
  elif architecture_related:
    use: ::arch
  else:
    use: ::validate
```

---

## Bengal Architecture Awareness

The system understands Bengal's subsystems:

### Core (`bengal/core/`) - PASSIVE MODELS
- **Site** - Root data container
- **Page** - Content model with PageCore contract
- **Section** - Directory/section model
- **Asset** - Static asset model
- **Theme** - Theme resolution

**Rule**: No I/O, no logging, no side effects

### Orchestration (`bengal/orchestration/`) - ACTIVE OPERATIONS
- **BuildOrchestrator** - Build coordination
- **RenderOrchestrator** - Page rendering
- **ContentOrchestrator** - Content discovery
- **AssetOrchestrator** - Asset processing

**Rule**: All I/O and logging happens here

### Rendering (`bengal/rendering/`)
- **TemplateEngine** - Jinja environment
- **Markdown Parser** - Content parsing
- **Directives** - MyST directive system
- **Filters** - Jinja filters

### Cache (`bengal/cache/`)
- **BuildCache** - Incremental build state
- **Indexes** - Query indexes (taxonomy, content)
- **DependencyTracker** - Cross-page dependencies

### Tests (`tests/`)
- **Unit** - Fast, isolated tests
- **Integration** - Full workflow tests
- **Roots** - Reusable test site fixtures

---

## Key Principles

1. **Types as Contracts** - Type signatures define behavior, not implementations
2. **Models are Passive** - No I/O in `bengal/core/`
3. **Evidence-First** - All claims require `file:line` references
4. **Fail Loudly** - Explicit errors over silent degradation
5. **Composition over Inheritance** - Mixins, not deep hierarchies

---

## Confidence Scoring

```yaml
confidence = Evidence(40) + Consistency(30) + Recency(15) + Tests(15) = 0-100%

thresholds:
  90-100%: HIGH 🟢 (ship it)
  70-89%: MODERATE 🟡 (review recommended)
  50-69%: LOW 🟠 (needs work)
  < 50%: UNCERTAIN 🔴 (do not ship)

quality_gates:
  rfc: 85%
  plan: 85%
  implementation_core: 90%
  implementation_other: 85%
```

---

## Quick Reference

| Task | Command | Time |
|------|---------|------|
| Understand code | `::research` | 10-15 min |
| Design feature | `::rfc` | 15-20 min |
| Break down work | `::plan` | 10 min |
| Make changes | `::implement` | varies |
| Verify quality | `::validate` | 10-15 min |
| Check types | `::types` | 5 min |
| Full feature | `::workflow-feature` | 30-45 min |
| Quick fix | `::workflow-fix` | 25-40 min |

---

## Error Handling

### Ambiguous Intent
```markdown
🤔 **Multiple Options Available**

Based on your request, I can:

1. **Research existing code** - `::research`
2. **Draft design proposal** - `::rfc`
3. **Start implementation** - `::implement`

Which would you like? (Or `::auto` to let me decide)
```

### Missing Context
```markdown
⚠️ **Need More Context**

To proceed with implementation, I need:
- [ ] Target file/module
- [ ] Expected behavior

Please provide more details or run `::research` first.
```

---

## Related Rules

### Modules (always applied)
- `modules/types-as-contracts` - Type-first philosophy
- `modules/architecture-patterns` - Model/orchestrator split
- `modules/evidence-handling` - Code reference patterns
- `modules/output-format` - Consistent formatting

### Commands
- `commands/research` - Evidence extraction
- `commands/rfc` - RFC drafting
- `commands/plan` - Task breakdown
- `commands/implement` - Code changes
- `commands/validate` - Deep validation

### Validation
- `validation/type-audit` - Type system audit with mypy
- `validation/architecture-audit` - Architecture compliance
- `validation/test-coverage` - Coverage analysis

### Implementation Guides
- `implementation/type-first` - Type-first development
- `implementation/add-directive` - Adding directives
- `implementation/add-filter` - Adding Jinja filters
- `implementation/core-model` - Modifying core models

### Workflows
- `workflows/feature` - Full feature development
- `workflows/fix` - Bug fix cycle
- `workflows/ship` - Pre-release validation
