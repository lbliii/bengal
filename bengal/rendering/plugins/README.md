# Mistune Plugins for Bengal SSG

This package provides custom Mistune plugins for enhanced markdown processing in Bengal SSG.

## 📦 Package Structure

```
plugins/
├── __init__.py                    # Public API
├── variable_substitution.py       # {{ variable }} in markdown
├── cross_references.py            # [[link]] syntax
└── directives/
    ├── __init__.py               # Directive factory
    ├── admonitions.py            # Callout boxes
    ├── tabs.py                   # Tabbed content
    ├── dropdown.py               # Collapsible sections
    └── code_tabs.py              # Multi-language code examples
```

## 🎯 Architecture Principles

### Modular Design
- Each plugin is self-contained in its own file (~100-200 lines)
- Clear separation of concerns
- Easy to test, extend, and maintain

### Clean API
Only 3 main exports:
- `VariableSubstitutionPlugin` - Core plugin
- `CrossReferencePlugin` - Core plugin  
- `create_documentation_directives()` - Factory for all directives

### Backward Compatibility
The old `plugin_documentation_directives` function is still available for compatibility.

## 🚀 Usage

### Basic Usage

```python
from bengal.rendering.plugins import (
    VariableSubstitutionPlugin,
    CrossReferencePlugin,
    create_documentation_directives
)
import mistune

# Create markdown parser with all plugins
md = mistune.create_markdown(
    plugins=[
        'table',
        'strikethrough',
        create_documentation_directives(),
        VariableSubstitutionPlugin(context),
    ]
)

# Parse markdown
html = md(content)
```

### Individual Plugin Usage

```python
# Use only admonitions
from bengal.rendering.plugins.directives import AdmonitionDirective
from mistune.directives import FencedDirective

directive = FencedDirective([AdmonitionDirective()])
md = mistune.create_markdown(plugins=[directive])
```

## 📝 Plugin Documentation

### Core Plugins

#### VariableSubstitutionPlugin
- **File**: `variable_substitution.py`
- **Purpose**: Substitute `{{ page.metadata.xxx }}` in markdown content
- **Features**:
  - Code blocks stay literal (no escaping needed)
  - Single-pass parsing
  - Safe evaluation with error handling

#### CrossReferencePlugin
- **File**: `cross_references.py`
- **Purpose**: Resolve `[[docs/page]]` references to internal pages
- **Features**:
  - O(1) lookups using pre-built index
  - Multiple reference types (path, ID, heading)
  - Broken reference detection

### Documentation Directives

#### Admonitions
- **File**: `directives/admonitions.py`
- **Syntax**: ` ```{note} Title `
- **Types**: note, tip, warning, danger, error, info, example, success, caution
- **Features**: Full markdown support in content

#### Tabs
- **File**: `directives/tabs.py`
- **Syntax**: ` ```{tabs} ` with `### Tab: Title` markers
- **Features**: Nested markdown, multiple tabs, custom IDs

#### Dropdown
- **File**: `directives/dropdown.py`
- **Syntax**: ` ```{dropdown} Title `
- **Features**: Collapsible sections, open/closed state, nested content

#### Code Tabs
- **File**: `directives/code_tabs.py`
- **Syntax**: ` ```{code-tabs} ` with language markers
- **Features**: Multi-language code examples with syntax highlighting

## 🧪 Testing

Each plugin should have corresponding unit tests:

```bash
tests/unit/rendering/plugins/
├── test_variable_substitution.py
├── test_cross_references.py
└── directives/
    ├── test_admonitions.py
    ├── test_tabs.py
    ├── test_dropdown.py
    └── test_code_tabs.py
```

Run tests:
```bash
pytest tests/unit/rendering/plugins/ -v
```

## 🔧 Contributing

### Adding a New Plugin

1. **Create plugin file** in appropriate location:
   - Core plugins: `plugins/my_plugin.py`
   - Directives: `plugins/directives/my_directive.py`

2. **Implement plugin class**:
   ```python
   class MyPlugin:
       def __init__(self, options):
           self.options = options

       def __call__(self, md):
           # Register with mistune
           pass
   ```

3. **Export from `__init__.py`** (if public):
   ```python
   from bengal.rendering.plugins.my_plugin import MyPlugin
   __all__ = [..., 'MyPlugin']
   ```

4. **Write tests**:
   ```python
   def test_my_plugin():
       plugin = MyPlugin(options)
       # Test implementation
   ```

5. **Update documentation**:
   - Add to this README
   - Update ARCHITECTURE.md if needed

### Code Style

- Follow PEP 8
- Keep files under 200 lines when possible
- Use type hints
- Write comprehensive docstrings
- Add examples in docstrings

## 📊 Migration Notes

### From Old Structure (v0.1.x)

The old `mistune_plugins.py` file (757 lines) has been split into this modular package.

**Old imports:**
```python
from bengal.rendering.mistune_plugins import (
    VariableSubstitutionPlugin,
    plugin_documentation_directives
)
```

**New imports (preferred):**
```python
from bengal.rendering.plugins import (
    VariableSubstitutionPlugin,
    create_documentation_directives
)
```

**Both work!** The old function name is aliased for compatibility.

### Benefits of New Structure

1. **Maintainability**: Each plugin in ~100-200 line file
2. **Testability**: Test plugins independently
3. **Extensibility**: Add new plugins without touching existing code
4. **Documentation**: Each plugin documented in its own file
5. **Code Review**: Review single focused files

## 🔗 Related Documentation

- `bengal/rendering/parser.py` - How plugins are used
- `tests/unit/rendering/plugins/` - Plugin tests
- `ARCHITECTURE.md` - Overall system architecture

## ✨ Version History

- **v1.0.0** (Oct 2025): Modular plugin package created from monolithic file
- **v0.1.x** (Sep 2025): Original `mistune_plugins.py` implementation
