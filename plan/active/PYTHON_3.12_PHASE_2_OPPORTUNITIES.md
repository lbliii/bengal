# Python 3.12 Phase 2 Optimization Opportunities

**Status**: Ready to Implement  
**Date**: 2025-10-11  
**Prerequisites**: ✅ Phase 1 Complete

---

## Summary

Ruff has identified additional Python 3.12 optimization opportunities. These are all auto-fixable and low-risk.

---

## 1. Remove Unnecessary Quotes from Type Annotations (UP037) 🔥

**What**: With `from __future__ import annotations`, we no longer need quotes around forward references.

**Impact**: ~30 occurrences across multiple files

**Example**:
```python
# Current (with future annotations)
def process(self, site: 'Site') -> None:
    pass

# Better (quotes not needed)
def process(self, site: Site) -> None:
    pass
```

**Files Affected**:
- `bengal/analysis/performance_advisor.py` (4 locations)
- `bengal/core/section.py` (7 locations)
- `bengal/core/site.py` (2 locations)
- `bengal/health/health_check.py` (2 locations)
- `bengal/orchestration/build.py` (3 locations)
- `bengal/orchestration/render.py` (8+ locations)
- Others...

**Why it matters**:
- ✅ Cleaner code (less visual noise)
- ✅ Consistent with modern Python style
- ✅ With future annotations, quotes are unnecessary

**Auto-fix**:
```bash
ruff check --select UP037 --fix bengal/
```

---

## 2. Modernize isinstance() Calls (UP038) 🔥

**What**: In Python 3.10+, `isinstance()` can use `X | Y` syntax instead of `(X, Y)` tuples.

**Impact**: 3 occurrences in `bengal/autodoc/extractors/python.py`

**Example**:
```python
# Old way
if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
    pass

# Modern way (3.10+)
if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
    pass
```

**Files Affected**:
- `bengal/autodoc/extractors/python.py`:
  - Line 122: `isinstance(node, (ast.Constant, ast.Str))`
  - Line 167: `isinstance(item, (ast.Name, ast.Attribute))`  
  - Line 401: `isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))`

**Why it matters**:
- ✅ Consistent with new union syntax
- ✅ More readable (matches type annotations)
- ✅ Slightly more efficient (no tuple allocation)

**Auto-fix**:
```bash
ruff check --select UP038 --fix bengal/
```

---

## 3. Additional Ruff Rules to Enable 📋

Now that we're on Python 3.12, we can enable additional Ruff rules:

### Enable All Python Upgrade Rules
```toml
[tool.ruff]
select = ["UP"]  # Enable all upgrade rules
```

### Recommended Rules for Python 3.12+:
- `UP001` - `useless-metaclass-type`
- `UP003` - `type-of-primitive`
- `UP004` - `useless-object-inheritance`
- `UP005` - `deprecated-unittest-alias`
- `UP006` - `non-pep585-annotation` (List → list, Dict → dict)
- `UP007` - `non-pep604-annotation` (Optional → X | None)
- `UP008` - `super-call-with-parameters`
- `UP009` - `utf8-encoding-declaration`
- `UP010` - `unnecessary-future-import`
- `UP030` - `format-literals` (%-formatting → f-strings)
- `UP031` - `printf-string-formatting`
- `UP032` - `f-string`
- `UP034` - `extraneous-parentheses`
- `UP037` - `quoted-annotation` ⭐
- `UP038` - `non-pep604-isinstance` ⭐

---

## 4. Dependency Updates 📦

Check if any dependencies have Python 3.12-specific optimizations:

### Core Dependencies
```
click>=8.1.0         → Check for 8.1.7+ (Python 3.12 support)
jinja2>=3.1.0        → Check for 3.1.4+ (Performance improvements)
pillow>=10.0.0       → Already modern
pygments>=2.16.0     → Check for 2.18+ (Better Python 3.12 support)
```

### Dev Dependencies
```
pytest>=7.4.0        → Check for 8.0+ (Better 3.12 compatibility)
black>=23.7.0        → Check for 24.0+ (Native 3.12 syntax support)
mypy>=1.5.0          → Check for 1.11+ (Better 3.12 inference)
ruff>=0.0.287        → Check for 0.6+ (More UP rules)
```

**Action**:
```bash
pip list --outdated
```

---

## 5. Performance Optimizations 🚀

### Use faster dict/set operations (Python 3.12)
Python 3.12 has faster dict/set operations. Look for:

```python
# Potentially slow (multiple lookups)
if key in my_dict:
    value = my_dict[key]

# Better (single lookup)
if (value := my_dict.get(key)) is not None:
    # use value
```

### Use match/case for complex conditionals
Python 3.10+ match/case is optimized in 3.12:

