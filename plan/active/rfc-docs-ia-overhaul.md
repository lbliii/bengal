# RFC: Documentation Information Architecture Overhaul

**Status**: Draft  
**Created**: 2025-12-03  
**Author**: AI Assistant + Human  
**Priority**: High  
**Confidence**: 88% 🟢  
**Est. Impact**: Improved discoverability, clearer user journeys, better content reuse

---

## Executive Summary

This RFC proposes a complete overhaul of the Bengal documentation site's information architecture (IA). The current structure mixes Diataxis types (tutorials, how-tos, explanations, references) in ways that make content hard to discover and maintain.

The new structure organizes documentation by **product/feature dimensions** (content, theming, building, extending) with nested capabilities under each, paired with relevant references at the point of need rather than in a separate silo.

**Key Changes**:
1. Reorganize around feature dimensions instead of Diataxis types
2. Create dedicated `tutorials/` for true learning journeys
3. Add `_snippets/` directory for reusable content fragments
4. Pair how-tos with scoped references within each dimension
5. Expand `recipes/` for quick copy-paste solutions

---

## Problem Statement

### Current State

The Bengal documentation site has this structure:

```
docs/
├── about/           # Understanding Bengal (concepts, FAQ, comparison)
├── getting-started/ # Onboarding (installation, quickstarts)
├── guides/          # Mixed content (tutorials + how-tos + explanations)
├── recipes/         # Quick solutions (underutilized, only 3 recipes)
└── reference/       # Architecture-heavy, lacks practical references
```

**Evidence**: `site/content/docs/` directory structure

### Pain Points

1. **`guides/` is a dumping ground**: Contains 14 files mixing:
   - True tutorials (`blog-from-scratch.md` - learning journey)
   - Task-focused how-tos (`content-collections.md` - specific task)
   - Conceptual explanations (`graph-analysis.md` - understanding)

   **Evidence**: `site/content/docs/guides/_index.md:20-43` lists content without clear categorization

2. **References are siloed from usage**: The `reference/` directory focuses on architecture but doesn't provide practical lookup references (frontmatter fields, config options, template functions) near where users need them.

   **Evidence**: `site/content/docs/reference/_index.md` only links to architecture, directives, and theme variables

3. **No content reuse infrastructure**: Common content (installation steps, prerequisites, CLI commands) is duplicated across multiple pages with no mechanism for DRY documentation.

   **Evidence**: Installation instructions appear in `installation.md`, README, and quickstart guides separately

4. **Feature discovery is poor**: Users asking "how do I use collections?" must hunt through `guides/` hoping to find the right file. There's no clear path from feature → documentation.

5. **Recipes underutilized**: Only 3 recipes exist despite this being a valuable format for quick wins.

   **Evidence**: `site/content/docs/recipes/` contains only `analytics.md`, `custom-404.md`, `search.md`

### User Impact

| Persona | Pain | Current Experience |
|---------|------|-------------------|
| **Writer** | Can't find how to organize content | Hunts through guides, hopes for the best |
| **Themer** | No clear theming section | Scatters across guides, reference, concepts |
| **Contributor** | Architecture docs exist but disconnected | Reference is isolated from practical guidance |
| **New User** | Overwhelmed by flat guide list | 14 guides with no clear starting point |

---

## Goals & Non-Goals

### Goals

1. **G1**: Organize docs by feature/capability dimensions that match user mental models
2. **G2**: Separate true tutorials (learning journeys) from how-tos (task completion)
3. **G3**: Place references at point-of-need, not in isolated silos
4. **G4**: Enable content reuse via `_snippets/` directory
5. **G5**: Expand recipes for common quick wins
6. **G6**: Improve discoverability through clear navigation hierarchy
7. **G7**: Demonstrate Bengal's content reuse features in our own docs

### Non-Goals

- **NG1**: Changing the theming/styling of the documentation site
- **NG2**: Rewriting content (just reorganizing and creating new index pages)
- **NG3**: Adding new features to Bengal (this is content organization only)
- **NG4**: Changing the auto-generated API/CLI reference structure

---

## Proposed Information Architecture

### Top-Level Structure

