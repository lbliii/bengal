# RFC: Navigation Labels (Section Dividers)

| Field | Value |
|-------|-------|
| **Status** | Draft |
| **Created** | 2024-12-30 |
| **Updated** | 2024-12-30 |
| **Author** | Bengal Team |
| **Scope** | Non-Breaking Enhancement |
| **Goal** | Enable grouped sidebar navigation with non-clickable section headings |

## Summary

Add support for **navigation labels**—non-clickable section dividers in sidebar navigation trees. Labels group related items visually without being navigable destinations themselves.

```
Getting Started          ← Label (not clickable)
  ├─ Installation
  ├─ Quick Start
  └─ Configuration

Reference                ← Label (not clickable)
  ├─ API
  └─ CLI Commands
```

## Motivation

### The Problem

Documentation sidebars often need visual groupings that aren't navigable pages. Currently, Bengal's `NavNode` always represents a clickable destination (page or section index).

**Current behavior:**
- Every nav item has a meaningful `href`
- Sections must have index pages to appear in navigation
- No way to create "headless" groupings without content

**User need:**
- Group related pages under a heading
- Heading should be styled differently (non-clickable, bold, maybe uppercase)
- Pattern is universal in docs sites (VitePress, Docusaurus, Hugo Docsy, GitBook)

### Competitive Analysis

| SSG | How Labels Work |
|-----|-----------------|
| **VitePress** | `{ text: 'Getting Started', items: [...] }` (no `link` = label) |
| **Docusaurus** | `{ type: 'category', label: '...' }` |
| **Hugo Docsy** | `headless: true` in section frontmatter |
| **GitBook** | Groups in SUMMARY.md without links |
| **MkDocs Material** | `- 'Section Name':` without path |

### Use Cases

**1. Flat groupings in docs sidebar:**
```
GETTING STARTED      ← Label
  Installation
  Quick Start

GUIDES               ← Label
  Authentication
  Deployment

REFERENCE            ← Label
  API
  CLI
```

**2. Mixed content sections:**
```
docs/
├─ _index.md         # "Documentation" - has content
├─ installation.md
├─ quick-start.md
├─ guides/           # "Guides" - just a label, no index
│   ├─ auth.md
│   └─ deploy.md
└─ reference/        # "Reference" - just a label
    ├─ api.md
    └─ cli.md
```

**3. Scoped section trees:**
```
# In /docs/ sidebar
Guides              ← Label (subsection acts as label)
  ├─ Authentication
  └─ Deployment
```

## Design

### Core Principle: Data Model + Theme Collaboration

**Core (Bengal) provides:**
- `is_label` flag on `NavNode`
- Frontmatter parsing for `nav_label: true`
- Flag setting during `NavTree.build()`

**Theme decides:**
- Whether to render labels differently
- How labels look (styling, icons, behavior)
- Whether labels are collapsible or static

This mirrors existing patterns like `icon` (core stores data, theme renders).

### Data Model Changes

```python
# bengal/core/nav_tree.py

@dataclass(slots=True)
class NavNode:
    id: str
    title: str
    _path: str
    icon: str | None = None
    weight: int = 0
    children: list[NavNode] = field(default_factory=list)
    page: Page | None = None
    section: Section | None = None

    # State flags
    is_index: bool = False
    is_current: bool = False
    is_in_trail: bool = False
    is_expanded: bool = False

    # NEW: Label support
    is_label: bool = False  # Non-navigable section divider

    _depth: int = 0

    @property
    def is_navigable(self) -> bool:
        """True if this node should be rendered as a link."""
        return not self.is_label and self._path != "#"
```

### Frontmatter Interface

**Section index (`_index.md`):**
```yaml
---
title: Getting Started
nav_label: true    # This section appears as a non-clickable label
weight: 10
---
```

**Alternative: Label-only sections (no index page):**
Create a section directory with only child pages. Bengal detects the missing index and treats the section title as a label:

```
docs/
├─ guides/           # No _index.md → "Guides" becomes a label
│   ├─ auth.md
│   └─ deploy.md
```

This is opt-in via config:

```toml
# bengal.toml
[nav]
auto_label_empty_sections = true  # Default: false
```

### NavTree Building Logic

