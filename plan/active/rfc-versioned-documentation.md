# RFC: Versioned Documentation Support

**Status**: Draft  
**Created**: 2025-12-03  
**Author**: AI Assistant + Lawrence Lane

---

## Problem Statement

Documentation sites often need to serve multiple versions simultaneously:
- API docs for v1, v2, v3
- Product docs for LTS releases
- "Latest" always pointing to newest stable

Bengal currently has no built-in versioning support. Users must manually manage version folders without framework assistance.

---

## Goals

1. **Version isolation** - Each version is a complete, independent doc set
2. **Version switching** - UI to switch between versions
3. **"Latest" alias** - `/docs/latest/` always resolves to newest stable
4. **Selective versioning** - Only some sections may be versioned (e.g., `/docs/` but not `/blog/`)
5. **Shared content** - Some pages shared across versions (changelog, migration guides)
6. **SEO-friendly** - Canonical URLs, proper redirects, no duplicate content penalties

---

## How Other SSGs Handle This

### 1. Docusaurus (Built-in)

**Structure:**
```
docs/
├── intro.md                    # "Next" (unreleased)
├── tutorial.md
versioned_docs/
├── version-2.0/
│   ├── intro.md
│   └── tutorial.md
├── version-1.0/
│   ├── intro.md
│   └── tutorial.md
versions.json                   # ["2.0", "1.0"]
versioned_sidebars/
├── version-2.0-sidebars.json
└── version-1.0-sidebars.json
```

**Config:**
```js
// docusaurus.config.js
module.exports = {
  docs: {
    lastVersion: 'current',
    versions: {
      current: { label: '3.0-next', path: 'next' },
      '2.0': { label: '2.0', path: '2.0' },
      '1.0': { label: '1.0 (LTS)', path: '1.0', banner: 'unmaintained' },
    },
  },
};
```

**URLs:**
- `/docs/` → Latest stable
- `/docs/next/` → Unreleased
- `/docs/2.0/intro` → Version 2.0
- `/docs/1.0/intro` → Version 1.0

**Pros:**
- Built-in CLI: `npm run docusaurus docs:version 2.0`
- Per-version sidebars
- Version banners ("This is old!")
- Algolia DocSearch integration

**Cons:**
- Copies entire docs folder per version (disk space)
- Complex folder structure
- Opinionated about "next" vs "current"

---

### 2. MkDocs + Mike (External Tool)

**Approach:** Each version is a separate build, deployed to version subfolder.

**Structure:**
```
site/
├── 1.0/
│   ├── index.html
│   └── ...
├── 2.0/
│   ├── index.html
│   └── ...
├── latest/              # Symlink or redirect to 2.0
└── versions.json
```

**Workflow:**
```bash
# Build and deploy version 1.0
mike deploy 1.0

# Build and deploy version 2.0 and set as latest
mike deploy 2.0 latest --update-aliases

# List versions
mike list
# 2.0 [latest]
# 1.0
```

**Pros:**
- Simple mental model (separate builds)
- Works with any MkDocs theme
- Git branch per version supported

**Cons:**
- External tool (not built into MkDocs)
- No content sharing between versions
- Each version is full rebuild

---

### 3. Sphinx + Read the Docs (Platform)

**Approach:** Platform handles versioning via Git branches/tags.

**Config:**
```yaml
# .readthedocs.yaml
version: 2
build:
  os: ubuntu-22.04
  tools:
    python: "3.11"
```

**How it works:**
- Each Git branch/tag = one version
- RTD builds each automatically
- Version selector injected by platform

**Pros:**
- Zero config in Sphinx itself
- Git-native (branch = version)
- Platform handles everything

**Cons:**
- Requires Read the Docs platform
- No local preview of version switching
- Tied to their infrastructure

---

### 4. Astro Starlight (Built-in Plugin)

**Structure:**
```
src/content/docs/
├── guides/
│   └── getting-started.md
├── v1/
│   └── guides/
│       └── getting-started.md
```

**Config:**
```ts
// astro.config.mjs
export default defineConfig({
  integrations: [
    starlight({
      versions: {
        root: { label: 'v2 (Latest)' },
        v1: { label: 'v1' },
      },
    }),
  ],
});
```

**Pros:**
- Clean integration with Astro
- Shared components across versions
- Type-safe config

**Cons:**
- Relatively new, less battle-tested
- Astro-specific

---

### 5. VuePress/VitePress (Community Plugins)

