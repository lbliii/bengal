# RFC: Engine-Agnostic Template Architecture

**Status**: Ready for Review  
**Created**: 2025-12-25  
**Updated**: 2025-12-25  
**Author**: AI Assistant  
**Effort**: Medium (~3-4 weeks across 4 phases)  
**Impact**: Enables true "bring your own template engine" support  
**Breaking Changes**: Internal API changes only, no user-facing breaks  
**Dependencies**: None (self-contained refactor)

---

## Summary

Bengal's vision is modularity: bring your own renderer, template engine, highlighter. The template engine layer partially delivers on this promise with `TemplateEngineProtocol`, but the implementation leaks Jinja2 assumptions throughout the codebase.

This RFC proposes a clean adapter pattern that:
1. Makes template functions engine-agnostic (pure Python)
2. Moves engine-specific logic into adapter modules
3. Enables themes to work across engines (with documented feature levels)
4. Preserves 100% backward compatibility for existing users

---

## Problem

### The Current State

Bengal defines a clean protocol for template engines:

```python
# bengal/rendering/engines/protocol.py
class TemplateEngineProtocol(Protocol):
    def render_template(self, name: str, context: dict[str, Any]) -> str: ...
    def template_exists(self, name: str) -> bool: ...
    def get_template_path(self, name: str) -> Path | None: ...
    def list_templates(self) -> list[str]: ...
```

But the implementation violates this abstraction in several places:

#### 1. Template Functions Use `@pass_context` (Jinja2-specific)

```python
# bengal/rendering/template_functions/i18n.py
from jinja2 import pass_context

@pass_context  # ← Jinja2-specific decorator!
def t(ctx: Any, key: str, params: dict | None = None, ...) -> str:
    page = ctx.get("page")  # ← Assumes Jinja2 Context object
    return _translate(key, ...)

@pass_context
def current_lang(ctx: Any) -> str | None:
    page = ctx.get("page")
    return _current_lang(site, page)
```

**Impact**: Any non-Jinja2 engine must either:
- Implement Jinja2's `@pass_context` mechanism
- Override all these functions manually (what we did for Kida)

#### 2. Template Functions Use Jinja2 Types in Signatures

```python
# bengal/rendering/template_functions/taxonomies.py
from jinja2 import pass_context

@pass_context
def tag_url_with_site(ctx: Any, tag: str) -> str:
    page = ctx.get("page")  # Jinja2 Context interface
    ...
```

#### 3. Environment Setup Assumes Jinja2

```python
# bengal/rendering/template_engine/environment.py
from jinja2 import pass_context

@pass_context
def asset_url_with_context(ctx: Context, asset_path: str) -> str:
    page = ctx.get("page") if hasattr(ctx, "get") else None
    result = template_engine._asset_url(asset_path, page_context=page)
    ...
```

#### 4. Themes Use Jinja2-Specific Syntax

```jinja2
{# bengal/themes/default/templates/partials/content-components.html #}
{% set ns = namespace(value='') %}
{% for item in items %}
    {% set ns.value = item.group %}  {# ← Namespace mutation, not portable! #}
{% endfor %}
```

### The Coupling Diagram