```python
# bengal/core/nav_tree.py

@classmethod
def _build_node_recursive(cls, section: Section, version_id: str | None, depth: int) -> NavNode:
    """Build a NavNode from a section."""

    # Determine if this section is a label
    is_label = False

    # Check explicit frontmatter flag
    if section.metadata.get("nav_label"):
        is_label = True

    # Check index page frontmatter
    elif section.index_page and section.index_page.metadata.get("nav_label"):
        is_label = True

    # Optional: auto-label empty sections (if configured)
    # elif auto_label_enabled and section.index_page is None:
    #     is_label = True

    node = NavNode(
        id=section.name,
        title=section.nav_title or section.title,
        _path=section._path if not is_label else "#",  # Labels have no destination
        icon=section.metadata.get("icon"),
        weight=int(section.weight),
        section=section,
        is_index=bool(section.index_page),
        is_label=is_label,  # NEW
        _depth=depth,
    )

    # ... build children ...

    return node
```

### Template Usage

**Basic rendering in theme:**
```jinja
{% macro render_nav_item(item, depth) %}
  {% if item.is_label %}
    {# Non-clickable label #}
    <span class="nav-label" data-depth="{{ depth }}">
      {% if item.icon %}<span class="icon">{{ item.icon }}</span>{% endif %}
      {{ item.title }}
    </span>
  {% else %}
    {# Regular link #}
    <a href="{{ item.href }}"
       class="nav-link{% if item.is_current %} active{% endif %}"
       data-depth="{{ depth }}">
      {% if item.icon %}<span class="icon">{{ item.icon }}</span>{% endif %}
      {{ item.title }}
    </a>
  {% endif %}

  {% if item.children %}
    <ul class="nav-children">
      {% for child in item.children %}
        <li>{{ render_nav_item(child, depth + 1) }}</li>
      {% endfor %}
    </ul>
  {% endif %}
{% endmacro %}
```

**Or using `is_navigable` property:**
```jinja
{% if item.is_navigable %}
  <a href="{{ item.href }}">{{ item.title }}</a>
{% else %}
  <span class="nav-label">{{ item.title }}</span>
{% endif %}
```

### Default Theme Styling

```css
/* themes/default/assets/css/components/docs-nav.css */

.nav-label {
  display: block;
  font-size: var(--text-xs);
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: var(--color-text-muted);
  padding: var(--space-3) var(--space-4);
  margin-top: var(--space-4);
  cursor: default;
  user-select: none;
}

/* First label doesn't need top margin */
.nav-label:first-child {
  margin-top: 0;
}

/* Labels with children can optionally be collapsible */
.nav-label[data-collapsible] {
  cursor: pointer;
}

.nav-label[data-collapsible]::after {
  content: '';
  /* chevron icon */
}
```

## Implementation Plan

### Phase 1: Data Model (1-2 days)

1. Add `is_label: bool = False` to `NavNode`
2. Add `is_navigable` computed property
3. Update `NavNode.keys()` to include new fields
4. Add to Jinja2 compatibility dict access

### Phase 2: Frontmatter Support (1 day)

1. Parse `nav_label: true` in section metadata
2. Parse `nav_label: true` in index page frontmatter
3. Update `NavTree._build_node_recursive()` to set flag

### Phase 3: Default Theme (1-2 days)

1. Update `docs-nav.html` to handle `is_label`
2. Add `.nav-label` CSS styling
3. Test with sample content

### Phase 4: Documentation (1 day)

1. Document frontmatter option
2. Add examples to Content Organization guide
3. Update Theme Development guide

## Alternatives Considered

### Alternative A: `headless: true` (Hugo-style)

Use `headless: true` to mark sections without navigable index.

**Rejected because:**
- `headless` in Hugo means "don't render at all" (different semantics)
- Confusing for Hugo users expecting that behavior
- `nav_label` is more explicit about intent

### Alternative B: Config-only Labels

Define labels in `bengal.toml` rather than frontmatter:

```toml
[nav.labels.docs]
"Getting Started" = { before = "installation" }
```

**Rejected because:**
- Separates label definition from content structure
- More complex API
- Frontmatter is more discoverable
- Could be added later as an enhancement

### Alternative C: Infer from Missing Index

Automatically make sections without `_index.md` into labels.

**Partially accepted:**
- Available as opt-in config `auto_label_empty_sections`
- Not default behavior (could surprise users)
- Explicit frontmatter preferred for clarity

### Alternative D: Special URL Value

Use `href: "#"` or `href: null` to indicate non-navigable.

**Partially accepted:**
- `_path` is set to `"#"` for labels internally
- But `is_label` flag is explicit and clearer for templates
- `is_navigable` property checks both

## Impact

### Breaking Changes

