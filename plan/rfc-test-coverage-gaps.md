# RFC: Test Coverage Gap Analysis and Remediation

**Status**: Draft  
**Created**: 2025-12-05  
**Author**: AI Assistant  
**Scope**: Test Suite Completeness

---

## Executive Summary

Bengal has excellent test coverage on critical paths (75-100%) with 4,000+ tests. However, a systematic analysis reveals **45+ source files lacking any test coverage**, particularly in utils, config, health validators, and orchestration phases.

**Recommendation**: Add ~25-30 new test files over 3 phases, prioritizing modules that affect build correctness.

---

## 1. Problem Statement

### Current State

Bengal's test suite is comprehensive on the critical build path:
- ✅ 4,000+ tests (3,838 unit + 200+ integration + 116 property-based)
- ✅ Core objects: 75-100% coverage
- ✅ Cache indexes: 77-100% coverage
- ✅ Fast execution (~60-90 seconds)

### Gap Analysis

A file-by-file comparison of `bengal/` against `tests/unit/` reveals:

| Category | Source Files | Test Files | Gap |
|----------|--------------|------------|-----|
| `bengal/utils/` | 35 | 26 | **14 missing** |
| `bengal/config/` | 12 | 9 | **4 missing** |
| `bengal/health/validators/` | 20 | 7 | **11 missing** |
| `bengal/orchestration/` | 19 | 16 | **6 missing** |
| `bengal/postprocess/` | 13 | 6 | **5 missing** |
| `bengal/content_layer/sources/` | 4 | 1 | **3 missing** |
| `bengal/services/` | 1 | 0 | **1 missing** |
| `bengal/cli/commands/` | 30 | 8 | **15+ missing** (intentional) |

**Total**: ~45+ source files with no corresponding tests.

### Risk Assessment

**High Risk** (affects build correctness):
- `services/validation.py` - Validation protocol with no tests
- `utils/build_context.py` - Build state management
- `utils/metadata.py` - Metadata extraction
- `utils/theme_resolution.py` - Theme chain resolution
- `orchestration/build/*.py` - Build phases

**Medium Risk** (affects specific features):
- Config validators and defaults
- Health validators
- Postprocess generators

**Low Risk** (intentionally untested):
- Interactive CLI wizards
- Progress/console output
- Network-dependent sources

---

## 2. Goals

### Must Have
1. Test coverage for all `services/` modules
2. Test coverage for high-risk `utils/` modules
3. Test coverage for `config/` validators and defaults
4. Test coverage for `orchestration/build/` phases

### Should Have
5. Test coverage for health validators
6. Test coverage for postprocess generators
7. Mock-based tests for content layer sources

### Won't Have (By Design)
- Interactive CLI wizard tests (require terminal interaction)
- Rich console output tests (visual QA)
- Font downloader tests (network-dependent, rarely used)

---

## 3. Evidence from Codebase

### Missing Test Files (Verified)

#### Utils (14 files missing)

| File | Lines | Risk | Evidence |
|------|-------|------|----------|
| `build_context.py` | ~100 | 🔴 High | Used in every build - `grep -r "BuildContext" bengal/` shows 15+ usages |
| `metadata.py` | ~80 | 🔴 High | Metadata extraction used by Page |
| `sections.py` | ~120 | 🔴 High | Section utilities used by Section model |
| `theme_resolution.py` | ~200 | 🔴 High | Theme chain resolution - critical for rendering |
| `build_stats.py` | ~150 | 🟡 Medium | Build statistics tracking |
| `build_summary.py` | ~100 | 🟡 Medium | Build summary generation |
| `css_minifier.py` | ~80 | 🟡 Medium | CSS minification |
| `js_bundler.py` | ~120 | 🟡 Medium | JS bundling |
| `file_utils.py` | ~100 | 🟡 Medium | File operations |
| `autodoc.py` | ~80 | 🟡 Medium | Autodoc utilities |
| `live_progress.py` | ~150 | 🟢 Low | Progress bars |
| `progress.py` | ~100 | 🟢 Low | Progress reporting |
| `performance_collector.py` | ~80 | 🟢 Low | Performance metrics |
| `performance_report.py` | ~100 | 🟢 Low | Performance reports |

