---
title: From Docusaurus/MDX
description: Onboarding guide for Docusaurus and MDX users migrating to Bengal
weight: 30
tags:
- tutorial
- migration
- docusaurus
- mdx
- react
keywords:
- docusaurus
- mdx
- react
- jsx
- migration
- components
---

# Bengal for Docusaurus/MDX Users

Great news: You get the same rich components without React, JSX, or npm. Bengal's directives provide similar functionality in pure Markdown.

## Quick Wins (5 Minutes)

### Admonition Syntax Is Almost Identical

| Docusaurus | Bengal | Status |
|------------|--------|--------|
| `:::note` | `:::{note}` | ✅ Just add `{}` |
| `:::tip` | `:::{tip}` | ✅ Just add `{}` |
| `:::warning` | `:::{warning}` | ✅ Just add `{}` |
| `:::danger` | `:::{danger}` | ✅ Just add `{}` |
| `:::info` | `:::{info}` | ✅ Just add `{}` |

### Side-by-Side

:::{tab-set}

:::{tab} Docusaurus
```markdown
:::note
This is a note
:::

:::tip Pro Tip
This is a tip with a title
:::
```
:::{/tab}

:::{tab} Bengal
```markdown
:::{note}
This is a note
:::

:::{tip} Pro Tip
This is a tip with a title
:::
```
:::{/tab}

:::{/tab-set}

The only difference: `:::note` → `:::{note}` (add curly braces).

---

## Component → Directive Translation

### Tabs

:::{tab-set}

:::{tab} Docusaurus (MDX)
```jsx
import Tabs from '@theme/Tabs';
import TabItem from '@theme/TabItem';

<Tabs>
  <TabItem value="js" label="JavaScript">
    ```javascript
    console.log("Hello");
    ```
  </TabItem>
  <TabItem value="py" label="Python">
    ```python
    print("Hello")
    ```
  </TabItem>
</Tabs>
```
:::{/tab}

:::{tab} Bengal (No imports!)
````markdown
:::{tab-set}
:::{tab} JavaScript
```javascript
console.log("Hello");
```
:::{/tab}
:::{tab} Python
```python
print("Hello")
```
:::{/tab}
:::{/tab-set}
````
:::{/tab}

:::{/tab-set}

:::{tip}
No imports, no JSX, no React. Just markdown.
:::

### Code Blocks

:::{tab-set}

:::{tab} Docusaurus

```jsx
import CodeBlock from '@theme/CodeBlock';

<CodeBlock language="python" title="hello.py" showLineNumbers>
def hello():
    print("Hello!")
</CodeBlock>
```

:::{/tab}

:::{tab} Bengal
````markdown
```python title="hello.py"
def hello():
    print("Hello!")
```
````
:::{/tab}

:::{/tab-set}

### Cards / Feature Grid

:::{tab-set}

:::{tab} Docusaurus (Custom Component)
```jsx
import {Card, CardGrid} from '@site/src/components/Card';

<CardGrid>
  <Card title="Quick Start" href="/docs/quickstart">
    Get started in 5 minutes
  </Card>
  <Card title="API Reference" href="/docs/api">
    Complete API documentation
  </Card>
</CardGrid>
```
:::{/tab}

:::{tab} Bengal (Built-in!)
```markdown
:::{cards}
:columns: 2
:::{card} Quick Start
:link: /docs/quickstart/
Get started in 5 minutes
:::{/card}
:::{card} API Reference
:link: /docs/api/
Complete API documentation
:::{/card}
:::{/cards}
```
:::{/tab}

:::{/tab-set}

### Collapsible Sections

:::{tab-set}

:::{tab} Docusaurus
```jsx
<details>
  <summary>Click to expand</summary>

  Hidden content here with **markdown** support.
</details>
```
:::{/tab}

:::{tab} Bengal
```markdown
:::{dropdown} Click to expand
:icon: info

Hidden content here with **markdown** support.
:::
```
:::{/tab}

:::{/tab-set}

### Live Code Editor

:::{tab-set}

:::{tab} Docusaurus
```jsx
```jsx live
function Hello() {
  return <div>Hello World!</div>;
}
```
:::{/tab}

:::{tab} Bengal
```markdown
<!-- Live editors not built-in -->
<!-- Options: -->
<!-- 1. Link to CodeSandbox/StackBlitz -->
<!-- 2. Embed external playground -->
<!-- 3. Use static code examples -->

```jsx
function Hello() {
  return <div>Hello World!</div>;
}
```
:::{/tab}

:::{/tab-set}

:::{note}
Bengal focuses on documentation, not interactive playgrounds. For live code, link to external tools like CodeSandbox, StackBlitz, or Jupyter.
:::

---

## What You Don't Need Anymore

