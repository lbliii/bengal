# RFC: Template Context Redesign

**Status:** Draft  
**Author:** Bengal Team  
**Created:** 2024-12-23  
**Target Release:** v0.next  

---

## Summary

Unify Bengal's fragmented template context system into a single, cohesive architecture. This RFC addresses the root cause of template ergonomics issues: **multiple context-building systems that evolved independently and never integrated**.

**Vision:** Hugo's ergonomics + Eleventy's data cascade + Jinja2's familiarity + Python's ecosystem.

Template authors should be able to write `{{ params.author }}` without fear, access `{{ section.pages }}` on any page, and never write `.get()`, `is defined`, or `or {}`. Missing data returns empty, not errors. Configuration cascades naturally from site → section → page.

---

## Why This Approach?

### The Core Problem

Bengal's template context evolved across 5 separate systems that never integrated. The wrappers exist. The core objects are well-designed. They just aren't wired together. **This RFC is primarily a wiring fix, not a rewrite.**

### Why Wrappers (Not Alternatives)?

| Alternative | Why Not |
|-------------|---------|
| **Modify core classes directly** | Pollutes domain objects with template concerns. `Page` shouldn't know about Jinja2 undefined behavior. |
| **Use ChainableUndefined alone** | Only handles missing keys, not missing objects. `section.pages` still fails if `section` is None. |
| **Dict subclasses** | Can't add methods like `theme.has()`. Can't wrap non-dict objects like Section. |
| **Proxy everything at render time** | Already doing this—just inconsistently. This RFC makes it consistent. |

**Wrappers give us:**
- Separation of concerns (core objects stay clean)
- Method additions (`theme.has()`, `section.params`)
- Null-object pattern (`SectionContext(None)` returns safe empties)
- Recursion for nested dicts (`params.social.twitter.handle`)
- Single point of change when template needs evolve

### Performance

**TL;DR: Negligible impact, likely net improvement.**

| Concern | Reality |
|---------|---------|
| Wrapper allocation | ~200 bytes per render. You're already allocating the Jinja2 context dict, template AST, and output buffer. One more small object is noise. |
| `__getattr__` overhead | ~50ns per access. Template renders take 1-10ms. Even 100 attribute accesses add 5μs (0.05% of render time). |
| ChainableUndefined | Creates Undefined objects on miss. But misses are rare in well-written templates—we're optimizing for the happy path. |
| Removing `.get()` calls | **Faster.** Dict `.get()` with default is slightly slower than attribute access on a wrapper with `__getattr__`. |
| Removing `is defined` checks | **Faster.** Jinja2's `is defined` test has overhead. Truthy checks on wrappers are cheaper. |
| Deleting dead code | **Faster.** Removing 100+ lines of manual context building from renderer.py eliminates redundant work. |

**Net effect:** The wrapper overhead is dwarfed by the savings from simplifying the render path and eliminating defensive template patterns.

### Why Now?

1. **The infrastructure exists** — Wrappers are written, just not used
2. **Templates are painful** — 57+ `.get()` calls prove the current DX is broken
3. **Competitive pressure** — Hugo's DX is the benchmark; we're not there yet
4. **Technical debt** — 5 parallel context systems is unsustainable

This RFC turns Bengal's template experience from "powerful but defensive" into "powerful and effortless."

---

## Current State Analysis

### The Problem: Parallel Evolution Without Integration

Bengal has **five separate systems** that build template context:

| System | Location | What It Does | Status |
|--------|----------|--------------|--------|
| Core Objects | `bengal/core/` | Page, Site, Section, Theme | ✅ Well-designed |
| URL Wrappers | `template_context.py` | TemplatePageWrapper for baseurl | ⚠️ Exists, rarely used |
| Safe Access Wrappers | `context.py` | SmartDict, ParamsContext, etc. | ⚠️ Exists, never wired in |
| Renderer Context | `renderer.py` | Ad-hoc dict construction | ❌ Bypasses wrappers |
| Environment Globals | `environment.py` | Raw objects as globals | ❌ Bypasses wrappers |
| Pipeline Context | `pipeline/core.py` | Anonymous class for sections | ❌ Completely separate |

### What Templates Actually Receive

```
┌──────────────────────────────────────────────────────────────┐
│                    CURRENT TEMPLATE CONTEXT                   │
├──────────────────────────────────────────────────────────────┤
│                                                               │
│  From env.globals:     site = raw Site object                │
│                        config = raw dict                     │
│                        theme = raw Theme object              │
│                                                               │
│  From renderer.py:     page = raw Page object                │
│  (ad-hoc dict)         params = raw dict (page.metadata)     │
│                        section = raw Section (conditional)   │
│                        metadata = raw dict                   │
│                                                               │
│  NEVER USED:           build_page_context() from context.py  │
│                        ParamsContext, SectionContext, etc.   │
│                        TemplatePageWrapper for baseurl       │
│                                                               │
└──────────────────────────────────────────────────────────────┘
```

### Why Template Authors Write Defensive Code

Because wrappers aren't consistently used, template authors learned:

```jinja2
{# This sometimes works, sometimes raises UndefinedError #}
{{ params.author }}

{# This ALWAYS works (dicts have .get()) #}
{{ params.get('author', '') }}
```

