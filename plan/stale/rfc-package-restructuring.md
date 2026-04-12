# RFC: Package Restructuring

**Status**: Draft  
**Author**: AI Assistant  
**Created**: 2026-01-15  
**Updated**: 2026-01-15  
**Python Version**: 3.14  
**Related**: rfc-build-system-package.md (companion RFC)

---

## Executive Summary

This RFC follows the `build/` package extraction (see rfc-build-system-package.md). Once the build RFC lands, Bengal has several packages that need restructuring to improve cohesion and clarity. This RFC proposes:

1. **Split**: `rendering/parsers/` → `parsing/` (61 files; `rendering/` total 170)
2. **Split**: `cli/templates/` → `scaffolds/` (57 files; 38 content files)
3. **Merge**: `discovery/` + `content_layer/` → `content/` (10 + 10 files)
4. **Optional**: `cli/dashboard/` → `tui/` (23 files)

**Key Principle**: Packages should have single, clear responsibilities. Split large packages with distinct concerns; merge small packages with overlapping concerns.

**Counts**: This RFC measures file counts with `find` and excludes `__pycache__` in the current repository state.

---

## Goals and Non-Goals

### Goals

1. **Clear Package Boundaries**: Each package has a single, well-defined responsibility
2. **Appropriate Package Sizes**: Split large packages (50+ files) with distinct concerns
3. **Conceptual Clarity**: Related code lives together
4. **Improved Testability**: Isolated packages are easier to test independently
5. **Backward Compatibility**: Old imports continue working via re-exports

### Non-Goals

1. **API Changes**: Public interfaces remain stable
2. **Behavior Changes**: Code location changes, not functionality
3. **Performance Optimization**: Focus is organization, not speed
4. **Complete Overhaul**: This RFC addresses packages with clear issues

---

## Analysis: Current Package Structure

### Package Size Distribution

| Package | Files | Status |
|---------|-------|--------|
| `themes/` | 448 | ✅ Fine (static assets) |
| `rendering/` | 170 | ⚠️ Large, mixed concerns |
| `cli/` | 147 | ⚠️ Large, mixed concerns |
| `core/` | 56 | ✅ Fine (well-organized subpackages) |
| `orchestration/` | 55 | ⚠️ Addressed by build/ RFC |
| `directives/` | 47 | ✅ Fine (cohesive purpose) |
| `health/` | 46 | ✅ Fine (validators are cohesive) |
| `utils/` | 41 | ✅ Fine (standard utility pattern) |
| `cache/` | 37 | ⚠️ Addressed by build/ RFC |
| `autodoc/` | 33 | ✅ Fine (self-contained) |
| `discovery/` | 10 | ⚠️ Overlaps with content_layer |
| `content_layer/` | 10 | ⚠️ Overlaps with discovery |

---

## Proposal 1: Split `rendering/parsers/` → `parsing/`

### Current Structure

```
rendering/ (170 files)
├── parsers/                    # 61 files - markdown + HTML parsing
│   ├── patitas/               # 51 files
│   │   ├── ast_handler.py
│   │   ├── block_handler.py
│   │   ├── document_builder.py
│   │   └── ...
│   ├── mistune/               # 5 files
│   ├── native_html.py
│   ├── python_markdown.py
│   └── factory.py
├── engines/                    # Template engines
├── template_functions/         # 41 files
├── pipeline/                   # Render pipeline
└── ...
```

### Problem

`parsers/` is **larger than several top-level packages** (61 files vs `discovery/` at 10 files and `content_layer/` at 10 files). It has **distinct concerns** from template rendering:

- **Parsing**: Converting markdown/HTML to AST (input processing)
- **Rendering**: Converting AST + templates to HTML (output generation)

These are different stages with different dependencies:
- Parsing depends on: markdown syntax, AST types
- Rendering depends on: templates, Jinja, context

### Evidence

- Parser engines and unified parser API are defined in `bengal/rendering/parsers/__init__.py:1-40`.
- AST types and utilities live in `bengal/rendering/ast_types.py:1-35` and `bengal/rendering/ast_utils.py:1-38`.
- Template engine responsibilities live in `bengal/rendering/engines/jinja.py:1-35`.

### Proposed Structure