```
┌─────────────────────────────────────────────────────────────────────────┐
│                          CURRENT ARCHITECTURE                            │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  TemplateEngineProtocol (clean)                                         │
│          │                                                               │
│          ▼                                                               │
│  ┌─────────────────┐     ┌──────────────────────────────────────────┐  │
│  │ JinjaTemplate   │◄────│ template_functions/* (Jinja2-coupled!)   │  │
│  │ Engine          │     │ @pass_context, Context.get()             │  │
│  └─────────────────┘     └──────────────────────────────────────────┘  │
│          │                         ▲                                    │
│          │                         │                                    │
│  ┌─────────────────┐               │                                    │
│  │ KidaTemplate    │───────────────┘ Must work around Jinja2 coupling  │
│  │ Engine          │                                                    │
│  └─────────────────┘                                                    │
│          │                                                               │
│          ▼                                                               │
│  ┌─────────────────┐                                                    │
│  │ FutureEngine?   │  ← Blocked by Jinja2 assumptions                  │
│  └─────────────────┘                                                    │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

### Symptoms Encountered

When implementing Kida (a Jinja2-compatible engine), we hit these walls:

| Issue | Root Cause | Workaround |
|-------|------------|------------|
| `@pass_context` functions fail | Kida doesn't implement this decorator | Override 3 functions manually |
| Menu functions not found | Defined in TemplateEngine mixin, not registered | Copy mixin code to Kida engine |
| `asset_url` is None | Added in environment.py with `@pass_context` | Create simplified version |
| Theme templates fail to parse | Use `{% set ns.value = x %}` syntax | Blocked - requires parser changes |

---

## Proposal

### Design Principles

1. **Template functions are pure Python** - no engine-specific decorators
2. **Engines adapt pure functions** to their context mechanism
3. **Themes declare feature requirements** - engines report capabilities
4. **Gradual migration** - existing code continues to work

### Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                          PROPOSED ARCHITECTURE                           │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  ┌───────────────────────────────────────────────────────────────────┐  │
│  │           template_functions/* (Engine-Agnostic)                   │  │
│  │                                                                     │  │
│  │   def translate(site, key, lang=None) -> str                       │  │
│  │   def current_language(site, page=None) -> str                     │  │
│  │   def tag_url(tag, site, page=None) -> str                         │  │
│  │   def asset_url(path, site, page=None) -> str                      │  │
│  │                                                                     │  │
│  │   # Pure functions - no @pass_context, no Context objects          │  │
│  └───────────────────────────────────────────────────────────────────┘  │
│                              │                                           │
│                              ▼                                           │
│  ┌───────────────────────────────────────────────────────────────────┐  │
│  │                     Engine Adapter Layer                           │  │
│  │                                                                     │  │
│  │  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────────┐ │  │
│  │  │ jinja_adapter   │  │ kida_adapter    │  │ mustache_adapter    │ │  │
│  │  │                 │  │                 │  │                     │ │  │
│  │  │ @pass_context   │  │ (direct call)   │  │ (lambda helper)     │ │  │
│  │  │ def t(ctx, key):│  │ def t(key):     │  │ "t": lambda k: ...  │ │  │
│  │  │   page=ctx.get  │  │   return trans  │  │                     │ │  │
│  │  │   return trans  │  │                 │  │                     │ │  │
│  │  └─────────────────┘  └─────────────────┘  └─────────────────────┘ │  │
│  └───────────────────────────────────────────────────────────────────┘  │
│                              │                                           │
│                              ▼                                           │
│  ┌───────────────────────────────────────────────────────────────────┐  │
│  │                    Template Engine Instances                       │  │
│  │                                                                     │  │
│  │  JinjaTemplateEngine    KidaTemplateEngine    MustacheEngine       │  │
│  └───────────────────────────────────────────────────────────────────┘  │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

### Concrete Changes

#### 1. Refactor Template Functions to Pure Python

**Before** (Jinja2-coupled):

```python
# bengal/rendering/template_functions/i18n.py
from jinja2 import pass_context

@pass_context
def t(ctx: Any, key: str, params: dict | None = None, lang: str | None = None) -> str:
    page = ctx.get("page") if hasattr(ctx, "get") else None
    use_lang = lang or getattr(page, "lang", None)
    return _translate(key, params=params, lang=use_lang)

@pass_context
def current_lang(ctx: Any) -> str | None:
    page = ctx.get("page") if hasattr(ctx, "get") else None
    return _current_lang(site, page)
```

**After** (engine-agnostic):

```python
# bengal/rendering/template_functions/i18n.py

