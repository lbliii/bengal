# RFC: Kida-Native Release Single Template

| Field | Value |
|-------|-------|
| **Status** | Draft |
| **Created** | 2024-12-30 |
| **Updated** | 2024-12-30 |
| **Author** | Bengal Team |
| **Scope** | Non-Breaking Enhancement |
| **Goal** | Rich, YAML-driven release page template with labels, variants, and markdown support |

## Summary

Implement `changelog/single.html` as a Kida-native template for individual release pages. The template supports both narrative release notes and structured changelogs through a unified, YAML-driven schema with:

- **Label system** for badges (new, experimental, breaking, deprecated, etc.)
- **Variant support** via Component Model (`release-notes`, `compact`, `timeline`)
- **Markdown in fields** for rich descriptions with code blocks and links
- **Composable components** via `{% def %}` with lexical scoping
- **Pattern-matched change types** via `{% match %}`
- **Timeline navigation** to related releases

## Current State

### What Exists

The `changelog/list.html` template is **already fully implemented** (328 lines) with sophisticated Kida features:

```bash
$ wc -l bengal/themes/default/templates/changelog/*.html
     328 list.html   # ✅ Complete - data-driven + page-driven modes
       1 single.html # ❌ Empty - needs implementation
```

The list template already supports:
- `{% def %}` components (`change_category`, `release_item_data`, `release_item_page`)
- `{% while %}` loops for version traversal
- Optional chaining (`?.`) and null coalescing (`??`)
- Both data-driven (`data/changelog.yaml`) and page-driven modes

### What's Missing

Individual release pages (`single.html`) currently have no dedicated template. When users click a release from the list, they get generic page rendering without:
- Version badges and stats
- Categorized change display
- Breaking change callouts
- Migration guidance
- Related releases navigation

### Existing Content Pattern

Current release pages use narrative markdown with minimal frontmatter:

```yaml
---
title: Bengal 0.1.5
description: Named directive closers, media embeds...
type: changelog
date: 2025-12-22
---

# Bengal 0.1.5

**Key additions:** Named directive closers...

## Highlights
### Named Directive Closers
...narrative content...
```

This RFC preserves full backward compatibility while enabling richer structured data.

## Design

### 1. Enhanced Frontmatter Schema

The schema supports both release notes (narrative) and changelogs (structured) with a unified format:

```yaml
---
title: Bengal 1.0.0
description: First stable release with full feature set
type: changelog
variant: release-notes  # Component Model: release-notes | compact | timeline
date: 2025-06-15

# Version metadata
version:
  number: 1.0.0
  codename: Tiger
  status: stable        # alpha | beta | rc | stable | lts
  labels:               # Version-level labels
    - recommended
    - lts

# Structured changes with labels + markdown descriptions
changes:
  - type: added
    title: New shortcode system
    description: |
      Composable shortcodes with `{% def %}` syntax.
      See [migration guide](/docs/migration/shortcodes/).
    labels: [new, experimental]
    pr: 123

  - type: changed
    title: Config format migrated to TOML
    description: |
      Rename `bengal.yaml` → `bengal.toml`. Run:
      ```bash
      bengal migrate config
      ```
    labels: [breaking]
    migration: /docs/migration/toml/

  - type: security
    title: Fixed XSS in markdown rendering
    description: Sanitize HTML in `markdownify` filter.
    labels: [critical]
    severity: high
    cve: CVE-2025-1234

  - type: fixed
    title: Memory leak in dev server
    description: Connection pool now properly releases resources.
    issue: 456

  - type: deprecated
    title: Old template syntax
    description: Use `{% end %}` instead of `{% endif %}`.
    labels: [removal-2.0]
    removal_version: 2.0.0

  - type: removed
    title: Python 3.8 support
    description: Minimum version is now Python 3.14.

# Upgrade information
upgrade:
  from: 0.9.x
  migration_guide: /docs/migration/1.0/
  breaking_count: 2

# External links
links:
  docs: https://bengal.dev/docs/
  changelog: https://github.com/bengal/bengal/blob/main/CHANGELOG.md
  github: https://github.com/bengal/bengal/releases/tag/v1.0.0
---

Optional narrative content here (highlights, demos, getting started)...
```

