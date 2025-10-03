# Template Syntax Escaping in Bengal

## Problem

When writing documentation about Bengal's template system, we need to show Jinja2 syntax literally (like `{{ toc }}` or `{% for %}`) without it being processed.

## Why {% raw %} Doesn't Work

Bengal has a **two-stage Jinja2 rendering pipeline**:

1. **Stage 1 - Markdown Preprocessing** (`_preprocess_content` in `pipeline.py` line 184):
   - Markdown content is processed through Jinja2
   - Allows variables like `{{ page.metadata.author }}` in markdown
   
2. **Stage 2 - Template Rendering** (`render_page` in `renderer.py` line 39):
   - Parsed HTML is wrapped in templates (base.html, page.html, etc.)
   - Final page assembly with CSS, navigation, etc.

**The Issue**: `{% raw %}...{% endraw %}` blocks can span between these stages, causing:
- Template rendering errors
- Broken CSS links  
- Missing navigation/styling
- Incomplete page structure

## Solution: String Literals

Use **string literals** in Jinja2 expressions:

```jinja2
{{ '{{ toc }}' }}           # Shows: {{ toc }}
{{ '{{ page.title }}' }}    # Shows: {{ page.title }}
{{ '{% for x in y %}' }}    # Shows: {% for x in y %}
```

### How It Works

1. **Stage 1**: `{{ '{{ toc }}' }}` is evaluated → outputs `{{ toc }}` as text
2. Markdown parser converts to HTML (inside code blocks if applicable)
3. **Stage 2**: The text `{{ toc }}` is now part of content, not a template expression

### Examples

**In regular text**:
```markdown
Use {{ '{{ page.title }}' }} to display the page title.
```

**In code blocks**:
````markdown
```jinja2
{{ '{{ toc }}' }}
{{ '{% if condition %}' }}
  Content
{{ '{% endif %}' }}
```
````

**Complex expressions**:
```jinja2
{{ '{{ site.pages | filter("draft", false) | sort("date") }}' }}
```

## Alternative: Disable Preprocessing (Not Recommended)

Could modify `_preprocess_content` to skip certain pages, but this:
- Loses the useful feature of variables in markdown
- Requires configuration for each documentation page
- More complex than using string literals

## Documentation Updates ✅

### Updated Files:

1. **`examples/quickstart/content/docs/template-system.md`**:
   - Added prominent note in Overview section linking to escaping docs
   - Created comprehensive "Escaping Template Syntax" section with:
     - Basic escaping examples
     - Code block examples
     - Common use cases
     - Detailed explanation of why `{% raw %}` doesn't work
     - Quick reference table
     - Pro tip about .html vs .md files

2. **`examples/quickstart/content/docs/advanced-markdown.md`**:
   - Added "Showing Template Syntax in Documentation" subsection under Table of Contents
   - Practical examples with string literals
   - Clear warning about `{% raw %}` blocks
   - Link to complete documentation in template-system.md

### Key Documentation Points:

- ✅ String literal syntax clearly explained: `{{ '{{ variable }}' }}`
- ✅ Why `{% raw %}` breaks (two-stage rendering)
- ✅ Multiple practical examples
- ✅ Quick reference for common cases
- ✅ Cross-references between docs
- ✅ Prominent callout in main template docs

## Testing ✅

Verified with Python script (`test_escape_methods.py`):
- String literals work correctly: `{{ '{{ toc }}' }}` → outputs `{{ toc }}`
- `{% raw %}` confirmed to cause issues in two-stage rendering
- Multiple escape patterns tested

## Best Practices

✅ **Do**:
- Use `{{ '{{ variable }}' }}` for showing template syntax
- Use string literals in code blocks
- Document why we don't use `{% raw %}`

❌ **Don't**:
- Use `{% raw %}...{% endraw %}` in markdown content
- Try to escape across rendering stages
- Assume standard Jinja2 escaping works the same in Bengal

## Related Code

- `bengal/rendering/pipeline.py:184-224` - `_preprocess_content()` method
- `bengal/rendering/pipeline.py:42-81` - `process_page()` two-stage rendering
- `bengal/rendering/renderer.py:39-101` - `render_page()` template assembly