```
site/content/
├── _index.md                       # Homepage
├── _snippets/                      # Reusable content fragments (NEW)
│
└── docs/
    ├── about/                      # UNDERSTANDING BENGAL
    ├── get-started/                # FIRST STEPS
    ├── tutorials/                  # LEARNING JOURNEYS (NEW)
    ├── content/                    # CONTENT AUTHORING (NEW)
    ├── theming/                    # DESIGN & STYLING (NEW)
    ├── building/                   # BUILD & DEPLOY (NEW)
    ├── extending/                  # ADVANCED / CONTRIBUTOR (NEW)
    └── recipes/                    # QUICK WINS (EXPANDED)
```

### Dimension Details

#### 1. About (`/docs/about/`)

**Purpose**: Understanding Bengal - philosophy, concepts, comparisons

```
about/
├── _index.md               # What is Bengal
├── why-bengal.md           # Philosophy, differentiators
├── comparison.md           # vs Hugo, Jekyll, MkDocs
├── concepts.md             # Core mental model (consolidated)
├── faq.md
└── glossary.md
```

**Migration**: Consolidates current `about/concepts/` subdirectory into single `concepts.md`

---

#### 2. Get Started (`/docs/get-started/`)

**Purpose**: First steps for new users

```
get-started/
├── _index.md               # Choose your path
├── installation.md         # Uses {{ include "_snippets/install/*.md" }}
├── quickstart-writer.md
├── quickstart-themer.md
└── quickstart-contributor.md
```

**Migration**: Rename from `getting-started/` to `get-started/` (shorter, matches common patterns)

---

#### 3. Tutorials (`/docs/tutorials/`) — NEW

**Purpose**: True learning journeys - guided, sequential, hands-on

```
tutorials/
├── _index.md               # Tutorial index
├── build-a-blog.md         # Zero to deployed blog (from guides/)
├── migrate-from-hugo.md    # Migration walkthrough (from guides/)
└── automate-with-github-actions.md  # CI/CD setup (from guides/)
```

**Migration**:
- Move `guides/blog-from-scratch.md` → `tutorials/build-a-blog.md`
- Move `guides/migrating-content.md` → `tutorials/migrate-from-hugo.md`
- Move `guides/ci-cd-setup.md` → `tutorials/automate-with-github-actions.md`

---

#### 4. Content (`/docs/content/`) — NEW

**Purpose**: Everything about content authoring in Bengal

```
content/
├── _index.md                   # Overview + quick links
│
├── organization/               # Structure
│   ├── _index.md               # Pages, sections, bundles
│   ├── frontmatter.md          # Ref: all frontmatter fields
│   └── menus.md                # Navigation menus
│
├── authoring/                  # Writing
│   ├── _index.md               # Markdown, MyST basics
│   ├── directives.md           # Ref: all directives
│   └── shortcodes.md           # Using/creating shortcodes
│
├── collections/                # Typed schemas
│   ├── _index.md               # What, why, when
│   ├── define-schemas.md       # Custom schemas
│   ├── validate.md             # Validation modes
│   └── built-in-schemas.md     # Ref: BlogPost, DocPage, etc.
│
├── sources/                    # Content origins
│   ├── _index.md               # Local vs remote
│   ├── github.md               # GitHub loader
│   ├── notion.md               # Notion loader
│   ├── rest-api.md             # REST API loader
│   └── custom-loaders.md       # Build your own
│
└── reuse/                      # Content reuse
    ├── _index.md               # Reuse strategies overview
    ├── snippets.md             # Using _snippets (meta!)
    ├── data-files.md           # YAML/JSON data
    └── filtering.md            # Taxonomies, queries
```

**Migration**:
- Move `guides/content-collections.md` → `content/collections/_index.md`
- Move `guides/content-sources.md` → `content/sources/_index.md` (split into subpages)
- Move `guides/content-reuse.md` → `content/reuse/_index.md`
- Move `guides/advanced-filtering.md` → `content/reuse/filtering.md`
- Move `reference/directives/` → `content/authoring/directives.md` (consolidate)
- Move `about/concepts/content-organization.md` → `content/organization/_index.md`

---

#### 5. Theming (`/docs/theming/`) — NEW

**Purpose**: Everything about design and styling

