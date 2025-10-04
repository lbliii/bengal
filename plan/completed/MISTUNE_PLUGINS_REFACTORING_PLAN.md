# Mistune Plugins Refactoring Plan

**Date:** October 4, 2025  
**Status:** 📋 Proposal  
**Complexity:** Medium  
**Estimated Time:** 2-3 hours  
**Risk Level:** Low (well-isolated module)

---

## 🎯 Executive Summary

Refactor the 757-line `mistune_plugins.py` monolith into a well-organized plugin package with clear separation of concerns, improved maintainability, and better testability.

**Current State:**
- ✅ Functionally excellent (works well, no bugs)
- ⚠️ Single 757-line file with 6 distinct plugins
- ⚠️ Mixed concerns (variable substitution, directives, cross-references)
- ⚠️ Hard to navigate and maintain

**Target State:**
- ✅ Modular plugin package with focused modules
- ✅ Each plugin in its own file (~100-200 lines)
- ✅ Clear public API via `__init__.py`
- ✅ Easier to test, extend, and document
- ✅ Zero behavioral changes (100% backward compatible)

---

## 📊 Current Structure Analysis

### File Breakdown

```
mistune_plugins.py (757 lines)
├── VariableSubstitutionPlugin      [22-171]   ~150 lines  ⭐ Core feature
├── AdmonitionDirective             [177-250]   ~74 lines  📦 Directive
├── TabsDirective                   [257-386]  ~130 lines  📦 Directive
├── DropdownDirective               [388-444]   ~57 lines  📦 Directive
├── CodeTabsDirective               [447-554]  ~108 lines  📦 Directive
├── CrossReferencePlugin            [561-712]  ~152 lines  ⭐ Core feature
└── plugin_documentation_directives [719-757]   ~39 lines  🏭 Factory
```

### Dependency Analysis

**External Dependencies:**
- `mistune.directives.DirectivePlugin` - All directive classes inherit
- `mistune.directives.FencedDirective` - Used in factory function
- No internal cross-plugin dependencies ✅

**Import Locations:**
```python
# Only imported in one place:
bengal/rendering/parser.py:
    from bengal.rendering.mistune_plugins import (
        VariableSubstitutionPlugin,
        plugin_documentation_directives
    )
```

**Key Insight:** Clean API surface! Only 2 exports are actually used.

---

## 🏗️ Proposed Architecture

### New Package Structure

```
bengal/rendering/plugins/
├── __init__.py                    # Public API (clean exports)
├── variable_substitution.py       # VariableSubstitutionPlugin
├── cross_references.py            # CrossReferencePlugin
├── directives/
│   ├── __init__.py               # Directive factory
│   ├── admonitions.py            # AdmonitionDirective + renderer
│   ├── tabs.py                   # TabsDirective + renderers
│   ├── dropdown.py               # DropdownDirective + renderer
│   └── code_tabs.py              # CodeTabsDirective + renderers
└── README.md                      # Plugin architecture docs
```

### File Sizes (Estimated)

| File | Lines | Complexity | Purpose |
|------|-------|------------|---------|
| `__init__.py` | ~40 | Simple | Public API, exports |
| `variable_substitution.py` | ~160 | Medium | Variable plugin + docs |
| `cross_references.py` | ~160 | Medium | Xref plugin + docs |
| `directives/__init__.py` | ~50 | Simple | Factory function |
| `directives/admonitions.py` | ~90 | Low | Admonition directive |
| `directives/tabs.py` | ~145 | Medium | Tabs directive |
| `directives/dropdown.py` | ~70 | Low | Dropdown directive |
| `directives/code_tabs.py` | ~120 | Medium | Code tabs directive |
| `README.md` | ~100 | N/A | Documentation |

**Total:** ~935 lines (178 more, but much better organized)

---

## 📝 Detailed Implementation Plan

### Phase 1: Setup Package Structure (15 min)

**Goal:** Create directory structure and skeleton files

