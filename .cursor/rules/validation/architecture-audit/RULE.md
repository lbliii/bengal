---
description: Audit architecture compliance - model/orchestrator split, composition patterns, file organization
alwaysApply: false
globs: ["bengal/**/*.py"]
---

# Architecture Audit

Validates Bengal's architecture patterns: passive models, orchestrator operations, composition over inheritance.

**Shortcut**: `::arch`

**Works with**: `modules/architecture-patterns`, `modules/evidence-handling`

---

## Overview

This audit checks:
1. **Model/Orchestrator split** - No I/O in `bengal/core/`
2. **Composition patterns** - Mixins over inheritance
3. **File organization** - 400-line threshold, package structure
4. **Single responsibility** - Focused classes

---

## Co-located Scripts

```bash
# Run architecture audit
python new-rules/validation/architecture-audit/scripts/audit_arch.py bengal/

# Check specific subsystem
python new-rules/validation/architecture-audit/scripts/audit_arch.py bengal/core/
```

---

## Procedure

### Step 1: Check Model Purity

**Models (`bengal/core/`) must NOT contain**:

```python
# ❌ VIOLATIONS
import logging              # No logging imports
logger = get_logger(...)    # No logger usage
logger.info(...)            # No log calls
open(file, 'w')            # No file writes
Path(...).write_text(...)  # No file operations
requests.get(...)          # No network calls
subprocess.run(...)        # No shell commands
```

**Search commands**:
```bash
# Find logging in core
grep -rn "logger\." bengal/core/
grep -rn "import logging" bengal/core/
grep -rn "get_logger" bengal/core/

# Find I/O in core
grep -rn "\.write\(" bengal/core/
grep -rn "open(" bengal/core/
grep -rn "Path.*write" bengal/core/
```

### Step 2: Check Orchestrator Placement

**All I/O operations should be in**:
- `bengal/orchestration/`
- `bengal/cli/`
- `bengal/server/`

**Verify delegation pattern**:
```python
# ✅ CORRECT - Model delegates to orchestrator
class Site:
    def build(self) -> None:
        return BuildOrchestrator.build(self)
```

### Step 3: Check Inheritance Depth

**Maximum inheritance depth**: 2 levels

```python
# ✅ OK - Composition with mixins
class Page(MetadataMixin, NavigationMixin):
    pass

# ❌ BAD - Deep inheritance
class ArticlePage(BlogPage(ContentPage(BasePage))):
    pass
```

**Detection**:
```bash
# Find class definitions
grep -rn "^class.*(.*):" bengal/ --include="*.py"

# Check for deep chains (manual review needed)
```

### Step 4: Check File Sizes

**Threshold**: 400 lines per file

```bash
# Find large files
find bengal/ -name "*.py" -exec wc -l {} \; | awk '$1 > 400 {print}'
```

**If exceeded**:
- File should be a package (`__init__.py` + modules)
- Or split into focused modules

### Step 5: Check Single Responsibility

**Warning signs**:
- More than 10 public methods
- Imports from >5 different modules
- Multiple unrelated responsibilities

---

## Output Format

```markdown
## 🔍 Architecture Audit: [Path]

### Model Purity (`bengal/core/`)

| Check | Status | Details |
|-------|--------|---------|
| No logging | ✅/❌ | [findings] |
| No file I/O | ✅/❌ | [findings] |
| No network | ✅/❌ | [findings] |
| Delegates to orchestrators | ✅/❌ | [findings] |

**Violations found**: [N]

### Composition Patterns

| Check | Status | Details |
|-------|--------|---------|
| Max inheritance depth ≤2 | ✅/❌ | [findings] |
| Uses mixins | ✅/❌ | [findings] |
| No God objects | ✅/❌ | [findings] |

### File Organization

| File | Lines | Status |
|------|-------|--------|
| `site.py` | 350 | ✅ OK |
| `page/__init__.py` | 180 | ✅ Package |
| `template.py` | 520 | ❌ Too large |

### Single Responsibility

| Class | Methods | Imports | Status |
|-------|---------|---------|--------|
| `Site` | 8 | 4 | ✅ OK |
| `Page` | 12 | 6 | ⚠️ Review |

### Confidence

**Overall**: [N]% [🟢/🟡/🟠/🔴]

### 📋 Action Items

**Critical**:
- [ ] Remove logging from `bengal/core/site.py:45`
- [ ] Split `bengal/rendering/template.py` into package

**Recommended**:
- [ ] Extract mixin from large class
```

---

## Quick Fixes

### Logging in Model → Move to Orchestrator

```python
# Before (in bengal/core/site.py)
class Site:
    def build(self):
        logger.info("Building site")  # ❌ NO!
        self._render()

# After (in bengal/orchestration/build_orchestrator.py)
class BuildOrchestrator:
    @staticmethod
    def build(site: Site) -> None:
        logger.info("Building site")  # ✅ OK here
        site._render()
```

### Large File → Package

```bash
# Before
bengal/core/page.py  # 520 lines

# After
bengal/core/page/
├── __init__.py      # Main class, re-exports
├── core.py          # PageCore
├── metadata.py      # Metadata mixin
├── navigation.py    # Navigation mixin
└── computed.py      # Computed properties
```

### Deep Inheritance → Composition

```python
# Before
class BlogPage(ContentPage):
    pass

class ContentPage(BasePage):
    pass

# After
class Page(ContentMixin, BlogMixin):
    """Composed from focused mixins."""
    pass
```

---

## Related

- `modules/architecture-patterns` - Detailed patterns
- `implementation/core-model` - Guide for modifying core
- `architecture/design-principles.md` - Design documentation