```
theming/
├── _index.md                   # Overview + quick links
│
├── templating/                 # Jinja2
│   ├── _index.md               # Template basics
│   ├── layouts.md              # Layouts & inheritance
│   ├── partials.md             # Reusable fragments
│   └── functions.md            # Ref: template functions
│
├── assets/                     # Static assets
│   ├── _index.md               # Asset pipeline overview
│   ├── stylesheets.md          # CSS handling
│   ├── javascript.md           # JS handling
│   ├── images.md               # Optimization, responsive
│   └── fonts.md                # Custom fonts
│
├── themes/                     # Theme packages
│   ├── _index.md               # Using themes
│   ├── customize.md            # Override without fork
│   └── create.md               # Create from scratch
│
└── variables.md                # Ref: all theme variables
```

**Migration**:
- Move `guides/customizing-themes.md` → `theming/themes/customize.md`
- Move `reference/theme-variables.md` → `theming/variables.md`
- Move `reference/template-functions.md` → `theming/templating/functions.md`
- Move `about/concepts/assets.md` → `theming/assets/_index.md`
- Move `about/concepts/templating.md` → `theming/templating/_index.md`

---

#### 6. Building (`/docs/building/`) — NEW

**Purpose**: Build configuration, CLI usage guides, and deployment.

*Note: The `commands/` directory contains human-written guides and common workflows. Comprehensive flag references remain in the auto-generated `/cli/` section, which these guides will link to.*

```
building/
├── _index.md                   # Overview + quick links
│
├── configuration/              # Config
│   ├── _index.md               # bengal.toml basics
│   ├── options.md              # Ref: all config options
│   └── environments.md         # Dev/staging/prod configs
│
├── commands/                   # CLI Guides (Human-Written)
│   ├── _index.md               # CLI workflow overview
│   ├── build.md                # Guide: Production build workflows
│   ├── serve.md                # Guide: Local development workflows
│   ├── new.md                  # Guide: Scaffolding new projects
│   └── validate.md             # Guide: Running health checks
│
├── performance/                # Speed
│   ├── _index.md               # Performance overview
│   ├── incremental.md          # Incremental builds
│   ├── parallel.md             # Parallel processing
│   └── caching.md              # Cache system
│
└── deployment/                 # Ship it
    ├── _index.md               # Deployment overview
    ├── netlify.md              # Deploy to Netlify
    ├── vercel.md               # Deploy to Vercel
    ├── github-pages.md         # Deploy to GH Pages
    └── ci-cd.md                # General CI/CD patterns
```

**Migration**:
- Move `guides/deployment.md` → `building/deployment/_index.md` (split into subpages)
- Move `about/concepts/configuration.md` → `building/configuration/_index.md`
- Move `about/concepts/build-pipeline.md` → `building/performance/_index.md`
- Create human-readable command guides in `building/commands/` that link to auto-generated `/cli/` references

---

#### 7. Extending (`/docs/extending/`) — NEW

**Purpose**: Advanced features and contributor documentation

```
extending/
├── _index.md                   # Overview
│
├── autodoc/                    # Doc generation
│   ├── _index.md               # Autodoc overview
│   ├── python.md               # Python API docs
│   ├── cli.md                  # CLI docs
│   └── openapi.md              # OpenAPI docs
│
├── analysis/                   # Site analysis
│   ├── _index.md               # Analysis tools overview
│   ├── graph.md                # Graph analysis
│   └── link-suggestions.md     # Internal linking
│
├── validation/                 # Health checks
│   ├── _index.md               # Validation overview
│   ├── health-checks.md        # Built-in checks
│   ├── autofix.md              # Auto-fix system
│   └── custom-validators.md
│
└── architecture/               # For contributors
    ├── _index.md               # Architecture overview
    ├── object-model.md         # Site, Page, Section
    ├── build-pipeline.md       # How builds work
    ├── plugin-api.md           # Extension points
    └── contributing.md         # Dev setup, PR guide
```

**Migration**:
- Move `guides/graph-analysis.md` → `extending/analysis/graph.md`
- Move `reference/architecture/` → `extending/architecture/`
- Create new autodoc docs
- Create new validation docs from health check system

---

#### 8. Recipes (`/docs/recipes/`) — EXPANDED

**Purpose**: Quick copy-paste solutions (5-15 minutes)

```
recipes/
├── _index.md               # Recipe index
├── add-search.md           # Pagefind integration (existing)
├── add-analytics.md        # GA, Plausible, Fathom (existing)
├── custom-404.md           # Branded error page (existing)
├── dark-mode.md            # Theme toggle (NEW)
├── rss-feed.md             # RSS setup (NEW)
├── og-images.md            # Open Graph images (NEW)
├── reading-time.md         # Estimated reading time (NEW)
├── table-of-contents.md    # Custom TOC (NEW)
└── syntax-highlighting.md  # Code block themes (NEW)
```

