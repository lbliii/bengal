---
title: Interactive Directives
nav_title: Interactive
description: Reference for interactive directives (code-tabs, data-table)
weight: 14
tags:
- reference
- directives
- interactive
- code-tabs
- data-table
keywords:
- code-tabs
- data-table
- interactive
- tabs
- tables
- language sync
- copy button
---

# Interactive Directives

Interactive directives provide JavaScript-enhanced components for code examples and data tables.

## Key Terms

:::{glossary}
:tags: interactive
:::

## Code Tabs

Create tabbed interfaces for multi-language code examples with automatic language sync, syntax highlighting, and copy buttons.

**Aliases**: `{code_tabs}`

### Enhanced Features

Code tabs include several developer-experience enhancements:

- **Auto language sync** — All code-tabs on a page sync when user picks a language
- **Language icons** — Automatic icons for common language categories
- **Pygments highlighting** — Proper syntax coloring with line numbers and line emphasis
- **Copy button** — One-click copy per tab
- **Filename display** — Show filename badges in tab labels

### Syntax

````markdown
:::{code-tabs}
:sync: language
:line-numbers: true
:highlight: 3-5

### Python (main.py)
```python
def greet(name):
    """Say hello."""
    print(f"Hello, {name}!")

greet("World")
```

### JavaScript (index.js)
```javascript {2-3}
function greet(name) {
    // Say hello
    console.log(`Hello, ${name}!`);
}

greet("World");
```

:::{/code-tabs}
````

**Note**: You can also use `### Language Name` (without "Tab:" prefix) for simpler headings.

### Options

| Option | Default | Description |
|--------|---------|-------------|
| `:sync:` | `"language"` | Sync key for cross-tab synchronization. Use `"none"` to disable. |
| `:line-numbers:` | auto | Force line numbers on/off. Auto-enabled for 3+ lines. |
| `:highlight:` | — | Global line highlights for all tabs (e.g., `"1,3-5"`) |
| `:icons:` | `true` | Show language icons in tab labels |

**Option aliases**: `:linenos:` = `:line-numbers:`, `:hl:` = `:highlight:`, `:hl-lines:` = `:highlight:`

### Filename Display

Add filenames to tab labels using parentheses:

```markdown
### Python (main.py)
### JavaScript (app.js)
### Config (settings.yaml)
```

Filenames must end with a file extension (e.g., `.py`, `.js`). Version annotations like `(v3.12+)` are treated as part of the language name, not filenames.

### Per-Tab Line Highlights

Add line highlights to individual tabs using the standard fence syntax:

````markdown
### Python
```python {2-3}
def hello():
    # These lines are highlighted
    print("Hello!")
```
````

### Language Sync

By default, all code-tabs on a page with the same sync key synchronize. When a user selects Python in one code-tabs block, all other blocks switch to Python.

**Sync is persistent**: User preferences are saved to localStorage and restored on page load.

**Disable sync** for a specific block:

```markdown
:::{code-tabs}
:sync: none

### Before
...

### After
...
:::
```

**Custom sync groups**:

```markdown
:::{code-tabs}
:sync: api-examples

### Python
...
:::

:::{code-tabs}
:sync: config-examples

### YAML
...
:::
```

### Examples

:::{example-label} Basic Usage
:::

````markdown
:::{code-tabs}

### Python
```python
def hello():
    print("Hello, World!")
```

### JavaScript
```javascript
function hello() {
    console.log("Hello, World!");
}
```

:::{/code-tabs}
````

:::{example-label} With Filenames and Highlights
:::

````markdown
:::{code-tabs}
:line-numbers: true

### Python (api_client.py)
```python {3-4}
import requests

def get_users():
    response = requests.get("/api/users")
    return response.json()
```

### JavaScript (client.js)
```javascript {3-4}
import fetch from 'node-fetch';

async function getUsers() {
    const response = await fetch('/api/users');
    return response.json();
}
```

:::{/code-tabs}
````

:::{example-label} Multiple Languages
:::

````markdown
:::{code-tabs}

### Python
```python
print("Hello")
```

### JavaScript
```javascript
console.log("Hello");
```

### Go
```go
fmt.Println("Hello")
```

### Bash
```bash
echo "Hello"
```

:::{/code-tabs}
````

### Rendering

Code tabs render as an interactive tabbed interface with:

- Tab navigation for switching languages
- Language icons (terminal for bash/shell, database for SQL, code for others)
- Filename badges in tab labels
- Pygments syntax highlighting with line numbers
- Line emphasis for highlighted lines
- Copy button on hover
- First tab selected by default
- Synced tab selection across the page

### Language Icons

Icons are automatically assigned based on language category:

| Languages | Icon |
|-----------|------|
| bash, shell, sh, zsh, powershell, cmd | Terminal |
| sql, mysql, postgresql, sqlite | Database |
| json, yaml, toml, xml, ini | File/Code |
| All others | Code |

## Data Table

Create interactive data tables with sorting, filtering, and pagination (requires Tabulator.js).

**Syntax**:

```markdown
:::{data-table}
:columns: col1,col2,col3
:headers: Header 1,Header 2,Header 3
:sortable: true
:filterable: true
:pagination: true

Row 1, Col 1 | Row 1, Col 2 | Row 1, Col 3
Row 2, Col 1 | Row 2, Col 2 | Row 2, Col 3
:::
```

**Options**:

- `:columns:` - Comma-separated column identifiers
- `:headers:` - Comma-separated header labels
- `:sortable:` - Enable sorting: `true`, `false` (default: `true`)
- `:filterable:` - Enable filtering: `true`, `false` (default: `true`)
- `:pagination:` - Enable pagination: `true`, `false` (default: `true`)

### Examples

:::{example-label} Basic Data Table
:::

```markdown
:::{data-table}
:columns: name,type,description
:headers: Name,Type,Description

`get_user` | Function | Get user by ID
`create_user` | Function | Create new user
`update_user` | Function | Update user
:::
```

:::{example-label} With Options
:::

```markdown
:::{data-table}
:columns: name,version,status
:headers: Package,Version,Status
:sortable: true
:filterable: true
:pagination: false

bengal | 0.1.0 | Active
mistune | 3.0.0 | Active
jinja2 | 3.1.0 | Active
:::
```

### Rendering

Data tables render as interactive tables with:
- Column sorting (click headers)
- Search/filter functionality
- Pagination (if enabled)
- Responsive design

**Note**: Requires Tabulator.js to be included in your theme.

## Best Practices

1. **Code Tabs**: Use for comparing code across languages or showing multiple approaches
2. **Language Sync**: Keep sync enabled (default) for API docs with consistent language examples
3. **Filenames**: Add filenames when showing complete file contents
4. **Line Highlights**: Use sparingly to draw attention to key lines
5. **Data Tables**: Use for large datasets that benefit from sorting/filtering
6. **Performance**: Consider pagination for very large tables
7. **Accessibility**: Keyboard navigation is supported for both directives

## Related

- [Layout Directives](/docs/reference/directives/layout/) - Static tabs (`tab-set`) and cards
- [Formatting Directives](/docs/reference/directives/formatting/) - List tables (static)
- [Code Blocks](/docs/content/authoring/code-blocks/) - Standard code block syntax
