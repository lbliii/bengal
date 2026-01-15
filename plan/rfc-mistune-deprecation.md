# RFC: Deprecate Mistune Parser and Directive Layer

**Status**: Draft  
**Created**: 2026-01-13  
**Author**: Auto-generated from codebase audit  
**Tracking**: `plan/rfc-mistune-deprecation.md`

---

## Executive Summary

Bengal maintains two parallel directive implementations: the original Mistune-based layer (`bengal/directives/`) and the newer Patitas-based layer (`bengal/rendering/parsers/patitas/`). With Patitas now production-ready and the default parser, the Mistune layer represents ~17,000 LOC of technical debt with significant duplication. This RFC proposes a phased deprecation of Mistune to eliminate ~15,000 LOC and simplify the codebase.

---

## Problem Statement

### Current State

Bengal currently ships with three markdown parsers:

| Parser | Status | LOC | Thread-Safe | Free-Threading Ready |
|--------|--------|-----|-------------|---------------------|
| **PatitasParser** | Default | 14,206 | ✅ Yes | ✅ Yes |
| MistuneParser | Legacy | 1,537 + 15,264* | ❌ No | ❌ No |
| PythonMarkdownParser | Fallback | ~200 | ❌ No | ❌ No |

*Mistune parser (1,537) + directive layer (15,264) = 16,801 LOC

### The Duplication Problem

Every directive is implemented **twice**:

| Mistune Location | Patitas Location | LOC (Mistune) | LOC (Patitas) |
|------------------|------------------|---------------|---------------|
| `directives/embed.py` | `parsers/patitas/directives/builtins/embed.py` | 1,201 | 1,030 |
| `directives/video.py` | `parsers/patitas/directives/builtins/video.py` | 919 | 765 |
| `directives/navigation.py` | `parsers/patitas/directives/builtins/navigation.py` | 517 | 583 |
| `directives/steps.py` | `parsers/patitas/directives/builtins/steps.py` | 458 | 508 |
| `directives/tabs.py` | `parsers/patitas/directives/builtins/tabs.py` | 520 | ~450 |
| `directives/cards.py` | `parsers/patitas/directives/builtins/cards.py` | 257 | 569 |
| ... (40+ directives) | ... | ... | ... |

**Total duplicated directive code**: ~12,000 LOC

### Why This Matters

1. **Maintenance burden**: Every directive change requires updating two implementations
2. **Divergence risk**: Implementations can drift, causing inconsistent behavior
3. **Testing overhead**: Two test suites for equivalent functionality
4. **Dependency cost**: Mistune remains a required dependency despite being legacy
5. **Future-proofing**: Mistune is not designed for Python 3.14+ free-threading

---

## Current Usage Analysis

### Who Uses What

```bash
# Parser references in codebase
grep -r "MistuneParser" bengal --include="*.py" | wc -l  # 20 references
grep -r "PatitasParser" bengal --include="*.py" | wc -l  # 22 references
```

### Mistune Import Locations

| File | Purpose | Migration Effort |
|------|---------|-----------------|
| `rendering/parsers/__init__.py` | Factory function | ✅ Update factory |
| `rendering/pipeline/core.py` | Parser dispatch | ✅ Remove branch |
| `directives/factory.py` | Plugin creation | ❌ Remove entirely |
| `directives/fenced.py` | FencedDirective wrapper | ❌ Remove entirely |
| `directives/list_table.py` | Inline markdown | 🔄 Use Patitas |
| `directives/steps.py` | Inline parsing fallback | 🔄 Use Patitas |
| `directives/__init__.py` | Docstring examples | ✅ Update docs |
| `directives/types.py` | Protocol definitions | 🔄 Keep or migrate |

### External Configuration

Users can select parser via `bengal.yaml`:

```yaml
markdown:
  parser: patitas   # Default since Bengal 2.x
  # parser: mistune  # Legacy, will be deprecated
```

---

## Proposed Solution

### Phase 1: Soft Deprecation (Bengal 2.x)

**Duration**: Current release cycle  
**Breaking Changes**: None

1. **Add deprecation warnings** (already partially in place):
   ```python
   # Set BENGAL_PARSER_DEPRECATION_WARNINGS=1 to see
   warnings.warn(
       "MistuneParser will be deprecated in Bengal 3.0. "
       "Consider switching to PatitasParser.",
       DeprecationWarning,
   )
   ```

2. **Update documentation**:
   - Mark Mistune as "Legacy" in all docs
   - Add migration guide for users explicitly using Mistune
   - Update `bengal.yaml` schema with deprecation note

3. **Freeze Mistune layer**:
   - No new features in `bengal/directives/`
   - Security fixes only
   - All new directives implemented only in Patitas

### Phase 2: Hard Deprecation (Bengal 3.0)

**Duration**: 1 release cycle  
**Breaking Changes**: Config change required for Mistune users

