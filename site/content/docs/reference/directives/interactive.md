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

### Features

- **Simplified syntax** — Tab labels derived from code fence language (no markers needed)
- **Auto language sync** — All code-tabs on a page sync when user picks a language
- **Language icons** — Automatic icons for common language categories
- **Pygments highlighting** — Proper syntax coloring with line numbers and line emphasis
- **Copy button** — One-click copy per tab
- **Filename display** — Show filename badges in tab labels

### Syntax

Tab labels are derived automatically from the code fence language:

````markdown
:::{code-tabs}

```python main.py {3-4}
def greet(name):
    """Say hello."""
    print(f"Hello, {name}!")

greet("World")
```

```javascript index.js {2-3}
function greet(name) {
    // Say hello
    console.log(`Hello, ${name}!`);
}

greet("World");
```

:::
````

### Info String Format

The code fence info string supports filename, title override, and highlights:

```
language [filename] [title="Label"] [{line-highlights}]
```

| Example | Tab Label | Filename Badge | Highlights |
|---------|-----------|----------------|------------|
| `python` | Python | — | — |
| `python client.py` | Python | client.py | — |
| `python {3-4}` | Python | — | Lines 3-4 |
| `python client.py {3-4}` | Python | client.py | Lines 3-4 |
| `python title="Flask"` | Flask | — | — |
| `python app.py title="Flask" {5-7}` | Flask | app.py | Lines 5-7 |

### Options

| Option | Default | Description |
|--------|---------|-------------|
| `:sync:` | `"language"` | Sync key for cross-tab synchronization. Use `"none"` to disable. |
| `:linenos:` | auto | Force line numbers on/off. Auto-enabled for 3+ lines. |

**Option aliases**: `:line-numbers:` = `:linenos:`

### Custom Tab Labels

Use `title="..."` to override the default language-derived label:

````markdown
:::{code-tabs}

```javascript title="React"
const [count, setCount] = useState(0);
```

```javascript title="Vue"
const count = ref(0);
```

:::
````

### Files Without Extensions

For files like `Dockerfile` that have no extension, use `title=`:

````markdown
:::{code-tabs}

```dockerfile title="Dockerfile"
FROM python:3.14-slim
```

```yaml docker-compose.yml
services:
  web:
    build: .
```

:::
````

### Language Display Names

Languages are automatically formatted with proper casing:

| Language | Display Name |
|----------|-------------|
| `javascript`, `js` | JavaScript |
| `typescript`, `ts` | TypeScript |
| `cpp`, `cxx` | C++ |
| `csharp`, `cs` | C# |
| `golang` | Go |
| `python` | Python |
| Others | Capitalized |

### Language Sync

By default, all code-tabs on a page with the same sync key synchronize. When a user selects Python in one code-tabs block, all other blocks switch to Python.

**Sync is persistent**: User preferences are saved to localStorage and restored on page load.

**Disable sync** for a specific block:

````markdown
:::{code-tabs}
:sync: none

```python
# Before
```

```python
# After
```

:::
````

**Custom sync groups**:

````markdown
:::{code-tabs}
:sync: api-examples

```python
...
```

:::

:::{code-tabs}
:sync: config-examples

```yaml
...
```

:::
````

### Examples

:::{example-label} Basic Usage
:::

````markdown
:::{code-tabs}

```python
def hello():
    print("Hello, World!")
```

```javascript
function hello() {
    console.log("Hello, World!");
}
```

:::
````

:::{example-label} With Filenames and Highlights
:::

````markdown
:::{code-tabs}

```python api_client.py {3-4}
import requests

def get_users():
    response = requests.get("/api/users")
    return response.json()
```

```javascript client.js {3-4}
import fetch from 'node-fetch';

async function getUsers() {
    const response = await fetch('/api/users');
    return response.json();
}
```

:::
````

:::{example-label} Multiple Languages
:::

````markdown
:::{code-tabs}

```python
print("Hello")
```

```javascript
console.log("Hello");
```

```go
fmt.Println("Hello")
```

```bash
echo "Hello"
```

:::
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

### Legacy Syntax

The older `### Language` marker syntax is still supported for backward compatibility:

````markdown
:::{code-tabs}

### Python (main.py)
```python
print("hello")
```

### JavaScript
```javascript
console.log("hello");
```

:::
````

This legacy syntax is not recommended for new content.

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
patitas | 1.0.0 | Active
kida | 1.0.0 | Active
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
