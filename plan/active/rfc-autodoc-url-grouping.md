Title: RFC: Configurable Autodoc URL Grouping via Prefix Mapping
Status: Draft
Author: Bengal Team
Date: 2025-10-25
Version: 2 (Updated with auto-detection mode)

## Executive Summary

This RFC proposes **three-mode URL grouping** for autodoc:
1. **Off (default)**: Current behavior - zero impact on existing sites
2. **Auto (recommended)**: Auto-detect groups from `__init__.py` hierarchy - respects Python package structure
3. **Explicit**: Manual prefix mapping - full control for power users

**Key Benefits**:
- ✅ Consistent, predictable URLs aligned with package structure
- ✅ Zero maintenance (auto mode adapts to new packages automatically)
- ✅ 100% backward compatible (opt-in via config)
- ✅ Works with directory-based config (`config/_default/autodoc.yaml`)

## Problem Statement

The Python autodoc currently derives module-to-URL mappings from the deepest package containing an `__init__.py`. This leads to inconsistent, code-structure-driven URL roots.

**Example of inconsistency**:
- `bengal/cli/templates/base.py` → `/api/templates/base/` ✅
- `bengal/cli/templates/registry.py` → `/api/templates/registry/` ✅
- `bengal/cli/templates/blog/template.py` → `/api/blog/template/` ❌ (missing `templates/`)

The last module appears at top-level because `blog/` lacks an `__init__.py`, so the deepest package is `templates`, but the URL generation doesn't group it under that package.

**User expectation**: All template modules under `/api/templates/*` regardless of subdirectory structure.

**Current behavior**: URL layout depends on internal package details (`__init__.py` placement) rather than logical grouping intent.

## Goals

- Provide consistent, predictable URL grouping for autodoc-generated API documentation
- **Auto-detect grouping** from existing Python package structure (zero maintenance)
- Keep default behavior 100% backward compatible (opt-in via config)
- Offer three modes: off (default), auto (smart), explicit (power users)
- Preserve Python packaging (do not require removing `__init__.py`)
- Work seamlessly with directory-based config (`config/_default/autodoc.yaml`)

## Non-Goals

- Rewriting import/package structure (respect existing Python layout)
- Forcing migration (default behavior preserved, grouping is opt-in)
- Complex glob-based rules as primary interface (explicit mode can add these later if needed)
- Breaking existing sites (zero impact unless explicitly enabled)

## Current State (Evidence)

Module name inference relies on deepest `__init__.py` and drives output paths:

```481:501:/Users/llane/Documents/github/python/bengal/bengal/autodoc/extractors/python.py
def _infer_module_name(self, file_path: Path) -> str:
    """Infer module name from file path."""
    # Remove .py extension
    parts = list(file_path.parts)

    # Find the start of the package (look for __init__.py)
    package_start = 0
    for i in range(len(parts) - 1, -1, -1):
        parent = Path(*parts[: i + 1])
        if (parent / "__init__.py").exists():
            package_start = i
            break

    # Build module name
    module_parts = parts[package_start:]
    if module_parts[-1] == "__init__.py":
        module_parts = module_parts[:-1]
    elif module_parts[-1].endswith(".py"):
        module_parts[-1] = module_parts[-1][:-3]

    return ".".join(module_parts)
```

Output path generation uses the qualified name directly:

```669:699:/Users/llane/Documents/github/python/bengal/bengal/autodoc/extractors/python.py
def get_output_path(self, element: DocElement) -> Path:
    """
    Get output path for element.

    Packages (modules from __init__.py) generate _index.md files to act as
    section indexes, matching the CLI extractor behavior. This ensures proper
    template selection with sidebars when the package has submodules.
    """
    if element.element_type == "module":
        # Check if this is a package (__init__.py file)
        is_package = element.source_file and element.source_file.name == "__init__.py"

        if is_package:
            # Packages get _index.md to act as section indexes
            module_path = element.qualified_name.replace(".", "/")
            return Path(module_path) / "_index.md"
        else:
            # Regular modules get their own file
            return Path(element.qualified_name.replace(".", "/") + ".md")
    else:
        # Classes/functions are part of module file
        parts = element.qualified_name.split(".")
        module_parts = parts[:-1] if len(parts) > 1 else parts
        return Path("/".join(module_parts) + ".md")
```

