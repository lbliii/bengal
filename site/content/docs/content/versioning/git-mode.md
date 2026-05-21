---
title: Git Mode Setup
description: Build versioned documentation from Git branches and tags
weight: 20
---

# Git Mode Setup

Git mode builds documentation from **Git branches or tags** instead of folder copies. This is ideal for projects that already use release branches or release tags.

## When to Use Git Mode

✅ **Use Git Mode if**:
- You already have release branches (e.g., `release/1.0`, `release/2.0`)
- You publish stable release tags (e.g., `v1.0.0`, `v1.1.0`, `v2.0.0`)
- You want versions tied to Git history
- You prefer not to duplicate content in folders
- Your CI/CD pipeline builds from branches

❌ **Use Folder Mode if**:
- You want simple, visible version directories
- You don't use release branches
- You're new to versioning

## How It Works

```
┌─────────────────────────────────────────────────────────┐
│                     Your Repo                           │
├─────────────────────────────────────────────────────────┤
│  main ──────────────────────────────► v3.0 (latest)     │
│    │                                                    │
│    └─ release/2.0 ──────────────────► v2.0              │
│         │                                               │
│         └─ release/1.0 ─────────────► v1.0              │
└─────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────┐
│                    Bengal Build                         │
├─────────────────────────────────────────────────────────┤
│  1. Discover branches/tags matching configuration       │
│  2. Create worktrees for each version                   │
│  3. Build each version into a staging output            │
│  4. Merge outputs into single site                      │
└─────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────┐
│                    Output Site                          │
├─────────────────────────────────────────────────────────┤
│  /docs/           ← from main (latest)                  │
│  /docs/2.0/       ← from release/2.0                    │
│  /docs/1.0/       ← from release/1.0                    │
└─────────────────────────────────────────────────────────┘
```

Bengal uses **Git worktrees** to check out each branch without affecting your working directory.

## Configuration

Configuration works in both `bengal.yaml` and `bengal.toml` formats.

### Basic Setup

```yaml
# bengal.yaml (or bengal.toml)
versioning:
  enabled: true
  mode: git

  git:
    branches:
      # Explicit branch
      - name: main
        latest: true

      # Pattern matching
      - pattern: "release/*"
        strip_prefix: "release/"

    default_branch: main
    parallel_builds: 4
```

### Pattern Matching

Match multiple branches with glob patterns:

```yaml
git:
  branches:
    # Match release/1.0, release/2.0, etc.
    - pattern: "release/*"
      strip_prefix: "release/"    # release/2.0 → version "2.0"

    # Match v1.0.0, v2.0.0, etc.
    - pattern: "v*"
      # No strip_prefix → version "v1.0.0"
```

### Using Tags

Build from Git tags instead of (or in addition to) branches:

```yaml
git:
  branches:
    - name: main
      latest: true

  tags:
    - pattern: "v*"
      strip_prefix: "v"    # v1.0.0 → version "1.0.0"
```

### Latest + Previous Tags

Use this when `main` should be the unversioned latest docs and the older docs
should come from the newest release tags:

```yaml
versioning:
  enabled: true
  mode: git
  sections:
    - docs

  git:
    latest:
      branch: main
      id: main
      label: Latest

    previous:
      source: tags
      count: 3
      pattern: "v*"
      strip_prefix: "v"
      sort: semver-desc
      include_prereleases: false

    cache_worktrees: true

  aliases:
    latest: main
```

If the repository has `v0.3.2`, `v0.3.1`, `v0.3.0`, and `v0.4.0-rc.1`,
Bengal builds `main` as `/docs/` and the three stable tags as
`/docs/0.3.2/`, `/docs/0.3.1/`, and `/docs/0.3.0/`. The prerelease tag is
skipped unless `include_prereleases: true`.

### Full Configuration Reference

```yaml
versioning:
  enabled: true
  mode: git

  git:
    # Latest branch selector (optional shorthand for the latest branch)
    latest:
      branch: main
      id: main
      label: Latest

    # Automatic previous-version selector (optional)
    previous:
      source: tags              # Currently supports tags
      count: 3                  # Number of previous tags to include
      pattern: "v*"             # Glob for candidate tags
      strip_prefix: "v"         # v1.2.3 → version "1.2.3"
      sort: semver-desc         # or: name-desc
      include_prereleases: false

    # Branch patterns
    branches:
      - name: main              # Explicit branch name
        latest: true            # This is the latest version

      - pattern: "release/*"    # Glob pattern
        version_from: branch    # How to extract version ID (see below)
        strip_prefix: "release/"
        latest: false

# version_from options:
#   branch - Use branch name (default)
#   tag    - Use tag name
#   <regex> - Custom regex pattern

    # Tag patterns (optional)
    tags:
      - pattern: "v*"
        strip_prefix: "v"

    # Settings
    default_branch: main        # Fallback if no latest specified (default: "main")
    cache_worktrees: true       # Keep worktrees for faster rebuilds (default: true)
    parallel_builds: 4          # Reserved for concurrent version builds

  # Standard versioning options still apply
  sections:
    - docs

  aliases:
    latest: main
    stable: "2.0"
```