# Pure functions - no Jinja2 imports
def translate(site: Site, key: str, params: dict | None = None,
              lang: str | None = None, page: Page | None = None) -> str:
    """Translate a key to the appropriate language.

    Args:
        site: Site instance for i18n config
        key: Translation key
        params: Interpolation parameters
        lang: Override language (default: page language or site default)
        page: Page context for language detection
    """
    use_lang = lang or getattr(page, "lang", None) or _default_lang(site)
    return _translate(key, params=params, lang=use_lang)

def current_language(site: Site, page: Page | None = None) -> str | None:
    """Get current language from page or site default."""
    return getattr(page, "lang", None) or _default_lang(site)
```

#### 2. Create Engine Adapter Layer

```python
# bengal/rendering/adapters/jinja.py
"""Jinja2-specific adapter for template functions."""

from jinja2 import pass_context
from bengal.rendering.template_functions import i18n, taxonomies, seo

def register_with_jinja(env, site):
    """Register template functions adapted for Jinja2's @pass_context."""

    @pass_context
    def t(ctx, key, params=None, lang=None, default=None):
        page = ctx.get("page") if hasattr(ctx, "get") else None
        return i18n.translate(site, key, params, lang, page, default)

    @pass_context
    def current_lang(ctx):
        page = ctx.get("page") if hasattr(ctx, "get") else None
        return i18n.current_language(site, page)

    @pass_context
    def tag_url(ctx, tag):
        page = ctx.get("page") if hasattr(ctx, "get") else None
        return taxonomies.tag_url(tag, site, page)

    @pass_context
    def asset_url(ctx, path):
        page = ctx.get("page") if hasattr(ctx, "get") else None
        return seo.asset_url(path, site, page)

    env.globals.update({
        "t": t,
        "current_lang": current_lang,
        "tag_url": tag_url,
        "asset_url": asset_url,
    })
```

```python
# bengal/rendering/adapters/kida.py
"""Kida-specific adapter for template functions."""

from bengal.rendering.template_functions import i18n, taxonomies, seo

def register_with_kida(env, site):
    """Register template functions for Kida.

    Strategy: Context-aware function factory

    Since Kida doesn't have @pass_context, we use a two-layer approach:
    1. Static functions registered at environment setup (for simple cases)
    2. Context-aware factory called at render time (for page-dependent functions)
    """

    # Static functions (don't need page context)
    def languages():
        return i18n.languages(site)

    # Context-aware factory - called at render time with page
    def make_page_aware_functions(page):
        """Create functions that have access to the current page.

        Called by KidaTemplateEngine.render_template() before rendering.
        """
        return {
            "t": lambda key, params=None, lang=None, default=None:
                i18n.translate(site, key, params, lang, page, default),
            "current_lang": lambda: i18n.current_language(site, page),
            "tag_url": lambda tag: taxonomies.tag_url(tag, site, page),
            "asset_url": lambda path: seo.asset_url(path, site, page),
        }

    # Register static functions
    env.globals.update({
        "languages": languages,
    })

    # Store factory for render-time injection
    env._page_aware_factory = make_page_aware_functions


def inject_page_context(env, page):
    """Inject page-aware functions into context before rendering.

    Called by KidaTemplateEngine.render_template():

        def render_template(self, name, context):
            from bengal.rendering.adapters.kida import inject_page_context
            page = context.get("page")
            inject_page_context(self._env, page)
            return template.render(context)
    """
    if hasattr(env, "_page_aware_factory"):
        env.globals.update(env._page_aware_factory(page))
```

#### 3. Refactor register_all() to Use Adapters

```python
# bengal/rendering/template_functions/__init__.py

