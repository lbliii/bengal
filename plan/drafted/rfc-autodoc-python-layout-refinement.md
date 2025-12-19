# RFC: Autodoc Python Layout Refinement

**Status**: Accepted  
**Created**: 2025-12-07  
**Author**: AI Pair Programmer  
**Priority**: P2 (Medium)  
**Context**: Refining autodoc Python layouts to match the quality and intentionality of the docs layouts, search modal, and other recent UI work.

---

## Executive Summary

This RFC catalogs all content elements and layout combinations for autodoc Python pages, identifies current issues, and proposes intentional design treatments for each combination. The goal is to create consistent, scannable, and aesthetically refined API documentation.

---

## 1. Current State Analysis

### 1.1 Template Architecture

The Python autodoc system uses a layered template structure:

```
base/base.md.jinja2           → Core document structure
  └── base/python_base.md.jinja2  → Python-specific features
        ├── python/module.md.jinja2   → Module pages
        ├── python/class.md.jinja2    → Class pages
        └── python/function.md.jinja2 → Function pages
```

**Partials** (reusable components):
- `class_attributes.md.jinja2` - Attribute tables
- `class_methods.md.jinja2` - Method listings with full details
- `class_properties.md.jinja2` - Property listings
- `method_examples.md.jinja2` - Code examples
- `method_notes.md.jinja2` - Notes and warnings
- `method_raises.md.jinja2` - Exception documentation
- `module_description.md.jinja2` - Module docstring
- `module_aliases.md.jinja2` - Type/import aliases
- `module_classes.md.jinja2` - Class listings
- `module_functions.md.jinja2` - Function listings

**Macros** (shared utilities):
- `parameter_table.md.jinja2` - Unified parameter tables
- `code_blocks.md.jinja2` - Signature and code block formatting
- `safe_macros.md.jinja2` - Error boundary wrappers

### 1.2 HTML Layout

Uses `autodoc/python/single.html` with three-column layout:
- **Left sidebar**: Navigation tree
- **Center**: Content (page hero + article)
- **Right sidebar**: Contextual graph + TOC + metadata

### 1.3 CSS Styling

`api-docs.css` provides specialized styling for:
- Signature blocks with left accent border
- Parameter tables (responsive)
- Badges (async, property, deprecated, dataclass, class)
- Rubric headers for sections
- Collapsible sections (dropdowns)
- Code examples with "Example" label

---

## 2. Content Elements Inventory

### 2.1 Module Page Elements

| Element | Source | Current Rendering | Notes |
|---------|--------|-------------------|-------|
| **Title** | Module name | `# module_name` H1 | Display name, not qualified |
| **Type indicator** | Template | `**Type:** Module` | Plain text, not badge |
| **Source link** | `source_file` | `**Source:** [View source](...)` | Links to source file with line |
| **Navigation breadcrumbs** | Computed | `[parent] › [child] › module` | Inline markdown links |
| **Description** | Module docstring | Full docstring content | May contain complex formatting |
| **Aliases section** | Extractor | List of type/import aliases | Optional |
| **Classes section** | Extractor children | H3 class names with details | Nested content |
| **Functions section** | Extractor children | H3 function names with details | Nested content |

### 2.2 Class Page Elements

| Element | Source | Current Rendering | Notes |
|---------|--------|-------------------|-------|
| **Title** | Class name | `# ClassName` H1 | Simple name |
| **Badges** | Metadata | MyST `:::{badge}` directives | Class, Dataclass, Deprecated |
| **Inheritance** | `metadata.bases` | `**Inherits from:** BaseClass` | Links to base classes |
| **Description** | Class docstring | Full docstring content | Parsed for structured sections |
| **Dataclass info** | `is_dataclass` | `:::{info} This is a dataclass.` | Info admonition |
| **Deprecation warning** | `deprecated` | `:::{warning} Deprecated...` | Warning admonition |
| **Attributes table** | Children (attribute) | Markdown table | Name, Type, Description |
| **Properties section** | Children (is_property) | H4 property names | Signature + description |
| **Methods section** | Children (method) | H4 method names | Full method details |
| **Inherited members** | Synthetic children | Dropdown with grouped list | Collapsible by default |

### 2.3 Function/Method Elements

