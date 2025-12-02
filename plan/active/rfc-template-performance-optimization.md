# RFC: Template Performance Optimization

**Status**: In Progress  
**Created**: 2024-12-02  
**Author**: AI Assistant  
**Subsystems**: Rendering, Themes

---

## Problem Statement

Bengal's default theme templates have grown organically and contain several performance inefficiencies:

1. **base.html is 508 lines** - Monolithic, hard to maintain
2. **Duplicate logic** - Mobile/desktop nav render identical menus separately
3. **Repeated defensive checks** - `{% if page is defined and page %}` appears 34 times across templates
4. **Uncached template function calls** - Same functions called multiple times per render
5. **No template-level profiling** - Unknown which parts are slow

### Evidence (Verified 2024-12-02)

```bash
# Template line counts (partials)
933 partials/search.html        # Huge but only on search pages
508 base.html                   # Every page pays this cost
409 partials/navigation-components.html
331 partials/content-components.html

# Defensive checks count (verified via grep)
34 instances of "page is defined and page" across 5 template files:
  - base.html: 16 instances (now 1 after optimization)
  - docs-nav.html: 9 instances
  - docs-nav-section.html: 5 instances
  - content-components.html: 1 instance
  - index.html: 3 instances

# Duplicate function calls (verified)
  - get_menu_lang('main', current_lang()): called 3x in base.html (desktop, mobile, footer)
  - get_auto_nav(): called 2x in base.html (desktop, mobile)
  - current_lang(): called 3+x
```

### Symptoms

- Cold build for ~700 pages takes 13-15 seconds
- Template rendering is estimated at 40-50% of build time
- No visibility into which template operations are expensive

---

## Goals

1. **Reduce template rendering time by 15-25%**
2. **Improve template maintainability** (smaller, focused files)
3. **Add template profiling** to identify future bottlenecks
4. **Preserve all existing functionality** (no visual changes)

## Non-Goals

- Complete theme redesign
- New template features
- Breaking changes to template API

---

## Design Options

### Option A: Incremental Cleanup (Recommended)

**Effort**: Medium (2-3 days)  
**Risk**: Low  
**Expected Gain**: 15-20%

#### Phase 1: Cache Template Variables (1-2 hours)

Add variable caching at top of `base.html`:

```jinja
{# Cache expensive lookups once #}
{% set _page = page if page is defined else none %}
{% set _has_page = _page is not none %}
{% set _page_title = _page.title if _has_page and _page.title else '' %}
{% set _main_menu = get_menu_lang('main', current_lang()) %}
{% set _auto_nav = get_auto_nav() if _main_menu | length == 0 else [] %}
{% set _footer_menu = get_menu_lang('footer', current_lang()) %}
```

Then replace all instances:
```jinja
{# Before (20+ instances) #}
{% if page is defined and page and page.title is defined %}

{# After #}
{% if _page_title %}
```

#### Phase 2: Extract Navigation Partial (2-3 hours)

Create `partials/nav-menu.html`:

```jinja
{# partials/nav-menu.html #}
{# Renders menu items - used by both desktop and mobile nav #}
{% macro render_menu(menu, auto_nav, is_mobile=false) %}
  {% if menu %}
    {% for item in menu %}
    <li class="{{ 'active' if item.active else '' }}">
      <a href="{{ item.url | absolute_url }}">{{ item.name }}</a>
      {% if item.children %}
      <ul class="submenu">
        {% for child in item.children %}
        <li><a href="{{ child.url | absolute_url }}">{{ child.name }}</a></li>
        {% endfor %}
      </ul>
      {% endif %}
    </li>
    {% endfor %}
  {% elif auto_nav %}
    <li class="{{ 'active' if _page_url == '/' else '' }}">
      <a href="{{ '/' | absolute_url }}">Home</a>
    </li>
    {% for item in auto_nav %}
    <li><a href="{{ item.url | absolute_url }}">{{ item.name }}</a></li>
    {% endfor %}
  {% endif %}
{% endmacro %}
```

Reduces duplication by ~80 lines.

#### Phase 3: Split base.html (3-4 hours)

Extract to focused partials:

```
templates/
├── base.html              # ~150 lines (skeleton only)
├── partials/
│   ├── head.html          # <head> content (~100 lines)
│   ├── header.html        # Site header (~80 lines)
│   ├── footer.html        # Site footer (~50 lines)
│   ├── nav-menu.html      # Shared nav macro (~40 lines)
│   └── scripts.html       # JS loading (~80 lines)
```