def register_all(env, site, engine_type: str | None = None):
    """Register all template functions with the environment.

    Args:
        env: Template environment (Jinja2, Kida, etc.)
        site: Site instance
        engine_type: Engine type for adapter selection (auto-detected if None)
    """
    from bengal.rendering.adapters import get_adapter_type

    # Auto-detect engine type if not specified
    if engine_type is None:
        engine_type = get_adapter_type(env, site)

    # Register engine-agnostic functions directly
    # (these don't need @pass_context)
    strings.register(env, site)
    collections.register(env, site)
    math_functions.register(env, site)
    dates.register(env, site)
    # ... etc

    # Use adapter for context-dependent functions
    if engine_type == "jinja":
        from bengal.rendering.adapters.jinja import register_context_functions
        register_context_functions(env, site)
    elif engine_type == "kida":
        from bengal.rendering.adapters.kida import register_context_functions
        register_context_functions(env, site)
    else:
        # Unknown engine - register pure functions, user handles context
        from bengal.rendering.adapters.generic import register_context_functions
        register_context_functions(env, site)
```

#### 4. Simplified Kida Engine (After Refactor)

The Kida engine's `_register_bengal_template_functions()` method shrinks from ~90 lines to ~20:

**Before** (current, with manual overrides):

```python
def _register_bengal_template_functions(self) -> None:
    # === Step 1: Register all template functions ===
    register_all(self._env, self.site)

    # === Step 2: Override @pass_context functions ===
    # Kida doesn't support Jinja2's @pass_context decorator...
    base_translate = _make_t(self.site)
    def t_no_ctx(key, params=None, lang=None, default=None):
        return base_translate(key, params=params, lang=lang, default=default)
    self._env.globals["t"] = t_no_ctx
    self._env.globals["current_lang"] = lambda: _current_lang(self.site, None)
    # ... 60+ more lines of overrides ...
```

**After** (with adapter):

```python
def _register_bengal_template_functions(self) -> None:
    """Register Bengal template functions using Kida adapter."""
    self._env.globals["site"] = self.site
    self._env.globals["config"] = self.site.config

    # Single call handles everything including context-dependent functions
    register_all(self._env, self.site)  # Auto-detects "kida" adapter

def render_template(self, name: str, context: dict[str, Any]) -> str:
    """Render template with page-aware context injection."""
    # Inject page context before render
    from bengal.rendering.adapters.kida import inject_page_context
    inject_page_context(self._env, context.get("page"))

    template = self._env.get_template(name)
    return template.render({"site": self.site, "config": self.site.config, **context})
```

#### 4. Theme Feature Levels

Define portable vs engine-specific theme features:

```yaml
# theme.yaml
name: my-theme
version: 1.0.0

engine:
  # Minimum compatibility level
  # Options: "portable" (works everywhere), "jinja2-compatible", "jinja2-only"
  minimum: "jinja2-compatible"

  # Explicit feature declarations (used by compatibility checker)
  features_used:
    # Scoping
    - namespace_mutation        # {% set ns.value = x %}

    # Control flow
    - loop_controls             # {% break %}, {% continue %}

    # Macros
    - macro_with_context        # {% from x import y with context %}

  # Features explicitly NOT used (for documentation)
  features_avoided:
    - expression_statement      # {% do %} - side effects in templates
    - i18n_extension            # {% trans %} - using t() instead
```

```python
# bengal/core/theme/compatibility.py

