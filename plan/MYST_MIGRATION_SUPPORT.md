# MyST Markdown Migration Support Plan

**Date**: 2025-10-10  
**Context**: Analysis of real Sphinx/MyST documentation (NeMo Microservices docs)  
**Goal**: Ease migration from Sphinx to Bengal SSG

## Current Usage Analysis

Based on the NeMo Microservices documentation in `experiments/docs/`, here are the MyST features being used:

### High-Priority Directives (Used Frequently)

#### Already Supported ✅
- `:::{note}` (83 uses) - **SUPPORTED** via `admonitions.py`
- `:::{tip}` (43 uses) - **SUPPORTED** via `admonitions.py`
- `:::{important}` (20 uses) - **SUPPORTED** via `admonitions.py`
- `:::{warning}` (18 uses) - **SUPPORTED** via `admonitions.py`
- `:::{dropdown}` (149 uses) - **SUPPORTED** via `dropdown.py`
- ````{rubric}` (30 uses) - **SUPPORTED** via `rubric.py`

#### Needs Implementation 🔨

**Sphinx-Design Directives** (Critical for Migration)
- `:::{grid}` (126 uses) - Responsive grid layouts
- `:::{grid-item-card}` (420 uses) - Cards in grids with icons/links
- `:::{tab-set}` (359 uses) - Tab containers
- `:::{tab-item}` (778 uses) - Individual tabs
- `{octicon}` role - GitHub octicon integration in cards

**Content Inclusion**
- ````{literalinclude}` (378 uses) - Include external code files
- ````{include}` (37 uses) - Include other markdown files
- ````{toctree}` (75 uses) - Table of contents tree

**Tables & Lists**
- ````{list-table}` (58 uses) - Structured tables with headers

**Code & Diagrams**
- ````{code-block}` (47 uses) - Code with language highlighting
- ````{mermaid}` (5 uses) - Diagram rendering

**Links & Navigation**
- ````{button-ref}` (7 uses) - Button-style links
- `{doc}` role - Document cross-references
- `{ref}` role - Reference cross-references

### Lower Priority (Used Less Frequently)

- ````{image}` (2 uses) - Enhanced images
- ````{raw}` (3 uses) - Raw HTML/LaTeX
- ````{eval-rst}` (3 uses) - Embedded reStructuredText
- ````{div}` (3 uses) - Generic containers
- `{bdg-*}` roles - Badges
- `{kbd}` role - Keyboard shortcuts

## Implementation Priority

### Phase 1: Critical Migration Blockers (Week 1-2)

These are essential for any Sphinx migration:

1. **Grid System** (`grid`, `grid-item-card`)
   - Responsive 1-4 column layouts
   - Cards with titles, links, icons, footers
   - Support for `{octicon}` icons in titles
   - Options: gutter, columns, class

2. **Tabs** (`tab-set`, `tab-item`)
   - Nested tab containers
   - Sync tabs across page
   - Code tabs for language examples

3. **Code Block** (`code-block`)
   - Language-specific highlighting
   - Line numbers, emphasis lines
   - Caption and name support

### Phase 2: Content Organization (Week 3)

4. **Literalinclude** (include external files)
   - Path resolution
   - Language detection
   - Line ranges
   - Dedent support

5. **Include** (include markdown files)
   - Relative path resolution
   - Fragment inclusion
   - Preprocessing

6. **List-Table** (structured tables)
   - Header rows
   - Column widths
   - Row/column spans

### Phase 3: Enhanced Features (Week 4)

7. **Mermaid** (diagrams)
   - Inline diagram rendering
   - Multiple diagram types
   - Dark mode support

8. **Button-Ref** (button links)
   - Styled buttons
   - Color schemes
   - Icon support

9. **TOC Tree** (navigation)
   - Multi-level ToC
   - Glob patterns
   - Hidden entries
   - Max depth

### Phase 4: Polish (Week 5+)

10. **Roles** (inline markup)
    - `{doc}` - document links
    - `{ref}` - reference links
    - `{kbd}` - keyboard keys
    - `{bdg-*}` - badges

11. **Special Content**
    - `{image}` - enhanced images
    - `{raw}` - raw HTML
    - `{eval-rst}` - RST blocks

## Bengal Architecture Integration

### Where to Add Features