#### Services (1 file missing)

| File | Lines | Risk | Evidence |
|------|-------|------|----------|
| `validation.py` | 50 | 🔴 High | Protocol for template validation - no tests |

**Source**: `bengal/services/validation.py:30-50`
```python
class TemplateValidationService(Protocol):
    def validate(self, site: Any) -> int:  # returns number of errors
        ...

@dataclass
class DefaultTemplateValidationService:
    """Adapter around bengal.rendering.validator with current TemplateEngine."""
    strict: bool = False

    def validate(self, site: Any) -> int:
        from bengal.rendering.template_engine import TemplateEngine
        from bengal.rendering.validator import validate_templates
        engine = TemplateEngine(site)
        return validate_templates(engine)
```

#### Config (4 files missing)

| File | Lines | Risk | Evidence |
|------|-------|------|----------|
| `defaults.py` | ~80 | 🟡 Medium | Default configuration values |
| `deprecation.py` | ~100 | 🟡 Medium | Deprecation warnings system |
| `validators.py` | ~150 | 🟡 Medium | Config validation logic |
| `env_overrides.py` | ~80 | 🟡 Medium | Environment variable overrides |

#### Orchestration/Build (4 files missing)

| File | Lines | Risk | Evidence |
|------|-------|------|----------|
| `build/content.py` | ~200 | 🔴 High | Content discovery phase |
| `build/finalization.py` | ~242 | 🔴 High | Build finalization phase |
| `build/initialization.py` | ~150 | 🔴 High | Build initialization phase |
| `build/rendering.py` | ~180 | 🔴 High | Rendering phase |

#### Health Validators (11 files missing)

| File | Tests | Used By |
|------|-------|---------|
| `cache.py` | ❌ | `bengal health` command |
| `config.py` | ❌ | `bengal health` command |
| `links.py` | ❌ | `bengal health` command |
| `menu.py` | ❌ | `bengal health` command |
| `output.py` | ❌ | `bengal health` command |
| `performance.py` | ❌ | `bengal health` command |
| `rendering.py` | ❌ | `bengal health` command |
| `tracks.py` | ❌ | `bengal health` command |
| `directives/analysis.py` | ❌ | Directive validation |
| `directives/checkers.py` | ❌ | Directive validation |
| `directives/constants.py` | ❌ | Directive validation |

#### Postprocess (5 files missing)

| File | Tests | Notes |
|------|-------|-------|
| `rss.py` | ❌ | RSS feed generator (validators tested, not generator) |
| `sitemap.py` | ❌ | Sitemap generator (validators tested, not generator) |
| `html_output.py` | ❌ | HTML output formatting |
| `output_formats/txt_generator.py` | ❌ | Plain text output |
| `output_formats/json_generator.py` | ❌ | JSON output |
| `output_formats/lunr_index_generator.py` | ❌ | Lunr search index |
| `output_formats/utils.py` | ❌ | Output utilities |

---

## 4. Design Options

### Option A: Comprehensive Coverage (Recommended)

**Approach**: Add tests for all high and medium priority gaps.

**Pros**:
- Fills all significant gaps
- Increases overall coverage to ~60%+
- Catches bugs before they reach production

**Cons**:
- ~25-30 new test files
- ~3-4 days of effort

**Estimated Files**:
- 5 high-priority utils tests
- 1 services test
- 4 config tests
- 4 orchestration/build tests
- 8 health validator tests
- 5 postprocess tests
- **Total**: ~27 new test files

### Option B: Critical Path Only

**Approach**: Only test files that affect build correctness.

**Pros**:
- Faster to implement (~1-2 days)
- Focuses on highest risk areas

**Cons**:
- Leaves medium-risk areas untested
- May miss edge cases in validators