#### 9. Curated Tracks (`/tracks/`) — GENERATED

**Purpose**: Guided learning paths combining tutorials and concepts. Defined in YAML and generated to leverage the new content structure.

**Proposed Tracks**:
1. **Content Author Track**: `getting-started` → `content/authoring` → `content/collections`
2. **Theme Developer Track**: `getting-started` → `theming/templates` → `theming/assets` → `theming/themes`
3. **Site Architect Track**: `building/configuration` → `content/collections` → `extending/architecture`

---

### `_snippets/` Directory — NEW

**Purpose**: Reusable content fragments for DRY documentation

```
_snippets/
├── _index.md                   # Meta: explains the snippet system
│
├── install/                    # Installation snippets
│   ├── pip.md                  # pip install bengal
│   ├── uv.md                   # uv add bengal
│   ├── pipx.md                 # pipx install bengal
│   └── from-source.md          # git clone + pip install -e
│
├── prerequisites/              # Requirement snippets
│   ├── python.md               # Python 3.14+ requirement
│   ├── git.md                  # Git requirement
│   └── optional-deps.md        # Optional dependencies
│
├── config/                     # Config example snippets
│   ├── minimal.md              # Minimal bengal.toml
│   ├── blog.md                 # Blog-focused config
│   ├── docs.md                 # Docs-focused config
│   └── full.md                 # Full config with all options
│
├── cli/                        # CLI snippets
│   ├── quick-reference.md      # Common commands table
│   ├── build-options.md        # Build command options
│   └── serve-options.md        # Serve command options
│
├── warnings/                   # Callout snippets
│   ├── breaking-change.md      # Breaking change warning
│   ├── experimental.md         # Experimental feature notice
│   └── deprecated.md           # Deprecation notice
│
└── support/                    # Support info snippets
    ├── channels.md             # GitHub, Discord, etc.
    └── reporting-bugs.md       # How to report issues
```

**Usage Pattern**:

```markdown
## Installation

Choose your package manager:

::::{tab-set}
:::{tab-item} pip
{{< include "_snippets/install/pip.md" >}}
:::
:::{tab-item} uv
{{< include "_snippets/install/uv.md" >}}
:::
::::

{{< include "_snippets/prerequisites/python.md" >}}
```

---

## Migration Plan

### Phase 1: Foundation (Day 1-2)

1. Create new directory structure (empty `_index.md` placeholders)
2. Create `_snippets/` directory with initial content
3. Update navigation configuration
4. Create redirects map for moved content

### Phase 2: Content Migration (Day 3-5)

**Priority Order**:

1. **High Traffic Pages First**:
   - `get-started/installation.md`
   - `content/collections/`
   - `content/sources/`
   - `building/commands/`

2. **Tutorial Extraction**:
   - Move tutorial content to `tutorials/`
   - Ensure learning paths remain intact

3. **Reference Consolidation**:
   - Move reference content to feature dimensions
   - Update cross-links

### Phase 3: Content Enhancement (Day 6-8)

1. Create missing `_index.md` overview pages
2. Add new recipes
3. Implement snippet includes
4. Verify all internal links

### Phase 4: Cleanup (Day 9-10)

1. Remove old structure
2. Verify redirects work
3. Update external links (README, etc.)
4. Final navigation testing

---

## Content Mapping

### Files to Move

| Current Location | New Location |
|------------------|--------------|
| `about/concepts/*.md` | Distributed to feature dimensions |
| `getting-started/` | `get-started/` |
| `guides/blog-from-scratch.md` | `tutorials/build-a-blog.md` |
| `guides/migrating-content.md` | `tutorials/migrate-from-hugo.md` |
| `guides/ci-cd-setup.md` | `tutorials/automate-with-github-actions.md` |
| `guides/content-collections.md` | `content/collections/_index.md` |
| `guides/content-sources.md` | `content/sources/_index.md` |
| `guides/content-reuse.md` | `content/reuse/_index.md` |
| `guides/advanced-filtering.md` | `content/reuse/filtering.md` |
| `guides/customizing-themes.md` | `theming/themes/customize.md` |
| `guides/deployment.md` | `building/deployment/_index.md` |
| `guides/graph-analysis.md` | `extending/analysis/graph.md` |
| `reference/directives/` | `content/authoring/directives.md` |
| `reference/theme-variables.md` | `theming/variables.md` |
| `reference/template-functions.md` | `theming/templating/functions.md` |
| `reference/architecture/` | `extending/architecture/` |

