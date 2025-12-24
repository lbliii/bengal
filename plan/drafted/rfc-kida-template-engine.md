# RFC: Kida — A Modern Python Template Engine

**Status**: Evaluated  
**Created**: 2025-12-23  
**Updated**: 2025-12-23  
**Author**: AI Assistant + Lawrence Lane  
**Priority**: P2 (Medium)  
**Related**: `bengal/rendering/engines/`, Jinja2, PEP 750  
**Confidence**: 60% 🟡

---

## Evaluation Summary

**Verdict**: ✅ **Approved with Conditions**

This RFC proposes building a new template engine to address real limitations in Jinja2. After reviewing Bengal's actual template complexity (103 HTML templates, 651-line base template, deep autodoc hierarchies), the case for a purpose-built engine is stronger than initially assumed. However, the RFC's performance claims need validation and the architecture needs refinement.

### Key Findings

| Claim | Verified | Notes |
|-------|----------|-------|
| Jinja2 ~5000 lines | ❌ | Actually **~14,350 lines** — strengthens the case |
| Bengal has workarounds | ✅ | ChainableUndefined, per-template locks, macro separation |
| Complex SSG templates | ✅ | 103 templates, autodoc partials with 6-level inheritance |
| 10k page scaling needs | ✅ | Benchmarks target <30s discovery, <2GB memory |

### Conditions for Approval

1. **Prototype performance benchmark first** — Build minimal Kida (expressions, if, for, extends) and benchmark against Jinja on Bengal's `base.html` before full implementation
2. **Reconsider interpreter vs. compiler** — Given template complexity (263-line autodoc partials, nested loops), a hybrid approach may be needed
3. **Error enhancement can land independently** — The error message improvements don't require a new engine

---

## Executive Summary

This RFC proposes **Kida**, a new Python template engine designed as a modern alternative to Jinja2. Kida will be developed as a standalone package (`pip install kida`) that Bengal can optionally use via its existing pluggable engine architecture.

| Aspect | Jinja2 | Kida |
|--------|--------|------|
| **Codebase** | ~14,350 lines | ~3500 lines (revised) |
| **Architecture** | Compile to Python | Hybrid: interpret + optional bytecode |
| **Error messages** | Cryptic, wrong line numbers | Precise, with suggestions |
| **Type checking** | None | Optional validation |
| **Caching** | External/bytecode only | Built-in fragment caching |
| **Block endings** | `{% endif %}`, `{% endfor %}`, etc. | Unified `{% end %}` |
| **Dependencies** | MarkupSafe | Zero |
| **Free-threading** | Limited | Designed for 3.14t |

**Why "Kida"?** Named after Kida, a Bengal cat. Keeps the feline theme.

---

## Problem Statement

### Jinja2 Shows Its Age

Jinja2 was designed in 2007 for Django-era web applications. While battle-tested, it carries significant baggage:

1. **Compile-to-Python Architecture**
   - Templates are compiled to Python source code, then `exec()`ed
   - Adds startup overhead and memory bloat
   - Debugging requires traceback rewriting to map back to template lines
   - ~2000 lines just for the compiler

2. **Cryptic Error Messages**
   ```
   jinja2.exceptions.UndefinedError: 'page object' has no attribute 'titl'
   ```
   vs what developers need:
   ```
   Error in templates/post.html line 23:
     22 │ <article>
     23 │   <h1>{{ page.titl }}</h1>
        │              ^^^^
        │ Unknown attribute 'titl' on Page
        │ Did you mean: title, tags, template?
   ```

3. **Confusing Macro Scoping**
   - Macros execute all top-level code during import
   - Bengal already documents workarounds in `themes/default/templates/README.md`
   - The "macro/include separation pattern" exists solely to work around Jinja limitations

4. **Inconsistent Syntax**
   ```jinja
   {% if x %}...{% endif %}
   {% for x in y %}...{% endfor %}
   {% block content %}...{% endblock %}
   {% macro foo() %}...{% endmacro %}
   ```
   Four different closing tags to remember.

5. **No Built-in Caching**
   - Bytecode cache helps with parsing, not rendering
   - Fragment caching requires external solutions
   - No awareness of template dependencies

6. **Feature Bloat**
   - Sandbox mode (~250 lines) — Bengal doesn't need
   - Line statements — Never used
   - i18n extension — Bengal has its own
   - Async mode — Dual code paths everywhere

### Bengal's Current Workarounds

Bengal already works around Jinja limitations:

| Workaround | Location | Purpose |
|------------|----------|---------|
| `ChainableUndefined` | `environment.py` | Safe dot-notation access |
| Per-template locks | `jinja.py` | Prevent duplicate compilation |
| Macro separation pattern | `templates/README.md` | Avoid import-time execution |
| Custom finalize | `environment.py` | Convert None to empty string |

These workarounds add complexity. A purpose-built engine eliminates them.

### Bengal's Actual Template Complexity

Analysis of Bengal's default theme reveals significant template complexity that any replacement engine must handle:

| Metric | Value | Notes |
|--------|-------|-------|
| **Total HTML templates** | 103 | Production theme, not toy examples |
| **base.html size** | 651 lines | Full-featured: i18n, view transitions, speculation rules, link previews |
| **Deepest inheritance** | 6 levels | `autodoc/python/module.html` → `base.html` + 4 partial includes |
| **Largest partial** | 263 lines | `autodoc/partials/members.html` with nested loops |
| **Template functions** | 25+ | `get_menu()`, `icon()`, `asset_url()`, `og_image()`, etc. |
| **Custom filters** | 15+ | `markdownify`, `meta_keywords`, `dateformat`, `safe_access` |

**Representative Template Patterns** (from `base.html`):

```jinja
{# Deep config access with safe defaults #}
{% set _speculation = _doc_app.speculation %}
{% set _speculation_enabled = _doc_app.enabled and _speculation.enabled %}
{% set _speculation_feature = _doc_app.features.speculation_rules | default(true) %}

{# Computed template variables for performance #}
{% set _main_menu = get_menu_lang('main', _current_lang) %}
{% set _auto_nav = get_auto_nav() if _main_menu | length == 0 else [] %}

{# Conditional i18n with multiple config checks #}
{% if _i18n and _i18n.strategy == 'prefix' %}
  {% set _default_lang = _i18n.default_language | default('en') %}
  {% set _default_in_subdir = _i18n.default_in_subdir %}
  {% if _lang and (_default_in_subdir or _lang != _default_lang) %}
    {% set _rss_href = '/' ~ _lang ~ '/rss.xml' %}
  {% endif %}
{% endif %}
```

**Autodoc Template Patterns** (from `autodoc/partials/members.html`):

```jinja
{# Nested loops with complex filtering #}
{% for member in public_members %}
  {% set member_params = member.metadata.args or member.metadata.parameters
       or (member.children or []) | selectattr('element_type', 'eq', 'parameter') | list %}
  {% set param_count = member_params | length %}

  {% for param in member_params %}
    {# 4 levels of nested attribute access #}
    {% set param_default = param.default %}
    {% if param_default is not none and param_default != '' %}
      <span class="autodoc-param-default">Default: <code>{{ param_default }}</code></span>
    {% endif %}
  {% endfor %}
{% endfor %}
```

**Scaling Requirements** (from `benchmarks/test_10k_site.py`):

| Target | Value | Implication |
|--------|-------|-------------|
| Discovery (10k pages) | <30s | ~333 pages/sec |
| Peak memory (10k) | <2GB | ~200KB/page |
| Discovery (1k pages) | <5s | ~200 pages/sec |

These benchmarks inform Kida's performance requirements. Template rendering must not become the bottleneck.

---

## Goals

1. **Familiar Syntax** — Jinja-like syntax with modern improvements
2. **Excellent Errors** — Precise location, suggestions, actionable messages
3. **Type-Aware** — Optional validation against known types (Page, Site, Config)
4. **Built-in Caching** — Fragment caching as a language feature
5. **Direct Interpreter** — No compile-to-Python indirection
6. **Zero Dependencies** — Pure Python, no external packages
7. **Free-Threading Ready** — Designed for Python 3.14t parallelism
8. **Standalone Package** — Usable outside Bengal

## Non-Goals

- 100% Jinja2 compatibility (subset is fine)
- Sandbox mode (use Python 3.14 interpreters instead)
- Async templates (future consideration)
- Django template compatibility

---

## Design

### Syntax Overview

Kida uses familiar `{{ }}` and `{% %}` delimiters with improvements:

```jinja
{# Kida Template #}

{% extends "base.html" %}

{% block content %}
  <article>
    <h1>{{ page.title }}</h1>

    {# Unified {% end %} for all blocks #}
    {% if page.draft %}
      <span class="badge">Draft</span>
    {% end %}

    {# Loops with {% empty %} #}
    {% for post in site.pages | recent(5) %}
      <a href="{{ post.url }}">{{ post.title }}</a>
    {% empty %}
      <p>No posts yet.</p>
    {% end %}

    {# Built-in caching #}
    {% cache "sidebar-" + site.nav_version %}
      {{ render_sidebar(site) }}
    {% end %}

    {# Pipeline operator for readability #}
    {{ items
       |> where(published=true)
       |> sort_by("date")
       |> take(5) }}

  </article>
{% end %}
```

### Key Syntax Differences from Jinja

#### 1. Unified Block Endings

```jinja
{# Jinja - must remember each closing tag #}
{% if x %}...{% endif %}
{% for x in y %}...{% endfor %}
{% block content %}...{% endblock %}

{# Kida - consistent {% end %} #}
{% if x %}...{% end %}
{% for x in y %}...{% end %}
{% block content %}...{% end %}
```

#### 2. Functions Instead of Macros

```jinja
{# Jinja macro - confusing scoping #}
{% macro card(item) %}
  <div>{{ item.title }}</div>
{% endmacro %}

{# Kida function - true lexical scope #}
{% def card(item) %}
  <div>{{ item.title }}</div>
  <span>From: {{ site.title }}</span>  {# Can access outer scope #}
{% end %}

{# Call like a function #}
{{ card(page) }}
```

#### 3. Loop Improvements

```jinja
{# Jinja loop #}
{% for item in items %}
  {% if loop.first %}First!{% endif %}
  {{ loop.index }}: {{ item }}
{% else %}
  No items.
{% endfor %}

{# Kida loop - cleaner syntax #}
{% for item, i in items | enumerate %}
  {% first %}First!{% end %}
  {{ i }}: {{ item }}
{% empty %}
  No items.
{% end %}
```