1. **Remove Mistune from default path**:
   ```python
   def create_markdown_parser(engine: str | None = None) -> BaseMarkdownParser:
       engine = (engine or "patitas").lower()
       
       if engine == "mistune":
           raise BengalConfigError(
               "MistuneParser has been removed in Bengal 3.0. "
               "Use PatitasParser (default) instead.",
               code=ErrorCode.C003,
           )
   ```

2. **Move Mistune to optional extra**:
   ```toml
   # pyproject.toml
   [project.optional-dependencies]
   legacy = ["mistune>=3.0.0"]  # For migration period only
   ```

3. **Keep Mistune code but mark as deprecated**:
   - Add `_deprecated` prefix to module
   - Emit loud warnings on import
   - Document removal timeline

### Phase 3: Removal (Bengal 3.1)

**Duration**: 1 release cycle  
**Breaking Changes**: Mistune support removed

1. **Delete Mistune parser**:
   - Remove `bengal/rendering/parsers/mistune/` (1,537 LOC)
   
2. **Delete Mistune directive layer**:
   - Remove `bengal/directives/` entirely (~15,264 LOC)
   - Keep only shared utilities that Patitas uses

3. **Remove Mistune dependency**:
   ```diff
   # pyproject.toml
   dependencies = [
   -    "mistune>=3.0.0",
       "patitas>=0.2.0",
       ...
   ]
   ```

4. **Simplify factory**:
   ```python
   def create_markdown_parser(engine: str | None = None) -> BaseMarkdownParser:
       engine = (engine or "patitas").lower()
       
       if engine == "patitas":
           return PatitasParser()
       elif engine in ("python-markdown", "markdown"):
           return PythonMarkdownParser()
       else:
           raise BengalConfigError(f"Unsupported parser: {engine}")
   ```

---

## Files to Remove

### Phase 3 Deletion List

```
bengal/rendering/parsers/mistune/           # 1,537 LOC
├── __init__.py         (666 lines)
├── highlighting.py     (448 lines)
├── toc.py              (245 lines)
├── ast.py              (137 lines)
└── patterns.py         (41 lines)

bengal/directives/                          # 15,264 LOC
├── __init__.py         (254 lines)
├── embed.py            (1,201 lines)  # Duplicated in patitas
├── video.py            (919 lines)    # Duplicated in patitas
├── code_tabs.py        (814 lines)    # Duplicated in patitas
├── validator.py        (648 lines)    # Move to shared
├── base.py             (569 lines)    # Not needed
├── tabs.py             (520 lines)    # Duplicated in patitas
├── navigation.py       (517 lines)    # Duplicated in patitas
├── figure.py           (476 lines)    # Duplicated in patitas
├── glossary.py         (473 lines)    # Duplicated in patitas
├── steps.py            (458 lines)    # Duplicated in patitas
├── data_table.py       (437 lines)    # Duplicated in patitas
├── literalinclude.py   (433 lines)    # Duplicated in patitas
├── contracts.py        (412 lines)    # Keep for shared validation
├── options.py          (410 lines)    # Already duplicated in patitas
├── types.py            (405 lines)    # Review for shared protocols
├── versioning.py       (404 lines)    # Duplicated in patitas
├── _icons.py           (389 lines)    # Keep for shared icons
├── include.py          (388 lines)    # Duplicated in patitas
├── factory.py          (334 lines)    # Remove
├── ... (remaining files)
└── Total: 47 files
```

### Files to Keep/Migrate

| File | Action | Reason |
|------|--------|--------|
| `directives/contracts.py` | Migrate to shared | Validation patterns used by Patitas |
| `directives/_icons.py` | Migrate to `themes/` or `utils/` | Icon definitions shared across themes |
| `directives/types.py` | Review | Some protocols may be useful |

---

## Migration Guide

### For Users

**If using default config** (no changes needed):
```yaml
# bengal.yaml - no parser specified = patitas (default)
```

**If explicitly using Mistune**:
```yaml
# Before (Bengal 2.x)
markdown:
  parser: mistune

# After (Bengal 3.0+)
markdown:
  parser: patitas  # Or remove line entirely
```

### For Extension Authors

**If extending BengalDirective (Mistune)**:
```python
# Before
from bengal.directives.base import BengalDirective

class MyDirective(BengalDirective):
    ...
```

**Migrate to Patitas DirectiveHandler**:
```python
# After
from bengal.parsing.backends.patitas.directives import DirectiveHandler

class MyDirective(DirectiveHandler):
    ...
```

See: `bengal/rendering/parsers/patitas/directives/protocol.py` for the interface.

---

## Impact Analysis

### LOC Reduction

| Component | Current LOC | After Removal | Reduction |
|-----------|-------------|---------------|-----------|
| `rendering/parsers/mistune/` | 1,537 | 0 | -1,537 |
| `directives/` (Mistune layer) | 15,264 | ~1,200* | -14,064 |
| **Total** | 16,801 | ~1,200 | **-15,601** |

