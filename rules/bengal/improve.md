---
description: Iterative improvement through reflexion - self-assessment, targeted actions, and regeneration
globs: ["plan/**/*.md", "bengal/**/*.py"]
alwaysApply: false
---

# Bengal Reflexion Loop

**Purpose**: Iterative improvement through self-assessment and regeneration.

**Shortcut**: `::improve`

**When to Use**:
- When validation reveals low confidence (< 70%)
- When initial RFC/plan has gaps or inconsistencies
- When implementation encounters unexpected issues
- For continuous refinement of artifacts

---

## Overview

Implements reflexion: Attempt → Evaluate → Reflect → Improve → Retry. Systematically improves low-confidence outputs through targeted actions.

---

## Reflexion Process

### Step 1: Initial Attempt

Produce initial output (RFC, plan, implementation) via standard rules.

### Step 2: Self-Evaluation

Run validation to assess:
- **Confidence Score**: Compute using formula
- **Gap Analysis**: What's missing or incorrect?
- **Inconsistencies**: Where do paths disagree?
- **Coverage**: Are all critical paths validated?

### Step 3: Reflection

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

### Step 4: Targeted Improvement

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
- Implement tests (if `::implement` phase)
- Flag for test addition (if `::rfc` phase)

**If claims unclear**:
- Rephrase with more specificity
- Add code examples
- Cite exact line numbers

### Step 5: Regenerate

Produce improved version of artifact:
- Update RFC with new evidence
- Refine plan with clearer tasks
- Fix implementation issues

### Step 6: Re-Evaluate

Run validation again. Compare:
- **Before Confidence**: [N]%
- **After Confidence**: [N]%
- **Improvement**: [+N]%

If confidence now meets threshold → success!
If still low → iterate again or escalate for SME input.

---

## Iteration Limits

- **Max Iterations**: 3 cycles
- **Convergence Check**: If improvement < 5% between iterations, stop and flag for human review
- **Divergence Check**: If confidence decreases, revert and flag issue

---

## Output Format

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

---

## Prompting Techniques

- **Self-Critique**: Systematic self-assessment
- **Reflexion**: Learn from mistakes and iterate
- **Chain-of-Thought**: Explicit reasoning about improvements

---

## Integration

Used by:
- **Validate**: Automatically suggests `::improve` for low-confidence results
- **Manual**: Invoke explicitly when artifacts need refinement
- **Workflows**: Can be chained after validation steps

---

## Example Scenario

**Initial RFC**: 65% confidence (LOW 🟠)
- Missing test evidence for 3 claims
- Config schema unclear

**Iteration 1**:
- Research test files more deeply
- Found 2/3 claims validated by integration tests
- Clarified config schema from `config/validators.py`
- New confidence: 78% (MODERATE 🟡)

**Iteration 2**:
- Added explicit unit test for remaining claim
- Updated RFC with precise config references
- New confidence: 87% (HIGH 🟢)

**Result**: RFC now meets 85% gate, ready for planning
