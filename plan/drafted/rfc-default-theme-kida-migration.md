# RFC: Convert Default Theme Templates to Kida-Native Syntax

**Status**: Draft  
**Created**: 2025-01-27  
**Updated**: 2025-12-26 (v2.1 - Comprehensive dog fooding)  
**Author**: AI Assistant  
**Confidence**: 95% 🟢  
**Category**: Rendering  
**Effort**: Medium (~3-4 weeks)  
**Impact**: Performance improvement, better free-threading support, modern template patterns  
**Breaking Changes**: None (backward compatible, Jinja2 remains supported)  
**Dependencies**: Kida template engine (production-ready)

---

## Executive Summary

Convert Bengal's default theme templates from Jinja2 syntax to Kida-native syntax, unlocking the full power of Kida's modern features:

| Category | Feature | Benefit |
|----------|---------|---------|
| **Syntax** | Unified `{% end %}`, `{% let %}`, `{% match %}` | Cleaner, less error-prone |
| **Modern** | `?.` optional chaining, `??` null coalescing | Reduced boilerplate |
| **Control** | `{% break %}`, `{% continue %}`, `{% unless %}`, inline `if` | Better flow control |
| **Nil-Resilience** | `{% with expr as name %}` conditional blocks | Graceful None handling |
| **Output** | `{% spaceless %}`, `{% trim %}`, pipeline `\|>` | Cleaner HTML, readable chains |
| **Components** | `{% embed %}`, `{% def %}` + `{% slot %}`, `{% capture %}` | True component architecture |
| **Literals** | Range `1..10`, `1...11`, `1..10 by 2` | Cleaner iteration patterns |
| **Performance** | AST optimizer, bytecode cache, strict mode | 5.6x faster, early error detection |

**Current State**: Templates use Jinja2 syntax via Kida's compatibility layer. This RFC converts them to Kida-native syntax for better performance, modern patterns, and full feature access.

**Why Now**:
- Kida engine is production-ready (`bengal/rendering/kida/`)
- Modern syntax features implemented (optional chaining, pattern matching, etc.)
- AST optimizer pipeline complete (constant folding, dead code elimination)
- Template compatibility issues resolved (`{% do %}` pattern, Python-style booleans)

---

## Problem Statement

### Current State

Bengal's default theme (`bengal/themes/default/`) uses Jinja2-compatible syntax. While Kida supports this via compatibility layer, the templates don't leverage Kida-native features:

**Evidence**:
- `bengal/rendering/engines/__init__.py:116` - Default engine is `"jinja2"`
- `bengal/themes/default/templates/` - 100+ templates use Jinja2 syntax
- `bengal/rendering/kida/` - 220+ files implementing full Kida engine

### Pain Points

| Pain Point | Current | After Kida-Native |
|------------|---------|-------------------|
| **End tag verbosity** | `{% endif %}`, `{% endfor %}`, `{% endblock %}` | Unified `{% end %}` |
| **Defensive coding** | `{% if x and x.y and x.y.z %}` | `{{ x?.y?.z }}` |
| **Nil handling** | Nested `{% if x %}{% if x.y %}` guards | `{% with x.y as val %}...{% end %}` |
| **Default values** | `{{ x \| default('fallback') }}` | `{{ x ?? 'fallback' }}` |
| **Loop control** | No early exit | `{% break %}`, `{% continue %}` |
| **Negated conditions** | `{% if not x %}` | `{% unless x %}` |
| **Filter chains** | `{{ x \| a \| b \| c }}` (read inside-out) | `{{ x \|> a \|> b \|> c }}` (left-to-right) |
| **Pattern matching** | Nested `{% if %}` chains | `{% match %}` |
| **List mutations** | `{% set _ = list.append(x) %}` (broken) | `{% do list.append(x) %}` |
| **Scope escaping** | `namespace()` workaround | `{% export x = val %}` |
| **Capturing output** | `{% set x %}...{% endset %}` (confusing) | `{% capture x %}...{% end %}` |
| **Range iteration** | `{% for i in range(1, 6) %}` | `{% for i in 1..5 %}` |
| **Whitespace control** | Manual `{%-` / `-%}` | `{% spaceless %}`, `{% trim %}` |
| **Component slots** | No equivalent | `{% def %}` + `{% slot %}` + `{% call %}` |
| **Silent failures** | Undefined vars → empty string | Strict mode catches typos |

### Kida Engine Capabilities

Kida provides significant advantages over Jinja2:

**Performance** (`KIDA.md`):
- **5.6x faster** than Jinja2 (arithmetic mean), 4.4x geometric mean
- AST-to-AST compilation (no string manipulation)
- StringBuilder pattern (O(n) vs O(n²))
- Single-pass HTML escaping
- Bytecode caching (90%+ cold-start reduction)

