# MyST Target Labels `()=` Feature Analysis

**Date**: 2025-10-10  
**Status**: 📋 Design/Planning

## What is MyST `()=` Syntax?

MyST Markdown allows creating custom reference targets (labels) using the `(target-name)=` syntax:

```markdown
(my-custom-label)=
## Some Heading

You can place a label before any content:

(another-label)=
This paragraph now has a label.

Reference it anywhere:
[Link text](my-custom-label)
[Another link](another-label)
```

**Key Features:**
- Labels can be placed before **any** content (headings, paragraphs, directives, etc.)
- Labels are **globally scoped** across the entire site
- Referenced using standard markdown link syntax: `[text](label)`
- Similar to Sphinx's `.. _label:` in reStructuredText

## Current Bengal Cross-Reference System

We already have a robust cross-reference system:

```markdown
[[docs/installation]]              # Link by path
[[docs/installation|Custom Text]]   # Link by path with custom text
[[#heading-slug]]                   # Link to heading by slug
[[id:custom-id]]                    # Link by custom frontmatter ID
```

**How it works:**
1. `ContentOrchestrator` builds `xref_index` during discovery
2. `CrossReferencePlugin` resolves `[[...]]` patterns during rendering
3. O(1) lookups using pre-built dictionaries
4. Automatic heading slug generation
5. Broken ref detection for debugging

## Comparison: MyST vs Bengal

| Feature | MyST `()=` | Bengal `[[...]]` |
|---------|-----------|------------------|
| **Syntax** | `[text](label)` | `[[path\|text]]` |
| **Label Definition** | `(label)=` before content | Frontmatter `id:` or auto slug |
| **Scope** | Global | Global |
| **Heading Refs** | Need explicit label | Auto from heading text |
| **Path Refs** | Need explicit label | Auto from file path |
| **Standard Markdown** | ✅ Uses `[]()`  | ❌ Custom `[[]]` |
| **Auto-completion** | ❌ Need to remember labels | ✅ Paths auto-complete |
| **Refactoring** | ❌ Labels break if renamed | ✅ Paths update with files |

## Implementation Complexity

### Option 1: Full MyST `()=` Support

**Difficulty**: 🔴 **Medium-High** (3-4 days)

**What we'd need to build:**

1. **Label Extraction (Parser Pre-processing)**
   ```python
   # Before markdown parsing, extract labels
   def extract_labels(content: str) -> tuple[str, dict[str, int]]:
       """
       Extract (label)= patterns and their positions.
       Returns: (content_without_labels, {label: line_number})
       """
       pattern = re.compile(r'^\(([a-z0-9-_]+)\)=\s*$', re.MULTILINE)
       labels = {}
       # ... extract and store positions
       return cleaned_content, labels
   ```

2. **Label Registry (Discovery Phase)**
   ```python
   # Store labels in xref_index during content discovery
   xref_index['custom_labels'] = {
       'my-label': {
           'page': page_object,
           'anchor': None,  # Or anchor ID if label is before heading
       }
   }
   ```

3. **Link Resolution (Rendering Phase)**
   ```python
   # Hook into Mistune's link rendering
   def resolve_link(href, text):
       # Check if href is a custom label
       if href in custom_labels:
           return custom_label_link
       # Fall back to standard link
       return standard_link
   ```

4. **Label Validation**
   - Check for duplicate labels across site
   - Warn about broken label references
   - Health check integration

**Challenges:**
- Need to modify Mistune's link parser (complex API)
- Label extraction must happen before markdown parsing
- Need to track label positions for anchor generation
- Conflicts with standard markdown links (need disambiguation)
- How to handle external links vs label refs?

### Option 2: Hybrid Approach (Extend Current System)

**Difficulty**: 🟡 **Low-Medium** (1-2 days)

**Idea**: Support `()=` for **defining** labels, but keep `[[label]]` for **referencing**:

```markdown
(my-custom-label)=
## Heading

Reference with our existing syntax:
[[my-custom-label]]
```

**Benefits:**
- Reuse existing `[[...]]` resolution (already works great)
- Only need to add label extraction (simpler)
- No conflicts with standard markdown links
- Clear distinction: `()=` defines, `[[]]` references

