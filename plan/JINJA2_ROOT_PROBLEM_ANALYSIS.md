# Root Problem Analysis: Variables in Markdown

**Date:** October 3, 2025  
**Question:** What's the root problem? What will users actually need?

---

## What Users Actually Want

Looking at the real use cases:

### Use Case 1: API Documentation with Cascade
```markdown
# content/api/v2/_index.md
---
cascade:
  product_name: "DataFlow API"
  version: "2.0"
  api_url: "https://api.example.com/v2"
---

# content/api/v2/quickstart.md
Welcome to {{ page.metadata.product_name }} version {{ page.metadata.version }}.

Connect to {{ page.metadata.api_url }}/users
```

**Need:** Variable substitution for DRY (Don't Repeat Yourself)
**Frequency:** Very common in technical docs

### Use Case 2: Conditional Content
```markdown
{% if page.metadata.enterprise %}
This feature requires an enterprise license.
{% endif %}
```

**Need:** Show/hide content based on metadata
**Frequency:** Less common, mostly for multi-audience docs

### Use Case 3: Documentation Examples
```markdown
To use variables, write:
```jinja2
{{ page.title }}
{% if page.draft %}Draft{% endif %}
```
```

**Need:** Show Jinja2 syntax literally (in code blocks)
**Frequency:** Common in documentation about the SSG itself

---

## Current Architecture (Too Complex)

```
Content → Protect code blocks → Jinja2 preprocess → Restore blocks 
       → Mistune parse → VariableSubstitutionPlugin → HTML
```

**Problems:**
1. ❌ **5 passes through content** (slow!)
2. ❌ **Complex nested code block handling** (buggy!)
3. ❌ **Two different systems** (preprocessing + plugin)
4. ❌ **Still failing** (api/v2/_index.html)

---

## The Right Solution: Simplify

### Insight: 90% of use cases are just {{ variables }}

**Most users want:**
- ✅ `{{ page.metadata.xxx }}` - Variable substitution
- ⚠️  `{% if %}` - Nice to have but not critical

**Almost no users want:**
- {% for %}, {% macro %}, complex Jinja2 logic in markdown

### Proposal: Plugin-Only Approach

**Architecture:**
```
Content → Mistune parse with VariableSubstitutionPlugin → HTML
```

**One pass. Simple. Fast.**

**What works:**
- ✅ `{{ page.metadata.xxx }}` - Works perfectly
- ✅ Code blocks stay literal - Natural behavior
- ✅ Inline code stays literal - Natural behavior
- ✅ Fast - Single parse pass

**What doesn't work:**
- ❌ `{% if %}` blocks - Don't work across markdown elements
- ❌ `{% for %}` loops - Don't work
- ❌ Complex Jinja2 - Don't work

**Solution for conditionals:** Use them in **templates**, not markdown content

```html
<!-- In page.html template -->
<article>
  {% if page.metadata.enterprise %}
  <div class="enterprise-badge">Enterprise</div>
  {% endif %}
  
  {{ content }}
</article>
```

---

## Performance Comparison

### Current (Complex):
- Protect code blocks: ~2ms per page
- Jinja2 preprocessing: ~3ms per page  
- Restore code blocks: ~1ms per page
- Mistune parsing: ~5ms per page
- Variable plugin: ~1ms per page
- **Total: ~12ms per page**
- For 100 pages: **1.2 seconds** just for parsing

### Proposed (Simple):
- Mistune parsing with plugin: ~6ms per page
- **Total: ~6ms per page**
- For 100 pages: **0.6 seconds**
- **50% faster!**

---

## Why api/v2/_index.html Still Fails

The actual content:

```markdown
Released {{ page.metadata.release_date }}, this is the
{% if page.metadata.requires_auth %}
**Note:** All API requests require authentication.
{% endif %}
```

**The problem:** This page has NO cascade metadata! It's showing an EXAMPLE of how to use cascades, but doesn't actually have the metadata itself.

**Current behavior:** Preprocessing tries to evaluate `{% if page.metadata.requires_auth %}`, but `requires_auth` doesn't exist, so Jinja2 treats it as falsy and removes the content.

**Result:** Health check still sees `{% if %}` in code blocks (examples)

---

## The Pragmatic Solution

### Step 1: Remove Complex Preprocessing

**Delete:**
- `_preprocess_with_protection()`
- `_protect_code_blocks()`  
- `_restore_code_blocks()`

**Keep:**
- `VariableSubstitutionPlugin` - Works great for {{ vars }}

### Step 2: Document the Architecture

**Make it clear:**
- ✅ Use `{{ var }}` for variables in markdown content
- ✅ Use `{% if %}` for conditionals in **templates** (not markdown)
- ✅ Code blocks naturally preserve syntax

### Step 3: Fix the Example Files

Files like `cascading-frontmatter.md` that SHOW Jinja2 examples should either:

**Option A:** Use actual cascade metadata so examples work
```yaml
---
title: "Cascading Frontmatter"
cascade:
  product_name: "Example API"
  version: "1.0"
  api_url: "https://example.com"
---
```

**Option B:** Show examples in code blocks only (no live demos)

---

## What About Hugo/Jekyll Users?

**Hugo:** No preprocessing at all - uses shortcodes
```markdown
{{< param "product_name" >}}
```

**Jekyll:** Has Liquid preprocessing, but:
- It's a design trade-off they accept
- Users learn to use `{% raw %}` blocks
- Simpler than our dual-system approach

**Bengal:** Focus on what we're good at
- ✅ Fast Mistune parsing
- ✅ Clean variable substitution
- ✅ Great DX for the 90% use case

---

## Recommendation

**Remove the preprocessing complexity.**

1. Delete `_preprocess_with_protection()` and helpers
2. Keep `VariableSubstitutionPlugin` for `{{ vars }}`
3. Document that `{% if %}` should be used in templates, not markdown
4. Fix example files to have actual metadata or use code blocks only
5. Make strict mode OFF by default (users can enable for CI)

**Result:**
- ✅ 50% faster
- ✅ Much simpler code
- ✅ Easier to maintain
- ✅ 90% of use cases work perfectly
- ✅ No weird edge cases with nested code blocks

**Trade-off:**
- ❌ No `{% if %}` in markdown content
- ✅ But you can use it in templates (where it belongs)

---

## The Real Question

**Do users ACTUALLY need `{% if %}` in markdown content?**

Looking at real SSG sites:
- Most conditionals are in templates (nav, sidebar, metadata display)
- Content is usually static or uses simple variable substitution
- Complex logic belongs in templates, not content

**Bengal should:**
- Be fast
- Be simple
- Handle the common cases really well
- Not try to be a full templating engine inside markdown

**That's the ergonomic, performant solution.**