**Modern Syntax** (`rfc-kida-modern-syntax-features.md`):
- Optional chaining: `user?.profile?.avatar`
- Null coalescing: `value ?? 'default'`
- Break/Continue: `{% break %}`, `{% continue %}`
- Inline filtering: `{% for x in items if x.visible %}`
- Unless blocks: `{% unless condition %}`
- Range literals: `1..10`, `1...11`
- Spaceless blocks: `{% spaceless %}...{% end %}`
- Embed blocks: `{% embed 'card.html' %}...{% end %}`

**Optimizations** (`rfc-kida-pure-python-optimizations.md`):
- Constant folding (5-15% speedup)
- Dead code elimination (10-30% speedup)
- Data node coalescing (5-10% fewer calls)
- Filter inlining (5-10% speedup)
- Buffer pre-allocation
- Bytecode cache (90%+ cold-start reduction)

### Template Compatibility Status

Previous compatibility issues have been resolved:

| Issue | Status | Resolution |
|-------|--------|------------|
| `{% set _ = list.append() %}` | ✅ Fixed | Use `{% do list.append() %}` - 58 replacements made |
| Python-style `True`/`False`/`None` | ✅ Fixed | Parser now recognizes both styles |
| `{% def %}` with nested content | ✅ Working | Both `{% end %}` and `{% enddef %}` work |
| `{% empty %}` after nested blocks | ✅ Working | Works correctly |

**Evidence**: `KIDA_FEEDBACK.md`, `KIDA_TEMPLATE_ANALYSIS.md`

---

## Goals and Non-Goals

### Goals

1. **Convert all default theme templates to Kida-native syntax**
   - Unified `{% end %}` tags
   - `{% let %}` for template-scoped variables
   - `{% match %}` for type/value switching
   - Pipeline operators for filter chains
   - Optional chaining and null coalescing

2. **Adopt Kida-native patterns**
   - Replace `{% set _ = list.append() %}` → `{% do list.append() %}`
   - Replace nested `{% if %}` chains → `{% match %}`
   - Replace verbose defaults → `??` operator
   - Replace defensive access → `?.` operator

3. **Enable Kida optimizations**
   - Constant folding in math-heavy templates
   - Dead code elimination for debug blocks
   - Bytecode caching for fast cold starts

4. **Maintain rendering parity**
   - Converted templates produce identical HTML output
   - Comprehensive test coverage

5. **Update documentation**
   - Theming docs with Kida-native examples
   - Migration guide for theme authors
   - Template best practices

### Non-Goals

- **Removing Jinja2 support** - Both engines supported long-term
- **Converting user themes** - User themes remain opt-in
- **Breaking existing sites** - All sites continue working
- **Deprecating Jinja2** - Ecosystem compatibility maintained

---

## Design Options

### Option A: Comprehensive Kida-Native Conversion (Recommended)

**Approach**: Full conversion to Kida-native syntax with all modern features.

**Phases**:
1. **Syntax Conversion** - Unified `{% end %}`, `{% let %}`, `{% do %}`
2. **Modern Features** - Optional chaining, null coalescing, pattern matching
3. **Optimization** - Enable bytecode caching, leverage optimizer
4. **Documentation** - Updated guides and examples

**Pros**:
- Maximum performance benefits
- Modern, maintainable templates
- Full Kida feature utilization
- Better developer experience

**Cons**:
- More comprehensive effort
- Learning curve for contributors

**Effort**: ~3-4 weeks

### Option B: Minimal Syntax Update

**Approach**: Only convert end tags and fix mutation patterns.

**Pros**:
- Faster implementation
- Lower risk

**Cons**:
- Misses performance benefits
- Doesn't leverage modern features
- Still looks like "old" Jinja2

**Effort**: ~1 week

### Option C: Gradual Migration

**Approach**: Convert templates incrementally as they're touched.

**Pros**:
- Spreads effort over time
- Lower immediate risk

**Cons**:
- Inconsistent codebase
- Longer time to full benefits
- Mixed syntax confusion

**Effort**: Ongoing

---

## Recommended Approach

**Option A: Comprehensive Kida-Native Conversion**

**Reasoning**:
1. Kida engine is production-ready with proven stability
2. Modern features significantly improve template maintainability
3. Performance benefits justify comprehensive conversion
4. Clean break avoids inconsistent mixed syntax
5. Template compatibility issues already resolved

---

## Architecture Impact

| Subsystem | Impact | Changes |
|-----------|--------|---------|
| `bengal/themes/default/templates/` | **High** | Convert 100+ templates to Kida-native syntax |
| `bengal/rendering/engines/__init__.py` | **Low** | Change default engine to `"kida"` |
| `scripts/` | **Medium** | Add conversion script, linting tools |
| `tests/themes/` | **High** | Add comprehensive Kida test suite |
| `site/content/docs/theming/` | **Medium** | Update templating documentation |
| `bengal/themes/default/README.md` | **Medium** | Document Kida-native patterns |

---

## Implementation Plan

### Phase 1: Foundation (Week 1)

