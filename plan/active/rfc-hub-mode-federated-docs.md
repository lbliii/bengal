# RFC: Hub Mode for Federated Multi-Site Documentation

**Status**: Draft  
**Created**: 2025-10-23  
**Author**: System Design  

---

## Executive Summary

Enable Bengal to operate in "hub mode" - a configuration where a parent site aggregates metadata from 300+ independent satellite documentation sites, providing unified discovery, navigation, and search while maintaining team autonomy and parallel build workflows.

**Target use case**: Enterprise organizations with hundreds of product documentation sites, currently managing them as chaotic S3 folders with no central registry or consistent discovery.

---

## Problem Statement

### Current Pain Points

Large organizations with 100+ products face terrible options:

1. **Monorepo documentation**:
   - Coordination nightmare across teams
   - Slow builds (N products × content size)
   - Tight coupling (one product's change blocks others)
   - Versioning complexity

2. **Completely separate sites**:
   - No discoverability (users don't know what exists)
   - Inconsistent structure across products
   - No unified search
   - Users get lost navigating between products

3. **Commercial platforms** (GitBook, ReadMe):
   - Expensive at scale (300 products = $$$)
   - Vendor lock-in
   - Often still suffer from discovery problems

4. **S3 chaos** (real-world example):
   ```
   s3://docs-bucket/
     product-a/v1/index.html
     product-a/v2/index.html
     product-b/latest/index.html
     product-c/docs/main/index.html  ← inconsistent paths
     old-product-d/...                ← deprecated, nobody knows
     random-folder/???                ← nobody knows what this is
   ```
   - No single source of truth
   - Can't tell what's active vs. deprecated
   - No consistent structure
   - Impossible to discover what exists

### Requirements

**Must Have**:
- Team autonomy (each product owns their docs, builds independently)
- Parallel builds (300 teams don't block each other)
- Unified discovery (central registry of all products)
- Versioning support (multiple versions per product)
- Graceful degradation (handle satellite downtime)
- Hourly sync acceptable (no real-time requirement)

**Should Have**:
- Namespaced search (search within product or across all)
- Cross-product linking (intersphinx-style)
- Status management (active/deprecated/beta)
- Category/taxonomy organization

**Nice to Have**:
- Analytics aggregation
- Automated dependency tracking
- Content freshness indicators
- API documentation cross-linking

---

## Proposed Solution

### Metadata Federation Architecture

**Each product is independent**, hub aggregates metadata at build time:

```
┌─────────────────────────────────────────────────────────┐
│ Hub Site (bengal in hub mode)                           │
│                                                          │
│  ┌──────────────────────────────────────────────────┐  │
│  │ Fetches index.json from each satellite           │  │
│  │ Caches locally (1hr TTL)                         │  │
│  │ Aggregates search indexes                        │  │
│  │ Generates unified directory/navigation           │  │
│  └──────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────┘
                           │
        ┌──────────────────┼──────────────────┐
        ▼                  ▼                  ▼
   ┌─────────┐       ┌─────────┐       ┌─────────┐
   │Product A│       │Product B│  ...  │Product N│
   │ (Bengal)│       │ (Bengal)│       │ (Bengal)│
   │         │       │         │       │         │
   │Generates│       │Generates│       │Generates│
   │index.json│      │index.json│      │index.json│
   └─────────┘       └─────────┘       └─────────┘
```

**Key insight**: Bengal already generates `index.json` for every site. We just need to:
1. Fetch them from satellites
2. Aggregate the data
3. Render a hub directory

---

## Design Details

### 1. Enhanced `index.json` Schema

Extend the existing schema with hub-mode metadata:

```json
{
  "site": {
    "title": "Bengal",
    "description": "...",
    "baseurl": "/bengal",
    "build_time": "2025-10-23T22:25:03.389509",

    // NEW: Hub-mode metadata
    "product": "bengal-core",
    "version": "0.1.3",
    "is_latest": true,
    "status": "active",  // or "deprecated", "beta"
    "namespace": "bengal"  // for search/cross-linking
  },

  "pages": [...],  // unchanged

  // NEW: Cross-link registry (flat lookup for fast resolution)
  "cross_link_registry": {
    "bengal:Site": "/api/core/site/#Site",
    "bengal:Site.build": "/api/core/site/#Site.build",
    "bengal:Page": "/api/core/page/#Page"
  },

  // EXISTING: Search index (already supported)
  "search_index": [
    {
      "objectID": "bengal/api/core/site",
      "title": "core.site",
      "url": "/api/core/site/",
      "content": "...",
      "namespace": "bengal@0.1.3"  // NEW: namespace for scoping
    }
  ]
}
```

**Backwards compatibility**: Sites without hub metadata work fine, hub just uses defaults.

### 2. Hub Site Configuration

```toml
# hub-site/bengal.toml
[site]
title = "Acme Documentation Hub"
mode = "hub"  # NEW: tells Bengal this is a hub site

[hub]
update_on_build = true
cache_dir = ".cache/satellites"
cache_ttl = 3600  # 1 hour
fail_on_missing = false  # use cached data if satellite is down

# Satellite product registry
[[hub.satellites]]
name = "Product A"
namespace = "product-a"
metadata_url = "https://product-a.docs.corp.com/index.json"
icon = "icons/product-a.svg"
category = "Developer Tools"
status = "active"
priority = 1  # for sorting

[[hub.satellites]]
name = "Product B"
namespace = "product-b"
metadata_url = "https://product-b.docs.corp.com/index.json"
icon = "icons/product-b.svg"
category = "Analytics"
status = "beta"
priority = 2

[[hub.satellites]]
name = "Legacy Product"
namespace = "legacy"
metadata_url = "https://legacy.docs.corp.com/index.json"
status = "deprecated"
deprecated_date = "2024-01-15"
replacement = "product-a"  # link to replacement
priority = 99

# Search configuration
[hub.search]
default_scope = "latest_only"  # or "all_versions"
namespaces = ["product-a", "product-b"]  # enable cross-product search

# Cross-linking configuration
[hub.cross_links]
enabled = true
syntax = "namespace:symbol"  # e.g., [product-a:api.create]
```

### 3. Satellite Product Configuration

Each product site adds minimal metadata:

```toml
# product-a/bengal.toml
[site]
title = "Product A Documentation"

[hub_metadata]
product = "product-a"
version = "2.1.0"
is_latest = true
status = "active"
namespace = "product-a"

# Optional: enable cross-linking to other products
[hub_metadata.cross_links]
[[hub_metadata.cross_links.external]]
product = "product-b"
registry_url = "https://product-b.docs.corp.com/index.json"
```

### 4. Caching & Fallback Strategy

```python
# bengal/discovery/hub_discovery.py
class SatelliteCache:
    def fetch_with_fallback(self, satellite):
        """Fetch satellite metadata with intelligent fallback."""

        try:
            # Try to fetch fresh data
            fresh_data = self._fetch_url(
                satellite.metadata_url,
                timeout=10
            )
            self._cache_write(satellite.name, fresh_data)
            return fresh_data, "fresh"

        except (Timeout, NetworkError) as e:
            # Fall back to cache
            cached = self._cache_read(satellite.name)
            if cached:
                logger.warning(
                    f"{satellite.name} unreachable, "
                    f"using cache (age: {cached.age})"
                )
                return cached.data, "stale"
            else:
                logger.error(
                    f"{satellite.name} unreachable "
                    f"and no cache available"
                )
                return None, "failed"
```

**Hub build output**:
```
Building hub site...
✓ Fetched 287 satellites (fresh)
⚠ Using cached data for 12 satellites (stale, avg age: 2.3 hours)
✗ Failed to load 1 satellite: product-xyz (no cache available)

Hub site built successfully.
Products: 287 active, 12 stale, 1 unavailable
```

### 5. Search Strategy

#### Option A: Namespaced Search (Recommended MVP)

**Default**: Search latest versions only

```javascript
// Hub site search
searchIndex = satellites
  .filter(s => s.is_latest)  // only latest versions
  .flatMap(s => s.search_index)
  .map(entry => ({
    ...entry,
    namespace: entry.namespace || s.product
  }));
```

**Advanced**: User can scope search

```html
<!-- Hub site search UI -->
<select id="search-scope">
  <option value="all">All Products (Latest)</option>
  <option value="product-a">Product A Only</option>
  <option value="product-a@2.0.0">Product A v2.0.0</option>
</select>

<input type="search" id="search-query" />
```

```javascript
// Filtered search
searchIndex = satellites
  .filter(s => matchesScope(s, selectedScope))
  .flatMap(s => s.search_index);
```

**Benefits**:
- Manageable index size (~300 products, not 300×N versions)
- Fast client-side search
- Progressive enhancement (can add version search later)

#### Option B: Federated Search (Defer to Phase 3)

Query each satellite's search endpoint at runtime:

```javascript
// Query all satellites in parallel
const results = await Promise.all(
  satellites.map(s =>
    fetch(`${s.base_url}/search?q=${query}`)
  )
);
```

**Pros**: Always fresh, smaller hub index  
**Cons**: Slower, requires 300 HTTP requests, complex error handling

**Decision**: Start with Option A, consider Option B later if index size becomes problematic.

### 6. Cross-Linking (Intersphinx-Style)

Enable cross-product linking with `namespace:symbol` syntax:

```markdown
<!-- In Product B docs -->
See [Product A's user creation API](product-a:api.users.create) for details.

<!-- Bengal resolves at build time -->
See [Product A's user creation API](https://product-a.docs.corp.com/api/users/#create) for details.
```

**Link resolution**:
1. Parse link syntax: `product-a:api.users.create`
2. Look up product-a's `cross_link_registry` (from cached `index.json`)
3. Find `api.users.create` → `/api/users/#create`
4. Resolve full URL: `https://product-a.docs.corp.com/api/users/#create`

**Implementation**:
```python
# bengal/rendering/filters/hub_filters.py
def resolve_cross_link(link_ref: str, hub_registry: dict) -> str:
    """
    Resolve cross-product link reference.

    Examples:
        product-a:api.create → https://product-a.docs.corp.com/api/#create
        bengal:Site.build → https://bengal.docs/api/core/site/#Site.build
    """
    if ':' not in link_ref:
        return link_ref  # not a cross-link

    namespace, symbol = link_ref.split(':', 1)

    # Look up in hub registry
    registry_key = f"{namespace}:{symbol}"
    if registry_key in hub_registry:
        return hub_registry[registry_key]

    logger.warning(f"Cross-link not found: {link_ref}")
    return link_ref  # fallback to original
```

### 7. Hub Theme & Templates

Hub sites get special template context:

```jinja2
{# themes/hub/index.html #}
<div class="hub-directory">
  <h1>{{ site.title }}</h1>

  {% for category in site.hub.categories %}
  <section class="product-category">
    <h2>{{ category.name }}</h2>

    <div class="products-grid">
      {% for product in category.products %}
      <div class="product-card {{ product.status }}">
        <img src="{{ product.icon }}" alt="{{ product.name }}" />
        <h3>{{ product.name }}</h3>
        <p>{{ product.description }}</p>

        <div class="product-meta">
          <span class="version">v{{ product.version }}</span>
          <span class="status-badge">{{ product.status }}</span>
          <span class="page-count">{{ product.page_count }} pages</span>
        </div>

        <a href="{{ product.base_url }}" class="btn">View Docs</a>

        {% if product.status == 'deprecated' %}
          <div class="deprecation-notice">
            Deprecated since {{ product.deprecated_date }}.
            Use <a href="{{ product.replacement_url }}">{{ product.replacement }}</a> instead.
          </div>
        {% endif %}
      </div>
      {% endfor %}
    </div>
  </section>
  {% endfor %}
</div>

{# Hub search #}
<div class="hub-search">
  <input type="search" placeholder="Search across all products..." />
  <div class="search-scope">
    <label>
      <input type="radio" name="scope" value="all" checked />
      All Products (Latest)
    </label>
    {% for product in site.hub.products %}
    <label>
      <input type="radio" name="scope" value="{{ product.namespace }}" />
      {{ product.name }} only
    </label>
    {% endfor %}
  </div>
</div>
```

### 8. CLI Commands for Hub Operations

While the MVP can work with just `bengal build`, operational tooling becomes essential at scale (300+ satellites).

#### Critical Commands (Ship with Production)

##### `bengal build` (Hub Mode)

**No new command needed** - existing build command detects hub mode:

```bash
$ bengal build

# Internally detects [site] mode = "hub" in config
# Routes to hub_orchestrator instead of normal build
```

**Output**:
```
Building hub site...
Fetching satellite metadata...
[████████████████████] 300/300 (2m 15s)

✓ Fetched 287 satellites (fresh)
⚠ Using cached data for 12 satellites (stale, avg age: 2.3 hours)
✗ Failed to load 1 satellite: product-xyz (no cache available)

Aggregating search indexes...
Generating hub pages...

Build complete: /public/
Products: 287 active, 12 stale, 1 unavailable
```

##### `bengal hub status` ⭐ **Critical**

**Purpose**: Visibility into hub health and satellite connectivity.

```bash
$ bengal hub status

Hub: Acme Documentation Hub
Satellites: 300 configured

Status:
✓ 287 reachable (fresh)
⚠ 12 using cache (stale, avg age: 3.2 hours)
✗ 1 unreachable: legacy-product (no cache)

Top stale satellites:
  - product-xyz: 48 hours old
  - beta-service: 36 hours old
  - old-api: 24 hours old

Cache stats:
- Cache directory: .cache/satellites/
- Total size: 45.2 MB
- Oldest cache: product-xyz (48 hours old)

Next sync: in 42 minutes (scheduled hourly)
```

**Why critical**: With 300 satellites, you need operational visibility. This is your health dashboard.

**Implementation**: ~100 lines of code, 2 hours.

##### `bengal hub sync` ⭐ **Critical**

**Purpose**: Force refresh satellite metadata (bypass cache).

```bash
# Sync all satellites
$ bengal hub sync

Syncing 300 satellites...
[████████████████████] 300/300 (2m 15s)

Results:
✓ 298 fetched successfully
✗ 2 failed:
  - legacy-product: Connection timeout
  - beta-service: 404 Not Found

Caches updated. Run 'bengal build' to regenerate site.

# Sync specific satellite
$ bengal hub sync --satellite product-a

✓ product-a refreshed
Cache updated (was 8 hours old)

# Sync only stale satellites (older than TTL)
$ bengal hub sync --stale-only

Found 12 stale satellites
[████████████████████] 12/12

✓ 11 refreshed
✗ 1 failed: legacy-product (timeout)
```

**Why critical**: When a satellite goes down and comes back up, you can't wait for TTL to expire. Need immediate control.

**Implementation**: ~50 lines of code (reuses fetch logic), 1 hour.

#### Important Commands (Phase 2)

##### `bengal hub validate` 🟡 **Important**

**Purpose**: Pre-deployment validation of hub configuration and satellite health.

```bash
$ bengal hub validate

Validating hub configuration...

Config validation:
✓ bengal.toml syntax valid
✓ 300 satellites configured
✓ No duplicate namespaces
✓ All categories defined
✗ Warning: 2 satellites missing icons

Checking satellite connectivity...
[████████████████████] 300/300

✓ 298 satellites reachable
✗ 2 satellites unreachable:
  - legacy-product: Connection timeout
  - beta-service: 404 Not Found

Schema validation:
✓ 298 satellites have valid index.json
✗ 2 satellites using old schema (missing 'namespace' field)

Validating cross-links...
Found 1,247 cross-link references
✓ 1,245 resolved successfully (99.8%)
✗ 2 broken links:
  - product-b → product-a:api.old_method (not in registry)
  - product-c → legacy:utils.deprecated (satellite unreachable)

Summary:
✓ Hub is operational (99.6% availability)
⚠ 2 satellites need attention
⚠ 2 broken cross-links found

Recommendation: Fix unreachable satellites before deploying.
```

**Why important**: Catch config errors, broken cross-links, and connectivity issues before build/deploy.

**Use cases**:
- Pre-commit hooks
- CI/CD validation
- On-call debugging

**Implementation**: ~150 lines of code, 3-4 hours (cross-link checking adds complexity).

#### Nice-to-Have Commands (Phase 3)

##### `bengal hub add <url>` 🟢 **Nice to have**

**Purpose**: Quickly add new satellite to hub (convenience over manual TOML editing).

```bash
$ bengal hub add https://new-product.docs.corp.com/index.json

Fetching satellite metadata...
✓ Reachable
  Name: New Product
  Version: 1.0.0
  Pages: 42
  Namespace: new-product

Add to bengal.toml? [Y/n] y

Added to bengal.toml:

[[hub.satellites]]
name = "New Product"
namespace = "new-product"
metadata_url = "https://new-product.docs.corp.com/index.json"
status = "active"
# TODO: Set category, icon, priority

✓ Satellite added
⚠ Edit bengal.toml to set category and icon
Run 'bengal build' to regenerate hub.
```

**Why nice-to-have**: Convenience, but users can manually edit TOML. Not critical.

**Implementation**: ~80 lines of code, 2 hours.

##### `bengal hub info <satellite>` 🟢 **Nice to have**

**Purpose**: Detailed information about specific satellite.

```bash
$ bengal hub info product-a

Name: Product A
Namespace: product-a
Status: active
Version: 2.1.0 (latest)
URL: https://product-a.docs.corp.com
Category: Developer Tools
Icon: icons/product-a.svg
Priority: 1

Statistics:
- Pages: 342
- Last updated: 2 hours ago (2025-10-23 14:30:00)
- Cache age: 15 minutes (fresh)
- Cache file: .cache/satellites/product-a.json

Cross-link registry:
- 156 symbols available
- 23 incoming links from other products
- 8 outgoing links to other products

Recent changes:
- api.users.create: Added
- api.auth.legacy_login: Deprecated
```

**Why nice-to-have**: Useful for debugging and exploration, but not operationally critical.

**Implementation**: ~60 lines of code, 1 hour.

##### `bengal hub cache clear` 🟢 **Optional**

**Purpose**: Clear satellite caches (nuclear option for debugging).

```bash
$ bengal hub cache clear

Clear all satellite caches? [y/N] y

Removed 300 cached files (45.2 MB)
Run 'bengal hub sync' to rebuild caches.

# Clear specific satellite
$ bengal hub cache clear --satellite product-a

✓ Removed cache for product-a
Run 'bengal hub sync --satellite product-a' to refresh.
```

**Why optional**: Rarely needed. `bengal hub sync` already bypasses cache. Mainly useful for debugging cache corruption.

**Implementation**: ~30 lines of code, 30 minutes.

#### Command Comparison & Prioritization

| Command | Priority | Lines of Code | Effort | Use Case |
|---------|----------|---------------|--------|----------|
| `build` (hub mode) | ⭐ Critical | ~200 | 1 day | Core functionality |
| `hub status` | ⭐ Critical | ~100 | 2 hours | Operational visibility |
| `hub sync` | ⭐ Critical | ~50 | 1 hour | Operational control |
| `hub validate` | 🟡 Important | ~150 | 3-4 hours | Pre-deploy checks |
| `hub add` | 🟢 Nice to have | ~80 | 2 hours | Convenience |
| `hub info` | 🟢 Nice to have | ~60 | 1 hour | Debugging |
| `hub cache clear` | 🟢 Optional | ~30 | 30 min | Edge cases |

**Total for critical commands**: ~350 lines, **1 day of work**

#### CLI Evolution by Phase

**Phase 1 (MVP)**:
- Just make `bengal build` work in hub mode
- No dedicated CLI subcommands
- Proves concept with minimal surface area

**Phase 2 (Production)**:
- Add `bengal hub status` and `bengal hub sync`
- Essential for operations at scale
- Ship these with hub mode feature

**Phase 3 (Polish)**:
- Add `bengal hub validate` for pre-deploy checks
- Add convenience commands (`add`, `info`) based on user feedback
- Community-driven prioritization

#### Example: On-Call Debugging Workflow

**Without CLI** (painful):
```bash
# "Docs hub showing stale data for Product X"
$ cat .cache/satellites/product-x.json | jq '.site.build_time'
"2025-10-22T10:15:00Z"  # 2 days old!

# How do I force refresh?
$ rm .cache/satellites/product-x.json
$ bengal build  # Rebuilds entire hub, slow
```

**With CLI** (clear):
```bash
$ bengal hub status
⚠ product-x: cache stale (48 hours)

$ bengal hub sync --satellite product-x
✓ Refreshed product-x

$ bengal build  # Fast, just regenerate HTML
```

**The CLI turns tribal knowledge into discoverability.**

---

## Implementation Phases

### Phase 1: MVP Prototype (1 day)

**Goal**: Prove core concept works

**Tasks**:
1. Create `bengal/discovery/hub_discovery.py`
   - `fetch_satellite_metadata(url)` - fetch `index.json`
   - `SatelliteCache` - basic file-based cache
2. Add `[hub]` config parsing to `bengal/config/loader.py`
3. Create minimal hub theme
   - Product directory page
   - Basic styling
4. Test with 2-3 fake satellite sites

**Success criteria**: Can fetch metadata from 3 satellites and generate a directory page.

### Phase 2: Production Ready (1 week)

**Goal**: Ship usable hub mode

**Tasks**:
1. Enhanced `index.json` schema
   - Add `product`, `version`, `namespace` to site metadata
   - Generate `cross_link_registry` (optional)
2. Robust caching with fallback
   - TTL-based cache invalidation
   - Graceful degradation on satellite failure
3. Versioning support
   - Handle multiple versions per product
   - Mark latest version
4. Namespaced search
   - Aggregate search indexes
   - Client-side scoped search
5. Status management
   - Active/deprecated/beta badges
   - Deprecation notices with replacement links
6. Hub theme polish
   - Category organization
   - Icons and visual hierarchy
   - Responsive design

**Success criteria**: Can build hub with 50+ satellites, search works, handles failures gracefully.

### Phase 3: Advanced Features (1-2 weeks)

**Goal**: Differentiated capabilities

**Tasks**:
1. Cross-linking system
   - Parse `namespace:symbol` syntax
   - Resolve at build time
   - Warning on broken cross-links
2. Multi-version search
   - Search across all versions (not just latest)
   - Version selector in search UI
3. Analytics stubs
   - Track most-viewed products
   - Freshness indicators
4. Hub CLI commands
   - `bengal hub validate` - check all satellites reachable
   - `bengal hub sync` - force refresh all caches
   - `bengal hub status` - show health of all satellites

**Success criteria**: Can cross-link between products, search multiple versions, monitor hub health.

---

## Architecture Impact

### New Modules

```
bengal/
  discovery/
    hub_discovery.py        # NEW: Satellite metadata fetching

  cache/
    satellite_cache.py      # NEW: Satellite metadata cache

  rendering/
    filters/
      hub_filters.py        # NEW: Cross-link resolution filter

  orchestration/
    hub_orchestrator.py     # NEW: Hub build orchestration

  cli/
    commands/
      hub.py                # NEW: Hub CLI commands
```

### Modified Modules

```
bengal/
  config/
    loader.py               # Add [hub] config parsing

  postprocess/
    output_formats.py       # Enhance index.json schema

  orchestration/
    build_orchestrator.py   # Route to hub_orchestrator if mode=hub
```

### Theme System

```
themes/
  hub/                      # NEW: Default hub theme
    templates/
      index.html            # Product directory
      search.html           # Hub search page
      product.html          # Individual product details
    assets/
      hub.css               # Hub-specific styles
      hub.js                # Client-side search/filtering
```

---

## Alternatives Considered

### Alternative 1: Hugo Modules Approach

**Description**: Import content from 300 repos at build time

```toml
[[content_sources.remote]]
repo = "https://github.com/corp/product-a-docs"
mount_at = "/products/product-a/"
```

**Pros**:
- Truly unified site (single search index, navigation)
- Content lives in hub site

**Cons**:
- Build time: 300 repos × clone time = hours
- Tight coupling (hub rebuild for any product change)
- Versioning nightmare (which commit/tag to use?)
- Teams lose autonomy

**Decision**: Rejected. Build time and coupling are dealbreakers.

### Alternative 2: Headless Bengal Service

**Description**: Each product runs headless Bengal as API service

```bash
product-a$ bengal serve --headless --port=5000
# Exposes: /api/pages, /api/search, /api/navigation
```

Hub orchestrates at runtime.

**Pros**:
- Real-time updates
- Dynamic content aggregation

**Cons**:
- Infrastructure cost (300 running services)
- Complexity (service discovery, health checks, load balancing)
- Unnecessary (hourly builds are acceptable)

**Decision**: Rejected. Overkill for stated requirements.

### Alternative 3: Third-Party Search (Algolia/Meilisearch)

**Description**: Use external search service for unified search

**Pros**:
- Scales better than client-side search
- Professional search UX

**Cons**:
- Defeats "static site" promise
- Vendor lock-in / additional infrastructure
- Cost at 300 products scale

**Decision**: Defer. Start with client-side search, can add later if needed.

---

## Risks & Mitigations

### Risk 1: Search Index Size

**Problem**: 300 products × 1000 pages × 1KB/entry = ~300MB search index

**Mitigation**:
- Phase 1: Only index latest versions (manageable)
- Phase 2: Progressive loading (load index per category/product on-demand)
- Phase 3: Switch to server-side search if needed (Meilisearch, Algolia)

### Risk 2: Build Time

**Problem**: Fetching 300 `index.json` files might be slow

**Mitigation**:
- Parallel fetching (10-20 concurrent requests)
- Aggressive caching (only re-fetch if TTL expired)
- Partial builds (only refresh changed satellites)
- Expected time: ~30 seconds for 300 satellites (100ms each, 20 parallel)

### Risk 3: Broken Satellites

**Problem**: What if 50 of 300 satellites are down?

**Mitigation**:
- Use cached data (with staleness indicator)
- Fail gracefully (mark as unavailable, don't block build)
- Alert/monitor satellite health
- Hub build continues even if some satellites fail

### Risk 4: Schema Versioning

**Problem**: What if old satellites have incompatible `index.json` schema?

**Mitigation**:
- Backwards compatibility (new fields optional)
- Schema version field in `index.json`
- Hub gracefully handles old schemas (uses defaults)
- Migration guide for updating satellites

### Risk 5: Cross-Link Breakage

**Problem**: Product A links to Product B's API, Product B renames it

**Mitigation**:
- Build-time validation (warn on broken cross-links)
- `bengal hub validate` command to check all cross-links
- Deprecation strategy (keep old symbols with redirects)
- Not a blocker (better than no cross-linking)

---

## Success Metrics

**Technical**:
- Hub builds in < 2 minutes with 300 satellites
- < 1% satellite fetch failures (cache fallback works)
- Client-side search latency < 200ms on 300-product index
- Cross-link resolution 99%+ success rate

**User Experience**:
- Developers can discover all products in one place
- Search finds relevant results across products
- Navigating between products is seamless
- Deprecated products clearly marked with replacements

**Adoption**:
- 3+ organizations pilot hub mode
- 100+ satellite sites connected to hubs
- Community feedback validates approach

---

## Open Questions

1. **Auto-discovery**: Should hub auto-discover satellites, or is manual registry OK?
   - Manual = more control, explicit
   - Auto = magic, but how would it work?
   - **Lean toward manual for MVP**

2. **Authentication**: What if some satellites are behind auth?
   - Could support auth tokens in config
   - Or require satellites to allow hub IP
   - **Defer to when it's needed**

3. **Build triggers**: How does hub know when to rebuild?
   - Cron job (hourly) - simple, works
   - Webhook from satellites - more complex
   - **Start with cron, add webhooks later**

4. **Offline mode**: Can hub build without network?
   - Use cached data only
   - Could be useful for development
   - **Nice to have, not critical**

5. **Hub-to-hub federation**: Can hubs aggregate other hubs?
   - Interesting for mega-enterprises
   - Probably overkill
   - **Defer indefinitely**

---

## Next Steps

1. **Validate demand**: Get 2-3 potential users to review this RFC
2. **Prototype** (1 day): Build minimal proof-of-concept
3. **Dogfood**: Use hub mode for Bengal's own docs (core, autodoc, themes)
4. **Iterate**: Based on prototype learnings, refine design
5. **Implement**: Build Phase 2 (production-ready)
6. **Ship**: Release as experimental feature, gather feedback
7. **Polish**: Implement Phase 3 based on real-world usage

---

## References

- **Intersphinx** (Sphinx): https://www.sphinx-doc.org/en/master/usage/extensions/intersphinx.html
- **Hugo Modules**: https://gohugo.io/hugo-modules/
- **Obsidian Graph View**: Inspiration for knowledge graph visualization
- **Bengal's `index.json`**: https://lbliii.github.io/bengal/index.json (current implementation)

---

## Appendix: Example Hub Site Structure

```
hub-site/
  bengal.toml              # Hub configuration
  content/
    index.md               # Hub landing page
  themes/
    hub/                   # Hub-specific theme
  .cache/
    satellites/            # Cached satellite metadata
      product-a.json
      product-b.json
      ...
  public/                  # Built hub site
    index.html             # Product directory
    search.html            # Unified search
    products/              # Per-product pages
      product-a.html
      product-b.html
```

---

**Status**: Ready for validation and prototyping  
**Next Action**: Get feedback from potential users, then prototype