```bash
# 1. Create package directories
mkdir -p bengal/rendering/plugins/directives

# 2. Create __init__.py files
touch bengal/rendering/plugins/__init__.py
touch bengal/rendering/plugins/directives/__init__.py

# 3. Create plugin files
touch bengal/rendering/plugins/variable_substitution.py
touch bengal/rendering/plugins/cross_references.py
touch bengal/rendering/plugins/directives/admonitions.py
touch bengal/rendering/plugins/directives/tabs.py
touch bengal/rendering/plugins/directives/dropdown.py
touch bengal/rendering/plugins/directives/code_tabs.py
touch bengal/rendering/plugins/README.md
```

**Verification:**
```bash
tree bengal/rendering/plugins/
```

---

### Phase 2: Extract Core Plugins (45 min)

#### 2.1: Variable Substitution Plugin

**File:** `bengal/rendering/plugins/variable_substitution.py`

```python
"""
Variable substitution plugin for Mistune.

Provides safe {{ variable }} replacement in markdown content while keeping
code blocks literal and maintaining clear separation from template logic.
"""

import re
from typing import Any, Dict, Match

__all__ = ['VariableSubstitutionPlugin']


class VariableSubstitutionPlugin:
    """
    Mistune plugin for safe variable substitution in markdown content.
    
    ARCHITECTURE: Separation of Concerns
    =====================================
    
    This plugin handles ONLY variable substitution ({{ vars }}) in markdown.
    It operates at the AST level after Mistune parses the markdown structure.
    
    WHAT THIS HANDLES:
    ------------------
    ✅ {{ page.metadata.xxx }} - Access page frontmatter
    ✅ {{ site.config.xxx }} - Access site configuration
    ✅ {{ page.title }}, {{ page.date }}, etc. - Page properties
    
    WHAT THIS DOESN'T HANDLE:
    --------------------------
    ❌ {% if condition %} - Conditional blocks
    ❌ {% for item %} - Loop constructs
    ❌ Complex Jinja2 logic
    
    WHY: Conditionals and loops belong in TEMPLATES, not markdown.
    
    ... [rest of docstring from original]
    """
    
    VARIABLE_PATTERN = re.compile(r'\{\{\s*([^}]+)\s*\}\}')
    
    def __init__(self, context: Dict[str, Any]):
        # ... [implementation from original]
        pass
    
    def update_context(self, context: Dict[str, Any]) -> None:
        # ... [implementation from original]
        pass
    
    def __call__(self, md):
        # ... [implementation from original]
        pass
    
    def _substitute_variables(self, text: str) -> str:
        # ... [implementation from original]
        pass
    
    def _eval_expression(self, expr: str) -> Any:
        # ... [implementation from original]
        pass
```

**Test File:** `tests/unit/rendering/plugins/test_variable_substitution.py`

#### 2.2: Cross-Reference Plugin

**File:** `bengal/rendering/plugins/cross_references.py`

```python
"""
Cross-reference plugin for Mistune.

Provides [[link]] syntax for internal page references with O(1) lookup
performance using pre-built xref_index.
"""

import re
from typing import Any, Dict, Match, Optional

__all__ = ['CrossReferencePlugin']


class CrossReferencePlugin:
    """
    Mistune plugin for inline cross-references with [[link]] syntax.
    
    Syntax:
        [[docs/installation]]           -> Link with page title
        [[docs/installation|Install]]   -> Link with custom text
        [[#heading-name]]               -> Link to heading anchor
        [[id:my-page]]                  -> Link by custom ID
        [[id:my-page|Custom]]          -> Link by ID with custom text
    
    ... [rest of docstring from original]
    """
    
    def __init__(self, xref_index: Dict[str, Any]):
        # ... [implementation from original]
        pass
    
    def __call__(self, md):
        # ... [implementation from original]
        pass
    
    def _substitute_xrefs(self, text: str) -> str:
        # ... [implementation from original]
        pass
    
    def _resolve_path(self, path: str, text: Optional[str] = None) -> str:
        # ... [implementation from original]
        pass
    
    def _resolve_id(self, ref_id: str, text: Optional[str] = None) -> str:
        # ... [implementation from original]
        pass
    
    def _resolve_heading(self, anchor: str, text: Optional[str] = None) -> str:
        # ... [implementation from original]
        pass
```

