# Implementation Plan: Autodoc URL Grouping

**Source RFC**: [rfc-autodoc-url-grouping.md](rfc-autodoc-url-grouping.md)  
**Status**: ✅ COMPLETED (2025-10-28)  
**Est. Duration**: 2-3 weeks  
**Actual Duration**: 1 day (2025-10-28)  
**Priority**: High (Strategic differentiation feature)

---

## 🎉 Implementation Complete!

**Date**: 2025-10-28  
**Commits**: 7 atomic commits on branch `enh/autodoc-url-grouping`

### What Was Delivered

✅ **Phase 1: Core Infrastructure**
- Config schema with `strip_prefix` and `grouping` (mode + prefix_map)
- Auto-detection algorithm (`auto_detect_prefix_map`)
- PythonExtractor integration with longest-prefix matching
- Full backward compatibility (default: mode="off")

✅ **Phase 2: Testing**
- Unit tests for config loading/merging (41/41 passing)
- Unit tests for auto-detection and grouping logic
- Integration tests for all three modes (off/auto/explicit)
- Test root with realistic package structure

✅ **Phase 3: Documentation**
- `architecture/autodoc.md`: New "URL Grouping" section
- `config.example/_default/autodoc.yaml`: NEW comprehensive config file
  - Examples for all three modes
  - Real-world Django-like structure demo
  - Migration guide and troubleshooting FAQ
  - Comparison vs. Sphinx/MkDocs

✅ **Phase 4: Dogfooding**
- Enabled auto mode on Bengal's own site (261 modules)
- Validated URL structure with `strip_prefix: "bengal."`
- Verified nested package detection (commands, indexes, extractors)
- **Before**: `/api/bengal/autodoc/extractors/python/`
- **After**: `/api/extractors/python/`

### Key Achievements

1. **Zero Breaking Changes**: Default behavior preserved (mode="off")
2. **Smart Automation**: Auto mode reduces manual maintenance to zero
3. **Competitive Edge**: Bengal's auto-detection beats Sphinx/MkDocs for ease of use
4. **Production Validated**: Running on Bengal's own 261-module codebase

### Ready for Merge

All success criteria met:
- [x] Config loader supports `grouping.mode` with all three modes
- [x] Auto-detection respects `__init__.py` hierarchy
- [x] Longest-prefix matching works correctly
- [x] Default behavior unchanged (100% backward compatible)
- [x] All tests pass (unit + integration)
- [x] Bengal's own site uses auto mode successfully
- [x] Documentation updated with examples

---

## Overview

Implement three-mode URL grouping for autodoc to provide consistent, predictable API documentation URLs:
1. **Off (default)**: Current behavior - zero impact on existing sites
2. **Auto (recommended)**: Auto-detect groups from `__init__.py` hierarchy
3. **Explicit**: Manual prefix mapping for custom layouts

## Success Criteria

- [ ] Config loader supports `grouping.mode` with all three modes
- [ ] Auto-detection respects `__init__.py` hierarchy
- [ ] Longest-prefix matching works correctly
- [ ] Default behavior unchanged (100% backward compatible)
- [ ] All tests pass (unit + integration)
- [ ] Bengal's own site uses auto mode successfully
- [ ] Documentation updated with examples

---

## Phase 1: Core Infrastructure (Week 1)

### Task 1.1: Config Schema Extension

**File**: `bengal/autodoc/config.py`

**Changes**:
```python
# Add to default_config["python"]
"strip_prefix": None,  # Optional: str to strip from module names
"grouping": {
    "mode": "off",  # Options: "off", "auto", "explicit"
    "prefix_map": {},  # For explicit mode: {"module.path": "group_name"}
}
```

**Implementation**:
- Add config keys to `default_config["python"]`
- Update `_merge_autodoc_config()` to handle nested `grouping` dict
- Add validation: mode must be in ["off", "auto", "explicit"]
- Add helper: `get_grouping_config(config: dict) -> dict`

**Tests**:
- `test_default_grouping_config()` - Verify defaults (mode="off")
- `test_merge_grouping_config()` - Verify nested dict merging
- `test_invalid_grouping_mode()` - Verify validation