**Implementation:**
```python
# 1. Extract labels during parsing
labels = extract_labels(content)  # Returns: {'my-label': line_num}

# 2. Store in page metadata
page.metadata['custom_labels'] = labels

# 3. Register in xref_index
xref_index['by_label'][label] = page

# 4. Existing [[...]] resolution picks it up automatically
```

### Option 3: Frontmatter Only (Current System)

**Difficulty**: 🟢 **Trivial** (Already implemented)

**Already works today:**
```markdown
---
id: my-custom-id
---

# Page

Reference anywhere:
[[id:my-custom-id]]
```

**Pros:**
- ✅ Already implemented and tested
- ✅ Clear, explicit labeling
- ✅ No parsing complexity
- ✅ Works great for most use cases

**Cons:**
- Only one label per page
- Label must be in frontmatter (not inline)

## Real-World Usage Analysis

### When do you actually need `()=` labels?

1. **Multiple targets per page** - Rare in practice
2. **Explicit label control** - Usually automatic slugs work fine
3. **Sphinx migration** - Only if heavily using `.. _label:`

### What we already handle well:

✅ **Heading references** - Auto-generated from heading text  
✅ **Page references** - By path or frontmatter ID  
✅ **Section references** - By heading slug  
✅ **Custom IDs** - Via frontmatter  

### What `()=` adds:

- Inline label definition (vs frontmatter)
- Multiple labels per page
- Label before any element (not just headings/pages)

**Assessment**: Nice-to-have for Sphinx parity, but most use cases covered by existing system.

## Recommendation

### Short Term: **Option 3** (Current System)

✅ **Already works**  
✅ **Covers 95% of use cases**  
✅ **Simple and explicit**  
✅ **No new complexity**

**For users wanting Sphinx-style labels:**
```markdown
---
id: my-label
---
# Page Content

Reference with: [[id:my-label]]
```

### Medium Term: **Option 2** (Hybrid)

If demand arises, implement:
- `(label)=` for **defining** multiple labels per page
- `[[label]]` for **referencing** (existing system)
- Best of both worlds: MyST compatibility + Bengal simplicity

### Long Term: **Option 1** (Full MyST)

Only if:
- Strong user demand for full MyST compatibility
- Willing to handle edge cases (link disambiguation)
- Users prefer `[text](label)` over `[[label]]`

## Implementation Priority

🔵 **Low Priority** - Current system handles the need

**Why:**
1. Existing `[[...]]` syntax is powerful and works well
2. Most docs don't need multiple labels per page
3. Frontmatter IDs solve the explicit labeling need
4. Auto-generated heading slugs work great
5. Medium complexity for marginal benefit

**When to revisit:**
- Multiple users request it
- Sphinx migration becomes a major use case
- MyST compatibility becomes a marketing requirement

## Technical Debt Assessment

**If we DON'T implement:**
- ❌ Not 100% MyST compatible
- ❌ Sphinx users need to adapt their refs
- ✅ Simpler codebase
- ✅ Clear, explicit syntax
- ✅ Less ambiguity

**If we DO implement (Option 2 - Hybrid):**
- ✅ Better Sphinx migration path
- ✅ More flexible labeling
- ⚠️ Slightly more complex
- ⚠️ Need to document two ways to label

**If we DO implement (Option 1 - Full):**
- ✅ 100% MyST compatible
- ❌ Significant complexity
- ❌ Link disambiguation issues
- ❌ Conflicts with standard markdown

## Conclusion

**Recommendation**: Stick with current system (`[[...]]` + frontmatter `id:`)

**Rationale:**
- ✅ Simple, explicit, works well
- ✅ No ambiguity with standard markdown links
- ✅ Auto-completion friendly (file paths)
- ✅ Refactoring friendly (paths update)
- ✅ Covers 95% of use cases

**If needed later**: Implement Option 2 (Hybrid) for best of both worlds.

## User Documentation

### Current System (Document This Better):

```markdown
# Three Ways to Reference Content

## 1. By Path (Auto-discovered)
[[docs/installation]]           # Link to page by path
[[docs/installation|Install]]   # With custom text

## 2. By Heading (Auto-generated)
[[#heading-slug]]               # Link to heading by slug

## 3. By Custom ID (Explicit)
---
id: my-custom-label
---

Reference with: [[id:my-custom-label]]

## Pro Tips
- Paths auto-complete in editors
- Paths update when files move
- Heading slugs auto-generated from titles
- Custom IDs for stable references
```

This is already powerful enough for most documentation needs!

