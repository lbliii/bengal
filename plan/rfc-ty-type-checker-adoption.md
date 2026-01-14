# RFC: Adopt ty Type Checker from Astral

**Status**: Implemented  
**Created**: 2026-01-14  
**Priority**: Medium  
**Effort**: Low (~45 minutes)  
**Tracking**: `plan/rfc-ty-type-checker-adoption.md`

---

## Executive Summary

Bengal already uses Astral tools (Ruff, uv) for linting and dependency management. Adopting **ty** — Astral's Rust-based type checker — completes the modern Python toolchain with significant performance benefits.

**Key wins**:
1. **10-100x faster** type checking than mypy (Rust implementation)
2. **Unified Astral ecosystem** — consistent tooling, shared config patterns
3. **CI acceleration** — type checking in seconds, not minutes
4. **Better developer experience** — instant feedback during development

**Reference**: [How to Switch to ty From Mypy](https://www.blog.pythonlibrary.org/2026/01/09/how-to-switch-to-ty-from-mypy/) (featured in PyCoder's Weekly #717)

---

## Problem Statement

### Current State

| Tool | Purpose | Status |
|------|---------|--------|
| **Ruff** | Linting, import sorting | ✅ Configured in `pyproject.toml` |
| **mypy** | Type checking | ✅ Configured, but not in CI |
| **uv** | Dependency management | ✅ Used in CI and locally |
| **ty** | Type checking (Astral) | ❌ Not adopted |

### Issues with Current Setup

1. **mypy not in CI** — Type errors can slip into main branch
2. **mypy speed** — Full codebase check takes 30-60 seconds locally
3. **Toolchain fragmentation** — Mixing Astral tools with non-Astral tools
4. **Developer friction** — Slow feedback discourages running type checks

### Why ty?

| Feature | mypy | ty |
|---------|------|-----|
| Language | Python | Rust |
| Cold check speed | ~30-60s | ~1-5s |
| Incremental speed | ~10-20s | ~0.5-2s |
| Memory usage | Higher | Lower |
| Astral ecosystem | ❌ | ✅ |
| Python 3.14 support | ✅ | ✅ |

---

## Proposed Changes

### 1. Add ty to Dev Dependencies

**Location**: `pyproject.toml`

```toml
[dependency-groups]
dev = [
    # ... existing deps ...
    # Linting & Type Checking
    "mypy>=1.11.0",        # Keep for comparison/fallback
    "ty>=0.1.0",           # Primary type checker (Astral, Rust-based)
    "ruff>=0.14.0",
    # ...
]
```

**Rationale**: Keep mypy during transition period for comparison, make ty the primary.

---

### 2. Add ty Configuration

**Location**: `pyproject.toml`

```toml
[tool.ty]
# Match mypy strictness
python-version = "3.14"
strict = true

# Type stubs for dependencies
extra-stubs = [
    "types-pyyaml",
    "types-psutil", 
    "types-pygments",
    "types-python-dateutil",
    "types-markdown",
    "types-jinja2",
]

# Exclude patterns
exclude = [
    "tests/roots/",        # Test fixture sites
    "MagicMock/",          # Generated stubs
    "dist/",
    "build/",
]
```

---

### 3. Add CI Type Checking Workflow

**Location**: `.github/workflows/ty.yml`

```yaml
name: Type Check

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

concurrency:
  group: ty-${{ github.workflow }}-${{ github.ref }}
  cancel-in-progress: true

jobs:
  type-check:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Install uv
        uses: astral-sh/setup-uv@v4
        with:
          python-version: "3.14t"

      - name: Cache uv dependencies
        uses: actions/cache@v4
        with:
          path: ~/.cache/uv
          key: uv-${{ runner.os }}-${{ hashFiles('uv.lock') }}
          restore-keys: |
            uv-${{ runner.os }}-

      - name: Install dependencies
        run: uv sync --group dev

      - name: Run ty type checker
        run: uv run ty check bengal/
```

**Expected CI time**: ~10-30 seconds (vs ~2-5 minutes for mypy on large codebases)

---

### 4. Update Makefile

**Location**: `Makefile`

```makefile
# Add new targets
.PHONY: ty mypy types

# Primary type check (ty - fast)
ty:
	uv run ty check bengal/

# Fallback type check (mypy - for comparison)
mypy:
	uv run mypy bengal/

# Alias for primary
types: ty
```

---

### 5. Enable Ruff ANN Rules (Optional Enhancement)

ty doesn't flag missing type annotations by default. Enable Ruff's ANN rules for coverage:

**Location**: `pyproject.toml`

```toml
[tool.ruff.lint]
select = [
    "E",    # pycodestyle errors
    "W",    # pycodestyle warnings
    "F",    # pyflakes
    "UP",   # pyupgrade
    "B",    # flake8-bugbear
    "SIM",  # flake8-simplify
    "I",    # isort
    "ANN",  # flake8-annotations (NEW)
]

[tool.ruff.lint.per-file-ignores]
"__init__.py" = ["F401"]
"tests/**/*.py" = ["S101", "ANN"]  # Allow missing annotations in tests
```

---

## Implementation Plan

### Phase 1: Install and Configure (15 min)

| Task | Output |
|------|--------|
| Add `ty>=0.1.0` to dev dependencies | Updated `pyproject.toml` |
| Add `[tool.ty]` configuration | Configured strictness and exclusions |
| Run `uv sync --group dev` | ty installed |
| Run `uv run ty check bengal/` | Baseline type errors identified |

### Phase 2: Fix Type Errors (varies)

| Task | Output |
|------|--------|
| Triage ty output vs mypy output | Understand differences |
| Fix critical type errors | Clean ty check |
| Document any ty-specific suppressions | Inline comments or `ty.toml` |

### Phase 3: Add CI (15 min)

| Task | Output |
|------|--------|
| Create `.github/workflows/ty.yml` | PR type checking enabled |
| Add Makefile targets | Local convenience commands |
| Update `CONTRIBUTING.md` | Document `make ty` command |

### Phase 4: Deprecate mypy (future)

| Task | Timeline |
|------|----------|
| Monitor ty stability for 2-4 weeks | Observation |
| Remove mypy from dev deps | When confident |
| Update docs to reference ty | Cleanup |

---

## Expected Outcomes

### Performance Improvement

| Metric | mypy | ty | Improvement |
|--------|------|-----|-------------|
| Cold check (full codebase) | ~45s | ~3s | **15x faster** |
| Incremental check | ~15s | ~1s | **15x faster** |
| CI job time | ~2 min | ~30s | **4x faster** |

*Estimates based on typical Rust vs Python tool benchmarks. Actual results may vary.*

### Developer Experience

| Before | After |
|--------|-------|
| Skip type checking due to speed | Run on every save |
| Type errors found in review | Type errors caught immediately |
| No CI type checking | Every PR type checked |
| Mixed toolchain | Unified Astral ecosystem |

### Toolchain Alignment

```
Before:
  uv (Astral) → Ruff (Astral) → mypy (third-party)
  
After:
  uv (Astral) → Ruff (Astral) → ty (Astral)
  ↑_________________________________________↑
              Unified Ecosystem
```

---

## Risks and Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| ty behavior differs from mypy | Medium | Low | Keep mypy for comparison during transition |
| ty bugs/instability | Low | Medium | Astral has strong track record (Ruff) |
| Missing type stub support | Low | Low | ty supports mypy stubs |
| Team learning curve | Low | Low | Familiar if using Ruff already |

### Free-Threaded Python Compatibility

**Q: Does ty support free-threaded Python 3.14?**

ty may re-enable the GIL when running, but this has **no impact on Bengal** because:

1. **Dev-time only** — ty is not imported at runtime
2. **Separate process** — ty runs in its own subprocess during `uv run ty check`
3. **CI isolation** — Type checking runs in a separate job from free-threaded tests

Bengal's runtime remains fully free-threaded (`PYTHON_GIL=0`). ty's GIL status only affects the type-checking process itself, which is CPU-bound single-threaded work anyway.

```
ty check bengal/     →  Runs in own process (GIL status irrelevant)
bengal build         →  Runs with PYTHON_GIL=0 ✅
```

---

## Compatibility Notes

### ty vs mypy Differences

Based on [migration guide](https://www.blog.pythonlibrary.org/2026/01/09/how-to-switch-to-ty-from-mypy/):

| Aspect | mypy | ty |
|--------|------|-----|
| Config file | `pyproject.toml` or `mypy.ini` | `pyproject.toml` or `ty.toml` |
| Ignore syntax | `# type: ignore[error-code]` | `# ty: ignore[error-code]` |
| Plugin system | Custom plugins supported | Plugin API (may differ) |
| Stub packages | `types-*` packages | Same `types-*` packages |

### Migration Commands

```bash
# Check current mypy errors
uv run mypy bengal/ 2>&1 | wc -l

# Check ty errors
uv run ty check bengal/ 2>&1 | wc -l

# Compare outputs
diff <(uv run mypy bengal/ 2>&1 | sort) <(uv run ty check bengal/ 2>&1 | sort)
```

---

## Files Changed

| File | Change |
|------|--------|
| `pyproject.toml` | Add ty dep, add `[tool.ty]` config |
| `.github/workflows/ty.yml` | New CI workflow |
| `Makefile` | Add `ty`, `mypy`, `types` targets |
| `CONTRIBUTING.md` | Document type checking workflow |

---

## Testing

### Validation Checklist

- [ ] `uv run ty check bengal/` runs without errors
- [ ] CI workflow passes on clean branch
- [ ] Type errors are caught on PRs with intentional errors
- [ ] `make ty` works locally
- [ ] ty and mypy outputs are comparable (no major regressions)

### Comparison Script

```python
#!/usr/bin/env python3
"""Compare ty and mypy outputs for validation."""

import subprocess
import sys

def run_checker(cmd: list[str]) -> set[str]:
    result = subprocess.run(cmd, capture_output=True, text=True)
    # Parse and normalize output
    errors = set()
    for line in result.stdout.splitlines():
        if "error" in line.lower():
            # Normalize path and extract error type
            errors.add(line.split(":")[-1].strip())
    return errors

mypy_errors = run_checker(["uv", "run", "mypy", "bengal/"])
ty_errors = run_checker(["uv", "run", "ty", "check", "bengal/"])

print(f"mypy errors: {len(mypy_errors)}")
print(f"ty errors: {len(ty_errors)}")
print(f"Only in mypy: {mypy_errors - ty_errors}")
print(f"Only in ty: {ty_errors - mypy_errors}")
```

---

## References

- [How to Switch to ty From Mypy](https://www.blog.pythonlibrary.org/2026/01/09/how-to-switch-to-ty-from-mypy/) — Mike Driscoll
- [ty Documentation](https://docs.astral.sh/ty/) — Astral
- [PyCoder's Weekly #717](https://pycoders.com/issues/717) — Where Bengal was featured
- [Ruff Documentation](https://docs.astral.sh/ruff/) — Related Astral tool

---

## Execution Checklist

- [ ] Add `ty>=0.1.0` to `[dependency-groups] dev`
- [ ] Add `[tool.ty]` configuration to `pyproject.toml`
- [ ] Run `uv sync --group dev`
- [ ] Run `uv run ty check bengal/` — fix any errors
- [ ] Create `.github/workflows/ty.yml`
- [ ] Update `Makefile` with ty targets
- [ ] Update `CONTRIBUTING.md` 
- [ ] Push and verify CI passes
- [ ] Monitor for 2-4 weeks before removing mypy
