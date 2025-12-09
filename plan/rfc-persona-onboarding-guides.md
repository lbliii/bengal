# RFC: Persona-Targeted Onboarding Guides

**Status**: Draft  
**Created**: 2025-12-05  
**Author**: AI Assistant

---

## Executive Summary

Create three focused onboarding guides for users migrating from specific documentation tool ecosystems:

1. **Sphinx/RST Users** → Bengal
2. **Hugo Shortcode Users** → Bengal  
3. **Docusaurus/MDX Users** → Bengal

Each guide speaks the user's existing language, mapping familiar concepts to Bengal equivalents.

---

## Problem Statement

Current Bengal documentation assumes users are starting fresh or have generic SSG knowledge. Users coming from specific ecosystems face friction:

- **Sphinx users** know RST directives but not MyST syntax
- **Hugo users** expect shortcodes, not directives
- **MDX users** expect React components, not markdown extensions

**Result**: Longer onboarding time, missed feature discovery, frustration.

---

## Proposed Solution

Three parallel guides using the same structure but tailored vocabulary:

### Structure (Common to All)

```markdown
1. Quick Wins (5-minute section)
   - "Your X works the same" (instant familiarity)
   - "Here's the one thing that's different"

2. Concept Mapping Table
   - Feature | [Source Tool] | Bengal Equivalent | Notes

3. Common Patterns Translation
   - Side-by-side examples

4. What Bengal Adds
   - Features not available in source tool

5. What's Different (Honest Gaps)
   - Features that work differently or don't exist
```

---

## Guide 1: Sphinx/RST Users → Bengal

### Target Audience
- Experienced with Sphinx/Docutils
- Comfortable with RST directive syntax
- May use MyST already (bonus: nearly native)
- Values: structured cross-references, API docs, extensibility

### Key Mappings

| Sphinx/RST | Bengal | Notes |
|------------|--------|-------|
| `.. note::` | `:::{note}` | Identical semantics |
| `.. warning::` | `:::{warning}` | Identical semantics |
| `.. code-block:: python` | ` ```python ` | Standard fenced code |
| `.. literalinclude::` | `:::{literalinclude}` | ✅ Same concept |
| `.. include::` | `:::{include}` | ✅ Same concept |
| `.. toctree::` | Navigation directives | `{child-cards}`, `{siblings}` |
| `:ref:`label`` | `[[link]]` | Cross-reference syntax |
| `:doc:`path`` | `[text](path.md)` | Standard markdown |
| `:term:`glossary`` | `:::{glossary}` directive | Centralized terms |
| `.. glossary::` | `data/glossary.yaml` | Data-driven |
| `conf.py` | `bengal.toml` | Config file |
| `_static/` | `assets/` | Static assets |
| `_templates/` | `themes/[name]/templates/` | Template override |
| Sphinx extensions | Bengal directives | Built-in or custom |

### Quick Wins Section

```markdown
## Your RST Knowledge Transfers

If you know Sphinx, you're 80% there:

| You Know | Bengal Equivalent |
|----------|-------------------|
| `.. note::` | `:::{note}` ✅ |
| `.. warning::` | `:::{warning}` ✅ |
| `.. tip::` | `:::{tip}` ✅ |
| `.. literalinclude::` | `:::{literalinclude}` ✅ |

**The main difference**: Triple-colon fence (`:::`) instead of double-dot (`..`).
```

### Unique Bengal Features (Sphinx Doesn't Have)

- **Cards**: `:::{cards}` for grid layouts
- **Tabs**: `:::{tab-set}` for content tabs
- **Steps**: `:::{steps}` for visual guides
- **Dropdowns**: `:::{dropdown}` for collapsible content
- **Data Tables**: `:::{data-table}` with Tabulator.js
- **Variable substitution**: `{{ page.title }}` in markdown
- **Hot reload**: Real-time preview during editing

### Honest Gaps

- No autodoc (Python introspection) - use `bengal autodoc` CLI separately
- No intersphinx (cross-project references) - use explicit URLs
- No custom builders - single HTML output focus

---

## Guide 2: Hugo Shortcode Users → Bengal

### Target Audience
- Experienced with Hugo templating
- Uses shortcodes for rich content
- Comfortable with Go templates
- Values: speed, simplicity, themes

### Key Mappings

| Hugo | Bengal | Notes |
|------|--------|-------|
| `{{< shortcode >}}` | `:::{directive}` | Different syntax, same purpose |
| `{{< figure >}}` | `![alt](src)` + `:::{card}` | Markdown + directive |
| `{{< highlight >}}` | ` ```lang ` | Fenced code |
| `{{< youtube >}}` | Embed HTML | No built-in shortcode |
| `{{< ref >}}` | `[text](path.md)` | Standard links |
| `{{< relref >}}` | `[[cross-ref]]` | Internal references |
| `{{ .Params.x }}` | `{{ page.metadata.x }}` | Similar! |
| `{{ .Site.x }}` | `{{ site.config.x }}` | Similar! |
| `config.toml` | `bengal.toml` | Nearly identical |
| `content/` | `content/` | Same structure |
| `_index.md` | `_index.md` | Same concept |
| `layouts/` | `themes/[name]/templates/` | Template location |
| `static/` | `assets/` | Static assets |