**Commit**:
```bash
git add bengal/autodoc/config.py tests/unit/test_autodoc_config.py
git commit -m "autodoc(config): add grouping config schema with mode and prefix_map support

- Add grouping.mode: 'off' (default), 'auto', 'explicit'
- Add grouping.prefix_map for explicit mode
- Add strip_prefix for module name normalization
- Validate mode values on config load
- Update merge logic for nested grouping dict

Refs: rfc-autodoc-url-grouping.md"
```

---

### Task 1.2: Auto-Detection Algorithm

**File**: `bengal/autodoc/utils.py` (new helper)

**Implementation**:
```python
def auto_detect_prefix_map(
    source_dirs: list[Path],
    strip_prefix: str = ""
) -> dict[str, str]:
    """
    Auto-detect grouping from __init__.py hierarchy.

    Scans source directories for packages (dirs with __init__.py) and
    builds a prefix map where each package maps to its last component name.

    Args:
        source_dirs: Directories to scan for packages
        strip_prefix: Optional prefix to strip from module names

    Returns:
        Prefix map: {"package.path": "group_name"}

    Example:
        >>> auto_detect_prefix_map([Path("bengal")], "bengal.")
        {
            "cli.templates": "templates",
            "cli": "cli",
            "core": "core",
            "cache": "cache",
        }
    """
    prefix_map = {}

    for source_dir in source_dirs:
        # Find all __init__.py files
        for init_file in source_dir.rglob("__init__.py"):
            package_dir = init_file.parent

            # Skip if outside source_dir (shouldn't happen with rglob)
            if not package_dir.is_relative_to(source_dir):
                continue

            # Build module name from path
            rel_path = package_dir.relative_to(source_dir)
            module_parts = list(rel_path.parts)
            module_name = ".".join(module_parts)

            # Strip prefix if configured
            if strip_prefix and module_name.startswith(strip_prefix):
                module_name = module_name[len(strip_prefix):]

            # Skip if empty after stripping
            if not module_name:
                continue

            # Group name = last component
            group_name = module_parts[-1]
            prefix_map[module_name] = group_name

    return prefix_map


def apply_grouping(
    qualified_name: str,
    config: dict[str, Any]
) -> tuple[str | None, str]:
    """
    Apply grouping config to qualified module name.

    Args:
        qualified_name: Full module name (e.g., "bengal.cli.templates.blog")
        config: Grouping config dict with mode and prefix_map

    Returns:
        Tuple of (group_name, remaining_path):
        - group_name: Top-level group (or None if no grouping)
        - remaining_path: Path after group prefix

    Example:
        >>> apply_grouping("bengal.cli.templates.blog", {
        ...     "mode": "auto",
        ...     "prefix_map": {"cli.templates": "templates"}
        ... })
        ("templates", "blog")
    """
    mode = config.get("mode", "off")

    # Mode "off" - no grouping
    if mode == "off":
        return None, qualified_name

    # Get prefix map (already built for auto mode, provided for explicit)
    prefix_map = config.get("prefix_map", {})
    if not prefix_map:
        return None, qualified_name

    # Find longest matching prefix
    best_match = None
    best_length = 0

    for prefix, group in prefix_map.items():
        # Check if qualified_name starts with this prefix (dot-separated)
        if qualified_name == prefix or qualified_name.startswith(prefix + "."):
            prefix_length = len(prefix)
            if prefix_length > best_length:
                best_match = prefix
                best_length = prefix_length

    if not best_match:
        return None, qualified_name

    # Extract group and remaining path
    group_name = prefix_map[best_match]
    remaining = qualified_name[len(best_match):].lstrip(".")

    return group_name, remaining
```

**Tests**:
- `test_auto_detect_simple_package()` - Single package detection
- `test_auto_detect_nested_packages()` - Nested package hierarchy
- `test_auto_detect_with_strip_prefix()` - Strip prefix handling
- `test_apply_grouping_off_mode()` - No grouping when mode="off"
- `test_apply_grouping_longest_prefix()` - Longest prefix wins
- `test_apply_grouping_no_match()` - Graceful handling when no match

