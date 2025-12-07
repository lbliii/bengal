# RFC: API Explorer Layout System

**Status**: Draft  
**Author**: AI Assistant  
**Created**: 2025-12-07  
**Priority**: High (Strategic Differentiator)

---

## Executive Summary

Replace the current prose-based autodoc output with a premium, app-like "API Explorer" layout that prioritizes:
- **Cognitive efficiency**: Progressive disclosure, compact information density
- **AI-friendliness**: Structured, predictable output patterns
- **Product polish**: Swagger/Stripe-quality visual design
- **Competitive moat**: Hard-to-replicate, intentional design system

---

## Problem Statement

Current autodoc output has several issues:

1. **Cognitive overload**: Everything expanded by default, lots of whitespace
2. **Prose-heavy**: Reads like a document, not an app
3. **Inconsistent density**: Some sections verbose, others sparse
4. **Generic look**: Resembles typical SSG output, not a product
5. **AI navigation**: Hard to parse programmatically

### Current Layout Issues

```
# ClassName                              <- H1 buried in prose

**Type:** Class                          <- Inline metadata
**Source:** View source                  

Description paragraph...                 <- Full expansion

:::info                                  <- Separate callout
This is a dataclass.
:::

**Attributes:**                          <- Bold text, not structured

`name`                                   <- Definition list
: `type` Description...

## Methods                               <- H2 heading

### method_name                          <- H3 for each method

```python                               <- Full signature block
def method_name(...) -> ...
```

**Parameters:**                          <- Full table per method
| Name | Type | Default | Description |
...

**Returns:**                             <- Paragraph format
`ReturnType` - Description

---                                      <- Visual separator

### next_method...                       <- Repeats for EVERY method
```

**Problems with this approach:**
- 50+ line methods become 100+ lines of output
- No progressive disclosure
- Impossible to scan quickly
- Wastes vertical space

---

## Proposed Solution: API Explorer

### Core Design Principles

1. **Cards, not prose** - Each class/function is a collapsible card
2. **Collapsed by default** - Expand to reveal details
3. **Inline metadata** - Badges in headers, not separate lines
4. **Compact tables** - Parameters in tight, scannable format
5. **Zero filler** - No "No description provided"
6. **AI-structured** - Predictable HTML patterns for parsing

### Visual Hierarchy

```
Layer 1: Card Header (Always Visible)
├── Icon (◆ class, ƒ function, ⚡ async)
├── Name (monospace)
├── Badges (dataclass, async, deprecated)
└── Toggle (▾/▸)

Layer 2: Quick Summary (First Expansion)
├── One-line description
├── Attributes table (compact)
└── Methods list (names only, clickable)

Layer 3: Method Details (Click to Expand)
├── Signature (syntax highlighted)
├── Parameters table
├── Returns (inline)
└── Raises (inline, colored)

Layer 4: Examples (Collapsed)
└── Code block (click to reveal)
```

### Information Density Comparison

| Element | Current | API Explorer |
|---------|---------|--------------|
| Class header | 5-8 lines | 1 line (card header) |
| Dataclass note | 3-4 lines (admonition) | 1 badge |
| Attributes | Definition list | Compact table |
| Method header | H3 + signature block | Inline row |
| Method details | 20-40 lines | Collapsible card |
| Parameters | Full table | Compact table |
| Returns | Paragraph + type | Single inline row |
| Examples | Always visible | Collapsed |

**Estimated reduction**: 60-70% less vertical space

---

## Technical Implementation

### Phase 1: CSS Foundation ✅

Created `api-explorer.css` with:
- `.api-card` - Collapsible card component
- `.api-badge--compact` - Inline type badges
- `.api-table` - Compact parameter tables
- `.api-signature` - Syntax-highlighted signatures
- `.api-returns`, `.api-raises` - Inline result rows
- `.api-method-list` - Compact method index

### Phase 2: Template Restructure

Update autodoc templates to output structured HTML:

```jinja2
{# OLD: Prose-based #}
## {{ class.name }}

**Type:** Class

{{ class.description }}

**Attributes:**
{% for attr in class.attributes %}
`{{ attr.name }}`
: {{ attr.description }}
{% endfor %}

{# NEW: Card-based #}
<details class="api-card api-card--class" open>
<summary class="api-card__header">
  <span class="api-card__icon">◆</span>
  <code class="api-card__name">{{ class.name }}</code>
  <span class="api-badge--compact api-badge--class">class</span>
</summary>
<div class="api-card__body">
  <p class="api-card__description">{{ class.description | first_sentence }}</p>
  <table class="api-table">...</table>
</div>
</details>
```

### Phase 3: New Directives

Create directives to simplify template authoring:

```markdown
:::api-card{type="class" name="PageRankResults" badges="dataclass"}
Results from PageRank computation.

:::api-attributes
| scores | dict[Page, float] | PageRank scores |
| iterations | int | Iterations to converge |
:::

:::api-methods
- get_top_pages(limit=20) → list[tuple]
- get_score(page) → float
:::
```

