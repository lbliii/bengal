---
title: Folder Mode Setup
description: Set up versioned documentation using folder-based versioning
weight: 10
---

# Folder Mode Setup

Folder mode is the simplest way to version your documentation. Each version lives in its own directory.

## Directory Structure

```tree
your-site/
├── bengal.yaml
├── content/
│   ├── docs/                    # Latest version (v3)
│   │   ├── _index.md
│   │   ├── installation.md
│   │   └── guide/
│   │       └── getting-started.md
│   └── _versions/
│       ├── v2/
│       │   └── docs/            # v2 content
│       │       ├── _index.md
│       │       ├── installation.md
│       │       └── guide/
│       │           └── getting-started.md
│       └── v1/
│           └── docs/            # v1 content
│               └── ...
```

:::{steps}
:::{step} Enable Versioning

Add to your `bengal.yaml`:

```yaml
versioning:
  enabled: true
  versions:
    - id: v3
      label: "3.0"
      latest: true
    - id: v2
      label: "2.0"
    - id: v1
      label: "1.0"
      deprecated: true
  sections:
    - docs  # Which content sections are versioned (default)
```

If you omit `sections`, it defaults to `["docs"]`.

:::{/step}
:::{step} Create Version Directories

### Option A: Use the CLI (Recommended)

```bash
# Before making breaking changes, snapshot current docs
bengal version create v2

# This creates _versions/v2/docs/ with a copy of docs/
```

### Option B: Create Manually

```bash
mkdir -p content/_versions/v2/docs
cp -r content/docs/* content/_versions/v2/docs/
```

:::{/step}
:::{step} Build and Verify

```bash
bengal build
```

Check the output:

```
public/
├── docs/
│   ├── index.html              # /docs/ (latest)
│   └── installation/
│       └── index.html          # /docs/installation/
├── docs/v2/
│   ├── index.html              # /docs/v2/
│   └── installation/
│       └── index.html          # /docs/v2/installation/
└── docs/v1/
    └── ...
```

:::{/step}
:::{/steps}

## Configuration Options

### Full Configuration Reference

```yaml
versioning:
  enabled: true

  # Version definitions
  versions:
    - id: v3                    # Required: unique identifier
      label: "3.0 (Current)"    # Optional: display label
      latest: true              # One version must be latest

    - id: v2
      label: "2.0 LTS"
      banner:                   # Optional: warning banner
        type: warning           # info, warning, or danger
        message: "This is an older version. See v3 for latest."
        show_latest_link: true

    - id: v1
      label: "1.0"
      deprecated: true          # Marks version as deprecated
      end_of_life: "2024-12-31" # Optional: EOL date

  # Aliases for version IDs
  aliases:
    latest: v3
    stable: v3
    lts: v2

  # Which sections are versioned (default: ["docs"])
  sections:
    - docs
    # - api    # Add more if needed

  # Shared content across all versions (default: ["_shared"])
  shared:
    - _shared  # Content in _shared/ appears in all versions
```

### Shared Content

Content that should appear in **all versions** goes in `_shared/`:

```tree
content/
├── docs/
├── _versions/
└── _shared/
    └── docs/
        └── changelog.md    # Appears in all versions
```

## Workflow: Creating a New Version

When you're about to release a breaking change:

:::{steps}
:::{step} Snapshot current docs

```bash
# Create v2 from current docs
bengal version create v2 --label "2.0"
```

:::{/step}
:::{step} Update configuration

```yaml
versions:
  - id: v3          # NEW: will be the latest
    latest: true
  - id: v2          # Previous latest
  - id: v1
```

:::{/step}
:::{step} Make breaking changes

Edit `content/docs/` freely—v2 is preserved in `_versions/v2/docs/`.

:::{/step}
:::{step} Build and deploy

```bash
bengal build
```

:::{/step}
:::{/steps}

## Tips

### Keep Versions in Sync

For pages that exist in all versions (like changelog), use shared content:

```
_shared/docs/changelog.md
```

### Mark Deprecated Versions

```yaml
versions:
  - id: v1
    deprecated: true
    banner:
      type: danger
      message: "v1 is no longer supported. Please upgrade to v3."
```

### Version-Specific Banners

Each version can have its own banner:

```yaml
versions:
  - id: v2
    banner:
      type: info
      message: "v2 is in LTS. Security updates until 2025."
```

## Troubleshooting

### Version Not Appearing

:::{dropdown} Check version is listed
:icon: check

Verify the version is listed in `bengal.yaml` under `versions`.
:::

:::{dropdown} Verify directory exists
:icon: folder

Ensure `_versions/{id}/docs/` exists for your version id.
:::

:::{dropdown} Ensure content exists
:icon: file

Confirm the version directory contains content files.
:::

### Wrong Version Showing as Latest

Only one version should have `latest: true`:

```yaml
versions:
  - id: v3
    latest: true    # ✓ Only this one
  - id: v2
    # latest: true  # ✗ Remove this
```

### URLs Incorrect

Check `sections` in your config matches your content structure:

```yaml
sections:
  - docs    # Must match your content/docs/ directory
```

## Next Steps

- [Cross-Version Links](./cross-version-links.md) — Link between versions
- [Version Directives](./directives.md) — Mark version-specific content
- [Git Mode](./git-mode.md) — Alternative: build from branches