### Files to Create

| New File | Content Source |
|----------|----------------|
| `tutorials/_index.md` | New index page |
| `content/_index.md` | New overview |
| `content/organization/_index.md` | From `concepts/content-organization.md` |
| `content/authoring/_index.md` | New, consolidates markdown guidance |
| `theming/_index.md` | New overview |
| `theming/templating/_index.md` | From `concepts/templating.md` |
| `theming/assets/_index.md` | From `concepts/assets.md` |
| `building/_index.md` | New overview |
| `building/configuration/_index.md` | From `concepts/configuration.md` |
| `building/performance/_index.md` | From `concepts/build-pipeline.md` |
| `extending/_index.md` | New overview |
| `extending/autodoc/_index.md` | New |
| `extending/validation/_index.md` | New |
| All `_snippets/` content | New |
| New recipes | New |

### Files to Delete (After Migration)

- `guides/_index.md` (replaced by feature dimensions)
- `guides/content-workflow.md` (absorbed into `content/`)
- `guides/curated-tracks.md` (absorbed into `content/reuse/`)
- `guides/troubleshooting.md` (distributed to relevant sections)
- `about/concepts/` directory (distributed)

---

## Tradeoffs & Risks

### Tradeoffs

| Gain | Lose |
|------|------|
| Clear feature-based navigation | Flat guide list (some users prefer this) |
| References at point of need | Single reference location |
| DRY content via snippets | Simpler file structure |
| Better discoverability | Deeper nesting (more clicks) |
| Demonstrates Bengal features | More complex site structure |

### Risks

#### Risk 1: Broken Links

**Description**: External links and bookmarks will break

- **Likelihood**: High
- **Impact**: Medium
- **Mitigation**:
  - Create comprehensive redirect map
  - Use Bengal's alias feature for old URLs
  - Update README, PyPI, external docs

#### Risk 2: User Confusion During Transition

**Description**: Users familiar with old structure may be disoriented

- **Likelihood**: Medium
- **Impact**: Low
- **Mitigation**:
  - Add "What's New" banner with migration guide
  - Ensure search indexes are updated
  - Keep redirects active for 6+ months

#### Risk 3: Incomplete Migration

**Description**: Some content may be forgotten or misplaced

- **Likelihood**: Medium
- **Impact**: Medium
- **Mitigation**:
  - Create checklist of all current files
  - Verify each file has destination
  - Run link checker after migration

#### Risk 4: Over-Nesting

**Description**: Too many directory levels hurt UX

- **Likelihood**: Low
- **Impact**: Medium
- **Mitigation**:
  - Max 3 levels deep (`docs/content/collections/`)
  - Consolidate thin directories
  - Use flat files where appropriate

---

## Success Metrics

1. **Navigation Depth**: Average clicks to find content ≤ 3
2. **Bounce Rate**: Decrease in docs section bounce rate
3. **Search Queries**: Reduction in "where is X" type searches
4. **Content Reuse**: ≥10 snippet includes across docs
5. **Recipe Growth**: ≥10 recipes within 3 months

---

## Open Questions

- [x] **Q1**: Should `tracks/` learning paths be migrated or kept separate? (Resolved: Keep separate, generate from YAML based on new IA)
- [ ] **Q2**: How to handle auto-generated `/api/` and `/cli/` documentation?
- [ ] **Q3**: Should we add search-specific metadata to improve discoverability?
- [ ] **Q4**: Priority order for new recipe creation?

---

## Approval

- [ ] IA structure reviewed and approved
- [ ] Migration plan approved
- [ ] Redirect strategy approved

---

## RFC Quality Checklist

- [x] Problem statement clear with evidence
- [x] Goals and non-goals explicit
- [x] Detailed proposed structure
- [x] Complete migration mapping
- [x] Risks identified with mitigations
- [x] Implementation phases defined
- [x] Content mapping provided
- [x] Success metrics defined
- [x] Confidence ≥ 85% (88%)