| Element | Source | Current Rendering | Notes |
|---------|--------|-------------------|-------|
| **Title** | Name + decorators | `` #### `method_name` @async @classmethod `` | Inline decorator indicators |
| **Badges** | Metadata | MyST `:::{badge}` directives | Function, Async, Deprecated |
| **Signature block** | `metadata.signature` | Fenced Python code block | Syntax highlighted |
| **Description** | Docstring description | Paragraph text | May be multi-paragraph |
| **Async info** | `is_async` | `:::{info} Async...` | Info admonition |
| **Deprecation warning** | `deprecated` | `:::{warning} Deprecated...` | Warning admonition |
| **Parameters table** | `metadata.args` | Markdown table | Name, Type, Default, Description |
| **Returns section** | `metadata.returns` | `` `ReturnType` - description `` | Type + description |
| **Raises section** | `parsed_doc.raises` | List of exceptions | Type + description |
| **Examples section** | `parsed_doc.examples` | Fenced code blocks | With rubric header |
| **Notes section** | `parsed_doc.notes` | `:::{note}` admonitions | One per note |
| **Warnings section** | `parsed_doc.warnings` | `:::{warning}` admonitions | One per warning |
| **See Also** | `parsed_doc.see_also` | Inline references | Links to related items |

### 2.4 Shared Elements (Macros/Partials)

| Element | Macro/Partial | Options | Notes |
|---------|---------------|---------|-------|
| **Parameter table** | `parameter_table` | `show_types`, `show_defaults`, `show_required`, `table_style` | Dropdown for >10 params |
| **Signature block** | `signature_block` | `language`, `element_type` | Falls back to warning if empty |
| **Code block** | `code_block` | `language`, `title`, `show_line_numbers` | With optional title |
| **Rubric** | `rubric_shell` | CSS class | Pseudo-heading (not in TOC) |
| **Safe section** | `safe_section` | Section name | Error boundary wrapper |

---

## 3. Layout Combinations Matrix

### 3.1 Module Combinations

| Combination | Description | Frequency | Priority |
|-------------|-------------|-----------|----------|
| **M1** | Description only (no children) | Rare | Low |
| **M2** | Description + classes only | Common | High |
| **M3** | Description + functions only | Uncommon | Medium |
| **M4** | Description + classes + functions | Very common | High |
| **M5** | Package index (from `__init__.py`) | Common | High |
| **M6** | Module with aliases | Uncommon | Medium |
| **M7** | Minimal module (no docstring, few children) | Uncommon | Medium |

### 3.2 Class Combinations

| Combination | Description | Frequency | Priority |
|-------------|-------------|-----------|----------|
| **C1** | Simple class (description + methods) | Very common | High |
| **C2** | Dataclass (with attributes table) | Common | High |
| **C3** | Class with inheritance | Common | High |
| **C4** | Class with properties only | Uncommon | Medium |
| **C5** | Class with inherited members | Common | High |
| **C6** | Abstract base class | Uncommon | Medium |
| **C7** | Deprecated class | Rare | Low |
| **C8** | Empty class (enum-like or marker) | Rare | Low |
| **C9** | Class with many methods (10+) | Common | High |
| **C10** | Class with many attributes (10+) | Uncommon | Medium |

### 3.3 Function/Method Combinations

| Combination | Description | Frequency | Priority |
|-------------|-------------|-----------|----------|
| **F1** | Minimal (signature + description) | Common | High |
| **F2** | With parameters (1-5 params) | Very common | High |
| **F3** | With many parameters (5+) | Common | High |
| **F4** | With returns documentation | Very common | High |
| **F5** | With raises documentation | Common | High |
| **F6** | With examples | Common | High |
| **F7** | With notes/warnings | Uncommon | Medium |
| **F8** | Async function | Common | High |
| **F9** | Classmethod | Common | High |
| **F10** | Staticmethod | Common | High |
| **F11** | Property | Very common | High |
| **F12** | Deprecated function | Rare | Low |
| **F13** | Full documentation (all sections) | Uncommon | Medium |
| **F14** | No docstring (signature only) | Common | High |

---

## 4. Current Issues

### 4.1 Structural Issues

| Issue | Location | Impact | Example |
|-------|----------|--------|---------|
| **I1** | Module header | Medium | Type/Source not visually integrated with title |
| **I2** | Navigation breadcrumbs | Low | Inline markdown styling inconsistent with page hero |
| **I3** | Properties duplicated in Methods | High | Properties appear twice (Properties section + Methods section) |
| **I4** | Long attribute descriptions | High | Break table formatting in `page_core.md` example |
| **I5** | Section spacing | Medium | Inconsistent vertical rhythm between sections |

### 4.2 Aesthetic Issues