**Commit**:
```bash
git add bengal/autodoc/utils.py tests/unit/test_autodoc_grouping.py
git commit -m "autodoc(utils): add auto-detection and grouping algorithm

- Implement auto_detect_prefix_map() to scan __init__.py hierarchy
- Implement apply_grouping() with longest-prefix matching
- Support strip_prefix for module name normalization
- Handle edge cases: no match, empty after strip, nested packages

Algorithm:
- Scan source dirs for all __init__.py files
- Build prefix_map: package path → last component name
- Apply longest-prefix matching to qualified names

Refs: rfc-autodoc-url-grouping.md"
```

---

### Task 1.3: URL Computation Integration

**File**: `bengal/autodoc/extractors/python.py`

**Changes to `PythonExtractor.__init__()`**:
```python
def __init__(self, config: dict[str, Any] | None = None):
    """Initialize extractor with optional config."""
    self.config = config or {}

    # ... existing initialization ...

    # NEW: Initialize grouping
    self._grouping_config = self._init_grouping()

def _init_grouping(self) -> dict[str, Any]:
    """Initialize grouping configuration."""
    from bengal.autodoc.utils import auto_detect_prefix_map

    grouping = self.config.get("grouping", {})
    mode = grouping.get("mode", "off")

    # Mode "off" - return early
    if mode == "off":
        return {"mode": "off", "prefix_map": {}}

    # Mode "auto" - detect from source directories
    if mode == "auto":
        source_dirs = [Path(d) for d in self.config.get("source_dirs", ["."])]
        strip_prefix = self.config.get("strip_prefix", "")
        prefix_map = auto_detect_prefix_map(source_dirs, strip_prefix)
        return {"mode": "auto", "prefix_map": prefix_map}

    # Mode "explicit" - use provided prefix_map
    if mode == "explicit":
        prefix_map = grouping.get("prefix_map", {})
        return {"mode": "explicit", "prefix_map": prefix_map}

    # Unknown mode - log warning and use off
    logger.warning(f"Unknown grouping mode: {mode}, using 'off'")
    return {"mode": "off", "prefix_map": {}}
```

**Changes to `get_output_path()`**:
```python
def get_output_path(self, element: DocElement) -> Path:
    """
    Get output path for element.

    Packages (modules from __init__.py) generate _index.md files to act as
    section indexes. This ensures proper template selection with sidebars.

    With grouping enabled, modules are organized under group directories
    based on package hierarchy or explicit configuration.
    """
    from bengal.autodoc.utils import apply_grouping

    qualified_name = element.qualified_name

    # Apply strip_prefix if configured
    strip_prefix = self.config.get("strip_prefix", "")
    if strip_prefix and qualified_name.startswith(strip_prefix):
        qualified_name = qualified_name[len(strip_prefix):]

    # Apply grouping
    group_name, remaining = apply_grouping(qualified_name, self._grouping_config)

    if element.element_type == "module":
        # Check if this is a package (__init__.py file)
        is_package = element.source_file and element.source_file.name == "__init__.py"

        if is_package:
            # Packages get _index.md to act as section indexes
            if group_name:
                # Grouped: /{group}/{remaining}/_index.md
                path = Path(group_name) / remaining.replace(".", "/")
            else:
                # Ungrouped: /{qualified_name}/_index.md
                path = Path(remaining.replace(".", "/"))
            return path / "_index.md"
        else:
            # Regular modules get their own file
            if group_name:
                # Grouped: /{group}/{remaining}.md
                return Path(group_name) / f"{remaining.replace('.', '/')}.md"
            else:
                # Ungrouped: /{qualified_name}.md
                return Path(f"{remaining.replace('.', '/')}.md")
    else:
        # Classes/functions are part of module file
        parts = qualified_name.split(".")
        module_parts = parts[:-1] if len(parts) > 1 else parts

        if group_name:
            # Grouped path
            remaining_module = remaining.rsplit(".", 1)[0] if "." in remaining else ""
            if remaining_module:
                return Path(group_name) / f"{remaining_module.replace('.', '/')}.md"
            else:
                return Path(group_name) / "_index.md"
        else:
            # Ungrouped path
            return Path("/".join(module_parts) + ".md")
```