**Approach:** Plugins like `vuepress-plugin-versioning`

**Structure:**
```
docs/
├── 1.x/
│   └── guide.md
├── 2.x/
│   └── guide.md
└── guide.md              # Latest
```

**Pros:**
- Flexible plugin architecture
- Community-driven

**Cons:**
- No official solution
- Plugin quality varies
- Breaking changes between versions

---

### 6. GitBook (Platform)

**Approach:** Platform feature, Git sync per "space"

- Each "space" can have multiple variants/versions
- Managed entirely through GitBook UI
- Sync from Git branches

**Pros:**
- No config needed
- Beautiful UI
- Team collaboration

**Cons:**
- Proprietary platform
- $$$ for teams
- Lock-in

---

## Comparison Matrix

| Feature | Docusaurus | MkDocs+Mike | Sphinx+RTD | Starlight | GitBook |
|---------|------------|-------------|------------|-----------|---------|
| Built-in | ✅ | ❌ (plugin) | ❌ (platform) | ✅ | ✅ (platform) |
| Git branch = version | ❌ | ✅ | ✅ | ❌ | ✅ |
| Folder = version | ✅ | ❌ | ❌ | ✅ | ❌ |
| Shared content | ❌ | ❌ | ❌ | ✅ | ❌ |
| Per-version sidebar | ✅ | ✅ | ✅ | ✅ | ✅ |
| Version banners | ✅ | ❌ | ✅ | ✅ | ✅ |
| "Latest" alias | ✅ | ✅ | ✅ | ✅ | ✅ |
| Local preview | ✅ | ⚠️ | ❌ | ✅ | ❌ |
| CLI for versioning | ✅ | ✅ | ❌ | ❌ | ❌ |

---

## Proposed Options for Bengal

### Option A: Folder-Based Versioning (Docusaurus-style)

**Structure:**
```
site/content/
├── docs/
│   ├── _index.md           # Latest (v3)
│   └── guide.md
├── docs-v2/
│   ├── _index.md
│   └── guide.md
├── docs-v1/
│   ├── _index.md
│   └── guide.md
└── blog/                    # Not versioned
```

**Config:**
```yaml
# bengal.yaml
versioning:
  enabled: true
  root: docs                 # Which section is versioned
  versions:
    - id: v3
      path: docs
      label: "3.0 (Latest)"
      aliases: [latest]
    - id: v2
      path: docs-v2
      label: "2.0"
    - id: v1
      path: docs-v1
      label: "1.0 (LTS)"
      banner: "This version is no longer maintained."
```

**URLs:**
- `/docs/` → v3 (latest)
- `/docs/latest/guide/` → Redirect to `/docs/guide/`
- `/docs/v2/guide/` → v2 guide
- `/docs/v1/guide/` → v1 guide

**Pros:**
- All content in one repo
- Easy local preview
- Works with existing Bengal architecture

**Cons:**
- Disk space (duplicate content)
- No automatic version creation

---

### Option B: Frontmatter-Driven Versioning

**Structure:**
```
site/content/docs/
├── v3/
│   ├── _index.md           # version: v3
│   └── guide.md
├── v2/
│   ├── _index.md           # version: v2
│   └── guide.md
└── _shared/                 # Shared across versions
    └── changelog.md
```

**Frontmatter:**
```yaml
---
title: Getting Started
version: v3
version_label: "3.0 (Latest)"
---
```

**Config:**
```yaml
# bengal.yaml
versioning:
  enabled: true
  discover: frontmatter      # Or "folder"
  latest: v3
  aliases:
    latest: v3
  shared_paths:
    - docs/_shared
```

**Pros:**
- Flexible (frontmatter OR folder)
- Shared content support
- Version metadata per-page

**Cons:**
- More complex discovery
- Frontmatter duplication

---

### Option C: Git Branch Versioning (Mike-style)

**Approach:** Each version is a separate Git branch, Bengal builds all branches.

**Config:**
```yaml
# bengal.yaml
versioning:
  mode: git-branches
  branches:
    - branch: main
      version: v3
      label: "3.0 (Latest)"
      aliases: [latest]
    - branch: v2.x
      version: v2
      label: "2.0"
    - branch: v1.x
      version: v1
      label: "1.0 (LTS)"
```

**CLI:**
```bash
# Build all versions
bengal build --all-versions

# Build specific version
bengal build --version v2
```

**Pros:**
- Git-native workflow
- Clean separation
- Works with existing release workflows