**Estimated Files**:
- 5 high-priority utils tests
- 1 services test
- 4 orchestration/build tests
- **Total**: ~10 new test files

### Option C: Risk-Based Phased Approach

**Approach**: Implement in 3 phases based on risk.

**Phase 1** (High Risk - 1 day):
- `services/validation.py`
- `utils/build_context.py`
- `utils/metadata.py`
- `utils/theme_resolution.py`
- `orchestration/build/*.py`

**Phase 2** (Medium Risk - 1-2 days):
- `config/*.py` (4 files)
- `health/validators/*.py` (11 files)

**Phase 3** (Lower Priority - 1 day):
- `postprocess/*.py` (5 files)
- `utils/*.py` (remaining 10 files)

**Pros**:
- Prioritizes by actual risk
- Can stop after Phase 1 if needed
- Clear checkpoints

**Cons**:
- May take longer overall
- Requires multiple PRs

---

## 5. Recommendation

**Recommended**: Option C - Risk-Based Phased Approach

### Rationale

1. **Immediate value**: Phase 1 addresses highest-risk gaps
2. **Flexibility**: Can adjust scope after Phase 1
3. **Clear deliverables**: Each phase is independently mergeable
4. **Matches existing patterns**: Bengal already uses phased approaches

### Implementation Plan

#### Phase 1: Critical Path (Priority: 🔴 High)

| Test File | Source File | Tests to Add |
|-----------|-------------|--------------|
| `tests/unit/services/test_validation.py` | `services/validation.py` | Protocol tests, adapter tests |
| `tests/unit/utils/test_build_context.py` | `utils/build_context.py` | State management tests |
| `tests/unit/utils/test_metadata.py` | `utils/metadata.py` | Metadata extraction tests |
| `tests/unit/utils/test_theme_resolution.py` | `utils/theme_resolution.py` | Theme chain tests |
| `tests/unit/utils/test_sections_utils.py` | `utils/sections.py` | Section utility tests |
| `tests/unit/orchestration/build/test_phases.py` | `build/*.py` | Phase transition tests |

**Estimated effort**: 1 day  
**Expected test count**: ~50-80 new tests

#### Phase 2: Config & Health (Priority: 🟡 Medium)

| Test File | Source File |
|-----------|-------------|
| `tests/unit/config/test_defaults.py` | `config/defaults.py` |
| `tests/unit/config/test_deprecation.py` | `config/deprecation.py` |
| `tests/unit/config/test_validators.py` | `config/validators.py` |
| `tests/unit/config/test_env_overrides.py` | `config/env_overrides.py` |
| `tests/unit/health/validators/test_cache.py` | `validators/cache.py` |
| `tests/unit/health/validators/test_config.py` | `validators/config.py` |
| `tests/unit/health/validators/test_links.py` | `validators/links.py` |
| `tests/unit/health/validators/test_menu.py` | `validators/menu.py` |
| `tests/unit/health/validators/test_output.py` | `validators/output.py` |
| `tests/unit/health/validators/test_performance.py` | `validators/performance.py` |
| `tests/unit/health/validators/test_rendering.py` | `validators/rendering.py` |
| `tests/unit/health/validators/test_tracks.py` | `validators/tracks.py` |

**Estimated effort**: 1-2 days  
**Expected test count**: ~100-150 new tests

#### Phase 3: Postprocess & Utils (Priority: 🟢 Lower)

| Test File | Source File |
|-----------|-------------|
| `tests/unit/postprocess/test_rss_generator.py` | `postprocess/rss.py` |
| `tests/unit/postprocess/test_sitemap_generator.py` | `postprocess/sitemap.py` |
| `tests/unit/postprocess/test_html_output.py` | `postprocess/html_output.py` |
| `tests/unit/postprocess/test_output_formats.py` | `output_formats/*.py` |
| `tests/unit/utils/test_build_stats.py` | `utils/build_stats.py` |
| `tests/unit/utils/test_build_summary.py` | `utils/build_summary.py` |
| `tests/unit/utils/test_css_minifier.py` | `utils/css_minifier.py` |
| `tests/unit/utils/test_js_bundler.py` | `utils/js_bundler.py` |
| `tests/unit/utils/test_file_utils.py` | `utils/file_utils.py` |