# Comprehensive feature matrix for all Jinja2-specific constructs
FEATURE_SUPPORT = {
    "jinja": {
        # Scoping & Variables
        "namespace_mutation": True,     # {% set ns.value = x %}
        "scoped_blocks": True,          # {% block x scoped %}

        # Control Flow
        "loop_controls": True,          # {% break %}, {% continue %}
        "recursive_loops": True,        # {% for x in y recursive %}

        # Macros & Imports
        "macro_with_context": True,     # {% from x import y with context %}
        "macro_caller": True,           # {{ caller() }}
        "import_with_context": True,    # {% import x with context %}

        # Expressions
        "expression_statement": True,   # {% do list.append(x) %}
        "inline_if": True,              # {{ x if y else z }}
        "walrus_operator": False,       # := not in Jinja2

        # Extensions
        "i18n_extension": True,         # {% trans %}...{% endtrans %}
        "loop_controls_ext": True,      # Requires extension
        "debug_extension": True,        # {% debug %}
    },
    "kida": {
        # Scoping & Variables
        "namespace_mutation": False,    # Not implemented
        "scoped_blocks": True,

        # Control Flow
        "loop_controls": True,          # Native support
        "recursive_loops": True,

        # Macros & Imports
        "macro_with_context": True,
        "macro_caller": True,
        "import_with_context": True,

        # Expressions
        "expression_statement": True,   # {% do %}
        "inline_if": True,
        "walrus_operator": True,        # Native Python 3.8+

        # Extensions
        "i18n_extension": False,        # Use t() function instead
        "loop_controls_ext": True,      # Native, no extension needed
        "debug_extension": False,
    },
    "generic": {
        # Minimal baseline for unknown engines
        "namespace_mutation": False,
        "scoped_blocks": False,
        "loop_controls": False,
        "recursive_loops": False,
        "macro_with_context": False,
        "macro_caller": False,
        "import_with_context": False,
        "expression_statement": False,
        "inline_if": True,              # Most engines support this
        "walrus_operator": False,
        "i18n_extension": False,
        "loop_controls_ext": False,
        "debug_extension": False,
    },
}


def check_theme_compatibility(theme: Theme, engine: str) -> list[str]:
    """Check if theme is compatible with engine, return missing features."""
    required = theme.config.get("engine", {}).get("features_used", [])
    supported = FEATURE_SUPPORT.get(engine, FEATURE_SUPPORT["generic"])
    return [f for f in required if not supported.get(f, False)]


def get_engine_capabilities(engine: str) -> dict[str, bool]:
    """Get full capability matrix for an engine."""
    return FEATURE_SUPPORT.get(engine, FEATURE_SUPPORT["generic"])