**Test File:** `tests/unit/rendering/plugins/test_cross_references.py`

---

### Phase 3: Extract Directives (60 min)

#### 3.1: Admonitions Directive

**File:** `bengal/rendering/plugins/directives/admonitions.py`

```python
"""
Admonition directive for Mistune.

Provides note, warning, tip, danger, and other callout boxes.
"""

from mistune.directives import DirectivePlugin

__all__ = ['AdmonitionDirective', 'render_admonition']


class AdmonitionDirective(DirectivePlugin):
    """
    Admonition directive using Mistune's fenced syntax.
    
    Syntax:
        ```{note} Optional Title
        Content with **markdown** support.
        ```
    
    Supported types: note, tip, warning, danger, error, info, example, success
    """
    
    ADMONITION_TYPES = [
        'note', 'tip', 'warning', 'danger', 'error', 
        'info', 'example', 'success', 'caution'
    ]
    
    def parse(self, block, m, state):
        # ... [implementation from original]
        pass
    
    def __call__(self, directive, md):
        # ... [implementation from original]
        pass


def render_admonition(renderer, text: str, admon_type: str, title: str) -> str:
    """Render admonition to HTML."""
    # ... [implementation from original]
    pass
```

#### 3.2: Tabs Directive

**File:** `bengal/rendering/plugins/directives/tabs.py`

```python
"""
Tabs directive for Mistune.

Provides tabbed content with full markdown support.
"""

from mistune.directives import DirectivePlugin

__all__ = [
    'TabsDirective',
    'render_tabs',
    'render_tab_title',
    'render_tab_content'
]


class TabsDirective(DirectivePlugin):
    """
    Tabbed content directive with full markdown support.
    
    ... [docstring from original]
    """
    
    def parse(self, block, m, state):
        # ... [implementation from original]
        pass
    
    def __call__(self, directive, md):
        # ... [implementation from original]
        pass


def render_tabs(renderer, text, **attrs):
    # ... [implementation from original]
    pass


def render_tab_title(renderer, text):
    # ... [implementation from original]
    pass


def render_tab_content(renderer, text):
    # ... [implementation from original]
    pass
```

#### 3.3: Dropdown Directive

**File:** `bengal/rendering/plugins/directives/dropdown.py`

```python
"""
Dropdown directive for Mistune.

Provides collapsible sections with markdown support.
"""

from mistune.directives import DirectivePlugin

__all__ = ['DropdownDirective', 'render_dropdown']


class DropdownDirective(DirectivePlugin):
    """
    Collapsible dropdown directive with markdown support.
    
    ... [docstring from original]
    """
    
    def parse(self, block, m, state):
        # ... [implementation from original]
        pass
    
    def __call__(self, directive, md):
        # ... [implementation from original]
        pass


def render_dropdown(renderer, text, **attrs):
    # ... [implementation from original]
    pass
```

#### 3.4: Code Tabs Directive

**File:** `bengal/rendering/plugins/directives/code_tabs.py`

```python
"""
Code tabs directive for Mistune.

Provides multi-language code examples with tabbed interface.
"""

from mistune.directives import DirectivePlugin

__all__ = [
    'CodeTabsDirective',
    'render_code_tabs',
    'render_code_tab_item'
]


class CodeTabsDirective(DirectivePlugin):
    """
    Code tabs for multi-language examples.
    
    ... [docstring from original]
    """
    
    def parse(self, block, m, state):
        # ... [implementation from original]
        pass
    
    def __call__(self, directive, md):
        # ... [implementation from original]
        pass


def render_code_tabs(renderer, text, **attrs):
    # ... [implementation from original]
    pass


def render_code_tab_item(renderer, **attrs):
    # ... [implementation from original]
    pass
```

---

### Phase 4: Create Factory & Public API (30 min)

#### 4.1: Directives Factory

**File:** `bengal/rendering/plugins/directives/__init__.py`