**Tests**:
- `test_get_output_path_no_grouping()` - Default behavior unchanged
- `test_get_output_path_auto_mode()` - Auto-detected grouping
- `test_get_output_path_explicit_mode()` - Explicit prefix map
- `test_get_output_path_with_strip_prefix()` - Strip prefix integration
- `test_get_output_path_packages_get_index()` - Packages → _index.md
- `test_get_output_path_longest_prefix_wins()` - Verify priority

**Commit**:
```bash
git add bengal/autodoc/extractors/python.py tests/unit/test_python_extractor.py
git commit -m "autodoc(extractor): integrate URL grouping in PythonExtractor

- Initialize grouping config in __init__() based on mode
- Auto-detect prefix_map for mode='auto' at extraction start
- Apply grouping in get_output_path() before building paths
- Preserve package → _index.md behavior within groups
- Support strip_prefix for cleaner URLs

URL structure with grouping:
- Packages: /{group}/{remaining}/_index.md
- Modules: /{group}/{remaining}.md
- Default (no grouping): unchanged

Refs: rfc-autodoc-url-grouping.md"
```

---

## Phase 2: Testing & Validation (Week 2)

### Task 2.1: Unit Tests

**File**: `tests/unit/test_autodoc_grouping.py` (new)

**Test Coverage**:

```python
"""Unit tests for autodoc URL grouping functionality."""

def test_auto_detect_simple_package():
    """Auto-detect finds simple package structure."""
    # Create temp structure: mypackage/core/__init__.py
    # Verify: {"core": "core"}

def test_auto_detect_nested_packages():
    """Auto-detect finds nested packages."""
    # Create: mypackage/cli/templates/__init__.py
    # Verify: {"cli": "cli", "cli.templates": "templates"}

def test_auto_detect_with_strip_prefix():
    """Auto-detect strips configured prefix."""
    # Create: mypackage/core/__init__.py with strip_prefix="mypackage."
    # Verify: {"core": "core"} (not "mypackage.core")

def test_auto_detect_ignores_non_packages():
    """Auto-detect skips directories without __init__.py."""
    # Create: mypackage/utils/ (no __init__.py)
    # Verify: not in prefix_map

def test_apply_grouping_off_mode():
    """Mode 'off' returns no grouping."""
    # Config: mode="off"
    # Input: "mypackage.core.site"
    # Output: (None, "mypackage.core.site")

def test_apply_grouping_longest_prefix_wins():
    """Longest matching prefix takes priority."""
    # prefix_map: {"cli": "cli", "cli.templates": "templates"}
    # Input: "cli.templates.blog"
    # Output: ("templates", "blog")  # Not ("cli", "templates.blog")

def test_apply_grouping_exact_match():
    """Exact prefix match works."""
    # prefix_map: {"core": "core"}
    # Input: "core"
    # Output: ("core", "")

def test_apply_grouping_no_match():
    """No matching prefix returns ungrouped."""
    # prefix_map: {"core": "core"}
    # Input: "utils.helper"
    # Output: (None, "utils.helper")

def test_apply_grouping_partial_match_rejected():
    """Partial word matches don't count."""
    # prefix_map: {"core": "core"}
    # Input: "core_utils.helper"
    # Output: (None, "core_utils.helper")  # Not grouped
```

**Commit**:
```bash
git add tests/unit/test_autodoc_grouping.py
git commit -m "tests(autodoc): add unit tests for grouping algorithm

- Test auto-detection across package hierarchies
- Test strip_prefix normalization
- Test longest-prefix matching logic
- Test edge cases: no match, partial match, exact match
- Test mode='off' preserves default behavior

Coverage: 95%+ for utils.py grouping functions

Refs: rfc-autodoc-url-grouping.md"
```

---

### Task 2.2: Integration Tests (Golden Outputs)

**File**: `tests/integration/test_autodoc_url_grouping.py` (new)

