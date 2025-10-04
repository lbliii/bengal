# Escape Syntax Design Options - Bug #3 Analysis

## Problem Statement

The current escape syntax `{{/* expr */}}` conflicts with Markdown emphasis (`*/` is treated as italic), causing it to be split before our variable substitution plugin can process it.

**Current broken behavior:**
```
Input:  Use {{/* page.title */}} to display...
Output: Use {{/<em> page.title </em>/}} to display...
```

## Design Options

### Option 1: Change Escape Syntax (RECOMMENDED)

**Use `{{% expr %}}` instead of `{{/* expr */}}`**

#### Pros:
- ✅ No conflict with Markdown syntax
- ✅ Similar to Hugo's "passthrough" shortcode syntax
- ✅ Clean, simple to remember
- ✅ Easy to implement (just change regex)
- ✅ Visually distinct from regular `{{ }}`

#### Cons:
- ⚠️ Breaking change for existing content
- ⚠️ Need to update all documentation
- ⚠️ Users who learned `{{/* */}}` need to relearn

#### Implementation:
```python
# In variable_substitution.py
ESCAPE_PATTERN = re.compile(r'\{\{%\s*(.+?)\s*%\}\}')
```

**Example:**
```markdown
Use {{% page.title %}} to display the page title.
Format dates with {{% page.date | format_date('%Y-%m-%d') %}}.
```

**Output:**
```html
Use {{ page.title }} to display the page title.
Format dates with {{ page.date | format_date('%Y-%m-%d') }}.
```

---

### Option 2: Use Existing `preprocess: false` Flag

**Already implemented! Just document better.**

#### Pros:
- ✅ Already works perfectly
- ✅ No code changes needed
- ✅ File-level control
- ✅ Zero conflicts with Markdown