### Quick Wins Section

```markdown
## Your Hugo Knowledge Transfers

Good news: Bengal's content model is very similar to Hugo!

| Hugo | Bengal | Status |
|------|--------|--------|
| `content/` structure | `content/` | ✅ Identical |
| `_index.md` sections | `_index.md` | ✅ Identical |
| YAML/TOML frontmatter | YAML frontmatter | ✅ Identical |
| `{{ .Params.x }}` | `{{ page.metadata.x }}` | ✅ Similar |
| `config.toml` | `bengal.toml` | ✅ Similar |

**The key difference**: Shortcodes become directives.
```

### Shortcode → Directive Examples

```markdown
## Translating Shortcodes

### Callout Boxes

**Hugo**:
```go
{{< notice warning >}}
This is a warning
{{< /notice >}}
```

**Bengal**:
```markdown
:::{warning}
This is a warning
:::
```

### Code with Tabs

**Hugo**:
```go
{{< tabs >}}
{{< tab "Python" >}}
print("hello")
{{< /tab >}}
{{< tab "JavaScript" >}}
console.log("hello");
{{< /tab >}}
{{< /tabs >}}
```

**Bengal**:
```markdown
::::{tab-set}
:::{tab-item} Python
```python
print("hello")
```
:::
:::{tab-item} JavaScript
```javascript
console.log("hello");
```
:::
::::
```
```

### What Bengal Adds

- **Built-in directives**: No need to copy shortcode templates
- **Cards**: `:::{cards}` for feature grids
- **Steps**: `:::{steps}` for tutorials
- **Data tables**: Interactive tables with sorting/filtering
- **Navigation**: Auto-generated breadcrumbs, siblings, prev/next
- **Glossary**: Centralized term definitions

### Honest Gaps

- No custom shortcode creation - use directives or templates
- No Go template functions - Jinja2 filters instead
- No Hugo Modules - themes are local

---

## Guide 3: Docusaurus/MDX Users → Bengal

### Target Audience
- Experienced with React/MDX
- Uses JSX components in markdown
- Comfortable with npm ecosystem
- Values: interactivity, React integration

### Key Mappings

| Docusaurus/MDX | Bengal | Notes |
|----------------|--------|-------|
| `<Tabs>` component | `:::{tab-set}` | No JSX needed |
| `<TabItem>` | `:::{tab-item}` | No JSX needed |
| `<Admonition>` | `:::{note}`, `:::{warning}` | Built-in |
| `:::note` | `:::{note}` | Identical! |
| `:::tip` | `:::{tip}` | Identical! |
| `<CodeBlock>` | ` ```lang ` | Fenced code |
| `import Component` | Not applicable | No imports needed |
| `export const x` | Not applicable | No exports |
| `{props.x}` | `{{ page.metadata.x }}` | Different syntax |
| `docusaurus.config.js` | `bengal.toml` | Config file |
| `docs/` | `content/docs/` | Content location |
| `sidebars.js` | Auto-generated | Weight-based ordering |
| `static/` | `assets/` | Static assets |

### Quick Wins Section

```markdown
## Your Docusaurus Knowledge Transfers

Great news: Docusaurus admonition syntax works in Bengal!

| Docusaurus | Bengal | Status |
|------------|--------|--------|
| `:::note` | `:::{note}` | ✅ Nearly identical |
| `:::tip` | `:::{tip}` | ✅ Nearly identical |
| `:::warning` | `:::{warning}` | ✅ Nearly identical |
| `:::danger` | `:::{danger}` | ✅ Nearly identical |
| Markdown links | Markdown links | ✅ Identical |

**The key difference**: No JSX. Directives replace React components.
```

### MDX Component → Directive Examples

```markdown
## From Components to Directives

### Tabs

**Docusaurus MDX**:
```jsx
import Tabs from '@theme/Tabs';
import TabItem from '@theme/TabItem';

<Tabs>
  <TabItem value="py" label="Python">
    ```python
    print("hello")
    ```
  </TabItem>
  <TabItem value="js" label="JavaScript">
    ```javascript
    console.log("hello");
    ```
  </TabItem>
</Tabs>
```

