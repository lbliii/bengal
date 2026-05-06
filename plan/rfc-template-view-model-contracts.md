# Template View Model Contracts

**Status**: Draft
**Created**: 2026-05-06
**Scope**: Rendering, Kida, themes, directives, shortcodes, content types

## Problem

Bengal has enough Kida and rendering infrastructure to support richer themes,
but too many surfaces still depend on theme-local HTML expectations instead of
clear data contracts. Directives, shortcodes, autodocs, indexes, notebooks,
tutorial flows, tracks, and reference hubs can leak presentation choices into
the parser, renderer, or theme.

That makes the default theme harder to migrate, makes Chirp UI adoption feel
like wrapping old Bengal markup, and keeps bring-your-own template engines from
having a universal contract to consume.

## Direction

Bengal should normalize content into engine-neutral view data before templates
render it:

```text
source syntax -> parsed semantic node -> template view model -> template engine
```

Kida is the first-class engine Bengal ships, but the contract should be plain
Python data: dictionaries, lists, strings, numbers, booleans, URLs, and explicit
safe-HTML fields when HTML is the actual value. Template engines should not need
to understand parser internals, shortcode implementation details, or Bengal's
default theme layout dialect.

Content type templates own information architecture. Theme systems such as
Chirp UI own interface grammar. Bengal's job is to hand either one a stable data
shape.

## Goals

- Define reusable template view models for directives, shortcodes, content
  types, resource indexes, REST autodocs, notebooks, tutorials, tracks, and
  reference hubs.
- Keep those view models presentation-neutral enough for Kida, Jinja, or a
  future template engine adapter.
- Make risky template data explicit: safe HTML, raw source, URLs, headings,
  asset references, diagnostics, and provenance should be named fields.
- Let the default theme keep working through compatibility shims while new
  surfaces migrate to view models.
- Add generated manifests and documentation checks so view contracts do not
  drift from implementation.

## Non-Goals

- Do not remove the default theme's existing HTML paths in the first wave.
- Do not change public plugin protocols, config keys, CLI commands, or template
  helper names without the constitution's stop-and-ask step.
- Do not move rendering behavior back into `bengal/core/`.
- Do not make Kida-specific syntax the contract. Kida consumes the contract; it
  is not the contract.

## Proposed Contract Shape

Each renderable concept should have a small descriptor and a serializable view
shape. A descriptor names the concept, its maturity, fields, allowed variants,
required assets, safe-HTML fields, and diagnostics.

Illustrative shape:

```python
{
    "kind": "directive.admonition",
    "schema": "bengal-template-view@1",
    "variant": "warning",
    "title": "Watch the cache key",
    "body_html": "<p>...</p>",
    "body_text": "Watch the cache key ...",
    "attrs": {"collapsible": False},
    "provenance": {"source_path": "docs/cache.md", "line": 42},
    "assets": [],
}
```

Field conventions:

- `*_html` fields are already rendered HTML and must be explicitly marked safe
  at the template boundary.
- `*_text` fields are plain text fallbacks for search, previews, and summaries.
- `assets` lists local CSS, JS, image, or library asset requirements.
- `provenance` carries enough source context for diagnostics without exposing
  mutable pipeline records.
- `variant`, `size`, `role`, and `state` fields use documented enum values.

## Chirp UI Lessons To Borrow

Chirp UI keeps contracts honest with deterministic generated artifacts:

- component descriptors in code;
- generated manifests checked in CI;
- generated API docs inside stable marker blocks;
- explicit runtime requirements;
- quality and debt scorecards that catch unclassified or under-described
  components.

Bengal should apply the same pattern to template view contracts. A generated
manifest can describe every known view model, field, allowed variant, safe-HTML
field, required asset, and template entrypoint. A `--check` mode should fail
when docs or manifests drift from descriptors.

## Milestones

1. **Manifest foundation**: add internal descriptors and a generated template
   view manifest for existing high-value render shapes. This is read-only
   documentation at first.
2. **Directive and shortcode pilot**: migrate a narrow set such as admonitions,
   cards, and tabs to descriptor-backed view data while preserving current
   output.
3. **Content type views**: define views for landing pages, tutorial pages,
   notebooks, list pages, tracks, and reference hubs.
4. **Autodoc and resource views**: normalize REST autodocs, API indexes, and
   resource listings so templates do not inspect parser-specific structures.
5. **Theme parity pass**: update the default theme and Chirp UI theme to consume
   the same view models for migrated surfaces.
6. **BYO engine proof**: render a representative fixture through a second
   template adapter using only the view manifest and plain data.

## Acceptance Criteria

- Representative directive, shortcode, and content type fixtures expose stable
  view data before template rendering.
- Default theme output remains unchanged except for intentional, reviewed
  template migrations.
- Chirp UI theme templates consume view models instead of Bengal-specific layout
  dialects for migrated surfaces.
- Manifest generation is deterministic and has a `--check` mode.
- Docs include generated contract sections guarded by marker comments.
- Tests cover safe-HTML handling, missing context diagnostics, malformed input,
  and at least one non-Kida adapter proof once the adapter exists.

## Compatibility And Risk

This direction should not break the default theme if the migration is additive:
old template-facing properties and render helpers can remain as shims while new
view models are introduced. The risk is contract sprawl. The mitigation is to
start with a small pilot, generate the manifest from descriptors, and avoid
promoting field names to public contracts until they are exercised by both the
default theme and the Chirp UI theme.

## Steward Notes

- **Rendering**: owns template view construction, safe-HTML boundaries, URLs,
  excerpts, TOCs, shortcode views, and content type render data.
- **Core**: immutable pipeline records stay unchanged; view models are derived
  rendering artifacts.
- **Themes**: default and Chirp UI themes should converge on the same data
  shapes while keeping different interface grammar.
- **Tests**: every accepted view contract needs fixtures, malformed input
  coverage, and parity proof when multiple entrypoints consume it.
- **Docs**: generated manifest/docs sections should move with any user-facing
  contract.
