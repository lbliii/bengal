---
description: Evaluate RFC for evidence quality, design completeness, and confidence scoring
alwaysApply: false
globs: ["plan/**/*.md"]
---

# RFC Evaluation

Evaluate an RFC for evidence quality, design completeness, and readiness.

**Shortcut**: `::rfc-eval`

**Works with**: `modules/evidence-handling`, `modules/output-format`

---

## RFC Lifecycle Position

```
plan/drafted/    →    plan/evaluated/    →    plan/ready/    →    DELETE
     ↑                      ↑                      ↑
  ::rfc               ::rfc-eval               ::plan
```

---

## Procedure

### Step 1: Evidence Audit

For each claim in the RFC:

```yaml
claim_audit:
  - claim: "[Claim text]"
    has_evidence: [yes/no]
    evidence_quality: [direct_code/test/inferred/none]
    file_line_refs: [list of references]
    needs_verification: [yes/no]
```

**Scoring**:
- Direct code reference with excerpt: 40 points
- Test reference: 30 points
- Inferred from context: 10 points
- No evidence: 0 points (flag for revision)

### Step 2: Design Completeness

Check RFC sections:

| Section | Present | Quality | Notes |
|---------|---------|---------|-------|
| Executive Summary | ✅/❌ | [Good/Needs work] | |
| Problem Statement | ✅/❌ | [Good/Needs work] | |
| Goals/Non-Goals | ✅/❌ | [Good/Needs work] | |
| Design Options (≥2) | ✅/❌ | [Good/Needs work] | |
| Recommended Approach | ✅/❌ | [Good/Needs work] | |
| Architecture Impact | ✅/❌ | [Good/Needs work] | |
| Risks & Mitigations | ✅/❌ | [Good/Needs work] | |
| Implementation Plan | ✅/❌ | [Good/Needs work] | |

### Step 3: 3-Path Validation (HIGH Criticality)

For claims about:
- API contracts
- Core behavior changes
- User-facing features
- Performance characteristics

Run 3-path validation:

```yaml
claim: "[HIGH criticality claim]"
path_a_source:
  location: "file:line"
  finding: "[What was found]"
  status: ✅/❌
  
path_b_tests:
  location: "file:line"
  finding: "[What tests show]"
  status: ✅/❌
  
path_c_config:
  location: "file:line or N/A"
  finding: "[Config/schema status]"
  status: ✅/❌/N/A

agreement: [3/3, 2/3, 1/3, conflict]
```

### Step 4: Calculate Confidence Score

```yaml
confidence = (
    evidence_strength +      # 0-40
    self_consistency +       # 0-30
    recency +                # 0-15
    completeness             # 0-15
) = 0-100%

thresholds:
  90-100%: Excellent - ready for planning 🟢
  85-89%: Good - minor improvements optional 🟢
  70-84%: Moderate - address gaps before planning 🟡
  50-69%: Weak - significant revision needed 🟠
  < 50%: Insufficient - major revision required 🔴
```

### Step 5: Identify Action Items

```yaml
critical_issues:  # Must fix before approval
  - "[Issue requiring RFC revision]"

recommended_improvements:  # Should fix
  - "[Improvement that would strengthen RFC]"

optional_enhancements:  # Nice to have
  - "[Optional improvement]"

open_questions:  # Need answers
  - "[Question that blocks approval]"
```

---

## Output Format

```markdown
## 🔍 RFC Evaluation: [RFC Title]

### Executive Summary
[2-3 sentences: overall assessment, confidence, recommendation]

---

### Evidence Quality

| Claim | Evidence | Quality | Status |
|-------|----------|---------|--------|
| [Claim 1] | `file:line` | Direct | ✅ |
| [Claim 2] | Inferred | Weak | ⚠️ |
| [Claim 3] | None | Missing | ❌ |

**Evidence Score**: [N]/40

---

### Design Completeness

| Section | Status | Notes |
|---------|--------|-------|
| Problem Statement | ✅ | Clear with evidence |
| Design Options | ⚠️ | Only 1 option, need alternatives |
| Architecture Impact | ❌ | Missing |

**Completeness Score**: [N]/15

---

### HIGH Criticality Validation

#### Claim: [Critical claim text]

| Path | Location | Finding | Status |
|------|----------|---------|--------|
| Source | `file:line` | [Finding] | ✅ |
| Tests | `file:line` | [Finding] | ✅ |
| Config | N/A | Not applicable | - |

**Agreement**: 2/2 applicable paths agree

---

### Confidence Score

| Component | Score | Max |
|-----------|-------|-----|
| Evidence Strength | [N] | 40 |
| Self-Consistency | [N] | 30 |
| Recency | [N] | 15 |
| Completeness | [N] | 15 |
| **Total** | **[N]** | **100** |

**Confidence**: [N]% [emoji]

---

### 📋 Action Items

**Critical (must fix)**:
- [ ] [Item]

**Recommended**:
- [ ] [Item]

**Open Questions**:
- [ ] [Question]

---

### Recommendation

[APPROVE / REVISE / REJECT]

**Reasoning**: [Why this recommendation]

**Next Steps**:
- If APPROVE: Move to `plan/evaluated/`, proceed to `::plan`
- If REVISE: Address critical items, re-run `::rfc-eval`
- If REJECT: [Reason and alternative approach]
```

---

## Approval Criteria

**APPROVE** when:
- Confidence ≥ 85%
- No critical issues
- All HIGH criticality claims validated
- At least 2 design options analyzed

**REVISE** when:
- Confidence 70-84%
- Has fixable critical issues
- Missing evidence that can be gathered

**REJECT** when:
- Confidence < 70%
- Fundamental design flaws
- Problem statement invalid
- Better approached differently

---

## After Approval

```bash
# Move RFC to evaluated
mv plan/drafted/rfc-[name].md plan/evaluated/

# Update status in file
Status: Evaluated

# Proceed to planning
::plan
```

---

## Related

- `commands/research` - Gather more evidence if needed
- `commands/rfc` - RFC drafting
- `commands/plan` - Convert to tasks after approval
- `commands/validate` - General validation patterns

