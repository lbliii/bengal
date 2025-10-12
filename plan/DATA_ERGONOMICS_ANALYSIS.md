# Data & Template Ergonomics Analysis

**Date:** October 12, 2025  
**Context:** Resume template implementation revealed ergonomic issues

## Problem Discovered

While implementing a data-driven resume template (inspired by Resumake), we hit a Jinja2 gotcha:

```yaml
skills:
  - category: Programming Languages
    items:  # ← Conflicts with dict.items() method!
      - Python
      - JavaScript
```

```jinja2
{% for skill in skill_group.items %}  {# ❌ Accesses .items() method! #}
{% for skill in skill_group['items'] %}  {# ✅ Accesses 'items' field #}
```

## Root Cause

Jinja2's dot notation (`obj.field`) tries these in order:
1. Attribute access (`obj.field`)
2. Dictionary key (`obj['field']`)
3. **But if there's a dict method like `.items()`, it takes precedence!**

This means field names like `items`, `keys`, `values`, `get`, `pop`, etc. cause problems.

## Current State Assessment

### What Bengal Does Well ✅

1. **YAML Parsing** - Using `python-frontmatter` library, works flawlessly
2. **Error Infrastructure** - `bengal/rendering/errors.py` has rich error handling with:
   - Line numbers
   - Source context
   - Syntax highlighting
   - Suggestions
3. **get_data() Function** - Already supports loading external JSON/YAML files
4. **Template Context** - Clean separation between page data and site data

### What Could Be Better 💡

1. **Default Error Visibility**
   - Template errors should show line numbers by default, not just with `--debug`
   - The build "succeeds" but template fails silently

2. **Field Name Safety**
   - No warnings about using reserved dict method names
   - No automatic sanitization or namespacing

3. **Data Validation**
   - No schema validation for structured data
   - Typos in field names fail silently (undefined errors)

4. **Documentation**
   - No guide on "gotchas" like the `.items` issue
   - No examples of data-driven templates beyond `home.html`

## Proposed Improvements

### 1. Better Error Visibility (High Priority)

**Problem:** Template errors are logged but easy to miss

**Solution:**
```python
# In template_engine.py or renderer.py
if template rendering fails:
    - Always show line number (not just in debug mode)
    - Print to stderr immediately
    - Make build fail with exit code 1 (optionally configurable)
```

**Config Option:**
```toml
[build]
strict_template_errors = true  # Fail build on template errors (default: false)
show_template_errors = true    # Always show errors (default: true)
```

### 2. Data Access Helper Filter (Medium Priority)

**Problem:** Dot notation conflicts with dict methods

**Solution:** Add a `field()` filter or `data()` filter:

```jinja2
{# Instead of: #}
{% for skill in skill_group['items'] %}

{# Use: #}
{% for skill in skill_group | field('items') %}

{# Or make it a function: #}
{% for skill in field(skill_group, 'items') %}
```

**Implementation:**
```python
# In bengal/rendering/template_functions/data.py

def field(obj, key, default=None):
    """
    Safe field access that bypasses dict methods.

    Use this when field names might conflict with dict methods
    like 'items', 'keys', 'values', 'get', etc.
    """
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)
```

### 3. Data Schema Validation (Medium Priority)

**Problem:** No validation of structured data, typos fail silently

**Solution:** Optional JSON Schema or Pydantic validation:

```yaml
# In frontmatter
---
title: Resume
schema: resume  # References schemas/resume.json
name: John Doe
...
```

```json
// schemas/resume.json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "object",
  "required": ["name", "contact"],
  "properties": {
    "name": {"type": "string"},
    "contact": {
      "type": "object",
      "properties": {
        "email": {"type": "string", "format": "email"}
      }
    }
  }
}
```

Benefits:
- Catch typos at parse time
- Autocomplete in editors (with JSON Schema)
- Self-documenting templates

### 4. data/ Directory Support (Low Priority)

**Problem:** Large datasets shouldn't go in frontmatter

**Solution:** Already partially implemented with `get_data()`!

Just needs documentation and conventions:

```
content/
  resume/
    index.md         # Minimal frontmatter
data/
  resume.yaml      # All the data
  projects.yaml    # Separate concerns
```

```jinja2
{# In template #}
{% set resume_data = get_data('data/resume.yaml') %}
{% for job in resume_data.experience %}
  ...
{% endfor %}
```

### 5. Template Linting (Nice to Have)

**Problem:** No static analysis of templates

**Solution:** Add a `bengal lint` command that:
- Checks for common gotchas (`.items`, `.keys`, etc.)
- Validates template syntax without building
- Suggests best practices

```bash
$ bengal lint templates/

⚠️  templates/resume/single.html:156
   Using 'skill_group.items' may conflict with dict.items() method
   💡 Consider using skill_group['items'] or skill_group | field('items')
```

## Comparison with Other SSGs

### Hugo
- Uses Go templates, different gotchas
- Has data/ directory support built-in
- Schema validation: No
- Error messages: Good, with line numbers

### Jekyll
- Uses Liquid templates, safer than Jinja2
- data/ directory support: ✅ Excellent (_data/)
- Schema validation: No
- Error messages: Basic

### 11ty
- Multiple template engines
- data/ directory support: ✅ Excellent (_data/)
- Schema validation: Via plugins
- Error messages: Varies by engine

### Bengal's Unique Position
- Python ecosystem (familiar to data scientists, ML engineers)
- Could leverage Pydantic for validation
- Could have best-in-class error messages with our error infrastructure
- Already has `get_data()` - just needs convention

## Recommendations

### Immediate (Next PR)
1. ✅ Fix resume template (done - use `skill_group['items']`)
2. Make template errors more visible (remove need for `--debug`)
3. Add documentation page on data-driven templates

### Short Term (Next Sprint)
1. Add `field()` helper function
2. Create example templates using external data files
3. Document the `.items` gotcha prominently

### Long Term (Backlog)
1. Optional schema validation system
2. Template linting command
3. VSCode extension with template warnings

## Conclusion

**Is the current approach ergonomic?**
- Core architecture: ✅ Yes
- Day-to-day usage: 🟡 Good with gotchas
- Error experience: 🟡 Good but could be better

**Should we refactor?**
- No major refactor needed
- Incremental improvements will have big impact
- The Jinja2 gotcha is a known issue, not a Bengal issue

**Priority:**
1. Error visibility (quick win, big impact)
2. Documentation (help users avoid pitfalls)
3. Helper functions (make gotchas easier to work around)
4. Validation (nice to have, not essential)

## Additional Notes

The resume template itself is a great pattern! Having structured data in YAML that drives a template is much better than putting everything in Markdown. This pattern works well for:

- Resumes/CVs
- Team pages (staff bios)
- Product catalogs
- Event listings
- API documentation
- Data visualizations

We should encourage this pattern and make it easier to use.
