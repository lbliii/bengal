# Theme Library Assets

**Status**: Draft
**Created**: 2026-05-06
**Scope**: Rendering assets, themes, dev server, static builds, diagnostics

## Problem

Bengal has a usable theme asset pipeline and Chirp UI has real package assets,
but the bridge between them is too implicit. A Chirp UI-powered theme currently
needs to know where provider CSS lives, which files Bengal fingerprints, which
paths live reload serves, and whether imported provider CSS is copied as a
logical asset.

That gap produced a live/dev/static parity failure: the browser requested local
CSS URLs that static output did not actually emit. The short-term fix is to make
the theme stylesheet the single entrypoint and import Chirp UI there. The
long-term fix is for Bengal to understand library assets as first-class inputs.

## Direction

Themes should be composition layers. A theme should declare that it uses a UI
library, then write templates, macros, tokens, and theme-specific polish. Bengal
should discover provider assets, serve them in development, copy and fingerprint
them in static builds, rewrite references, expose macros and filters, and fail
loudly when templates link assets Bengal did not emit.

## Goals

- Add a first-class library asset model that can represent package-provided CSS,
  JS, macros, filters, runtime requirements, and optional bundle behavior.
- Keep dev server URLs and static build URLs part of the same contract.
- Make missing emitted assets a build diagnostic before a browser sees a 404.
- Let provider metadata come from the library package when possible.
- Let themes override tokens and compose patterns without copying framework CSS
  or hand-linking package internals.

## Non-Goals

- Do not add npm, Node, or a JavaScript build phase.
- Do not commit to a public config shape without the constitution's stop-and-ask
  step.
- Do not require Chirp UI specifically; the model should work for any Python
  package that can expose static assets and optional template helpers.
- Do not replace the current theme asset pipeline in the first wave.

## Illustrative Declaration

This is a planning sketch, not an accepted config contract:

```toml
[libraries.chirp_ui]
package = "chirp_ui"
css = ["chirpui.css", "chirpui-transitions.css"]
js = ["chirpui.js"]
macros = true
mode = "bundle" # or "link"
runtime = ["alpine"]
```

Equivalent data may come from theme metadata, a Python registration hook, or a
library package manifest. The final shape needs explicit approval because it
would affect theme configuration and output behavior.

## Library Metadata

A provider such as Chirp UI can expose clean package metadata:

- static asset root, such as `chirp_ui.static_path()`;
- CSS and JS entrypoints;
- optional macro namespace and loader;
- optional filters or template helper registration;
- runtime requirements such as Alpine or HTMX;
- token and component manifest metadata;
- bundle/link capability and whether entries are safe to concatenate.

Bengal consumes that metadata declaratively. Theme templates should not hardcode
package-internal paths.

## Pipeline Contract

The asset pipeline should converge on this flow:

```text
library declaration
  -> provider metadata discovery
  -> logical asset records
  -> development stable URLs
  -> static copied/fingerprinted outputs
  -> asset manifest
  -> HTML reference audit
```

Development and static builds should agree on logical asset identity. Static
builds may fingerprint physical output paths, but templates should resolve
through the same logical asset records.

## Helper Surface

The exact helper names are open. Two candidate directions:

- `library_asset_url("chirp_ui", "chirpui.css")`
- `asset_url("chirp_ui/chirpui.css")` where library assets live in the same
  logical asset namespace as theme assets

The second option keeps templates simpler if Bengal can provide diagnostics
that distinguish project, theme, and library sources behind the scenes.

## Diagnostics

Missing or unsafe asset usage should produce structured diagnostics with:

- source page or template path when known;
- logical asset requested;
- known emitted assets in the same namespace;
- provider or theme responsible for declaration;
- suggestion, such as "declare this library asset" or "use asset_url()";
- dev/static mode and active manifest revision when relevant.

The same audit should catch local CSS and JS references in rendered HTML that
are not serveable in the current mode.

## Milestones

1. **Declarative contract draft**: define internal `LibraryAsset` and
   `ThemeLibrary` shapes without exposing new public config.
2. **Provider discovery pilot**: consume Chirp UI metadata from a small adapter
   or package manifest and map it into logical asset records.
3. **Dev/static parity**: serve library assets at stable dev URLs, copy and
   fingerprint them in static builds, and verify every rendered local CSS/JS URL
   is serveable.
4. **Diagnostics**: add missing-emitted-asset diagnostics with source context
   and actionable suggestions.
5. **Composition modes**: support link mode first; evaluate bundle mode only
   after defining pure-Python concatenation, source maps or provenance, and
   duplicate asset semantics.
6. **Theme cleanup**: remove Chirp UI asset plumbing from theme templates and
   keep theme CSS focused on token overrides and Bengal-specific composition.
7. **Generated manifest checks**: borrow Chirp UI's generated-manifest pattern
   for provider metadata, docs drift, and runtime requirement coverage.

## Acceptance Criteria

- A representative Chirp UI theme can declare library usage without hardcoding
  provider asset paths in templates.
- Dev server serves declared library assets at stable logical URLs.
- Static builds copy, fingerprint, and rewrite declared library assets.
- Route smoke tests verify all local CSS and JS references are serveable in
  development and static output.
- Missing undeclared or unemitted assets produce Bengal diagnostics with a
  suggestion and source context.
- Default theme behavior is unchanged unless it opts into the same library asset
  model.
- User-facing changes include docs, examples or theme scaffolds as applicable,
  tests, and a changelog fragment.

## Compatibility And Risk

This can stay additive if library assets enter the pipeline as another asset
source. Existing theme assets keep their current behavior, and the default theme
does not need to use library assets immediately.

The high-risk decisions are public config shape, helper names, bundle behavior,
and output manifest semantics. Those require an explicit stop-and-ask checkpoint
before implementation.

## Steward Notes

- **Assets/rendering**: own logical asset records, manifest revisioning,
  `asset_url()` behavior, and HTML reference audits.
- **Dev server**: must serve the same logical asset namespace that static builds
  emit.
- **Themes**: remain composition layers; custom CSS should shrink toward token
  overrides and Bengal documentation patterns.
- **Config/public contracts**: any accepted declaration syntax needs docs,
  scaffolds, tests, and migration notes.
- **Tests**: live/dev/static parity gets route smoke tests that exercise CSS and
  JS URLs, not just rendered HTML strings.