```
bengal/
├── parsing/                    # NEW - size to be measured after move
│   ├── __init__.py            # Public API
│   ├── ast/                   # AST types and transforms
│   │   ├── __init__.py
│   │   ├── types.py          # From rendering/ast_types.py
│   │   ├── utils.py          # From rendering/ast_utils.py
│   │   └── transforms.py     # From rendering/ast_transforms.py
│   ├── backends/              # Parser backends
│   │   ├── __init__.py
│   │   ├── patitas/          # From rendering/parsers/patitas/
│   │   ├── mistune/          # From rendering/parsers/mistune/
│   │   └── native_html.py    # From rendering/parsers/native_html.py
│   └── factory.py             # From rendering/parsers/factory.py
│
└── rendering/                  # REDUCED - parsers moved out
    ├── engines/               # Template engines
    ├── template_functions/    # Template functions
    ├── pipeline/              # Render pipeline
    ├── context/               # Template context
    └── ...
```

### Migration

**Phase 1: Create Package**
1. Create `bengal/parsing/__init__.py`
2. Copy `rendering/ast_*.py` → `parsing/ast/`
3. Copy `rendering/parsers/` → `parsing/backends/`

**Phase 2: Update Imports**
4. Add re-exports in `rendering/parsers/__init__.py`
5. Update internal imports across codebase
6. Run tests to verify

**Phase 3: Cleanup (next minor version)**
7. Remove re-exports
8. Delete old `rendering/parsers/` directory

### Benefits

1. **Clear Separation**: Parsing (input) vs rendering (output)
2. **Independent Testing**: Test parsers without template dependencies
3. **Potential Extraction**: `parsing/` could become standalone package
4. **Smaller Packages**: Both packages more focused

### Backward Compatibility

```python
# Old imports (deprecated, still work)
from bengal.parsing import MarkdownParser
from bengal.parsing.ast.types import ASTNode

# New imports (preferred)
from bengal.parsing import MarkdownParser
from bengal.parsing.ast import ASTNode
```

---

## Proposal 2: Split `cli/templates/` → `scaffolds/`

### Current Structure

```
cli/ (147 files)
├── commands/                   # CLI commands
├── dashboard/                  # TUI dashboard
├── helpers/                    # CLI utilities
├── templates/                  # Site starter templates (57 files)
│   ├── __init__.py
│   ├── base.py
│   ├── registry.py
│   ├── blog/
│   │   ├── __init__.py
│   │   ├── pages/
│   │   │   ├── about.md
│   │   │   ├── index.md
│   │   │   └── posts/
│   │   │       ├── first-post.md
│   │   │       └── second-post.md
│   │   ├── skeleton.yaml
│   │   └── template.py
│   ├── docs/
│   │   ├── __init__.py
│   │   ├── pages/
│   │   │   ├── _index.md
│   │   │   ├── api/
│   │   │   │   └── _index.md
│   │   │   ├── getting-started/
│   │   │   │   ├── _index.md
│   │   │   │   ├── index.md
│   │   │   │   ├── installation.md
│   │   │   │   └── quickstart.md
│   │   │   ├── guides/
│   │   │   │   └── _index.md
│   │   │   └── index.md
│   │   ├── skeleton.yaml
│   │   └── template.py
│   ├── portfolio/
│   ├── product/
│   ├── resume/
│   └── ...
└── ...
```

### Problem

`cli/templates/` contains **content scaffolds** (markdown files, YAML configuration files), not CLI code. The `bengal new` command uses these, but they have different concerns:

- **CLI**: Command parsing, user interaction, error handling
- **Scaffolds**: Content structure, default configurations, sample pages

The scaffolds are **data artifacts**, not executable code.

### Evidence

- Template discovery and registry logic lives in `bengal/cli/templates/registry.py:1-79`.
- Content files are present in template directories (example: `bengal/cli/templates/blog/pages/index.md:1-15`).
- Template skeleton manifests exist (example: `bengal/cli/templates/blog/skeleton.yaml:1-20`).

Counts (excluding `__pycache__`) from the current repository:

```bash
find bengal/cli/templates -type f -not -path "*/__pycache__/*" | wc -l
57

find bengal/cli/templates -type f -not -path "*/__pycache__/*" -name "*.md" | wc -l
31

find bengal/cli/templates -type f -not -path "*/__pycache__/*" -name "*.yaml" | wc -l
7

find bengal/cli/templates -type f -not -path "*/__pycache__/*" -name "*.py" | wc -l
19
```