Autodoc configuration today (partial):

```24:43:/Users/llane/Documents/github/python/bengal/site/bengal.toml
[autodoc.python]
enabled = true
source_dirs = ["../bengal"]
output_dir = "content/api"
docstring_style = "auto"
# Member visibility
include_private = false
include_special = false
```

## Proposed Design

Introduce **optional** URL grouping via three modes, preserving backward compatibility:

### Mode 1: Off (Default - Current Behavior)

If no `grouping` config is present, behavior is **unchanged**:
- URLs continue to use deepest `__init__.py` package
- Zero impact on existing sites

### Mode 2: Auto (Recommended - Smart Default)

Auto-detect grouping from Python package structure (`__init__.py` hierarchy):

```yaml
autodoc:
  python:
    strip_prefix: "bengal."
    grouping:
      mode: "auto"  # Auto-detect from filesystem
```

**Algorithm**:
1. Scan source directories for all `__init__.py` files
2. Build prefix map: each package → last component name
3. Apply longest-prefix matching

**Example auto-detected mapping** for `bengal/`:
```
bengal.cli.templates → "templates"
bengal.cli.commands  → "commands"
bengal.cli           → "cli"
bengal.core          → "core"
bengal.cache         → "cache"
```

**Result**:
- `bengal.cli.templates.blog.template` → `/api/templates/blog/template/` ✅
- `bengal.cli.templates.base` → `/api/templates/base/` ✅
- `bengal.core.site` → `/api/core/site/` ✅

### Mode 3: Explicit (Power Users - Full Control)

Manual prefix mapping for non-standard layouts:

```yaml
autodoc:
  python:
    strip_prefix: "bengal."
    grouping:
      mode: "explicit"
      prefix_map:
        cli.templates: "templates"
        cli.commands: "cli-reference"  # Custom group name
        core: "core"
```

**Use explicit mode when**:
- You want group names different from package names
- You need glob patterns (future: `cli.*: "cli"`)
- Auto-detection doesn't match your intent

### Common Options

All grouping modes support:

1) `strip_prefix` (optional string)
- Purpose: Remove leading module prefix before grouping
- Example: `"bengal."` → `bengal.cli.templates` becomes `cli.templates`

2) Resolution algorithm (all modes):
- Start with `qualified_name` (e.g., `bengal.cli.templates.blog.template`)
- If configured, strip `strip_prefix` from the start
- Find the longest key in prefix_map that matches (dot-separated prefix)
- Build output path: `{group}/{remaining}.md` (packages to `_index.md`)

## Configuration Examples

### No Grouping (Default)

```yaml
# config/_default/autodoc.yaml
autodoc:
  python:
    enabled: true
    source_dirs: ["../bengal"]
    output_dir: content/api
    # No grouping config = current behavior preserved
```

### Auto Mode (Recommended)

```yaml
# config/_default/autodoc.yaml
autodoc:
  python:
    enabled: true
    source_dirs: ["../bengal"]
    output_dir: content/api
    strip_prefix: "bengal."
    grouping:
      mode: "auto"  # Detects groups from __init__.py files
```

### Explicit Mode (Advanced)

```yaml
# config/_default/autodoc.yaml
autodoc:
  python:
    enabled: true
    source_dirs: ["../bengal"]
    output_dir: content/api
    strip_prefix: "bengal."
    grouping:
      mode: "explicit"
      prefix_map:
        cli.templates: templates
        cli.commands: cli-commands
        cli: cli
        core: core
        cache: cache
        rendering: rendering
        health: health
```

**Notes**:
- Optional. If `grouping` absent, current behavior is unchanged.
- Longest-prefix wins ensures `cli.templates` beats `cli` when both match.
- Auto mode respects Python package structure automatically.

## Implementation Plan

### Phase 1: Core Infrastructure