### 2. Label System

Labels provide visual badges for changes and versions:

| Label | Badge Text | Color | Use Case |
|-------|------------|-------|----------|
| `new` | NEW | success | Just added features |
| `experimental` | EXPERIMENTAL | purple | May change in future |
| `api-preview` | API PREVIEW | info | Testing new API |
| `breaking` | BREAKING | danger | Requires migration |
| `critical` | CRITICAL | danger | Security/urgent fix |
| `deprecated` | DEPRECATED | warning | Will be removed |
| `removal-X.Y` | REMOVAL X.Y | warning | Scheduled removal version |
| `recommended` | RECOMMENDED | success | Upgrade encouraged |
| `lts` | LTS | info | Long-term support |
| `beta` | BETA | warning | Beta feature |
| `internal` | INTERNAL | neutral | Internal change |

Custom labels are supported—unknown labels render with neutral styling and uppercase text.

### 3. Variant Support (Component Model)

Using the existing Component Model `variant` field:

| Variant | Description | Best For |
|---------|-------------|----------|
| `release-notes` | Full narrative + structured changes | Major releases, announcements |
| `compact` | Condensed, list-only view | Patch releases, quick reference |
| `timeline` | Visual timeline emphasis | Historical browsing |

```yaml
---
type: changelog
variant: release-notes  # Default: full narrative mode
---
```

### 4. Template Architecture

A modular approach ensures visual consistency between the list and single views by sharing core components:

```
templates/changelog/
├── single.html          # Individual release page (calls components)
├── list.html            # ✅ Already exists (328 lines)
└── partials/
    └── _components.html # New: Shared badges, labels, and entry blocks
```

### 5. Shared Components (`partials/_components.html`)

Extracting these into a partial allows the `list.html` to adopt the same rich labeling system.

```kida
{# =============================================================================
   Shared Changelog Components
   ============================================================================= #}

{% def label_badge(label) %}
  {% match label %}
    {% case 'new' %}          <span class="label label--success">NEW</span>
    {% case 'experimental' %} <span class="label label--purple">EXPERIMENTAL</span>
    {% case 'breaking' %}     <span class="label label--danger">BREAKING</span>
    {% case 'critical' %}     <span class="label label--danger">CRITICAL</span>
    {% case 'deprecated' %}   <span class="label label--warning">DEPRECATED</span>
    {% case 'recommended' %}  <span class="label label--success">RECOMMENDED</span>
    {% case 'lts' %}          <span class="label label--info">LTS</span>
    {% case _ %}              <span class="label label--neutral">{{ label | upper }}</span>
  {% end %}
{% end %}

{% def change_badge(type) %}
  {% match type %}
    {% case 'added' %}    <span class="badge badge--success">✨ Added</span>
    {% case 'changed' %}  <span class="badge badge--info">🔄 Changed</span>
    {% case 'fixed' %}    <span class="badge badge--success">🐛 Fixed</span>
    {% case 'security' %} <span class="badge badge--danger">🔒 Security</span>
    {% case 'deprecated' %}<span class="badge badge--warning">⚠️ Deprecated</span>
    {% case 'removed' %}  <span class="badge badge--danger">🗑️ Removed</span>
    {% case _ %}          <span class="badge badge--neutral">📝 {{ type | capitalize }}</span>
  {% end %}
{% end %}

{% def severity_badge(severity, cve=none) %}
  {% match severity %}
    {% case 'critical' %} <div class="sev sev--danger">🚨 CRITICAL</div>
    {% case 'high' %}     <div class="sev sev--danger">🔶 HIGH</div>
    {% case 'medium' %}   <div class="sev sev--warning">🟡 MEDIUM</div>
    {% case _ %}          <div class="sev sev--info">ℹ️ {{ severity | upper }}</div>
  {% end %}
  {% if cve %}
    <a href="https://nvd.nist.gov/vuln/detail/{{ cve }}" class="cve-link">{{ cve }}</a>
  {% end %}
{% end %}
```

### 6. Single Release Template (`single.html`)

The main template is now concise and focuses on layout, delegating visual elements to shared components.

