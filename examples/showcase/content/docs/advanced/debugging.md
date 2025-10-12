---
title: Debugging and Development Mode
description: Tools and techniques for debugging Bengal sites, templates, and themes
type: doc
weight: 100
tags: ["debugging", "development", "troubleshooting"]
toc: true
---

# Debugging and Development Mode

**Purpose**: Learn how to debug your Bengal site effectively using built-in tools and development mode features.

## Development Mode

Bengal provides a special **development mode** (`dev_mode`) that enables enhanced debugging features for template development and troubleshooting.

### Enabling Development Mode

Add to your `bengal.toml`:

```toml
[build]
dev_mode = true
```

Or use the command-line flag:

```bash
bengal build --dev-mode
```

### What Development Mode Does

When `dev_mode = true`, Bengal automatically:

1. **Logs undefined variable access** - Instead of silently failing or raising errors, Bengal logs when templates try to access undefined variables
2. **Disables minification** - Keeps HTML readable for debugging
3. **Provides verbose error messages** - More context when things go wrong
4. **Enables template debugging** - Better stack traces for template errors

### Undefined Variable Logging

One of the most powerful features of dev mode is automatic logging of undefined variables:

```jinja2
{# If page.custom_field doesn't exist, you'll see a warning in console #}
<div>{{ page.custom_field }}</div>
```

**Console output:**
```
[WARNING] Template accessed undefined variable: 'custom_field' on page object
  File: templates/page.html, Line: 42
```

This helps you catch:
- Typos in variable names
- Missing frontmatter fields
- Incorrect template assumptions
- Theme compatibility issues

### Strict Mode

For even stricter validation, you can enable `strict_mode`:

```toml
[build]
dev_mode = true
strict_mode = true
```

**Strict mode behavior:**
- **Raises errors** instead of warnings for undefined variables
- Forces you to handle all edge cases
- Useful for production-ready theme development
- Ensures your templates are robust

```{warning} Strict Mode in Production
Only use `strict_mode = true` when you're confident your templates handle all edge cases. It will halt the build on any undefined access.
```

## Debugging Template Functions

### Using the `debug` Filter

Bengal provides a built-in `debug` filter for inspecting variables:

```jinja2
{# Pretty-print the entire page object #}
{{ page | debug }}

{# Inspect specific variables #}
{{ page.metadata | debug }}
```

**Output:**
```
Page Object {
  title: "Getting Started"
  date: 2025-10-11
  tags: ["tutorial", "beginner"]
  content: "# Getting Started\n\n..."
  metadata: {
    word_count: 1250
    reading_time: 5
  }
}
```

### Type Inspection

Use `typeof` to check variable types:

```jinja2
{# What type is this? #}
Type: {{ page.tags | typeof }}
{# Output: Type: list #}

{# Conditional logic based on type #}
{% if page.related is defined and (page.related | typeof) == 'list' %}
  {% for item in page.related %}
    ...
  {% endfor %}
{% endif %}
```

### Detailed Inspection

For comprehensive inspection, use the `inspect` filter:

```jinja2
{{ page | inspect }}
```

**Output includes:**
- Object type
- All attributes
- Method signatures
- Memory address
- Inherited properties

## Common Debugging Scenarios

### Scenario 1: Missing Frontmatter Field

**Problem:**
```jinja2
{# Template expects author field #}
<p>By {{ page.author }}</p>
```

**Without dev_mode:** Silently outputs nothing

**With dev_mode:**
```
[WARNING] Undefined variable 'author' in template 'post.html' at line 23
```

**Solution:**
```jinja2
{# Safe access with default #}
<p>By {{ page.author | default('Anonymous') }}</p>

{# Or conditional #}
{% if page.author is defined %}
  <p>By {{ page.author }}</p>
{% endif %}
```

### Scenario 2: Wrong Variable Type

**Problem:**
```jinja2
{# Assuming tags is always a list #}
{% for tag in page.tags %}
  <span>{{ tag }}</span>
{% endfor %}
```

**Debug:**
```jinja2
{# Check the type first #}
{{ page.tags | typeof | debug }}

{# Safe iteration #}
{% if page.tags is defined and (page.tags | typeof) == 'list' %}
  {% for tag in page.tags %}
    <span>{{ tag }}</span>
  {% endfor %}
{% endif %}
```

### Scenario 3: Template Function Errors

**Problem:**
```jinja2
{# Function fails silently #}
{{ get_data('nonexistent.yaml') }}
```

**With dev_mode:**
```
[ERROR] Failed to load data file 'nonexistent.yaml'
  File: templates/base.html, Line: 15
  Reason: File not found in data directory
```

**Solution:**
```jinja2
{# Check if data exists first #}
{% set features = get_data('features.yaml') %}
{% if features %}
  {% for feature in features %}
    ...
  {% endfor %}
{% endif %}
```

## Template Error Messages

