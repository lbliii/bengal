---
title: "Data Tables"
description: "Interactive tables with filtering, sorting, and searching for complex data"
weight: 70
toc: true
---

# Data Tables

Bengal provides powerful data table components for displaying complex tabular data with interactive features like filtering, sorting, and searching. Perfect for hardware/software support matrices, API references, and any data that's too complex for basic markdown tables.

## Quick Start

### Basic Usage

The simplest way to use data tables is with the directive syntax:

````markdown
```{data-table} data/browser-support.yaml
```
````

This loads data from a YAML or CSV file and renders an interactive table.

## Supported Formats

### YAML Format

YAML files allow you to define both column metadata and data:

```yaml
# data/browser-support.yaml
columns:
  - title: Feature
    field: feature
  - title: Chrome
    field: chrome
  - title: Firefox
    field: firefox

data:
  - feature: CSS Grid
    chrome: "✓ v57+"
    firefox: "✓ v52+"
  - feature: Web Components
    chrome: "✓ v67+"
    firefox: "✓ v63+"
```

### CSV Format

CSV files are auto-parsed with header detection:

```csv
Feature,Chrome,Firefox,Safari
CSS Grid,✓ v57+,✓ v52+,✓ v10.1+
Web Components,✓ v67+,✓ v63+,✓ v13+
```

## Options

### Search

Enable or disable the search box (default: `true`):

````markdown
```{data-table} data/specs.yaml
:search: false
```
````

### Filtering

Enable column filters in headers (default: `true`):

````markdown
```{data-table} data/specs.yaml
:filter: true
```
````

### Sorting

Enable column sorting (default: `true`):

````markdown
```{data-table} data/specs.yaml
:sort: true
```
````

### Pagination

Set rows per page, or disable with `false` (default: `50`):

````markdown
```{data-table} data/specs.yaml
:pagination: 100
```
````

````markdown
```{data-table} data/specs.yaml
:pagination: false
```
````

### Height

Set table height (default: `auto`):

````markdown
```{data-table} data/specs.yaml
:height: 400px
```
````

### Visible Columns

Show only specific columns:

````markdown
```{data-table} data/specs.yaml
:columns: Feature,Chrome,Firefox
```
````

## Examples

### Browser Support Matrix

```{data-table} data/browser-support.yaml
:search: true
:filter: true
:pagination: 0
:height: 500px
```

This table shows browser compatibility for modern web features. Try:
- **Searching**: Type "CSS" to filter features
- **Sorting**: Click column headers to sort
- **Filtering**: Use the input boxes under headers

### Hardware Specifications

```{data-table} data/hardware-specs.csv
:search: true
:pagination: 5
:height: 400px
```

This CSV-based table shows laptop specifications. Try:
- **Search for "MacBook"** to see only Apple products
- **Sort by Price** by clicking the Price column
- **Page through results** using pagination controls

### Minimal Table

````markdown
```{data-table} data/simple.csv
:search: false
:filter: false
:pagination: false
```
````

For simple data, you can disable all interactive features.

## Template Function

You can also use data tables directly in templates:

```jinja2
{# Basic usage #}
{{ data_table('data/browser-support.yaml') }}

{# With options #}
{{ data_table('data/hardware-specs.csv',
              pagination=100,
              height='500px',
              search=True) }}

{# Show specific columns only #}
{{ data_table('data/support-matrix.yaml',
              columns='Feature,Chrome,Firefox') }}
```

This is useful for:
- Creating dedicated table pages
- Building custom partials
- Programmatic table generation

## Features

### Responsive Design

Tables automatically adapt to mobile devices:
- Column collapsing on small screens
- Touch-friendly controls
- Horizontal scrolling when needed

### Keyboard Navigation

Full keyboard support:
- **Tab**: Navigate cells
- **Arrow keys**: Move within table
- **Escape**: Clear search (when focused)
- **Enter**: Sort column (on headers)

### Dark Mode

Tables automatically adapt to Bengal's theme:
- Light and dark theme support
- Consistent color tokens
- Accessible contrast ratios

### Accessibility

Built with accessibility in mind:
- ARIA labels and roles
- Screen reader friendly
- Keyboard navigation
- Focus indicators
- High contrast support

## Performance

### Client-Side Rendering

Tables are rendered client-side with Tabulator.js:
- Fast initial load (JavaScript deferred)
- No backend required
- Smooth interactions
- Virtual scrolling for large datasets

### File Size Limits

- Maximum file size: **5MB**
- Recommended rows: **< 1000** for best performance
- For larger datasets, consider pagination

### Optimization Tips

1. **Use pagination** for tables with > 100 rows
2. **Limit visible columns** if you have many fields
3. **Disable features** you don't need (search, filter, sort)
4. **Use CSV** for simple data (smaller file size)
5. **Use YAML** for complex data with metadata

## Best Practices

### When to Use Data Tables

✅ **Good use cases:**
- Hardware/software compatibility matrices
- API endpoint references
- Version comparison tables
- Pricing/feature comparisons
- Large datasets (50+ rows)
- Data requiring filtering/sorting

❌ **Avoid for:**
- Simple 2-3 column tables (use markdown)
- Small tables (< 10 rows)
- Static data that doesn't need interactivity
- Tables with lots of formatting/custom HTML

### File Organization

```
my-site/
├── content/
│   └── docs/
│       └── support-matrix.md
└── data/                    # ← Data files here
    ├── browser-support.yaml
    ├── hardware-specs.csv
    └── api-endpoints.yaml
```

Keep data files in a `data/` directory at project root, separate from content.

### Data Maintenance

1. **Use spreadsheets** - Maintain data in Excel/Google Sheets, export to CSV
2. **Version control** - Commit CSV/YAML files to git
3. **Validate data** - Test tables after updates
4. **Document structure** - Add comments in YAML files

### Column Design

- **Keep columns to < 10** for readability
- **Use short header names** to save space
- **Use emoji/symbols** for visual cues (✓, ⚠️, ❌)
- **Consistent formatting** within columns

## Troubleshooting

### Table Not Showing

1. Check file path is correct
2. Verify file format (YAML/CSV)
3. Check browser console for errors
4. Ensure data file is < 5MB

### Search Not Working

The search box searches across **all columns**. Make sure:
- Data contains the search term
- Search is enabled (`:search: true`)

### Styling Issues

Tables use Bengal's design tokens. To customize:

```css
/* In your custom CSS */
.bengal-data-table {
  font-size: 0.9rem;
}

.bengal-data-table-search {
  background: var(--color-primary);
}
```

## Advanced Features (Future)

The data table component will continue to evolve. Planned features:

- **Column configuration** - Width, alignment, custom formatters
- **Export** - Download as CSV, Excel, PDF
- **Custom cell renderers** - Badges, icons, links
- **Row grouping** - Hierarchical data
- **Inline editing** - Edit cells directly
- **Advanced filters** - Date ranges, multi-select

## Technical Details

### Library

Tables use [Tabulator.js](https://tabulator.info/):
- ~60KB minified
- Zero dependencies
- Modern, actively maintained
- Excellent documentation

### Browser Support

- Chrome/Edge: v90+
- Firefox: v88+
- Safari: v14+
- Mobile browsers: Full support

### Loading Strategy

Assets are conditionally loaded:
- CSS in `<head>` only if page has tables
- JavaScript deferred until page load
- No impact on pages without tables

## See Also

- [Directives](/docs/directives/) - Other directive components
- [Template Functions](/docs/templates/function-reference/) - All template functions
- [Writing Guide](/docs/writing/) - Content best practices
