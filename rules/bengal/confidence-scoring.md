---
description: Transparent confidence scoring formula used across all validation activities
globs: ["bengal/**/*.py", "tests/**/*.py", "plan/**/*.md"]
alwaysApply: false
---

# Bengal Confidence Scoring System

**Purpose**: Transparent, reproducible confidence quantification.

**Used By**: All validation rules (especially Validate rule)

---

## Overview

Provides explicit scoring formula for assessing confidence in claims, implementations, and design decisions. Ensures transparency and consistency across all validation activities.

---

## Scoring Formula

```yaml
confidence_score = (
    evidence_strength +      # 0-40 points
    self_consistency +       # 0-30 points
    recency +                # 0-15 points
    test_coverage            # 0-15 points
) # Total: 0-100%
```

---

## Component Definitions

### Evidence Strength (0-40 points)

Measures quality of code references:

- **40 points**: Direct code reference with file:line and excerpt
  - Example: `bengal/core/site.py:145-150` with quoted code
- **30 points**: Direct code reference without excerpt
  - Example: `bengal/core/site.py:145` (line only)
- **20 points**: Docstring or comment only (no implementation verified)
- **10 points**: Inferred from context or indirect evidence
- **0 points**: No evidence or assumption only

### Self-Consistency (0-30 points)

Measures agreement across validation paths:

- **30 points**: All 3 paths agree (code + tests + config/schema)
- **20 points**: 2 paths agree, 1 path not applicable
- **10 points**: 1 path only (e.g., code only, no tests)
- **5 points**: Paths partially agree (minor discrepancies)
- **0 points**: Paths conflict (code says X, tests expect Y)

**Note**: Only apply 3-path for HIGH criticality claims. For MEDIUM/LOW, use code path only (assign 20 points if code verified, 10 if not).

### Recency (0-15 points)

Measures staleness of evidence:

- **15 points**: Modified in last 30 days
- **10 points**: Modified in last 6 months
- **5 points**: Modified in last 12 months
- **0 points**: Older than 1 year or unknown

Use `git log` to check last modification date of evidence files.

### Test Coverage (0-15 points)

Measures test quality:

- **15 points**: Explicit unit/integration tests exist and pass
  - Example: `test_incremental_build()` directly tests claimed behavior
- **10 points**: Tests exist but incomplete (edge cases missing)
- **5 points**: Indirectly tested via integration tests only
- **0 points**: No tests found

---

## Interpretation Thresholds

### Confidence Levels

- **90-100%**: HIGH confidence 🟢
  - **Action**: Ship it
  - **Gate**: Required for core implementation

- **70-89%**: MODERATE confidence 🟡
  - **Action**: Review recommended, acceptable for non-critical
  - **Gate**: Required for RFC/plan

- **50-69%**: LOW confidence 🟠
  - **Action**: Needs improvement before shipping
  - **Gate**: Run `::improve` reflexion loop

- **< 50%**: UNCERTAIN 🔴
  - **Action**: Do not ship, requires major work
  - **Gate**: Block until evidence/tests added

---

## Quality Gates

Different thresholds for different artifact types:

```yaml
gates:
  rfc_confidence: 85%      # RFC must have strong evidence
  plan_confidence: 85%     # Plan must be well-grounded
  implementation_core: 90% # Core modules require highest confidence
  implementation_other: 85% # Other modules slightly lower
  documentation: 70%       # Docs can be moderate (user-facing)
```

---

## Example Calculations

### Example 1: High Confidence Claim

**Claim**: "Site.build() supports incremental mode via `incremental` parameter"

**Scoring**:
- **Evidence**: 40/40 (direct code: `bengal/core/site.py:145` with signature)
- **Consistency**: 30/30 (code has param, tests verify behavior, config not needed)
- **Recency**: 15/15 (modified today)
- **Tests**: 15/15 (`test_incremental_build_only_rebuilds_changed_pages` passes)
- **Total**: **100/100** 🟢

**Interpretation**: HIGH confidence, ship it.

---

### Example 2: Moderate Confidence Claim

**Claim**: "Cache invalidation uses file modification timestamps"

**Scoring**:
- **Evidence**: 30/40 (code reference but no excerpt: `bengal/cache/build_cache.py:200`)
- **Consistency**: 20/30 (code verified, tests indirect, config N/A)
- **Recency**: 10/15 (modified 3 months ago)
- **Tests**: 5/15 (only integration tests cover this indirectly)
- **Total**: **65/100** 🟠

**Interpretation**: LOW confidence, needs unit tests and fresher evidence.

**Action**: Run `::improve` to add unit tests and verify logic.

---

### Example 3: Low Confidence Claim

**Claim**: "Rendering pipeline caches compiled Jinja templates"

**Scoring**:
- **Evidence**: 10/40 (inferred from performance, no direct code reference)
- **Consistency**: 10/30 (code not checked, no tests)
- **Recency**: 0/15 (unknown)
- **Tests**: 0/15 (no tests found)
- **Total**: **20/100** 🔴

**Interpretation**: UNCERTAIN, do not ship.

**Action**: Run `::research` to find actual implementation, then re-score.

---

## Usage in Rules

### In Research
- Compute confidence per claim
- Flag low-confidence claims for additional research

### In RFC
- Compute overall RFC confidence (weighted average of claim confidences)
- Gate: RFC requires ≥85% to proceed to planning

### In Validation
- Compute confidence for each validated claim
- Aggregate to overall validation confidence
- Gate: Core changes require ≥90%, other changes ≥85%

### In Reflexion
- Track confidence improvement across iterations
- Stop if improvement < 5% between iterations

---

## Weighted Aggregation

When aggregating multiple claims:

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

This ensures HIGH criticality claims have more impact on overall confidence.

---

## Prompting Techniques

- **Explicit Scoring**: Show formula and component scores
- **Transparency**: Always explain why a score was assigned
- **Self-Critique**: If score is low, analyze why and suggest improvements

---

## Integration

Used by:
- **Research**: Score each claim
- **RFC**: Validate critical claims
- **Validate**: Primary scoring mechanism
- **Improve**: Track improvements
- **All Rules**: Reference thresholds for quality gates