#### 1.1 Syntax Conversion Script

Create automated conversion tool:

```python
# scripts/convert_templates_to_kida.py
"""Automated conversion of Jinja2 syntax to Kida-native syntax."""

import re
from pathlib import Path

CONVERSIONS = [
    # Unified end tags
    (r'{%\s*endif\s*%}', '{% end %}'),
    (r'{%\s*endfor\s*%}', '{% end %}'),
    (r'{%\s*endblock\s*%}', '{% end %}'),
    (r'{%\s*endmacro\s*%}', '{% end %}'),
    (r'{%\s*endwith\s*%}', '{% end %}'),
    (r'{%\s*endcall\s*%}', '{% end %}'),

    # Mutation patterns (already done, verify)
    (r'{%\s*set\s+_\s*=\s*([^%]+)\.append\(', r'{% do \1.append('),

    # Let for template-scoped (manual review needed)
    # (r'{%\s*set\s+(\w+)\s*=', r'{% let \1 ='),  # MANUAL REVIEW
]

def convert_template(path: Path) -> tuple[str, int]:
    """Convert template to Kida-native syntax."""
    content = path.read_text()
    changes = 0

    for pattern, replacement in CONVERSIONS:
        new_content = re.sub(pattern, replacement, content)
        if new_content != content:
            changes += 1
            content = new_content

    return content, changes
```

#### 1.2 End Tag Conversion

Convert all Jinja2 end tags to unified `{% end %}`:

| Before | After |
|--------|-------|
| `{% endif %}` | `{% end %}` |
| `{% endfor %}` | `{% end %}` |
| `{% endblock %}` | `{% end %}` |
| `{% endmacro %}` | `{% end %}` |
| `{% endwith %}` | `{% end %}` |

#### 1.3 Mutation Pattern Verification

Verify all mutation patterns use `{% do %}`:

```jinja
{# ❌ Old pattern (broken) #}
{% set _ = items.append(value) %}

{# ✅ Kida pattern (correct) #}
{% do items.append(value) %}
```

**Status**: 58 replacements already made per `KIDA_TEMPLATE_ANALYSIS.md`

### Phase 2: Modern Features (Week 2)

#### 2.1 Unless Blocks

Replace negated conditionals with clearer intent:

```jinja
{# Before #}
{% if not user.banned %}
    {{ user.name }}
{% end %}

{# After #}
{% unless user.banned %}
    {{ user.name }}
{% end %}
```

**Where to use**: Permission checks, feature flags, exclusion logic.

#### 2.2 Nil-Resilient With Blocks

Replace defensive nesting with `{% with expr as name %}`:

```jinja
{# Before: defensive nesting #}
{% if page.author %}
    {% if page.author.profile %}
        <img src="{{ page.author.profile.avatar }}">
        <span>{{ page.author.profile.bio }}</span>
    {% end %}
{% end %}

{# After: nil-resilient with (silently skips if falsy) #}
{% with page.author?.profile as profile %}
    <img src="{{ profile.avatar }}">
    <span>{{ profile.bio }}</span>
{% end %}
```

**Behavior**: Block is **silently skipped** if expression is `None`, empty, or falsy. No error, no output.

**Where to use**: Optional metadata, author profiles, image galleries—anywhere `None` should be graceful.

#### 2.3 Optional Chaining

Replace defensive attribute access:

```jinja
{# Before #}
{% if page and page.metadata and page.metadata.author %}
    {{ page.metadata.author.name }}
{% end %}

{# After #}
{{ page?.metadata?.author?.name ?? 'Unknown' }}
```

#### 2.4 Null Coalescing

Replace verbose defaults:

```jinja
{# Before #}
{{ page.title | default('Untitled') }}
{{ config.timeout | default(30) }}

{# After #}
{{ page.title ?? 'Untitled' }}
{{ config.timeout ?? 30 }}
```

**Note**: `??` preserves falsy values (0, '', False) unlike `| default`.

#### 2.5 Pattern Matching

Replace complex if/elif chains:

```jinja
{# Before #}
{% if page.type == 'post' %}
    <i class="icon-pen"></i>
{% elif page.type == 'gallery' %}
    <i class="icon-image"></i>
{% elif page.type == 'video' %}
    <i class="icon-play"></i>
{% else %}
    <i class="icon-file"></i>
{% end %}

{# After #}
{% match page.type %}
    {% case 'post' %}<i class="icon-pen"></i>
    {% case 'gallery' %}<i class="icon-image"></i>
    {% case 'video' %}<i class="icon-play"></i>
    {% case _ %}<i class="icon-file"></i>
{% end %}
```

#### 2.6 Loop Control

Add break/continue where beneficial:

```jinja
{# Find first match and stop #}
{% for item in items %}
    {% if item.matches_criteria %}
        {{ item.name }}
        {% break %}
    {% end %}
{% end %}

{# Skip items #}
{% for item in items %}
    {% if item.hidden %}{% continue %}{% end %}
    {{ item.name }}
{% end %}
```

