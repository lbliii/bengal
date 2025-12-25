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

```text
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

A dropdown appears in the header, letting users switch versions:

```html
<!-- Automatically added to templates when versioning is enabled -->
{% include "partials/version-selector.html" %}
```

### Version Banners

Older versions display a warning banner:

```yaml
versions:
  - id: v2
    banner:
      type: warning
      message: "You're viewing docs for v2. See the latest version."
```

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

### SEO Optimization

Bengal automatically handles SEO for versioned docs:

- **Canonical URLs**: Older versions point to latest (prevents duplicate content)
- **Sitemap priorities**: Latest gets 0.8, older versions get 0.3
- **Configurable**: Opt out of canonical pointing if needed

## CLI Commands

```bash
# List all versions
bengal version list

# Show version details
bengal version info v2

# Create a new version snapshot
bengal version create v2 --label "2.0 LTS"

# Compare versions
bengal version diff v2 v3
```

## Next Steps

- [Folder Mode Setup](./folder-mode.md) — Step-by-step guide
- [Git Mode Setup](./git-mode.md) — Build from branches
- [Cross-Version Links](./cross-version-links.md) — Link between versions
- [Version Directives](./directives.md) — Mark version-specific content