**Estimated effort**: 1 day  
**Expected test count**: ~60-80 new tests

---

## 6. Test Patterns to Use

### Protocol Tests (for `services/validation.py`)

```python
"""Tests for validation service protocol."""
from bengal.services.validation import (
    DefaultTemplateValidationService,
    TemplateValidationService,
)

class TestTemplateValidationService:
    """Test validation service protocol compliance."""

    def test_default_service_implements_protocol(self):
        """DefaultTemplateValidationService implements TemplateValidationService."""
        service = DefaultTemplateValidationService()
        assert isinstance(service, TemplateValidationService)

    def test_validate_returns_error_count(self, mock_site):
        """validate() returns integer error count."""
        service = DefaultTemplateValidationService()
        result = service.validate(mock_site)
        assert isinstance(result, int)
        assert result >= 0
```

### Unit Tests (for utils)

```python
"""Tests for theme resolution utilities."""
from bengal.utils.theme_resolution import resolve_theme_chain

class TestThemeResolution:
    """Test theme chain resolution."""

    def test_single_theme_returns_list(self):
        """Single theme returns single-item list."""
        chain = resolve_theme_chain("default", available=["default"])
        assert chain == ["default"]

    def test_theme_with_parent_returns_chain(self):
        """Theme with parent returns full inheritance chain."""
        chain = resolve_theme_chain(
            "child",
            available=["default", "child"],
            parents={"child": "default"}
        )
        assert chain == ["child", "default"]
```

### Integration Tests (for orchestration phases)

```python
"""Tests for build phase orchestration."""
from bengal.orchestration.build import (
    ContentPhase,
    FinalizationPhase,
    InitializationPhase,
    RenderingPhase,
)

class TestBuildPhases:
    """Test build phase transitions."""

    def test_initialization_sets_up_context(self, tmp_site):
        """InitializationPhase sets up build context."""
        phase = InitializationPhase(tmp_site)
        context = phase.execute()
        assert context.site is not None
        assert context.cache is not None

    def test_phases_execute_in_order(self, tmp_site):
        """Phases execute in correct order."""
        # Test phase dependencies
        pass
```

---

## 7. Success Criteria

### Phase 1 Complete When:
- [ ] All 6 high-priority test files created
- [ ] 50+ new tests pass
- [ ] No regressions in existing tests
- [ ] Coverage report shows improvement in critical modules

### Phase 2 Complete When:
- [ ] All 12 config/health test files created
- [ ] 150+ total new tests pass
- [ ] Health validators have basic coverage

### Phase 3 Complete When:
- [ ] All 9 postprocess/utils test files created
- [ ] 250+ total new tests pass
- [ ] Overall coverage increased by ~5-10%

---

## 8. Architecture Impact

### Changes Required

**None** - This RFC adds tests only, no source changes needed.

### Test Infrastructure

May benefit from:
1. Additional mock fixtures for `Site`, `Page`, `Section`
2. Shared test utilities for phase testing
3. Fixtures for config validation testing

---

## 9. Risks & Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Tests reveal bugs | Medium | Low | Fix bugs as found - that's the point |
| Test maintenance burden | Low | Medium | Use parametrized tests, shared fixtures |
| Slow test suite | Low | Low | Use module-scoped fixtures, parallel execution |

---

## 10. Open Questions

1. **Should content layer sources have mock tests?**
   - `github.py`, `notion.py`, `rest.py` are network-dependent
   - Could add mock-based tests or mark as intentionally untested

2. **What coverage target for validators?**
   - 80%? 90%? 100%?
   - Some validators may have edge cases not worth testing

3. **Should we add property-based tests for new modules?**
   - Could add Hypothesis tests for `theme_resolution`, `metadata`
   - Adds ~100 examples per property test