Result: 57+ instances of `.get()` calls and `is defined` checks in default theme templates.

---

## Proposed Design

### Architecture: Single Source of Truth

```
┌──────────────────────────────────────────────────────────────┐
│                    NEW TEMPLATE CONTEXT                       │
├──────────────────────────────────────────────────────────────┤
│                                                               │
│  ALL contexts flow through: build_page_context()             │
│                                                               │
│  GLOBALS (always available, wrapped for safety):             │
│  ├── site        SiteContext (wraps Site)                   │
│  ├── config      ConfigContext (wraps config dict)          │
│  ├── theme       ThemeContext (wraps Theme)                 │
│  └── bengal      Engine metadata dict                       │
│                                                               │
│  PAGE CONTEXT (per render, all wrapped):                     │
│  ├── page        Page object (raw, properties work)         │
│  ├── params      ParamsContext (wraps page.metadata)        │
│  ├── section     SectionContext (wraps Section or empty)    │
│  ├── content     Markup (safe HTML)                         │
│  ├── toc         Markup (safe HTML)                         │
│  ├── toc_items   list[dict] (structured TOC)                │
│  ├── meta_desc   str (pre-computed)                         │
│  ├── reading_time int (pre-computed)                        │
│  └── excerpt     str (pre-computed)                         │
│                                                               │
│  SPECIALIZED (page-type specific):                           │
│  ├── posts       list[Page] (for indexes)                   │
│  ├── subsections list[Section] (for indexes)                │
│  ├── element     AutodocElement (for autodoc)               │
│  └── tag/tags    Tag data (for tag pages)                   │
│                                                               │
└──────────────────────────────────────────────────────────────┘
```

### Core Principles