1) **Config loader** (`bengal/autodoc/config.py`)
   - Add optional keys: `strip_prefix: str | None`, `grouping: dict[str, Any]`
   - Support `grouping.mode: "off" | "auto" | "explicit"`
   - Default: mode="off" (current behavior)

2) **Auto-detection helper** (`bengal/autodoc/utils.py`)
   ```python
   def auto_detect_prefix_map(source_dirs: list[Path], strip_prefix: str = "") -> dict[str, str]:
       """
       Auto-detect grouping from __init__.py hierarchy.

       Returns:
           prefix_map: {"package.path": "group_name"}
       """
       prefix_map = {}
       for source_dir in source_dirs:
           for init_file in source_dir.rglob("__init__.py"):
               package_dir = init_file.parent
               module_parts = package_dir.relative_to(source_dir).parts
               module_name = ".".join(module_parts)

               # Strip prefix if configured
               if strip_prefix and module_name.startswith(strip_prefix):
                   module_name = module_name[len(strip_prefix):]

               # Group name = last component
               group_name = module_parts[-1]
               prefix_map[module_name] = group_name

       return prefix_map
   ```

3) **URL computation** (`PythonExtractor.get_output_path()`)
   - Check if `grouping` config exists
   - If not: use current behavior (unchanged)
   - If mode="auto": call `auto_detect_prefix_map()` once at init
   - If mode="explicit": use `grouping.prefix_map` directly
   - Apply longest-prefix matching to build grouped paths

### Phase 2: Testing

4) **Unit tests** (`tests/unit/test_autodoc_grouping.py`)
   - Test auto-detection algorithm on sample package tree
   - Test longest-prefix matching logic
   - Test strip_prefix with all modes
   - Test no-grouping (default) behavior unchanged

5) **Integration tests** (`tests/integration/test_autodoc_url_grouping.py`)
   - Golden test: Generate docs with no grouping
   - Golden test: Generate docs with auto mode
   - Golden test: Generate docs with explicit mode
   - Verify URL consistency across all modes

### Phase 3: Documentation

6) **Architecture docs** (`architecture/autodoc.md`)
   - Add "URL Grouping" section
   - Document all three modes with examples
   - Explain auto-detection algorithm

7) **Config examples** (`config.example/_default/autodoc.yaml`)
   - Show all three configuration modes
   - Add inline comments explaining tradeoffs

8) **Migration guide** (in RFC or CHANGELOG)
   - Document URL churn when enabling grouping
   - Provide `bengal autodoc --dry-run` command
   - Show redirect generation strategy

## Backward Compatibility

### Zero-Impact Default

**No config change = no behavior change**:
- Existing sites without `grouping` config continue using current URL structure
- No migration required for users who don't need grouping
- 100% backward compatible

### Opt-In Migration

When enabling grouping (auto or explicit):
- **URLs will change** for affected modules
- Existing links and bookmarks break
- Search engine indexes need reindexing

**Mitigation strategies**:
1. **Dry-run mode**: `bengal autodoc --dry-run --show-changes` to preview URL changes
2. **Redirect generation**: Generate `.htaccess` or meta-refresh redirects
3. **Gradual rollout**: Generate both old and new docs temporarily
4. **Clear documentation**: CHANGELOG warns about URL churn

### Migration Example

```yaml
# Before (current behavior)
autodoc:
  python:
    enabled: true
# Result: /api/blog/template/ (inconsistent)

# After (auto mode)
autodoc:
  python:
    strip_prefix: "bengal."
    grouping:
      mode: "auto"
# Result: /api/templates/blog/template/ (consistent)
```

**Recommended migration path**:
1. Run `bengal autodoc --dry-run --show-changes` to see URL diff
2. Review changes and decide if grouping is worth the URL churn
3. Update internal links (autodoc will preserve cross-references automatically)
4. Deploy with redirect rules for external links

## Risks and Mitigations

- URL churn on enablement: Mitigate via clear docs and optional redirect generation.
- Ambiguous mappings: Longest-prefix wins; keep maps short and focused. Provide warnings when multiple prefixes could match if desired.
- Performance: Negligible; simple string checks per element.