**Cons:**
- Can't preview all versions locally easily
- Complex build orchestration
- Cherry-picking fixes across branches

---

### Option D: Hybrid (Recommended)

**Combine folder-based with smart features:**

**Structure:**
```
site/content/
├── docs/                    # Latest (v3)
│   ├── _index.md
│   └── guide.md
├── _versions/
│   ├── v2/
│   │   └── docs/
│   └── v1/
│       └── docs/
└── _shared/
    └── changelog.md         # Included in all versions
```

**Config:**
```yaml
# bengal.yaml
versioning:
  enabled: true

  # What sections are versioned
  sections:
    - docs

  # Version definitions
  versions:
    - id: v3
      source: docs           # Main content
      label: "3.0"
      latest: true
    - id: v2
      source: _versions/v2/docs
      label: "2.0"
    - id: v1
      source: _versions/v1/docs
      label: "1.0 (Legacy)"
      banner:
        type: warning
        message: "You're viewing docs for an older version."

  # Aliases
  aliases:
    latest: v3
    stable: v3
    lts: v1

  # Shared content (included in all versions)
  shared:
    - _shared/

  # URL patterns
  urls:
    latest_redirect: true    # /docs/latest/* → /docs/*
    version_prefix: true     # /docs/v2/* for older versions
```

**Generated URLs:**
```
/docs/                       # v3 (latest)
/docs/guide/                 # v3 guide
/docs/v2/                    # v2 index
/docs/v2/guide/              # v2 guide
/docs/v1/                    # v1 index
/docs/latest/guide/          # Redirects to /docs/guide/
```

**Features:**
1. **Version selector component** - Template function/partial
2. **Version banners** - Automatic "old version" warnings
3. **Canonical URLs** - Point to latest for SEO
4. **Sitemap** - Includes all versions with proper priority
5. **robots.txt** - Optional noindex for old versions

---

## Implementation Phases

### Phase 1: Foundation
- [ ] Version config schema
- [ ] Discovery: find versioned content
- [ ] URL generation with version prefixes
- [ ] Basic version selector data for templates

### Phase 2: Core Features
- [ ] "Latest" alias and redirects
- [ ] Version banners (frontmatter + auto)
- [ ] Shared content across versions
- [ ] Per-version menus

### Phase 3: Polish
- [ ] CLI: `bengal version create v4`
- [ ] CLI: `bengal version list`
- [ ] Canonical URL generation
- [ ] Sitemap with version awareness
- [ ] Search integration (per-version or unified)

### Phase 4: Advanced
- [ ] Git branch mode (optional)
- [ ] Version diffing ("What changed in v3?")
- [ ] Auto-migration guides
- [ ] API version detection from OpenAPI specs

---

## Open Questions

1. **How to handle cross-version links?**
   - `[[v2:docs/guide]]` syntax?
   - Or relative within version, absolute to cross?

2. **Should old versions be noindexed by default?**
   - Prevents SEO dilution
   - But users may search for old version docs

3. **How to handle version in development server?**
   - Serve all versions? (slow)
   - Serve one + version selector? (faster)

4. **Where does version selector live?**
   - Theme responsibility?
   - Bengal provides data, theme renders?

5. **How to handle breaking URL changes between versions?**
   - Page renamed in v3 but exists in v2
   - Redirect map per version?

---

## Recommendation

**Start with Option D (Hybrid)** because:

1. **Folder-based** is simpler than Git branches for most users
2. **Shared content** is a real need (changelog, migration)
3. **Aliases** (`latest`, `stable`) are essential for linking
4. **Version banners** prevent user confusion
5. **Incremental** - Can add Git branch mode later

The renderer state pattern we just implemented would be useful here:
```python
# During build, set version context on renderer
self._shared_renderer._version = current_version
self._shared_renderer._all_versions = versions_config
```

This enables version-aware directives:
```markdown
:::{version-note}
This feature was added in v2.1.
:::

:::{since}
3.0
:::
```

---

## Next Steps

1. **Feedback** on this RFC
2. **Prototype** Phase 1 (config + discovery)
3. **Design** version selector component
4. **Test** with real multi-version docs

---

## References

- [Docusaurus Versioning](https://docusaurus.io/docs/versioning)
- [Mike (MkDocs versioning)](https://github.com/jimporter/mike)
- [Read the Docs Versioning](https://docs.readthedocs.io/en/stable/versions.html)
- [Starlight Versioning](https://starlight.astro.build/guides/versioning/)