**Bengal** (no imports!):
```markdown
::::{tab-set}
:::{tab-item} Python
```python
print("hello")
```
:::
:::{tab-item} JavaScript
```javascript
console.log("hello");
```
:::
::::
```

### Feature Cards

**Docusaurus MDX**:
```jsx
import {Card, CardGrid} from '@site/src/components/Card';

<CardGrid>
  <Card title="Feature 1" href="/docs/feature1">
    Description here
  </Card>
</CardGrid>
```

**Bengal** (built-in!):
```markdown
::::{cards}
:columns: 3

:::{card} Feature 1
:link: /docs/feature1

Description here
:::
::::
```
```

### What Bengal Adds (No React Required)

- **All components built-in**: No npm install, no imports
- **Cards**: Feature grids without custom components
- **Steps**: Visual step-by-step without JSX
- **Dropdowns**: Collapsible sections without state
- **Data tables**: Interactive tables without React state
- **Glossary**: Term definitions without custom components
- **Variable substitution**: `{{ page.title }}` without props

### What's Different (Trade-offs)

| Docusaurus Has | Bengal Equivalent | Trade-off |
|----------------|-------------------|-----------|
| React interactivity | Static + vanilla JS | Simpler, no hydration |
| Live code editors | Not built-in | Focus on documentation |
| Algolia DocSearch | Search index | Different integration |
| Versioned docs | Not built-in | Manual versioning |
| i18n plugin | `lang` frontmatter | Simpler approach |
| Blog plugin | `type: post` sections | Built-in |

### Honest Gaps

- No JSX/React in markdown
- No live code playgrounds (use external tools)
- No versioned documentation system
- No plugin ecosystem (directives are built-in)

---

## Implementation Plan

### Phase 1: Create Guide Structure
1. Create `site/content/docs/tutorials/onboarding/` directory
2. Add `_index.md` for the section
3. Create three guide files

### Phase 2: Content Development
1. Write Sphinx guide (most similar, easiest)
2. Write Hugo guide (leverage existing migration doc)
3. Write MDX guide (most different, careful positioning)

### Phase 3: Cross-Linking
1. Update existing migration guide to link to persona guides
2. Add to main docs navigation
3. Cross-link between guides for users who know multiple tools

---

## File Structure

```
site/content/docs/tutorials/onboarding/
├── _index.md                    # Overview: "Coming from another tool?"
├── from-sphinx.md               # Sphinx/RST users
├── from-hugo.md                 # Hugo shortcode users  
├── from-docusaurus.md           # Docusaurus/MDX users
└── feature-comparison.md        # Side-by-side feature matrix (optional)
```

---

## Success Criteria

1. **Time to first success**: User can create equivalent content in < 10 minutes
2. **Concept mapping**: 100% of common features have documented equivalents
3. **Honest gaps**: Clearly documented what doesn't translate
4. **Quick reference**: Single-page mapping tables for quick lookup

---

## Open Questions

1. Should we include tool-specific migration scripts?
2. Should guides include video/animated examples?
3. Should we create a unified "feature comparison" page?
4. Priority order for writing (Sphinx → Hugo → MDX)?

---

## Next Steps

- [ ] Review RFC and approve structure
- [ ] Create directory structure
- [ ] Draft Sphinx guide (most familiar territory)
- [ ] Draft Hugo guide (enhance existing content)
- [ ] Draft Docusaurus guide (new territory)
- [ ] Review and polish all three

---

## Evidence

### Bengal Features Verified

| Feature | Source | Evidence |
|---------|--------|----------|
| Admonitions | `bengal/rendering/plugins/directives/admonitions.py` | 10 types: note, tip, warning, etc. |
| Tabs | `bengal/rendering/plugins/directives/tabs.py` | `{tab-set}`, `{tab-item}` |
| Cards | `bengal/rendering/plugins/directives/cards.py` | `{cards}`, `{card}`, `{child-cards}` |
| Literalinclude | `bengal/rendering/plugins/directives/literalinclude.py` | Same as Sphinx |
| Include | `bengal/rendering/plugins/directives/include.py` | Same as Sphinx |
| Variable substitution | `bengal/rendering/plugins/variable_substitution.py` | `{{ page.x }}` |
| Cross-references | `bengal/rendering/plugins/cross_references.py` | `[[link]]` syntax |
| Glossary | `bengal/rendering/plugins/directives/glossary.py` | Data-driven terms |
| Steps | `bengal/rendering/plugins/directives/steps.py` | `{steps}`, `{step}` |
| Dropdowns | `bengal/rendering/plugins/directives/dropdown.py` | Collapsible sections |

### Directive Syntax Verified
- MyST-compatible `:::{name}` syntax
- Fenced ` ```{name} ` alternative
- Nesting with fence count increment

**Confidence**: 95% 🟢