---

## 11. References

- `tests/TEST_COVERAGE.md` - Current coverage documentation
- `tests/_testing/mocks.py` - Existing mock infrastructure
- `tests/_testing/fixtures.py` - Existing test fixtures
- `architecture/testing.md` - Testing architecture (if exists)

---

## Appendix: Full Gap List

<details>
<summary>Click to expand full file list</summary>

### Utils (14 files)
1. `bengal/utils/build_context.py` - ❌ No tests
2. `bengal/utils/build_stats.py` - ❌ No tests
3. `bengal/utils/build_summary.py` - ❌ No tests
4. `bengal/utils/css_minifier.py` - ❌ No tests
5. `bengal/utils/file_utils.py` - ❌ No tests
6. `bengal/utils/js_bundler.py` - ❌ No tests
7. `bengal/utils/live_progress.py` - ❌ No tests
8. `bengal/utils/metadata.py` - ❌ No tests
9. `bengal/utils/performance_collector.py` - ❌ No tests
10. `bengal/utils/performance_report.py` - ❌ No tests
11. `bengal/utils/progress.py` - ❌ No tests
12. `bengal/utils/sections.py` - ❌ No tests
13. `bengal/utils/theme_resolution.py` - ❌ No tests
14. `bengal/utils/autodoc.py` - ❌ No tests

### Services (1 file)
1. `bengal/services/validation.py` - ❌ No tests

### Config (4 files)
1. `bengal/config/defaults.py` - ❌ No tests
2. `bengal/config/deprecation.py` - ❌ No tests
3. `bengal/config/validators.py` - ❌ No tests
4. `bengal/config/env_overrides.py` - ❌ No tests

### Orchestration/Build (4 files)
1. `bengal/orchestration/build/content.py` - ❌ No tests
2. `bengal/orchestration/build/finalization.py` - ❌ No tests
3. `bengal/orchestration/build/initialization.py` - ❌ No tests
4. `bengal/orchestration/build/rendering.py` - ❌ No tests

### Orchestration (2 additional files)
1. `bengal/orchestration/asset.py` - ❌ No tests
2. `bengal/orchestration/autodoc.py` - ❌ No tests

### Health Validators (11 files)
1. `bengal/health/validators/cache.py` - ❌ No tests
2. `bengal/health/validators/config.py` - ❌ No tests
3. `bengal/health/validators/links.py` - ❌ No tests
4. `bengal/health/validators/menu.py` - ❌ No tests
5. `bengal/health/validators/output.py` - ❌ No tests
6. `bengal/health/validators/performance.py` - ❌ No tests
7. `bengal/health/validators/rendering.py` - ❌ No tests
8. `bengal/health/validators/tracks.py` - ❌ No tests
9. `bengal/health/validators/directives/analysis.py` - ❌ No tests
10. `bengal/health/validators/directives/checkers.py` - ❌ No tests
11. `bengal/health/validators/directives/constants.py` - ❌ No tests

### Postprocess (7 files)
1. `bengal/postprocess/rss.py` - ❌ No tests (only validator)
2. `bengal/postprocess/sitemap.py` - ❌ No tests (only validator)
3. `bengal/postprocess/html_output.py` - ❌ No tests
4. `bengal/postprocess/output_formats/txt_generator.py` - ❌ No tests
5. `bengal/postprocess/output_formats/json_generator.py` - ❌ No tests
6. `bengal/postprocess/output_formats/lunr_index_generator.py` - ❌ No tests
7. `bengal/postprocess/output_formats/utils.py` - ❌ No tests

### Content Layer Sources (3 files)
1. `bengal/content_layer/sources/github.py` - ❌ No tests
2. `bengal/content_layer/sources/notion.py` - ❌ No tests
3. `bengal/content_layer/sources/rest.py` - ❌ No tests

</details>

---

**Total Gap**: 45+ source files without tests  
**Recommended Action**: Implement Phase 1 immediately, Phase 2-3 as follow-up