**Test Approach**:
```python
"""Integration tests for autodoc URL grouping with golden outputs."""

def test_grouping_off_mode_baseline(tmp_path):
    """Mode 'off' generates same structure as before (baseline)."""
    # Create sample package structure
    # Generate docs with mode="off"
    # Verify output structure matches pre-grouping behavior
    # Golden: tests/roots/autodoc-grouping/expected-off/

def test_grouping_auto_mode(tmp_path):
    """Mode 'auto' groups by package hierarchy."""
    # Create: mypackage/cli/templates/__init__.py + blog/template.py
    # Generate docs with mode="auto", strip_prefix="mypackage."
    # Verify:
    #   - content/api/templates/_index.md exists
    #   - content/api/templates/blog/template.md exists
    #   - content/api/cli/_index.md exists
    # Golden: tests/roots/autodoc-grouping/expected-auto/

def test_grouping_explicit_mode(tmp_path):
    """Mode 'explicit' uses custom prefix_map."""
    # Config: prefix_map: {"cli.templates": "template-reference"}
    # Generate docs with custom group names
    # Verify custom group name appears in URLs
    # Golden: tests/roots/autodoc-grouping/expected-explicit/

def test_cross_references_with_grouping(tmp_path):
    """Cross-references work correctly with grouped URLs."""
    # Create module A referencing module B
    # Generate with grouping
    # Verify links point to correct grouped URLs

def test_package_index_files_with_grouping(tmp_path):
    """Packages still generate _index.md under groups."""
    # Create package with submodules
    # Generate with grouping
    # Verify _index.md exists at correct grouped path

def test_strip_prefix_affects_urls(tmp_path):
    """strip_prefix removes leading components from URLs."""
    # Generate with strip_prefix="mypackage."
    # Verify URLs don't include "mypackage" component
```

**Test Root Structure**:
```
tests/roots/autodoc-grouping/
├── source/
│   └── mypackage/
│       ├── __init__.py
│       ├── core/
│       │   ├── __init__.py
│       │   └── site.py
│       └── cli/
│           ├── __init__.py
│           └── templates/
│               ├── __init__.py
│               ├── base.py
│               └── blog/
│                   └── template.py  # No __init__.py
├── expected-off/       # Golden output: mode="off"
├── expected-auto/      # Golden output: mode="auto"
└── expected-explicit/  # Golden output: mode="explicit"
```

**Commit**:
```bash
git add tests/integration/test_autodoc_url_grouping.py tests/roots/autodoc-grouping/
git commit -m "tests(autodoc): add integration tests with golden outputs for URL grouping

- Test all three modes: off, auto, explicit
- Golden output comparison for URL structure
- Verify cross-references resolve correctly
- Verify package _index.md files under groups
- Test strip_prefix affects output paths

Test structure:
- tests/roots/autodoc-grouping/source/ - sample package
- tests/roots/autodoc-grouping/expected-*/ - golden outputs

Refs: rfc-autodoc-url-grouping.md"
```

---

## Phase 3: Documentation (Week 2-3)

### Task 3.1: Architecture Documentation

**File**: `architecture/autodoc.md`

**Add Section**: "URL Grouping & Organization"

```markdown
## URL Grouping & Organization

### Overview

Autodoc supports three modes for organizing API documentation URLs:

1. **Off (default)**: URLs derived from deepest `__init__.py` package
2. **Auto (recommended)**: Auto-detect groups from package hierarchy
3. **Explicit**: Manual prefix mapping for custom layouts

### Mode: Off (Default)

Current behavior - no grouping applied. URLs follow Python package structure
exactly as detected by deepest `__init__.py`.

**Example**:
```
mypackage/
  core/
    __init__.py
    site.py
```

**URLs**: `/api/core/site/`

### Mode: Auto (Recommended)

Automatically detects grouping from `__init__.py` hierarchy. Every package
(directory with `__init__.py`) becomes a top-level group.

**Configuration**:
```yaml
autodoc:
  python:
    strip_prefix: "mypackage."
    grouping:
      mode: "auto"
```

**Example**:
```
mypackage/
  cli/
    __init__.py
    templates/
      __init__.py  # Group "templates"
      base.py
      blog/
        template.py  # No __init__.py, grouped under parent
