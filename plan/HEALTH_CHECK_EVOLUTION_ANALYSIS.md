# Health Check System Evolution Analysis

**Date:** October 3, 2025  
**Status:** Strategic Analysis  
**Purpose:** Evaluate current health check system and propose evolution

---

## Executive Summary

Bengal's health check system was implemented as a reactive fix after a template rendering bug. Since then, the product has grown significantly with **75 template functions**, **incremental builds**, **parallel processing**, **mistune parser**, **menu systems**, and **rich navigation**. The health check hasn't evolved to match this complexity.

**Key Finding:** We have the pieces of a comprehensive validation system scattered across multiple files, but no unified health check strategy.

---

## Current State Assessment

### What We Have: `_validate_build_health()` in `site.py`

```python
def _validate_build_health(self) -> None:
    """Lines 851-914 in bengal/core/site.py"""
    
    # Check 1: Page size validation (active)
    min_size = self.config.get("min_page_size", 1000)
    for page in self.pages:
        if page.output_path.stat().st_size < min_size:
            issues.append(f"Page {page} suspiciously small")
    
    # Check 2: Asset presence (active)
    css_count = len(list(assets_dir.glob("css/*.css")))
    if css_count == 0:
        issues.append("No CSS files found")
    
    # Check 3: Unrendered Jinja2 (DISABLED)
    # NOTE: Disabled because of false positives in docs
    pass
```

**Observations:**
1. ✅ **Simple and focused** - Does what it was designed for
2. ⚠️ **Reactive, not proactive** - Built to catch one specific bug
3. ⚠️ **Limited scope** - Only 2 active checks (3rd disabled)
4. ⚠️ **Post-build only** - Runs after everything is done
5. ⚠️ **No structured output** - Just prints to console

**Configuration:**
- `validate_build: true` (default) - Enable/disable all checks
- `strict_mode: false` (default) - Fail build on issues vs warn
- `min_page_size: 1000` (bytes) - Minimum page size threshold

**When It Runs:**
```python
# In site.build() after rendering, assets, and post-processing
self._post_process()
self._validate_build_health()  # Last step before completion
```

---

## Product Growth Since Implementation

### New Complexity (October 2025)

1. **Cache & Incremental Builds** (18-42x speedup)
   - SHA256 file hashing
   - Dependency graph tracking
   - Template change detection
   - `.bengal-cache.json` persistence
   - **Not validated** ❌

2. **75 Template Functions** (across 15 modules)
   - Strings, collections, math, dates, URLs
   - Content, data, files, images
   - SEO, debug, taxonomies, pagination
   - **Not validated** ❌

3. **Mistune Parser Integration** (42% faster)
   - Multi-engine architecture
   - Custom plugins (admonitions, directives)
   - Variable substitution in markdown
   - Thread-local caching
   - **Not validated** ❌

4. **Menu System**
   - Config-driven hierarchical menus
   - Active state detection
   - Dropdown support
   - **Not validated** ❌

5. **Navigation System**
   - Page.next, Page.prev
   - Breadcrumbs (ancestors)
   - Section navigation
   - **Not validated** ❌

6. **Parallel Processing**
   - Pages, assets, post-processing
   - Thread-safe operations
   - Smart thresholds
   - **Not validated** ❌

7. **Configuration Validation** (SEPARATE SYSTEM!)
   - `ConfigValidator` in `bengal/config/validators.py`
   - Type checking, coercion, ranges
   - Already working well ✅
   - **Not integrated with health checks** ⚠️

### Existing Validation Systems (Scattered)

#### 1. Config Validation (`config/validators.py`)
```python
class ConfigValidator:
    """Type-safe config validation with coercion"""
    - Validates: types, ranges, dependencies
    - Runs: At config load time
    - Output: Clear error messages, fails early
    - Coverage: Excellent ✅
```

#### 2. Frontmatter Parsing (`discovery/content_discovery.py`)
```python
def _parse_frontmatter(self, file_path):
    """Parses YAML/TOML frontmatter"""
    - Validates: YAML syntax
    - Runs: During content discovery
    - Output: Warnings, preserves content
    - Coverage: Good ✅
```