1. **One context builder** — All rendering paths use `build_page_context()`
2. **Wrappers everywhere** — No raw dicts in template context
3. **Safe by default** — Missing values return empty, never error
4. **Section always exists** — `SectionContext` with empty fallbacks, no `is defined` checks
5. **ChainableUndefined** — Deep dot-notation access never fails
6. **Data cascade** — Configuration inherits: site → section → page (Eleventy's best idea)

---

## Implementation Plan

### Phase 1: Configure Jinja2 for Safe Access

**File:** `bengal/rendering/template_engine/environment.py`

```python
from jinja2 import ChainableUndefined

env = Environment(
    # ... existing config ...
    undefined=ChainableUndefined,
)

# Add finalize to convert None to empty string
env.finalize = lambda x: '' if x is None else x
```

**Effect:** `{{ params.deeply.nested.missing }}` returns `''` instead of erroring.

**Note:** Remove `strict_mode` option — we commit fully to safe templates.

---

### Phase 2: Wire Wrappers into Environment Globals

**File:** `bengal/rendering/template_engine/environment.py`

```python
from bengal.rendering.context import SiteContext, ThemeContext, ConfigContext

# Replace raw objects with wrapped versions
env.globals["site"] = SiteContext(site)
env.globals["config"] = ConfigContext(site.config)
env.globals["theme"] = ThemeContext(site.theme_config)
```

---

### Phase 3: Make Renderer Use build_page_context()

**File:** `bengal/rendering/renderer.py`

Replace the ad-hoc context building:

```python
# BEFORE (lines 165-178):
context = {
    "page": page,
    "content": Markup(content),
    "title": page.title,
    "metadata": page.metadata,
    "params": page.metadata,  # Raw dict!
    ...
}

# AFTER:
from bengal.rendering.context import build_page_context

context = build_page_context(
    page=page,
    site=self.site,
    content=content,
    section=getattr(page, '_section', None),
)
```

Delete all the manual context construction code (~100 lines).

---

### Phase 4: Add site.params Property

**File:** `bengal/core/site/properties.py`

```python
@property
def params(self) -> dict[str, Any]:
    """
    Site-level custom parameters from [params] config section.

    Example config:
        [params]
        repo_url = "https://github.com/org/repo"
        author = "Jane Doe"

    Template usage:
        {{ site.params.repo_url }}
        {{ site.params.author }}
    """
    return self.config.get('params', {})

@property
def logo(self) -> str:
    """Logo URL from config (checks multiple locations)."""
    cfg = self.config
    return (
        cfg.get('logo_image', '') or
        cfg.get('site', {}).get('logo_image', '') or
        ''
    )
```

---

### Phase 5: Enhance Wrapper Classes

**File:** `bengal/rendering/context.py`

#### ParamsContext — Add recursive SmartDict wrapping

```python
class ParamsContext:
    """Safe access to page frontmatter with nested dict support."""

    def __init__(self, metadata: dict[str, Any] | None):
        self._data = metadata or {}

    def __getattr__(self, name: str) -> Any:
        if name.startswith('_'):
            return object.__getattribute__(self, name)

        value = self._data.get(name)

        # Recursively wrap nested dicts
        if isinstance(value, dict):
            return ParamsContext(value)

        # Return empty string for missing/None, preserving other falsy values
        if value is None:
            return ''
        return value

    def __getitem__(self, key: str) -> Any:
        return self.__getattr__(key)

    def get(self, key: str, default: Any = '') -> Any:
        value = self._data.get(key)
        return default if value is None else value

    def __contains__(self, key: str) -> bool:
        return key in self._data

    def __bool__(self) -> bool:
        return bool(self._data)

    def __iter__(self):
        return iter(self._data)

    def keys(self):
        return self._data.keys()

    def values(self):
        return self._data.values()

    def items(self):
        return self._data.items()
```

#### SectionContext — Always safe, never None

```python
class SectionContext:
    """
    Safe wrapper for Section. Returns empty values when no section exists.

    Template authors can always write {{ section.title }} without checks.
    """

    def __init__(self, section: Section | None):
        self._section = section

    @property
    def title(self) -> str:
        return getattr(self._section, 'title', '') or '' if self._section else ''

    @property
    def name(self) -> str:
        return getattr(self._section, 'name', '') or '' if self._section else ''

    @property
    def path(self) -> str:
        return str(getattr(self._section, 'path', '') or '') if self._section else ''

    @property
    def href(self) -> str:
        return getattr(self._section, '_path', '') or '' if self._section else ''

    @property
    def pages(self) -> list:
        return getattr(self._section, 'pages', []) or [] if self._section else []

    @property
    def subsections(self) -> list:
        return getattr(self._section, 'subsections', []) or [] if self._section else []

    @property
    def params(self) -> ParamsContext:
        """Section metadata as ParamsContext for safe access."""
        if self._section and hasattr(self._section, 'metadata'):
            return ParamsContext(self._section.metadata)
        return ParamsContext({})

    def __bool__(self) -> bool:
        """Returns True if a real section exists."""
        return self._section is not None

    def __getattr__(self, name: str) -> Any:
        if name.startswith('_'):
            return object.__getattribute__(self, name)
        if self._section is None:
            return ''
        return getattr(self._section, name, '')
```

#### ThemeContext — Add convenience methods

```python
class ThemeContext:
    """Safe access to theme configuration."""

    def __init__(self, theme: Theme):
        self._theme = theme

    @property
    def name(self) -> str:
        return self._theme.name or 'default'

    @property
    def appearance(self) -> str:
        return self._theme.default_appearance or 'system'

    @property
    def palette(self) -> str:
        return self._theme.default_palette or ''

    @property
    def features(self) -> list[str]:
        return self._theme.features or []

    @property
    def config(self) -> ParamsContext:
        """Theme config as ParamsContext for safe nested access."""
        return ParamsContext(self._theme.config or {})

    def has(self, feature: str) -> bool:
        """Check if feature flag is enabled."""
        return feature in (self._theme.features or [])

    def get(self, key: str, default: Any = '') -> Any:
        """Get theme config value with default."""
        if self._theme.config:
            return self._theme.config.get(key, default)
        return default

    def __getattr__(self, name: str) -> Any:
        if name.startswith('_'):
            return object.__getattribute__(self, name)

        # Check theme properties first
        if hasattr(self._theme, name):
            val = getattr(self._theme, name)
            if val is not None:
                return val

        # Fall back to theme.config
        return self.get(name, '')
```

---

### Phase 6: Update build_page_context()

**File:** `bengal/rendering/context.py`

```python
def build_page_context(
    page: Page | SimpleNamespace,
    site: Site,
    content: str = '',
    *,
    section: Section | None = None,
    element: Any = None,
    posts: list | None = None,
    subsections: list | None = None,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Build complete template context for any page type.

    This is the SINGLE SOURCE OF TRUTH for all template contexts.
    All rendering paths must use this function.

    Args:
        page: Page object or SimpleNamespace (synthetic pages)
        site: Site instance
        content: Rendered HTML content
        section: Section override (defaults to page._section)
        element: Autodoc element (for autodoc pages)
        posts: Override posts list (for generated pages)
        subsections: Override subsections list
        extra: Additional context variables

    Returns:
        Complete template context with all wrappers applied
    """
    # Get metadata
    metadata = getattr(page, 'metadata', {}) or {}

    # Resolve section (from arg, page attribute, or None)
    resolved_section = section
    if resolved_section is None:
        resolved_section = getattr(page, '_section', None)

    # Build context with wrappers
    context: dict[str, Any] = {
        # Globals (wrapped)
        'site': SiteContext(site),
        'config': ConfigContext(site.config),
        'theme': ThemeContext(site.theme_config) if site.theme_config else ThemeContext._empty(),

        # Page context (wrapped where needed)
        'page': page,
        'params': ParamsContext(metadata),
        'section': SectionContext(resolved_section),

        # Pre-computed content (safe HTML)
        'content': Markup(content) if content else Markup(''),
        'title': getattr(page, 'title', '') or '',
        'toc': Markup(getattr(page, 'toc', '') or ''),
        'toc_items': getattr(page, 'toc_items', []) or [],

        # Pre-computed metadata
        'meta_desc': getattr(page, 'meta_description', '') or '',
        'reading_time': getattr(page, 'reading_time', 0) or 0,
        'excerpt': getattr(page, 'excerpt', '') or '',

        # Versioning defaults
        'current_version': None,
        'is_latest_version': True,
    }

    # Add section content lists
    if resolved_section:
        context['posts'] = posts if posts is not None else getattr(resolved_section, 'pages', [])
        context['pages'] = context['posts']  # Alias
        context['subsections'] = subsections if subsections is not None else getattr(resolved_section, 'subsections', [])
    else:
        context['posts'] = posts or []
        context['pages'] = context['posts']
        context['subsections'] = subsections or []

    # Add autodoc element
    if element:
        context['element'] = element

    # Add versioning context
    if site.versioning_enabled and hasattr(page, 'version') and page.version:
        version_obj = site.get_version(page.version)
        if version_obj:
            context['current_version'] = version_obj.to_dict()
            context['is_latest_version'] = version_obj.latest

    # Merge extra context
    if extra:
        context.update(extra)

    return context
```

---

### Phase 7: Delete Dead Code

**Remove from `context.py`:**
- `SmartDict` class (replaced by ParamsContext recursive wrapping)

**Remove from `renderer.py`:**
- All manual context dict construction (lines 165-268)
- `_add_generated_page_context()` method
- All the conditional section handling

**Remove from `pipeline/core.py`:**
- `_build_variable_context()` anonymous class creation
- Replace with call to `build_page_context()`

**Remove from `environment.py`:**
- `strict_mode` handling (we're always safe now)

---

### Phase 8: Implement Data Cascade

**Concept:** Configuration should flow down: `site.params` → `section.params` → `page.params`

When a page accesses `params.author`, Bengal should check:
1. Page frontmatter (`author: Jane`)
2. Section `_index.md` frontmatter (`author: Team Blog`)
3. Site `bengal.toml` `[params]` (`author: Default Author`)

**File:** `bengal/rendering/context.py`

```python
class CascadingParamsContext:
    """
    Params with inheritance: page → section → site.

    Access {{ params.author }} and get the most specific value defined.
    """

    def __init__(
        self,
        page_params: dict[str, Any],
        section_params: dict[str, Any] | None = None,
        site_params: dict[str, Any] | None = None,
    ):
        self._page = page_params or {}
        self._section = section_params or {}
        self._site = site_params or {}

    def __getattr__(self, name: str) -> Any:
        if name.startswith('_'):
            return object.__getattribute__(self, name)

        # Check page first (most specific)
        if name in self._page:
            value = self._page[name]
            if isinstance(value, dict):
                return CascadingParamsContext(
                    value,
                    self._section.get(name, {}),
                    self._site.get(name, {}),
                )
            return value

        # Then section
        if name in self._section:
            value = self._section[name]
            if isinstance(value, dict):
                return CascadingParamsContext(
                    {},
                    value,
                    self._site.get(name, {}),
                )
            return value

        # Finally site
        if name in self._site:
            value = self._site[name]
            if isinstance(value, dict):
                return CascadingParamsContext({}, {}, value)
            return value

        # Not found anywhere
        return ''

    def __contains__(self, key: str) -> bool:
        return key in self._page or key in self._section or key in self._site

    def __bool__(self) -> bool:
        return bool(self._page) or bool(self._section) or bool(self._site)
```

**Usage in templates:**

```jinja2
{# bengal.toml #}
{# [params] #}
{# company = "Acme Corp" #}

{# blog/_index.md #}
{# --- #}
{# params: #}
{#   author: Blog Team #}
{# --- #}

{# blog/post.md #}
{# --- #}
{# author: Jane Doe #}
{# --- #}

{{ params.author }}   {# → "Jane Doe" (page) #}
{{ params.company }}  {# → "Acme Corp" (cascaded from site) #}
```

**Update `build_page_context()` to use cascading:**

```python
# In build_page_context():
section_params = {}
if resolved_section and hasattr(resolved_section, 'metadata'):
    section_params = resolved_section.metadata or {}

site_params = site.config.get('params', {})

context['params'] = CascadingParamsContext(
    page_params=metadata,
    section_params=section_params,
    site_params=site_params,
)
```

---

### Phase 9: Update All Templates

#### Pattern Migrations

| Before | After |
|--------|-------|
| `params.get('author')` | `params.author` |
| `params.get('image', '')` | `params.image` |
| `config.get('title')` | `config.title` |
| `config.get('i18n', {}).get('strategy')` | `config.i18n.strategy` |
| `theme.config.get('hero_style')` | `theme.hero_style` or `theme.get('hero_style')` |
| `site.config.get('params', {}).get('repo_url')` | `site.params.repo_url` |
| `{% if section is defined and section %}` | `{% if section %}` |
| `{% if page is defined and page %}` | Always true, remove check |
| `'feature' in theme.features` | `theme.has('feature')` |

#### Files to Update

All templates in `bengal/themes/default/templates/`:
- `base.html`
- `page.html`
- `section/*.html`
- `partials/*.html`
- `autodoc/**/*.html`

Use find-and-replace with review:
```bash
# Find all .get() patterns
rg "\.get\(" bengal/themes/default/templates/

# Find all "is defined" patterns
rg "is defined" bengal/themes/default/templates/

# Find all "or {}" patterns  
rg "or \{\}" bengal/themes/default/templates/
```

---

## Template Developer Guide

### The New Mental Model

```jinja2
{# GLOBALS - always available, always safe #}
{{ site.title }}              {# Site title #}
{{ site.params.repo_url }}    {# Custom site params #}
{{ config.baseurl }}          {# Raw config access #}
{{ theme.appearance }}        {# Theme setting #}
{{ theme.has('navigation.toc') }}  {# Feature check #}

{# PAGE - current page being rendered #}
{{ page.title }}              {# Page title #}
{{ page.href }}               {# Page URL (with baseurl) #}
{{ page.date }}               {# Page date #}
{{ params.author }}           {# Page frontmatter #}
{{ params.custom.nested }}    {# Deep access is safe #}

{# SECTION - always exists (empty if no section) #}
{{ section.title }}           {# Section title ('' if none) #}
{{ section.name }}            {# Section name ('' if none) #}
{% if section %}              {# Check if real section exists #}
{% for post in section.pages %}

{# CONTENT - pre-rendered, safe HTML #}
{{ content }}                 {# Page content #}
{{ toc }}                     {# Table of contents #}
```

### Safe Patterns

```jinja2
{# Deep access - never errors #}
{{ params.social.twitter.handle }}

{# Conditionals - use truthiness #}
{% if params.author %}
  By {{ params.author }}
{% endif %}

{# Defaults - use Jinja2 default filter #}
{{ params.layout | default('single') }}

{# Feature flags #}
{% if theme.has('content.reading_time') %}
  {{ reading_time }} min read
{% endif %}

{# Section iteration - always safe #}
{% for post in posts %}
  {{ post.title }}
{% endfor %}
```

### What You Never Need

```jinja2
{# NEVER write this anymore: #}
{% if params is defined %}                    {# params always exists #}
{{ params.get('author', '') }}                {# just use params.author #}
{% set x = (config.i18n or {}).get('foo') %}  {# just use config.i18n.foo #}
{% if section is defined and section %}       {# just use {% if section %} #}
```

---

## Files Changed Summary

| File | Change |
|------|--------|
| `bengal/rendering/template_engine/environment.py` | ChainableUndefined, wrapped globals |
| `bengal/rendering/context.py` | Enhanced wrappers, simplified build_page_context |
| `bengal/rendering/renderer.py` | Use build_page_context(), delete manual building |
| `bengal/rendering/pipeline/core.py` | Use build_page_context() for variable context |
| `bengal/core/site/properties.py` | Add `params`, `logo` properties |
| `bengal/themes/default/templates/**` | Remove all defensive patterns |

---

## Testing Plan

1. **Unit tests** for wrapper classes
   - ParamsContext nested access
   - SectionContext empty state
   - ThemeContext.has() method

2. **Integration tests** for build_page_context()
   - Regular pages
   - Section index pages
   - Generated pages (tags, archives)
   - Autodoc pages
   - Special pages (404, search)

3. **Template rendering tests**
   - Every template renders without error
   - Verify expected output for key patterns

4. **Smoke test**
   - Build Bengal docs site
   - Build example sites
   - Visual inspection

---

## Timeline

| Phase | Duration | Description |
|-------|----------|-------------|
| 1 | 2 hours | Jinja2 ChainableUndefined config |
| 2 | 2 hours | Wire wrappers into environment globals |
| 3 | 4 hours | Renderer uses build_page_context() |
| 4 | 1 hour | Add site.params property |
| 5 | 4 hours | Enhance wrapper classes |
| 6 | 2 hours | Update build_page_context() |
| 7 | 2 hours | Delete dead code |
| 8 | 4 hours | Implement data cascade (CascadingParamsContext) |
| 9 | 8 hours | Update all templates |

**Total:** ~4 days focused work

---

## Success Criteria

After this RFC is implemented:

- [ ] Zero `.get()` calls in default theme templates
- [ ] Zero `is defined` checks in default theme templates  
- [ ] Zero `or {}` patterns in default theme templates
- [ ] All templates use dot notation for access
- [ ] `section` is always available (as SectionContext)
- [ ] `params` is always available (as CascadingParamsContext)
- [ ] Deep access like `params.a.b.c` never errors
- [ ] Data cascade works: site → section → page inheritance
- [ ] Template authors guide documents new patterns
- [ ] All existing sites build successfully
- [ ] Competitive advantage documented: beat Hugo DX, match Eleventy data model

---

## Appendix: Hugo Comparison (Final State)

| Concept | Hugo | Bengal |
|---------|------|--------|
| Site title | `.Site.Title` | `site.title` |
| Site params | `.Site.Params.key` | `site.params.key` |
| Page title | `.Page.Title` | `page.title` |
| Page params | `.Params.key` | `params.key` |
| Section name | `.Section` | `section.name` |
| Section title | N/A | `section.title` |
| Content | `.Content` | `content` |
| Safe access | `{{ with .Params.x }}` | `{% if params.x %}` |
| Default value | `{{ .Params.x \| default "y" }}` | `{{ params.x \| default('y') }}` |
| Feature flag | N/A | `theme.has('feature')` |
| Theme config | N/A | `theme.get('key')` or `theme.key` |

Bengal matches Hugo's ergonomics while adding theme-specific conveniences.

---

## Appendix: Competitive Analysis — Templating Developer Experience

### Overview

This analysis examines the templating DX of major static site generators to identify pain points Bengal can avoid and opportunities to differentiate.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    TEMPLATING DX LANDSCAPE                                   │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  DOCUMENTATION-FOCUSED           GENERAL-PURPOSE           MODERN/JS-BASED  │
│  ├── Sphinx (RST/Jinja2)         ├── Hugo (Go)             ├── Astro        │
│  ├── MkDocs (Jinja2)             ├── Jekyll (Liquid)       ├── Docusaurus   │
│  └── Bengal (Jinja2) ←           └── Eleventy (Multi)      └── Next.js      │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

### 1. Hugo (Go Templates)

**The Gold Standard for SSG Templating**

Hugo is the benchmark Bengal aims to match. Its `.Params` and `.Site` conventions are industry-defining.

#### Strengths We Should Match

| Hugo Feature | What Makes It Great | Bengal Equivalent |
|--------------|---------------------|-------------------|
| `.Site.Title` | Always works, never undefined | `site.title` |
| `.Params.key` | Page frontmatter, safe access | `params.key` |
| `.Section` | Current section name | `section.name` |
| `with` blocks | Scoped nil-safe access | `{% if params.x %}` |
| `default` function | `{{ .Params.x \| default "y" }}` | `{{ params.x \| default('y') }}` |

#### Hugo Pain Points We Can Beat

| Pain Point | Description | Bengal Advantage |
|------------|-------------|------------------|
| **Go Template Syntax** | Unfamiliar to most devs. `{{ range }}`, `{{ end }}`, `{{ .Scratch }}` | Jinja2 is Python-like, widely known |
| **Cryptic Error Messages** | `can't evaluate field X in type Y` | Clear Jinja2 tracebacks with line numbers |
| **No IDE Support** | Go templates have poor editor tooling | Jinja2 has excellent VSCode/PyCharm support |
| **Scratch Pad Anti-Pattern** | Need `.Scratch.Set`/`.Get` for variables across scopes | Jinja2 `{% set %}` is straightforward |
| **Partial Context** | Must explicitly pass variables to partials | Jinja2 inherits parent scope, `{% include %}` with context |
| **Nested Conditionals** | `{{ with .Params.x }}{{ with .y }}` nesting hell | `params.x.y` works directly |

#### Hugo Template (Verbose)
```go-html-template
{{ with .Params.author }}
  {{ with .name }}
    <span>{{ . }}</span>
  {{ end }}
{{ end }}
{{ if isset .Params "image" }}
  <img src="{{ .Params.image }}">
{{ end }}
```

#### Bengal Template (Clean)
```jinja2
{% if params.author.name %}
  <span>{{ params.author.name }}</span>
{% endif %}
{% if params.image %}
  <img src="{{ params.image }}">
{% endif %}
```

---

### 2. Sphinx (RST + Jinja2)

**The Documentation Powerhouse with Legacy Baggage**

#### Strengths

- Exceptional cross-referencing (`:ref:`, `:doc:`, `:func:`)
- Multiple output formats (HTML, PDF, ePub)
- Mature extension ecosystem
- Autodoc from Python docstrings

#### Pain Points We Can Beat

| Pain Point | Description | Bengal Advantage |
|------------|-------------|------------------|
| **RST Learning Curve** | reStructuredText is verbose and unfamiliar | Markdown-first with RST features via directives |
| **Theme Complexity** | `conf.py` + `_templates/` + inheritance = confusion | Single `bengal.toml` + clear template hierarchy |
| **Extension Hell** | Need extensions for basic features (Markdown, tabs) | Batteries included, extensions for advanced only |
| **Template Context** | Must dig through Sphinx internals to find variables | Documented context with type hints |
| **Build Speed** | Large sites are slow (Python overhead) | Parallel rendering, caching, incremental builds |
| **Jinja2 Partial Access** | Only theme templates use Jinja2, content uses RST | Jinja2 everywhere (templates + content via `{{ }}`) |

#### Sphinx Template Context Access
```jinja2
{# Sphinx: Must know internal variable names #}
{{ pagename }}
{{ toctree() }}
{{ theme_analytics_id }}
{{ config.html_theme_options.get('repo_url', '') }}
```

#### Bengal Template Context Access
```jinja2
{# Bengal: Intuitive hierarchy #}
{{ page.title }}
{{ toc }}
{{ theme.analytics_id }}
{{ site.params.repo_url }}
```

---

### 3. MkDocs (Jinja2)

**Simple and Accessible, But Limited**

MkDocs is Bengal's closest comparison — both use Jinja2 and target documentation.

#### Strengths

- Simple `mkdocs.yml` configuration
- Material for MkDocs is beautiful
- Low barrier to entry
- Good plugin ecosystem for docs

#### Pain Points We Can Beat

| Pain Point | Description | Bengal Advantage |
|------------|-------------|------------------|
| **Flat Page Structure** | No true sections/hierarchy in context | First-class `Section` objects with nesting |
| **Limited Frontmatter** | Basic YAML, no computed properties | Rich `Page` object with `reading_time`, `excerpt`, etc. |
| **Plugin for Everything** | Versioning, search, tabs all need plugins | Built-in versioning, search, components |
| **No Page Relationships** | No `prev`/`next`, no related pages | `page.prev`, `page.next`, `page.related_posts` |
| **Theme Lock-in** | Material is great but tightly coupled | Modular theme system, easy overrides |
| **Template Context Poverty** | Limited variables available | Rich context with `site`, `page`, `section`, `params` |

#### MkDocs Theme Template
```jinja2
{# MkDocs: Limited context #}
{{ page.title }}
{{ page.meta.author }}  {# Must check if exists #}
{{ config.site_name }}
{{ config.extra.repo_url }}  {# Deep nesting required #}
```

#### Bengal Theme Template
```jinja2
{# Bengal: Rich context #}
{{ page.title }}
{{ params.author }}  {# Always safe #}
{{ site.title }}
{{ site.params.repo_url }}  {# Clean hierarchy #}
```

---

### 4. Docusaurus (React/MDX)

**Modern and Powerful, But High Barrier**

#### Strengths

- React component ecosystem
- Built-in versioning and i18n
- Excellent search (Algolia integration)
- Modern build tooling

#### Pain Points We Can Beat

| Pain Point | Description | Bengal Advantage |
|------------|-------------|------------------|
| **React Required** | Must know JSX, components, hooks | Jinja2 requires no JS knowledge |
| **MDX Complexity** | Mixing Markdown and JSX is error-prone | Clean Markdown + directives separation |
| **Node.js Tooling** | `node_modules`, build times, npm issues | Pure Python, simple `pip install` |
| **Component Prop Drilling** | Must pass props through component tree | Template inheritance with automatic context |
| **Config Sprawl** | `docusaurus.config.js` is complex | Single `bengal.toml` |
| **Customization Cliff** | Easy until you need custom, then steep | Gradual customization curve |

#### Docusaurus Component
```jsx
// Docusaurus: Must create React component
import {useDoc} from '@docusaurus/theme-common';

export default function AuthorDisplay() {
  const {metadata} = useDoc();
  const author = metadata.frontMatter?.author;

  if (!author) return null;
  return <span className="author">{author}</span>;
}
```

#### Bengal Template
```jinja2
{# Bengal: Just template it #}
{% if params.author %}
  <span class="author">{{ params.author }}</span>
{% endif %}
```

---

### 5. Astro

**Modern Architecture, Flexible Framework Support**

#### Strengths

- Zero JS by default (islands architecture)
- Use React/Vue/Svelte components
- Excellent performance
- Modern developer tooling

#### Pain Points We Can Beat

| Pain Point | Description | Bengal Advantage |
|------------|-------------|------------------|
| **Framework Fatigue** | Must choose React vs Vue vs Svelte | One template language (Jinja2) |
| **Astro-Specific Syntax** | `.astro` files are unique | Standard Jinja2, transferable skills |
| **Content Collections Complexity** | Schema definition, Zod validation | Simple frontmatter, automatic inference |
| **Node.js Dependency** | Same issues as Docusaurus | Pure Python |
| **Young Ecosystem** | Fewer themes, plugins, examples | Mature Jinja2 ecosystem |

---

### 6. Jekyll (Liquid)

**The Original SSG, Showing Its Age**

#### Strengths

- GitHub Pages integration
- Large theme ecosystem
- Well-documented
- Simple mental model

#### Pain Points We Can Beat

| Pain Point | Description | Bengal Advantage |
|------------|-------------|------------------|
| **Liquid Limitations** | No functions, limited filters | Jinja2 macros, rich filter library |
| **Ruby Dependency** | Gem management, version conflicts | Python ecosystem, pip/uv |
| **Slow Builds** | Large sites take minutes | Parallel builds, caching |
| **No Type Safety** | Variables silently fail | Wrapper classes with defined behavior |
| **Plugin Complexity** | Ruby gems for basic features | Python extensions, batteries included |

#### Jekyll Liquid (Defensive)
```liquid
{% if page.author %}
  {% if page.author.name %}
    {{ page.author.name }}
  {% endif %}
{% endif %}
{% assign repo = site.repo_url | default: "" %}
```

#### Bengal Jinja2 (Clean)
```jinja2
{{ params.author.name }}
{{ site.params.repo_url }}
```

---

### 7. Eleventy (11ty)

**Data Cascade — The Best Idea We Should Steal**

Eleventy's **Data Cascade** is the gold standard for how configuration should merge.

#### What Eleventy Gets Right

```
┌─────────────────────────────────────────────┐
│           ELEVENTY DATA CASCADE              │
├─────────────────────────────────────────────┤
│                                              │
│  1. Global Data Files (_data/*.json)         │
│       ↓ merged with                          │
│  2. Template/Directory Data Files            │
│       ↓ merged with                          │
│  3. Front Matter                             │
│       ↓ merged with                          │
│  4. Layout Front Matter                      │
│       ↓ = Final Page Data                    │
│                                              │
└─────────────────────────────────────────────┘
```

**Bengal should adopt this cascade pattern:**

```
┌─────────────────────────────────────────────┐
│            BENGAL DATA CASCADE               │
├─────────────────────────────────────────────┤
│                                              │
│  1. bengal.toml [params]                     │
│       ↓ merged with                          │
│  2. Section _index.md frontmatter            │
│       ↓ merged with                          │
│  3. Page frontmatter                         │
│       = params (with inheritance)            │
│                                              │
│  Access anywhere:                            │
│    {{ params.inherited_value }}              │
│    {{ params.page_override }}                │
│                                              │
└─────────────────────────────────────────────┘
```

#### Eleventy Pain Points

| Pain Point | Description | Bengal Advantage |
|------------|-------------|------------------|
| **Multiple Template Languages** | Choose between Nunjucks, Liquid, Handlebars, etc. | One language: Jinja2 |
| **Config Complexity** | `.eleventy.js` can become sprawling | Declarative `bengal.toml` |
| **JavaScript Required** | Custom filters/shortcodes need JS | Python extensions |
| **No Built-in Theme System** | Roll your own or use starter | First-class theme inheritance |

---

### Competitive Matrix

| Feature | Hugo | Sphinx | MkDocs | Docusaurus | Astro | Jekyll | 11ty | **Bengal** |
|---------|------|--------|--------|------------|-------|--------|------|------------|
| **Safe Dot Access** | ✅ | ❌ | ❌ | N/A | N/A | ❌ | ⚠️ | ✅ |
| **Section Objects** | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ |
| **Template Language** | Go | Jinja2 | Jinja2 | JSX | Astro | Liquid | Multi | Jinja2 |
| **Learning Curve** | High | High | Low | High | Med | Low | Med | **Low** |
| **Error Messages** | Poor | Good | Good | Good | Good | Poor | Good | **Good** |
| **IDE Support** | Poor | Good | Good | Great | Good | Poor | Varies | **Good** |
| **Data Cascade** | ⚠️ | ❌ | ❌ | ❌ | ⚠️ | ❌ | ✅ | **✅** |
| **Theme System** | ✅ | ⚠️ | ⚠️ | ⚠️ | ❌ | ✅ | ❌ | **✅** |
| **Built-in Features** | Many | Many | Few | Many | Few | Few | Few | **Many** |
| **Pure Python** | ❌ | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | **✅** |

---

### Bengal's Unique Advantages

Based on this analysis, Bengal should emphasize:

#### 1. **Safe Access Without Ceremony**
No other Jinja2-based SSG provides truly safe dot-notation. MkDocs and Sphinx require `.get()` everywhere.

```jinja2
{# Only Bengal: #}
{{ params.social.twitter.handle }}  {# Never errors, returns '' #}
```

#### 2. **First-Class Section Objects**
Hugo has sections, but no one else does. Bengal's `Section` with `pages`, `subsections`, `params` is unique.

```jinja2
{# Only Bengal: #}
{% for post in section.pages %}
  {{ post.title }} by {{ post.params.author }}
{% endfor %}
```

#### 3. **Python-Native with Modern Tooling**
Unlike Node.js SSGs (Docusaurus, Astro, 11ty), Bengal uses pure Python with `pip`/`uv`. Unlike Ruby (Jekyll), it's fast and type-safe.

#### 4. **Eleventy's Data Cascade, Hugo's DX**
Combine the best of both: inherited configuration that merges intuitively, with Hugo's clean access patterns.

#### 5. **Documentation-First, Not Documentation-Only**
Unlike Sphinx/MkDocs (docs-only) or Hugo (general-purpose), Bengal is optimized for technical documentation but flexible enough for blogs, marketing, and more.

---

### Implementation Priorities from Competitive Analysis

| Priority | Feature | Why |
|----------|---------|-----|
| **P0** | Safe dot-notation access | Differentiator vs MkDocs/Sphinx |
| **P0** | Section always available | Differentiator vs all except Hugo |
| **P1** | Data cascade (params inheritance) | Match Eleventy's best feature |
| **P1** | Clear error messages | Beat Hugo, match modern SSGs |
| **P2** | Theme composition | Beat Jekyll/Hugo's flat themes |
| **P2** | IDE integration docs | Help adoption |

---

### What Others Do Poorly (Avoid These)

1. **Hugo**: Cryptic Go template errors, `.Scratch` workarounds
2. **Sphinx**: RST verbosity, extension dependency hell
3. **MkDocs**: Limited context, plugin for everything
4. **Docusaurus**: React requirement, MDX complexity
5. **Astro**: Framework choice paralysis, `.astro` learning curve
6. **Jekyll**: Liquid limitations, Ruby dependency management
7. **Eleventy**: Multiple template language confusion, no built-in themes

### What Others Do Well (Adopt These)

1. **Hugo**: `.Params`, `.Site`, safe access, sections
2. **Sphinx**: Cross-references, autodoc, multi-format output
3. **MkDocs**: Simple config, Material theme quality
4. **Docusaurus**: Built-in versioning, search, i18n
5. **Astro**: Zero JS default, modern performance
6. **Eleventy**: Data cascade, config inheritance
7. **11ty**: Computed data, flexible data sources

---

### Bengal's Templating Vision

> **"Hugo's ergonomics, Eleventy's data model, Jinja2's familiarity, Python's ecosystem."**

Template authors should be able to:
- Write `{{ params.author }}` without fear
- Access `{{ section.pages }}` on any page
- Never write `.get()`, `is defined`, or `or {}`
- Trust that missing data returns empty, not errors
- Inherit configuration from site → section → page naturally

This RFC delivers that vision.
