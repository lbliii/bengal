---
description: Deep validation with 3-path self-consistency and transparent confidence scoring formula
globs: ["bengal/**/*.py", "tests/**/*.py", "plan/**/*.md"]
alwaysApply: false
---

# Bengal Validation & Confidence Scoring

**Purpose**: Deep audit with self-consistency and transparent confidence scores.

**Shortcut**: `::validate`

**Use Cases**:
- Pre-commit validation
- Post-implementation verification
- RFC/plan accuracy audit
- Critical path changes (core, orchestration)

---

## Overview

Validates code, claims, and implementations using multi-path verification and explicit confidence scoring. Critical claims validated via 3-path self-consistency.

---

## Validation Method

### Level 1: Standard Validation

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

### Level 2: Deep Validation (Self-Consistency)

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

---

## Confidence Scoring Formula

For each claim or change, compute confidence score:

```yaml
confidence_score = (
    evidence_strength +      # 0-40 points
    self_consistency +       # 0-30 points
    recency +                # 0-15 points
    test_coverage            # 0-15 points
) # Total: 0-100%
```

### Component Definitions

**Evidence Strength (0-40)**:
- 40: Direct code reference with file:line and excerpt
- 30: Direct code reference without excerpt
- 20: Docstring or comment only
- 10: Inferred from context
- 0: No evidence

**Self-Consistency (0-30)**:
- 30: All 3 paths agree (code + tests + config)
- 20: 2 paths agree, 1 N/A
- 10: 1 path only
- 5: Paths partially agree
- 0: Paths conflict

**Recency (0-15)**:
- 15: Modified in last 30 days
- 10: Modified in last 6 months
- 5: Modified in last 12 months
- 0: Older than 1 year or unknown

**Test Coverage (0-15)**:
- 15: Explicit unit/integration tests exist and pass
- 10: Tests exist but incomplete
- 5: Indirectly tested via integration tests
- 0: No tests found

### Interpretation Thresholds

- **90-100%**: HIGH confidence 🟢 (ship it)
- **70-89%**: MODERATE confidence 🟡 (review recommended)
- **50-69%**: LOW confidence 🟠 (needs work)
- **< 50%**: UNCERTAIN 🔴 (do not ship)

### Quality Gates

```yaml
gates:
  rfc_confidence: 85%      # RFC must have strong evidence
  plan_confidence: 85%     # Plan must be well-grounded
  implementation_core: 90% # Core modules require highest confidence
  implementation_other: 85% # Other modules slightly lower
  documentation: 70%       # Docs can be moderate
```

---

## Procedure

### Step 1: Identify Claims

Extract claims from:
- RFC/plan documents
- Code comments/docstrings
- Changed behavior

### Step 2: Validate Each Claim

For each claim:
1. Determine criticality (HIGH/MEDIUM/LOW)
2. If HIGH: apply 3-path self-consistency
3. If MEDIUM/LOW: apply path A (source code) only
4. Compute confidence score

### Step 3: Aggregate Results

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

---

## Output Format

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

---

## Prompting Techniques

- **Self-Consistency**: 3-path validation for HIGH criticality
- **Chain-of-Thought**: Explicit reasoning per claim
- **Self-Critique**: Post-validation analysis to identify gaps

---

## Integration

Used by:
- **Orchestrator**: Routes validation requests
- **RFC**: Validates critical claims before finalizing
- **Implementation**: Pre-commit validation
- **Reflexion**: Measures confidence improvement

Can be invoked:
- Explicitly via `::validate`
- Automatically via workflows (e.g., `::workflow-ship`)
- As part of reflexion loop
