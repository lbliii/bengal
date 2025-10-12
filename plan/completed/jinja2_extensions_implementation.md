# Jinja2 Extensions - Quick Implementation Guide

**Date:** 2025-10-12  
**Status:** 🎯 Ready to Implement  
**Parent:** JINJA2_FEATURE_OPPORTUNITIES.md

## Quick Wins (< 30 minutes)

### 1. Enable Loop Controls & Debug Extensions

**File:** `bengal/rendering/template_engine.py`

```python
# Current (line ~131)
env = Environment(**env_kwargs)

# Updated
env = Environment(
    **env_kwargs,
    extensions=[
        'jinja2.ext.loopcontrols',  # Enable {% break %} and {% continue %}
        'jinja2.ext.debug',          # Enable {% debug %} for development
    ]
)
```

**Benefit:** Immediate access to `{% break %}` and `{% continue %}` in all templates.

### 2. Add Custom Tests

**Create:** `bengal/rendering/template_tests.py`

```python
"""
Custom Jinja2 tests for Bengal templates.

Tests are used with 'is' operator for cleaner conditionals:
  {% if page is draft %} vs {% if page.metadata.get('draft', False) %}
"""

from typing import TYPE_CHECKING, Any
from datetime import datetime

if TYPE_CHECKING:
    from jinja2 import Environment
    from bengal.core.site import Site


def register(env: "Environment", site: "Site") -> None:
    """Register custom template tests."""

    env.tests.update({
        'draft': test_draft,
        'featured': test_featured,
        'outdated': test_outdated,
        'section': test_section,
        'translated': test_translated,
    })


def test_draft(page: Any) -> bool:
    """
    Test if page is a draft.

    Usage:
        {% if page is draft %}
    """
    if not hasattr(page, 'metadata'):
        return False
    return page.metadata.get('draft', False)


def test_featured(page: Any) -> bool:
    """
    Test if page has 'featured' tag.

    Usage:
        {% if page is featured %}
    """
    if not hasattr(page, 'tags'):
        return False
    return 'featured' in page.tags


def test_outdated(page: Any, days: int = 90) -> bool:
    """
    Test if page is older than N days.

    Usage:
        {% if page is outdated %}         # 90 days default
        {% if page is outdated(30) %}     # 30 days
    """
    if not hasattr(page, 'date') or page.date is None:
        return False

    age = (datetime.now() - page.date).days
    return age > days


def test_section(obj: Any) -> bool:
    """
    Test if object is a Section.

    Usage:
        {% if page is section %}
    """
    from bengal.core.section import Section
    return isinstance(obj, Section)


def test_translated(page: Any) -> bool:
    """
    Test if page has translations.

    Usage:
        {% if page is translated %}
    """
    if not hasattr(page, 'translations'):
        return False
    return bool(page.translations)
```

**Update:** `bengal/rendering/template_engine.py`

```python
# Add import
from bengal.rendering.template_tests import register as register_tests

# In _create_environment(), after register_all()
register_tests(env, self.site)
```

**Benefit:** Cleaner template conditionals throughout codebase.

### 3. Immediate Template Improvements

**Update:** `bengal/themes/default/templates/base.html`

```jinja
{# OLD: Lines 58-67 - verbose scoping #}
{% set _lang = current_lang() %}
{% set _i18n = site.config.get('i18n', {}) %}
{% set _rss_href = '/rss.xml' %}
{% if _i18n and _i18n.get('strategy') == 'prefix' %}
    {% set _default_lang = _i18n.get('default_language', 'en') %}
    {% set _default_in_subdir = _i18n.get('default_in_subdir', False) %}
    {% if _lang and (_default_in_subdir or _lang != _default_lang) %}
        {% set _rss_href = '/' ~ _lang ~ '/rss.xml' %}
    {% endif %}
{% endif %}

{# NEW: Scoped with 'with' statement #}
{% with
    lang = current_lang(),
    i18n = site.config.get('i18n', {}),
    default_lang = site.config.get('i18n', {}).get('default_language', 'en'),
    default_in_subdir = site.config.get('i18n', {}).get('default_in_subdir', False)
%}
    {% if i18n and i18n.get('strategy') == 'prefix' and lang and (default_in_subdir or lang != default_lang) %}
        {% set rss_href = '/' ~ lang ~ '/rss.xml' %}
    {% else %}
        {% set rss_href = '/rss.xml' %}
    {% endif %}
    <link rel="alternate" type="application/rss+xml" title="{{ site.config.title }} RSS Feed" href="{{ rss_href }}">
{% endwith %}
```

**Update:** `bengal/themes/default/templates/blog/list.html`

```jinja
{# OLD: No early termination #}
{% for post in posts %}
    {% if post.metadata.get('draft', False) == False %}
        {% include 'partials/article-card.html' with {'article': post} %}
    {% endif %}
{% endfor %}

{# NEW: With custom tests and early break #}
{% for post in posts %}
    {% if post is draft %}{% continue %}{% endif %}
    {% if loop.index > 20 %}{% break %}{% endif %}  {# Performance: max 20 #}
    {% from 'partials/content-components.html' import article_card %}
    {{ article_card(post, show_excerpt=True) }}
{% endfor %}
```

**Update:** `bengal/themes/default/templates/partials/content-components.html`