```

---

## Migration Path

### Phase 1: Add Adapter Layer (Non-Breaking)

1. Create `bengal/rendering/adapters/` module
2. Move `@pass_context` wrappers from template functions to adapters
3. Template functions become pure Python internally
4. Existing code continues to work (Jinja adapter is default)

**Effort**: 1 week  
**Risk**: Low (purely additive)

### Phase 2: Refactor Template Functions

1. Remove `@pass_context` from template_functions/*
2. Add `page` parameter to functions that need context
3. Update adapters to pass page from context
4. Update tests

**Effort**: 1 week  
**Risk**: Medium (internal API change)

### Phase 3: Theme Compatibility Layer

1. Add feature declarations to theme.yaml
2. Implement compatibility checker
3. Warn users when theme requires unsupported features
4. Document portable theme guidelines

**Effort**: 1 week  
**Risk**: Low

### Phase 4: Portable Default Theme (Optional)

1. Create portable version of content-components.html
2. Replace namespace mutation with alternative patterns
3. Test with Kida and other engines

**Effort**: 1 week  
**Risk**: Low (opt-in)

---

## Files to Change

### Phase 1: New Files (Adapter Layer)

| File | Purpose | Lines (est.) |
|------|---------|--------------|
| `bengal/rendering/adapters/__init__.py` | Adapter detection, exports | ~50 |
| `bengal/rendering/adapters/jinja.py` | Jinja2 `@pass_context` wrappers | ~80 |
| `bengal/rendering/adapters/kida.py` | Kida context injection | ~100 |
| `bengal/rendering/adapters/generic.py` | Fallback for unknown engines | ~40 |

### Phase 2: Modified Files (Core Refactor)

| File | Change | Risk |
|------|--------|------|
| `bengal/rendering/template_functions/i18n.py` | Remove `@pass_context` from `t()`, `current_lang()` | Medium |
| `bengal/rendering/template_functions/taxonomies.py` | Remove `@pass_context` from `tag_url_with_site()` | Low |
| `bengal/rendering/template_engine/environment.py` | Remove `@pass_context` from `asset_url_with_context()` | Low |
| `bengal/rendering/template_functions/__init__.py` | Add `engine_type` parameter to `register_all()` | Low |
| `bengal/rendering/engines/kida.py` | Use adapter instead of manual overrides (simplifies ~40 lines) | Low |
| `bengal/rendering/engines/jinja.py` | Use adapter for consistency | Low |

### Phase 3: New Files (Compatibility Layer)

| File | Purpose |
|------|---------|
| `bengal/core/theme/compatibility.py` | Feature matrix, compatibility checker |
| `bengal/cli/commands/lint_theme.py` | `bengal lint-theme --portability` command |

### Phase 4: Modified Templates

| Template | Change |
|----------|--------|
| `themes/default/templates/partials/content-components.html` | Replace `namespace()` with `groupby` |
| `themes/default/templates/category-browser.html` | Replace 2× `namespace()` with filters |
| `themes/default/templates/partials/archive-sidebar.html` | Replace `namespace()` with `sum` filter |

---

## Alternatives Considered

### A. Do Nothing / Status Quo

Keep Jinja2 coupling, document that "pluggable" means "Jinja2-compatible engines only."

**Rejected because**: Violates Bengal's modularity promise. Forces every alternative engine to work around the same issues.

### B. Make Kida 100% Jinja2-Compatible

Add every Jinja2 feature (namespace mutation, etc.) to Kida until templates just work.

**Rejected because**:
- Perpetuates bad architecture
- Every new engine faces same burden
- Jinja2 has 17 years of features; full compatibility is a multi-month effort

### C. Different Themes Per Engine

Ship jinja-theme/, kida-theme/, etc.

**Rejected because**:
- Maintenance burden multiplies
- Users with custom themes must maintain multiple versions
- Doesn't solve the template functions coupling

---

## Implementation Notes

### Functions Requiring Adapter Pattern

These functions currently use `@pass_context` and need adapter treatment:

| Function | Module | Context Usage |
|----------|--------|---------------|
| `t()` | i18n | Gets `page.lang` |
| `current_lang()` | i18n | Gets `page.lang` |
| `tag_url()` | taxonomies | Gets `page.lang` for i18n prefix |
| `asset_url()` | seo | Gets `page._path` for relative URLs |

### Functions Already Engine-Agnostic

These functions don't use `@pass_context` and need no changes:

- All string filters (`truncatewords`, `slugify`, etc.)
- All collection filters (`sort_by`, `group_by`, etc.)
- All date filters (`time_ago`, `date_iso`, etc.)
- All math filters (`percentage`, `floor`, etc.)
- Most globals (`icon`, `breadcrumbs`, etc.)

### Template Patterns to Avoid (For Portability)

| Pattern | Issue | Portable Alternative |
|---------|-------|---------------------|
| `{% set ns = namespace() %}` | Jinja2-specific | Use `groupby` filter or pre-process |
| `{% set ns.value = x %}` | Namespace mutation | Use `sum` filter or pass in context |
| `{% do list.append(x) %}` | Side effects in template | Build list in Python |
| `{% set x = caller() %}` | Macro caller | Pass content as parameter |
| `{% trans %}...{% endtrans %}` | i18n extension | Use `{{ t('key') }}` function |
| `{% import x with context %}` | Context propagation | Pass required vars explicitly |

### Portable Alternatives: Concrete Examples

#### Replacing `namespace()` for Group Headers

**Non-portable (Jinja2 only)** — uses namespace mutation:

```jinja2
{% set current_group = namespace(value='') %}
{% for item in items %}
    {% if item.group != current_group.value %}
        <h2>{{ item.group }}</h2>
        {% set current_group.value = item.group %}
    {% endif %}
    <p>{{ item.name }}</p>
{% endfor %}
```

**Portable (all engines)** — use `groupby` filter:

```jinja2
{% for group_name, group_items in items | groupby('group') %}
    <h2>{{ group_name }}</h2>
    {% for item in group_items %}
        <p>{{ item.name }}</p>
    {% endfor %}
{% endfor %}
```

#### Replacing `namespace()` for Counters

**Non-portable**:

```jinja2
{% set total = namespace(count=0) %}
{% for category in categories %}
    {% set total.count = total.count + category.posts | length %}
{% endfor %}
<p>Total: {{ total.count }}</p>
```

**Portable** — use `sum` and `map` filters:

```jinja2
{% set total_count = categories | map(attribute='posts') | map('length') | sum %}
<p>Total: {{ total_count }}</p>
```

#### Replacing `{% trans %}` Blocks

**Non-portable** — requires Jinja2 i18n extension:

```jinja2
{% trans name=user.name %}Hello, {{ name }}!{% endtrans %}
```

**Portable** — use `t()` function (works in all Bengal engines):

```jinja2
{{ t('greeting.hello', {'name': user.name}) }}
```

---

## Success Criteria

### Functional Requirements

1. ✅ **No Jinja2 imports in core functions**: `grep -r "from jinja2" template_functions/` returns only TYPE_CHECKING imports
2. ✅ **Adapter-only integration**: New engines implement `adapters/<engine>.py` (~50 lines), not override individual functions
3. ✅ **Theme compatibility check**: `bengal build` warns before failure if theme requires unsupported features
4. ✅ **100% backward compatible**: All existing tests pass without modification
5. ✅ **Kida parity**: Kida renders default theme identically to Jinja2 (after Phase 4)

### Test Strategy

```python
# tests/rendering/test_adapter_parity.py
"""Verify adapters produce identical output across engines."""