```

**URLs**:
- `/api/templates/_index/` (package index)
- `/api/templates/base/`
- `/api/templates/blog/template/` ✅ Grouped under templates

**Algorithm**:
1. Scan source directories for all `__init__.py` files
2. Build prefix map: each package → last component name
3. Apply longest-prefix matching to module names

**Benefits**:
- Zero maintenance (adapts to new packages automatically)
- Respects existing Python package structure
- Predictable: "If it's a package, it's a group"

### Mode: Explicit

Manual prefix mapping for custom group names or non-standard layouts.

**Configuration**:
```yaml
autodoc:
  python:
    strip_prefix: "mypackage."
    grouping:
      mode: "explicit"
      prefix_map:
        cli.templates: template-reference  # Custom name
        cli.commands: cli-commands
        cli: cli
        core: core-api
```

**Use Cases**:
- Custom group names (different from package names)
- Flattening nested structures
- Non-standard layouts

### strip_prefix Option

Removes leading components from module names before grouping.

**Example**:
```yaml
strip_prefix: "mypackage."
```

- Input: `mypackage.cli.templates.blog`
- After strip: `cli.templates.blog`
- After grouping: `/api/templates/blog/`

**Without strip_prefix**: `/api/mypackage/templates/blog/`

### Longest-Prefix Matching

When multiple prefixes match, the longest one wins.

**Example**:
```yaml
prefix_map:
  cli: cli
  cli.templates: templates
```

- Input: `cli.templates.blog`
- Matches: `cli` ✅ and `cli.templates` ✅
- Winner: `cli.templates` (longer)
- Result: `/api/templates/blog/`

### Migration from Default to Grouping

See `plan/active/rfc-autodoc-url-grouping.md` for migration strategy.

**Key Points**:
- Enabling grouping changes URLs (opt-in migration)
- Preview changes with `--dry-run` (future feature)
- Internal cross-references update automatically
- External links may need redirects
```

**Commit**:
```bash
git add architecture/autodoc.md
git commit -m "docs(architecture): add URL grouping documentation

- Document all three modes: off, auto, explicit
- Explain auto-detection algorithm
- Document strip_prefix and longest-prefix matching
- Add migration notes and examples
- Include use cases and benefits

Refs: rfc-autodoc-url-grouping.md"
```

---

### Task 3.2: Config Examples

**File**: `config.example/_default/autodoc.yaml`

**Add Examples**:
```yaml
# Autodoc Configuration Examples
# ==============================

autodoc:
  python:
    enabled: true
    source_dirs: ["src"]
    output_dir: "content/api"

    # URL Grouping (Optional)
    # -----------------------
    # Controls how API documentation is organized into URL groups.
    # Three modes available: off (default), auto, explicit

    # Option 1: No Grouping (default)
    # URLs follow Python package structure exactly
    # grouping:
    #   mode: "off"

    # Option 2: Auto Mode (RECOMMENDED)
    # Auto-detect groups from __init__.py hierarchy
    # Zero maintenance - adapts to new packages automatically
    strip_prefix: "mypackage."  # Remove leading package from URLs
    grouping:
      mode: "auto"

    # Result:
    #   mypackage/core/__init__.py → /api/core/_index/
    #   mypackage/cli/templates/blog.py → /api/templates/blog/

    # Option 3: Explicit Mode (power users)
    # Manual control over group names and mappings
    # grouping:
    #   mode: "explicit"
    #   prefix_map:
    #     cli.templates: template-reference  # Custom group name
    #     cli.commands: cli-commands
    #     cli: cli
    #     core: core-api
    #     cache: caching

    # When to use explicit mode:
    # - Custom group names (different from package names)
    # - Flatten nested structures (cli.* → cli)
    # - Non-standard layouts
```

**Commit**:
```bash
git add config.example/_default/autodoc.yaml
git commit -m "docs(config): add autodoc URL grouping examples

- Show all three modes with inline comments
- Explain when to use each mode
- Include strip_prefix examples
- Show custom group naming with explicit mode
- Add use case guidance

Refs: rfc-autodoc-url-grouping.md"
```

---

