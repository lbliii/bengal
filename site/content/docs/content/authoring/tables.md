---
title: Tables
nav_title: Tables
description: Create simple and complex tables using pipe syntax, list-table directive, and interactive data-tables
weight: 50
category: how-to
icon: layers
keywords:
- tables
- list-table
- data-table
- markdown tables
- comparison tables
---

# Tables

Bengal supports three table formats, each suited to different use cases.

## Quick Reference

| Format | Best For | Features |
|--------|----------|----------|
| **Pipe tables** | Simple data, 3-5 columns | Standard Markdown, easy to write |
| **`list-table`** | Complex cells, multi-line content | Code blocks, lists, formatted text |
| **`data-table`** | Large datasets (50+ rows) | Sort, filter, search, pagination |

## Pipe Tables (Standard Markdown)

Use pipe tables for simple, scannable data:

```markdown
| Name | Role | Location |
|------|------|----------|
| Alice | Engineer | NYC |
| Bob | Designer | LA |
| Carol | PM | Seattle |
```

**Result**:

| Name | Role | Location |
|------|------|----------|
| Alice | Engineer | NYC |
| Bob | Designer | LA |
| Carol | PM | Seattle |

### Column Alignment

Control alignment with colons in the separator row:

```markdown
| Left | Center | Right |
|:-----|:------:|------:|
| Text | Text   | 99.99 |
| More | More   | 0.50  |
```

| Left | Center | Right |
|:-----|:------:|------:|
| Text | Text   | 99.99 |
| More | More   | 0.50  |

- `:---` left-align (default)
- `:--:` center
- `---:` right-align

## List-Table Directive

For tables with multi-line cells, code blocks, or nested content:

```markdown
:::{list-table} Pricing Comparison
:header-rows: 1
:widths: 20 40 40

* - Feature
  - Free Plan
  - Pro Plan
* - Storage
  - 5 GB
  - Unlimited
* - Support
  - Community forums
  - Priority email + phone
* - API Access
  - 1,000 calls/month
  - Unlimited
:::
```

**Result**:

:::{list-table} Pricing Comparison
:header-rows: 1
:widths: 20 40 40

* - Feature
  - Free Plan
  - Pro Plan
* - Storage
  - 5 GB
  - Unlimited
* - Support
  - Community forums
  - Priority email + phone
* - API Access
  - 1,000 calls/month
  - Unlimited
:::

### List-Table Options

| Option | Description | Example |
|--------|-------------|---------|
| `:header-rows:` | Number of header rows (default: 0) | `:header-rows: 1` |
| `:widths:` | Column widths as percentages | `:widths: 30 70` |
| `:class:` | CSS class for styling | `:class: striped` |

### Rich Content in Cells

List-table cells support full Markdown, including code blocks:

```markdown
:::{list-table} API Endpoints
:header-rows: 1

* - Endpoint
  - Description
  - Response
* - `GET /users`
  - List all users.

    Returns paginated results with metadata.
  - ```json
    {"users": [...], "total": 100}
    ```
* - `POST /users`
  - Create a new user.

    Requires authentication.
  - ```json
    {"id": "abc123", "name": "Alice"}
    ```
:::
```

**Key syntax**:
- Start each row with `* -`
- Start each subsequent cell with `  -` (2-space indent)
- Blank line before multi-line content within a cell

## Data-Table Directive

For large datasets with interactive features:

```markdown
:::{data-table} data/products.yaml
:search: true
:filter: true
:sort: true
:pagination: 10
:columns: name,price,category
:::
```

### Data-Table Options

| Option | Description | Default |
|--------|-------------|---------|
| `:search:` | Enable text search | `false` |
| `:filter:` | Enable column filters | `false` |
| `:sort:` | Enable column sorting | `false` |
| `:pagination:` | Rows per page | `25` |
| `:columns:` | Columns to display (comma-separated) | All columns |
| `:height:` | Fixed table height | Auto |

### Data File Format

Data files can be YAML or CSV:

```yaml
# data/products.yaml
- name: Widget A
  price: 29.99
  category: Electronics
  stock: 150
- name: Widget B
  price: 49.99
  category: Electronics
  stock: 75
- name: Gadget C
  price: 19.99
  category: Accessories
  stock: 200
```

Or CSV format:

```csv
name,price,category,stock
Widget A,29.99,Electronics,150
Widget B,49.99,Electronics,75
Gadget C,19.99,Accessories,200
```

## Choosing the Right Format

| Scenario | Use This |
|----------|----------|
| Simple data, few columns | Pipe table |
| Code examples in cells | `list-table` |
| Multi-paragraph cells | `list-table` |
| Feature comparison | `list-table` with `:header-rows: 1` |
| API reference tables | `list-table` with code cells |
| Hardware/software matrices | `data-table` |
| Datasets with 50+ rows | `data-table` |
| User-searchable data | `data-table` with `:search: true` |

## Styling Tables

### CSS Classes

Add custom classes to list-tables:

```markdown
:::{list-table}
:class: striped hover compact

* - Row 1
  - Data
* - Row 2
  - Data
:::
```

Common classes: `striped`, `hover`, `compact`, `bordered`

### Responsive Behavior

Tables scroll horizontally on small screens. For wide tables:

- Split into multiple focused tables
- Move less critical columns to expandable sections
- Provide downloadable CSV for full data

## Troubleshooting

### Cells Not Aligning

**Problem**: Content appears in wrong columns.

**Fix**: Ensure consistent indentation. Each cell must start with exactly `  -` (2 spaces + hyphen):

```markdown
* - First cell
  - Second cell    ✅ Correct (2 spaces)
   - Third cell    ❌ Wrong (3 spaces)
```

### Code Blocks Breaking Table

**Problem**: Fenced code blocks inside pipe tables break rendering.

**Fix**: Use `list-table` for cells containing code blocks. Pipe tables don't support fenced code.

### Data-Table Not Loading

**Problem**: `data-table` shows error or empty.

**Fix**:
1. Verify the data file path is correct (relative to content root)
2. Check YAML/CSV syntax is valid
3. Ensure column names in `:columns:` match the data file

## Best Practices

:::{checklist}
- Use pipe tables for simple, scannable data
- Use list-table when cells need rich formatting
- Always include a header row for context
- Keep tables focused—one topic per table
- Consider mobile readers—avoid very wide tables
- Use `:widths:` to control column proportions
- Right-align numeric columns for easier scanning
:::

## See Also

- [[docs/reference/directives/formatting|Formatting Directives Reference]] — Complete directive options
- [[docs/content/authoring|Authoring Overview]] — Other content authoring features