import pytest
from bengal.rendering.adapters import jinja, kida

CONTEXT_DEPENDENT_FUNCTIONS = ["t", "current_lang", "tag_url", "asset_url"]

@pytest.fixture
def site_with_i18n(tmp_site):
    """Site with i18n configured and test translations."""
    ...

@pytest.mark.parametrize("func_name", CONTEXT_DEPENDENT_FUNCTIONS)
def test_adapter_parity(site_with_i18n, func_name):
    """Functions produce same output regardless of adapter."""
    jinja_env = create_jinja_env(site_with_i18n)
    kida_env = create_kida_env(site_with_i18n)

    jinja.register_context_functions(jinja_env, site_with_i18n)
    kida.register_context_functions(kida_env, site_with_i18n)

    # Render same template with both engines
    template = "{{ " + func_name + "(...) }}"
    jinja_result = render_with_jinja(jinja_env, template, context)
    kida_result = render_with_kida(kida_env, template, context)

    assert jinja_result == kida_result

def test_theme_compatibility_warning(site_with_namespace_theme, caplog):
    """Warning emitted when theme uses unsupported features."""
    with pytest.warns(ThemeCompatibilityWarning):
        site_with_namespace_theme.build(engine="kida")

    assert "namespace_mutation" in caplog.text

def test_portable_theme_renders_identically():
    """Portable theme produces identical HTML with both engines."""
    jinja_html = build_site(engine="jinja", theme="portable-default")
    kida_html = build_site(engine="kida", theme="portable-default")

    # Normalize whitespace and compare
    assert normalize(jinja_html) == normalize(kida_html)
```

### Acceptance Checklist

| Phase | Acceptance Criteria | Verification |
|-------|---------------------|--------------|
| Phase 1 | Adapters created, Jinja behavior unchanged | Existing tests pass |
| Phase 2 | Core functions have no `@pass_context` | grep verification |
| Phase 3 | `bengal build` warns on incompatible theme | Integration test |
| Phase 4 | Default theme works with Kida | Render parity test |

---

## Design Decisions

### Decision 1: Adapter Detection Strategy

**Approach**: Auto-detect with config override.

```python
# bengal/rendering/adapters/__init__.py

