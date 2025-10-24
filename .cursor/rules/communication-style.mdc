---
description: Consistent output formatting standards and communication guidelines for all Bengal rules
globs: ["**/*"]
alwaysApply: false
---

# Bengal Communication Style

**Purpose**: Consistent, scannable, professional output formatting for all rules.

Adapted from the documentation framework's communication style, tailored for Bengal's software development context.

---

## Overview

Defines universal output structure, visual indicators, formatting principles, and tone guidelines for all Bengal rule outputs.

---

## Universal Output Structure

All rule outputs follow this structure:

```markdown
## [Icon] [Response Title/Summary]

### Executive Summary (2-3 sentences)
- What was done
- Key finding or outcome
- Next recommended action

### Main Content
[Structured content based on rule type]

### Evidence Trail (for validation rules)
[Structured findings with sources]

### Action Items
[Clear next steps and recommendations]
```

---

## Visual Indicators

### Status Icons

```yaml
status:
  verified: "✅"
  warning: "⚠️"
  error: "❌"
  info: "ℹ️"

confidence:
  high: "🟢"        # 90-100%
  moderate: "🟡"    # 70-89%
  low: "🟠"         # 50-69%
  uncertain: "🔴"   # < 50%

priority:
  critical: "🔴"
  important: "🟡"
  optional: "🔵"

section:
  research: "📚"
  rfc: "📄"
  plan: "📋"
  implementation: "⚙️"
  validation: "🔍"
  retrospective: "📝"
  improvement: "🔄"
  help: "💡"
  analysis: "🎯"
  workflow: "🔗"
```

---

## Formatting Principles

### 1. Start with Most Important Information

Put conclusions first, details later.

**Good**:
```markdown
## ✅ Validation Complete: Incremental Build

### Executive Summary
Validated 18 claims across core and orchestration. All HIGH criticality claims verified (95% confidence). Ready to merge.
```

**Bad**:
```markdown
I started by reading the files. First I checked site.py. Then I looked at the tests. After reviewing everything, I found that the implementation is good.
```

### 2. Use Code References with `file:line` Format

Always cite evidence with specific locations:

**Good**: `bengal/core/site.py:145-150`
**Bad**: "the Site class" or "in the core module"

### 3. Group by Subsystem, Not by Rule Step

Organize content by Bengal subsystems (Core, Orchestration, Rendering, etc.) rather than by process steps.

### 4. Use Tables for Structured Comparisons

When comparing options, risks, or metrics:

```markdown
| Option | Complexity | Performance | Testability |
|--------|-----------|-------------|-------------|
| A: Timestamp-based | Simple | Fast | Easy |
| B: Hash-based | Moderate | Slower | Moderate |
| **C: Hybrid** | **Moderate** | **Fast** | **Easy** |
```

### 5. Provide Executable Commands

For actions, show actual commands:

```bash
git add -A && git commit -m "core: add incremental build state tracking"
pytest tests/unit/test_site.py
```

### 6. End with Clear Next Steps

Always finish with actionable recommendations:

```markdown
### 📋 Next Steps

**Immediate**:
- [ ] Run `::validate` to verify changes
- [ ] Merge feature branch to main

**Follow-up**:
- [ ] Monitor performance in production
- [ ] Add benchmarks for incremental build
```

---

## Tone and Voice (PACE)

- **Professional**: Competent and reliable, not casual
- **Active**: Active voice, present tense, direct language
- **Conversational**: Clear and accessible, not academic
- **Engaging**: Scannable and purposeful, not dry

**Good**: "The incremental build reduces build time by 80% for small changes."

**Bad (too casual)**: "Incremental build is super fast! 🚀 You'll love it lol"

**Bad (too academic)**: "Upon conducting a comprehensive evaluation of the temporal performance characteristics, the proposed incremental methodology demonstrates a reduction in compilation duration..."

---

## Accessibility

- Use "refer to" instead of "see" (better for screen readers)
- Avoid directional language: use "previous section" not "above"
- Provide text descriptions for diagrams (if applicable)
- Use descriptive link text: "refer to the Site API docs" not "click here"

---

## File References in Output

When citing code, use this format:

````markdown
**Evidence**: `bengal/core/site.py:145-150`
```python
def build(self, incremental: bool = False):
    """Build the site with optional incremental mode."""
    if incremental:
        self.render_changed_pages()
```
````

---

## Error and Warning Messages

### Error Format

```markdown
❌ **[Error Type]**: [Brief description]

**Location**: [where it occurred]
**Cause**: [why it happened]
**Fix**: [how to resolve]

**Example**:
```python
# Incorrect
site.build(incremental="yes")  # TypeError: expected bool, got str
```

**Corrected**:
```python
# Correct
site.build(incremental=True)
```
```

### Warning Format

```markdown
⚠️ **Warning**: [Issue description]

**Severity**: [Low/Medium/High]
**Recommendation**: [what to do]
```

---

## Integration Across All Rules

Every Bengal rule output should:

1. ✅ Start with executive summary (2-3 sentences)
2. ✅ Use consistent visual indicators (✅ ⚠️ ❌ 🟢 🟡 🟠 🔴)
3. ✅ Cite evidence with `file:line` format
4. ✅ Group content by subsystem when applicable
5. ✅ End with clear action items
6. ✅ Apply PACE tone principles
7. ✅ Use code blocks for technical content
8. ✅ Provide confidence/status indicators

---

## Rule-Specific Templates

### For Validation Rules

```markdown
## 🔍 Validation Results

### Summary
- **Claims Analyzed**: [N]
- **Verified**: [N] ✅
- **Warnings**: [N] ⚠️
- **Unverifiable**: [N] ❌
- **Confidence**: [N]% 🟢

### Findings

#### ✅ Verified Claims ([N])
Brief summary, full details in Evidence section

#### ⚠️ Requires Clarification ([N])
1. **Claim**: [description]
   - **Issue**: [what's wrong]
   - **Evidence**: `file:line`
   - **Recommendation**: [how to fix]

### 📋 Action Items
[Prioritized list]
```

### For Creation Rules (RFC, Plan)

```markdown
## 📄 [Artifact Type] Complete

### Overview
[2-3 sentence summary]

### [Artifact] Details
- **File**: `plan/active/[name].md`
- **Confidence**: [N]% [🟢/🟡/🟠/🔴]
- **Status**: [status]

### Key Sections
1. ✅ [Section 1]
2. ✅ [Section 2]
3. ⚠️ [Issues flagged]

### 📋 Next Steps
[Actionable items]
```

### For Implementation Rules

```markdown
## ⚙️ Implementation: [Task]

### Changes Made

#### Code Changes
- **File**: [path]
  - [Change description]
  - Lines changed: [N]

#### Test Changes
- **File**: [path]
  - [Test description]

### Validation
- ✅ Linter passed
- ✅ Tests pass ([N]/[N])

### Commit
```bash
[commit command]
```

### 📋 Next Steps
[Next actions]
```

---

## Example Complete Output

```markdown
## 🔍 Validation Complete: Cache Optimization

### Executive Summary
Validated 22 claims across cache and orchestration subsystems. Found 20 verified (91% confidence), 2 require unit tests. Core changes meet 90% gate. Ready to proceed with minor improvements.

### Summary
- **Claims Validated**: 22
- **High Criticality**: 8
- **Medium Criticality**: 10
- **Low Criticality**: 4
- **Overall Confidence**: 91% 🟢

---

### ✅ Verified Claims (20)

#### Claim 1: Build cache tracks file modification times
**Criticality**: HIGH
**Confidence**: 95% 🟢

**Evidence**:
- ✅ **Path A (Source)**: `bengal/cache/build_cache.py:145-150`
  ```python
  def is_stale(self, path: Path) -> bool:
      cached_mtime = self._mtimes.get(path)
      return cached_mtime != path.stat().st_mtime
  ```
- ✅ **Path B (Tests)**: `tests/unit/test_build_cache.py:89`
  - `test_is_stale_detects_modified_files`
- ✅ **Path C (Config)**: Default behavior, no config needed

**Scoring**: Evidence 40/40 + Consistency 30/30 + Recency 15/15 + Tests 15/15 = 100/100

---

### ⚠️ Requires Improvement (2)

#### Issue 1: Cache invalidation edge case
**Criticality**: MEDIUM
**Confidence**: 75% 🟡

**Problem**: No unit test for cache invalidation when dependencies change

**Recommendation**: Add `test_invalidate_with_dependencies` to `tests/unit/test_build_cache.py`

---

### 📊 Confidence Breakdown

| Category | Claims | Avg Confidence |
|----------|--------|----------------|
| High Criticality | 8 | 94% |
| Medium Criticality | 10 | 89% |
| Low Criticality | 4 | 85% |
| **Overall** | **22** | **91%** 🟢 |

---

### ✅ Validation Gates

- ✅ **RFC Gate**: Confidence ≥ 85% → PASS (91%)
- ✅ **Core Implementation Gate**: Confidence ≥ 90% → PASS (91%)

**Overall Status**: PASS (conditional on adding 2 unit tests)

---

### 📋 Action Items

**Recommended (before merge)**:
- [ ] Add `test_invalidate_with_dependencies` (Issue 1)
- [ ] Add `test_cache_persistence_across_builds` (Issue 2)

**Optional (future work)**:
- [ ] Add performance benchmarks for cache hit rates
- [ ] Document cache architecture in `architecture/cache.md`

---

**Next Step**: Run `::improve` to add tests, or proceed to `::retro` if tests not critical.
```

---

## Quality Checklist

Before finalizing any output:

- [ ] Executive summary present (2-3 sentences)
- [ ] Visual indicators used consistently
- [ ] Code references include `file:line` format
- [ ] Content grouped logically (by subsystem when applicable)
- [ ] Clear action items at end
- [ ] PACE tone applied
- [ ] Code blocks formatted correctly
- [ ] Confidence/status indicators shown
- [ ] No invented facts or unsupported claims
