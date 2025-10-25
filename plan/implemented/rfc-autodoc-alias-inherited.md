## RFC: Autodoc Alias Detection and Inherited Member Controls

### Summary
Add AST-only alias detection and configurable inherited member display to Bengal Autodoc. This closes key parity gaps with Sphinx while preserving Bengal’s robustness and performance. The feature introduces minimal configuration, surfaces aliases and inheritance clearly in templates, and ships with comprehensive tests and docs.

### Goals
- Treat simple assignment aliases (alias = original) as documented symbols with provenance.
- Allow users to include/exclude inherited members in class documentation, with per-type overrides.
- Maintain AST-only extraction (no runtime imports) and good performance.
- Provide clear UX in generated docs (badges/sections) and stable URL structure.

### Non-goals
- Complex alias analysis across dynamic assignments or runtime rebinding.
- Full MRO resolution across third-party libraries not present in documented source.
- Emitting duplicate pages for aliases; aliases should point to canonical docs.

### User Stories
- As a maintainer, when I write `public_api = _internal_impl`, autodoc should document `public_api` and indicate it’s an alias of `_internal_impl`.
- As a library user, I want to optionally see inherited methods listed under a class, labeled with their origin base.
- As a doc author, I can disable inherited members to declutter pages or enable them for completeness.

### Configuration Design
New keys under `[autodoc.python]` (default values shown):

```toml
[autodoc.python]
# Existing
enabled = true
include_private = false
include_special = false

# New
include_inherited = false              # Global toggle
include_inherited_by_type = {          # Per-element overrides
  class = false,                       # Show inherited methods/attributes on classes
  exception = false                    # Future-friendly; same behavior as class
}

# Alias rendering strategy for assignment aliases
# - "canonical": only canonical element gets the full doc; aliases get short entries linking to canonical
# - "duplicate": render full doc under alias (risks duplication/divergence)
# - "list-only": record aliases but only list them on the canonical page
alias_strategy = "canonical"
```

Notes:
- Defaults keep current output stable (no inherited members) and avoid duplication.
- Users can enable inherited globally or just for classes via `include_inherited_by_type.class = true`.

### Extraction Design
Alias Detection (module scope):
- Detect patterns: `ast.Assign` where each target is `ast.Name` and value is `ast.Name | ast.Attribute`.
- Build an alias map for the module: `alias_name -> qualified_original` if original is defined in the same extraction corpus.
- Emit a `DocElement` for the alias with `metadata.alias_of = qualified_original` and `metadata.alias_kind = "assignment"`.
- For `alias_strategy = "canonical"`, the alias element is a lightweight entry that links to the canonical element’s anchor; canonical element lists its aliases.

Inherited Members (class scope):
- Build an in-memory index: `qualified_name -> class DocElement` during extraction of a directory.
- For each class with `include_inherited` enabled (effective after merging global + per-type), compute its base class list (already captured as strings) and look up base classes present in the corpus.
- For each base class found, copy method/property signatures into the derived class as synthetic children with metadata:
  - `metadata.inherited_from = qualified_base`
  - `metadata.synthetic = true`
  - `metadata.visibility = "public" | "private"` inferred from name pattern
- Do not duplicate full docstrings by default; provide short description like “Inherited from Base.method”.
- Avoid collisions: if the derived class overrides a member, do not add inherited copy.

Edge Handling:
- If a base class is not present in the corpus (e.g., stdlib), skip silently; optionally surface a note count in metadata.
- Respect `include_private = false` by filtering inherited private names (leading underscore) unless overridden.

### Template Updates
- Module/class templates: show an “Alias of …” badge next to alias items; canonical pages include an “Also known as” list.
- Class template: add an “Inherited members” collapsible section. Group by `inherited_from` base class.
- Allow theme hooks to style badges/sections; keep default neutral.

### URL and Navigation
- Canonical URLs remain based on canonical qualified names. Aliases do not create new pages by default; they produce anchors/short entries linking to the canonical page.
- Optional: expose alias anchors as redirect stubs if a site wants old aliases to resolve (out of scope for MVP).

### Testing Plan
Unit tests:
- Alias extraction: module with `def f(); g = f; h = mod.f` yields alias entries; metadata.alias_of set; canonical lists aliases.
- Inherited extraction: `class A: def m()` and `class B(A)`; with inheritance off → only own members; with on → includes `A.m` as inherited with `inherited_from`.
- Config merge precedence: per-type override beats global; private filtering respected.

Integration tests:
- Snapshot pages for a small package demonstrating alias badges and inherited sections.
- Ensure templates hide inherited members when disabled and show when enabled.

Performance tests:
- Measure extraction time delta on medium repo; target <5% overhead with inheritance on; ~0% when off.

### Migration/Docs
- Update configuration reference with new keys and examples.
- Add examples to showcase site demonstrating both modes.
- Provide guidance on choosing alias strategy.

### Risks and Mitigations
- Duplicate/confusing output if aliases render full docs → default to "canonical" strategy.
- Large inherited sections could overwhelm pages → off by default; collapsible UI; per-type toggle.
- Cross-module base resolution may miss third-party bases → document limitation; consider stubs later.

### Rollout
- Phase 1: Extraction + canonical alias strategy, inherited listing (off by default).
- Phase 2: Add optional redirect stubs for aliases (if demanded).

### Implementation Outline
1) Extend `bengal.autodoc.extractors.python.PythonExtractor`:
   - Build module-level alias map from `ast.Assign`.
   - Add alias elements and wire to canonical.
   - Build a class index and synthesize inherited members when enabled.
2) Update Jinja templates for Python autodoc.
3) Add configuration keys parsing and defaults.
4) Tests: unit + integration snapshots.
5) Docs: README and examples.