#### 3. Menu Validation (`core/menu.py`)
```python
class MenuBuilder:
    """Validates menu structure"""
    - Validates: Orphaned items, circular refs
    - Runs: During menu building
    - Output: Warnings in verbose mode
    - Coverage: Good ✅
```

#### 4. Link Validation (`rendering/link_validator.py`)
```python
class LinkValidator:
    """Validates internal/external links"""
    - Validates: Broken links
    - Runs: During post-processing
    - Output: Summary of broken links
    - Coverage: Basic ✅
```

#### 5. Template Rendering (`rendering/renderer.py`)
```python
def render_page(self, page, content):
    """Renders with error handling"""
    try:
        return self.template_engine.render(...)
    except Exception as e:
        if strict_mode:
            raise  # Fail loudly
        return self._render_fallback(page, content)  # Graceful
```

**Problem:** All these validation systems exist in **silos** with no unified health check report!

---

## Gap Analysis

### What's Missing

#### 1. **Pre-Build Validation** ❌
- No environment checks before starting
- No dependency verification
- No theme validation
- **Impact:** Waste time building before failing

#### 2. **Build-Time Validation** ❌
- No rendering quality checks during build
- No template function validation
- No parser plugin validation
- **Impact:** Silent failures until users notice

#### 3. **Post-Build Validation** (Partially Present)
- ✅ Page size checks
- ✅ Asset presence checks
- ❌ Link validation not surfaced in health check
- ❌ No navigation validation
- ❌ No taxonomy validation
- ❌ No cache validation
- **Impact:** Incomplete coverage

#### 4. **Unified Reporting** ❌
- Each validator prints to console independently
- No structured health check report
- No severity levels (error vs warning vs info)
- No machine-readable output
- **Impact:** Hard to diagnose issues

#### 5. **Incremental Build Health** ❌
- No cache integrity checks
- No dependency graph validation
- No detection of cache corruption
- **Impact:** Incremental builds may be incorrect

#### 6. **Performance Health** ❌
- No detection of slow pages
- No memory usage warnings
- No parallel processing verification
- **Impact:** Performance regressions unnoticed

---

## Strategic Evolution Plan

### Philosophy: Health Checks Should Be Like Tests

**Principles:**
1. **Multi-Stage**: Pre-build, build-time, post-build
2. **Composable**: Each validator is independent
3. **Configurable**: Enable/disable specific checks
4. **Actionable**: Clear recommendations
5. **Non-Intrusive**: Fast, minimal overhead
6. **Comprehensive**: Cover all major systems

### Architecture Proposal

```
bengal/
└── health/
    ├── __init__.py
    ├── health_check.py         # Orchestrator
    ├── validators/
    │   ├── __init__.py
    │   ├── environment.py      # Pre-build: deps, theme, config
    │   ├── rendering.py        # Build-time: templates, pages
    │   ├── output.py           # Post-build: pages, assets
    │   ├── cache.py            # Cache integrity
    │   ├── navigation.py       # Menus, links, breadcrumbs
    │   └── performance.py      # Timing, memory, bottlenecks
    └── report.py               # Structured reporting
```

### Implementation Phases

#### Phase 1: Unify Existing Validators (Foundational)

**Goal:** Bring all existing validation under one health check system

**Changes:**
1. Create `health/` module
2. Create `HealthCheck` orchestrator class
3. Migrate existing validators to new structure
4. Create unified report format

**Validators to Integrate:**
- ConfigValidator (already exists)
- Menu validation (already exists)
- Link validation (already exists)
- Page size checks (already exists)
- Asset presence checks (already exists)

**Example Output:**
```
🏥 Health Check Report
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

✅ Configuration       5 checks passed
✅ Content Discovery   3 checks passed
⚠️  Rendering          2 warnings
   • 3 pages < 1KB (likely fallback HTML)
   • Consider reviewing: about.html, contact.html
✅ Navigation          4 checks passed
⚠️  Post-Processing    1 warning
   • 5 broken links found (see details below)
✅ Cache Integrity     2 checks passed

Summary: 19 passed, 3 warnings, 0 errors
Build Quality: 87% (Good)
```

