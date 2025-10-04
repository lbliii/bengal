# Showcase Site Template Escaping Fix

**Date:** October 4, 2025  
**Status:** Completed ✅

## Problem

The showcase site had 11 Jinja2 template errors caused by documentation files containing template syntax examples that were being processed instead of displayed as literal text.

### Errors Found

```
Jinja2 Template Errors (11):
   ├─ content/docs/output/output-formats.md
   │  └─ expected token 'end of print statement', got ':'
   ├─ content/docs/markdown/kitchen-sink.md
   │  └─ No filter named 'truncatewords'.
   ├─ content/docs/templates/function-reference/collections.md
   │  └─ unexpected char '#' at 18809
   ├─ content/docs/templates/function-reference/urls.md
   │  └─ No filter named 'absolute_url'.
   ├─ content/docs/templates/function-reference/_index.md
   │  └─ No filter named 'truncatewords'.
   ├─ content/docs/templates/function-reference/dates.md
   │  └─ No filter named 'time_ago'.
   ├─ content/docs/templates/function-reference/math.md
   │  └─ unexpected char '#' at 16482
   ├─ content/docs/templates/function-reference/strings.md
   │  └─ No filter named 'truncatewords'.
   ├─ content/docs/templates/function-reference/seo.md
   │  └─ No filter named 'meta_description'.
   ├─ content/index.md
   │  └─ No filter named 'truncatewords'.
   └─ content/tutorials/migration/from-hugo.md
      └─ unexpected '/'
```

## Solution

Used the Hugo-style escape pattern `{{/* ... */}}` that was already implemented in `bengal/rendering/plugins/variable_substitution.py`.

### How It Works

The `VariableSubstitutionPlugin` includes an escape pattern:
- **Input:** `{{/* expression */}}`
- **Output:** `{{ expression }}` (literal text)

This allows documentation to show template syntax examples without them being processed.

## Files Fixed

### Manual Fixes (Complex Patterns)

1. **kitchen-sink.md** - Escaped `truncatewords` examples and variable substitution demos
2. **output-formats.md** - Escaped JSX code with `dangerouslySetInnerHTML={{ __html: page.content_html }}`
3. **collections.md** - Escaped template syntax in examples

### Bulk Fixes (sed replacements)

4. **strings.md** - 30+ `truncatewords` examples
5. **urls.md** - 22 `absolute_url` examples
6. **dates.md** - 24 `time_ago` examples
7. **seo.md** - 17 `meta_description` examples
8. **_index.md** - 6 `truncatewords` examples
9. **index.md** - 1 `truncatewords` example
10. **from-hugo.md** - Multiple Hugo template syntax examples

## Example Transformations

### Before
```jinja2
{{ post.content | truncatewords(50) }}
```

### After
```jinja2
{{/* post.content | truncatewords(50) */}}
```

### Rendering
When processed through the pipeline:
- Stage 1: `{{/* ... */}}` → `{{ ... }}` (escape pattern processed)
- Stage 2: `{{ ... }}` rendered as literal text in final HTML

## Verification

Build completed successfully with no Jinja2 template errors:

```bash
cd examples/showcase
python -m bengal.cli build
# ✅ No errors or warnings found!
```

## Benefits

1. **Documentation can show template examples** without them being executed
2. **No need for complex workarounds** like using string literals
3. **Consistent with Hugo's approach** for users familiar with that ecosystem
4. **Clean, readable markdown** source files

## Related Files

- `/bengal/rendering/plugins/variable_substitution.py` - Escape pattern implementation
- `/bengal/rendering/pipeline.py` - Variable substitution integration
- `/examples/quickstart/content/docs/template-system.md` - Example usage documented

## Commands Used

```bash
# Bulk escape patterns using sed
sed -i.bak 's/{{ \([^}]*\)FILTER\([^}]*\) }}/{{\/\* \1FILTER\2 *\/}}/g' FILE.md

# Where FILTER was: truncatewords, absolute_url, time_ago, meta_description
```

## Notes

- The escape pattern is processed at the AST level during markdown parsing
- Code blocks naturally stay literal (not processed by variable substitution)
- This approach is architectural aligned: content (markdown) vs logic (templates)
- Works seamlessly with Bengal's two-stage rendering process

## Next Steps

- ✅ All showcase site template errors fixed
- ✅ Build completes successfully
- 📝 Consider documenting this pattern in user-facing docs
- 📝 Add to migration guide for users coming from other SSGs

