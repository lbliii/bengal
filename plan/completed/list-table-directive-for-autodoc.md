# List-Table Directive for Autodoc

## Problem

Autodoc templates were using markdown pipe tables for parameters and attributes. This caused issues:
1. Pipe characters (`|`) in type annotations like `str | None` broke table structure
2. Tables appeared as bullet lists instead of proper tables
3. Inconsistent formatting between parameter and attribute sections

## Solution

### Created MyST List-Table Directive

**File**: `bengal/rendering/plugins/directives/list_table.py`

- Implemented MyST-compatible `list-table` directive
- Parses list syntax: `* -` for rows, `  -` for cells
- Supports:
  - `:header-rows:` - number of header rows
  - `:widths:` - column width percentages
  - `:class:` - custom CSS classes
- Renders cells as HTML with inline markdown parsing (backticks → `<code>` tags)
- Handles pipe characters in content without breaking table structure

### Updated Autodoc Template

**File**: `bengal/autodoc/templates/python/module.md.jinja2`

1. Created `render_attributes()` macro matching `render_parameters()` style
2. Both use dropdown tables with list-table directive
3. Fixed Jinja2 whitespace control:
   - Added explicit blank lines between rows
   - Removed `-` from `{% endif %}` to preserve newlines between cells
   - Kept backticks around types and defaults

### Registered Directive

**File**: `bengal/rendering/plugins/directives/__init__.py`

- Added `ListTableDirective` to the directive plugin list
- Updated docstring to document list-table support

### Added Tests

**File**: `tests/unit/rendering/test_list_table.py`

Comprehensive test coverage (6 tests, all passing):
- Basic table rendering
- Column widths
- Pipe characters in content (`str | None`)
- Markdown in cells (backticks, bold, italic)
- No header rows
- Custom CSS classes

## Results

✅ **All 6 tests passing**

**Before**:
```
- **`file_hashes`** (`dict[str, str]`) - Mapping of file paths...
- **`dependencies`** (`dict[str, set[str]]`) - Mapping of pages...
```

**After**:
```html
<table class="bengal-list-table">
  <thead>
    <tr>
      <th>Name</th>
      <th>Type</th>
      <th>Description</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td><code>file_hashes</code></td>
      <td><code>dict[str, str]</code></td>
      <td>Mapping of file paths to their SHA256 hashes</td>
    </tr>
    ...
  </tbody>
</table>
```

## Benefits

1. **Proper table rendering** - Clean, structured tables with proper columns
2. **Type annotations work** - `str | None` renders correctly
3. **Backticks render as code** - `<code>` tags for inline code
4. **Consistent style** - Attributes and parameters use same format
5. **Collapsible dropdowns** - Keeps documentation clean and organized
6. **No pipe character issues** - List syntax avoids markdown pipe delimiter conflicts

## Files Modified

- `bengal/rendering/plugins/directives/list_table.py` (new)
- `bengal/rendering/plugins/directives/__init__.py`
- `bengal/autodoc/templates/python/module.md.jinja2`
- `tests/unit/rendering/test_list_table.py` (new)

## No Breaking Changes

- Existing rendering tests remain passing
- No changes to existing directives or parsers
- Additive feature only

## Usage

When regenerating autodoc documentation:
```bash
bengal autodoc --clean
```

The new list-table directive will automatically be used for parameter and attribute tables, providing clean, pipe-safe table rendering with proper markdown support.
