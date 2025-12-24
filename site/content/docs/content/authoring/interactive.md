---
title: Interactive Elements
nav_title: Interactive
description: Create tabs, dropdowns, steps, and other interactive content
weight: 70
category: how-to
icon: layers
---
# Interactive Elements

How to create engaging, interactive documentation.

## Tabs

Present related content in switchable tabs:

```markdown
:::{tab-set}
:::{tab-item} macOS
```bash
brew install bengal
```
:::
:::{tab-item} Linux
```bash
pip install bengal
```
:::
:::{tab-item} Windows
```powershell
pip install bengal
```
:::
:::
```

:::{tab-set}
:::{tab-item} macOS
```bash
brew install bengal
```
:::
:::{tab-item} Linux
```bash
pip install bengal
```
:::
:::{tab-item} Windows
```powershell
pip install bengal
```
:::
:::

### When to Use Tabs

- Platform-specific instructions (macOS/Linux/Windows)
- Language alternatives (Python/JavaScript/Go)
- Framework variations (React/Vue/Svelte)
- Configuration formats (YAML/TOML/JSON)

:::{tip}
Tabs remember the user's selection across pages. If someone picks "macOS", they'll see macOS content on other tabbed sections too.
:::

## Code Tabs

For multi-language code examples, use `code-tabs` — tab labels are derived directly from code fence languages:

:::{code-tabs}

```python
import requests

response = requests.get("https://api.example.com/users")
users = response.json()
```

```javascript
const response = await fetch("https://api.example.com/users");
const users = await response.json();
```

```bash
curl -X GET "https://api.example.com/users" \
  -H "Authorization: Bearer $TOKEN"
```

:::

**Key differences from `tab-set`**:

- Simpler syntax: Just code fences, no markers or nested directives
- Auto language sync: All code-tabs on the page switch together
- Built-in features: Language icons, copy button, line numbers
- Zero config: Smart defaults for code-first documentation

See [Code Blocks](/docs/content/authoring/code-blocks/) for more options like filenames, custom labels, and line highlighting.

## Dropdowns

Hide optional or detailed content:

```markdown
:::{dropdown} Advanced Configuration
:icon: settings

Here's the full configuration reference...
:::
```

:::{dropdown} Advanced Configuration
:icon: settings

Here's where advanced configuration details would go...
:::

### Dropdown Options

| Option | Description |
|--------|-------------|
| `:open:` | Start expanded |
| `:icon:` | Icon name (from icon library) |
| `:class:` | CSS class for styling |

### Dropdown Use Cases

- FAQ answers
- Advanced options
- Troubleshooting details
- Long code examples
- Optional explanations

## Step-by-Step Guides

Create visual step sequences:

```markdown
:::{steps}

:::{step} Install Dependencies
:description: Set up your development environment
:duration: 5 min

```bash
pip install bengal
```
:::{/step}

:::{step} Create Your Site
:description: Initialize a new Bengal project

```bash
bengal new site mysite
cd mysite
```
:::{/step}

:::{step} Start the Server
:description: Preview your site locally

```bash
bengal serve
```

Visit http://localhost:5173 to see your site.
:::{/step}

:::{/steps}
```

### Step Options

| Option | Description |
|--------|-------------|
| `:description:` | Brief description shown below title |
| `:duration:` | Estimated time (e.g., "5 min") |
| `:optional:` | Mark step as optional |

## Cards

Create visual navigation or feature highlights:

```markdown
:::{cards}
:columns: 3

:::{card} Getting Started
:icon: rocket
:link: docs/get-started

New to Bengal? Start here.
:::{/card}

:::{card} Tutorials
:icon: book
:link: docs/tutorials

Learn by building.
:::{/card}

:::{card} Reference
:icon: list
:link: docs/reference

Complete API docs.
:::{/card}

:::{/cards}
```

### Card Options

| Option | Description |
|--------|-------------|
| `:columns:` | Number of columns (1-4) |
| `:gap:` | Gap size: `small`, `medium`, `large` |

### Individual Card Options

| Option | Description |
|--------|-------------|
| `:icon:` | Icon name |
| `:link:` | Click destination |
| `:badge:` | Badge text |
| `:color:` | Card accent color |

## Auto-Generated Cards

Generate cards from child pages:

```markdown
:::{child-cards}
:columns: 2
:::
```

This automatically creates cards for all pages in the current section.

## Buttons

Add call-to-action buttons:

```markdown
:::{button} Get Started
:link: docs/get-started
:color: primary
:::

:::{button} View on GitHub
:link: https://github.com/example/repo
:color: secondary
:icon: github
:::
```

### Button Options

| Option | Description |
|--------|-------------|
| `:link:` | Destination URL |
| `:color:` | `primary`, `secondary`, `success`, `warning`, `danger` |
| `:icon:` | Icon name |
| `:size:` | `small`, `medium`, `large` |

## Checklists

Interactive task lists:

```markdown
:::{checklist} Deployment Checklist
- Run tests locally
- Update version number
- Create changelog entry
- Tag the release
- Deploy to staging
- Verify staging
- Deploy to production
:::
```

:::{checklist} Deployment Checklist
- Run tests locally
- Update version number
- Create changelog entry
- Tag the release
- Deploy to staging
- Verify staging
- Deploy to production
:::

## Combining Elements

Create rich, interactive content by combining elements:

```markdown
:::{steps}

:::{step} Choose Your Platform
:description: Select installation method

:::{tab-set}
:::{tab-item} pip
```bash
pip install bengal
```
:::
:::{tab-item} pipx
```bash
pipx install bengal
```
:::
:::
:::

:::{step} Verify Installation

```bash
bengal --version
```

:::{dropdown} Troubleshooting
:icon: alert

If you see "command not found", ensure Python's bin directory is in your PATH.
:::
:::

:::
```

## Best Practices

:::{checklist}
- Use tabs for platform/language alternatives
- Use dropdowns for optional details
- Use steps for sequential procedures
- Use cards for navigation or feature lists
- Don't over-nest interactive elements
- Ensure content works without JavaScript
:::

## Accessibility

All interactive elements are keyboard-navigable:

- **Tabs**: Arrow keys to switch, Enter to select
- **Dropdowns**: Enter/Space to toggle
- **Cards**: Tab to focus, Enter to follow link

::::{seealso}
- [[docs/reference/directives/interactive|Interactive Directives Reference]] — Complete options
- [[docs/reference/directives/layout|Layout Directives]] — Cards and grids
- [[docs/reference/directives/navigation|Navigation Directives]] — Breadcrumbs, prev/next
::::
