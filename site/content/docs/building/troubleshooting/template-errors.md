---
title: Template Errors
nav_title: Templates
description: Diagnosing and fixing template syntax errors, undefined variables, and missing templates
weight: 10
category: guide
icon: alert-triangle
---
# Template Error Troubleshooting

Bengal provides rich error messages for template issues. This guide helps you understand and resolve common template errors.

## Understanding Template Errors

When Bengal encounters a template error, it displays:

- **Error type** - What kind of error (syntax, undefined variable, unknown filter)
- **Location** - File path and line number
- **Code context** - Surrounding lines with the error highlighted
- **Suggestions** - Potential fixes based on the error type
- **Search paths** - All directories Bengal checked for templates

## Enabling Proactive Validation

Catch template errors early by enabling validation in your config:

```toml
[build]
validate_templates = true
```

This validates all templates during build, even those not used by every page. Combine with `strict_mode = true` for CI/CD pipelines.

## Common Error Types

### Syntax Errors

**Symptoms:**
- `unexpected '}'`
- `expected token 'end of statement block'`
- `Unexpected end of template`

**Causes:**
- Unclosed tags (`{% if ... %}` without `{% endif %}`)
- Missing closing brackets
- Invalid Jinja2 syntax

**Example error:**
```
⚠️  Template Syntax Error in partials/nav.html:15

    14 | {% for item in menu.items %}
  > 15 |   <li>{{ item.name }
    16 | {% endfor %}

Error: unexpected end of template, expected 'end of print statement'
```

**Fix:** Add the missing `}}`:
```jinja
<li>{{ item.name }}</li>
```

---

### Undefined Variables

**Symptoms:**
- `'variable_name' is undefined`
- `'dict object' has no attribute 'key'`

**Causes:**
- Typo in variable name
- Variable not passed to template context
- Accessing dict key that doesn't exist

**Example error:**
```
⚠️  Undefined Variable in page.html:8

Error: 'titel' is undefined

💡 Suggestions:
   1. Common typo: try 'title' instead
   2. Use safe access: {{ titel | default('fallback') }}
   3. Add 'titel' to page frontmatter
```

**Fix options:**
1. Correct the typo: `{{ title }}` instead of `{{ titel }}`
2. Use safe access: `{{ page.metadata.get('custom_field', 'default') }}`
3. Use the `default` filter: `{{ variable | default('fallback') }}`

---

### Unknown Filters

**Symptoms:**
- `No filter named 'filter_name'`

**Causes:**
- Typo in filter name
- Using a filter from another SSG (Hugo, Jekyll, etc.)
- Custom filter not registered

**Example error:**
```
⚠️  Unknown Filter in page.html:12

Error: No filter named 'in_section'

💡 Suggestions:
   1. Bengal doesn't have 'in_section' filter.
      Check if the page is in a section using: {% if page.parent %}

Did you mean:
   • intersection
   • int
```

**Common filter migrations:**

| From Hugo/Jekyll | Bengal Equivalent |
|-----------------|-------------------|
| `markdownify` | `markdown` |
| `truncatewords` | `truncate` with word mode |
| `in_section` | `{% if page.parent %}` |
| `is_ancestor` | Compare `page.url` values |

---

### Template Not Found

**Symptoms:**
- `TemplateNotFound: template_name.html`

**Causes:**
- Typo in template name
- Template in wrong directory
- Theme not installed or misconfigured

**Example error:**
```
⚠️  Template Error

Error: TemplateNotFound: partials/sidebar.html

🔍 Template Search Paths:
   1. /site/templates
   2. /site/themes/custom/templates
   3. /bengal/themes/default/templates
```

**Diagnosis:**
1. Check the search paths listed in the error
2. Verify the template exists in one of those directories
3. Check for case sensitivity issues
4. Ensure theme is correctly configured

**Fix:**
- Create the missing template in `templates/` or `themes/your-theme/templates/`
- Fix the template name in your code
- Check theme configuration in `bengal.toml`

---

## Template Search Path Order

Bengal searches for templates in this order:

1. **Site templates** - `your-site/templates/`
2. **Theme templates** - `your-site/themes/theme-name/templates/`
3. **Installed themes** - Via Python entry points
4. **Bundled themes** - Bengal's built-in themes
5. **Default theme** - Ultimate fallback

Templates in higher-priority directories override lower ones.

## Best Practices

### Use Safe Access for Optional Data

```jinja
{# Safe access for metadata that might not exist #}
{{ page.metadata.get('custom_field', 'default_value') }}

{# Or use the default filter #}
{{ page.custom_field | default('fallback') }}
```

### Check Variables Before Use

```jinja
{% if page.metadata.author %}
  <p>By {{ page.metadata.author }}</p>
{% endif %}
```

### Enable Validation in Development

```toml
# bengal.toml
[build]
validate_templates = true
debug = true
```

### Enable Strict Mode in CI

```toml
# config/environments/ci.yaml
build:
  validate_templates: true
  strict_mode: true
```

## Getting Help

If you're stuck:

1. **Check the full error message** - Bengal provides detailed context
2. **Review template search paths** - Ensure templates are in the right location
3. **Enable debug mode** - Set `debug = true` for more verbose output
4. **Check the template documentation** - See [Template Functions](../../reference/template-functions.md)
