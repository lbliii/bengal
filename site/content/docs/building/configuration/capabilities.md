---
title: Runtime Capabilities
nav_title: Capabilities
description: Enable self-hosted diagram, math, and third-party JS capabilities
weight: 45
tags:
- persona-operator
- persona-site-builder
---

# Runtime Capabilities

Runtime capabilities are **opt-in, self-hosted vendor features** — Mermaid
diagrams, KaTeX math, Iconify icon packs, and third-party packages you install.
Bengal provisions vendor files at **build time** and emits them only on pages
that actually use the feature.

There are **zero runtime CDN requests by default**. Capabilities must be
explicitly enabled in config and vendor files must exist under
`assets/vendor/` before templates emit script or link tags.

## Enable and disable

```toml
[capabilities]
mermaid = true
katex = true
iconify = true   # implied automatically when mermaid content is present
```

Each key is an allow-list entry. Disabled capabilities never download vendors and
never appear in output, even if your theme supports them.

Use the CLI to inspect the registry:

```bash
bengal capability list
bengal capability info mermaid
bengal capability validate
```

## Per-page emission (content detection)

Site-wide enablement does **not** mean site-wide asset tags. Bengal detects
capability usage per page — a ` ```mermaid ` fence, inline `$...$` math, or
matching HTML markers — and emits vendor assets only where needed.

The home page without diagrams ships **zero** Mermaid vendor tags even when
`[capabilities].mermaid = true`.

## Supply-chain overrides

Override how individual capabilities are provisioned:

```toml
[capabilities.sources.mermaid]
source = "local"
path = "vendor/mermaid.min.js"

[capabilities.sources.katex]
pin = "0.16.11"
require_sri = true
```

| Key | Purpose |
|-----|---------|
| `source` | `cdn` (default) or `local` |
| `path` / `local_path` | Required when `source = "local"` |
| `pin` | Override the default version pin |
| `sri` | Expected integrity hash for verification |
| `require_sri` | Fail the build on SRI mismatch (default `true`) |

Templates emit `integrity` and `crossorigin="anonymous"` on vendor tags when
hashes are known.

## CDN provisioning policy

Restrict which CDN origins Bengal may download from during build-time
provisioning:

```toml
[capabilities.policy]
allowed_cdn_origins = ["cdn.jsdelivr.net", "unpkg.com"]
```

Or deny all CDN downloads (airgapped / strict CSP deployments):

```toml
[capabilities.policy]
cdn_mode = "deny"
```

When `cdn_mode = "deny"`, use `source = "local"` under
`[capabilities.sources.<name>]` for every enabled capability.

## Versioned documentation builds

Tagged version worktrees inherit the **orchestrating build's**
`[capabilities]` config. Build-environment decisions (which vendors to
provision) apply across all version builds — historical tags do not need to
have shipped capability config themselves.

## Third-party capabilities

Packages register via the `bengal.capabilities` entry point. See
[[docs/extending/plugins|Plugin Development]] for author guidance and the
`examples/capability-demo/` reference package for an end-to-end sample.

## Related

- [[docs/theming/capabilities-vs-theme|Capabilities vs theme features]]
- [[docs/extending/plugins#runtime-capabilities-diagram--math-vendors|Authoring a capability package]]