```python
"""
Mistune directives package.

Provides all documentation directives (admonitions, tabs, dropdown, code-tabs)
as a single factory function for easy registration.
"""

from bengal.rendering.plugins.directives.admonitions import AdmonitionDirective
from bengal.rendering.plugins.directives.tabs import TabsDirective
from bengal.rendering.plugins.directives.dropdown import DropdownDirective
from bengal.rendering.plugins.directives.code_tabs import CodeTabsDirective

__all__ = ['create_documentation_directives']


def create_documentation_directives():
    """
    Create documentation directives plugin for Mistune.
    
    Returns a function that can be passed to mistune.create_markdown(plugins=[...]).
    
    Provides:
    - admonitions: note, tip, warning, danger, error, info, example, success
    - tabs: Tabbed content with full markdown support
    - dropdown: Collapsible sections with markdown
    - code-tabs: Code examples in multiple languages
    
    Usage:
        from bengal.rendering.plugins.directives import create_documentation_directives
        
        md = mistune.create_markdown(
            plugins=[create_documentation_directives()]
        )
    
    Raises:
        RuntimeError: If directive registration fails
        ImportError: If FencedDirective is not available
    """
    def plugin_documentation_directives(md):
        """Register all documentation directives with Mistune."""
        try:
            from mistune.directives import FencedDirective
        except ImportError as e:
            import sys
            print(f"Error: FencedDirective not available in mistune: {e}", file=sys.stderr)
            raise ImportError(
                "FencedDirective not found. Ensure mistune>=3.0.0 is installed."
            ) from e
        
        try:
            # Create fenced directive with all our custom directives
            directive = FencedDirective([
                AdmonitionDirective(),  # Supports note, tip, warning, etc.
                TabsDirective(),
                DropdownDirective(),
                CodeTabsDirective(),
            ])
            
            # Apply to markdown instance
            return directive(md)
        except Exception as e:
            import sys
            print(f"Error registering documentation directives: {e}", file=sys.stderr)
            raise RuntimeError(f"Failed to register directives plugin: {e}") from e
    
    return plugin_documentation_directives
```

#### 4.2: Package Public API

**File:** `bengal/rendering/plugins/__init__.py`

```python
"""
Mistune plugins package for Bengal SSG.

Provides custom Mistune plugins for enhanced markdown processing:

Core Plugins:
    - VariableSubstitutionPlugin: {{ variable }} substitution in content
    - CrossReferencePlugin: [[link]] syntax for internal references

Documentation Directives:
    - Admonitions: note, warning, tip, danger, etc.
    - Tabs: Tabbed content sections
    - Dropdown: Collapsible sections
    - Code Tabs: Multi-language code examples

Usage:
    # Import plugins
    from bengal.rendering.plugins import (
        VariableSubstitutionPlugin,
        CrossReferencePlugin,
        create_documentation_directives
    )
    
    # Use in mistune parser
    md = mistune.create_markdown(
        plugins=[
            create_documentation_directives(),
            VariableSubstitutionPlugin(context),
        ]
    )

For detailed documentation on each plugin, see:
    - variable_substitution.py
    - cross_references.py
    - directives/ package
"""

from bengal.rendering.plugins.variable_substitution import VariableSubstitutionPlugin
from bengal.rendering.plugins.cross_references import CrossReferencePlugin
from bengal.rendering.plugins.directives import create_documentation_directives

# For backward compatibility, provide the old function name
def plugin_documentation_directives(md):
    """
    DEPRECATED: Use create_documentation_directives() instead.
    
    This function is maintained for backward compatibility but will be
    removed in a future version.
    """
    return create_documentation_directives()(md)


__all__ = [
    # Core plugins
    'VariableSubstitutionPlugin',
    'CrossReferencePlugin',
    
    # Directive factory
    'create_documentation_directives',
    
    # Backward compatibility (deprecated)
    'plugin_documentation_directives',
]

__version__ = '1.0.0'
```

---

### Phase 5: Update Imports (15 min)

#### 5.1: Update Parser

**File:** `bengal/rendering/parser.py`