```
bengal/rendering/plugins/directives/
├── grid.py          # NEW: Grid layouts
├── tabs.py          # EXISTS: Needs tab-set/tab-item
├── code_block.py    # NEW: Enhanced code blocks
├── literalinclude.py # NEW: External file inclusion
├── include.py       # NEW: Markdown file inclusion
├── list_table.py    # NEW: Structured tables
├── mermaid.py       # NEW: Diagram rendering
├── buttons.py       # NEW: Button links
└── roles.py         # NEW: Inline roles
```

### Theme Support

Add to `bengal/themes/default/components/`:
```
grid.css         # Grid layouts
cards.css        # Card styling
tabs.css         # Tab styling (enhance existing)
buttons.css      # Button styling
badges.css       # Badge styling
```

## Migration Path for Users

### Step 1: Frontmatter

Replace Sphinx config:
```yaml
# Old (Sphinx conf.py)
html_theme = "sphinx_book_theme"

# New (Bengal)
---
type: doc
cascade:
    type: doc
---
```

### Step 2: Grid Migration

```markdown
# Old (Sphinx/MyST)
::::{grid} 1 2 2 2
:gutter: 1

:::{grid-item-card} {octicon}`book` Title
:link: docs/page
:link-type: doc
Content here
:::
::::

# New (Bengal - Phase 1)
Same syntax! Bengal will support it.
```

### Step 3: Tabs Migration

```markdown
# Old (Sphinx/MyST)
::::{tab-set}
:::{tab-item} Python
python code
:::
:::{tab-item} JavaScript
js code
:::
::::

# New (Bengal - Phase 1)
Same syntax! Bengal will support it.
```

### Step 4: Code Blocks

```markdown
# Old (Sphinx/MyST)
```{code-block} python
:linenos:
:emphasize-lines: 2,3
code here
```

# New (Bengal)
Same syntax! Bengal will support it.
```

## Compatibility Matrix

| Feature | MyST Syntax | Bengal Support | Priority |
|---------|-------------|----------------|----------|
| Admonitions | `:::{note}` | ✅ Full | - |
| Dropdowns | `:::{dropdown}` | ✅ Full | - |
| Rubrics | ````{rubric}` | ✅ Full | - |
| Grids | `:::{grid}` | ❌ Not yet | 🔴 High |
| Grid Cards | `:::{grid-item-card}` | ❌ Not yet | 🔴 High |
| Tab Sets | `:::{tab-set}` | ⚠️ Partial | 🔴 High |
| Tab Items | `:::{tab-item}` | ⚠️ Partial | 🔴 High |
| Code Blocks | ````{code-block}` | ⚠️ Basic | 🟡 Medium |
| Literalinclude | ````{literalinclude}` | ❌ Not yet | 🟡 Medium |
| Include | ````{include}` | ❌ Not yet | 🟡 Medium |
| List Tables | ````{list-table}` | ❌ Not yet | 🟡 Medium |
| Mermaid | ````{mermaid}` | ❌ Not yet | 🟢 Low |
| Button Refs | ````{button-ref}` | ❌ Not yet | 🟢 Low |
| Doc Role | `{doc}` | ⚠️ Via [[]] | 🟡 Medium |
| Octicons | `{octicon}` | ❌ Not yet | 🔴 High |

## Testing Strategy

For each new directive, add:
1. Unit tests in `tests/unit/rendering/plugins/directives/`
2. Integration test in `examples/showcase/content/`
3. Visual regression test (screenshot comparison)

## Success Metrics

Migration is successful when:
- ✅ All 420+ grid-item-cards render correctly
- ✅ All 778+ tab-items are clickable and functional
- ✅ All 378+ literalinclude blocks load external files
- ✅ All admonitions render with correct styling
- ✅ Cross-references resolve correctly
- ✅ Visual parity with Sphinx output (95%+)

## Next Steps

1. **Prototype Grid System** (1-2 days)
   - Basic grid layout
   - Grid-item-card with icons
   - Responsive columns

2. **Test with Real Docs** (1 day)
   - Build experiments/docs with Bengal
   - Identify rendering issues
   - Fix critical bugs

3. **Iterate on Missing Features** (ongoing)
   - Add features based on actual usage
   - Prioritize by frequency in real docs
   - Maintain backwards compatibility

## Resources

- MyST Parser Docs: https://myst-parser.readthedocs.io/
- Sphinx Design: https://sphinx-design.readthedocs.io/
- Octicons: https://primer.style/foundations/icons
- Mistune Directives: https://mistune.lepture.com/en/latest/directives.html

