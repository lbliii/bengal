---
title: Interactive Directives
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
---

# Interactive Directives

Interactive directives provide JavaScript-enhanced components for code examples and data tables.

## Key Terms

:::{glossary}
:tags: interactive
:::

## Code Tabs

Create tabbed interfaces for multi-language code examples.

**Syntax**:

````markdown
:::{code-tabs}

### Tab: Language Name
```language
code here
```

### Tab: Another Language
```language
more code
```

:::{/code-tabs}
````

**Note**: You can also use `### Language Name` (without "Tab:" prefix).

**Alias**: `{code_tabs}` (underscore variant)

### Examples

**Python and JavaScript**:

````markdown
:::{code-tabs}

### Tab: Python
```python
def hello():
    print("Hello, World!")
```

### Tab: JavaScript
```javascript
function hello() {
    console.log("Hello, World!");
}
```

:::{/code-tabs}
````

**Multiple Languages**:

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

:::{/code-tabs}
````

### Rendering

Code tabs render as interactive tabbed interface with:
- Tab navigation for switching languages
- Syntax highlighting for each language
- First tab selected by default

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

**Basic Data Table**:

```markdown
:::{data-table}
:columns: name,type,description
:headers: Name,Type,Description

`get_user` | Function | Get user by ID
`create_user` | Function | Create new user
`update_user` | Function | Update user
:::
```

**With Options**:

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
2. **Data Tables**: Use for large datasets that benefit from sorting/filtering
3. **Performance**: Consider pagination for very large tables
4. **Accessibility**: Ensure JavaScript is enabled for interactive features

## Related

- [Layout Directives](/docs/reference/directives/layout/) - Static tabs and cards
- [Formatting Directives](/docs/reference/directives/formatting/) - List tables (static)
