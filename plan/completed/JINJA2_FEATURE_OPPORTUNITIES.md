# Jinja2 Feature Opportunities for Bengal SSG

**Date:** 2025-10-12  
**Status:** 📋 Analysis  
**Source:** [Jinja2 Template Designer Documentation](https://jinja.palletsprojects.com/en/stable/templates/)

## Executive Summary

Bengal SSG is already leveraging many Jinja2 features well, including:
- ✅ **Template inheritance** (base.html → child templates)
- ✅ **Macros** (recently migrated, 13 macro-based components)
- ✅ **Filters** (30+ custom filters)
- ✅ **Global functions** (80+ template functions)
- ✅ **Autoescape** with `select_autoescape(["html", "xml"])`
- ✅ **Whitespace control** (`trim_blocks`, `lstrip_blocks`)
- ✅ **Bytecode caching** for performance
- ✅ **Strict mode** for development

However, there are **7 valuable features** from the Jinja2 documentation that Bengal is **not currently using** but could significantly benefit from:

---

## 1. 🎯 **Jinja2 Extensions** (High Value)

### Current Status
Bengal's `template_engine.py` creates the Environment without any extensions enabled:

```python
# bengal/rendering/template_engine.py:131
env = Environment(**env_kwargs)  # No extensions parameter
```

### Opportunities

#### A. **Loop Controls Extension** (`jinja2.ext.loopcontrols`)
**Value:** High for complex template logic

```jinja
{# Current workaround - cumbersome #}
{% for post in posts %}
    {% if loop.index > 10 %}
        {# Can't break out of loop! #}
    {% endif %}
{% endfor %}

{# With loop controls extension #}
{% for post in posts %}
    {% if loop.index > 10 %}{% break %}{% endif %}
    {{ post.title }}
{% endfor %}

{# Skip certain items #}
{% for user in users %}
    {% if loop.index is even %}{% continue %}{% endif %}
    {{ user.name }}
{% endfor %}
```

**Use Cases in Bengal:**
- Breaking out of expensive rendering loops early
- Skipping draft posts in production builds
- Conditional rendering based on loop state

#### B. **Debug Extension** (`jinja2.ext.debug`)
**Value:** Medium for theme development

```jinja
{# Dump context for debugging #}
{% debug %}

{# Output: Shows all available variables, filters, and tests #}
{'context': {'page': <Page object>, 'site': <Site object>, ...},
 'filters': ['abs', 'batch', 'capitalize', ...],
 'tests': ['defined', 'divisibleby', 'even', ...]}
```

**Use Cases in Bengal:**
- Component preview development
- Theme developer ergonomics
- Debugging complex template contexts
- Integration with `bengal health` command

#### C. **i18n Extension** (`jinja2.ext.i18n`)
**Value:** High for internationalization

Bengal has i18n support but not using Jinja2's built-in extension:

```jinja
{# Current approach - manual functions #}
{{ _("Hello World") }}  # Custom function

{# With i18n extension - standardized #}
{% trans %}Hello World!{% endtrans %}

{# With variables #}
{% trans name=user.name %}Hello {{ name }}!{% endtrans %}

{# Pluralization #}
{% trans count=items|length %}
    There is {{ count }} item.
{% pluralize %}
    There are {{ count }} items.
{% endtrans %}
```

**Benefits:**
- Standard Babel integration
- Extraction tools (pybabel extract)
- Better tooling support
- Cleaner template syntax

**Implementation:**
```python
# In template_engine.py
from jinja2.ext import i18n
env.add_extension('jinja2.ext.i18n')
env.install_gettext_translations(translations)  # Or callables
```

---

## 2. 🧪 **Custom Tests** (Medium Value)

### Current Status
Bengal has 30+ **filters** but **no custom tests**. Tests are used with the `is` operator for cleaner conditional logic.

### Opportunities

```python
# Add to template_engine.py
def test_draft(page):
    """Test if page is a draft."""
    return page.metadata.get('draft', False)

def test_featured(page):
    """Test if page has featured tag."""
    return 'featured' in getattr(page, 'tags', [])

def test_outdated(page, days=90):
    """Test if page is older than N days."""
    if not page.date:
        return False
    age = (datetime.now() - page.date).days
    return age > days

env.tests['draft'] = test_draft
env.tests['featured'] = test_featured
env.tests['outdated'] = test_outdated
```

**Usage in Templates:**
```jinja
{# Current approach - verbose #}
{% if page.metadata.get('draft', False) %}
{% if page | has_tag('featured') %}

{# With custom tests - cleaner #}
{% if page is draft %}
{% if page is featured %}
{% if page is outdated(30) %}  {# 30 days #}

{# Negation #}
{% if page is not draft %}

{# Logical combinations #}
{% if page is featured and page is not outdated %}
```

**Recommended Tests:**
- `is draft` - Check draft status
- `is featured` - Check featured tag
- `is outdated(days)` - Check content freshness
- `is translated` - Check if page has translations
- `is section` - Check if object is a section
- `is api_page` - Check if autodoc page
- `is empty` - Check if collection is empty (cleaner than `|length == 0`)

---

## 3. 📦 **With Statement for Scoped Variables** (Medium Value)

### Current Status
Bengal uses `{% set %}` throughout templates, which can lead to variable pollution.

### Opportunity

```jinja
{# Current approach - variable pollution #}
{% set i18n_config = site.config.get('i18n', {}) %}
{% set default_lang = i18n_config.get('default_language', 'en') %}
{% set prefix_strategy = i18n_config.get('strategy') == 'prefix' %}
{# These variables are now in scope for the entire template #}

{# With 'with' statement - scoped #}
{% with
    i18n_config = site.config.get('i18n', {}),
    default_lang = i18n_config.get('default_language', 'en'),
    prefix_strategy = i18n_config.get('strategy') == 'prefix'
%}
    {# Use variables here #}
    {% if prefix_strategy %}
        {{ default_lang }}
    {% endif %}
{% endwith %}
{# Variables no longer accessible here #}
```

**Use Cases:**
- Complex i18n logic (already present in base.html:58-67)
- Image processing metadata
- Temporary calculations
- Component-local state

**Example from Base.html:**
```jinja
{# Current: Lines 58-67 #}
{% set _lang = current_lang() %}
{% set _i18n = site.config.get('i18n', {}) %}
{% set _rss_href = '/rss.xml' %}
{% if _i18n and _i18n.get('strategy') == 'prefix' %}
    {# ... complex logic ... #}
{% endif %}

{# Better: Scoped #}
{% with
    lang = current_lang(),
    i18n = site.config.get('i18n', {}),
    rss_href = '/rss.xml'
%}
    {% if i18n and i18n.get('strategy') == 'prefix' %}
        {# ... complex logic ... #}
    {% endif %}
{% endwith %}
```

---

## 4. 🎭 **Call Blocks** (Low-Medium Value)

### Current Status
Not used. Macros are used for composition but not callable blocks.

### Opportunity

Call blocks allow you to pass template content *into* a macro as a callable:

```jinja
{# Define a macro that accepts a caller #}
{% macro card(title) %}
<div class="card">
    <h3>{{ title }}</h3>
    <div class="card-body">
        {{ caller() }}  {# Renders the content passed in #}
    </div>
</div>
{% endmacro %}

{# Use with call block #}
{% call card("Featured Post") %}
    <p>This is the card content.</p>
    <a href="/post/">Read more</a>
{% endcall %}

{# Output: #}
<div class="card">
    <h3>Featured Post</h3>
    <div class="card-body">
        <p>This is the card content.</p>
        <a href="/post/">Read more</a>
    </div>
</div>
```

**Advanced: Parametrized Callers**
```jinja
{% macro list_users(users) %}
<ul>
{% for user in users %}
    <li>{{ caller(user) }}</li>  {# Pass user to caller #}
{% endfor %}
</ul>
{% endmacro %}

{% call(user) list_users(all_users) %}
    <strong>{{ user.name }}</strong> ({{ user.email }})
{% endcall %}
```

**Use Cases for Bengal:**
- Wrapper components (cards, alerts, panels)
- Layout components with custom content
- Conditional wrappers
- Advanced component composition

**Example:**
```jinja
{# In content-components.html #}
{% macro alert(type='info') %}
<div class="alert alert-{{ type }}">
    {{ caller() }}
</div>
{% endmacro %}

{# Usage #}
{% from 'partials/content-components.html' import alert %}
{% call alert('warning') %}
    <strong>Warning:</strong> This page is outdated!
{% endcall %}
```

---

## 5. 🔗 **Block Nesting and Scoping** (Low Value, but good to know)

### Current Status
Bengal uses block inheritance extensively but may not be aware of advanced scoping.

### Advanced Patterns

#### A. **Access Parent Block Content**
```jinja
{# base.html #}
{% block title %}My Site{% endblock %}

{# child.html #}
{% block title %}{{ super() }} - Blog Post{% endblock %}
{# Output: "My Site - Blog Post" #}
```

**Already used in Bengal** (base.html:9):
```jinja
{% block title %}{{ page.title | default(site.config.title) }}{% if page and page.title %} - {{ site.config.title }}{% endif %}{% endblock %}
```

#### B. **Named Block End Tags**
```jinja
{# More readable for large blocks #}
{% block content %}
    {# 100+ lines #}
{% endblock content %}

{% block scripts %}
    {# Many scripts #}
{% endblock scripts %}
```

**Recommendation:** Use for blocks over 50 lines in Bengal templates.

#### C. **Block Nesting**
```jinja
{# Blocks can be defined inside other blocks #}
{% block content %}
    <article>
        {% block article_content %}{% endblock %}
    </article>
{% endblock %}
```

---

## 6. 📝 **Template Comments with Line Statements** (Low Value)

### Current Status
Bengal uses `{# ... #}` comments extensively.

### Opportunity

If you set `line_statement_prefix` (e.g., `##`), you can use line-based syntax:

```python
# In template_engine.py
env = Environment(
    ...
    line_statement_prefix='##',
    line_comment_prefix='###',
)
```

```jinja
{# Current syntax #}
{% if condition %}
    {{ value }}
{% endif %}

{# With line statements #}
## if condition
    {{ value }}
## endif

{# Line comments #}
### This is a comment
```

**Recommendation:** **Don't use this** for Bengal. It's non-standard and reduces portability. The default syntax is fine.

---

## 7. 🔍 **Better Error Messages with `required` Blocks** (Medium Value)

### Current Status
Macros don't validate required parameters well.

### Opportunity

While Jinja2 doesn't have native required parameters, Bengal can add validation:

```jinja
{# Current - silent failure #}
{% macro pagination(current_page, total_pages, base_url) %}
{% if total_pages > 1 %}
    {# Breaks if parameters are undefined #}
{% endif %}
{% endmacro %}

{# With validation #}
{% macro pagination(current_page, total_pages, base_url) %}
{% if not current_page %}
    {{ _fail("pagination: 'current_page' is required") }}
{% endif %}
{% if not total_pages %}
    {{ _fail("pagination: 'total_pages' is required") }}
{% endif %}
{% if not base_url %}
    {{ _fail("pagination: 'base_url' is required") }}
{% endif %}
{# ... rest of macro ... #}
{% endmacro %}
```

**Implementation:**
```python
# In template_engine.py
def fail_template(message):
    """Raise an error in templates."""
    from jinja2 import TemplateError
    raise TemplateError(message)

env.globals['_fail'] = fail_template
```

**Better Alternative:** Use `StrictUndefined` (already enabled in strict mode!)
```python
# Already in Bengal - good!
if self.site.config.get("strict_mode", False):
    env_kwargs["undefined"] = StrictUndefined
```

This means undefined variables already fail in `bengal serve` mode.

---

## 8. 🎨 **Inline If Expressions** (Already Used Well!)

### Current Status
✅ **Already using this extensively**

```jinja
{# Bengal already uses ternary expressions #}
{% set variant = variant | default('default') %}
<div class="{{ 'active' if item.active else '' }}">
```

**Keep doing this!** It's clean and Pythonic.

---

## Priority Recommendations

### 🔴 **High Priority - Implement Now**

1. **Enable Loop Controls Extension**
   - Immediate value for performance (early breaks)
   - Better template logic
   - Minimal migration effort

2. **Add Custom Tests**
   - Cleaner template syntax
   - Better readability (`is draft` vs checking metadata)
   - Easy to add incrementally

3. **Enable i18n Extension** (if not breaking)
   - Standard Babel integration
   - Better tooling
   - Future-proof for multilingual sites
   - **Caveat:** Needs migration assessment

### 🟡 **Medium Priority - Consider for v1.0**

4. **Use `with` Statement for Complex Scopes**
   - Prevents variable pollution
   - Better code organization
   - Refactor existing templates incrementally

5. **Add Debug Extension**
   - Better theme developer experience
   - Integrate with `bengal health`
   - Controlled by config flag

6. **Use Call Blocks for Wrapper Components**
   - More flexible component API
   - Better composition patterns
   - Add to new components only

### 🟢 **Low Priority - Nice to Have**

7. **Named Block End Tags**
   - Use for blocks > 50 lines
   - Style guide recommendation
   - No implementation needed

---

## Implementation Plan

### Phase 1: Extensions (Week 1)

```python
# bengal/rendering/template_engine.py

from jinja2.ext import debug, loopcontrols

env = Environment(
    loader=...,
    autoescape=...,
    trim_blocks=True,
    lstrip_blocks=True,
    extensions=[
        'jinja2.ext.loopcontrols',  # Enable break/continue
        'jinja2.ext.debug',          # Enable {% debug %}
    ],
    ...
)
```

**Testing:**
```bash
# Run existing tests to ensure no breakage
pytest tests/unit/test_template*.py
```

### Phase 2: Custom Tests (Week 1-2)

```python
# bengal/rendering/template_tests.py (new file)

def register_tests(env, site):
    """Register custom template tests."""

    def is_draft(page):
        return page.metadata.get('draft', False)

    def is_featured(page):
        return 'featured' in getattr(page, 'tags', [])

    def is_outdated(page, days=90):
        if not page.date:
            return False
        from datetime import datetime
        age = (datetime.now() - page.date).days
        return age > days

    env.tests['draft'] = is_draft
    env.tests['featured'] = is_featured
    env.tests['outdated'] = is_outdated

# In template_engine.py
from bengal.rendering.template_tests import register_tests
...
register_tests(env, site)
```

### Phase 3: Template Refactoring (Week 2-3)

Update templates to use new features:

1. **Add `{% break %}` to expensive loops**
   ```jinja
   {# In partials/content-components.html #}
   {% for post in all_posts %}
       {% if loop.index > 10 %}{% break %}{% endif %}
       {{ article_card(post) }}
   {% endfor %}
   ```

2. **Replace verbose conditionals with tests**
   ```jinja
   {# Old #}
   {% if page.metadata.get('draft', False) %}

   {# New #}
   {% if page is draft %}
   ```

3. **Scope i18n logic with `with`**
   ```jinja
   {# In base.html #}
   {% with i18n=site.config.get('i18n', {}), ... %}
       {# i18n logic #}
   {% endwith %}
   ```

### Phase 4: Documentation (Week 3)

1. Update theme documentation
2. Add examples to component README
3. Update template function reference
4. Add migration guide for theme developers

---

## Risks and Considerations

### Extensions
- ✅ **Low risk** - Jinja2 built-in, well-tested
- ❓ **i18n extension** - May conflict with existing i18n system, needs audit

### Custom Tests
- ✅ **Low risk** - Additive, doesn't break existing code
- ✅ **High value** - Cleaner templates immediately

### Call Blocks
- ⚠️ **Medium complexity** - New pattern for theme developers
- 📚 **Requires documentation** - Examples and best practices

### With Statement
- ✅ **Low risk** - Standard Jinja2 feature
- 🔄 **Refactoring effort** - Need to update existing templates

---

## Examples of Impact

### Before (Current)
```jinja
{# Verbose and error-prone #}
{% for post in site.regular_pages %}
    {% if post.metadata.get('draft', False) == False %}
        {% if 'featured' in post.tags if post.tags else [] %}
            {% if loop.index <= 5 %}
                {{ article_card(post) }}
            {% endif %}
        {% endif %}
    {% endif %}
{% endfor %}
```

### After (With New Features)
```jinja
{# Clean and readable #}
{% for post in site.regular_pages %}
    {% if loop.index > 5 %}{% break %}{% endif %}
    {% if post is not draft and post is featured %}
        {{ article_card(post) }}
    {% endif %}
{% endfor %}
```

**Benefits:**
- 60% less code
- More readable
- Easier to maintain
- Better performance (early break)

---

## Success Metrics

- ✅ Extensions enabled without breaking tests
- ✅ 5+ custom tests implemented
- ✅ 10+ templates refactored to use new patterns
- ✅ Documentation updated
- ✅ Showcase site uses new features as examples
- ✅ Theme developer feedback collected

---

## Next Steps

1. ✅ Create this analysis document
2. ⏭️ Get feedback on priorities
3. ⏭️ Implement Phase 1 (Extensions)
4. ⏭️ Implement Phase 2 (Custom Tests)
5. ⏭️ Refactor templates (Phase 3)
6. ⏭️ Update documentation (Phase 4)

---

## References

- [Jinja2 Template Designer Documentation](https://jinja.palletsprojects.com/en/stable/templates/)
- [Jinja2 Extensions API](https://jinja.palletsprojects.com/en/stable/extensions/)
- Bengal Template Engine: `bengal/rendering/template_engine.py`
- Bengal Template Functions: `bengal/rendering/template_functions/`
- Theme README: `bengal/themes/default/dev/components/README.md`

---

**Last Updated:** 2025-10-12  
**Reviewers:** @llane  
**Status:** 📋 Ready for Review