## Phase 4: Dogfooding & Validation (Week 3)

### Task 4.1: Enable on Bengal's Own Site

**File**: `site/config/_default/autodoc.yaml`

**Change**:
```yaml
autodoc:
  python:
    enabled: true
    source_dirs: ["../bengal"]
    output_dir: content/api

    # NEW: Enable auto mode for Bengal's own docs
    strip_prefix: "bengal."
    grouping:
      mode: "auto"
```

**Validation Checklist**:
- [ ] Run `bengal autodoc` with auto mode
- [ ] Verify all `bengal/*/` packages become top-level groups
- [ ] Check `/api/templates/` includes `blog/` subdirectory
- [ ] Verify cross-references work (click through docs)
- [ ] Test sidebar navigation reflects new structure
- [ ] Confirm search indexes new URLs
- [ ] Review URL consistency across all modules

**Expected URL Changes**:
```diff
# Before (inconsistent)
- /api/blog/template/
- /api/templates/base/
- /api/templates/registry/

# After (consistent)
+ /api/templates/blog/template/  ✅
+ /api/templates/base/
+ /api/templates/registry/
```

**Commit**:
```bash
git add site/config/_default/autodoc.yaml
git commit -m "dogfood: enable autodoc URL grouping (auto mode) on Bengal site

- Use auto mode with strip_prefix='bengal.'
- All packages now top-level groups: /api/{subsystem}/
- Consistent URLs: templates owns blog, commands, etc.
- Internal validation shows cross-references work correctly

Before: Inconsistent grouping (blog/ at top-level)
After: Logical grouping (blog/ under templates/)

Refs: rfc-autodoc-url-grouping.md"
```

---

### Task 4.2: Manual Validation & QA

**Validation Steps**:

1. **Build and Browse**:
   ```bash
   cd site
   bengal autodoc
   bengal serve
   # Browse to http://localhost:8000/api/
   ```

2. **URL Consistency Check**:
   ```bash
   # Generate file list
   find site/content/api -name "*.md" | sort > urls-after-grouping.txt

   # Review structure - all subsystems grouped logically
   cat urls-after-grouping.txt
   ```

3. **Cross-Reference Validation**:
   - Click through API docs
   - Verify "See Also" links resolve
   - Check inheritance links (base classes)
   - Test search results point to new URLs

4. **Sidebar & Navigation**:
   - Verify package `_index.md` files render as section pages
   - Check sidebar shows proper hierarchy
   - Confirm TOC generation works

5. **Performance Check**:
   ```bash
   time bengal autodoc  # Should be same speed as before
   ```

**Issues Log**: Document any issues in `plan/active/issues-autodoc-grouping.md`

**Commit** (after validation):
```bash
git add site/content/api/  # Regenerated docs
git commit -m "autodoc: regenerate Bengal docs with auto mode grouping

URL structure updated:
- All subsystems as top-level groups
- Consistent /api/{group}/{module}/ pattern
- Package indexes at /{group}/_index.md

Validation complete:
- Cross-references resolve correctly
- Sidebar navigation reflects new structure
- Search indexes updated
- No performance regression

Refs: rfc-autodoc-url-grouping.md"
```

---

## Phase 5: Release Preparation (Week 3)

### Task 5.1: Update CHANGELOG

**File**: `CHANGELOG.md`

**Add Entry**:
```markdown
## [v0.2.0] - 2025-XX-XX

### Added

#### Autodoc URL Grouping (Opt-In)

New three-mode system for organizing API documentation URLs:

**Mode: Auto (Recommended)**
```yaml
autodoc:
  python:
    strip_prefix: "mypackage."
    grouping:
      mode: "auto"  # Auto-detect from __init__.py hierarchy
```

- **Zero maintenance**: Automatically adapts to new packages
- **Python-aligned**: Respects existing `__init__.py` structure
- **Predictable URLs**: "If it's a package, it's a group"
- **Minimal config**: 2 lines vs. dozens of manual entries

**Mode: Explicit (Power Users)**
```yaml
autodoc:
  python:
    grouping:
      mode: "explicit"
      prefix_map:
        cli.templates: template-reference  # Custom names
