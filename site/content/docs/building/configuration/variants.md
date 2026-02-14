---
title: Multi-Variant Builds
description: Build different site variants (OSS vs Enterprise, brand1 vs brand2) from one content tree
weight: 25
category: guide
icon: layers
card_color: purple
---
# Multi-Variant Builds

Build multiple documentation sites from a single content tree. Use this when you have:

- **OSS vs Enterprise** — Open-source docs plus paid-feature docs
- **Brand variants** — Same content, different branding or feature sets
- **Acquired products** — Merged doc sites with edition-specific pages

## How It Works

1. **Frontmatter**: Add `edition` to pages that belong to specific variants.
2. **Config**: Set `params.edition` per environment to select the variant.
3. **Build**: Bengal filters out pages whose `edition` does not include the selected variant.

Pages without `edition` are included in **all** builds.

## Frontmatter

Use `edition` in page frontmatter:

```yaml
# Shared page — included in every build
---
title: Getting Started
---

# Getting Started

Welcome to the docs.
```

```yaml
# Enterprise-only page
---
title: SSO Configuration
edition: [enterprise]
---

# SSO Configuration

Configure single sign-on for your organization.
```

```yaml
# OSS and Enterprise (both variants)
---
title: API Reference
edition: [oss, enterprise]
---

# API Reference

Full API documentation.
```

**Accepted formats:**

| Format | Result |
|--------|--------|
| `edition: [enterprise]` | Page only in `enterprise` builds |
| `edition: [oss, enterprise]` | Page in both `oss` and `enterprise` builds |
| `edition: enterprise` | Normalized to `[enterprise]` |
| Omit `edition` | Page in all builds |

## Configuration

Set `params.edition` in your environment config:

```yaml
# config/environments/oss.yaml
params:
  edition: oss

site:
  baseurl: "https://docs.example.com"
```

```yaml
# config/environments/enterprise.yaml
params:
  edition: enterprise

site:
  baseurl: "https://enterprise.example.com"
```

### Environment Variable Override

Override via `BENGALxPARAMSxEDITION`:

```bash
BENGALxPARAMSxEDITION=enterprise bengal build --environment production
```

This follows Bengal's standard env override pattern: `BENGALx` + key path with `x` as delimiter.

## Build Commands

```bash
# OSS site
bengal build --environment oss

# Enterprise site
bengal build --environment enterprise

# Or via env var
BENGALxPARAMSxEDITION=enterprise bengal build --environment production
```

## Content Organization

Typical structure:

```tree
content/
├── _index.md              # Shared landing
├── getting-started/
│   ├── _index.md          # Shared
│   ├── install.md         # Shared
│   └── quickstart.md      # Shared
├── api/
│   ├── _index.md          # Shared
│   └── reference.md       # edition: [oss, enterprise]
├── enterprise/
│   ├── _index.md          # edition: [enterprise]
│   ├── sso.md             # edition: [enterprise]
│   └── audit-logs.md      # edition: [enterprise]
└── oss/
    └── contributing.md    # edition: [oss]
```

## Cascade

Use cascade to apply `edition` to entire sections:

```markdown
---
# content/enterprise/_index.md
title: Enterprise
edition: [enterprise]
cascade:
  edition: [enterprise]
---
```

Child pages inherit `edition` from cascade unless they override it.

## CI/CD

Build both variants in separate jobs:

```yaml
jobs:
  build-oss:
    steps:
      - run: bengal build --environment oss
      - uses: actions/upload-artifact@v4
        with:
          name: site-oss
          path: public/

  build-enterprise:
    steps:
      - run: bengal build --environment enterprise
      - uses: actions/upload-artifact@v4
        with:
          name: site-enterprise
          path: public/
```

Or use a matrix:

```yaml
jobs:
  build:
    strategy:
      matrix:
        edition: [oss, enterprise]
    steps:
      - run: bengal build --environment ${{ matrix.edition }}
      - uses: actions/upload-artifact@v4
        with:
          name: site-${{ matrix.edition }}
          path: public/
```

## See Also

- [Configuration](./) — Base configuration
- [Deployment](../deployment/) — Deploying variant sites
- [GitHub Actions](/docs/tutorials/operations/automate-with-github-actions/) — CI/CD for variants
