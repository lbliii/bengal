---
description: Deep validation with 3-path self-consistency and transparent confidence scoring
alwaysApply: false
globs: ["bengal/**/*.py", "tests/**/*.py", "plan/**/*.md"]
---

# Validate

Deep audit with self-consistency and transparent confidence scores.

**Shortcut**: `::validate`

**Works with**: `modules/evidence-handling`, `modules/output-format`

---

## Overview

Validates code, claims, and implementations using:
1. **Deterministic checks** - mypy, linter, tests (reproducible)
2. **3-path validation** - Source + Tests + Config (for HIGH criticality)
3. **Confidence scoring** - Transparent formula with breakdown

---

## Procedure

### Step 1: Identify What to Validate

**Auto-detect from context**:
```yaml
if uncommitted_changes:
  validate: changed files

if rfc_or_plan:
  validate: claims in document

if specific_module:
  validate: that module
```

### Step 2: Run Deterministic Checks

```bash
# Type check
mypy bengal/ --show-error-codes

# Linter
ruff check bengal/

# Tests
pytest tests/unit/ tests/integration/ -v
```

### Step 3: Extract Claims

From code, docs, or changes:
- API contracts (method signatures, return types)
- Behavioral claims (what code does)
- Configuration claims (defaults, options)

### Step 4: Validate Each Claim

**For HIGH criticality** (API, core, user-facing):

```yaml
path_a_source:
  action: Find implementation in source code
  tool: read_file, grep
  output: file:line + excerpt

path_b_tests:
  action: Find tests verifying behavior
  tool: grep for test functions
  output: test name + assertion

path_c_config:
  action: Check if configurable
  tool: search config files
  output: config key + default

agreement:
  3/3: HIGH confidence
  2/3: MODERATE confidence
  1/3 or conflict: LOW confidence
```

**For MEDIUM/LOW criticality**:
- Path A (source code) only
- Simpler verification

### Step 5: Calculate Confidence

```yaml
confidence = (
    evidence_strength +      # 0-40 points
    self_consistency +       # 0-30 points
    recency +                # 0-15 points
    test_coverage            # 0-15 points
)

# Evidence Strength (0-40)
40: Direct code with file:line and excerpt
30: Direct code without excerpt
20: Docstring/comment only
10: Inferred from context
0:  No evidence

# Self-Consistency (0-30)
30: All 3 paths agree
20: 2 paths agree, 1 N/A
10: 1 path only
5:  Partial agreement
0:  Paths conflict

# Recency (0-15)
15: Modified < 30 days
10: Modified < 6 months
5:  Modified < 12 months
0:  Older than 1 year

# Test Coverage (0-15)
15: Comprehensive tests exist
10: Good coverage
5:  Indirect tests only
0:  No tests
```

### Step 6: Check Quality Gates

```yaml
gates:
  rfc: 85%
  plan: 85%
  implementation_core: 90%
  implementation_other: 85%

status:
  PASS: All gates met
  CONDITIONAL: Some gates need review
  FAIL: Critical gates not met
```

---

## Output Format

```markdown
## 🔍 Validation Results: [Topic]

### Executive Summary
[2-3 sentences: what was validated, overall confidence, key findings]

### 🤖 Deterministic Checks

| Check | Status | Details |
|-------|--------|---------|
| mypy | ✅/❌ | [N] errors |
| ruff | ✅/❌ | [N] issues |
| pytest | ✅/❌ | [N]/[N] passed |

---

### ✅ Verified Claims ([N])

#### Claim 1: [Description]
**Criticality**: HIGH
**Confidence**: 95% 🟢

**Evidence**:
- ✅ **Path A (Source)**: `bengal/core/site.py:145-150`
  ```python
  def build(self, incremental: bool = False):
  ```
- ✅ **Path B (Tests)**: `tests/unit/test_site.py:89`
  - `test_incremental_build` verifies behavior
- N/A **Path C (Config)**: API parameter, no config

**Scoring**:
| Component | Score | Max |
|-----------|-------|-----|
| Evidence | 40 | 40 |
| Consistency | 30 | 30 |
| Recency | 15 | 15 |
| Tests | 15 | 15 |
| **Total** | **100** | **100** |

---

### ⚠️ Moderate Confidence ([N])

#### Claim 2: [Description]
**Criticality**: MEDIUM
**Confidence**: 75% 🟡

**Evidence**:
- ✅ **Source**: `bengal/cache/build_cache.py:200`
- ❌ **Tests**: No direct tests found

**Issue**: Missing test coverage
**Recommendation**: Add unit test for this method

---

### 🔴 Issues Found ([N])

#### Issue 1: [Description]
**Criticality**: HIGH
**Confidence**: 45% 🔴

**Problem**: [What's wrong]
**Action Required**: [How to fix]

---

### 📊 Confidence Summary

| Category | Claims | Avg Confidence |
|----------|--------|----------------|
| High Criticality | [N] | [N]% |
| Medium Criticality | [N] | [N]% |
| Low Criticality | [N] | [N]% |
| **Overall** | **[N]** | **[N]%** |

---

### ✅ Quality Gates

| Gate | Required | Actual | Status |
|------|----------|--------|--------|
| Core modules | 90% | [N]% | ✅/❌ |
| Other modules | 85% | [N]% | ✅/❌ |
| RFC/Plan | 85% | [N]% | ✅/❌ |

**Overall Status**: [PASS / CONDITIONAL / FAIL]

---

### 📋 Action Items

**Critical (must fix)**:
- [ ] [Item]

**Recommended**:
- [ ] [Item]

**Optional**:
- [ ] [Item]
```

---

## When to Run

| Scenario | Command |
|----------|---------|
| Before commit | `::validate` |
| After implementation | `::validate` |
| Pre-merge | `::workflow-ship` |
| RFC review | `::validate @plan/rfc-*.md` |
| Core changes | `::validate bengal/core/` |

---

## Integration

Used by:
- `::workflow-ship` - Pre-merge validation
- `::workflow-fix` - Post-implementation check
- `::improve` - Confidence improvement loop

---

## Related

- `modules/evidence-handling` - Reference format
- `validation/type-audit` - Type-specific audit
- `validation/architecture-audit` - Architecture audit
- `commands/improve` - Improve low confidence