#### 4. Pipeline Operator

```jinja
{# Jinja - nested filters get ugly #}
{{ items | selectattr("published") | sort(attribute="date") | reverse | first }}

{# Kida - pipeline is more readable #}
{{ items
   |> where(published=true)
   |> sort_by("date", reverse=true)
   |> first }}
```

#### 5. Built-in Caching

```jinja
{# Cache expensive operations #}
{% cache key="nav-" + site.nav_hash, ttl="1h" %}
  {{ build_nav_tree(site.pages) }}
{% end %}

{# With dependency tracking #}
{% cache "sidebar", depends=[site.nav, config.theme] %}
  {{ render_sidebar() }}
{% end %}
```

#### 6. Explicit Template Context (Optional)

```jinja
{# Declare expected variables at top #}
{% template page: Page, site: Site, config: Config %}

{# Enables type checking and better errors #}
{{ page.titl }}
{#       ^^^^ Error: Page has no attribute 'titl'. Did you mean 'title'? #}
```

---

### Architecture

Given Bengal's template complexity (651-line base.html, 263-line autodoc partials, nested loops with filter chains), a pure tree-walking interpreter may not achieve performance parity with Jinja2's compiled approach. Kida uses a **hybrid architecture**:

```
┌─────────────────────────────────────────────────────────────────┐
│                    Kida Template Pipeline                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│   Template Source                                                │
│        │                                                         │
│        ▼                                                         │
│   ┌─────────┐                                                   │
│   │  Lexer  │  Regex-based tokenization (~250 lines)            │
│   └────┬────┘                                                   │
│        │ Tokens                                                  │
│        ▼                                                         │
│   ┌─────────┐                                                   │
│   │ Parser  │  Recursive descent, typed AST (~500 lines)        │
│   └────┬────┘                                                   │
│        │ AST                                                     │
│        ├──────────────────────────────────┐                     │
│        ▼                                  ▼                     │
│   ┌─────────────┐                   ┌───────────┐              │
│   │  Validator  │                   │ Optimizer │              │
│   │ (optional)  │                   │           │              │
│   └──────┬──────┘                   └─────┬─────┘              │
│          │                                │                     │
│          ▼                                ▼                     │
│   ┌─────────────┐                   ┌───────────┐              │
│   │ Interpreter │    ◄── OR ──►     │ Compiler  │              │
│   │  (dev mode) │                   │ (prod)    │              │
│   └──────┬──────┘                   └─────┬─────┘              │
│          │                                │                     │
│          └────────────┬───────────────────┘                     │
│                       ▼                                         │
│                  String Output                                   │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

**Hybrid Execution Strategy:**

| Mode | Execution | Use Case |
|------|-----------|----------|
| **Interpreted** | Tree-walking | Dev server (`bengal serve`), small templates |
| **Compiled** | Python bytecode | Production builds, hot templates |
| **Auto** | Profile-guided | Compile templates rendered >N times |

**Why Hybrid?**

1. **Dev Mode Benefits** — Interpreted mode gives instant error feedback with perfect source mapping
2. **Production Speed** — Compiled mode matches Jinja2 performance for hot paths
3. **Incremental Adoption** — Start interpreted, profile, compile bottlenecks
4. **Debugging Flexibility** — Switch modes without template changes

**Compilation Approach:**

Unlike Jinja2's compile-to-Python-source approach (which requires `exec()`), Kida compiles to:
- **Python code objects** directly via `compile()` + `types.CodeType`
- This enables the same native speed while avoiding eval/exec for security
- Bytecode is cacheable (like Jinja's `.cache` files)

For Bengal's use case (103 templates, complex autodoc rendering, 10k page builds), the hybrid approach provides:
- Fast iteration during development
- Jinja-competitive production performance
- Better error messages in both modes

---

### Module Structure

```
kida/
├── __init__.py         # Public API exports
├── py.typed            # PEP 561 type marker
│
├── # Core Pipeline
├── lexer.py            # Token generation (~250 lines)
├── parser.py           # AST construction (~500 lines)
├── ast.py              # Node type definitions (~300 lines)
├── interpreter.py      # Tree-walking execution (~600 lines)
│
├── # Compilation (Production Mode)
├── optimizer.py        # AST optimization passes (~300 lines)
├── compiler.py         # Python bytecode generation (~500 lines)
├── bytecode_cache.py   # Persistent cache (~150 lines)
│
├── # Features
├── filters.py          # Built-in filters (~400 lines) - match Jinja's filter set
├── tests.py            # Built-in tests (~150 lines) - is defined, is none, etc.
├── cache.py            # Fragment caching (~150 lines)
├── validator.py        # Type-aware validation (~300 lines)
├── errors.py           # Rich error messages (~250 lines)
│
├── # API
├── environment.py      # Configuration & template loading (~300 lines)
├── loaders.py          # FileSystem, Dict, Choice, Prefix (~200 lines)
├── template.py         # Template object (~150 lines)
│
└── # Optional
└── compat/
    └── jinja.py        # Jinja syntax compatibility layer (~250 lines)