```python
# Old import (line 124)
from bengal.rendering.mistune_plugins import plugin_documentation_directives

# New import
from bengal.rendering.plugins import (
    VariableSubstitutionPlugin,
    create_documentation_directives
)

# Update usage (line 137)
# Old:
plugin_documentation_directives,

# New:
create_documentation_directives(),
```

#### 5.2: Update Other References

```bash
# Search for any other imports
grep -r "mistune_plugins" bengal/
grep -r "mistune_plugins" tests/
```

---

### Phase 6: Testing & Validation (30 min)

#### 6.1: Run Existing Tests

```bash
# Run all mistune-related tests
pytest tests/unit/rendering/test_parser.py -v
pytest tests/unit/rendering/ -k mistune -v

# Run full test suite
pytest tests/
```

#### 6.2: Integration Testing

```bash
# Build example site
cd examples/quickstart
bengal build --parallel

# Verify output
ls -la public/
cat public/docs/index.html  # Check for directives, variables
```

#### 6.3: Manual Testing Checklist

- [ ] Variable substitution works in markdown
- [ ] Admonitions render correctly
- [ ] Tabs directive works with nested markdown
- [ ] Dropdown directive works
- [ ] Code tabs work
- [ ] Cross-references resolve correctly
- [ ] No import errors
- [ ] Performance unchanged (benchmark)

---

### Phase 7: Documentation & Cleanup (15 min)

#### 7.1: Create Plugin README

**File:** `bengal/rendering/plugins/README.md`

```markdown
# Mistune Plugins for Bengal SSG

This package provides custom Mistune plugins for enhanced markdown processing.

## Architecture

- **Core Plugins**: Variable substitution and cross-references
- **Directives**: Documentation features (admonitions, tabs, dropdowns)
- **Clean API**: Only 3 main exports, rest is internal

## Plugin Organization

### Core Plugins

- `variable_substitution.py` - {{ variable }} in markdown
- `cross_references.py` - [[link]] syntax

### Directives

- `directives/admonitions.py` - Callout boxes
- `directives/tabs.py` - Tabbed content
- `directives/dropdown.py` - Collapsible sections
- `directives/code_tabs.py` - Multi-language code examples

## Usage

See main package `__init__.py` for usage examples.

## Testing

Each plugin should have corresponding unit tests:
- `tests/unit/rendering/plugins/test_variable_substitution.py`
- `tests/unit/rendering/plugins/test_cross_references.py`
- `tests/unit/rendering/plugins/directives/test_*.py`

## Contributing

When adding new plugins:
1. Create focused module in appropriate location
2. Add to `__init__.py` exports if public
3. Write comprehensive tests
4. Update this README
```

#### 7.2: Update ARCHITECTURE.md

Add section about plugin architecture:

```markdown
### Mistune Plugins (`bengal/rendering/plugins/`)

Modular plugin system for Mistune markdown processing:

- **Variable Substitution**: `{{ page.title }}` in content
- **Cross-References**: `[[docs/page]]` syntax
- **Documentation Directives**: Admonitions, tabs, dropdowns
- **Clean Architecture**: Each plugin in focused ~100-200 line file
- **Easy Extension**: Add new plugins without touching existing code
```

#### 7.3: Remove Old File

```bash
# Only after verifying everything works!
git rm bengal/rendering/mistune_plugins.py
```

---

## 🔄 Migration Strategy

### Backward Compatibility

**✅ FULLY BACKWARD COMPATIBLE**

The old import path will continue to work via the compatibility layer:

```python
# Old code (still works)
from bengal.rendering.mistune_plugins import (
    VariableSubstitutionPlugin,
    plugin_documentation_directives
)

# New code (preferred)
from bengal.rendering.plugins import (
    VariableSubstitutionPlugin,
    create_documentation_directives
)
```

### Deprecation Timeline

1. **v0.2.0** (current): Both old and new imports work
2. **v0.3.0** (3 months): Add deprecation warnings for old imports
3. **v0.4.0** (6 months): Remove old file, only new imports work

---

## ✅ Quality Checklist

### Before Starting