## Building

### Build All Versions

```bash
# Discover and build all matching branches/tags
bengal build --all-versions
```

Output:
```text
🔍 Discovering versions from git...
Found 3 versions to build
  • main
  • 2.0
  • 1.0

📦 Building version main...
✅ Built 45 pages

📦 Building version 2.0...
✅ Built 42 pages

📦 Building version 1.0...
✅ Built 38 pages

✅ Built 3 versions
```

### Build Specific Version

```bash
# Build only version 2.0
bengal build --build-version 2.0
```

### Regular Build (Current Branch Only)

```bash
# Build current branch only
bengal build
```

## Comparing Versions

Compare content between Git refs:

```bash
# Compare branches
bengal version diff --old-version main --new-version release/2.0 --git

# Output as markdown (for release notes)
bengal version diff --old-version main --new-version release/2.0 --git --output markdown

# Output as JSON (for automation)
bengal version diff --old-version main --new-version release/2.0 --git --output json
```

Example output:
```text
📊 Version Diff: release/2.0 → main

Version diff: release/2.0 → main
  Added: 3 pages
  Removed: 1 pages
  Modified: 12 pages
  Unchanged: 28 pages

✨ Added pages:
  + docs/new-feature.md
  + docs/api/webhooks.md
  + docs/guide/advanced.md

🗑️ Removed pages:
  - docs/deprecated-guide.md

📝 Modified pages:
  ~ docs/installation.md (45.2% changed)
  ~ docs/configuration.md (12.8% changed)
```

## CI/CD Integration

### GitHub Actions Example

```yaml
# .github/workflows/docs.yml
name: Build Docs

on:
  push:
    branches:
      - main
      - 'release/*'

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0  # Need full history for branches

      - name: Setup Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.14'

      - name: Install Bengal
        run: pip install bengal

      - name: Build All Versions
        run: bengal build --all-versions

      - name: Deploy
        # Pin to SHA for supply chain security (v3.9.3)
        uses: peaceiris/actions-gh-pages@373f7f263a76c20808c831209c920827a82a2847
        with:
          github_token: ${{ secrets.GITHUB_TOKEN }}
          publish_dir: ./public
```

### GitLab CI Example

```yaml
# .gitlab-ci.yml
build-docs:
  image: python:3.14
  script:
    - pip install bengal
    - bengal build --all-versions
  artifacts:
    paths:
      - public/
```

## Worktrees

Bengal uses Git worktrees to check out multiple branches simultaneously:

```tree
.bengal/
└── worktrees/
    ├── 2.0/          # Checked out from release/2.0
    └── 1.0/          # Checked out from release/1.0
```

### Caching Worktrees

By default, worktrees are cached for faster rebuilds:

```yaml
git:
  cache_worktrees: true    # Reuse matching worktrees between builds
```

When a cached worktree already points at the expected commit, Bengal reuses it.
If the ref moved, Bengal refreshes that worktree before building.
Set `cache_worktrees: false` to remove worktrees after the build.

### Manual Cleanup

```bash
# Remove cached worktrees
rm -rf .bengal/worktrees
git worktree prune
```

## Troubleshooting

### Branch Not Found

```
❌ Version 2.0 not found
```

Check that the branch exists:
```bash
git branch -a | grep release
```

Verify your pattern matches:
```yaml
branches:
  - pattern: "release/*"    # Must match exactly
```

### Worktree Errors

```
Failed to create worktree
```

Clean up stale worktrees:
```bash
git worktree prune
rm -rf .bengal/worktrees
```

### Permission Errors

```
error: unable to create file: Permission denied
```

Ensure write access to the `.bengal/` directory:
```bash
chmod -R u+w .bengal/
```

If running in CI, ensure the checkout step has write permissions.

### Slow Builds

Keep cached worktrees enabled so unchanged refs do not need a fresh checkout:
```yaml
git:
  cache_worktrees: true
```

## Next Steps

- [Cross-Version Links](./cross-version-links.md) — Link between versions
- [Version Directives](./directives.md) — Mark version-specific content
- [Folder Mode](./folder-mode.md) — Alternative: folder-based versioning