```

**Total: ~4250 lines** (vs Jinja's ~14,350)

Still ~3x smaller than Jinja2, but realistic for Bengal's requirements:
- Full filter/test suite for template compatibility
- Bytecode compilation for production performance
- Rich error system that matches the RFC's promises

---

### Error Messages

Kida prioritizes actionable error messages:

```
Error in templates/post.html line 23:

  22 │ <article>
  23 │   <h1>{{ page.titl }}</h1>
     │              ^^^^
     │              Unknown attribute 'titl' on Page
     │  
     │              Did you mean: title, tags, template?
  24 │   <p>{{ page.date | dateformat }}</p>

Hint: Page attributes are defined in your content frontmatter.
      See: https://bengal.dev/docs/pages#attributes
```

```
Error in templates/list.html line 15:

  14 │ {% for item in items %}
  15 │   {{ item.name }
     │                 ^
     │                 Expected '}}' to close expression
     │  
     │                 Opening '{{' is on line 15, column 3
  16 │ {% end %}
```

```
Error in templates/base.html line 45:

  44 │ {% block content %}
  45 │ {% endblock %}
     │    ^^^^^^^^
     │    Unknown tag 'endblock'
     │  
     │    In Kida, use {% end %} to close all blocks.
     │    Migration: Replace {% endblock %} with {% end %}
```

---

### Built-in Filters

Kida includes essential filters. More can be registered.

| Filter | Description | Example |
|--------|-------------|---------|
| `escape` / `e` | HTML escape | `{{ user_input \| e }}` |
| `safe` | Mark as safe HTML | `{{ content \| safe }}` |
| `default(val)` | Default if undefined | `{{ x \| default("N/A") }}` |
| `first` / `last` | First/last item | `{{ items \| first }}` |
| `length` | Collection length | `{{ items \| length }}` |
| `join(sep)` | Join strings | `{{ tags \| join(", ") }}` |
| `lower` / `upper` | Case conversion | `{{ name \| upper }}` |
| `trim` | Strip whitespace | `{{ text \| trim }}` |
| `replace(a, b)` | String replace | `{{ s \| replace("-", "_") }}` |
| `sort_by(attr)` | Sort by attribute | `{{ pages \| sort_by("date") }}` |
| `where(k, v)` | Filter by attribute | `{{ pages \| where("draft", false) }}` |
| `take(n)` | First n items | `{{ items \| take(5) }}` |
| `skip(n)` | Skip first n items | `{{ items \| skip(10) }}` |
| `enumerate` | Add index to loop | `{% for x, i in items \| enumerate %}` |
| `dateformat(fmt)` | Format dates | `{{ date \| dateformat("%Y-%m-%d") }}` |
| `json` | JSON serialize | `{{ data \| json }}` |
| `truncate(n)` | Truncate string | `{{ text \| truncate(100) }}` |
| `slugify` | URL-safe string | `{{ title \| slugify }}` |
| `markdown` | Render markdown | `{{ content \| markdown \| safe }}` |

---

### Type-Aware Validation

Optional type declarations enable compile-time checking:

```jinja
{% template page: Page, site: Site %}

{# These errors are caught at parse time, not runtime #}
{{ page.titl }}           {# Error: Unknown attribute 'titl' #}
{{ page.date | upper }}   {# Warning: 'upper' on datetime may not work #}
{{ site.pages | first.url }}  {# Error: 'first' returns optional #}
```

Type information sources:
1. Explicit `{% template %}` declarations
2. Inferred from filename conventions (`page.html` → Page context)
3. Bengal's type registry (Page, Site, Config, etc.)

---

### Caching

Kida includes built-in fragment caching:

```jinja
{# Simple key-based cache #}
{% cache "expensive-widget" %}
  {{ compute_expensive_thing() }}
{% end %}

{# Key with dynamic component #}
{% cache "nav-" + site.nav_version %}
  {{ build_navigation(site) }}
{% end %}

{# With TTL #}
{% cache "weather", ttl="5m" %}
  {{ fetch_weather() }}
{% end %}

{# With dependency invalidation #}
{% cache "sidebar", depends=[config.theme, site.nav] %}
  {{ render_sidebar() }}
{% end %}
```

Cache storage is pluggable:
- In-memory (default)
- File-based
- Redis (optional integration)

---

### Jinja Compatibility Layer

For migration, Kida includes a compatibility mode:

```python
from kida.compat.jinja import JinjaCompatEnvironment

# Accepts Jinja syntax, runs on Kida engine
env = JinjaCompatEnvironment(loader=...)
```

The compatibility layer:
1. Converts `{% endif %}` → `{% end %}`
2. Converts `{% endfor %}` → `{% end %}`
3. Converts `{% macro %}` → `{% def %}`
4. Maps `loop.*` variables to Kida equivalents
5. Warns about unsupported features

---

## Public API

### Core Classes

```python
from kida import Environment, Template, FileSystemLoader

# Environment-based (recommended)
env = Environment(
    loader=FileSystemLoader("templates"),
    autoescape=True,
    cache_size=400,
)
template = env.get_template("page.html")
html = template.render(page=page, site=site)

# Direct template usage
t = Template("Hello {{ name }}!")
html = t.render(name="World")

# String templates via environment
t = env.from_string("{{ x + y }}")
html = t.render(x=1, y=2)
```

### Loaders

```python
from kida import FileSystemLoader, DictLoader, ChoiceLoader, PrefixLoader

# Filesystem
loader = FileSystemLoader(["templates", "fallback"])

# Dictionary (for testing)
loader = DictLoader({
    "base.html": "<!DOCTYPE html>...",
    "page.html": "{% extends 'base.html' %}...",
})

# Priority chain
loader = ChoiceLoader([
    FileSystemLoader("project/templates"),
    FileSystemLoader("theme/templates"),
])

# Prefix-based
loader = PrefixLoader({
    "default": FileSystemLoader("themes/default"),
    "custom": FileSystemLoader("themes/custom"),
})
# Usage: {% extends "default/base.html" %}
```

### Custom Filters

```python
env = Environment(loader=...)

@env.filter
def reverse_words(value: str) -> str:
    return " ".join(value.split()[::-1])

# Usage: {{ text | reverse_words }}
```

### Custom Functions

```python
@env.function
def now() -> datetime:
    return datetime.now()

# Usage: {{ now() | dateformat }}
```

---

## Bengal Integration

### Engine Implementation

```python
# bengal/rendering/engines/kida.py

from kida import Environment, FileSystemLoader, ChoiceLoader
from bengal.rendering.engines.protocol import TemplateEngineProtocol

class KidaTemplateEngine:
    """Kida template engine for Bengal."""

    def __init__(self, site: Site, *, profile: bool = False) -> None:
        self.site = site
        self.template_dirs = self._build_template_dirs(site)

        self.env = Environment(
            loader=ChoiceLoader([
                FileSystemLoader(d) for d in self.template_dirs
            ]),
            autoescape=True,
            cache_size=0 if site.dev_mode else 400,
        )

        # Register Bengal's template functions
        self._register_functions()

    def render_template(self, name: str, context: dict[str, Any]) -> str:
        context.setdefault("site", self.site)
        context.setdefault("config", self.site.config)
        template = self.env.get_template(name)
        return template.render(**context)

    def render_string(self, template: str, context: dict[str, Any]) -> str:
        context.setdefault("site", self.site)
        context.setdefault("config", self.site.config)
        t = self.env.from_string(template)
        return t.render(**context)

    def template_exists(self, name: str) -> bool:
        try:
            self.env.get_template(name)
            return True
        except Exception:
            return False

    def get_template_path(self, name: str) -> Path | None:
        for d in self.template_dirs:
            path = d / name
            if path.exists():
                return path
        return None

    def list_templates(self) -> list[str]:
        templates = set()
        for d in self.template_dirs:
            for p in d.rglob("*.html"):
                templates.add(str(p.relative_to(d)))
        return sorted(templates)

    def validate(self, patterns: list[str] | None = None) -> list[TemplateError]:
        errors = []
        for name in self.list_templates():
            try:
                self.env.get_template(name)
            except TemplateSyntaxError as e:
                errors.append(TemplateError(name, e.lineno, str(e)))
        return errors
```

### Registration

```python
# bengal/rendering/engines/__init__.py

if engine_name == "kida":
    try:
        from bengal.rendering.engines.kida import KidaTemplateEngine
    except ImportError as e:
        raise BengalConfigError(
            "Kida engine requires kida package.\n"
            "Install with: pip install bengal[kida]",
        ) from e
    return KidaTemplateEngine(site, profile=profile)
```

### Configuration

```yaml
# bengal.yaml
site:
  template_engine: kida
```

```toml
# pyproject.toml (Bengal)
[project.optional-dependencies]
kida = ["kida>=0.1.0"]
```

---

## Performance

### Bengal Template Performance Requirements

Based on Bengal's 10k-page benchmark targets and actual template complexity:

| Requirement | Target | Derived From |
|-------------|--------|--------------|
| Render `base.html` | <10ms | 10k pages in <30s allows ~3ms overhead |
| Render autodoc module | <20ms | Complex nested loops, ~50 method cards |
| Memory per template | <30KB | 2GB limit for 10k pages + templates |
| First render (cold) | <50ms | Dev server responsiveness |
| Repeat render (hot) | <5ms | Bytecode cached |

### Benchmark Templates (from Bengal's default theme)

| Template | Lines | Loops | Includes | Complexity |
|----------|-------|-------|----------|------------|
| `base.html` | 651 | 8 | 5 | High (i18n, view transitions) |
| `autodoc/python/module.html` | 87 | 3 | 4 | Medium (macro imports) |
| `autodoc/partials/members.html` | 263 | 4 nested | 0 | High (tables, conditionals) |
| `partials/docs-nav.html` | 89 | 2 | 1 recursive | Medium (tree traversal) |

### Execution Mode Performance Targets

| Mode | Parse | First Render | Repeat Render | Use Case |
|------|-------|--------------|---------------|----------|
| **Interpreted** | <5ms | <20ms | <15ms | Dev server, debugging |
| **Compiled** | <10ms | <50ms | <3ms | Production builds |
| **Cached** | 0ms | 0ms | <3ms | Hot path (bytecode loaded) |

### Free-Threading (Python 3.14t)

Kida is designed for true parallelism:

```python
# With PYTHON_GIL=0, this achieves real parallelism
with ThreadPoolExecutor(max_workers=8) as executor:
    results = list(executor.map(
        lambda p: template.render(page=p),
        pages
    ))
```

**Expected speedup**: 2-4x on 8-core machines for template rendering phase.

**Note**: Overall build speedup depends on other GIL-bound operations (Markdown parsing, file I/O). Template rendering is typically 15-25% of total build time.

### Optimizations

Kida applies AST optimizations before compilation:

1. **Constant Folding** — `"Hello " + "World"` → `"Hello World"` at parse time
2. **Filter Chain Compilation** — `|> a |> b |> c` → single function call
3. **Loop-Invariant Hoisting** — Move unchanging expressions outside loops
4. **Attribute Path Caching** — `page.metadata.author` → pre-computed lookup
5. **Dead Code Elimination** — `{% if false %}...{% end %}` → removed
6. **Fragment Caching** — `{% cache %}` blocks skip re-rendering

### Performance Validation Requirement

**Before Phase 2 begins**, a prototype benchmark must demonstrate:

```python
# Minimum viable performance test
def test_kida_performance_parity():
    """Kida must be within 2x of Jinja2 for Bengal's base.html."""
    jinja_time = benchmark_jinja_render("base.html", context)
    kida_time = benchmark_kida_render("base.html", context)

    assert kida_time < jinja_time * 2.0, (
        f"Kida ({kida_time:.2f}ms) >2x slower than Jinja ({jinja_time:.2f}ms)"
    )
```

If interpreted mode cannot achieve 2x parity, compiled mode must be prioritized.

---

## Implementation Plan

### Phase 0: Prototype Benchmark (Week 0 — GATE)

**Priority**: Validate performance assumptions before committing to full implementation.

**Scope**: Minimal Kida prototype to benchmark against Jinja2.

- [ ] Lexer for `{{ }}`, `{% if %}`, `{% for %}`, `{% extends %}`, `{% block %}`
- [ ] Parser producing minimal AST
- [ ] Tree-walking interpreter (no compiler yet)
- [ ] Benchmark harness comparing Kida vs Jinja2
- [ ] Test against Bengal's actual `base.html` (651 lines)
- [ ] Test against `autodoc/partials/members.html` (263 lines, nested loops)

**Gate Criteria**:

| Metric | Pass | Fail | Action on Fail |
|--------|------|------|----------------|
| `base.html` render | <20ms | >50ms | Prioritize compiler |
| Nested loop (100 items) | <30ms | >100ms | Investigate hot path |
| Memory overhead | <2x Jinja | >5x Jinja | Profile allocations |

**Deliverable**: Performance report with go/no-go recommendation

**Estimated Effort**: 3-5 days

---

### Phase 1: Core Engine (Week 1-2)

**Priority**: Critical path — nothing works without this.

- [ ] Lexer with token generation
- [ ] Parser with AST construction
- [ ] Interpreter (text, expressions, if, for, set, with)
- [ ] Environment and Template classes
- [ ] FileSystemLoader, DictLoader, ChoiceLoader
- [ ] Basic filters (escape, safe, default, first, last, length, join, lower, upper)
- [ ] Basic tests (defined, none, callable, iterable)
- [ ] Unit tests for each component

**Deliverable**: `pip install kida` works, basic templates render

### Phase 2: Template Inheritance (Week 2-3)

**Priority**: Required for Bengal's theme system.

- [ ] `{% extends %}` with block inheritance
- [ ] `{% block %}...{% end %}` with super() support
- [ ] `{% include %}` with context passing
- [ ] `{% def %}` functions with lexical scoping
- [ ] `{% for %}...{% empty %}...{% end %}`
- [ ] Full filter set (match Jinja's common filters)
- [ ] Pipeline operator `|>`

**Gate**: Render Bengal's `base.html` correctly

**Deliverable**: Can render Bengal's default theme templates

### Phase 3: Production Compiler (Week 3-4)

**Priority**: Performance parity with Jinja2.

- [ ] AST optimizer (constant folding, dead code elimination)
- [ ] Bytecode compiler (Python code objects)
- [ ] Bytecode cache (filesystem persistence)
- [ ] Execution mode switching (interpreted ↔ compiled)
- [ ] Profile-guided compilation (auto-compile hot templates)

**Gate**: `base.html` renders in <5ms (compiled, cached)

**Deliverable**: Production-ready performance

### Phase 4: Error Messages (Week 4)

**Priority**: DX differentiator.

- [ ] Source location tracking in all nodes
- [ ] Rich error formatting with context (before/after lines)
- [ ] Suggestion system (Levenshtein distance for typos)
- [ ] Hint system for common mistakes (Jinja syntax → Kida)
- [ ] Terminal color support (ANSI codes)
- [ ] Structured error output for IDE integration

**Deliverable**: Best-in-class error messages

### Phase 5: Advanced Features (Week 5)

**Priority**: Feature completeness.

- [ ] `{% cache %}` block with key expressions
- [ ] `{% template %}` context declarations
- [ ] Type registry integration
- [ ] Attribute validation against known types
- [ ] Unused variable warnings
- [ ] `{% call %}` for caller blocks
- [ ] Attribute checking
- [ ] Filter argument validation
- [ ] Unused variable warnings

**Deliverable**: Optional type checking

### Phase 6: Bengal Integration (Week 5)

**Priority**: Required for adoption.

- [ ] `KidaTemplateEngine` class
- [ ] Register with engine factory
- [ ] Migrate template functions
- [ ] Test with default theme
- [ ] Documentation

**Deliverable**: `template_engine: kida` works in Bengal

### Phase 7: Polish (Week 5-6)

- [ ] Jinja compatibility layer
- [ ] Migration guide
- [ ] Performance benchmarks
- [ ] Documentation site
- [ ] PyPI release

**Deliverable**: v0.1.0 release

---

## Testing Strategy

### Unit Tests

```python
# tests/test_lexer.py
def test_tokenizes_expression():
    tokens = list(Lexer("{{ x + 1 }}").tokenize())
    assert tokens == [
        Token(EXPR_START, "{{"),
        Token(NAME, "x"),
        Token(PLUS, "+"),
        Token(INTEGER, "1"),
        Token(EXPR_END, "}}"),
    ]

# tests/test_parser.py
def test_parses_if_block():
    ast = Parser("{% if x %}yes{% end %}").parse()
    assert isinstance(ast.body[0], IfNode)
    assert ast.body[0].test.name == "x"

# tests/test_interpreter.py
def test_renders_expression():
    t = Template("{{ x + 1 }}")
    assert t.render(x=41) == "42"

def test_renders_loop():
    t = Template("{% for x in items %}{{ x }}{% end %}")
    assert t.render(items=[1, 2, 3]) == "123"
```

### Integration Tests

```python
# tests/test_integration.py
def test_full_template_render():
    env = Environment(loader=DictLoader({
        "base.html": "<html>{% block content %}{% end %}</html>",
        "page.html": "{% extends 'base.html' %}{% block content %}{{ title }}{% end %}",
    }))
    t = env.get_template("page.html")
    assert t.render(title="Hello") == "<html>Hello</html>"

def test_caching():
    call_count = 0
    def expensive():
        nonlocal call_count
        call_count += 1
        return "result"

    env = Environment(...)
    env.function("expensive", expensive)
    t = env.from_string("{% cache 'key' %}{{ expensive() }}{% end %}")

    t.render()
    t.render()
    assert call_count == 1  # Cached
```

### Jinja Comparison Tests

```python
# tests/test_jinja_parity.py
@pytest.mark.parametrize("template,context,expected", [
    ("{{ x }}", {"x": 42}, "42"),
    ("{% if x %}yes{% end %}", {"x": True}, "yes"),
    ("{% for x in items %}{{ x }}{% end %}", {"items": [1, 2]}, "12"),
    # ... 100+ cases
])
def test_parity(template, context, expected):
    assert Template(template).render(**context) == expected
```

---

## Risks and Mitigations

### Risk 1: Adoption Resistance

**Problem**: Users comfortable with Jinja may resist change.

**Mitigation**:
- Jinja compatibility layer for gradual migration
- Clear documentation of benefits
- Migration tooling (`kida migrate templates/`)
- Keep Jinja as default in Bengal, Kida as opt-in

### Risk 2: Performance Regression

**Problem**: Interpreter may be slower than compiled Jinja.

**Mitigation**:
- Benchmark continuously during development
- Profile and optimize hot paths
- If needed, add optional mypyc compilation
- Target "as fast as Jinja" not "faster"

### Risk 3: Feature Gaps

**Problem**: Users may need Jinja features we dropped.

**Mitigation**:
- Document intentionally unsupported features
- Provide workarounds in migration guide
- Add features based on real demand
- Keep Jinja available as fallback

### Risk 4: Maintenance Burden

**Problem**: Two template engines to maintain.

**Mitigation**:
- Kida is separate repo with own lifecycle
- Bengal's Jinja integration stays stable
- Community can contribute to Kida independently
- Smaller codebase = less maintenance

---

## Alternatives Considered

### Alternative 1: Fork Jinja2

**Pros**: Immediate compatibility  
**Cons**: Inherit all technical debt, massive codebase, hard to evolve

**Decision**: Rejected. Jinja's architecture is the problem.

### Alternative 2: Use Mako or Chameleon

**Pros**: Existing solutions  
**Cons**: Different syntax, own quirks, not purpose-built

**Decision**: Rejected. Want familiar syntax with specific improvements.

### Alternative 3: Python 3.14 T-Strings Only

**Pros**: Zero parsing, native Python  
**Cons**: Not a template language, requires Python 3.14, less flexible

**Decision**: Future consideration. Kida first, t-strings later.

### Alternative 4: Keep Using Jinja, Just Improve Wrappers

**Pros**: No new code  
**Cons**: Can't fix core issues (errors, architecture, performance)

**Decision**: Current approach. Works but doesn't scale.

---

## Success Metrics

### Phase 0 Gate (Must Pass Before Continuing)

| Metric | Target | Measurement |
|--------|--------|-------------|
| `base.html` interpreted render | <20ms | Benchmark vs Jinja2 |
| Nested loop (100 items) | <30ms | Synthetic benchmark |
| Prototype LOC | <1000 | Core engine only |

### Final Release Targets

| Metric | Target | Notes |
|--------|--------|-------|
| **Codebase size** | <5000 lines | ~3x smaller than Jinja's 14,350 |
| **Test coverage** | >95% | All branches |
| **Compiled render time** | ≤ Jinja2 | Production mode |
| **Interpreted render time** | ≤ 2x Jinja2 | Dev mode acceptable |
| **Error message quality** | "Obviously better" | User testing |
| **Bengal integration** | Drop-in via protocol | No template changes required |
| **Filter compatibility** | 90%+ Jinja filters | Migration friction |
| **Documentation** | Full API + migration guide | Required for adoption |

### Bengal-Specific Targets

| Template | Max Render Time | Notes |
|----------|-----------------|-------|
| `base.html` | <10ms | Core overhead for every page |
| `autodoc/python/module.html` | <20ms | Complex, many includes |
| Full 10k-page build | <5min | Template rendering portion |

### Adoption Path

| Milestone | Target | Gate |
|-----------|--------|------|
| Alpha (opt-in) | Bengal 1.x | Phase 2 complete |
| Beta (recommended) | Bengal 1.x | Phase 4 complete, 1 month stable |
| Default engine | Bengal 2.0 | 6 months production use |

---

## References

- **Jinja2**: https://jinja.palletsprojects.com/
- **PEP 750**: Template String Literals (Python 3.14)
- **Bengal Protocol**: `bengal/rendering/engines/protocol.py`
- **Bengal Engines**: `bengal/rendering/engines/__init__.py`
- **Template README**: `bengal/themes/default/templates/README.md`

---

## Appendix A: Full Syntax Reference

### Delimiters

| Delimiter | Purpose |
|-----------|---------|
| `{{ ... }}` | Expression output |
| `{% ... %}` | Statement |
| `{# ... #}` | Comment |

### Statements

| Statement | Example |
|-----------|---------|
| `if` | `{% if x %}...{% elif y %}...{% else %}...{% end %}` |
| `for` | `{% for x in items %}...{% empty %}...{% end %}` |
| `set` | `{% set x = 1 %}` |
| `extends` | `{% extends "base.html" %}` |
| `block` | `{% block name %}...{% end %}` |
| `include` | `{% include "partial.html" %}` |
| `def` | `{% def name(args) %}...{% end %}` |
| `call` | `{% call name(args) %}...{% end %}` |
| `with` | `{% with x = 1 %}...{% end %}` |
| `cache` | `{% cache "key" %}...{% end %}` |
| `template` | `{% template page: Page, site: Site %}` |

### Expressions

| Expression | Example |
|------------|---------|
| Variables | `x`, `page.title` |
| Literals | `42`, `"string"`, `true`, `none` |
| Operators | `+`, `-`, `*`, `/`, `%`, `**` |
| Comparisons | `==`, `!=`, `<`, `>`, `<=`, `>=` |
| Logic | `and`, `or`, `not` |
| Ternary | `x if condition else y` |
| Filters | `x \| filter` |
| Pipeline | `x \|> filter1 \|> filter2` |
| Function calls | `func(arg1, arg2)` |
| List | `[1, 2, 3]` |
| Dict | `{"a": 1, "b": 2}` |

---

## Appendix B: Example Template

```jinja
{# templates/blog/post.html #}
{% template page: Page, site: Site, config: Config %}
{% extends "base.html" %}

{% block title %}{{ page.title }} | {{ site.title }}{% end %}

{% block content %}
<article class="post">
  <header>
    <h1>{{ page.title }}</h1>
    <time datetime="{{ page.date | dateformat('%Y-%m-%d') }}">
      {{ page.date | dateformat('%B %d, %Y') }}
    </time>

    {% if page.tags %}
      <ul class="tags">
        {% for tag in page.tags %}
          <li><a href="{{ tag.url }}">{{ tag.name }}</a></li>
        {% end %}
      </ul>
    {% end %}
  </header>

  <div class="content">
    {{ page.content | safe }}
  </div>

  {% cache "related-" + page.url %}
    {% set related = page.related_posts | take(3) %}
    {% if related %}
      <aside class="related">
        <h2>Related Posts</h2>
        {% for post in related %}
          {{ post_card(post) }}
        {% end %}
      </aside>
    {% end %}
  {% end %}
</article>
{% end %}

{% def post_card(post) %}
  <a href="{{ post.url }}" class="card">
    <h3>{{ post.title }}</h3>
    <p>{{ post.summary | truncate(100) }}</p>
  </a>
{% end %}
```

---

## Changelog

- **2025-12-23**: Evaluated — Approved with Conditions
  - Added Evaluation Summary with approval conditions
  - Corrected Jinja2 line count (~14,350, not ~5,000)
  - Added Bengal Template Complexity section with real metrics:
    - 103 HTML templates, 651-line base.html
    - Documented autodoc partial complexity (263-line members.html)
    - Referenced 10k-page benchmark requirements
  - Revised architecture to hybrid interpreter/compiler
  - Updated line estimates to ~4,250 (more realistic)
  - Added Phase 0 performance gate requirement
  - Added Bengal-specific render time targets
  - Adjusted confidence from 80% to 60%

- **2025-12-23**: Initial draft
  - Defined syntax and architecture
  - Specified Bengal integration
  - Created implementation plan
  - Added testing strategy