### Understanding Stack Traces

When a template error occurs in dev mode, you get detailed stack traces:

```
TemplateError: division by zero in 'post.html' at line 42

Stack trace:
  File: themes/default/templates/layouts/post.html, line 42
    {{ stats.views | divided_by(0) }}
                      ^^^^^^^^^^^^^

  Called from: themes/default/templates/base.html, line 18
    {% block content %}{% endblock %}

Context:
  stats = {'views': 1250, 'likes': 45}

Suggestion: Check for zero divisor before performing division
```

### Common Error Patterns

```{dropdown} "UndefinedError: 'page' is undefined"

**Cause:** Template trying to access `page` variable in a context where it doesn't exist

**Fix:**
```jinja2
{% if page is defined %}
  {{ page.title }}
{% endif %}
```
```

```{dropdown} "TypeError: 'NoneType' object is not iterable"

**Cause:** Trying to iterate over a None value

**Fix:**
```jinja2
{% for post in posts | default([]) %}
  ...
{% endfor %}
```
```

```{dropdown} "TemplateNotFound: 'custom.html'"

**Cause:** Template file doesn't exist in theme directories

**Fix:** Check theme structure, ensure file exists, or provide fallback:
```jinja2
{% include 'custom.html' ignore missing %}
```
```

## Build Diagnostics

### Verbose Build Output

Use verbose mode for detailed build information:

```bash
bengal build --verbose
```

**Output includes:**
- File discovery details
- Template compilation times
- Cache hit/miss rates
- Incremental build decisions
- Plugin execution logs

### Health Checks

Run health checks to validate your site:

```bash
bengal health
```

**Checks include:**
- Broken internal links
- Missing images
- Invalid frontmatter
- Template syntax errors
- Configuration issues

```{tip} Automated Health Checks
Enable automatic health checks in `bengal.toml`:

```toml
[build]
validate_links = true      # Check for broken links
validate_frontmatter = true # Validate frontmatter syntax
```
```

## Performance Debugging

### Build Performance Analysis

Track build performance:

```bash
bengal build --profile
```

**Output:**
```
Build Performance Report:
  Total: 2.34s

  Phases:
    Content Discovery: 0.12s (5%)
    Template Compilation: 0.45s (19%)
    Page Rendering: 1.23s (53%)
    Asset Processing: 0.34s (15%)
    Post-processing: 0.20s (8%)

  Slowest Pages:
    1. /docs/api-reference/ (0.23s)
    2. /blog/comprehensive-guide/ (0.18s)
    3. /tutorials/advanced-features/ (0.15s)
```

### Template Performance

Identify slow template functions:

```jinja2
{# Time expensive operations #}
{% set start = now() %}
{% set result = expensive_operation() %}
{% set elapsed = (now() - start).total_seconds() %}
{{ "Operation took: " ~ elapsed ~ "s" | debug }}
```

## Best Practices

```{success} Development Workflow
**Recommended setup for active development:**

```toml
[build]
dev_mode = true           # Enable debugging
incremental = true        # Fast rebuilds
cache_templates = false   # Always recompile templates
minify_html = false       # Readable output
strict_mode = false       # Warnings, not errors
```

**For production builds:**

```toml
[build]
dev_mode = false          # Disable debugging overhead
incremental = true        # Still fast
cache_templates = true    # Cache compiled templates
minify_html = true        # Optimize output
strict_mode = false       # Don't halt on edge cases
```
```

```{note} Theme Development
When developing themes, always:

1. Enable `dev_mode = true`
2. Use `bengal serve` for live reload
3. Check console for undefined variable warnings
4. Test with `strict_mode = true` before release
5. Run `bengal health` regularly
```

## Debugging Tools Summary

| Tool | Purpose | When to Use |
|------|---------|-------------|
| `dev_mode = true` | Enhanced debugging | Active development |
| `strict_mode = true` | Strict validation | Theme development, testing |
| `{{ var | debug }}` | Inspect variables | Understanding data structure |
| `{{ var | typeof }}` | Check type | Type-related issues |
| `{{ var | inspect }}` | Detailed inspection | Complex debugging |
| `bengal build --verbose` | Detailed logs | Build issues |
| `bengal health` | Site validation | Pre-deployment |
| `bengal build --profile` | Performance analysis | Optimization |

## Related Documentation

- **[Template Functions Reference](../templates/function-reference/_index.md)** - All available template functions
- **[Health Checks](health-checks.md)** - Site health validation
- **[Variables](variables.md)** - Understanding variable scope
- **[Configuration](../../config-reference.md)** - Complete configuration options

---

```{tip} Quick Start
**Start debugging now:**

1. Add `dev_mode = true` to `bengal.toml`
2. Run `bengal build`
3. Watch console for undefined variable warnings
4. Fix issues using safe access patterns
5. Test with `strict_mode = true` before deploying
```