*Keeping shared utilities like `contracts.py`, `_icons.py`

### Dependency Reduction

```diff
# pyproject.toml dependencies
- "mistune>=3.0.0",
```

- Removes 1 direct dependency
- Reduces install size
- Eliminates potential Mistune security advisories

### Test Suite Impact

- Remove Mistune-specific parser tests
- Remove duplicate directive tests (Mistune variants)
- Estimated: -3,000 LOC in tests

### Performance Impact

- No runtime performance change (Patitas already default)
- Faster package install (smaller wheel)
- Reduced import time (fewer modules)

---

## Risks and Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Users on Mistune can't upgrade | Low | Medium | 2-release deprecation cycle |
| Extension authors need migration | Low | High | Provide migration guide and examples |
| Mistune had features Patitas lacks | Very Low | High | Audit feature parity before Phase 2 |
| Breaking existing sites | Low | High | Clear error messages pointing to fix |

### Feature Parity Checklist

Before Phase 2, verify Patitas supports all Mistune features:

- [ ] Variable substitution (`{{ var }}`)
- [ ] Cross-references (`{ref}`, `{doc}`)
- [ ] TOC extraction
- [ ] AST output mode
- [ ] All 40+ directives
- [ ] Syntax highlighting (Rosettes backend)
- [ ] Footnotes
- [ ] Definition lists
- [ ] Task lists

---

## Timeline

| Phase | Version | Target Date | Actions |
|-------|---------|-------------|---------|
| 1: Soft Deprecation | 2.x | Current | Warnings, docs, freeze |
| 2: Hard Deprecation | 3.0 | Q2 2026 | Remove from default path |
| 3: Removal | 3.1 | Q3 2026 | Delete code, remove dependency |

---

## Success Criteria

1. **Phase 1 Complete**:
   - [ ] Deprecation warnings in place
   - [ ] Documentation updated
   - [ ] No new features in Mistune layer

2. **Phase 2 Complete**:
   - [ ] Mistune moved to optional dependency
   - [ ] Clear error messages for Mistune users
   - [ ] Migration guide published

3. **Phase 3 Complete**:
   - [ ] 15,000+ LOC removed
   - [ ] Mistune dependency removed
   - [ ] All tests pass
   - [ ] No regression in supported features

---

## Alternatives Considered

### 1. Keep Both Parsers Indefinitely

**Rejected**: Ongoing maintenance burden, duplication, and divergence risk outweigh flexibility benefits.

### 2. Extract Shared Directive Core

**Considered but Deferred**: Could create `bengal/directives/shared/` with validation/rendering logic used by both Mistune and Patitas. However, this adds complexity and delays removal. Better to complete migration to Patitas.

### 3. Immediate Removal (No Deprecation)

**Rejected**: Would break users who explicitly configured Mistune. Deprecation cycle is standard practice.

---

## References

- [Patitas RFC](plan/drafted/rfc-patitas-markdown-parser.md)
- [Patitas Directive Migration](plan/drafted/rfc-patitas-bengal-directive-migration.md)
- [Codebase Audit: Directive Duplication](#) (this RFC's motivation)
- [Python 3.14 Free-Threading](https://peps.python.org/pep-0703/)

---

## Appendix: Full File List

<details>
<summary>Complete list of files to remove in Phase 3</summary>

```
bengal/rendering/parsers/mistune/__init__.py
bengal/rendering/parsers/mistune/ast.py
bengal/rendering/parsers/mistune/highlighting.py
bengal/rendering/parsers/mistune/patterns.py
bengal/rendering/parsers/mistune/toc.py

bengal/directives/__init__.py
bengal/directives/_icons.py
bengal/directives/admonitions.py
bengal/directives/badge.py
bengal/directives/base.py
bengal/directives/build.py
bengal/directives/button.py
bengal/directives/cards.py
bengal/directives/checklist.py
bengal/directives/code_tabs.py
bengal/directives/container.py
bengal/directives/contracts.py
bengal/directives/data_table.py
bengal/directives/dropdown.py
bengal/directives/embed.py
bengal/directives/example_label.py
bengal/directives/factory.py
bengal/directives/fenced.py
bengal/directives/figure.py
bengal/directives/gallery.py
bengal/directives/glossary.py
bengal/directives/icon.py
bengal/directives/include.py
bengal/directives/list_table.py
bengal/directives/literalinclude.py
bengal/directives/marimo.py
bengal/directives/navigation.py
bengal/directives/options.py
bengal/directives/registry.py
bengal/directives/rubric.py
bengal/directives/steps.py
bengal/directives/tabs.py
bengal/directives/target.py
bengal/directives/terminal.py
bengal/directives/tokens.py
bengal/directives/types.py
bengal/directives/validator.py
bengal/directives/versioning.py
bengal/directives/video.py
```

</details>
