Title: RFC: Configurable Autodoc URL Grouping via Prefix Mapping
Status: Draft
Author: Bengal Team
Date: 2025-10-25
Version: 1

## Problem Statement

The Python autodoc currently derives module-to-URL mappings from the deepest package containing an `__init__.py`. This leads to inconsistent, code-structure-driven URL roots. For example, items under `bengal/cli/templates/base.py` and `registry.py` appear under `/api/templates/`, while template-specific modules like `bengal/cli/templates/blog/template.py` appear at top-level as `/api/blog/template/`.

Users expect human-oriented, consistent grouping (e.g., all templates under `/api/templates/...`), stable across refactors. The current behavior makes URL layout depend on internal package details rather than intent.

## Goals

- Provide explicit, configurable grouping of autodoc URLs independent of Python package layout.
- Keep default behavior backward compatible unless configuration is provided.
- Offer simple, minimal configuration that most users can understand and maintain.
- Preserve Python packaging (do not require removing `__init__.py`).

## Non-Goals

- Rewriting import/package structure.
- Implementing a complex rules engine as the only path (we will prefer a small prefix map, with globs as optional).

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

Introduce two optional, minimal configuration knobs to control URL grouping while preserving backward compatibility:

1) `strip_prefix` (string)
- Purpose: Remove a leading module prefix for display/path purposes.
- Example: `"bengal."` → `bengal.cli.templates.blog.template` becomes `cli.templates.blog.template`.

2) `grouping.prefix_map` (object: prefix → group name)
- Purpose: Map the leftmost matching module prefix to a fixed top-level URL root. Longest-prefix wins.
- Example mapping:
  - `"cli.templates" = "templates"`
  - `"cli" = "cli"`
  - `"core" = "core"`
  - `"cache" = "cache"`
  - `"rendering" = "rendering"`

Resolution algorithm (per element/module):
- Start with `qualified_name` (e.g., `bengal.cli.templates.blog.template`).
- If configured, strip `strip_prefix` from the start.
- Find the longest key in `grouping.prefix_map` that is a prefix of the remaining name (dot-separated). If found, set `group = mapping[key]` and remove that prefix from the remaining name; else, no grouping.
- Build output path as:
  - If grouped: `group/<remaining>.md` (packages to `_index.md` as today)
  - Else: current behavior.

Examples:
- `bengal.cli.templates.blog.template` → strip `bengal.` → `cli.templates.blog.template` → prefix `cli.templates` → group `templates` → `/api/templates/blog/template/`.
- `bengal.cli.templates.registry` → `/api/templates/registry/`.
- `bengal.core.site` → group `core` → `/api/core/site/`.

## Configuration (TOML)

```toml
[autodoc.python]
# Existing options ...
strip_prefix = "bengal."

[autodoc.python.grouping.prefix_map]
"cli.templates" = "templates"
"cli" = "cli"
"core" = "core"
"cache" = "cache"
"rendering" = "rendering"
"health" = "health"
```

Notes:
- Optional. If fields are absent, current behavior is unchanged.
- Longest-prefix wins ensures `cli.templates` beats `cli` when both match.

## Implementation Plan

1) Config loader (`bengal/autodoc/config.py`)
- Add optional keys: `strip_prefix: str | None`, `grouping: { prefix_map: dict[str, str] }`.
- Provide defaults (None / empty map).

2) URL computation (Extractor or dedicated helper)
- Add a small helper in `PythonExtractor` (or a shared autodoc utility) to compute the display path from `qualified_name` using the config above.
- Apply this only in `get_output_path()` before building the file path; keep the rest of extraction logic unchanged.

3) Tests
- Unit tests for prefix resolution (strip, longest-prefix selection, no-match).
- Golden tests for a small module tree demonstrating grouped vs. default behavior.

4) Docs
- Update architecture/autodoc.md to describe URL grouping.
- Add examples in `bengal.toml.example`.

## Backward Compatibility

- Default behavior preserved when new config fields are absent.
- Enabling grouping changes output paths and URLs; document this as an opt-in feature.
- Optionally provide a redirect helper script for sites wanting to preserve legacy URLs (out of scope for this RFC, can be a follow-up).

## Risks and Mitigations

- URL churn on enablement: Mitigate via clear docs and optional redirect generation.
- Ambiguous mappings: Longest-prefix wins; keep maps short and focused. Provide warnings when multiple prefixes could match if desired.
- Performance: Negligible; simple string checks per element.

## Alternatives Considered

- Remove `__init__.py` to force higher package root: brittle, affects imports and tooling.
- Glob-only rules: more power but verbose; keep as optional escape hatch if needed later.
- Hard-code subsystem mappings: inflexible for downstream users; configuration is preferable.

## Validation Plan

- Run autodoc on Bengal with and without grouping; compare directory structures under `site/content/api`.
- Click-through QA: `/api/templates/*` pages render and cross-links remain correct.
- Ensure TOC and sidebars still resolve (package `_index.md` behavior unchanged).

## Rollout

- Implement behind optional config flags.
- Update `bengal.toml.example` and site docs.
- Announce in CHANGELOG with examples.

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