| Docusaurus Requires | Bengal |
|---------------------|--------|
| `npm install` | `pip install bengal` |
| `node_modules/` (500MB+) | ~5MB Python package |
| React/JSX knowledge | Just Markdown |
| Component imports | Built-in directives |
| `package.json` | `bengal.toml` |
| Build step (Webpack) | Simple file processing |
| Hydration debugging | Static HTML |

---

## Configuration Comparison

### Basic Config

:::{tab-set}

:::{tab} Docusaurus (docusaurus.config.js)
```javascript
module.exports = {
  title: 'My Site',
  tagline: 'Documentation made easy',
  url: 'https://example.com',
  baseUrl: '/',

  presets: [
    [
      '@docusaurus/preset-classic',
      {
        docs: {
          sidebarPath: require.resolve('./sidebars.js'),
        },
        theme: {
          customCss: require.resolve('./src/css/custom.css'),
        },
      },
    ],
  ],
};
```
:::{/tab}

:::{tab} Bengal (bengal.toml)
```toml
[site]
title = "My Site"
description = "Documentation made easy"
baseurl = "https://example.com"
theme = "bengal"
```
:::{/tab}

:::{/tab-set}

### Sidebar Configuration

:::{tab-set}

:::{tab} Docusaurus (sidebars.js)
```javascript
module.exports = {
  docs: [
    'intro',
    {
      type: 'category',
      label: 'Getting Started',
      items: ['quickstart', 'installation'],
    },
    {
      type: 'category',
      label: 'Guides',
      items: ['guide1', 'guide2'],
    },
  ],
};
```
:::{/tab}

:::{tab} Bengal (Automatic!)
```markdown
<!-- Bengal auto-generates sidebar from directory structure -->
<!-- Use weight frontmatter for ordering: -->

<!-- content/docs/getting-started/_index.md -->
---
title: Getting Started
weight: 10
---

<!-- content/docs/getting-started/quickstart.md -->
---
title: Quickstart  
weight: 10
---

<!-- content/docs/getting-started/installation.md -->
---
title: Installation
weight: 20
---
```
:::{/tab}

:::{/tab-set}

:::{tip}
No `sidebars.js` needed! Bengal generates navigation from your directory structure. Use `weight` frontmatter to control order.
:::

---

## Feature Comparison

### What Bengal Has (No React Required)

| Feature | Docusaurus | Bengal |
|---------|------------|--------|
| Admonitions | `:::note` | `:::{note}` ✅ |
| Tabs | `<Tabs>` component | `:::{tab-set}` ✅ |
| Code blocks | Built-in | Built-in ✅ |
| Cards | Custom component | `:::{cards}` ✅ |
| Dropdowns | `<details>` | `:::{dropdown}` ✅ |
| Steps | Custom component | `:::{steps}` ✅ |
| Badges | Custom component | `:::{badge}` ✅ |
| Buttons | Custom component | `:::{button}` ✅ |
| Include files | MDX import | `:::{include}` ✅ |
| Code inclusion | MDX import | `:::{literalinclude}` ✅ |
| TOC | Built-in | Built-in ✅ |
| Search | Algolia | Built-in index |
| Breadcrumbs | Theme | `:::{breadcrumbs}` ✅ |
| Prev/Next | Built-in | `:::{prev-next}` ✅ |

### What's Different (Trade-offs)

| Feature | Docusaurus | Bengal | Trade-off |
|---------|------------|--------|-----------|
| Live code | Built-in | External links | Simpler, no hydration |
| Versioning | Plugin | Manual | Copy to `v1/`, `v2/` folders |
| i18n | Plugin | `lang` frontmatter | Simpler, less automated |
| Algolia | Integrated | External | Bring your own search |
| Custom components | React/JSX | Templates | Less flexible, more standard |
| Plugins | npm ecosystem | Built-in directives | Fewer options, zero config |

---

## MDX-Specific Migration

### Imports Don't Work (You Don't Need Them)

```jsx
// ❌ MDX - Won't work in Bengal
import MyComponent from '@site/src/components/MyComponent';

<MyComponent prop="value" />
```

```markdown
<!-- ✅ Bengal - Use built-in directives instead -->
:::{card} Title
:link: /path/

Content here
:::
```

### Export/Props Don't Work (Use Frontmatter)

```jsx
// ❌ MDX - Won't work
export const data = { version: '2.0' };

Current version: {data.version}
```

```markdown
<!-- ✅ Bengal - Use frontmatter -->
---
title: My Page
version: "2.0"
---

Current version: {{ page.metadata.version }}
```

### JSX in Markdown → Use Directives or HTML

```jsx
// ❌ MDX - Won't work
<div className="custom-box">
  <h3>Custom Content</h3>
  <p>With JSX styling</p>
</div>
```