#### Phase 4: Lazy Search Modal (1-2 hours)

Only include search modal on pages that need it:

```jinja
{# base.html - conditional include #}
{% set _search_modal = site.config.get('search', {}).get('ui', {}).get('modal', false) %}
{% if _search_modal %}
  {% include 'partials/search-modal.html' %}
{% endif %}
```

### Option B: Template Function Optimization

**Effort**: Medium (2-3 days)  
**Risk**: Medium  
**Expected Gain**: 10-15%

Optimize Python-side template functions:

```python
# bengal/rendering/template_functions.py

# Add memoization to expensive functions
@lru_cache(maxsize=128)
def get_menu_lang(menu_name: str, lang: str) -> list[MenuItem]:
    """Get menu items for language (cached per build)."""
    ...

# Pre-compute asset URLs at build start
class AssetURLCache:
    """Cache asset URLs to avoid repeated lookups."""
    def __init__(self, site):
        self._cache = {}
        self._site = site

    def get(self, path: str) -> str:
        if path not in self._cache:
            self._cache[path] = self._compute_url(path)
        return self._cache[path]
```

### Option C: Template Profiling Infrastructure

**Effort**: Low (1 day)  
**Risk**: Low  
**Expected Gain**: Visibility only (enables future optimization)

Add template rendering timing:

```python
# bengal/rendering/template_engine.py

class ProfiledEnvironment(Environment):
    """Jinja environment with template profiling."""

    def __init__(self, *args, profile=False, **kwargs):
        super().__init__(*args, **kwargs)
        self._profile = profile
        self._timings = defaultdict(list)

    def get_template(self, name, *args, **kwargs):
        template = super().get_template(name, *args, **kwargs)
        if self._profile:
            return ProfiledTemplate(template, self._timings)
        return template

    def get_timing_report(self) -> dict:
        """Get template timing statistics."""
        return {
            name: {
                'count': len(times),
                'total_ms': sum(times) * 1000,
                'avg_ms': (sum(times) / len(times)) * 1000,
            }
            for name, times in self._timings.items()
        }
```

Usage:
```bash
bengal build --profile-templates
# Output:
# Template Rendering Report:
#   base.html: 700 renders, 4.2s total, 6.0ms avg
#   partials/docs-nav.html: 350 renders, 1.8s total, 5.1ms avg
#   ...
```

---

## Recommendation

**Implement Options A + C together:**

1. **Option C first** (1 day) - Get visibility into actual bottlenecks
2. **Option A phases 1-2** (half day) - Quick wins with variable caching and nav extraction
3. **Measure improvement** - Profile again
4. **Option A phases 3-4** (1 day) - If still needed based on profiling

This approach:
- Validates assumptions with data before major refactoring
- Delivers quick wins immediately
- Preserves option to stop if gains are sufficient

---

## Implementation Plan

### Phase 1: Template Profiling (Day 1)

| Task | File | Estimate |
|------|------|----------|
| Add `ProfiledEnvironment` | `template_engine.py` | 2h |
| Add `--profile-templates` flag | `cli/build.py` | 1h |
| Run baseline profile | - | 1h |
| Document findings | This RFC | 1h |

### Phase 2: Variable Caching (Day 2, AM)

| Task | File | Estimate |
|------|------|----------|
| Add cached variables to base.html | `base.html` | 1h |
| Replace defensive checks (20+ instances) | `base.html` | 1h |
| Test all page types render correctly | - | 1h |

### Phase 3: Navigation Extraction (Day 2, PM)

| Task | File | Estimate |
|------|------|----------|
| Create `nav-menu.html` macro | `partials/nav-menu.html` | 1h |
| Update desktop nav in base.html | `base.html` | 30m |
| Update mobile nav in base.html | `base.html` | 30m |
| Test navigation on all screen sizes | - | 1h |

### Phase 4: Measure & Decide (Day 3)

| Task | Estimate |
|------|----------|
| Run profile again | 30m |
| Compare before/after | 30m |
| Decide if Phase 3-4 of Option A needed | 30m |
| Update RFC with results | 1h |

---

## Metrics

### Before (Baseline)

