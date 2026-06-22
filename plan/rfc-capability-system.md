# RFC: Capabilities as a First-Class, Extensible System

**Status**: Proposed (Phase 0–1 landed; Phase 2 landed #572; Phase 3 landed #573)
**Created**: 2026-06-18
**Tracking**: #570 (epic) — children #571, #572, #573; bug fix #569
**Source**: Root-cause of #569 (Mermaid missing on `/docs/0.5.0/`), generalized to the third-party case
**Related**: #533/#550 (self-hosted capabilities), `plan/epic-default-theme-refresh.md`, `plan/rfc-theme-library-assets.md`

---

## Why This Matters

"Capabilities" are opt-in heavy frontend features that need build-time provisioning
and runtime asset loading: Mermaid diagrams, KaTeX math, Iconify icon sets, and
(future) D3 / third-party visualizations. Today they are a single per-config
boolean (`capabilities.mermaid: true`) plus a hardcoded vendor table
(`bengal/capabilities/vendors.py`) and bespoke template/JS wiring in the default
theme.

That model has two problems, one already breaking production:

1. **Activation is sourced from the wrong place.** #569: the docs site builds
   previous versions from their git **tags**. Each version build reads `[capabilities]`
   from the checked-out tag, so a tag cut before a capability was enabled renders
   its diagrams as raw text forever. Mermaid was enabled (#563) two days after the
   `v0.5.0` tag — so `/docs/0.5.0/content/#how-content-flows` shipped broken.

2. **There is no extension point.** A third party cannot add a capability without
   editing core's vendor table, render path, and theme JS. As the ecosystem grows
   (more diagram engines, math renderers, embeds), this doesn't scale.

The fix for #569 and the design for third-party capabilities are the same insight:
**get the ownership model right.**

---

## A Capability Spans Three Concerns

A single capability bundles three things that today are scattered across core and
the theme:

1. **Provisioning spec** — pinned asset URL(s) and where they land
   (`VENDOR_SOURCES` / `VENDOR_FILES` in `vendors.py`; network I/O is build-time
   only, runtime uses same-origin URLs).
2. **Parse-time transform** — the fence/shortcode → HTML element. Mermaid's
   ` ```mermaid ` fence becomes `<div class="mermaid">…</div>` in the patitas
   block renderer.
3. **Runtime contract** — when/how to load the asset, the init hook, and
   theme-token bindings. Mermaid lazy-loads via an IntersectionObserver on
   `.mermaid` (`lazy-loaders.js`) and recolors diagrams by resolving OKLCH /
   `light-dark()` tokens to sRGB before render (`mermaid-theme.js`, #567).

These three concerns have **different owners and different lifecycles**. Collapsing
them into one versioned boolean is the root cause.

---

## The Ownership Model: Three Owners, Three Control Surfaces

| Layer | Owner | Controls | Lifecycle |
|---|---|---|---|
| **Capability definition** | Third-party author | asset pins + SRI, content *detector*, render transform, JS init contract, theme-token hooks, dependencies | ships with the tooling/plugin — **always current** |
| **Activation policy** | Site owner | enable/disable allow-list, asset *source* (self-host / CDN / local), version-pin override, CSP/SRI policy | **build environment** — applies to *all* version builds |
| **Actual use** | Content author | writes a ` ```mermaid ` fence — config-free | **versioned with content** |

The build-time resolver becomes a clean conjunction:

> **enabled** (owner) **AND provisioned-successfully** (author spec) **AND needed**
> (detector) **→ emit assets + init.**

### The one principle that resolves everything

**Enablement is a build-environment decision. "Is it needed?" is answered by
content-detection — not by a per-version config flag.**

- The *theme/JS machinery* that consumes a capability already comes from the
  installed `bengal` package (current), not from the historical tag. Capabilities
  were the odd one out being sourced from historical content.
- Enabling a capability is cheap because the runtime lazy-loads assets only on
  pages that actually contain the triggering content. So a site owner can enable
  Mermaid globally and pay nothing on the 95% of pages without a diagram.
- Archived docs versions render diagrams with **today's** tooling, which is what a
  reader wants — not whatever was (or wasn't) wired up the week that tag was cut.

The one knob that *is* legitimately version-overridable is the **asset version
pin** (an old version's content might require Mermaid 10 syntax, not 11). That
belongs to the site **owner** as an explicit override, not buried in tag content.

---

## What a Third-Party Author Declares (#572)

A `bengal.capabilities` entry-point registers a capability that declares:

- **Identity + asset spec** — name, pinned version, source URL(s), **SRI hash**
  (supply chain: they're pulling from a third-party CDN at build time).
- **Content detector** — "I'm needed if the page contains `.mermaid`" / "a fence
  of type X". This is what makes broad enablement safe and cheap.
- **Render hook** — the fence/shortcode → HTML transform, so it lives with the
  capability instead of core's `blocks.py`.
- **Init contract** — JS entry, load position (head/body, defer/module), and
  optional **theme-token bindings** (generalize the recolorization need:
  "give me these CSS vars resolved to sRGB").
- **Dependencies** — "I need capability Y first."

---

## What a Site Owner Controls (#573)

- **Allow-list** — capabilities are opt-in (security: third-party JS + third-party
  CDN downloads).
- **Source override** — self-host (default) vs CDN vs local file, per capability,
  for airgapped / CSP-strict / offline builds. This is the point of the #533
  self-hosting push.
- **Pin override** — inherit the author's pin by default; force a version when an
  archived docs version needs older syntax.
- **CSP / SRI policy** — emit integrity attributes, restrict allowed origins.

---

## What a Content Author Does

Nothing but write the feature: a ` ```mermaid ` fence. The detector triggers the
capability; zero config. This is the lifecycle that *should* be versioned —
content is, and only content is.

---

## Phasing

### Phase 0 — Inherit build-environment capabilities (LANDED, #569)

Version worktree builds now inherit the orchestrating build's `[capabilities]`
(`_apply_inherited_capabilities` in `bengal/cli/milo_commands/build.py`), which
wins on conflict. Current tooling provisions and activates the feature for every
version build; vendor provisioning and runtime resolution both key off the
worktree's own `assets/vendor/`, so the whole chain works.

Verified: `bengal build --build-version 0.5.0 --environment production` provisions
the 3.3 MB bundle, emits `mermaid: '/bengal/assets/vendor/mermaid.min.<hash>.js'`,
and copies the fingerprinted file into output.

This is a correctness fix, not the full design — it makes activation a
build-environment decision in the one place it was leaking from versioned content.

### Phase 1 — Content-detection as first-class metadata (#571) — LANDED

Formalize the build-time half of detection (the runtime half exists in
`lazy-loaders.js`). A declarative predicate over rendered HTML / parsed AST decides
which pages get asset wiring, so global enablement costs nothing on non-using pages
and authors never touch config.

### Phase 2 — Third-party registry via entry-points (#572) — LANDED

Promote the hardcoded vendor table to a registry populated by `bengal.capabilities`
entry-points, carrying the author-owned declaration above. Built-in Mermaid/KaTeX/Iconify
register via `pyproject.toml`; third parties add their own entry points without editing core.

### Phase 3 — Supply-chain controls (#573) — LANDED

SRI hashes, source override (self-host/CDN/local), pin override — the
owner-facing controls that make self-hosting third-party assets trustworthy.
CSP allowed-origins policy (#589) adds `[capabilities.policy]` for build-time CDN
provisioning restrictions.

### Phase 4 — Render-hook dispatcher (#584) — LANDED

Fence → HTML transforms route through the capability registry. Each spec declares
`fence_render` (or derives it from a single `fence_languages` entry). Core
`blocks.py` no longer hardcodes Mermaid.

### Phase 5 — Registry-driven theme init (#585) — LANDED

`CapabilityInitContract` drives head/body asset tags, lazy loaders, companion
scripts, and runtime fetch globals via `build_capability_wiring()`. The default
theme iterates `capability_wiring` instead of branching on capability names.

### Phase 6 — Ecosystem tooling (#586–#588) — LANDED

- `bengal capability list|info|validate` CLI (#588)
- Reference package at `examples/capability-demo/` (#586)
- Site-owner docs at `docs/building/configuration/capabilities/` (#587)

---

## Non-Goals

- Re-tagging published releases to backfill config (rejected: rewrites release
  history; Phase 0 makes it unnecessary).
- Per-content capability *configuration* beyond "use the feature" — content
  declares need by using the feature, not by setting flags.

---

## History (do not re-litigate)

- Capabilities introduced as self-hosted opt-in assets in #533 / #550 (default
  theme refresh, zero-dep promise).
- Mermaid self-hosting enabled for the docs site in #563; recolorization fixed in
  #567.
- #569 found activation was sourced from versioned tag content → previous-version
  docs rendered diagrams as raw text. Phase 0 fixed it by making activation a
  build-environment inheritance.