Directives needed:
- `api-card` - Collapsible card wrapper
- `api-attributes` - Compact attribute table
- `api-methods` - Method index list
- `api-signature` - Syntax-highlighted signature
- `api-param-table` - Compact parameter table

### Phase 4: JavaScript Enhancement (Optional)

Add interactivity:
- Keyboard navigation (j/k to move, enter to expand)
- Deep linking to methods (`#class.method`)
- Search within page
- Copy signature button
- "Expand all" / "Collapse all"

---

## File Changes Required

### Templates to Modify

```
bengal/autodoc/templates/python/
├── module.md.jinja2          # Use card layout for module overview
├── class.md.jinja2           # Full card-based class layout
├── function.md.jinja2        # Card-based function layout
└── partials/
    ├── class_attributes.md.jinja2  # Compact table format
    ├── class_methods.md.jinja2     # Method list + expandable cards
    ├── class_properties.md.jinja2  # Compact property cards
    ├── function_body.md.jinja2     # Signature + params + returns
    └── class_explorer.md.jinja2    # NEW: Macro library ✅
```

### CSS Files

```
bengal/themes/default/assets/css/components/
├── api-explorer.css    # NEW: Card-based components ✅
└── api-docs.css        # UPDATE: Integrate with explorer styles
```

### Directives

```
bengal/rendering/plugins/directives/
├── api_card.py         # NEW: Collapsible card directive
├── api_table.py        # NEW: Compact table directive
└── api_signature.py    # NEW: Highlighted signature
```

---

## AI-Friendliness

The new layout is designed for AI consumption:

### Structured Patterns

```html
<!-- Every class follows this pattern -->
<details class="api-card" data-type="class" data-name="ClassName">
  <summary>...</summary>
  <div class="api-card__body">
    <p class="api-card__description">...</p>
    <table class="api-table" data-section="attributes">...</table>
    <ul class="api-method-list">...</ul>
  </div>
</details>

<!-- Every method follows this pattern -->
<details class="api-card" data-type="method" data-name="method_name">
  <summary>...</summary>
  <div class="api-card__body">
    <pre class="api-signature">...</pre>
    <table class="api-table" data-section="parameters">...</table>
    <div class="api-returns">...</div>
  </div>
</details>
```

### Data Attributes for Parsing

- `data-type`: class, function, method, property
- `data-name`: Element name
- `data-module`: Parent module path
- `data-async`: true/false
- `data-deprecated`: true/false

### LLM.txt Integration

The structured output enables better `llm.txt` generation:
- Extract all method signatures
- Build parameter index
- Generate usage examples

---

## Migration Strategy

### Step 1: Parallel Implementation
- Keep existing templates
- Create new `*_explorer.md.jinja2` templates
- Add config flag: `autodoc.layout: "explorer" | "classic"`

### Step 2: Testing
- Generate both layouts for comparison
- Validate all edge cases (inheritance, async, properties)
- Test with real codebases

### Step 3: Gradual Rollout
- Default to "explorer" for new projects
- Document migration path
- Deprecate "classic" in future version

---

## Success Metrics

1. **Vertical space reduction**: 60-70% less scrolling
2. **Time to find method**: < 3 seconds (vs 10+ currently)
3. **AI parsing accuracy**: 95%+ structured extraction
4. **User satisfaction**: "This looks like a product"

---

## Open Questions

1. **Expand by default?** Should first class/function be expanded?
2. **Inherited members?** Show in collapsed section or separate card?
3. **Source links?** In header badge or separate?
4. **Mobile behavior?** Stack cards or accordion?

---

## Timeline Estimate

| Phase | Effort | Status |
|-------|--------|--------|
| CSS Foundation | 2 hours | ✅ Done |
| Template Macros | 4 hours | ✅ Started |
| Module Template | 2 hours | Pending |
| Class Template | 3 hours | Pending |
| Function Template | 2 hours | Pending |
| New Directives | 4 hours | Pending |
| Testing | 3 hours | Pending |
| Documentation | 2 hours | Pending |
| **Total** | **~22 hours** | |

---

## Next Steps

1. [ ] Review RFC and provide feedback
2. [ ] Finalize visual design in CSS
3. [ ] Implement module.md.jinja2 with explorer layout
4. [ ] Implement class.md.jinja2 with card structure
5. [ ] Create api-card directive for cleaner templates
6. [ ] Test with Bengal's own API docs
7. [ ] Compare output size and usability

---

## References

- [Stripe API Docs](https://stripe.com/docs/api) - Inspiration for information density
- [Swagger UI](https://petstore.swagger.io/) - Inspiration for expand/collapse
- [FastAPI Docs](https://fastapi.tiangolo.com/) - Inspiration for readability
- [Diataxis Framework](https://diataxis.fr/) - Reference documentation principles