#### Cons:
- ⚠️ All-or-nothing per file (can't mix real + escaped variables)
- ⚠️ Requires frontmatter
- ⚠️ Less flexible for inline examples

#### Usage:
```markdown
---
title: "Template Reference"
preprocess: false  # ← Disable variable substitution
---

All {{ variables }} stay literal.
All {% tags %} stay literal.
Perfect for template documentation pages.
```

**Best for:** Entire pages that are template documentation.

---

### Option 3: Raw HTML Markers

**Use HTML comments as delimiters**

#### Syntax:
```markdown
Use <!--{{--> {{ page.title }} <!--}}-->to display the page title.
```

#### Pros:
- ✅ No Markdown conflicts
- ✅ HTML comments are invisible
- ✅ Flexible

#### Cons:
- ❌ Ugly and verbose
- ❌ Hard to type
- ❌ Confusing for users
- ❌ Difficult to spot in source

**Verdict:** Too complex, poor UX.

---

### Option 4: Backtick Escaping

**Use inline code for examples**

#### Syntax:
```markdown
Use `{{ page.title }}` to display the page title.
```

#### Pros:
- ✅ Already works! (code blocks are naturally literal)
- ✅ Zero implementation needed
- ✅ Natural for code examples
- ✅ No conflicts

#### Cons:
- ⚠️ Shows with `<code>` styling
- ⚠️ Not suitable for inline prose
- ⚠️ Can't show multiple examples in one sentence

**Example:**
> Use `{{ page.title }}` to display the page title.

**Renders as:**
> Use <code>{{ page.title }}</code> to display the page title.

**Best for:** Code-like examples and function signatures.

---

### Option 5: Jinja2 String Literals (Template-Level)

**Already works in Jinja2 templates!**

#### Syntax (in .html templates):
```jinja2
Use {{ '{{ page.title }}' }} to display the page title.
```

#### Pros:
- ✅ Works perfectly in templates
- ✅ No special handling needed
- ✅ Standard Jinja2 feature

#### Cons:
- ❌ Only works in .html templates, not .md files
- ❌ Doesn't help with Markdown content

**Best for:** Template documentation pages (not markdown).

---

### Option 6: Two-Pass Processing

**Parse Markdown first, then substitute variables in HTML**

#### Approach:
1. Parse markdown to HTML (no variable substitution)
2. Apply variable substitution to HTML output
3. Use special markers for escapes

#### Pros:
- ✅ No Markdown conflicts (HTML is already parsed)
- ✅ Could support `{{/* */}}` syntax
- ✅ More control

#### Cons:
- ❌ Complex implementation
- ❌ Performance impact (two full passes)
- ❌ Harder to debug
- ❌ Variables in headings won't work for TOC
- ❌ Architectural change

**Verdict:** Over-engineered for the problem.

---

### Option 7: Custom Markdown Extension

**Create a Mistune plugin for escape blocks**

#### Syntax:
```markdown
Use {{escape}}{{ page.title }}{{/escape}} to display...
```

#### Pros:
- ✅ Complete control
- ✅ No Markdown conflicts
- ✅ Extensible

#### Cons:
- ❌ Verbose
- ❌ Complex implementation
- ❌ Custom syntax (not standard)
- ❌ Harder to learn

**Verdict:** Too much complexity for the benefit.

---

## Comparison Matrix

| Option | Conflicts | Inline Use | Ease of Use | Implementation | Breaking Change |
|--------|-----------|------------|-------------|----------------|-----------------|
| **1. `{{% %}}`** | ✅ None | ✅ Yes | ⭐⭐⭐⭐⭐ | Easy | Yes (minor) |
| **2. `preprocess: false`** | ✅ None | ❌ No | ⭐⭐⭐⭐ | Already done | No |
| **3. HTML comments** | ✅ None | ⚠️ Ugly | ⭐⭐ | Medium | Yes |
| **4. Backticks** | ✅ None | ⚠️ Styled | ⭐⭐⭐⭐⭐ | Already done | No |
| **5. String literals** | ✅ None | ❌ Templates only | ⭐⭐⭐ | Already done | No |
| **6. Two-pass** | ✅ None | ✅ Yes | ⭐⭐ | Hard | Yes |
| **7. Custom extension** | ✅ None | ⚠️ Verbose | ⭐⭐ | Hard | Yes |

---

## Recommendation: Hybrid Approach

### **Primary: Option 1 - Change to `{{% %}}`**

Fix the inline escape syntax with a simple, non-conflicting pattern:

```markdown
Use {{% page.title %}} to display the page title.
Site name: {{% site.title %}}
```

### **Secondary: Document Existing Options**

The other options already work! Just need better documentation:

1. **`preprocess: false`** - For full documentation pages
2. **Backticks** - For code-like examples: `` `{{ var }}` ``
3. **Code blocks** - Already literal automatically

### Migration Path

1. **Update regex** in `variable_substitution.py`:
   ```python
   ESCAPE_PATTERN = re.compile(r'\{\{%\s*(.+?)\s*%\}\}')
   ```

2. **Add backward compatibility** (temporary):
   ```python
   LEGACY_ESCAPE_PATTERN = re.compile(r'\{\{/\*\s*(.+?)\s*\*/\}\}')
   # Log warning when found
   ```

3. **Update documentation** with examples of all 3 approaches

4. **Migration script** to help users update:
   ```bash
   bengal migrate escape-syntax
   ```

---

## Alternative: Keep `{{/* */}}` but Fix It

### Using Zero-Width Spaces

Insert zero-width spaces to break up the `*/`:
```python
def save_escaped(match):
    expr = match.group(1).strip()
    # Use zero-width space to prevent Markdown parsing
    return f"{{{{/\u200B* {expr} *\u200B/}}}}"
```

#### Pros:
- ✅ No breaking change
- ✅ Keeps Hugo compatibility

#### Cons:
- ❌ Hacky solution
- ❌ Invisible characters are confusing
- ❌ May break copy/paste
- ❌ Potential edge cases

**Verdict:** Clever but fragile. Not recommended.

---

## Decision Criteria

**Choose Option 1 (`{{% %}}`) if:**
- ✅ You want a clean, long-term solution
- ✅ Breaking change is acceptable
- ✅ Migration effort is reasonable

**Choose Option 2 (`preprocess: false`) if:**
- ✅ You want zero breaking changes
- ✅ Documentation pages are okay without inline escapes
- ✅ Simplicity is priority #1

**Use Both if:**
- ✅ You want maximum flexibility
- ✅ Different use cases need different solutions

---

## Implementation Plan (Recommended)

### Phase 1: Immediate (Keep backward compat)
1. Add `{{% %}}` syntax support
2. Keep `{{/* */}}` working (with warning)
3. Update tests to use `{{% %}}`

### Phase 2: Documentation
1. Update all docs to show `{{% %}}`
2. Document the 3 approaches (inline, file-level, code blocks)
3. Add migration guide

### Phase 3: Future (v1.0)
1. Deprecate `{{/* */}}` syntax
2. Remove legacy support
3. Clean up code

---

## Conclusion

**RECOMMENDED: Option 1 (`{{% %}}`) + Document existing options**

This gives users:
- **Inline escaping:** `{{% expr %}}` for mixed content
- **File-level:** `preprocess: false` for full doc pages
- **Code styling:** Backticks for code examples

All three approaches serve different use cases, making Bengal flexible and powerful.

The `{{% %}}` syntax is:
- ✅ Clean and simple
- ✅ No Markdown conflicts
- ✅ Easy to implement
- ✅ Familiar (similar to Hugo)
- ✅ Future-proof

**Next step:** Decide on migration strategy and implement.