**Effort:** 4-6 hours

---

#### Phase 2: Add Build-Time Validators (Enhanced)

**Goal:** Catch issues during build, not after

**New Validators:**

1. **Rendering Quality Validator**
   ```python
   class RenderingValidator:
       def validate_during_render(self, page, html):
           """Called during page rendering"""
           checks = []
           
           # Check HTML structure
           if not self._has_valid_html_structure(html):
               checks.append(Warning(f"{page}: Invalid HTML structure"))
           
           # Check for unrendered variables
           if '{{ page.' in html and 'language-' not in html:
               checks.append(Warning(f"{page}: Possible unrendered variable"))
           
           # Check metadata usage
           if page.metadata.get('required_var') and 'required_var' not in html:
               checks.append(Info(f"{page}: Metadata 'required_var' not used"))
           
           return checks
   ```

2. **Navigation Validator**
   ```python
   class NavigationValidator:
       def validate(self, site):
           """Validate all navigation works"""
           checks = []
           
           # Check menu structure
           for menu_name, items in site.menu.items():
               checks.extend(self._validate_menu(menu_name, items))
           
           # Check breadcrumbs
           for page in site.pages:
               if page.ancestors:
                   checks.extend(self._validate_breadcrumbs(page))
           
           # Check next/prev
           for page in site.pages:
               if page.next and not page.next.output_path.exists():
                   checks.append(Error(f"{page}: page.next points to missing page"))
           
           return checks
   ```

3. **Taxonomy Validator**
   ```python
   class TaxonomyValidator:
       def validate(self, site):
           """Validate taxonomies and generated pages"""
           checks = []
           
           # Check tag pages generated
           for tag_slug, tag_data in site.taxonomies['tags'].items():
               tag_page = self._find_tag_page(site, tag_slug)
               if not tag_page:
                   checks.append(Error(f"Tag '{tag_slug}' has no page"))
           
           # Check orphaned tag pages
           for page in site.pages:
               if page.metadata.get('type') == 'tag':
                   tag_slug = page.metadata.get('_tag_slug')
                   if tag_slug not in site.taxonomies['tags']:
                       checks.append(Warning(f"Orphaned tag page: {tag_slug}"))
           
           return checks
   ```

4. **Template Function Validator**
   ```python
   class TemplateFunctionValidator:
       def validate(self, template_engine):
           """Validate all template functions are registered"""
           checks = []
           
           expected_functions = [
               'truncatewords', 'slugify', 'where', 'group_by',
               'time_ago', 'absolute_url', 'safe_html', 'get_data',
               # ... all 75 functions
           ]
           
           registered = template_engine.env.filters.keys()
           
           for func in expected_functions:
               if func not in registered:
                   checks.append(Error(f"Template function '{func}' not registered"))
           
           return checks
   ```

**Effort:** 6-8 hours

---

#### Phase 3: Cache & Performance Validators (Advanced)

**Goal:** Validate incremental builds and performance

**New Validators:**

1. **Cache Integrity Validator**
   ```python
   class CacheValidator:
       def validate(self, cache_path, site):
           """Validate cache integrity"""
           checks = []
           
           # Check cache file
           if not cache_path.exists():
               return [Info("No cache file (first build)")]
           
           # Load cache
           cache = BuildCache.load(cache_path)
           
           # Validate file hashes
           for file_path in cache.file_hashes.keys():
               if not Path(file_path).exists():
                   checks.append(Warning(f"Cached file missing: {file_path}"))
           
           # Validate dependencies
           for source, deps in cache.dependencies.items():
               for dep in deps:
                   if not Path(dep).exists():
                       checks.append(Warning(f"Dependency missing: {dep} (from {source})"))
           
           # Check cache size
           cache_size = cache_path.stat().st_size
           if cache_size > 10_000_000:  # 10MB
               checks.append(Warning(f"Cache file very large: {cache_size / 1_000_000:.1f}MB"))
           
           return checks
   ```