#### 2.7 Inline Loop Filtering

Simplify filtered loops:

```jinja
{# Before #}
{% for post in posts %}
    {% if post.published and not post.hidden %}
        {{ post.title }}
    {% end %}
{% end %}

{# After #}
{% for post in posts if post.published and not post.hidden %}
    {{ post.title }}
{% end %}
```

#### 2.8 Range Literals

Replace `range()` calls with native range syntax:

```jinja
{# Before: Python range() #}
{% for i in range(1, 6) %}
    <span class="star">★</span>
{% end %}

{% for page_num in range(1, total_pages + 1) %}
    <a href="/page/{{ page_num }}">{{ page_num }}</a>
{% end %}

{# After: Kida-native ranges #}
{% for i in 1..5 %}           {# inclusive: 1, 2, 3, 4, 5 #}
    <span class="star">★</span>
{% end %}

{% for page_num in 1..total_pages %}
    <a href="/page/{{ page_num }}">{{ page_num }}</a>
{% end %}

{# With step #}
{% for i in 0..100 by 10 %}   {# 0, 10, 20, ..., 100 #}
    <option value="{{ i }}">{{ i }}%</option>
{% end %}
```

**Where to use**: Pagination, star ratings, progress indicators, numbered lists.

#### 2.9 Export for Scope Escaping

Escape inner scope with `{% export %}`:

```jinja
{# Accumulate total from loop #}
{% let total = 0 %}
{% for item in cart.items %}
    {% export total = total + item.price %}
{% end %}
<span>Total: ${{ total }}</span>

{# Find last matching item #}
{% let last_post = none %}
{% for post in posts if post.featured %}
    {% export last_post = post %}
{% end %}
{% with last_post as post %}
    <div class="featured">{{ post.title }}</div>
{% end %}
```

**Where to use**: Counters, accumulators, finding "last" items, collecting values across iterations.

#### 2.10 Capture Blocks

Replace confusing `{% set %}...{% endset %}` with clearer `{% capture %}`:

```jinja
{# Before: Jinja pattern #}
{% set card_content %}
    <h3>{{ page.title }}</h3>
    <p>{{ page.excerpt }}</p>
{% endset %}
{{ card_content }}

{# After: Kida capture #}
{% capture card_content %}
    <h3>{{ page.title }}</h3>
    <p>{{ page.excerpt }}</p>
{% end %}
{{ card_content }}
```

**Where to use**: Storing rendered fragments for reuse, conditional injection, building up content.

### Phase 3: Pipeline and Functions (Week 3)

#### 3.1 Pipeline Operators

Convert complex filter chains:

```jinja
{# Before (read inside-out) #}
{{ items | selectattr('published') | sort(attribute='date') | reverse | first }}

{# After (read left-to-right) #}
{{ items |> where(published=true) |> sort_by('date') |> reverse |> first }}
```

#### 3.2 True Functions

Convert complex macros to `{% def %}`:

```jinja
{# Before: Jinja macro #}
{% macro card(item, show_date=true) %}
    <div class="card">
        <h3>{{ item.title }}</h3>
        {% if show_date %}
            <span>{{ item.date }}</span>
        {% end %}
    </div>
{% end %}

{# After: Kida function #}
{% def card(item, show_date=true) %}
    <div class="card">
        <h3>{{ item.title }}</h3>
        {% if show_date %}
            <span>{{ item.date }}</span>
        {% end %}
    </div>
{% end %}
```

**Note**: `{% def %}` has lexical scope access - it can access `site`, `config`, etc. from the template context.

#### 3.3 Component Pattern with Slots

Create true composable components using `{% slot %}`:

```jinja
{# partials/alert.html #}
{% def alert(type='info', dismissible=false) %}
    <div class="alert alert-{{ type }}{% if dismissible %} alert-dismissible{% end %}">
        {% slot %}  {# Content injection point #}
        {% if dismissible %}
            <button type="button" class="close" aria-label="Close">×</button>
        {% end %}
    </div>
{% end %}

{# Usage with {% call %} #}
{% call alert('warning', dismissible=true) %}
    <strong>Warning:</strong> Check your input before submitting.
{% end %}

{% call alert('success') %}
    <strong>Success!</strong> Your changes have been saved.
{% end %}
```

**Where to use**: UI components (cards, modals, alerts, buttons), layout wrappers, reusable patterns.

#### 3.4 Spaceless Blocks

Reduce HTML whitespace:

```jinja
{% spaceless %}
<ul>
    {% for item in nav_items %}
    <li><a href="{{ item.url }}">{{ item.title }}</a></li>
    {% end %}
</ul>
{% end %}

{# Output: <ul><li><a href="...">...</a></li><li>...</li></ul> #}
```

#### 3.5 Trim Blocks

More granular whitespace control (trims leading/trailing only):