| Issue | Location | Impact | Example |
|-------|----------|--------|---------|
| **A1** | Badge placement | Medium | Badges render as separate block elements |
| **A2** | Signature blocks | Low | Good styling but inconsistent margin/padding |
| **A3** | Rubric headers | Medium | Could be more visually distinct |
| **A4** | Empty states | Low | `*No description provided.*` styling bland |
| **A5** | Decorator indicators | Medium | `@async @classmethod` inline text vs badges |
| **A6** | Table styling | Medium | Tables could use zebra striping consistently |

### 4.3 Content Issues

| Issue | Location | Impact | Example |
|-------|----------|--------|---------|
| **T1** | Missing type annotations | High | `-` placeholder not informative |
| **T2** | Truncated descriptions | Medium | Long module descriptions in frontmatter |
| **T3** | Source link format | Low | Points to source file, not viewable online |
| **T4** | Inherited member descriptions | Low | Just "Inherited from X" not actual description |

---

## 5. Design Proposals

### 5.1 Module Page Refinements

#### 5.1.1 Unified Page Header

**Current**:
```markdown
# module_name
**Type:** Module
**Source:** [View source](...)

**Navigation:**
[parent] › module_name
```

**Proposed**: Move metadata into page hero pattern like docs layouts:
```markdown
# module_name

:::{page-meta}
:type: Module
:source: bengal/core/site.py
:lines: 1-450
:::
```

Benefits:
- Consistent with docs hero pattern
- Source file + line count provides context
- Type as badge instead of plain text

#### 5.1.2 Section Organization

Enforce consistent section order:
1. Description (with any docstring examples inline)
2. Module Aliases (if any)
3. Classes (if any)
4. Functions (if any)

Add visual separators between major sections (currently just headings).

### 5.2 Class Page Refinements

#### 5.2.1 Badge Consolidation

Move all badges to a single line after title:

```markdown
# ClassName

:::{badges}
Class • Dataclass • Deprecated
:::
```

Or render inline with CSS `.api-badge-group`.

#### 5.2.2 Attributes Table Enhancement

**Decision**: Switch to definition list (Option B) to handle long descriptions gracefully. We will use a distinct styling for these lists (`.api-attributes`) to ensure they scan well and don't look like generic text.

For attributes with descriptions > 100 chars, use definition list format:

```markdown
**Attributes:**

`source_path`
: Path to source markdown file (relative to content dir). Used as cache key
  and for file change detection.

`title`
: Page title from frontmatter or filename. Required field, defaults to
  "Untitled" if not provided.
```

#### 5.2.3 Properties vs Methods

**Fix**: Properties should NOT appear in Methods section.

Update `class_methods.md.jinja2` to explicitly filter:
```jinja2
{% set own_methods = all_methods
   | rejectattr('metadata.synthetic')
   | rejectattr('metadata.is_property')  {# ADD THIS #}
   | list %}
```

#### 5.2.4 Inherited Members

Keep current dropdown pattern but improve:
- Show method signature snippet (not just name)
- Group by source class with better visual hierarchy
- Option to show full docs on expand

### 5.3 Function/Method Refinements

#### 5.3.1 Signature Block Styling

Current signature blocks are good. Minor refinements:
- Add copy button (like code blocks)
- Ensure consistent left border color (use `--color-primary`)
- Add subtle syntax highlighting for type annotations

#### 5.3.2 Decorator Badges

Convert inline decorator text to visual badges:

**Current**: `#### \`method_name\` @async @classmethod`

**Proposed**:
```markdown
#### `method_name`

:::{badges}
async • classmethod
:::
```

CSS renders as inline badges with appropriate colors.

#### 5.3.3 Parameter Table Thresholds

Current threshold for dropdown: not implemented (always table).

**Proposed thresholds**:
- 0-5 parameters: Always visible table
- 6-10 parameters: Collapsible, open by default
- 11+ parameters: Collapsible, closed by default

#### 5.3.4 Returns Section

**Current**:
```markdown
**Returns**

`ReturnType` - Description of what is returned.
```

**Proposed**: Use consistent rubric styling:
```markdown
:::{rubric} Returns
:class: rubric-returns
:::

`ReturnType`
: Description of what is returned.
```

#### 5.3.5 Examples Section

Examples are well-styled. Minor refinements:
- Add "Run in REPL" badge/link for interactive examples
- Ensure consistent spacing after example blocks
- Consider syntax highlighting for doctest output

### 5.4 CSS Refinements

#### 5.4.1 Badge Group Component

```css
.api-badge-group {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-2);
  margin: var(--space-3) 0;
}

.api-badge-group .api-badge {
  margin-left: 0; /* Remove individual margin */
}
```

#### 5.4.2 Definition List Styling