- [ ] Read this entire plan
- [ ] Understand current plugin architecture
- [ ] Review test coverage for plugins
- [ ] Create git branch: `refactor/mistune-plugins`

### During Implementation

- [ ] Follow phases in order
- [ ] Test after each phase
- [ ] Keep commits focused (one phase = one commit)
- [ ] Document any deviations from plan

### Before Merging

- [ ] All existing tests pass
- [ ] New tests written and passing
- [ ] Documentation updated
- [ ] Example site builds successfully
- [ ] Performance benchmarks unchanged
- [ ] Code review completed
- [ ] CHANGELOG.md updated

---

## 📈 Expected Benefits

### Maintainability

- **Before**: 757-line file, hard to navigate
- **After**: 8 focused files, easy to find and modify

### Testability

- **Before**: Test entire plugins file
- **After**: Test each plugin independently, better isolation

### Extensibility

- **Before**: Add to bottom of large file
- **After**: Create new file, add to factory

### Documentation

- **Before**: Large docstrings mixed with code
- **After**: Each plugin documented in its file

### Code Review

- **Before**: Scroll through 757 lines
- **After**: Review single 100-line file

---

## 🎯 Success Criteria

1. ✅ All tests pass (including new tests)
2. ✅ Example site builds successfully
3. ✅ No performance regression (< 5% difference)
4. ✅ All plugins work identically to before
5. ✅ Import paths remain backward compatible
6. ✅ Code is easier to navigate and understand
7. ✅ Future plugin additions are straightforward

---

## 🚀 Execution Timeline

| Phase | Time | Dependencies | Validation |
|-------|------|--------------|------------|
| 1. Setup | 15 min | None | Directory structure exists |
| 2. Core Plugins | 45 min | Phase 1 | Files created, compile clean |
| 3. Directives | 60 min | Phase 1 | Files created, compile clean |
| 4. Factory/API | 30 min | Phases 2-3 | Imports work |
| 5. Update Imports | 15 min | Phase 4 | No import errors |
| 6. Testing | 30 min | Phase 5 | All tests pass |
| 7. Documentation | 15 min | Phase 6 | Docs updated |

**Total Time:** 3 hours 30 minutes (with breaks: 4 hours)

---

## 🎓 Learning Outcomes

This refactoring demonstrates:

1. **Package Organization**: How to structure Python packages
2. **API Design**: Clean public interface with backward compatibility
3. **Plugin Architecture**: Modular, extensible design
4. **Safe Refactoring**: Zero behavioral changes, just reorganization
5. **Documentation**: How to document plugin systems

---

## 📚 References

- [PEP 8](https://pep8.org/) - Python code style
- [Python Packages](https://python-packaging.readthedocs.io/) - Package structure
- [Mistune Documentation](https://mistune.lepture.com/) - Plugin API
- Bengal's `ARCHITECTURE.md` - System architecture

---

## 🤔 Open Questions

1. **Should we split tests too?**
   - Proposal: Yes, mirror the plugin structure in tests/
   - Decision: Defer to Phase 6

2. **Should we version the plugins package?**
   - Proposal: Yes, use `__version__` in `__init__.py`
   - Decision: Start with '1.0.0'

3. **Should we support plugin discovery?**
   - Proposal: No, explicit registration is clearer
   - Decision: Keep explicit for now

---

## 💡 Future Enhancements

After this refactoring, we could:

1. **Plugin Registry**: Auto-discover plugins in plugins/ dir
2. **Plugin Configuration**: Per-plugin config in bengal.toml
3. **Plugin Metrics**: Track which plugins are used/slow
4. **Third-party Plugins**: Allow external plugin packages
5. **Plugin CLI**: `bengal plugins list`, `bengal plugins install`

But these are NOT in scope for this refactoring!

---

## ✨ Summary

This refactoring transforms a working but monolithic 757-line file into a
clean, modular package with clear separation of concerns. It's low-risk
(backward compatible), high-value (much better organization), and sets us
up for future extensibility.

The plan is detailed enough to execute confidently, flexible enough to adapt,
and includes validation at every step.

**Let's make the code as beautiful as the architecture! 🐯**

