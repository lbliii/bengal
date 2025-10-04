# Showcase Site Issues

**Date:** October 4, 2025

## 🐛 Critical Issue: Variable Substitution in Documentation Pages

### The Problem

The showcase site has **11 Jinja2 template errors**, all from documentation pages that show template syntax examples:

```
⚠️  Build completed with warnings (11):

   Jinja2 Template Errors (11):
   ├─ kitchen-sink.md → No filter named 'truncatewords'
   ├─ function-reference/_index.md → No filter named 'truncatewords'
   ├─ function-reference/math.md → unexpected char '#' at 16482
   ├─ function-reference/urls.md → No filter named 'absolute_url'
   ├─ output/output-formats.md → expected token 'end of print statement', got ':'
   ├─ function-reference/dates.md → No filter named 'time_ago'
   ├─ function-reference/strings.md → No filter named 'truncatewords'
   ├─ function-reference/seo.md → No filter named 'meta_description'
   ├─ function-reference/collections.md → unexpected char '#' at 18809
   ├─ index.md → No filter named 'truncatewords'
   └─ tutorials/migration/from-hugo.md → unexpected '/'
```

### Root Cause

**VariableSubstitutionPlugin is trying to evaluate Jinja2 filter syntax in documentation:**

Documentation pages contain examples like:

```markdown
## Example Usage

```jinja2
{{ text | truncatewords(50) }}
````
```

**What happens:**
1. Page has `preprocess: false` in frontmatter
2. `preprocess: false` only disables old Jinja2 preprocessing (legacy path)
3. **But VariableSubstitutionPlugin is ALWAYS active** in Mistune parser
4. Plugin sees `{{ text | truncatewords(50) }}` in markdown text
5. Tries to evaluate it as a variable expression
6. Fails because it doesn't support filter syntax (only simple variables)

### The Architecture Issue

From `bengal/rendering/pipeline.py`:

```python
def process_page(self, page: Page) -> None:
    # Check if preprocessing is disabled
    if page.metadata.get('preprocess') is False:
        # Parse without variable substitution (for docs showing template syntax)
        parsed_content, toc = self.parser.parse_with_toc(
            page.content,
            page.metadata
        )
    else:
        # Single-pass parsing with variable substitution - fast and simple!
        context = {
            'page': page,
            'site': self.site,
            'config': self.site.config
        }
        parsed_content, toc = self.parser.parse_with_toc_and_context(
            page.content,
            page.metadata,
            context
        )
```

**BUT!** `parse_with_toc()` still uses a Mistune parser that has VariableSubstitutionPlugin registered!

From `bengal/rendering/parser.py`:

```python
def parse_with_toc(self, content: str, metadata: Dict[str, Any]) -> tuple[str, str]:
    """Parse Markdown and extract TOC (WITHOUT variable substitution)."""
    # ...
    # Create parser without VariableSubstitutionPlugin
    md = self._mistune.create_markdown(
        plugins=[
            'table',
            'strikethrough',
            'task_lists',
            'url',
            'footnotes',
            'def_list',
            create_documentation_directives(),
            # NO VariableSubstitutionPlugin here!
        ],
        renderer='html',
    )
```

**This SHOULD work!** But let me check if there's a bug...

### Verification Needed

Looking at the code, `parse_with_toc()` should NOT have VariableSubstitutionPlugin. But the errors suggest it's still being applied somehow.

**Possible causes:**
1. Parser caching is reusing a parser with the plugin
2. The plugin is being added somewhere else
3. The `preprocess: false` check isn't working

### Example Error Case

File: `function-reference/_index.md`

```markdown
---
title: "Template Functions Reference"
preprocess: false  ← THIS SHOULD DISABLE VARIABLE SUBSTITUTION!
---

| Function | Example |
|----------|---------|
| `truncatewords` | `{{ text | truncatewords(50) }}` |
                              ^^^^^^^^^^^^^^^^^^^
                              Plugin tries to evaluate this!