```kida
{% extends "base.html" %}
{% from 'changelog/partials/_components.html' import label_badge, change_badge, severity_badge %}
{% from 'partials/navigation-components.html' import breadcrumbs, page_navigation %}

{% block content %}
{% let p = page?.props ?? {} %}
{% let variant = page?.variant ?? 'release-notes' %}

<article class="release-page release-page--{{ variant }}">
  <header class="release-hero">
    <div class="container">
      {{ breadcrumbs(page) }}

      <div class="release-version">
        <span class="version-number">v{{ p.version?.number ?? '0.0.0' }}</span>
        {% for label in p.version?.labels ?? [] %}{{ label_badge(label) }}{% end %}
      </div>

      <h1 class="release-hero__title">{{ page.title }}</h1>
      {% if p.description %}<p class="hero-desc">{{ p.description }}</p>{% end %}
    </div>
  </header>

  <div class="container release-layout">
    <main class="release-main">
      {# Upgrade Callout #}
      {% if p.upgrade %}
        <aside class="upgrade-box">
          <h4>⬆️ Upgrading from {{ p.upgrade.from ?? 'previous' }}</h4>
          {% if p.upgrade.migration_guide %}
            <a href="{{ p.upgrade.migration_guide }}">Migration Guide →</a>
          {% end %}
        </aside>
      {% end %}

      {# Narrative Content #}
      {% if content %}<div class="prose">{{ content | safe }}</div>{% end %}

      {# Structured Changes #}
      {% if p.changes %}
        <section class="changes-list">
          {% for change in p.changes %}
            <div class="change-item">
              <div class="change-header">
                {{ change_badge(change.type) }}
                {% for l in change.labels ?? [] %}{{ label_badge(l) }}{% end %}
                <strong>{{ change.title }}</strong>
              </div>
              {% if change.description %}
                <div class="change-desc">{{ change.description | markdownify | safe }}</div>
              {% end %}
              {% if change.type == 'security' %}
                {{ severity_badge(change.severity, change.cve) }}
              {% end %}
            </div>
          {% end %}
        </section>
      {% end %}
    </main>

    <aside class="release-sidebar">
      {{ related_releases(page) }}
    </aside>
  </div>
</article>

{# Page Navigation #}
{{ page_navigation(page) }}
{% end %}

{% def related_releases(current) %}
  {# Efficient lookup restricted to same section #}
  {% let siblings = current.parent?.pages |> where('type', 'changelog') |> sort_by('date', reverse=true) |> take(6) %}
  <nav class="release-timeline">
    <h4>Release History</h4>
    <ul>
      {% for rel in siblings if rel.href != current.href %}
        <li><a href="{{ rel.href }}">{{ rel.title }}</a></li>
      {% end %}
    </ul>
  </nav>
{% end %}
```

### 6. CSS Architecture

Create a dedicated release components stylesheet:

```
themes/default/assets/css/components/
├── releases/
│   ├── _index.css          # Imports all
│   ├── version-badge.css   # Version display + status badges
│   ├── labels.css          # Label badge system
│   ├── change-entry.css    # Individual change items
│   ├── release-stats.css   # Stats bar/cards
│   ├── timeline.css        # Timeline visualization
│   └── upgrade-callout.css # Breaking change warnings
```

Key CSS variables for theming:

```css
:root {
  /* Change type colors */
  --release-added: var(--color-success, #22c55e);
  --release-changed: var(--color-info, #3b82f6);
  --release-deprecated: var(--color-warning, #f59e0b);
  --release-removed: var(--color-danger, #ef4444);
  --release-fixed: var(--color-success, #22c55e);
  --release-security: var(--color-danger, #ef4444);

  /* Label colors */
  --label-success: var(--color-success, #22c55e);
  --label-danger: var(--color-danger, #ef4444);
  --label-warning: var(--color-warning, #f59e0b);
  --label-info: var(--color-info, #3b82f6);
  --label-purple: #8b5cf6;
  --label-neutral: var(--color-muted, #6b7280);

  /* Timeline */
  --release-timeline-line: var(--color-border, #e5e7eb);
  --release-timeline-dot: var(--color-primary, #3b82f6);

  /* Version badges */
  --release-major-bg: var(--color-primary);
}

/* Variant modifiers */
.release-page--compact .release-body { display: none; }
.release-page--compact .release-changes { margin-top: 0; }
.release-page--timeline .release-sidebar { order: -1; flex: 0 0 300px; }
```

