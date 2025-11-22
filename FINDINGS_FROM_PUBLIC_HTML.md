# Findings from Public HTML Inspection

## Key Discovery

The `site/public/` HTML was built from markdown generated with **OLD templates** (before our fixes).

**Evidence**:
- HTML still shows 6x duplicate "🔍 Compare configurations" (in meta tags + content)
- Markdown source files still have bugs (Sentinel.UNSET, duplicates, excessive blank lines)
- Our template fixes haven't been applied to generate new markdown yet

## What We Found in public/cli/config/diff/index.html

### ✅ Rendered Successfully
- Navigation structure ✓
- Page header ✓
- Badge system ✓  
- Basic content structure ✓

### ❌ Known Issues (From OLD Templates)

1. **Duplicate Content** (6 instances of description)
   - Meta description
   - OG tags (2x)
   - Twitter tags (2x)
   - Page lead paragraph
   - Article content (2x)

2. **Format Issues**
   - Parameters render as individual H3 headings, not tables
   - Excessive spacing between sections
   - Missing default values (filtered but markdown still has blanks)

### Parameter Rendering Style

Current approach: **Individual sections per parameter**
```html
<h3 id="against"><code>against</code></h3>
<p>Environment or file to compare against</p>
<p><strong>Type:</strong><code>text</code></p>
```

Alternative: **Table format** (not currently used)
```markdown
| Name | Type | Default | Required | Description |
|------|------|---------|----------|-------------|
| against | text | - | ✓ | Environment or file... |
```

## Template Design Decision: Sections vs. Tables

The templates import `cli_options` and `cli_arguments` macros (which create tables) but don't use them.

**Current approach** (command_options.md.jinja2):
```jinja2
{% from 'macros/parameter_table.md.jinja2' import cli_options %}  ← IMPORTED
{% set options = element.children | selectattr('element_type', 'equalto', 'option') | list %}
{% if options %}
## Options
{% call(current_item) safe_for(options, "*No options available.*") %}
  {#- Manual rendering with H3 headings -#}  ← NOT USING MACRO
  ### `{{ current_item.name }}`
  ...
{% endcall %}
{% endif %}
```

**Alternative approach** (if using macro):
```jinja2
{% from 'macros/parameter_table.md.jinja2' import cli_options %}
{% set options = element.children | selectattr('element_type', 'equalto', 'option') | list %}
{% if options %}
## Options
{{ cli_options(options) }}  ← USES MACRO (renders table)
{% endif %}
```

## Issue #7: Unused Imports

**Severity**: 🟡 Code Quality

**Files**:
- `bengal/autodoc/templates/cli/partials/command_options.md.jinja2`
- `bengal/autodoc/templates/cli/partials/command_arguments.md.jinja2`

**Problem**: Templates import table macros but manually render instead.

**Options**:

### Option A: Remove Unused Imports (Simple)
```jinja2
{#- Remove line 9 -#}
{% from 'macros/safe_macros.md.jinja2' import safe_render, safe_for %}
{#- cli_options import removed -#}
```

### Option B: Use Table Macros (Compact)
```jinja2
{% from 'macros/parameter_table.md.jinja2' import cli_options %}
{% set options = element.children | selectattr('element_type', 'equalto', 'option') | list %}
{% if options %}
{{ cli_options(options) }}
{% endif %}
```

**Recommendation**: Option A (remove imports) - the detailed heading format provides better UX for CLI docs.

## Why Public HTML Doesn't Show Our Fixes

**Build Pipeline**:
```
1. Extractor (cli.py) → DocElement with metadata
2. Generator + Templates → Markdown files (site/content/)
3. Bengal SSG → HTML files (site/public/)
```

**Current State**:
- ✅ Step 1: Extractor fixed (Sentinel filtering added)
- ✅ Step 2: Templates fixed (6 issues resolved)
- ❌ Step 3: **Markdown not regenerated** (still old)
- ❌ Step 4: **HTML not rebuilt** (from old markdown)

**To see fixes**:
```bash
# Regenerate markdown with new templates
rm -rf site/content/cli/ site/content/api/
python -m bengal.cli utils autodoc
python -m bengal.cli utils autodoc-cli

# Rebuild HTML
cd site
python -m bengal.cli site build
```

## Public HTML Validation Findings

### What's Actually in site/public/

**CLI Documentation**: ✓ Present
- `/cli/config/diff/index.html` - 806 lines
- Multiple commands documented
- Navigation working

**Python API Documentation**: ✓ Present
- `/api/core/site/index.html` - 101KB, 2,665 lines
- Extensive API docs
- URL grouping visible in navigation

**Issues Visible in HTML**:
1. Duplicate descriptions (6x instances)
2. No Sentinel.UNSET (but missing default values → blank spaces)
3. Excessive whitespace (many empty `<p></p>` tags)
4. Navigation structure good (URL grouping working!)

## Correct Diagnosis

**User said**: "parameter tables break after the first entry"

**Reality**:
- Parameters ARE rendering (all of them)
- They render as **H3 headings**, not **table rows**
- This might look "broken" if expecting table format
- Or might refer to visual spacing issues (excessive blank lines)

**Actual Issue**:
- The current output was generated with OLD templates
- Need to regenerate with NEW templates to see improvements

## Next Steps

1. **Clean old documentation**
   ```bash
   rm -rf site/content/cli/ site/content/api/
   ```

2. **Regenerate with fixed templates**
   ```bash
   python -m bengal.cli utils autodoc
   python -m bengal.cli utils autodoc-cli
   ```

3. **Rebuild site**
   ```bash
   cd site
   python -m bengal.cli site build
   ```

4. **Verify fixes in new HTML**
   - Check for duplicate descriptions (should be 1x only)
   - Check for Sentinel values (should be none)
   - Check spacing (should be compact)
   - Check Python API docs (should show methods/attributes)

5. **Optional: Remove unused imports**
   - `command_options.md.jinja2` line 9
   - `command_arguments.md.jinja2` line 9

---

**Status**: Analysis complete, regeneration needed to verify fixes
**Date**: 2025-11-14
**Confidence**: HIGH - we know exactly what needs to be done