```

**Expected:** `{{ text | truncatewords(50) }}` stays literal (just markdown text)  
**Actual:** Plugin tries to evaluate it and fails: "No filter named 'truncatewords'"

## 📊 Performance Issue: Parallel vs Sequential Mode

### The Problem

Build output shows "Mode: sequential" even though `bengal.toml` has `parallel = true`:

```toml
[build]
parallel = true
```

But build stats show:

```
⚙️  Build Configuration:
   └─ Mode:        sequential
```

### Root Cause

From `bengal/utils/build_stats.py`:

```python
def display_build_stats(stats: BuildStats, ...) -> None:
    mode_parts = []
    if stats.incremental:
        mode_parts.append(click.style("incremental", fg='yellow'))
    if stats.parallel:
        mode_parts.append(click.style("parallel", fg='yellow'))
    if not mode_parts:  # ← THIS LINE!
        mode_parts.append(click.style("sequential", fg='yellow'))
```

**The logic is:**
- If incremental=False AND parallel=False → show "sequential"
- If parallel=True → show "parallel"

**So the warning was wrong!** The build I ran WAS in parallel mode:

```
parallel = True
build_stats = BuildStats(parallel=True)  ✓
```

But the terminal output from earlier showed "sequential", which means `stats.parallel = False` somehow.

### Verification

Running `bengal build --parallel` shows "Mode: parallel" ✓

So this might be a case of the config not being passed correctly, or an earlier build being sequential.

## 🔧 Fixes Required

### 1. Fix Variable Substitution in Documentation

**Option A: Check preprocess flag in plugin**

Modify `VariableSubstitutionPlugin` to check page metadata:

```python
def __init__(self, context: Dict[str, Any], enabled: bool = True):
    self.context = context
    self.enabled = enabled  # NEW

def _substitute_variables(self, text: str) -> str:
    if not self.enabled:
        return text  # Skip substitution
    # ... rest of logic ...
```

**Option B: Don't use VariableSubstitutionPlugin for preprocess:false**

In `parser.py`, check `preprocess` in both code paths:

```python
def parse_with_toc(self, content: str, metadata: Dict[str, Any]) -> tuple[str, str]:
    # Check if variable substitution is disabled
    if metadata.get('preprocess') is False:
        # Use parser WITHOUT VariableSubstitutionPlugin
        # (current code already does this!)
    else:
        # Use parser WITH VariableSubstitutionPlugin
```

**Option C: Escape all template syntax in docs**

Use Hugo-style escaping in all documentation:

```markdown
{{/* text | truncatewords(50) */}}
```

This renders as: `{{ text | truncatewords(50) }}`

**Recommendation:** Option A or B (code fix) is better than Option C (content fix).

### 2. Verify Parallel Mode Config

Check that `bengal.toml` `parallel = true` is correctly passed to BuildStats.

## 📝 Action Items

### Immediate (High Priority)

1. **Debug why `preprocess: false` isn't disabling VariableSubstitutionPlugin**
   - Add logging to see which parser is being used
   - Check if parser caching is causing issues
   - Verify the conditional logic in pipeline.py

2. **Fix VariableSubstitutionPlugin to respect preprocess flag**
   - Implement Option A or B above
   - Test with showcase site
   - Verify all 11 errors are resolved

3. **Document the escape syntax**
   - Add examples of {{/* ... */}} to docs
   - Explain when to use preprocess: false
   - Clarify the difference between markdown {{}} and template {{}}

### Medium Priority

4. **Add per-page build timing**
   - Show which pages are slow
   - Help identify optimization targets
   - Add to build stats output

5. **Profile directive parsing**
   - Measure tabs vs admonitions vs other directives
   - Identify the slowest operations
   - Consider caching strategies

### Low Priority

6. **Consider directive caching**
   - Cache parsed directive AST
   - Only re-parse when content changes
   - Could provide 30-50% speedup

## 🎯 Expected Outcomes

### After Fixes

1. **No template errors** in showcase site build ✓
2. **Clear documentation** on when to use `preprocess: false`
3. **Proper escape syntax** examples in docs
4. **Parallel mode** correctly reflected in stats

### Performance

- Build time will remain ~7-9 seconds (this is expected for directive-heavy content)
- Incremental builds will be fast (only changed pages)
- Documentation will explain performance characteristics

---

**Status:** Issues identified, fixes designed, ready to implement.