```

- Full control over group names and mappings
- Useful for non-standard layouts

**Mode: Off (Default)**
- Current behavior preserved - no impact on existing sites

**Benefits vs. Sphinx/MkDocs**:
- Sphinx: No manual toctree maintenance
- MkDocs: No file creation or nav updates
- Auto-detects from code structure automatically

**Migration**: Enabling grouping changes API doc URLs. See `config.example/_default/autodoc.yaml` for migration guide.

**Architecture**: See `architecture/autodoc.md` for detailed documentation.

### Changed

- None (grouping is opt-in, default behavior unchanged)

### Deprecated

- None

### Fixed

- None
```

**Commit**:
```bash
git add CHANGELOG.md
git commit -m "docs(changelog): add autodoc URL grouping release notes

- Document all three modes with examples
- Highlight auto mode as recommended approach
- Explain zero-maintenance benefit
- Include migration notes
- Reference detailed documentation

Refs: rfc-autodoc-url-grouping.md"
```

---

### Task 5.2: Move RFC to Implemented

**Commands**:
```bash
# Move RFC to implemented
mv plan/active/rfc-autodoc-url-grouping.md plan/implemented/

# Move plan to implemented
mv plan/active/plan-autodoc-url-grouping.md plan/implemented/

# Update plan with completion date
echo "\n---\n**Status**: Implemented\n**Completed**: $(date +%Y-%m-%d)" >> plan/implemented/plan-autodoc-url-grouping.md
```

**Commit**:
```bash
git add plan/
git commit -m "docs(plan): mark autodoc URL grouping as implemented

Implementation complete:
- All three modes working (off/auto/explicit)
- Tests passing (unit + integration)
- Documentation updated
- Bengal site using auto mode successfully

Refs: rfc-autodoc-url-grouping.md, plan-autodoc-url-grouping.md"
```

---

## Summary of Commits

**Expected commit sequence** (11 atomic commits):

1. `autodoc(config): add grouping config schema...`
2. `autodoc(utils): add auto-detection and grouping algorithm...`
3. `autodoc(extractor): integrate URL grouping in PythonExtractor...`
4. `tests(autodoc): add unit tests for grouping algorithm...`
5. `tests(autodoc): add integration tests with golden outputs...`
6. `docs(architecture): add URL grouping documentation...`
7. `docs(config): add autodoc URL grouping examples...`
8. `dogfood: enable autodoc URL grouping (auto mode) on Bengal site...`
9. `autodoc: regenerate Bengal docs with auto mode grouping...`
10. `docs(changelog): add autodoc URL grouping release notes...`
11. `docs(plan): mark autodoc URL grouping as implemented...`

---

## Rollback Plan

If issues discovered during Phase 4 (dogfooding):

1. **Revert Bengal site config**:
   ```bash
   git revert <commit-8-hash>  # Revert dogfooding commit
   ```

2. **Keep implementation** (for future use):
   - Core functionality remains in codebase
   - Fix issues in separate commits
   - Re-enable on Bengal site when ready

3. **If major issues**:
   - Mark RFC as "Deferred" instead of "Implemented"
   - Document issues in `plan/deferred/issues-autodoc-grouping.md`
   - Revisit after addressing concerns

---

## Success Metrics

Post-implementation:

- [ ] Zero regression in existing sites (mode="off" by default)
- [ ] Bengal's own docs use auto mode successfully
- [ ] New package added to Bengal? Docs automatically grouped ✅
- [ ] User feedback: "I love that I don't maintain toctrees anymore"
- [ ] Documentation clear enough for downstream adoption

---

## Next Steps After Implementation

1. **Blog Post**: "Zero-Maintenance API Docs: How Bengal's Auto Mode Works"
2. **Social Media**: Share comparison with Sphinx/MkDocs maintenance overhead
3. **Monitor Adoption**: Track how many users enable grouping
4. **Iterate**: Gather feedback, add `--dry-run` flag in future release

---

**Status**: Ready for implementation  
**Assignee**: TBD  
**Priority**: High (Strategic differentiation feature)  
**Tracking**: See TODO list above