2. **Performance Validator**
   ```python
   class PerformanceValidator:
       def validate(self, build_stats):
           """Validate build performance"""
           checks = []
           
           # Check for slow pages
           for page, render_time in build_stats.page_times.items():
               if render_time > 1000:  # 1 second
                   checks.append(Warning(f"{page}: Slow render ({render_time}ms)"))
           
           # Check build time
           total_time = build_stats.build_time_ms
           page_count = build_stats.total_pages
           avg_time = total_time / page_count
           
           if avg_time > 100:  # 100ms per page
               checks.append(Warning(f"Slow average render: {avg_time:.1f}ms/page"))
           
           # Check parallel efficiency
           if build_stats.parallel and build_stats.speedup < 1.5:
               checks.append(Info("Parallel processing not providing much speedup"))
           
           return checks
   ```

**Effort:** 6-8 hours

---

#### Phase 4: CI/CD Integration (Production)

**Goal:** Make health checks useful for CI/CD pipelines

**Features:**

1. **Machine-Readable Output**
   ```python
   class HealthCheckReport:
       def to_json(self):
           return {
               "status": "passed",  # passed, warning, failed
               "summary": {
                   "passed": 19,
                   "warnings": 3,
                   "errors": 0
               },
               "checks": [
                   {
                       "validator": "NavigationValidator",
                       "status": "warning",
                       "message": "5 broken links found",
                       "details": [...]
                   }
               ],
               "build_quality_score": 87
           }
   ```

2. **Exit Codes**
   ```python
   # In cli.py
   def build(...):
       stats = site.build(...)
       health_report = site.health_check()
       
       if health_report.has_errors():
           sys.exit(1)  # Fail CI
       elif health_report.has_warnings() and strict:
           sys.exit(1)  # Fail CI in strict mode
       else:
           sys.exit(0)  # Pass CI
   ```

3. **GitHub Actions Integration**
   ```yaml
   - name: Build Site
     run: bengal build --strict --health-check-json=report.json
   
   - name: Upload Health Report
     uses: actions/upload-artifact@v3
     with:
       name: health-check-report
       path: report.json
   ```

**Effort:** 3-4 hours

---

## Configuration Design

### Proposed Config Format

```toml
[health_check]
enabled = true
strict_mode = false  # Fail build on warnings
report_format = "console"  # console, json, html

# Enable/disable specific validators
[health_check.validators]
environment = true
rendering = true
output = true
cache = true
navigation = true
performance = true

# Thresholds
[health_check.thresholds]
min_page_size = 1000  # bytes
max_render_time = 1000  # ms per page
max_broken_links = 0
min_build_quality_score = 80  # 0-100

# Ignore patterns
[health_check.ignore]
pages = ["test/**", "drafts/**"]
broken_links = ["https://example.com/external"]
```

### CLI Flags

```bash
# Enable health checks (default)
bengal build

# Disable health checks
bengal build --no-health-check

# Strict mode (fail on warnings)
bengal build --strict

# JSON output for CI
bengal build --health-check-json=report.json

# HTML report
bengal build --health-check-html=report.html

# Verbose health check details
bengal build --health-check-verbose
```

---

## Implementation Priority

### Immediate (Next Session)
1. ✅ **Create health/ module structure**
2. ✅ **Implement HealthCheck orchestrator**
3. ✅ **Migrate existing validators**
4. ✅ **Create unified report format**
5. ✅ **Add to build process**

**Justification:** Foundation for everything else, low risk

---

### High Priority (Next Week)
1. **Add NavigationValidator**
   - Most complex new feature
   - High user impact
   - Currently unvalidated

2. **Add CacheValidator**
   - Incremental builds are critical
   - Cache corruption is silent
   - Hard to debug without validation

3. **Add TaxonomyValidator**
   - Generated pages are tricky
   - Easy to have orphaned pages
   - User-facing

**Justification:** These systems are complex and currently have no validation

---

### Medium Priority (Next Month)
1. **PerformanceValidator**
2. **TemplateFunctionValidator**
3. **RenderingValidator enhancements**
4. **CI/CD integration**

**Justification:** Nice to have, but not blocking

---

### Low Priority (Future)
1. **HTML report generation**
2. **Historical trend tracking**
3. **Performance regression detection**
4. **Custom validator plugins**

**Justification:** Advanced features for large teams

---