```markdown
<!-- ✅ Bengal - Use directive or HTML -->
:::{card} Custom Content
:class: custom-box

With directive styling
:::

<!-- Or plain HTML (still works) -->
<div class="custom-box">
  <h3>Custom Content</h3>
  <p>With HTML styling</p>
</div>
```

---

## Directory Structure Comparison

| Docusaurus | Bengal | Notes |
|------------|--------|-------|
| `docs/` | `content/docs/` | Content location |
| `blog/` | `content/blog/` | Blog posts |
| `src/pages/` | `content/` | Static pages |
| `src/components/` | Not needed | Use directives |
| `src/css/` | `themes/[name]/static/css/` | Custom CSS |
| `static/` | `assets/` | Static files |
| `docusaurus.config.js` | `bengal.toml` | Configuration |
| `sidebars.js` | Auto-generated | Use `weight` |
| `package.json` | `pyproject.toml` (optional) | Dependencies |

---

## What Bengal Adds

### Variable Substitution in Content

```markdown
---
title: API Reference
api_version: "3.0"
base_url: "https://api.example.com"
---

# {{ page.title }}

Current API version: **{{ page.metadata.api_version }}**

Base URL: `{{ page.metadata.base_url }}`
```

Docusaurus requires React state or MDX exports for this.

### Centralized Glossary

```yaml
# data/glossary.yaml
terms:
  - term: API
    definition: Application Programming Interface
    tags: [api, core]

  - term: Endpoint
    definition: A specific URL path that accepts requests
    tags: [api, http]
```

```markdown
<!-- In any page -->
:::{glossary}
:tags: api
:::
```

### Navigation Directives

```markdown
<!-- Auto-generate cards from child pages -->
:::{child-cards}
:columns: 3
:::

<!-- Show sibling pages in section -->
:::{siblings}
:::

<!-- Related pages by tag -->
:::{related}
:tags: api, authentication
:::
```

### Data Tables

```markdown
:::{data-table}
:source: data/endpoints.yaml
:columns: method, path, description
:sortable: true
:filterable: true
:::
```

---

## Migration Checklist

:::{checklist} Before You Start
- [ ] Install Bengal: `pip install bengal`
- [ ] Create new site: `bengal new site mysite`
- [ ] Keep Docusaurus running for reference
:::

:::{checklist} Content Migration
- [ ] Copy `docs/` to `content/docs/`
- [ ] Copy `blog/` to `content/blog/`
- [ ] Convert `:::note` to `:::{note}` (add braces)
- [ ] Remove MDX imports (use built-in directives)
- [ ] Convert React components to directives
:::

:::{checklist} Configuration
- [ ] Create `bengal.toml` from `docusaurus.config.js`
- [ ] Remove `sidebars.js` (use `weight` frontmatter)
- [ ] Move `static/` to `assets/`
:::

:::{checklist} Cleanup
- [ ] Remove `node_modules/`
- [ ] Remove `package.json`
- [ ] Remove `src/` directory
:::

:::{checklist} Verify
- [ ] Build: `bengal build`
- [ ] Check: `bengal health linkcheck`
- [ ] Preview: `bengal serve`
:::

---

## Quick Reference Card

| Task | Docusaurus | Bengal |
|------|------------|--------|
| Install | `npm install` | `pip install bengal` |
| New site | `npx create-docusaurus` | `bengal new site` |
| Build | `npm run build` | `bengal build` |
| Serve | `npm start` | `bengal serve` |
| Note | `:::note` | `:::{note}` |
| Tabs | `<Tabs>` + import | `:::{tab-set}` |
| Cards | Custom component | `:::{cards}` |
| Dropdown | `<details>` | `:::{dropdown}` |
| Include | MDX import | `:::{include}` |

---

## Common Questions

### "Can I use React components?"

No. Bengal outputs static HTML. For interactivity:
- Use vanilla JavaScript
- Embed external widgets (CodeSandbox, etc.)
- Link to interactive demos

### "What about live code playgrounds?"

Link to external tools:
```markdown
[Try it on CodeSandbox](https://codesandbox.io/s/example)
[Open in StackBlitz](https://stackblitz.com/edit/example)
```

### "Can I keep my custom CSS?"

Yes! Put it in `themes/[name]/static/css/custom.css` and include in your template.

### "What about search?"

Bengal generates a search index. For Algolia-level search, integrate externally or use the built-in index with JavaScript.

---

## Next Steps

- [Directives Reference](/docs/reference/directives/) - All available directives  
- [Writer Quickstart](/docs/get-started/quickstart-writer/) - Full markdown guide
- [Configuration](/docs/about/concepts/configuration/) - Config options