```jinja
{# Spaceless removes ALL whitespace between tags #}
{# Trim only removes leading/trailing whitespace #}
{% trim %}
    <span class="tag">{{ tag.name }}</span>
{% end %}

{# Useful for inline elements #}
<p>Contact us at {% trim %}{{ email }}{% end %} for more info.</p>
```

**Where to use**: Inline elements, email addresses, small inline components.

#### 3.6 Raw Blocks

Include literal template syntax (for documentation/examples):

```jinja
{# Documentation template showing syntax examples #}
{% raw %}
    To output a variable, use {{ variable_name }}.
    For loops: {% for item in items %}...{% end %}
{% end %}
```

**Where to use**: Template documentation pages, code examples, syntax guides.

#### 3.7 Embed Blocks

Create reusable component patterns:

```jinja
{# partials/card.html #}
<div class="card {{ modifier }}">
    <div class="card-header">{% block header %}Default{% end %}</div>
    <div class="card-body">{% block body %}{% end %}</div>
</div>

{# Usage #}
{% embed 'partials/card.html' %}
    {% block header %}Custom Header{% end %}
    {% block body %}
        <p>Custom content here</p>
    {% end %}
{% end %}
```

### Phase 4: Validation and Testing (Week 3-4)

#### 4.1 Test Suite

```python
# tests/themes/test_default_theme_kida.py

import pytest
from bengal.core.site import Site

class TestDefaultThemeKida:
    """Verify default theme renders correctly with Kida engine."""

    def test_all_templates_parse(self, tmp_site):
        """Every template parses without syntax errors."""
        site = Site(tmp_site, template_engine="kida")
        templates = site.template_engine.list_templates()

        for name in templates:
            # Should not raise
            site.template_engine.get_template(name)

    def test_rendering_parity(self, tmp_site):
        """Converted templates produce identical HTML."""
        # Build with both engines
        jinja_output = build_site(tmp_site, engine="jinja")
        kida_output = build_site(tmp_site, engine="kida")

        # Normalize and compare
        assert normalize_html(jinja_output) == normalize_html(kida_output)

    def test_modern_features_work(self, tmp_site):
        """Modern Kida features render correctly."""
        site = Site(tmp_site, template_engine="kida")

        # Test optional chaining
        tmpl = site.template_engine.from_string("{{ user?.name ?? 'Anonymous' }}")
        assert tmpl.render(user=None) == "Anonymous"
        assert tmpl.render(user={"name": "Alice"}) == "Alice"

        # Test pattern matching
        tmpl = site.template_engine.from_string("""
            {% match x %}
                {% case 'a' %}A
                {% case 'b' %}B
                {% case _ %}Other
            {% end %}
        """)
        assert "A" in tmpl.render(x="a")
        assert "B" in tmpl.render(x="b")
        assert "Other" in tmpl.render(x="c")
```

#### 4.2 Syntax Linting

```python
# bengal/cli/commands/lint_templates.py
"""Lint templates for Kida-native syntax."""

JINJA_PATTERNS = [
    (r'{%\s*endif\s*%}', "Use {% end %} instead of {% endif %}"),
    (r'{%\s*endfor\s*%}', "Use {% end %} instead of {% endfor %}"),
    (r'{%\s*set\s+_\s*=.*\.append\(', "Use {% do list.append() %} for mutations"),
    (r'\|\s*default\(', "Consider {{ x ?? default }} for null coalescing"),
]

def lint_template(path: Path) -> list[LintWarning]:
    """Check template for non-Kida patterns."""
    content = path.read_text()
    warnings = []

    for pattern, message in JINJA_PATTERNS:
        for match in re.finditer(pattern, content):
            line = content[:match.start()].count('\n') + 1
            warnings.append(LintWarning(path, line, message))

    return warnings
```

### Phase 5: Documentation and Polish (Week 4)

#### 5.1 Theming Documentation

Update `site/content/docs/theming/templating/`:

```markdown
# Template Syntax (Kida)

Bengal uses the Kida template engine, a high-performance pure-Python
engine designed for modern template development.

## Modern Features

### Optional Chaining
Access nested properties safely:
\`\`\`jinja
{{ user?.profile?.avatar ?? '/default.png' }}
\`\`\`

### Pattern Matching
Clean type/value switching:
\`\`\`jinja
{% match page.type %}
    {% case 'post' %}...
    {% case 'page' %}...
    {% case _ %}...
{% end %}
\`\`\`

### Pipeline Operators
Readable filter chains:
\`\`\`jinja
{{ items |> where(visible=true) |> sort_by('date') |> take(5) }}
\`\`\`
```

#### 5.2 Migration Guide

Create `docs/migration/jinja-to-kida.md`:

```markdown
# Migrating Templates to Kida-Native Syntax

## Quick Reference

| Jinja2 | Kida-Native | Notes |
|--------|-------------|-------|
| `{% endif %}` | `{% end %}` | Unified end tags |
| `{% set _ = list.append(x) %}` | `{% do list.append(x) %}` | Side effects |
| `{{ x \| default('y') }}` | `{{ x ?? 'y' }}` | Preserves falsy values |
| `{% if x and x.y %}{{ x.y }}` | `{{ x?.y }}` | Optional chaining |
| `{% if not x %}` | `{% unless x %}` | Clearer negation |
| `{% if x %}{% set y = x %}` | `{% with x as y %}` | Nil-resilient |
| `{% set x %}...{% endset %}` | `{% capture x %}...{% end %}` | Capture output |
| `{% for i in range(1, 6) %}` | `{% for i in 1..5 %}` | Range literals |
| `{% macro name() %}` | `{% def name() %}` | True functions |
| `namespace()` workaround | `{% export x = val %}` | Scope escaping |

## Automated Conversion

\`\`\`bash
bengal template convert --to-kida templates/
\`\`\`

## Strict Mode

Kida's strict mode catches undefined variables early:

\`\`\`jinja
{{ typo_var }}  {# UndefinedError instead of silent empty string #}
{{ optional ?? 'default' }}  {# Use ?? for explicit fallbacks #}
\`\`\`
```

#### 5.3 Theme README

Update `bengal/themes/default/README.md`:

```markdown
# Bengal Default Theme

A modern, accessible theme using Kida-native template syntax.

## Template Patterns

### Modern Syntax
- Unified `{% end %}` tags for all blocks
- Optional chaining (`?.`) for safe attribute access
- Null coalescing (`??`) for defaults (preserves falsy values)
- Nil-resilient blocks (`{% with expr as name %}`)
- Pattern matching (`{% match %}`) for clean branching
- Inverted conditionals (`{% unless %}`)
- Range literals (`1..10`, `1..100 by 10`)
- Pipeline operators (`|>`) for readable filter chains

### Component Architecture
- True functions with `{% def %}` (lexical scope)
- Content slots with `{% slot %}` + `{% call %}`
- Block overrides with `{% embed %}`
- Output capture with `{% capture %}`

### Performance Features
- Strict mode (catches undefined variables)
- Bytecode caching enabled
- Constant folding optimization
- Dead code elimination
```

---

## Kida-Native Syntax Reference

### Core Syntax

| Feature | Syntax | Example |
|---------|--------|---------|
| Unified end | `{% end %}` | `{% if x %}...{% end %}` |
| Scoped variable | `{% let x = y %}` | `{% let count = 0 %}` |
| Side effects | `{% do expr %}` | `{% do items.append(x) %}` |
| Export scope | `{% export x = val %}` | `{% export total = total + 1 %}` |
| Capture output | `{% capture x %}...{% end %}` | Store rendered block |

### Modern Features

| Feature | Syntax | Example |
|---------|--------|---------|
| Optional chain | `?.` | `{{ user?.profile?.name }}` |
| Null coalesce | `??` | `{{ name ?? 'Anonymous' }}` |
| Nil-resilient with | `{% with expr as name %}` | `{% with page?.author as a %}` |
| Match | `{% match %}` | Type/value switching |
| Break | `{% break %}` | Exit loop early |
| Continue | `{% continue %}` | Skip iteration |
| Inline if | `for x if cond` | `{% for x in items if x.visible %}` |
| Unless | `{% unless %}` | `{% unless banned %}...{% end %}` |
| Range inclusive | `1..10` | `{% for i in 1..5 %}` (1,2,3,4,5) |
| Range exclusive | `1...11` | `{% for i in 1...6 %}` (1,2,3,4,5) |
| Range with step | `1..10 by 2` | `{% for i in 0..10 by 2 %}` |
| Spaceless | `{% spaceless %}` | Remove HTML whitespace |
| Trim | `{% trim %}` | Trim leading/trailing only |
| Raw | `{% raw %}` | Literal template syntax |
| Embed | `{% embed %}` | Include with overrides |
| Pipeline | `\|>` | `{{ x \|> filter \|> sort }}` |

### Components with Slots

```jinja
{% def alert(type='info') %}
    <div class="alert alert-{{ type }}">
        {% slot %}  {# Content injection point #}
    </div>
{% end %}

{% call alert('warning') %}
    <strong>Warning:</strong> Check your input!
{% end %}
```

### Functions

```jinja
{% def card(item, show_date=true) %}
    <div class="card">
        <h3>{{ item.title }}</h3>
        {% if show_date %}
            <time>{{ item.date }}</time>
        {% end %}
    </div>
{% end %}

{{ card(page) }}
{{ card(page, show_date=false) }}
```

### Fragment Caching

```jinja
{% cache 'sidebar-' ~ site.nav_version %}
    {{ build_nav_tree(site.pages) }}
{% end %}

{% cache 'weather', ttl='5m' %}
    {{ fetch_weather() }}
{% end %}
```

---

## Configuration Changes

### New Default Engine

