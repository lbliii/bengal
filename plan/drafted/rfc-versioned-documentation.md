# RFC: Versioned Documentation Support

**Status**: Ready for Review  
**Created**: 2025-12-03  
**Updated**: 2025-12-10  
**Author**: AI Assistant + Lawrence Lane
**Priority**: P2 (Medium)  

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
7. **Cross-version linking** - Link to specific versions from any page

---

## Key Differentiators vs. Competitors

Bengal's versioning approach provides unique advantages over existing tools:

### 1. Shared Content (`_shared/`)

**No competitor handles this well.** Bengal allows content like changelogs and migration guides to appear in all versions without duplication:

```yaml
shared:
  - _shared/    # Included in ALL versions automatically
```

- **Docusaurus**: Must duplicate files per version
- **MkDocs+Mike**: Each branch is completely isolated
- **Sphinx+RTD**: Each branch is separate; no sharing mechanism

### 2. Flexible Multi-Alias System

Bengal supports **multiple named aliases**, not just "latest":

```yaml
aliases:
  latest: v3
  stable: v3
  lts: v1
  next: v4-beta
```

URLs: `/docs/latest/`, `/docs/stable/`, `/docs/lts/`, `/docs/next/`

Docusaurus only supports `current` vs numbered versions with limited aliasing.

### 3. Cross-Version Linking Syntax

**Unique to Bengal.** Link to specific versions from any page:

```markdown
See the [v2 migration guide]([[v2:migration]]).
For the latest API, see [[latest:api/reference]].
```

No competitor provides built-in cross-version linking syntax.

### 4. Version-Aware Directives

Built into Bengal's MyST rendering pipeline:

```markdown
:::{since}
3.0
:::

:::{deprecated}
2.0
Use `new_function()` instead.
:::

:::{version-changed}
version: 2.5
The default timeout changed from 30s to 60s.
:::
```

Docusaurus requires custom MDX components for this.

### 5. No JavaScript Required

Bengal is Python/Jinja-based. Teams without React/JS expertise can use full versioning without learning a new ecosystem.

---

## Competitive Comparison

| Feature | **Bengal** | Docusaurus | MkDocs+Mike | Sphinx+RTD | Hugo |
|---------|------------|------------|-------------|------------|------|
| **Built-in versioning** | ✅ | ✅ | ❌ (plugin) | ❌ (platform) | ❌ |
| **Shared content across versions** | ✅ | ❌ | ❌ | ❌ | ❌ |
| **Multiple aliases** (`latest`, `stable`, `lts`) | ✅ | ⚠️ limited | ✅ | ⚠️ | ❌ |
| **Cross-version linking** | ✅ | ❌ | ❌ | ❌ | ❌ |
| **Version-aware directives** | ✅ | ⚠️ (MDX) | ❌ | ⚠️ | ❌ |
| **Per-version banners** | ✅ | ✅ | ❌ | ✅ | ❌ |
| **Local preview all versions** | ✅ | ✅ | ⚠️ | ❌ | N/A |
| **Git branch mode** | ✅ | ❌ | ✅ | ✅ | N/A |
| **CLI for versioning** | ✅ | ✅ | ✅ | ❌ | ❌ |
| **No JS/React required** | ✅ | ❌ | ✅ | ✅ | ✅ |
| **Canonical URL handling** | ✅ | ✅ | ❌ | ✅ | Manual |

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

**Pros:**
- Built-in CLI: `npm run docusaurus docs:version 2.0`
- Per-version sidebars
- Version banners ("This is old!")
- Algolia DocSearch integration

**Cons:**
- Copies entire docs folder per version (disk space)
- Complex folder structure
- Opinionated about "next" vs "current"
- **No shared content between versions**
- **No cross-version linking**
- Requires React/JS knowledge

---

### 2. MkDocs + Mike (External Tool)

**Approach:** Each version is a separate build, deployed to version subfolder.

**Pros:**
- Simple mental model (separate builds)
- Works with any MkDocs theme
- Git branch per version supported

**Cons:**
- External tool (not built into MkDocs)
- **No content sharing between versions**
- Each version is full rebuild
- No local preview of version switching

---

### 3. Sphinx + Read the Docs (Platform)

**Approach:** Platform handles versioning via Git branches/tags.

