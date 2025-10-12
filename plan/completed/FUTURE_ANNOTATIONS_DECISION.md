# Future Annotations Decision

**Date**: 2025-10-11  
**Status**: ✅ Resolved  
**Context**: Python 3.14 deprecates `from __future__ import annotations`

---

## The Issue

Python 3.14 (released Oct 7, 2025) officially deprecated `from __future__ import annotations` ([PEP 649](https://docs.python.org/3/whatsnew/3.14.html#changes-in-annotations-pep-649-and-pep-749)).

- **Deprecation timeline**: Will be removed after Python 3.13 reaches EOL in **2029**
- **Current status**: Works fine, just deprecated with long timeline
- **Impact**: Affects 3 Bengal files that use `TYPE_CHECKING` imports

---

## Our Decision

**Keep `from __future__ import annotations` for now** in files with extensive TYPE_CHECKING usage.

### Rationale:

1. **Long timeline**: 4+ years until removal (2029+)
2. **Cleaner code**: Avoids quoting dozens of forward references
3. **TYPE_CHECKING pattern**: Files use this to avoid circular imports
4. **Pragmatic**: Bengal is Python 3.12+ only, so modern syntax works everywhere else

---

## Files Affected

### ✅ Kept future import (TYPE_CHECKING heavy):
- `bengal/orchestration/render.py` - 20+ forward references
- `bengal/orchestration/streaming.py` - 10+ forward references

### ✅ Removed future import (minimal forward refs):
None currently - we initially tried but reverted.

### ✅ Manually quoted (self-references):
- `bengal/core/section.py` - Uses `'Section'` in type hints (no future import)

---

## Alternative Considered

**Quote all TYPE_CHECKING references manually:**

```python
# Would need to quote every reference:
def __init__(self, site: 'Site'): ...
def process(self, pages: list['Page'], ...) -> None: ...
def _render_sequential(self, pages: list['Page'],
                      tracker: 'DependencyTracker | None',
                      stats: 'BuildStats | None') -> None: ...
```

**Why we didn't**: Too tedious, error-prone, and we have years before it's required.

---

## The Python 3.12+ Strategy

### Best Practices Going Forward:

1. **New code**: Use modern syntax (`X | Y`, `X | None`) without future import when possible
2. **Self-references**: Quote them (`list['Section']`) instead of using future import
3. **TYPE_CHECKING blocks**: OK to use future import for files with many forward refs
4. **Timeline**: Revisit in 2028 before Python 3.13 EOL

### Modern Type Hint Syntax (Python 3.12+):

✅ **Use these**:
```python
def func(x: str | int) -> Page | None:
    items: list[str] = []
    mapping: dict[str, Any] = {}
```

❌ **Avoid these** (old style):
```python
from typing import Union, Optional
def func(x: Union[str, int]) -> Optional[Page]:
    items: List[str] = []
    mapping: Dict[str, Any] = {}
```

---

## Migration Timeline

| Year | Action |
|------|--------|
| 2025 | ✅ Keep future import where needed |
| 2026-2028 | Monitor Python 3.14 adoption |
| 2028 | Plan removal before 3.13 EOL |
| 2029+ | Remove future imports, quote all refs |

---

## Summary

- `from __future__ import annotations` is deprecated but works fine for years
- We use it in 2 files with heavy TYPE_CHECKING usage
- Bengal uses modern Python 3.12 syntax everywhere else
- We'll remove it when necessary (2028+)

**Status**: Pragmatic solution, no action needed until 2028.
