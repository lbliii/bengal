# Blog Template Fix Analysis

**Date**: 2025-10-12  
**Issue**: Blog sections created by `bengal init` fail to render with undefined variable errors

## Root Cause

The blog/list.html template expects pagination variables (`total_pages`, `current_page`, `base_url`, `total_posts`) but these are only provided for specific page types.

### Current Behavior

**Template Expectations** (`blog/list.html` lines 35-40, 176-177):
```jinja2
{% if total_pages %}
<p class="blog-count">
    Showing {{ posts | length }} of {{ total_posts }} posts
    {% if current_page > 1 %}(Page {{ current_page }} of {{ total_pages }}){% endif %}
</p>
{% endif %}

{% if total_pages and total_pages > 1 %}
{{ pagination(current_page, total_pages, base_url) }}
{% endif %}
```

**Context Provider** (`bengal/rendering/renderer.py` lines 198-238):
```python
def _add_generated_page_context(self, page: Page, context: dict[str, Any]) -> None:
    page_type = page.metadata.get("type")

    if page_type in ("archive", "api-reference", "cli-reference", "tutorial"):
        # ✅ These get pagination context
        # ❌ "blog" type is NOT in this list!
```

### The Problem

1. **Manual `_index.md` with `type: blog`** → No pagination context → Template errors
2. **Auto-generated archive** with `type: archive`** → Gets pagination context → Works fine

## Type Confusion

There are actually TWO different concepts being mixed:

| Type | Purpose | Template | Gets Pagination |
|------|---------|----------|----------------|
| `blog` | Content type for individual blog posts | `blog/single.html` | N/A |
| `archive` | Generated list page for sections | `archive.html` or `blog/list.html` | ✅ Yes |

**The Issue**: Our `bengal init` creates sections with `type: blog` expecting it to work for section indexes, but that's not how Bengal's architecture works.

## Long-Term Solutions

### Option 1: Make Blog Type Work for Sections ✅ RECOMMENDED

**Modify**: `bengal/rendering/renderer.py`

```python
def _add_generated_page_context(self, page: Page, context: dict[str, Any]) -> None:
    page_type = page.metadata.get("type")

    # Add "blog" to the list
    if page_type in ("archive", "blog", "api-reference", "cli-reference", "tutorial"):
        # Provide pagination context
```

**Pros**:
- Intuitive: `type: blog` works for blog sections
- Fixes the immediate problem
- Aligns with user expectations
- Minimal code change

**Cons**:
- Conflates blog content type with blog section type
- May need additional logic to distinguish post vs section

### Option 2: Make Template Defensive

**Modify**: `bengal/themes/default/templates/blog/list.html`

```jinja2
{# Use defaults for optional pagination variables #}
{% set total_pages = total_pages | default(1) %}
{% set current_page = current_page | default(1) %}
{% set total_posts = total_posts | default(posts | length if posts else 0) %}
{% set base_url = base_url | default(section.url if section else '/blog/') %}

{# Then use them safely #}
{% if total_pages > 1 %}
<p class="blog-count">
    Showing {{ posts | length }} of {{ total_posts }} posts
    {% if current_page > 1 %}(Page {{ current_page }} of {{ total_pages }}){% endif %}
</p>
{% endif %}
```

**Pros**:
- Template works with OR without pagination context
- No rendering errors
- Backward compatible

**Cons**:
- Doesn't fix the architectural issue
- Each template needs defensive coding
- Pagination won't actually work (just won't error)

### Option 3: Use Correct Type in bengal init

**Modify**: `bengal/cli/commands/init.py`

```python
def _infer_section_type(section_name: str) -> str:
    section_lower = section_name.lower()

    if section_lower in ['blog', 'posts', 'articles', 'news']:
        return 'archive'  # Not 'blog'!

    if section_lower in ['docs', 'documentation', 'guides']:
        return 'doc'

    return 'section'
```

**Pros**:
- Uses Bengal's architecture correctly
- Works immediately with existing code
- No template or renderer changes needed

**Cons**:
- `type: archive` is less intuitive than `type: blog`
- User confusion ("why archive not blog?")
- Doesn't match documentation examples

### Option 4: Introduce "blog-section" Type

**Modify**: Multiple files

Add new type specifically for blog section indexes:
- Update renderer to handle `blog-section` type
- Update init to generate `blog-section` type
- Keep `blog` for individual posts

**Pros**:
- Clearest separation of concerns
- Most architecturally sound
- Future-proof

**Cons**:
- More complex
- More types to document
- Migration path for existing sites

## Recommended Approach: Hybrid Solution

**Phase 1 - Quick Fix (Option 2 + Option 1):**

1. **Make template defensive** (immediate)
   - No build errors even without pagination context
   - Safe fallback behavior

2. **Add "blog" to pagination types** (proper fix)
   - Makes `type: blog` work for sections
   - Aligns with user expectations

**Phase 2 - Architectural Improvement (Future):**

3. **Documentation clarification**
   - Explain when to use `blog` vs `archive` vs `blog-section`
   - Provide examples for each

4. **Better type inference**
   - Detect if page is section index vs regular page
   - Auto-apply correct pagination logic

## Implementation Plan

### Immediate (Now)

**File 1**: `bengal/themes/default/templates/blog/list.html`
```jinja2
{# At top of template, after extends #}
{% set total_pages = total_pages | default(1) %}
{% set current_page = current_page | default(1) %}
{% set total_posts = total_posts | default(posts | length if posts else 0) %}
{% set base_url = base_url | default(section.url if section else '/blog/') %}
```

**File 2**: `bengal/rendering/renderer.py` line 200
```python
if page_type in ("archive", "blog", "api-reference", "cli-reference", "tutorial"):
```

### Testing

```bash
# Test 1: Blog section with type: blog
bengal new site test1
cd test1
bengal init --sections "blog" --with-content
bengal build  # Should work!

# Test 2: Blog section with type: archive
# (current working method)
bengal new site test2
cd test2
# Create blog/_index.md with type: archive
bengal build  # Should work!

# Test 3: Auto-generated blog archive
# (already works)
```

## Root Cause Summary

**Architectural Mismatch**:
- Template designed for paginated list pages
- Context only provided for specific generated types
- User-created blog sections fall through the cracks

**Why It Happened**:
- Blog template created for auto-generated archives
- Later added as explicit template option
- Never added to pagination context provider
- Documentation showed `type: blog` but system expected `type: archive`

## Lessons Learned

1. **Template-Context Contract**: Templates and context providers must be in sync
2. **Type System Clarity**: Need clear distinction between content types and layout types
3. **Defensive Templates**: Critical templates should handle missing context gracefully
4. **Init Validation**: Template choices in `bengal init` should be validated against renderer

## Success Criteria

After fix:
- ✅ `bengal init` with blog sections builds without errors
- ✅ Pagination works when posts > per_page limit
- ✅ Template degrades gracefully without pagination
- ✅ Both `type: blog` and `type: archive` work
- ✅ Documentation clarifies when to use each type

## Alternative: Quick Patch vs Proper Fix

### Quick Patch (5 minutes)
- Change `bengal init` to use `type: archive` instead of `type: blog`
- Works immediately with zero other changes
- Document as "known quirk"

### Proper Fix (30 minutes)
- Template defaults + renderer update
- Fixes root cause
- Better long-term

**Recommendation**: Do the proper fix. It's only 30 minutes and prevents future confusion.