38 of 57 files are **content** (`.md` + `.yaml`), not code.

### Proposed Structure

```
bengal/
├── scaffolds/                  # NEW - site starter templates
│   ├── __init__.py
│   ├── base.py                # Base scaffold class
│   ├── registry.py            # Scaffold registry
│   ├── blog/
│   │   ├── __init__.py
│   │   ├── scaffold.py        # BlogScaffold class
│   │   ├── content/           # Template content
│   │   │   ├── _index.md
│   │   │   └── ...
│   │   └── config.yaml
│   ├── docs/
│   ├── portfolio/
│   ├── product/
│   └── resume/
│
└── cli/                        # REDUCED - commands focused
    ├── commands/
    │   ├── new.py             # Uses bengal.scaffolds
    │   └── ...
    ├── dashboard/
    └── helpers/
```

### Migration

**Phase 1: Create Package**
1. Create `bengal/scaffolds/__init__.py`
2. Move `cli/templates/` → `scaffolds/`
3. Rename template-specific code to scaffold-specific

**Phase 2: Update References**
4. Update `cli/commands/new.py` to import from `scaffolds`
5. Add re-exports in `cli/templates/__init__.py`
6. Run tests

**Phase 3: Cleanup (next minor version)**
7. Remove re-exports
8. Delete old `cli/templates/` directory

### Benefits

1. **CLI Focused**: CLI package only does command handling
2. **Extensibility**: Users could potentially add custom scaffold packages
3. **Clear Purpose**: "scaffolds" is more descriptive than "templates"
4. **Independent Testing**: Test scaffolds without CLI dependencies

### Backward Compatibility

```python
# Old imports (deprecated, still work)
from bengal.scaffolds import BlogTemplate

# New imports (preferred)
from bengal.scaffolds import BlogScaffold
```

**Note**: We also rename "Template" → "Scaffold" to avoid confusion with Jinja templates.

---

## Proposal 3: Merge `discovery/` + `content_layer/` → `content/`

### Current Structure

```
discovery/ (10 files)
├── __init__.py
├── asset_discovery.py
├── content_discovery.py
├── section_builder.py
└── ...

content_layer/ (10 files)
├── __init__.py
├── entry.py
├── loaders.py
├── manager.py
├── source.py
├── sources/
│   ├── __init__.py
│   ├── github.py
│   ├── local.py
│   ├── notion.py
│   └── rest.py
└── ...
```

### Problem

These packages have **overlapping responsibilities**:

| discovery/ | content_layer/ | Overlap |
|------------|----------------|---------|
| Finding content files | Defining content sources | Where content comes from |
| Asset discovery | Content loading | Getting content |
| Section structure | Content protocols | Content contracts |

Both deal with "content acquisition" - finding and loading content.

### Evidence

- Discovery is responsible for finding and parsing site content files (`bengal/discovery/content_discovery.py:1-105`).
- Content sources define how content is fetched and normalized (`bengal/content_layer/source.py:1-70`).
- Loader factory functions expose user-facing content loaders (`bengal/content_layer/loaders.py:1-57`).

### Proposed Structure

```
bengal/
└── content/                    # MERGED - size to be measured after move
    ├── __init__.py
    ├── discovery/              # Where content is found
    │   ├── __init__.py
    │   ├── content.py         # Content file discovery
    │   ├── assets.py          # Asset discovery
    │   └── sections.py        # Section discovery
    ├── sources/                # How content is loaded
    │   ├── __init__.py
    │   ├── local.py           # File-based sources
    │   ├── github.py          # GitHub sources
    │   ├── notion.py          # Notion sources
    │   ├── rest.py            # REST sources
    │   └── loaders.py         # Content loaders
    └── types.py                # Content type definitions
```

### Migration

**Phase 1: Create Package**
1. Create `bengal/content/__init__.py`
2. Move `discovery/` → `content/discovery/`
3. Move `content_layer/` → `content/sources/`

**Phase 2: Update Imports**
4. Add re-exports in old packages
5. Update internal imports
6. Run tests

**Phase 3: Cleanup (next minor version)**
7. Remove old packages

### Benefits