```python
# bengal/rendering/engines/__init__.py
engine_name = site.config.get("template_engine", "kida")  # Changed from "jinja2"
```

### New Site Scaffold

```python
# bengal/cli/commands/new/config.py
def _create_site_config(site_title: str, baseurl: str) -> dict:
    return {
        "site": {
            "title": site_title,
            "template_engine": "kida",  # Default for new sites
        }
    }
```

### Bytecode Cache and Strict Mode

```python
# bengal/core/site.py
from bengal.rendering.kida.bytecode_cache import BytecodeCache

def _setup_template_engine(self):
    if self.config.template_engine == "kida":
        cache_dir = self.cache_dir / "kida"
        return KidaTemplateEngine(
            self,
            bytecode_cache=BytecodeCache(cache_dir),
            optimized=True,
            strict=True,  # Catch undefined variables early
        )
```

### Strict Mode Benefits

Strict mode catches template errors during development instead of silent failures:

```python
# Without strict mode (Jinja2 default behavior):
{{ typo_var }}  # → empty string (silent failure)

# With strict mode (Kida default):
{{ typo_var }}  # → UndefinedError: Undefined variable 'typo_var'

# Safe patterns for optional values:
{{ optional_var ?? 'default' }}  # → 'default' (explicit fallback)
{{ optional_var | default('fallback') }}  # → 'fallback' (filter-based)
```

**Recommendation**: Default theme should use strict mode to catch typos and missing context variables during development.

---

## Testing Strategy

### Unit Tests

```python
def test_optional_chaining():
    tmpl = env.from_string("{{ user?.profile?.name ?? 'Anonymous' }}")
    assert tmpl.render(user=None) == "Anonymous"
    assert tmpl.render(user={"profile": {"name": "Alice"}}) == "Alice"

def test_pattern_matching():
    tmpl = env.from_string("""
        {% match x %}
            {% case 'a' %}A{% case 'b' %}B{% case _ %}Other
        {% end %}
    """)
    assert "A" in tmpl.render(x="a")
    assert "Other" in tmpl.render(x="c")

def test_pipeline_operators():
    tmpl = env.from_string("{{ items |> sort |> first }}")
    assert tmpl.render(items=[3, 1, 2]) == "1"
```

### Integration Tests

```python
def test_new_site_uses_kida():
    """New sites default to Kida engine."""
    with temp_site() as site:
        assert site.template_engine.__class__.__name__ == "KidaTemplateEngine"

def test_existing_site_keeps_jinja():
    """Sites with explicit jinja config keep Jinja2."""
    with temp_site(config={"site": {"template_engine": "jinja"}}) as site:
        assert site.template_engine.__class__.__name__ == "JinjaTemplateEngine"
```

### Performance Benchmarks

```python
def test_kida_faster_than_jinja(benchmark):
    """Kida renders faster than Jinja2."""
    jinja_time = benchmark_render(engine="jinja", iterations=1000)
    kida_time = benchmark_render(engine="kida", iterations=1000)

    assert kida_time < jinja_time * 0.5  # At least 2x faster
```

---

## Risks and Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| **Breaking existing sites** | Low | High | Explicit engine config preserved |
| **Template syntax errors** | Low | Medium | Comprehensive test suite, rollback plan |
| **Performance regression** | Very Low | Low | Benchmarks before/after |
| **Contributor confusion** | Medium | Low | Clear documentation, examples |
| **Theme compatibility** | Low | Medium | Compatibility checker, warnings |

### Rollback Plan

If issues discovered:
1. **Immediate**: Revert default to `"jinja2"` in `engines/__init__.py`
2. **Short-term**: Keep Kida opt-in while issues resolved
3. **Long-term**: Fix issues, re-enable Kida default

---

## Success Criteria

### Functional

- [ ] All default theme templates use Kida-native syntax
- [ ] Zero `{% endif %}`, `{% endfor %}`, etc. in templates
- [ ] All mutation patterns use `{% do %}`
- [ ] Modern features adopted where beneficial:
  - [ ] `{% unless %}` for negated conditionals
  - [ ] `{% with expr as name %}` for nil-resilience
  - [ ] `?.` and `??` for defensive access
  - [ ] `{% match %}` for type/value switching
  - [ ] Range literals for pagination/ratings
  - [ ] `{% slot %}` for component patterns
- [ ] All tests pass with both engines
- [ ] Rendering parity verified
- [ ] Strict mode enabled (catches undefined variables)

### Performance

- [ ] Kida renders at least 2x faster than Jinja2
- [ ] Cold-start 90%+ faster with bytecode cache
- [ ] Memory usage comparable or better

### Quality

- [ ] Template linting tool available
- [ ] Migration guide complete
- [ ] Documentation updated
- [ ] Theme README updated

---

## Timeline

