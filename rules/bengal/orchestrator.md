---
description: Central command interface for intelligent routing and task orchestration based on user intent
globs: ["**/*.py", "**/*.md", "**/*.toml"]
alwaysApply: true
---

# Bengal Orchestrator

**Purpose**: Central command interface for intelligent routing and task orchestration.

**Shortcut**: `::auto`

---

## Overview

The orchestrator analyzes user requests and routes them to the appropriate Bengal rule based on intent and context. Supports both shortcuts and natural language queries.

---

## Routing Logic

### Step 1: Context Analysis

Automatically invoke **Context Analyzer** to gather:
- Code context (changed files, imports, dependents)
- Test context (coverage, related tests)
- Git context (recent commits, branch, diff)
- Architecture context (subsystems affected)

### Step 2: Intent Classification

Classify user request into primary intent:
- **RESEARCH**: Understanding existing code/behavior
- **RFC**: Design proposal or architectural decision
- **PLAN**: Task breakdown and organization
- **IMPLEMENT**: Code changes and edits
- **VALIDATE**: Verification and testing
- **IMPROVE**: Iterative enhancement
- **HELP**: Guidance and assistance

Use natural language triggers and context signals.

### Step 3: Smart Routing

```yaml
if intent == RESEARCH:
  if broad_exploratory:
    use: ::research (full scan)
  elif focused_on_module:
    use: ::research (scoped to module)

if intent == RFC:
  if has_evidence:
    use: ::rfc (draft from evidence)
  else:
    chain: ::research → ::rfc

if intent == PLAN:
  if has_rfc:
    use: ::plan (convert RFC to tasks)
  elif simple_task:
    use: ::plan (direct task breakdown)
  else:
    chain: ::research → ::rfc → ::plan

if intent == IMPLEMENT:
  if has_plan:
    use: ::implement (execute plan)
  else:
    chain: ::plan → ::implement

if intent == VALIDATE:
  if critical_changes_or_api:
    use: ::validate (deep audit with self-consistency)
  else:
    use: ::validate (standard verification)

if intent == IMPROVE:
  use: ::improve (reflexion loop)

if intent == HELP:
  use: ::? or ::help (help system)
```

### Step 4: Confirmation (Destructive Actions)

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

---

## Natural Language Support

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
  → Routes to ::research (rendering subsystem)

"Should we cache taxonomy index results?"
  → Routes to ::rfc (cache + taxonomy)

"Break down the incremental build implementation"
  → Routes to ::plan

"Implement incremental asset builds"
  → Routes to ::plan → ::implement chain

"Verify the health validator changes"
  → Routes to ::validate (health subsystem)

"What should I do with these uncommitted changes?"
  → Routes to ::? (context-aware help)
```

---

## Output Format

```markdown
## 🎯 Execution Plan

### Context Summary
[Brief context from Context Analyzer]

### Detected Intent
**Primary**: [RESEARCH/RFC/PLAN/IMPLEMENT/VALIDATE/IMPROVE/HELP]
**Confidence**: [HIGH/MEDIUM/LOW]

### Routing Decision
**Selected Rule**: [rule name]
**Reasoning**: [why this rule fits]

### Execution
[Immediately proceed to selected rule unless confirmation required]
```

---

## Prompting Techniques

- **ReAct**: Reason about intent, search context, route to rule
- **RAG**: Pull from `architecture/` docs and recent context
- **Chain-of-Thought**: Explicit reasoning for routing decision

---

## Integration

Works seamlessly with all Bengal rules and workflows. Can be invoked explicitly via `::auto` or implicitly when user provides natural language queries without specific shortcuts.