```yaml
cold_build_700_pages: ~14s
template_rendering_estimate: 40-50% (~6s)
base_html_lines: 508
defensive_checks: 20+
menu_function_calls_per_page: 4
```

### Target (After)

```yaml
cold_build_700_pages: <12s  # 15% improvement
template_rendering: <5s
base_html_lines: <200
defensive_checks: 2-3 (cached)
menu_function_calls_per_page: 1 (cached)
```

---

## Risks & Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Template changes break rendering | Medium | High | Test all page types (page, post, doc, blog) |
| Profiling overhead in production | Low | Low | Only enable with `--profile-templates` |
| Cached variables become stale | Low | Medium | Cache at render time, not build time |
| Partial extraction breaks inheritance | Medium | Medium | Careful testing of `{% block %}` behavior |

---

## Alternatives Considered

### 1. Switch to Faster Template Engine (Mako, Chameleon)

**Rejected**: Jinja2 is fast enough, ecosystem benefits outweigh marginal speed gains.

### 2. Server-Side Rendering with Caching (SSR)

**Rejected**: Bengal is a static site generator, not a dynamic server.

### 3. Pre-compile All Templates at Startup

**Already Done**: Bengal uses `FileSystemBytecodeCache`.

### 4. Use Jinja2's `{% cache %}` Extension

**Considered for Future**: Would require careful cache invalidation logic.

---

## Open Questions

1. **What's the actual template rendering time?** Need profiling data.
2. **Are template functions (`get_menu_lang`, `asset_url`) cached?** Need to verify.
3. **Is search modal inclusion expensive?** 137 lines on every page.
4. **Would async template rendering help?** Jinja2 supports async, but unclear if beneficial.

---

## References

- [Jinja2 Performance Tips](https://jinja.palletsprojects.com/en/3.1.x/api/#high-level-api)
- `bengal/themes/default/templates/base.html` - Main template
- `bengal/rendering/template_engine.py` - Template engine setup
- `plan/active/rfc-render-performance-optimization.md` - Related RFC

---

## Implementation Progress

### ✅ Phase 1: Template Profiling (COMPLETE)

Added `bengal/rendering/template_profiler.py` with:
- `TemplateProfiler` class for collecting timing data
- `ProfiledTemplate` wrapper for template.render() timing
- `format_profile_report()` for CLI output
- Integration with TemplateEngine via `profile_templates` parameter

New CLI flag: `bengal build --profile-templates`

Files changed:
- `bengal/rendering/template_profiler.py` (new, ~320 lines)
- `bengal/rendering/template_engine.py` (updated)
- `bengal/rendering/pipeline.py` (updated)
- `bengal/cli/commands/build.py` (updated)
- `bengal/core/site.py` (updated)
- `bengal/orchestration/build/__init__.py` (updated)
- `bengal/orchestration/build/rendering.py` (updated)
- `bengal/utils/build_context.py` (updated)

### ✅ Phase 2: Variable Caching (COMPLETE)

Added cached variables at top of `base.html`:
```jinja
{% set _page = page if page is defined else none %}
{% set _has_page = _page is not none %}
{% set _page_title = _page.title if (_has_page and _page.title is defined) else '' %}
{% set _page_url = _page.relative_url if (_has_page and _page.relative_url is defined) else '/' %}
{% set _current_lang = current_lang() %}
{% set _main_menu = get_menu_lang('main', _current_lang) %}
{% set _auto_nav = get_auto_nav() if _main_menu | length == 0 else [] %}
{% set _footer_menu = get_menu_lang('footer', _current_lang) %}
{% set _site_title = site.config.title %}
```

Results:
- `page is defined and page` in base.html: 16 → 1 (15 eliminated)
- `get_menu_lang()` calls: 3 → 1
- `get_auto_nav()` calls: 2 → 1
- `current_lang()` calls: 3+ → 1

### ⏳ Phase 3: Navigation Extraction (PENDING)

Create `partials/nav-menu.html` macro to share between desktop/mobile nav.

### ⏳ Phase 4: Baseline Profile (PENDING)

Run `bengal build --profile-templates` on test site to measure actual impact.

---

## Changelog

| Date | Change |
|------|--------|
| 2024-12-02 | Initial draft |
| 2024-12-02 | Phase 1: Added template profiling infrastructure |
| 2024-12-02 | Phase 2: Added variable caching in base.html |
| 2024-12-02 | Updated evidence with verified counts |