| Phase | Duration | Deliverables |
|-------|----------|--------------|
| Phase 1: Foundation | Week 1 | Conversion script, end tag conversion, mutation verification |
| Phase 2: Modern Features | Week 2 | `{% unless %}`, `{% with as %}`, `?.`, `??`, `{% match %}`, ranges, `{% export %}`, `{% capture %}` |
| Phase 3: Pipeline & Functions | Week 3 | Pipeline `\|>`, `{% def %}` + `{% slot %}`, `{% spaceless %}`, `{% trim %}`, `{% raw %}`, `{% embed %}` |
| Phase 4: Validation | Week 3-4 | Test suite, syntax linting, parity verification, strict mode |
| Phase 5: Documentation | Week 4 | Docs update, migration guide, README |

**Total**: ~4 weeks

---

## Open Questions

- [x] **Mutation patterns**: Use `{% do %}` for side effects ✅ Resolved
- [x] **Python-style booleans**: Parser recognizes both styles ✅ Resolved
- [ ] **Deprecation timeline**: Support both engines indefinitely
- [ ] **Third-party themes**: Theme authors declare engine requirements in `theme.yaml`

---

## References

### Evidence
- `bengal/rendering/kida/` - Kida engine implementation (220+ files)
- `bengal/themes/default/templates/` - Default theme templates (100+ files)
- `KIDA.md` - Kida architecture and features
- `KIDA_FEEDBACK.md` - Known issues and resolutions
- `KIDA_TEMPLATE_ANALYSIS.md` - Template compatibility analysis

### Related RFCs
- `rfc-kida-modern-syntax-features.md` - Modern syntax features
- `rfc-kida-pure-python-optimizations.md` - AST optimizer pipeline
- `rfc-kida-template-engine.md` - Original Kida RFC
- `rfc-template-engine-agnostic-architecture.md` - Engine abstraction

### External
- Jinja2 documentation: https://jinja.palletsprojects.com/
- Python 3.14t free-threading: PEP 703

---

## Appendix: Template Files Inventory

### High-Priority Templates (Complex Logic)

| Template | Features to Apply |
|----------|-------------------|
| `base.html` | `{% slot %}` components, `{% block required %}` |
| `doc/home.html` | `{% match %}` for page types, `{% export %}` for accumulators |
| `partials/content-components.html` | `{% def %}` + `{% slot %}` for UI components |
| `autodoc/*.html` | `{% with as %}` nil-resilience, `?.` chaining |
| `blog/home.html` | Inline loop filtering, range literals for pagination |

### Medium-Priority Templates (Standard Patterns)

| Template | Features to Apply |
|----------|-------------------|
| `partials/nav.html` | `{% spaceless %}`, `{% cache %}` for nav tree |
| `partials/sidebar.html` | `{% with as %}` for optional sections |
| `partials/footer.html` | `{% unless %}` for conditional links |
| `page/*.html` | `{{ title ?? 'Untitled' }}`, `{{ author?.name }}` |

### Low-Priority Templates (Simple)

| Template | Features to Apply |
|----------|-------------------|
| `partials/head.html` | `{{ meta?.description ?? '' }}` |
| `partials/scripts.html` | `{% unless debug %}` for production-only |
| Error pages | Minimal changes, unified `{% end %}` |

### Feature Application Matrix

| Feature | Where to Use |
|---------|--------------|
| `{% unless %}` | Permission checks, feature flags, debug guards |
| `{% with expr as name %}` | Optional metadata, author profiles, images |
| `{% export %}` | Loop counters, finding last items, accumulators |
| `{% capture %}` | Conditional block injection, template fragments |
| Range literals | Pagination, star ratings, progress bars |
| `{% slot %}` + `{% call %}` | Cards, alerts, modals, buttons, layout wrappers |
| `{% match %}` | Page type icons, status badges, role-based UI |
| `{% spaceless %}` | Navigation, inline lists, compact HTML |
| `{% trim %}` | Inline elements, email addresses |
| `{% raw %}` | Documentation pages showing template examples |

---

## Revision History

### v2.1 (2025-12-26)
- Comprehensive dog fooding review
- Added `{% unless %}` blocks for cleaner negated conditionals
- Added `{% with expr as name %}` for nil-resilience patterns
- Added `{% export %}` examples for scope escaping
- Added `{% capture %}` for output capture
- Added range literals (`1..10`, `1...11`, `1..10 by 2`)
- Added `{% slot %}` component pattern with `{% call %}`
- Added `{% trim %}` for granular whitespace control
- Added `{% raw %}` for literal template syntax
- Added strict mode configuration for undefined variable detection
- Updated Feature Application Matrix for template inventory
- Expanded success criteria with specific feature adoption goals

### v2.0 (2025-12-26)
- Major revision incorporating lessons learned
- Added modern syntax features (optional chaining, null coalescing, etc.)
- Added AST optimizer integration
- Updated with resolved compatibility issues
- Expanded implementation plan with concrete examples
- Added comprehensive testing strategy
- Updated timeline to 4 weeks

### v1.0 (2025-01-27)
- Initial draft
