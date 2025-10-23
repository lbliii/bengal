---
description: Draft evidence-backed RFC for design decisions with architecture impact analysis and tradeoffs
globs: ["plan/active/*.md", "architecture/**/*.md"]
alwaysApply: false
---

# Bengal RFC Drafting

**Purpose**: Draft evidence-backed Request for Comments (RFC) for design decisions.

**Shortcut**: `::rfc`

**Input**: Verified claims from Research or existing research artifacts.

---

## Overview

Creates structured design proposals grounded in code evidence. Uses Chain-of-Thought reasoning for tradeoffs and self-consistency validation for critical claims.

---

## RFC Structure

### 1. Metadata
```yaml
Title: [Brief, descriptive title]
Author: [AI + Human reviewer]
Date: [YYYY-MM-DD]
Status: [Draft | Review | Accepted | Implemented]
Confidence: [0-100%]
```

### 2. Problem Statement
- **Current State**: What exists today (with evidence)
- **Pain Points**: Issues, limitations, technical debt
- **User Impact**: Who is affected and how

### 3. Goals & Non-Goals

**Goals**:
- [Goal 1: Specific, measurable]
- [Goal 2]

**Non-Goals** (explicit scope boundaries):
- [What we're NOT solving]

### 4. Architecture Impact

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

### 5. Design Options

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

### 6. Detailed Design (Selected Option)

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

### 7. Tradeoffs & Risks

**Tradeoffs**:
- [Tradeoff 1: what we gain vs lose]

**Risks**:
- **Risk 1**: [Description]
  - **Likelihood**: [Low/Medium/High]
  - **Impact**: [Low/Medium/High]
  - **Mitigation**: [How to address]

### 8. Performance & Compatibility

**Performance Impact**:
- Build time: [expected change]
- Memory: [expected change]
- Cache implications: [invalidation, new indexes]

**Compatibility**:
- Breaking changes: [yes/no, details]
- Migration path: [how users upgrade]
- Deprecation timeline: [if applicable]

### 9. Migration & Rollout

**Implementation Phases**:
1. [Phase 1: Foundation]
2. [Phase 2: Core functionality]
3. [Phase 3: Polish & documentation]

**Rollout Strategy**:
- Feature flag: [yes/no]
- Beta period: [duration]
- Documentation updates: [list]

### 10. Open Questions

- [ ] **Question 1**: [Needs SME input or research]
- [ ] **Question 2**: [Requires benchmarking]

---

## Procedure

### Step 1: Gather Evidence

Ensure research is complete. If not, run `::research` automatically.

### Step 2: Draft Sections

Use RFC template, fill with evidence from research.

### Step 3: Apply Chain-of-Thought

For design options, show explicit reasoning:
- Why Option A is better/worse than Option B
- What assumptions drive the recommendation
- How trade-offs were evaluated

### Step 4: Self-Consistency Check

Validate critical claims (API, behavior, config) via 3 paths:
- Code evidence
- Test evidence
- Config/schema evidence

### Step 5: Confidence Scoring

Apply confidence scoring formula (see Confidence Scoring rule):
```yaml
confidence = Evidence(40) + Consistency(30) + Recency(15) + Tests(15)
```

Gate: RFC requires **≥85% confidence** to proceed to planning.

---

## Output Format

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
- [ ] Run `::plan` to convert to implementation tasks
```

---

## Prompting Techniques

- **Chain-of-Thought**: Explicit reasoning for design tradeoffs
- **Self-Consistency**: 3-path validation for critical API/behavior claims
- **Example-guided**: Use RFC template structure
- **RAG**: Pull from `architecture/` docs for context

---

## Quality Checklist

Before finalizing RFC:
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