def detect_adapter_type(env) -> str:
    """Auto-detect engine type from environment class.

    Uses class name inspection as primary detection,
    with explicit config override for edge cases.
    """
    class_name = type(env).__name__.lower()

    if "jinja" in class_name or "environment" == class_name:
        return "jinja"
    elif "kida" in class_name:
        return "kida"
    else:
        return "generic"


def get_adapter_type(env, site) -> str:
    """Get adapter type with config override support.

    Config example:
        rendering:
          adapter: kida  # Explicit override
    """
    # Check for explicit config override
    config_adapter = site.config.get("rendering", {}).get("adapter")
    if config_adapter:
        return config_adapter

    # Auto-detect from environment
    return detect_adapter_type(env)
```

**Rationale**:
- Most users won't need to configure anything (auto-detection works)
- Power users can override when using custom engine implementations
- Simple to implement and maintain

### Decision 2: Context-Dependent Filters

**Approach**: Use render-time context injection for Kida; `@pass_context` for Jinja2.

For Jinja2, `@pass_context` handles this automatically. For engines without this mechanism:

```python
# In engine's render_template():
def render_template(self, name: str, context: dict) -> str:
    page = context.get("page")

    # Inject page-aware functions before render
    from bengal.rendering.adapters.kida import inject_page_context
    inject_page_context(self._env, page)

    template = self._env.get_template(name)
    return template.render(context)
```

**Tradeoff**: Slight overhead per render, but maintains full context access.

### Decision 3: Template Portability Lint

**Approach**: Implement as opt-in CLI command in Phase 3.

```bash
# Check theme for non-portable constructs
bengal lint-theme --portability

# Output:
# ⚠️ content-components.html:281 - namespace() is Jinja2-specific
# ⚠️ category-browser.html:66 - namespace() is Jinja2-specific
# 💡 Consider using accumulator pattern (see docs/themes/portability.md)
```

**Implementation**: Parse templates, pattern-match against known non-portable constructs.

---

## Summary of Benefits

| Stakeholder | Benefit |
|-------------|---------|
| **Engine Authors** | Implement ~50-line adapter instead of overriding individual functions |
| **Theme Authors** | Clear feature matrix; lint tool catches portability issues |
| **Bengal Users** | Themes work across engines; no silent failures |
| **Bengal Maintainers** | Single source of truth for template functions; easier testing |

### Lines of Code Impact

| Component | Before | After | Change |
|-----------|--------|-------|--------|
| `kida.py` (function overrides) | ~90 lines | ~20 lines | -70 lines |
| `i18n.py` | ~150 lines | ~120 lines | -30 lines (no decorators) |
| New adapter layer | 0 lines | ~270 lines | +270 lines |
| **Net** | | | +170 lines |

The net increase is modest (+170 lines) and consists of well-organized, single-purpose adapter modules rather than scattered workarounds.

---

## References

- [Jinja2 @pass_context documentation](https://jinja.palletsprojects.com/en/3.1.x/api/#jinja2.pass_context)
- [RFC: Kida Template Engine](./rfc-kida-template-engine.md)
- [Bengal TemplateEngineProtocol](../bengal/rendering/engines/protocol.py)

---

## Appendix: Current @pass_context Locations

Verified via `grep -r "@pass_context" bengal/rendering/`:

| File | Line | Function |
|------|------|----------|
| `template_functions/i18n.py` | 108 | `t()` |
| `template_functions/i18n.py` | 120 | `current_lang()` |
| `template_functions/taxonomies.py` | 44 | `tag_url_with_site()` |
| `template_engine/environment.py` | 452 | `asset_url_with_context()` |

These 4 locations are the complete scope of changes needed in Phase 2.