For long attribute descriptions:
```css
.prose.api-content dl.api-attributes {
  background: var(--color-bg-elevated);
  border-radius: var(--radius-lg);
  padding: var(--space-4);
  margin: var(--space-4) 0;
}

.prose.api-content dl.api-attributes dt {
  font-family: var(--font-mono);
  font-weight: var(--weight-semibold);
  color: var(--color-primary);
  margin-top: var(--space-4);
}

.prose.api-content dl.api-attributes dt:first-child {
  margin-top: 0;
}

.prose.api-content dl.api-attributes dd {
  margin-left: var(--space-6);
  color: var(--color-text-secondary);
  margin-top: var(--space-1);
}
```

#### 5.4.3 Section Spacing Standardization

```css
/* API content section spacing */
.prose.api-content h2 {
  margin-top: var(--space-12);
  margin-bottom: var(--space-4);
  padding-bottom: var(--space-3);
  border-bottom: 2px solid var(--color-border-light);
}

.prose.api-content h3 {
  margin-top: var(--space-8);
  margin-bottom: var(--space-3);
}

.prose.api-content h4 {
  margin-top: var(--space-6);
  margin-bottom: var(--space-2);
}
```

---

## 6. Implementation Plan

### Phase 1: Bug Fixes (High Priority)
1. [ ] Fix properties appearing in Methods section
2. [ ] Fix long descriptions breaking attribute tables
3. [ ] Ensure consistent section spacing

### Phase 2: Template Improvements (High Priority)
1. [ ] Implement parameter table thresholds (dropdown at 6+)
2. [ ] Convert decorator indicators to badges
3. [ ] Standardize rubric usage for all sections
4. [ ] Add copy button to signature blocks

### Phase 3: CSS Refinements (Medium Priority)
1. [ ] Implement badge group component
2. [ ] Add definition list styling for attributes
3. [ ] Standardize section spacing
4. [ ] Improve empty state styling

### Phase 4: Enhanced Features (Lower Priority)
1. [ ] Improve inherited members display
2. [ ] Add source link to GitHub/GitLab
3. [ ] Consider interactive example integration

---

## 7. Testing Strategy

### 7.1 Visual Test Cases

Create test fixtures for each combination:

```
tests/roots/test-autodoc-layouts/
├── bengal.toml
├── content/
│   └── api/
│       └── generated/  # Auto-generated by test
└── src/
    ├── minimal_module.py      # M1: Description only
    ├── classes_only.py        # M2: Classes only
    ├── functions_only.py      # M3: Functions only
    ├── full_module.py         # M4: Classes + functions
    ├── dataclass_example.py   # C2: Dataclass
    ├── inherited_class.py     # C3, C5: Inheritance
    ├── many_methods.py        # C9: 10+ methods
    ├── minimal_function.py    # F1: Signature only
    ├── many_params.py         # F3: 10+ parameters
    ├── async_example.py       # F8: Async functions
    └── full_docs.py           # F13: All doc sections
```

### 7.2 Regression Tests

Add snapshot tests for key combinations to catch rendering regressions.

---

## 8. Success Criteria

- [ ] All 7 module combinations render correctly
- [ ] All 10 class combinations render correctly
- [ ] All 14 function/method combinations render correctly
- [ ] No visual regressions in existing API docs
- [ ] Consistent spacing and typography across all page types
- [ ] Properties no longer duplicated in Methods section
- [ ] Long attribute descriptions don't break table layout
- [ ] Badge groups render inline properly
- [ ] Parameter tables collapse appropriately

---

## 9. Deferred Decisions (Future Work)

1. **Inherited member expansion?**  
   Current behavior: Dropdown with summary.
   Future consideration: Should expanding an inherited member show full docs or just signature?

2. **Source link destination?**  
   Current behavior: Relative local path (useful for dev).
   Future consideration: Configurable support for GitHub/GitLab remote links.

3. **Interactive examples?**  
   Future consideration: "Try in REPL" integration (like Marimo) for example blocks.

---

## 10. Resolved Questions

1. **Definition list vs table for attributes?**  
   **Decision**: Use Definition Lists (`<dl>`) with specialized styling. Tables are too rigid for long docstrings and break mobile layouts.

---

## 11. References

**Evidence Sources**:
- `bengal/autodoc/templates/python/` - Template files
- `bengal/autodoc/extractors/python.py` - Data extraction
- `bengal/themes/default/assets/css/components/api-docs.css` - Current styling
- `content/api/bengal/core/site.md` - Real-world module output
- `content/api/bengal/core/page/page_core.md` - Dataclass example with issues

**Related RFCs**:
- None currently

**Architecture Docs**:
- `bengal/autodoc/README.md` - Autodoc system overview
