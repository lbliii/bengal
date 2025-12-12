---
title: Tables
nav_title: Tables
description: Create simple and complex tables in your content
weight: 50
category: how-to
icon: table
---
# Tables

How to create tables in your documentation.

## Simple Tables (Pipe Syntax)

The standard Markdown pipe table works for simple data:

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
| Text | Text   | Text  |
| More | More   | More  |
```

| Left | Center | Right |
|:-----|:------:|------:|
| Text | Text   | Text  |
| More | More   | More  |

## Complex Tables (List-Table)

For tables with multi-line cells, nested content, or complex formatting, use the `list-table` directive:

```markdown
:::{list-table} Table Caption
:header-rows: 1
:widths: 20 40 40

* - Feature
  - Free Plan
  - Pro Plan
* - Storage
  - 5 GB
  - Unlimited
* - Support
  - Community
  - Priority email + phone
* - API Access
  - 1,000 calls/month
  - Unlimited
:::
```

### List-Table Options

| Option | Description | Example |
|--------|-------------|---------|
| `:header-rows:` | Number of header rows | `:header-rows: 1` |
| `:stub-columns:` | Number of stub columns | `:stub-columns: 1` |
| `:widths:` | Column widths (space-separated) | `:widths: 30 70` |
| `:class:` | CSS class | `:class: comparison-table` |
| `:align:` | Table alignment | `:align: center` |

### Multi-Line Cells

List-table supports rich content in cells:

```markdown
:::{list-table} API Endpoints
:header-rows: 1

* - Endpoint
  - Description
  - Example
* - `GET /users`
  - List all users.

    Returns paginated results.
  - ```json
    {"users": [...]}
    ```
* - `POST /users`
  - Create a new user.

    Requires authentication.
  - ```json
    {"name": "Alice"}
    ```
:::
```

## Interactive Tables (Data-Table)

For large datasets with sorting, filtering, and pagination:

```markdown
:::{data-table}
:source: data/products.yaml
:columns: name, price, category, stock
:sortable: true
:filterable: true
:page-size: 10
:::
```

### Data-Table Options

| Option | Description | Default |
|--------|-------------|---------|
| `:source:` | Path to YAML/JSON data file | Required |
| `:columns:` | Columns to display | All |
| `:sortable:` | Enable column sorting | `false` |
| `:filterable:` | Enable search/filter | `false` |
| `:page-size:` | Rows per page | `25` |

### Data File Format

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
```

## When to Use Each

| Use Case | Recommended |
|----------|-------------|
| Simple data (3-5 columns, single-line cells) | Pipe tables |
| Complex cells (code, lists, multi-line) | `list-table` |
| Large datasets (50+ rows) | `data-table` |
| Comparison tables | `list-table` with `:header-rows:` |
| API reference | `list-table` with code cells |

## Styling Tables

### Add CSS Classes

```markdown
:::{list-table}
:class: striped hover

* - Row 1
  - Data
* - Row 2
  - Data
:::
```

### Responsive Tables

Tables automatically scroll horizontally on small screens. For very wide tables, consider:

- Breaking into multiple smaller tables
- Using collapsible sections for less critical columns
- Providing a downloadable CSV

## Best Practices

:::{checklist}
- Use pipe tables for simple, scannable data
- Use list-table when cells need rich formatting
- Always include a header row for context
- Keep tables focused—don't cram everything into one
- Consider mobile readers—very wide tables are hard to read
- Use `:widths:` to control column proportions
:::

::::{seealso}
- [[docs/reference/directives/formatting|Formatting Directives Reference]] — Complete `list-table` options
- [[docs/content/authoring|Authoring Overview]] — Other authoring features
::::