```python
# Before
if isinstance(node, ast.FunctionDef):
    handle_function(node)
elif isinstance(node, ast.ClassDef):
    handle_class(node)
elif isinstance(node, ast.Import):
    handle_import(node)

# After (3.10+, faster in 3.12)
match node:
    case ast.FunctionDef():
        handle_function(node)
    case ast.ClassDef():
        handle_class(node)
    case ast.Import():
        handle_import(node)
```

---

## 6. Clean Up Old Python 3.9/3.10 Workarounds 🧹

Search for and remove:

### Unnecessary future imports
```python
# Can now remove these if we have from __future__ import annotations
from __future__ import annotations
from typing import TYPE_CHECKING  # Still needed
```

### Old-style type comments
```python
# Old
result = []  # type: List[str]

# New
result: list[str] = []
```

---

## Implementation Plan

### Phase 2A: Auto-fixes (5 minutes) ⚡

1. **Run UP037 fix (quoted annotations)**
   ```bash
   ruff check --select UP037 --fix bengal/
   ```

2. **Run UP038 fix (isinstance modernization)**
   ```bash
   ruff check --select UP038 --fix bengal/
   ```

3. **Run all UP rules to find more**
   ```bash
   ruff check --select UP --fix bengal/
   ```

4. **Test**
   ```bash
   pytest tests/ -x
   ```

### Phase 2B: Ruff Configuration (2 minutes)

Update `pyproject.toml`:

```toml
[tool.ruff]
line-length = 100
target-version = "py312"

# Enable Python upgrade rules
select = [
    "E",   # pycodestyle errors
    "W",   # pycodestyle warnings
    "F",   # pyflakes
    "UP",  # pyupgrade - Python modernization
    "B",   # flake8-bugbear
    "SIM", # flake8-simplify
    "I",   # isort
]

# Specific rules we want to enforce
extend-select = [
    "UP037",  # Remove quotes from type annotations
    "UP038",  # Use X | Y in isinstance
]

[tool.ruff.per-file-ignores]
"__init__.py" = ["F401"]  # Allow unused imports in __init__ files
"tests/**/*.py" = ["S101"]  # Allow assert in tests
```

### Phase 2C: Dependency Updates (Optional, 10 minutes)

```bash
# Check for updates
pip list --outdated

# Update specific packages
pip install --upgrade pytest black mypy ruff

# Update requirements.txt
pip freeze > requirements.txt
```

### Phase 2D: Documentation (5 minutes)

Update `CONTRIBUTING.md` to mention Python 3.12 requirements:

```markdown
## Code Style

Bengal uses Python 3.12+ features:
- Use `X | Y` instead of `Union[X, Y]`
- Use `X | None` instead of `Optional[X]`
- Use `type` keyword for type aliases
- Use PEP 695 generic syntax for generic classes
- No quotes needed for type annotations (we use `from __future__ import annotations`)
- Use `isinstance(obj, Type1 | Type2)` instead of `isinstance(obj, (Type1, Type2))`
```

---

## Expected Benefits

### Phase 2A (Auto-fixes)
- ✅ Cleaner code (~30 fewer quote marks)
- ✅ More readable isinstance calls
- ✅ Consistent modern Python style
- ⏱️ **Time**: 5 minutes
- 📊 **Impact**: Medium (code cleanliness)

### Phase 2B (Ruff config)
- ✅ Automated enforcement of modern Python
- ✅ Prevent regression to old style
- ⏱️ **Time**: 2 minutes
- 📊 **Impact**: High (prevents future tech debt)

### Phase 2C (Dependencies)
- ✅ Better Python 3.12 compatibility
- ✅ Performance improvements
- ✅ Bug fixes
- ⏱️ **Time**: 10 minutes
- 📊 **Impact**: Low-Medium (gradual improvements)

---

## Risk Assessment

**Risk**: ⭐ Very Low

All changes are:
- Auto-fixable by Ruff (well-tested)
- Syntactic only (no runtime behavior changes)
- Reversible via git
- Covered by existing tests

**Recommendation**: ✅ Safe to proceed with all phases

---

## Quick Command Summary

```bash
# Phase 2A: Auto-fixes
ruff check --select UP --fix bengal/
pytest tests/ -x

# Phase 2B: Check what else can be upgraded
ruff check --select UP bengal/ | less

# Check dependencies
pip list --outdated

# Run tests
pytest tests/unit/ -q
pytest tests/integration/ -q
```

---

## Next Steps

1. ✅ Review this document
2. ⏭️ Run Phase 2A auto-fixes
3. ⏭️ Update ruff config (Phase 2B)
4. ⏭️ Consider dependency updates (Phase 2C)
5. ⏭️ Update CONTRIBUTING.md (Phase 2D)

**Estimated total time**: 20-30 minutes for all phases