## Why Auto Mode is Recommended

**Auto mode respects your existing code structure**:
- No manual maintenance of prefix maps
- Automatically adapts when you add new packages
- Follows Python's own package semantics (via `__init__.py`)
- Makes URL structure predictable: "If it's a package, it's a group"

**Example**: Adding a new subsystem
```python
# Add new package
bengal/analytics/
  __init__.py      # Auto-detects as group "analytics"
  tracker.py       → /api/analytics/tracker/
  events.py        → /api/analytics/events/
```

No config changes needed - autodoc automatically groups under `/api/analytics/`.

**When to use explicit mode instead**:
- Group names differ from package names (`cli.commands` → `cli-reference`)
- Flattening nested packages (`cli.*` → `cli`)
- Non-standard layouts (package structure doesn't match desired URL structure)

## Comparison with Industry Tools

### Sphinx (autodoc + autosummary)

**URL Organization Approach**:
```rst
.. toctree::
   :maxdepth: 2

   api/core
   api/rendering
   api/cli
```

- **Structure**: Manual `toctree` in RST files specifies grouping
- **URL Pattern**: `/api/package.module.html` or `/api/package/module/` (configurable)
- **Grouping Method**: Explicit toctree entries + autosummary templates
- **Pros**:
  - Total control over organization
  - Industry standard (Python ecosystem)
  - Rich cross-referencing
- **Cons**:
  - **Manual maintenance**: Add toctree entry for every new module
  - **RST knowledge required**: Steeper learning curve
  - **Verbose configuration**: Separate `.rst` files for structure

**Example workflow**:
```rst
# docs/api/index.rst
.. autosummary::
   :toctree: generated

   mypackage.core
   mypackage.rendering
   mypackage.cli.templates
```

### MkDocs (mkdocstrings)

**URL Organization Approach**:
```yaml
# mkdocs.yml
nav:
  - API Reference:
    - Core: api/core.md
    - Rendering: api/rendering.md
    - CLI:
      - Templates: api/cli/templates.md
```

```markdown
# docs/api/core.md
::: mypackage.core
    options:
      show_source: false
```

- **Structure**: Manual file creation + `nav` configuration in YAML
- **URL Pattern**: Controlled by file placement (e.g., `docs/api/core.md` → `/api/core/`)
- **Grouping Method**: 100% manual - you create the file structure
- **Pros**:
  - **Complete flexibility**: Organize however you want
  - **Markdown-based**: Easier for many users than RST
  - **Modern themes**: Material theme is beautiful
- **Cons**:
  - **Extremely manual**: Create separate `.md` file for every module/group
  - **Nav maintenance**: Update `mkdocs.yml` for every structural change
  - **Tedious for large APIs**: 50+ modules = 50+ files + nav entries

**Example workflow**:
1. Create `docs/api/cli/templates.md` manually
2. Add `::: mypackage.cli.templates` directive
3. Add to `nav` in `mkdocs.yml`
4. Repeat for every module

### Bengal (This RFC - Auto Mode)

**URL Organization Approach**:
```yaml
# config/_default/autodoc.yaml
autodoc:
  python:
    strip_prefix: "mypackage."
    grouping:
      mode: "auto"  # That's it!
```

- **Structure**: Auto-detected from `__init__.py` hierarchy
- **URL Pattern**: `/api/{group}/{module}/` (e.g., `/api/templates/blog/template/`)
- **Grouping Method**: Respects Python package structure automatically
- **Pros**:
  - ✅ **Zero maintenance**: Adapts to new packages automatically
  - ✅ **Python-aligned**: Follows your existing `__init__.py` structure
  - ✅ **Minimal config**: 2 lines (vs. dozens of toctree/nav entries)
  - ✅ **Predictable**: "If it's a package, it's a group"
  - ✅ **No file creation**: No separate `.md` or `.rst` files needed
- **Cons**:
  - ⚠️ Less flexible than manual approaches (but explicit mode available)
  - ⚠️ Tied to Python package structure (but that's usually desired)

**Example workflow**:
1. Add `__init__.py` to packages (you probably already have these)
2. Enable auto mode in config
3. Done! URLs automatically organized by package hierarchy

### Comparison Matrix

| Feature | Sphinx | MkDocs | Bengal (Auto) | Bengal (Explicit) |
|---------|--------|---------|---------------|-------------------|
| **Config Approach** | Manual toctree | Manual nav + files | Auto-detect | Prefix map |
| **Maintenance** | High (toctree per module) | Very High (file + nav per module) | **Zero** (adapts automatically) | Low (update map when needed) |
| **Learning Curve** | Steep (RST) | Moderate (Markdown + nav) | **Minimal** (2 lines) | Low (simple YAML map) |
| **Flexibility** | High (full control) | Very High (total control) | Moderate (follows packages) | High (custom mappings) |
| **New Module** | Add to toctree | Create file + add to nav | **Automatic** | Automatic (or add to map) |
| **URL Stability** | Depends on toctree | Depends on file placement | **Stable** (follows packages) | Stable (config-driven) |
| **Python Alignment** | Manual alignment | Manual alignment | **Native** (respects __init__.py) | Configurable |

### Bengal's Sweet Spot

**Bengal's auto mode occupies a unique position**:

1. **Lower maintenance than Sphinx**: No toctree, no autosummary templates
2. **Lower maintenance than MkDocs**: No file creation, no nav entries
3. **More automated than both**: Respects existing Python structure
4. **Fallback to control**: Explicit mode when auto isn't enough

**Best for**:
- ✅ Projects that want documentation to mirror code structure
- ✅ Teams that want minimal documentation maintenance
- ✅ Codebases with well-organized packages (`__init__.py` hierarchy)
- ✅ Users who prefer configuration over manual file management

**Not ideal for**:
- ❌ Projects wanting documentation structure completely independent of code
- ❌ Non-Python projects (Sphinx/MkDocs more general-purpose)
- ❌ Complex documentation with extensive narrative content (Bengal is SSG + autodoc, not just docs)

### Real-World Example: Django

**How Django would look in each tool**:

```python
# Django structure
django/
  core/
    __init__.py
    cache.py
    management.py
  db/
    __init__.py
    models.py
    backends/
      __init__.py
      base.py
```

**Sphinx**: Add ~50+ toctree entries across multiple `.rst` files
```rst
.. toctree::
   api/django.core.cache
   api/django.core.management
   api/django.db.models
   api/django.db.backends.base
   # ... repeat for 50+ modules
```

**MkDocs**: Create ~50+ `.md` files + nav entries
```yaml
nav:
  - Core:
    - Cache: api/core/cache.md
    - Management: api/core/management.md
  - Database:
    - Models: api/db/models.md
    - Backends:
      - Base: api/db/backends/base.md
  # ... repeat for 50+ modules
```

**Bengal Auto Mode**: 3 lines of config
```yaml
autodoc:
  python:
    strip_prefix: "django."
    grouping:
      mode: "auto"
# Result: /api/core/cache/, /api/db/backends/base/, etc.
# Automatically grouped by package structure
```

## Alternatives Considered

### Remove `__init__.py` Files
- ❌ Breaks Python imports and tooling
- ❌ Violates Python packaging conventions
- ❌ Forces code changes to fix a docs problem

### Glob-Only Rules (e.g., `cli.*: "cli"`)
- ⚠️ More powerful but verbose
- ⚠️ Harder to reason about (multiple patterns, priority rules)
- ✅ Could add later as explicit mode enhancement

### Hard-Code Subsystem Mappings
- ❌ Inflexible for downstream users
- ❌ Requires code changes when packages added
- ❌ Configuration is preferable

### Manual URL Configuration per Module
- ❌ Too granular (config explosion)
- ❌ Hard to maintain
- ❌ Doesn't scale to large codebases

## Validation Plan

### Automated Testing

1. **Unit tests** for core logic:
   - `test_auto_detect_prefix_map()` - Verify __init__.py scanning
   - `test_longest_prefix_matching()` - Verify grouping algorithm
   - `test_strip_prefix()` - Verify prefix stripping
   - `test_no_grouping_default()` - Verify unchanged default behavior

2. **Integration tests** with golden outputs:
   - Generate Bengal docs with mode="off" (baseline)
   - Generate Bengal docs with mode="auto"
   - Generate Bengal docs with mode="explicit"
   - Compare URL structures and verify consistency

3. **Cross-reference validation**:
   - Verify internal links resolve correctly in all modes
   - Check that `See Also` references point to correct URLs
   - Ensure inheritance links (base classes) work

### Manual Validation (Bengal Site)

1. **Before/after comparison**:
   ```bash
   # Generate current structure
   bengal autodoc
   find site/content/api -name "*.md" | sort > before.txt

   # Enable auto mode
   # Update config/_default/autodoc.yaml

   # Generate new structure
   bengal autodoc
   find site/content/api -name "*.md" | sort > after.txt

   # Review diff
   diff before.txt after.txt
   ```

2. **URL consistency check**:
   - All `bengal/cli/templates/*` → `/api/templates/*` ✅
   - All `bengal/core/*` → `/api/core/*` ✅
   - All `bengal/cache/*` → `/api/cache/*` ✅

3. **Click-through QA**:
   - Browse `/api/templates/` - verify blog/ subdirectory appears
   - Click into `/api/templates/blog/template/` - verify renders correctly
   - Check sidebar navigation - verify hierarchy is correct
   - Test search - verify new URLs indexed

4. **Template selection**:
   - Verify package `_index.md` files still act as section indexes
   - Check that proper templates applied (with sidebars for docs)

## Rollout Strategy

### Phase 1: Implementation (Week 1-2)
- ✅ Implement auto-detection algorithm
- ✅ Add config support for all three modes
- ✅ Update `PythonExtractor.get_output_path()` with grouping logic
- ✅ Write comprehensive test suite
- ✅ Document in `architecture/autodoc.md`

### Phase 2: Internal Testing (Week 2)
- ✅ Enable auto mode on Bengal's own site
- ✅ Review URL changes and consistency
- ✅ Fix any cross-reference issues
- ✅ Verify search indexing works

### Phase 3: Documentation (Week 3)
- ✅ Update `config.example/_default/autodoc.yaml` with all modes
- ✅ Add migration guide to CHANGELOG
- ✅ Document `--dry-run` flag usage
- ✅ Create redirect generation helper script

### Phase 4: Release (Week 3-4)
- ✅ Merge to main with comprehensive CHANGELOG entry
- ✅ Announce in release notes with examples
- ✅ Publish updated Bengal docs site with grouped URLs
- ✅ Monitor issues and provide support

### CHANGELOG Entry (Draft)

```markdown
## [v0.X.0] - 2025-XX-XX

### Added

- **Autodoc URL Grouping**: New opt-in feature for consistent API doc URLs
  - `mode: "auto"` (recommended) - Auto-detect groups from package structure
  - `mode: "explicit"` - Manual prefix mapping for custom layouts
  - `mode: "off"` (default) - Current behavior unchanged
  - No impact on existing sites unless explicitly enabled

  Example configuration:
  ```yaml
  autodoc:
    python:
      strip_prefix: "mypackage."
      grouping:
        mode: "auto"  # Respects __init__.py hierarchy
  ```

  See `config.example/_default/autodoc.yaml` for detailed examples.

### Breaking Changes

- None (grouping is opt-in)

### Migration Notes

- Enabling grouping changes API doc URLs - preview with `--dry-run`
- Internal cross-references update automatically
- External links may need redirects (see migration guide)
```

## Appendix: Current Configuration Reference (excerpts)

```24:43:/Users/llane/Documents/github/python/bengal/site/bengal.toml
[autodoc.python]
enabled = true
source_dirs = ["../bengal"]
output_dir = "content/api"
docstring_style = "auto"
# Member visibility
include_private = false
include_special = false
```