## Migration

### Existing Content Compatibility

Current release pages work unchanged:

```yaml
---
title: Bengal 0.1.5
description: ...
type: changelog
date: 2025-12-22
---

Narrative content here...
```

**What happens:**
- ✅ Title, description, date render in hero
- ✅ Markdown body renders in `.release-body`
- ✅ Stats bar hidden (no `changes` data)
- ✅ Timeline shows other releases

### Progressive Enhancement

Add structured data incrementally:

```yaml
---
title: Bengal 0.1.5
description: ...
type: changelog
date: 2025-12-22
# Add these for rich rendering:
version:
  number: 0.1.5
changes:
  - type: added
    title: Named directive closers
    labels: [new]
---
```

### Migration Script (Optional)

A future script could parse markdown bodies to extract changes:

```bash
bengal migrate releases --extract-changes
```

## Alternatives Considered

### Alternative A: Separate release-notes and changelog Types

Two distinct types with different templates.

**Rejected because:**
- Duplicates template logic
- Forces users to choose upfront
- Current `list.html` already handles both modes elegantly

### Alternative B: Icon-Based Labels (SVG)

Use `{{ icon('star', size=12) }}` instead of emoji.

**Considered but deferred:**
- Emoji works well, matches `list.html` style
- Icons can be added later via CSS/config
- Reduces template complexity

### Alternative C: Labels as Boolean Flags

```yaml
changes:
  - type: added
    breaking: true  # Instead of labels: [breaking]
    experimental: true
```

**Rejected because:**
- Less flexible—can't add custom labels
- More verbose for multiple labels
- Array approach is more extensible

## Success Criteria

| Criterion | Measurement |
|-----------|-------------|
| Backward compatible | Existing release pages render without changes |
| Shared Components | `list.html` and `single.html` share badge logic from `_components.html` |
| Labels render | All defined labels show correct badges via `{% match %}` |
| Variants work | `release-notes`, `compact`, `timeline` apply correctly |
| Performance | `related_releases` uses scoped parent lookup (O(1) vs O(N)) |
| Markdown in descriptions | Code blocks, links render properly |
| Matches list.html style | Visual consistency with existing template |

### Validation

```bash
# 1. Existing releases render
bengal build
# Verify /releases/0.1.5/ renders with narrative content

# 2. Structured release works
# Add test release with full schema, verify all features

# 3. Kida features
grep -E "\{% (def|match|let)" bengal/themes/default/templates/changelog/single.html
# Should find multiple matches

# 4. Modularity check
ls bengal/themes/default/templates/changelog/partials/_components.html
# File must exist
```

## Implementation Plan

| Phase | Duration | Deliverables |
|-------|----------|--------------|
| 1: Shared Components | 1 day | `partials/_components.html` with match patterns |
| 2: Core Template | 1 day | `single.html` calling shared components |
| 3: CSS | 1-2 days | Labels, badges, stats, timeline styles |
| 4: Integration | 0.5 day | Update `list.html` to use shared components |
| 5: Documentation | 0.5 day | Frontmatter schema reference |
| **Total** | ~4 days | |

## Future Enhancements

Out of scope for this RFC, but enabled by the architecture:

1. **Label filtering on list page** — Filter by `experimental`, `breaking`, etc.
2. **RSS/Atom feed** with label metadata
3. **Comparison view** between two versions
4. **Auto-extraction** — Parse markdown body into structured changes
5. **Custom labels via config** — Define project-specific labels in `theme.yaml`

## References

- Existing list template: `bengal/themes/default/templates/changelog/list.html`
- Component Model docs: `site/content/docs/content/organization/component-model.md`
- Blog single template: `bengal/themes/default/templates/blog/single.html`
- Kida syntax: `site/content/docs/theming/templating/kida/syntax/`