**Pros:**
- Zero config in Sphinx itself
- Git-native (branch = version)
- Platform handles everything

**Cons:**
- Requires Read the Docs platform
- No local preview of version switching
- Tied to their infrastructure
- **No shared content**

---

### 4. Hugo

Hugo has **no built-in versioning support**. Teams must manually manage version folders or use external tools.

---

## Recommended Design: Option D (Hybrid)

Combine folder-based with smart features for the best balance of simplicity and power.

### Quick Start (80% of use cases)

```yaml
# bengal.yaml - Minimal config
versioning:
  enabled: true
  versions: [v3, v2, v1]  # Auto-discovers from _versions/ folders
```

Bengal auto-discovers:
- `docs/` → v3 (latest, since it's first)
- `_versions/v2/docs/` → v2
- `_versions/v1/docs/` → v1

### Full Configuration

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
    ├── changelog.md         # Included in all versions
    └── migration/
        └── v2-to-v3.md
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

  # Multiple aliases (unique to Bengal)
  aliases:
    latest: v3
    stable: v3
    lts: v1

  # Shared content (unique to Bengal)
  shared:
    - _shared/

  # URL patterns
  urls:
    latest_redirect: true    # /docs/latest/* → /docs/*
    version_prefix: true     # /docs/v2/* for older versions

  # SEO
  seo:
    canonical_to_latest: true
    noindex_older_than: null  # Or "v1" to noindex v1
```

**Generated URLs:**
```
/docs/                       # v3 (latest)
/docs/guide/                 # v3 guide
/docs/v2/                    # v2 index
/docs/v2/guide/              # v2 guide
/docs/v1/                    # v1 index
/docs/latest/guide/          # Redirects to /docs/guide/
/docs/lts/guide/             # Redirects to /docs/v1/guide/
```

---

## Cross-Version Linking Syntax

**Syntax:** `[[version:path]]`

```markdown
# In any page
See the [previous guide]([[v2:getting-started]]).
Check the [latest API reference]([[latest:api/reference]]).
The [LTS documentation]([[lts:overview]]) is also available.
```

**Rules:**
- `[[v2:path]]` → `/docs/v2/path/`
- `[[latest:path]]` → `/docs/path/` (resolves alias)
- `[[lts:path]]` → `/docs/v1/path/` (resolves alias)
- Relative links within a version stay in that version
- Broken cross-version links flagged during build

---

## Version-Aware Directives

```markdown
:::{since}
3.0
:::

:::{deprecated}
2.0
Use `new_api()` instead.
:::

:::{version-changed}
version: 2.5
The default timeout changed from 30s to 60s.
:::

:::{version-note}
This feature behaves differently in v1. See [[v1:quirks]].
:::
```

**Rendering:**
- `:::{since}` → Badge: "New in 3.0"
- `:::{deprecated}` → Warning box with deprecation notice
- `:::{version-changed}` → Info box with change description

---

## Version Selector Component

Bengal ships a default version selector partial. Themes can override.

**Default partial:** `partials/version-selector.html`

```html
{# themes/default/partials/version-selector.html #}
<div class="version-selector">
  <select onchange="window.location.href=this.value">
    {% for v in versions %}
    <option value="{{ v.url }}" {% if v.current %}selected{% endif %}>
      {{ v.label }}{% if v.latest %} (Latest){% endif %}
    </option>
    {% endfor %}
  </select>
</div>
```

**Template data available:**
```python
# In templates
{{ versions }}         # List of all versions
{{ current_version }}  # Current version object
{{ is_latest }}        # Boolean
{{ version_banner }}   # Banner HTML if configured
```

---

## Implementation Phases

### Phase 1: Foundation (MVP) ✅ COMPLETE
- [x] Version config schema with validation
- [x] Discovery: find versioned content from folders
- [x] URL generation with version prefixes
- [x] Basic version selector data for templates
- [x] Default `version-selector.html` partial
- [x] Version banner partial for older versions
- [x] PageCore.version field for caching
- [x] Unit tests for versioning models

### Phase 2: Core Features ✅ COMPLETE
- [x] CLI: `bengal version create v4` (snapshot current docs)
- [x] CLI: `bengal version list`
- [x] CLI: `bengal version info`
- [x] "Latest" alias and redirects
- [x] Multiple alias support (`latest`, `stable`, `lts`)
- [x] Version banners (frontmatter + auto)
- [x] Shared content across versions (`_shared/`)
- [x] VersionResolver for path resolution
- [ ] Per-version menus (deferred - can use existing menu system)

### Phase 3: Cross-Version & SEO ✅ COMPLETE
- [x] Cross-version linking syntax `[[v2:path]]`
- [x] Version-aware directives (`:::{since}`, `:::{deprecated}`, `:::{changed}`)
- [x] Canonical URL generation (older versions point to latest)
- [x] Sitemap with version awareness (priority: 0.8 latest, 0.3 older)
- [ ] Per-version redirect maps (deferred - use existing redirect system)
- [ ] Search integration (deferred - per-version or unified)

### Phase 4: Git Integration & Advanced ✅ COMPLETE
- [x] Git branch mode: build from multiple branches (`mode: git`)
- [x] Pattern-based branch/tag discovery (e.g., `release/*`)
- [x] Git worktree adapter for parallel version builds
- [x] CLI: `bengal build --all-versions`, `bengal build --version 0.1.6`
- [x] Version diffing: `bengal version diff v1 v2` + `--git` mode
- [x] Markdown changelog generation from diffs
- [ ] Auto-migration guide generation (deferred)
- [ ] API version detection from OpenAPI specs (deferred)

---

## Design Decisions

### 1. Cross-version links: `[[v2:docs/guide]]` syntax

**Decision:** Yes, implement cross-version linking syntax.

**Rationale:** No competitor offers this. It's a clear differentiator and solves a real problem (linking to specific version docs from migration guides, changelogs, etc.).

### 2. Should old versions be noindexed by default?

**Decision:** No. Index all versions by default.

**Rationale:** Users legitimately search for old version docs. Provide easy opt-in via config:
```yaml
seo:
  noindex_older_than: v1  # Only noindex v1 and older
```

### 3. Dev server: serve all versions or one?

**Decision:** Serve current version by default + version selector. Flag for all.

**Commands:**
```bash
bengal serve                    # Serves latest, version selector works
bengal serve --version v2       # Serves specific version
bengal serve --all-versions     # Serves all (slower startup)
```

### 4. Where does version selector live?

**Decision:** Bengal provides data + default partial. Theme can override.

- Bengal always provides `versions` and `current_version` in template context
- Ships `partials/version-selector.html` in default theme
- Themes override by providing their own partial

### 5. Breaking URL changes between versions?

**Decision:** Support per-version redirect maps.

```yaml
# _versions/v2/redirects.yaml
redirects:
  old-guide: new-guide
  api/old-endpoint: api/new-endpoint
```

Bengal generates redirects during build.

---

## Why This Beats Docusaurus

| Pain Point | Docusaurus | Bengal |
|------------|------------|--------|
| Shared changelog across versions | Copy to each version folder | `_shared/changelog.md` auto-included |
| Link to v2 docs from v3 migration guide | Manual relative paths, breaks easily | `[[v2:api/reference]]` |
| "Added in v2.1" badges | Custom MDX component | Built-in `:::{since}` directive |
| Team doesn't know React | Steep learning curve | Python/Jinja (familiar to most) |
| Multiple aliases (`lts`, `stable`) | Limited, workarounds needed | First-class support |

---

## Quick Reference

**Minimal setup:**
```yaml
versioning:
  enabled: true
  versions: [v3, v2, v1]
```

**Link to other versions:**
```markdown
See [[v2:getting-started]] for the old guide.
```

**Mark new features:**
```markdown
:::{since}
3.0
:::
```

**CLI:**
```bash
bengal version create v4    # Snapshot current docs as v4
bengal version list         # Show all versions
bengal serve --version v2   # Preview specific version
```

---

## Next Steps

1. ✅ RFC reviewed and updated
2. **Prototype** Phase 1 (config + discovery + default partial)
3. **Test** with Bengal's own site (version the docs!)
4. **Implement** Phase 2 (CLI + aliases + shared content)

---

## References

- [Docusaurus Versioning](https://docusaurus.io/docs/versioning)
- [Mike (MkDocs versioning)](https://github.com/jimporter/mike)
- [Read the Docs Versioning](https://docs.readthedocs.io/en/stable/versions.html)
- [Starlight Versioning](https://starlight.astro.build/guides/versioning/)
