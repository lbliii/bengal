# MyST Tabs Implementation Summary

**Date**: 2025-10-10  
**Status**: ✅ Complete (13/13 tests passing, 99% coverage)

## Overview

Migrated Bengal's tab system from a custom syntax to the standard MyST Markdown `{tab-set}` and `{tab-item}` pattern while maintaining full backward compatibility with the legacy syntax.

## What Changed

### Old Syntax (Still Supported)
```markdown
````{tabs}
### Tab: Python
Python content
### Tab: JavaScript
JavaScript content
````
```

**Issues:**
- Uses markdown headers (`###`) which is confusing
- Not consistent with other directives
- Harder to nest other directives
- Not standard MyST Markdown

### New Syntax (Preferred)
```markdown
:::{tab-set}
:sync: language  # Optional: sync tabs

:::{tab-item} Python
:selected:  # Optional: mark as initially selected

Python content with **markdown** support
:::

:::{tab-item} JavaScript
JavaScript content
:::
::::
```

**Benefits:**
- ✅ Standard MyST Markdown syntax
- ✅ Each tab is its own directive (cleaner nesting)
- ✅ Consistent with `{cards}`, `{card}` pattern
- ✅ Easy to scan when reading markdown
- ✅ Better tooling support (syntax highlighters understand it)
- ✅ Optional `:sync:` for synchronized tabs across sets
- ✅ Optional `:selected:` to control initial tab

## Implementation Details

### Files Created

1. **`bengal/rendering/plugins/directives/tabs.py`** (updated, 301 lines)
   - `TabSetDirective` - Modern MyST tab container
   - `TabItemDirective` - Individual tab within set
   - `TabsDirective` - Legacy syntax (backward compat)
   - `render_tab_set()` - HTML renderer for tab sets
   - `render_tab_item()` - HTML renderer for tab items

2. **`tests/unit/rendering/test_myst_tabs.py`** (new, 255 lines)
   - 7 tests for modern MyST syntax
   - 2 tests for legacy syntax
   - 3 tests for edge cases
   - 1 test comparing both syntaxes

### Files Modified

1. **`bengal/rendering/plugins/directives/__init__.py`**
   - Registered `TabSetDirective` and `TabItemDirective`
   - Kept `TabsDirective` for backward compatibility

## Architecture

### Modern MyST Pattern

```python
class TabSetDirective(DirectivePlugin):
    """Container for tab items."""
    def parse(self, block, m, state):
        # Parse nested tab-item directives
        content = self.parse_content(m)
        children = self.parse_tokens(block, content, state)
        return {'type': 'tab_set', 'attrs': {...}, 'children': children}

class TabItemDirective(DirectivePlugin):
    """Individual tab within tab-set."""
    def parse(self, block, m, state):
        title = self.parse_title(m)  # Tab title from directive line
        content = self.parse_content(m)
        children = self.parse_tokens(block, content, state)
        return {'type': 'tab_item', 'attrs': {'title': title, ...}, 'children': children}
```

### Rendering Strategy

1. **TabItemDirective** renders each tab as:
   ```html
   <div class="tab-item" data-title="..." data-selected="...">
     [rendered content]
   </div>
   ```

2. **TabSetDirective** parses these wrapper divs and builds:
   ```html
   <div class="tabs" data-sync="...">
     <ul class="tab-nav">
       <li><a href="#" data-tab-target="...">Title</a></li>
       ...
     </ul>
     <div class="tab-content">
       <div id="..." class="tab-pane active">[content]</div>
       ...
     </div>
   </div>
   ```

This two-pass approach allows proper nesting and markdown rendering within tabs.

## Features

### Basic Tabs
```markdown
:::{tab-set}
:::{tab-item} Tab 1
Content 1
:::
:::{tab-item} Tab 2
Content 2
:::
::::
```

### Synchronized Tabs
```markdown
First set:
:::{tab-set}
:sync: os
:::{tab-item} Linux
Linux instructions
:::
:::{tab-item} Windows  
Windows instructions
:::
::::

Second set (automatically syncs):
:::{tab-set}
:sync: os
:::{tab-item} Linux
More Linux info
:::
:::{tab-item} Windows
More Windows info
:::
::::
```

### Initially Selected Tab
```markdown
:::{tab-set}
:::{tab-item} First
Default behavior - first tab selected
:::
:::{tab-item} Second
:selected:
This tab will be selected on page load
:::
::::
```

### Nested Directives
```markdown
:::{tab-set}
:::{tab-item} Example

```{note}
Tabs can contain any markdown or directives!
```

- Lists work
- **Bold works**
- Everything works!

:::
::::
```

### Multiple Tab Sets
```markdown
:::{tab-set}
:::{tab-item} A
:::
::::

Some text between...

:::{tab-set}
:::{tab-item} B
:::
::::
```

Each tab-set is independent with its own ID and state.

## Test Coverage

**13/13 tests passing (100%)** ✅  
**99% code coverage** on `tabs.py`

### Test Categories:

1. **Modern MyST Syntax (7 tests)**
   - Basic tab-set
   - Markdown in tabs
   - Code blocks in tabs
   - Selected option
   - Sync option
   - Nested directives
   - Multiple tab sets

2. **Legacy Syntax (2 tests)**
   - Old `### Tab:` syntax
   - Markdown in legacy tabs

3. **Edge Cases (3 tests)**
   - Empty tab-set
   - Single tab
   - Tab without title

4. **Comparison (1 test)**
   - Both syntaxes produce similar output

## Migration Path

Users can:

1. **Keep old syntax** - Legacy `{tabs}` with `### Tab:` markers still works
2. **Gradually migrate** - Mix old and new syntax in same docs
3. **Adopt new syntax** - Use `{tab-set}`/`{tab-item}` for new content

### Migration Example:

```markdown
# Before (Legacy - Still Works)
````{tabs}
### Tab: Python
Code here
### Tab: JavaScript
Code here
````

# After (Modern MyST - Preferred)
:::{tab-set}
:::{tab-item} Python
Code here
:::
:::{tab-item} JavaScript
Code here
:::
::::
```

## Compatibility

- ✅ **Backward compatible** - Old syntax still works
- ✅ **Forward compatible** - MyST syntax matches standard
- ✅ **CSS unchanged** - Same HTML structure, same styling
- ✅ **JavaScript unchanged** - Tab switching logic unchanged

## Benefits for Users

### 1. **Easier to Read**
When scanning markdown files, the new syntax is clearer:
```markdown
:::{tab-item} Clear Title Here
```
vs
```markdown
### Tab: Confusing Because It Looks Like Heading
```

### 2. **Better Nesting**
Each tab is its own directive, so nesting is clean:
```markdown
:::{tab-set}
  :::{tab-item} One
    :::{note}
    Nested!
    :::
  :::
::::
```

### 3. **Standard Syntax**
MyST Markdown is the standard for Sphinx and many Python tools. Using standard syntax means:
- Better editor support
- Better syntax highlighting
- Easier to find documentation
- Familiar to users migrating from Sphinx

### 4. **More Features**
- Tab synchronization with `:sync:`
- Explicit initial selection with `:selected:`
- Cleaner to add more options in the future

## Performance

- **Zero impact** - Same HTML output, same rendering speed
- **Efficient parsing** - Nested directives parsed in one pass
- **No breaking changes** - Old syntax uses same renderer

## Summary

Successfully migrated Bengal's tab system to MyST Markdown standard syntax while maintaining full backward compatibility. The new syntax is cleaner, more standard, and easier to use.

**Status**: ✅ Production-ready  
**Tests**: 13/13 passing  
**Coverage**: 99%  
**Breaking Changes**: None