```jinja
{# OLD: Line 49 - verbose tag check #}
{% if article | has_tag('featured') %}
    <span class="badge badge-featured">⭐ Featured</span>
{% endif %}

{# NEW: With custom test #}
{% if article is featured %}
    <span class="badge badge-featured">⭐ Featured</span>
{% endif %}
```

---

## Testing Changes

### Run Test Suite
```bash
# All template tests
pytest tests/unit/test_template*.py -v

# Specific macro tests
pytest tests/unit/test_template_macros.py -v

# Integration tests
pytest tests/integration/ -v
```

### Test in Showcase
```bash
cd examples/showcase
bengal build --strict
bengal serve
```

### Manual Testing Checklist
- [ ] Homepage renders correctly
- [ ] Blog list shows featured posts
- [ ] Draft posts are hidden
- [ ] i18n RSS links work
- [ ] Component preview still works
- [ ] No console errors
- [ ] `{% debug %}` works in dev mode

---

## Rollout Strategy

### Step 1: Add Extensions (No Breaking Changes)
```bash
# Edit template_engine.py
# Run tests
pytest tests/unit/
# Commit
git add bengal/rendering/template_engine.py
git commit -m "feat: enable Jinja2 loop controls and debug extensions"
```

### Step 2: Add Custom Tests (Additive)
```bash
# Create template_tests.py
# Update template_engine.py to register tests
# Run tests
pytest tests/unit/
# Commit
git add bengal/rendering/template_tests.py bengal/rendering/template_engine.py
git commit -m "feat: add custom Jinja2 tests (draft, featured, outdated, etc.)"
```

### Step 3: Update Templates (Gradual Refactor)
```bash
# Update one template at a time
# Test after each change
# Commit incrementally
git add bengal/themes/default/templates/base.html
git commit -m "refactor: use 'with' statement for scoped i18n vars in base.html"

git add bengal/themes/default/templates/blog/list.html
git commit -m "refactor: use custom tests and loop controls in blog list"
```

---

## Feature Flags (Optional Safety)

If concerned about breaking changes, add feature flags:

```python
# In bengal.toml (user config)
[features]
jinja2_extensions = true        # Default: true
jinja2_custom_tests = true      # Default: true

# In template_engine.py
if self.site.config.get('features', {}).get('jinja2_extensions', True):
    extensions = ['jinja2.ext.loopcontrols', 'jinja2.ext.debug']
else:
    extensions = []

env = Environment(..., extensions=extensions)
```

**Recommendation:** Don't add flags - these are standard features and low risk.

---

## Documentation Updates

### 1. Template Function Reference
**Update:** `examples/showcase/content/docs/templates/tests.md` (new file)

```markdown
# Template Tests

Tests are used with the `is` operator to check conditions.

## Built-in Tests

- `defined` - Check if variable is defined
- `undefined` - Check if variable is undefined
- `none` - Check if value is None
- `even` - Check if number is even
- `odd` - Check if number is odd
- `divisibleby(n)` - Check if divisible by n

## Custom Tests

### `is draft`
Check if page is a draft.

```jinja
{% if page is draft %}
  <span class="badge">Draft</span>
{% endif %}
```

### `is featured`
Check if page has 'featured' tag.

```jinja
{% for post in posts %}
  {% if post is featured %}
    {{ article_card(post, show_image=True) }}
  {% endif %}
{% endfor %}
```

[... more examples ...]
```

### 2. Component README
**Update:** `bengal/themes/default/dev/components/README.md`

Add section:
```markdown
## Using Loop Controls

Bengal enables Jinja2's loop control extensions:

```jinja
{# Break out of loop early #}
{% for post in posts %}
  {% if loop.index > 10 %}{% break %}{% endif %}
  {{ article_card(post) }}
{% endfor %}

{# Skip items #}
{% for user in users %}
  {% if user is draft %}{% continue %}{% endif %}
  {{ user.name }}
{% endfor %}
```
```

---

## Performance Impact

### Loop Controls
✅ **Positive** - Early break saves rendering time
- Before: Iterate all posts (potential 100s)
- After: Stop at 10 items
- Savings: Up to 90% in large loops

### Custom Tests
✅ **Neutral** - Function call overhead negligible
- Simple boolean checks
- No database queries
- Cached at template compile time

### With Statement
✅ **Neutral** - Same performance, better scope hygiene
- No runtime overhead
- Prevents accidental variable pollution

---

## Migration Path for Users

**Good News:** Zero breaking changes!

All new features are:
- ✅ Additive (don't break existing code)
- ✅ Optional (old patterns still work)
- ✅ Backward compatible

Users can migrate at their own pace:

```jinja
{# Old pattern - still works #}
{% if page.metadata.get('draft', False) %}

{# New pattern - cleaner #}
{% if page is draft %}

{# Both work simultaneously during migration #}
```

---

## Success Criteria

- [ ] Extensions enabled without test failures
- [ ] 5+ custom tests implemented
- [ ] 5+ templates refactored
- [ ] Documentation updated
- [ ] Showcase site demonstrates features
- [ ] No performance regression (< 1% build time increase)

---

**Next Action:** Implement Step 1 (Extensions) - 10 minutes  
**Estimated Total Time:** 2-3 hours for all phases  
**Risk Level:** 🟢 Low