## Risk Assessment

### Risks of Current Approach

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Silent build failures | High | High | ✅ Unified health checks |
| Cache corruption undetected | Medium | High | ✅ Cache validator |
| Navigation broken | Medium | High | ✅ Navigation validator |
| Performance regressions | Medium | Medium | ✅ Performance validator |
| False positives | Low | Medium | ⚠️ Configurable thresholds |

### Risks of New System

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Performance overhead | Low | Low | • Run post-build<br>• Configurable<br>• Parallel execution |
| False positives | Medium | Medium | • Conservative thresholds<br>• Ignore patterns<br>• Severity levels |
| Maintenance burden | Low | Medium | • Modular design<br>• Comprehensive tests<br>• Clear docs |
| Breaking changes | Low | High | • Opt-in features<br>• Backward compatible<br>• Gradual rollout |

---

## Success Metrics

### How We'll Know It's Working

1. **Build Confidence**
   - ✅ Zero "silent failure" bug reports
   - ✅ Users trust build output
   - ✅ CI catches issues before production

2. **Time Savings**
   - ✅ Reduce debugging time by 50%
   - ✅ Catch issues in < 5 seconds vs minutes of investigation
   - ✅ Clear actionable recommendations

3. **Coverage**
   - ✅ All major systems validated
   - ✅ 90%+ of build issues detected
   - ✅ No major component without health check

4. **Usability**
   - ✅ Reports are clear and actionable
   - ✅ False positive rate < 5%
   - ✅ Performance overhead < 2% of build time

---

## Alternatives Considered

### Alternative 1: Do Nothing
**Pros:** No work, no risk  
**Cons:** Product complexity growing without validation  
**Verdict:** ❌ Unacceptable as product scales

### Alternative 2: External Tool (like vale, markdownlint)
**Pros:** Battle-tested, maintained by others  
**Cons:** Can't validate Bengal-specific features (cache, navigation, taxonomies)  
**Verdict:** ⚠️ Complement, not replacement

### Alternative 3: Test Suite Only
**Pros:** Developers are familiar with tests  
**Cons:** Tests validate code, not actual builds  
**Verdict:** ⚠️ Both needed (tests + health checks)

### Alternative 4: User-Facing Diagnostic Command
```bash
bengal doctor  # Like brew doctor, npm doctor
```
**Pros:** User-initiated, comprehensive  
**Cons:** Reactive, not proactive  
**Verdict:** ✅ Good addition, but not replacement for automatic checks

---

## Recommendations

### Immediate Actions (This Week)

1. **Create `bengal/health/` module**
   - Start with structure
   - Implement HealthCheck orchestrator
   - Add report formatting

2. **Migrate existing validators**
   - ConfigValidator integration
   - Menu validator integration
   - Link validator integration
   - Page size checks

3. **Add 2-3 critical validators**
   - NavigationValidator (high user impact)
   - CacheValidator (build correctness)
   - TaxonomyValidator (generated pages)

4. **Update documentation**
   - Health check configuration
   - Validator reference
   - CI/CD integration guide

### Long-Term Vision (Next Quarter)

1. **Make Bengal the most validated SSG**
   - More thorough than Hugo
   - More actionable than Jekyll
   - Production-ready confidence

2. **"Zero Surprise Builds"**
   - If build passes health checks → output is correct
   - If health checks fail → clear reason & fix
   - No silent failures ever

3. **Community Trust**
   - Users trust build output
   - Contributors understand validation
   - Clear path to adding validators

---

## Conclusion

Bengal's health check system is a **tactical success** (solved the immediate bug) but needs to become **strategic** (comprehensive validation as product grows).

**Key Insight:** We already have most validation pieces scattered across the codebase. We just need to unify them into a cohesive health check system.

**Recommendation:** Implement Phase 1 (Unify Existing Validators) this week. It's low-risk, high-value, and provides immediate ROI by surfacing all validation in one place.

**Next Step:** Create `bengal/health/` module and start migrating existing validators.

---

**Status:** Ready for implementation  
**Effort:** Phase 1 = 4-6 hours  
**ROI:** High (better build confidence, easier debugging, foundation for growth)