None. This is purely additive:
- New optional frontmatter field
- New optional `NavNode` property
- Themes that don't check `is_label` render normally (with `href="#"`)

### Theme Compatibility

| Theme Behavior | Result |
|----------------|--------|
| Ignores `is_label` | Label renders as link to `#` (harmless) |
| Checks `is_label` | Label renders as styled divider |
| Uses `is_navigable` | Clean conditional rendering |

### Default Theme Changes

- `docs-nav.html`: ~10 lines added for label rendering
- `docs-nav.css`: ~20 lines added for `.nav-label` styling
- Total: minimal, non-breaking

## Success Criteria

| Criterion | Measurement |
|-----------|-------------|
| **Frontmatter works** | `nav_label: true` creates non-clickable item |
| **Template access** | `item.is_label` and `item.is_navigable` available |
| **Default theme styled** | Labels visually distinct from links |
| **No breaking changes** | Existing sites build without modification |
| **Backward compatible** | Themes ignoring `is_label` still work |

### Validation Tests

```python
# test_nav_labels.py

def test_nav_label_from_frontmatter():
    """Section with nav_label: true becomes a label node."""
    section = Section(
        name="guides",
        metadata={"nav_label": True, "title": "Guides"}
    )
    node = NavTree._build_node_recursive(section, None, depth=1)

    assert node.is_label is True
    assert node.is_navigable is False
    assert node._path == "#"
    assert node.title == "Guides"

def test_nav_label_has_children():
    """Label nodes can have navigable children."""
    # ... test that children are still built correctly

def test_non_label_default():
    """Sections without nav_label remain navigable."""
    section = Section(name="docs", metadata={"title": "Docs"})
    node = NavTree._build_node_recursive(section, None, depth=1)

    assert node.is_label is False
    assert node.is_navigable is True
```

## Timeline

| Phase | Duration | Deliverables |
|-------|----------|--------------|
| 1: Data Model | 1-2 days | `NavNode.is_label`, `is_navigable` |
| 2: Frontmatter | 1 day | Parse `nav_label: true` |
| 3: Default Theme | 1-2 days | Template + CSS |
| 4: Documentation | 1 day | Usage guide, examples |
| **Total** | ~5 days | |

## Future Considerations

### Potential Enhancements (Out of Scope)

1. **Collapsible labels**: Theme-controlled, labels with children can collapse/expand
2. **Config-based labels**: Define labels in `bengal.toml` for non-content groupings
3. **Label icons**: Already supported via existing `icon` field
4. **Label badges**: Count of children, "New" indicator, etc.

### Related RFCs

- RFC: Template Object Model (`page._source`, conventions) - same underscore convention applies
- RFC: Directive Base CSS - theme/core separation pattern applies here

## References

- VitePress Sidebar: https://vitepress.dev/reference/default-theme-sidebar
- Docusaurus Sidebar: https://docusaurus.io/docs/sidebar
- Hugo Headless Bundles: https://gohugo.io/content-management/page-bundles/#headless-bundle
- Bengal NavTree: `bengal/core/nav_tree.py`
- Bengal Section: `bengal/core/section/`

## Appendix: Content Structure Examples

### Example 1: Explicit Labels

```
docs/
├─ _index.md                    # "Documentation" - regular section
├─ getting-started/
│   ├─ _index.md                # nav_label: true → "Getting Started" label
│   ├─ installation.md
│   └─ quick-start.md
├─ guides/
│   ├─ _index.md                # nav_label: true → "Guides" label  
│   ├─ authentication.md
│   └─ deployment.md
└─ reference/
    ├─ _index.md                # Regular section (has content)
    ├─ api.md
    └─ cli.md
```

**Sidebar result:**
```
Documentation           (clickable - has index content)

GETTING STARTED         (label - not clickable)
  Installation
  Quick Start

GUIDES                  (label - not clickable)
  Authentication
  Deployment

Reference               (clickable - has index content)
  API
  CLI
```

### Example 2: Mixed Flat/Nested

```yaml
# docs/tutorials/_index.md
---
title: Tutorials
nav_label: true
weight: 10
---
```

```yaml
# docs/tutorials/beginner/_index.md  
---
title: Beginner
# No nav_label - this is a regular clickable section
weight: 1
---

Welcome to beginner tutorials...
```

**Sidebar result:**
```
TUTORIALS               (label)
  Beginner              (clickable - has content)
    First Steps
    Basic Concepts
  Advanced              (clickable - has content)
    Performance
    Scaling
```
