---
description: Audit Bengal's type system using deterministic tools (mypy) and AI analysis
alwaysApply: false
globs: ["bengal/**/*.py"]
---

# Type System Audit

Validates Bengal's type system using deterministic mypy checks and AI-powered analysis of `Any` usage.

**Shortcut**: `::types`

**Works with**: `modules/types-as-contracts`, `modules/evidence-handling`

---

## Overview

This audit combines:
1. **Deterministic checks** - mypy output (reproducible, objective)
2. **AI analysis** - Pattern detection, `Any` classification (heuristic)

**Key principle**: Types are contracts. `Any` at boundaries violates this principle.

---

## Co-located Scripts

This rule includes helper scripts for validation:

```bash
# Run full type audit
python new-rules/validation/type-audit/scripts/audit_types.py bengal/

# Check specific module
python new-rules/validation/type-audit/scripts/audit_types.py bengal/core/

# Output: JSON report with mypy errors and Any locations
```

---

## Procedure

### Step 1: Run mypy (Deterministic)

```bash
mypy bengal/ --show-error-codes --no-error-summary
```

**Expected output**: Zero errors (Bengal uses strict mypy)

**If errors found**:
- Report each error with file:line
- Categorize by error code
- Prioritize: `[arg-type]`, `[return-value]`, `[assignment]`

### Step 2: Find `Any` Usage

```bash
grep -rn ": Any" bengal/ --include="*.py" | grep -v "TYPE_CHECKING"
grep -rn "-> Any" bengal/ --include="*.py"
```

**Classify each `Any`**:

| Classification | Acceptable | Example |
|----------------|------------|---------|
| Escape hatch | ✅ Yes | `extra: dict[str, Any]` for user data |
| External library | ✅ Yes | Untyped third-party returns |
| Circular import workaround | ⚠️ Fix | Use `TYPE_CHECKING` instead |
| Lazy typing | ❌ No | Should be properly typed |

### Step 3: Check Type Patterns

**Verify Bengal patterns are followed**:

- [ ] **Frozen dataclasses for contracts**
  ```python
  @dataclass(frozen=True)
  class PageCore:
      ...
  ```

- [ ] **Forward refs with TYPE_CHECKING**
  ```python
  if TYPE_CHECKING:
      from bengal.core.site import Site
  ```

- [ ] **TypedDict for known structures**
  ```python
  class KnownFrontmatter(TypedDict, total=False):
      title: str
      date: datetime | None
  ```

- [ ] **Modern union syntax**
  ```python
  # ✅ str | None
  # ❌ Optional[str]
  ```

### Step 4: Calculate Confidence

```yaml
confidence_score:
  mypy_clean: 40          # 40 if zero errors, 0 otherwise
  any_acceptable: 30      # Proportional to acceptable Any usage
  patterns_followed: 15   # Modern syntax, frozen dataclasses
  tests_typed: 15         # Test functions have type hints

thresholds:
  90-100%: Type system is solid 🟢
  70-89%: Some issues to address 🟡
  50-69%: Significant gaps 🟠
  < 50%: Major type safety issues 🔴
```

---

## Output Format

```markdown
## 🔍 Type Audit: [Module/Path]

### 🤖 Deterministic Checks

**mypy**: [✅ Pass / ❌ N errors]

| File | Line | Error | Code |
|------|------|-------|------|
| `site.py` | 45 | Missing return type | `[no-untyped-def]` |

### `Any` Usage Analysis

**Total `Any` occurrences**: [N]

| Location | Classification | Action |
|----------|---------------|--------|
| `page.py:145` | Escape hatch | ✅ Acceptable |
| `site.py:89` | Circular import | ⚠️ Fix with TYPE_CHECKING |
| `utils.py:23` | Lazy typing | ❌ Must type properly |

### Pattern Compliance

- [✅/❌] Frozen dataclasses for contracts
- [✅/❌] TYPE_CHECKING for forward refs
- [✅/❌] TypedDict for known structures
- [✅/❌] Modern union syntax (str | None)

### Confidence

**Overall**: [N]% [🟢/🟡/🟠/🔴]

| Component | Score | Max |
|-----------|-------|-----|
| mypy clean | [N] | 40 |
| Any acceptable | [N] | 30 |
| Patterns followed | [N] | 15 |
| Tests typed | [N] | 15 |

### 📋 Action Items

**Critical** (must fix):
- [ ] [Fix unacceptable Any usage]

**Recommended**:
- [ ] [Convert Optional to | None]
- [ ] [Add TYPE_CHECKING for circular imports]
```

---

## Quick Fixes

### Circular Import → TYPE_CHECKING

```python
# Before (bad)
from bengal.core.site import Site  # Circular!

# After (good)
from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from bengal.core.site import Site
```

### dict[str, Any] → TypedDict

```python
# Before (loses type safety)
metadata: dict[str, Any]

# After (typed access)
class PageMetadata(TypedDict, total=False):
    title: str
    date: datetime | None
    tags: list[str]
```

### Optional[X] → X | None

```python
# Before (legacy)
from typing import Optional
def get_page(id: str) -> Optional[Page]:

# After (modern)
def get_page(id: str) -> Page | None:
```

---

## Integration

**Run before**:
- Committing changes to `bengal/core/`
- Finalizing RFCs about type changes
- Pre-release validation

**Triggers**:
- `::types` command
- Part of `::validate` for core modules
- Part of `::workflow-ship`

---

## Related

- [RFC: Type System Hardening](plan/ready/rfc-type-system-hardening.md)
- [TYPE_CHECKING_GUIDE.md](TYPE_CHECKING_GUIDE.md)
- `modules/types-as-contracts` - Philosophy
- `pyproject.toml` - mypy configuration
