---
title: Versioned Documentation
description: Serve multiple versions of your documentation from a single site
weight: 50
---

# Versioned Documentation

Bengal supports **versioned documentation**, allowing you to maintain multiple versions of your docs (e.g., v1, v2, v3) and let users switch between them.

## Why Version Your Docs?

- **API libraries**: Users on older versions need docs that match their installed version
- **Breaking changes**: Major releases often have different APIs or workflows
- **Enterprise support**: Some users stay on LTS versions for years
- **Migration guides**: Link between versions to help users upgrade

## Two Modes

Bengal supports two versioning modes:

### Folder Mode (Default)

Store versions in `_versions/` directories:

```tree
content/
├── docs/              # Latest version (v3)
│   └── guide.md
└── _versions/
    ├── v2/
    │   └── docs/
    │       └── guide.md
    └── v1/
        └── docs/
            └── guide.md
```

**Best for**: Most projects, simple setup, easy to understand.

→ [Set up Folder Mode](./folder-mode.md)

### Git Mode

Build from Git branches or tags:

```yaml
versioning:
  mode: git
  git:
    branches:
      - name: main
        latest: true
      - pattern: "release/*"
        strip_prefix: "release/"
```

**Best for**: Projects that already use release branches, CI/CD pipelines.

→ [Set up Git Mode](./git-mode.md)

## Quick Start (Folder Mode)

### 1. Enable Versioning

```yaml
# bengal.yaml
versioning:
  enabled: true
  versions:
    - id: v3
      latest: true
    - id: v2
    - id: v1
  sections:
    - docs
```

### 2. Create a Version Snapshot

```bash
# Snapshot current docs as v2 before making breaking changes
bengal version create v2
```

This copies `docs/` → `_versions/v2/docs/`.

### 3. Build

```bash
bengal build
```

Your site now has:

- `/docs/guide/` → v3 (latest)
- `/docs/v2/guide/` → v2
- `/docs/v1/guide/` → v1

## URL Structure

| Version | URL Pattern | Example |
|---------|-------------|---------|
| Latest | `/docs/page/` | `/docs/installation/` |
| Older | `/docs/{version}/page/` | `/docs/v2/installation/` |

The latest version has **no version prefix** in URLs—cleaner for most users.

## Features

### Version Selector

A dropdown appears in the documentation sidebar when versioning is enabled, letting users switch between versions. Bengal's version selector includes smart fallback: if a page doesn't exist in the target version, it navigates to the nearest equivalent (section index or version root) instead of showing a 404.

The default theme includes the version selector automatically. To customize, override `partials/version-selector.html` in your theme.

### Version Banners

Older versions automatically display a warning banner linking to the latest docs. Customize the banner per version:

```yaml
versions:
  - id: v2
    banner:
      type: warning  # or: info, danger
      message: "You're viewing docs for v2. See the latest version."
```

Banner types: `info` (blue), `warning` (yellow), `danger` (red for deprecated versions).

### Cross-Version Links

Link to specific versions from any page:

```markdown
See the [[v2:docs/migration|v2 Migration Guide]] for upgrade steps.
```

→ [Cross-Version Linking](./cross-version-links.md)

### Version Directives

Mark when features were added, deprecated, or changed:

```markdown
:::{since} v2.0
This feature was added in version 2.0.
:::

:::{deprecated} v3.0
Use `new_function()` instead.
:::

:::{changed} v2.5
Default timeout changed from 30s to 60s.
:::
```

→ [Version Directives](./directives.md)

### Build Artifacts (versions.json)

When versioning is enabled, Bengal emits `versions.json` at the output root. This Mike-compatible manifest lists all versions with titles, aliases, and URL prefixes—useful for custom themes or external tools.

```json
[
  {"version": "v3", "title": "3.0", "aliases": ["latest"], "url_prefix": ""},
  {"version": "v2", "title": "2.0", "aliases": [], "url_prefix": "/v2"}
]
```

Disable with `versioning.emit_versions_json: false`.

### Root Redirect

For docs-only sites where the root should redirect to the default version:

```yaml
versioning:
  enabled: true
  default_redirect: true
  default_redirect_target: "/docs/"  # optional, defaults to first section
```

This writes `index.html` at the output root with a meta-refresh and JavaScript redirect. **Note**: This overwrites any existing home page—use only when the site root is meant to redirect to docs.

### SEO Optimization

Bengal automatically handles SEO for versioned docs:

- **Canonical URLs**: Older versions point to latest version (prevents duplicate content penalties)
- **Sitemap priorities**: Latest version pages get priority 0.8; older versions get 0.3
- **No-index option**: Mark deprecated versions as `noindex` to remove from search entirely

## CLI Commands

```bash
# List all versions
bengal version list

# List versions as JSON (for scripting)
bengal version list --format json

# Show version details
bengal version info v2

# Create a new version snapshot
bengal version create v2 --label "2.0 LTS"

# Preview what create would do
bengal version create v2 --dry-run

# Compare versions
bengal version diff v2 v3

# Compare git branches directly
bengal version diff main release/0.1.6 --git
```

## Next Steps

- [Folder Mode Setup](./folder-mode.md) — Step-by-step guide
- [Git Mode Setup](./git-mode.md) — Build from branches
- [Cross-Version Links](./cross-version-links.md) — Link between versions
- [Version Directives](./directives.md) — Mark version-specific content
