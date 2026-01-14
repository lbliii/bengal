---
description: Consistent output formatting standards for all Bengal rules
alwaysApply: false
---

# Output Format

Standard formatting patterns for consistent, scannable output across all Bengal rules.

**Works with**: `modules/evidence-handling`

---

## Structure

Every major output follows this structure:

```markdown
## [Emoji] [Title]: [Context]

### Executive Summary
[2-3 sentences: what was done, key findings, confidence level]

### [Main Content Sections]
...

### 📋 Action Items (if applicable)
- [ ] [Actionable task]

### Confidence (if applicable)
[Score]% [Emoji] - [Brief reasoning]
```

---

## Emoji Vocabulary

### Status Indicators

| Emoji | Meaning | Usage |
|-------|---------|-------|
| ✅ | Verified/Pass | Confirmed claims, passing checks |
| ⚠️ | Warning/Caution | Needs review, partial match |
| ❌ | Error/Fail | Failed checks, incorrect claims |
| ❓ | Unknown/Uncertain | Cannot verify, needs investigation |

### Confidence Levels

| Emoji | Range | Meaning |
|-------|-------|---------|
| 🟢 | 90-100% | HIGH - Ship it |
| 🟡 | 70-89% | MODERATE - Review recommended |
| 🟠 | 50-69% | LOW - Needs work |
| 🔴 | < 50% | UNCERTAIN - Do not ship |

### Section Types

| Emoji | Section |
|-------|---------|
| 📚 | Research findings |
| 🔍 | Validation results |
| 📋 | Action items |
| 📊 | Statistics/metrics |
| ⚡ | Quick summary |
| 💡 | Recommendations |
| 🎯 | Goals/targets |

---

## Output Templates

### Research Output

```markdown
## 📚 Research: [Topic/Module]

### Executive Summary
[2-3 sentences summarizing findings]

### Evidence Summary
- **Claims Extracted**: [N]
- **High Criticality**: [N]
- **Average Confidence**: [N]%

---

### 🔴 High Criticality Claims

#### Claim 1: [Description]
**Evidence**:
- ✅ **Source**: `file.py:45-50`
- ✅ **Test**: `test_file.py:89`

**Confidence**: 95% 🟢

---

### 📋 Next Steps
- [ ] Use findings for RFC (run `::rfc`)
- [ ] Identify gaps requiring investigation
```

### Validation Output

```markdown
## 🔍 Validation Results: [Topic]

### Executive Summary
[2-3 sentences: what was validated, overall confidence]

### Summary
- **Claims Validated**: [N]
- **Overall Confidence**: [N]% [🟢/🟡/🟠/🔴]

---

### ✅ Verified Claims ([N])

#### [Claim]
**Confidence**: 95% 🟢
**Evidence**: `file.py:45`

---

### ⚠️ Moderate Confidence ([N])

#### [Claim]
**Confidence**: 75% 🟡
**Issue**: [What's uncertain]

---

### 📋 Action Items
- [ ] [Required action]
```

### Implementation Output

```markdown
## ✅ Implementation: [Task]

### Executive Summary
[2-3 sentences: what was implemented, files changed]

### Changes Made

#### Code Changes
- **File**: `bengal/core/site.py`
  - Added `incremental: bool` parameter
  - Lines changed: [N]

#### Test Changes
- **File**: `tests/unit/test_site.py`
  - Added `test_incremental_build`
  - Lines added: [N]

### Validation
- ✅ Linter passed
- ✅ Unit tests pass
- ✅ Type check passes

### Commit
```bash
git add -A && git commit -m "core: add incremental build support"
```

**Status**: ✅ Ready to commit
```

---

## Tables

Use tables for structured comparisons:

```markdown
| Option | Pros | Cons | Recommendation |
|--------|------|------|----------------|
| A | Fast | Complex | ⭐ Recommended |
| B | Simple | Slow | Alternative |
| C | Flexible | Risky | Not recommended |
```

---

## Code Blocks

### With File Reference

````markdown
**Evidence**: `bengal/core/site.py:145-150`

```python
def build(self, incremental: bool = False) -> None:
    """Build the site with optional incremental mode."""
    return BuildOrchestrator.build(self, incremental=incremental)
```
````

### For Commands

````markdown
```bash
git add -A && git commit -m "core: add feature"
```
````

---

## Checklists

Use checklists for actionable items:

```markdown
### 📋 Pre-Commit Checklist
- [ ] Code changes minimal and focused
- [ ] Type hints maintained/improved
- [ ] Tests added/updated
- [ ] Linter passes
```

---

## Confidence Scoring Display

Always show the formula when reporting confidence:

```markdown
### Confidence Breakdown

**Overall**: 92% 🟢

| Component | Score | Max |
|-----------|-------|-----|
| Evidence Strength | 38 | 40 |
| Self-Consistency | 30 | 30 |
| Recency | 12 | 15 |
| Test Coverage | 12 | 15 |
| **Total** | **92** | **100** |
```

---

## Progressive Disclosure

For complex output, use collapsible sections:

```markdown
### Summary
[Key findings here]

<details>
<summary>📊 Detailed Breakdown (click to expand)</summary>

[Detailed content that most users don't need to see]

</details>
```

---

## Horizontal Rules

Use `---` to separate major sections:

```markdown
### Section 1
Content...

---

### Section 2
Content...
```

---

## Formatting Rules

1. **Be concise** - Executive summary first, details later
2. **Use emojis consistently** - Same meaning everywhere
3. **Include evidence** - File:line references for claims
4. **Action-oriented** - End with clear next steps
5. **Scannable** - Headers, bullets, tables over paragraphs

---

## Anti-Patterns

### ❌ Wall of Text

```markdown
The analysis shows that the module has several issues that need attention
including type errors and missing tests. The confidence is moderate because
while the source code was found, there were no tests to verify the behavior
and the documentation was outdated...
```

### ✅ Structured Output

```markdown
### Summary
- **Issues Found**: 3
- **Confidence**: 75% 🟡

### Issues
1. Type errors in `file.py:45`
2. Missing tests for `feature_x`
3. Outdated docs in `README.md`
```

---

## Related

- `modules/evidence-handling` - How to cite evidence
- `commands/research` - Research output format
- `commands/validate` - Validation output format
