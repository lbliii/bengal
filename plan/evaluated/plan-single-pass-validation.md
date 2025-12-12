---
status: Draft
parent: rfc-single-pass-ast-html.md
---

## Plan: Single-pass token validation and default-on evaluation

### Summary
Complete validation work for the single-pass token capture feature to enable default-on for `markdown.ast_cache.single_pass_tokens`.

### Prerequisites
- ✅ Phase 0: Config flags and single-pass path (COMPLETE)
- ✅ Phase 1: Deterministic directive IDs (COMPLETE)
- ✅ Unit test exists (`tests/unit/rendering/test_pipeline_single_pass_ast_spike.py`)
- ✅ Benchmark script exists (`scripts/benchmark_single_pass_tokens_directives.py`)

### Tasks

#### 1. Document benchmark results
**Estimate**: 10 min  
**Command**:
```bash
python scripts/benchmark_single_pass_tokens_directives.py
```

**Expected output**:
```
pages=500 mode=no-parallel runs=3 avg_ms_off=X avg_ms_on=Y savings_ms=Z savings_pct=W%
pages=1000 mode=no-parallel runs=3 avg_ms_off=X avg_ms_on=Y savings_ms=Z savings_pct=W%
```

**Acceptance**: Document results in `rfc-single-pass-ast-html.md` under "Benchmark results".

---

#### 2. Create golden output equivalence test
**Estimate**: 30 min  
**Files**:
- Create: `tests/integration/test_single_pass_output_equivalence.py`

**Test design**:
```python
@pytest.mark.bengal(testroot="test-basic")
@pytest.mark.parametrize("single_pass_tokens", [False, True])
def test_output_identical_with_single_pass_tokens(site_factory, single_pass_tokens):
    """Verify HTML output is identical with single_pass_tokens=True vs False."""
    site = site_factory(
        "test-basic",
        confoverrides={"markdown.ast_cache.single_pass_tokens": single_pass_tokens}
    )
    site.build()
    # Compare normalized HTML output
```

**Acceptance**: Test passes showing output equivalence.

---

#### 3. Add directive-heavy golden test
**Estimate**: 30 min  
**Files**:
- Create: `tests/roots/test-directives-heavy/` (if not exists)
- Update: `tests/integration/test_single_pass_output_equivalence.py`

**Content**: Test site with:
- `:::{note}`, `:::{warning}`, `:::{tip}`
- `:::{tab-set}` with multiple tabs
- `:::{code-tabs}`
- `:::{dropdown}`
- Variable substitution (`{{ page.title }}`)

**Acceptance**: Test passes for directive-heavy content.

---

#### 4. Evaluate default-on criteria
**Estimate**: 15 min  

**Decision matrix**:
| Metric | Threshold | Actual | Pass? |
|--------|-----------|--------|-------|
| Benchmark savings | ≥5% | TBD | TBD |
| Output equivalence | 100% | TBD | TBD |
| Unit test pass | Yes | ✅ | ✅ |

**If all pass**: Propose PR to set `single_pass_tokens: true` as default.

---

#### 5. (Optional) Update default config
**Estimate**: 5 min  
**Files**:
- `bengal/config/defaults.py:296`

**Change**:
```python
# Before
"single_pass_tokens": False,

# After
"single_pass_tokens": True,
```

**Acceptance**: All tests pass with new default.

---

### Commits

```bash
# Task 1
git commit -m "docs(plan): document single-pass token benchmark results"

# Task 2
git commit -m "tests: add output equivalence test for single_pass_tokens"

# Task 3
git commit -m "tests: add directive-heavy golden test for single_pass_tokens"

# Task 5 (if approved)
git commit -m "config: enable single_pass_tokens by default; benchmarks show X% improvement"
```

### Success criteria
- [ ] Benchmark results documented (≥5% savings)
- [ ] Golden tests pass for basic and directive-heavy content
- [ ] Decision made on default-on