1. **Conceptual Clarity**: Single package for "content acquisition"
2. **Clearer Imports**: `from bengal.content import discover, load`
3. **Reduced Navigation**: Related code in one place

### Backward Compatibility

```python
# Old imports (deprecated, still work)
from bengal.content.discovery import discover_content
from bengal.content.sources import ContentSource

# New imports (preferred)
from bengal.content.discovery import discover_content
from bengal.content.sources import ContentSource
```

---

## Proposal 4 (Optional): Split `cli/dashboard/` → `tui/`

### Current Structure

```
cli/
├── commands/           # CLI commands
├── dashboard/          # TUI dashboard (23 files)
│   ├── __init__.py
│   ├── app.py         # Textual App
│   ├── widgets/       # Custom widgets (11 files)
│   ├── screens.py
│   └── ...
└── helpers/
```

### Problem

The dashboard is a **Textual TUI application** embedded in `cli/`:
- Textual app entrypoint and bindings are defined in `bengal/cli/dashboard/app.py:1-95`.

### Considerations

**For splitting**:
- Dashboard could be optional (don't require Textual if not using TUI)
- Dashboard has its own complexity (widgets, screens, state)
- Textual apps often grow; having own package gives room

**Against splitting**:
- Dashboard shares CLI concepts (commands, site loading)
- Tight integration is a feature
- Extra package maintenance overhead

### Recommendation

**Soft recommendation**: Consider splitting if:
1. Dashboard grows beyond the current 23 files
2. Users request optional dashboard
3. Dashboard needs independent release cycle

**For now**: Keep in `cli/` but prepare for eventual extraction by:
- Minimizing imports from `cli.dashboard` → `cli.commands`
- Using clear interfaces between dashboard and CLI

---

## Implementation Plan

**Prerequisite**: Implement this RFC after rfc-build-system-package.md is merged and released.

### Phase 1: Parsing Package

**Tasks**:
1. Create `bengal/parsing/__init__.py`
2. Create `bengal/parsing/ast/` with types, utils, transforms
3. Create `bengal/parsing/backends/` with patitas, mistune, native_html
4. Add re-exports in `rendering/parsers/__init__.py`
5. Update internal imports
6. Run full test suite

**Deliverables**:
- `bengal/parsing/` package
- Tests passing
- Re-exports working

### Phase 2: Scaffolds Package

**Tasks**:
1. Create `bengal/scaffolds/__init__.py`
2. Move templates and rename to scaffolds
3. Update `cli/commands/new.py`
4. Add re-exports in `cli/templates/__init__.py`
5. Update documentation

**Deliverables**:
- `bengal/scaffolds/` package
- `bengal new` command working
- Re-exports working

### Phase 3: Content Package

**Tasks**:
1. Create `bengal/content/__init__.py`
2. Create `bengal/content/discovery/` from `discovery/`
3. Create `bengal/content/sources/` from `content_layer/`
4. Add re-exports in old packages
5. Update internal imports

**Deliverables**:
- `bengal/content/` package
- Re-exports working
- Tests passing

### Phase 4: Cleanup (next minor release)

**Tasks**:
1. Add deprecation warnings on old imports
2. Update external documentation
3. Remove re-exports (next minor version)
4. Delete old directories

---

## Dependency Graph (Post-Migration)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         DEPENDENCY FLOW (POST-MIGRATION)                     │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  bengal/core/          ◄─────────────────────────────────────┐              │
│  ├── site/             Models                                │              │
│  ├── page/                                                   │              │
│  └── section/                                                │              │
│                                                              │              │
│  bengal/parsing/       ◄─────────────────┐                   │              │
│  ├── ast/              Markdown to AST   │                   │              │
│  └── backends/                           │                   │              │
│                                          │                   │              │
│  bengal/content/       ◄─────────────────┤  ◄────────────────┤              │
│  ├── discovery/        Finding content   │                   │              │
│  └── sources/          Loading content   │                   │              │
│                                          │                   │              │
│  bengal/rendering/     ◄─────────────────┘                   │              │
│  ├── engines/          Template rendering                    │              │
│  └── pipeline/                                               │              │
│                                          │                   │              │
│  bengal/scaffolds/     ◄─────────────────┘                   │              │
│  └── blog/, docs/...   Site starters                         │              │
│                                                              │              │
│  bengal/cli/           ◄─────────────────────────────────────┘              │
│  ├── commands/         Uses scaffolds, orchestration                        │
│  └── dashboard/                                                             │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Testing Strategy (planned additions)

### Unit Tests (to add)
- `tests/unit/parsing/` for parser factory + backend selection
- `tests/unit/scaffolds/` for scaffold registry + skeleton parsing
- `tests/unit/content/` for discovery + content_layer source adapters

### Integration Tests (to add)
- `tests/integration/` for legacy import re-exports (parsing, scaffolds, discovery, content_layer)

---

## Risks and Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Import breakage | High | Medium | Re-exports with deprecation warnings |
| Test failures | High | Low | Run full test suite at each phase |
| Circular imports | Medium | High | Strict dependency direction |
| External plugin breakage | Low | Medium | Document migration, long deprecation period |

---

## Success Criteria

### Phase 1 Complete (Parsing)
- [ ] `bengal/parsing/` package exists
- [ ] All parser tests pass
- [ ] Old imports work via re-exports

### Phase 2 Complete (Scaffolds)
- [ ] `bengal/scaffolds/` package exists
- [ ] `bengal new` command works
- [ ] Old imports work via re-exports

### Phase 3 Complete (Content)
- [ ] `bengal/content/` package exists
- [ ] `discovery/` and `content_layer/` merged
- [ ] Old imports work via re-exports

### Phase 4 Complete (Cleanup)
- [ ] Deprecation warnings on old imports
- [ ] Documentation updated
- [ ] Old directories ready for removal

---

## Summary: Package Structure (Baseline + Proposed)

### Baseline (current repository, counts exclude `__pycache__`)

- `rendering/`: 170 files
- `rendering/parsers/`: 61 files
- `cli/`: 147 files
- `cli/templates/`: 57 files
- `cli/dashboard/`: 23 files
- `discovery/`: 10 files
- `content_layer/`: 10 files

### Proposed (post-RFC)

- **New packages**: `parsing/`, `scaffolds/`, `content/`
- **Removed packages**: `discovery/`, `content_layer/` (merged into `content/`)
- **Reduced packages**: `rendering/`, `cli/` (parsers/templates moved out)

---

## References

- `plan/rfc-build-system-package.md` - Companion RFC for build/ extraction
- `bengal/rendering/parsers/` - Current parser location
- `bengal/cli/templates/` - Current scaffold location
- `bengal/discovery/` - Current discovery package
- `bengal/content_layer/` - Current content layer package

---

## Appendix A: File Inventory

### Files to Create

```
bengal/parsing/
├── __init__.py
├── ast/
│   ├── __init__.py
│   ├── types.py
│   ├── utils.py
│   └── transforms.py
├── backends/
│   ├── __init__.py
│   ├── patitas/          # 51 files
│   ├── mistune/          # 5 files
│   └── native_html.py
└── factory.py

bengal/scaffolds/
├── __init__.py
├── base.py
├── registry.py
├── blog/
├── changelog/
├── docs/
├── landing/
├── portfolio/
├── product/
└── resume/

bengal/content/
├── __init__.py
├── discovery/
│   ├── __init__.py
│   └── ... (from discovery/)
└── sources/
    ├── __init__.py
    └── ... (from content_layer/)
```

### Files to Move

| From | To |
|------|-----|
| `rendering/ast_types.py` | `parsing/ast/types.py` |
| `rendering/ast_utils.py` | `parsing/ast/utils.py` |
| `rendering/ast_transforms.py` | `parsing/ast/transforms.py` |
| `rendering/parsers/patitas/` | `parsing/backends/patitas/` |
| `rendering/parsers/mistune/` | `parsing/backends/mistune/` |
| `rendering/parsers/native_html.py` | `parsing/backends/native_html.py` |
| `rendering/parsers/factory.py` | `parsing/factory.py` |
| `cli/templates/` | `scaffolds/` |
| `discovery/` | `content/discovery/` |
| `content_layer/` | `content/sources/` |

### Files to Delete (After Deprecation Period)

| Directory | Reason |
|-----------|--------|
| `rendering/parsers/` | Moved to `parsing/` |
| `cli/templates/` | Moved to `scaffolds/` |
| `discovery/` | Merged into `content/` |
| `content_layer/` | Merged into `content/` |
