# RFC: CLI Analysis Improvements & Semantic Link Model

```yaml
Title: CLI Analysis Improvements & Semantic Link Model
Author: AI + Human reviewer
Date: 2025-12-10
Status: Draft
Confidence: 88%
```

## Problem Statement

### Current State

Bengal's graph analysis commands provide valuable site structure insights but suffer from discoverability, usability, and accuracy issues:

**CLI Discoverability Issues:**

1. **Hidden under `utils`**: Commands live at `bengal utils graph <cmd>` but users expect `bengal graph <cmd>` or `bengal analyze`. Evidence: `bengal/cli/__init__.py:118` shows `utils_cli` as a generic container, while `bengal/cli/commands/utils.py:23` adds `graph_cli` as a subcommand.

2. **No unified report**: Getting complete analysis requires 4 separate commands:
   - `bengal utils graph analyze` (stats + orphans)
   - `bengal utils graph suggest` (link recommendations)
   - `bengal utils graph bridges` (navigation bottlenecks)
   - `bengal utils graph communities` (topic clusters)

3. **Orphan detection not in health checks**: `bengal check` skips connectivity analysis by default. Evidence: `bengal/cli/commands/validate.py` doesn't include orphan detection; users must run separate graph commands.

4. **No brief/CI-friendly output**: Commands produce verbose output (~50+ lines) unsuitable for CI pipelines or quick checks.

**Link Detection Gaps:**

5. **Missing structural link sources**: The knowledge graph only tracks explicit markdown links (`[text](url)`), missing important structural relationships. Evidence: `bengal/analysis/knowledge_graph.py:242-267` shows `_analyze_cross_references()` only processes `page.links` from `extract_links()`.

   Currently tracked:
   - ✅ Explicit markdown links
   - ✅ HTML links
   - ✅ Taxonomy membership
   - ✅ Related posts
   - ✅ Menu items
   
   **Missing (causes false orphans)**:
   - ❌ Section hierarchy (parent `_index.md` → children)
   - ❌ Sequential navigation (next/prev in section)
   - ❌ Template-generated page lists

6. **False orphan reports**: Pages like `/releases/0.1.1.md` are reported as orphans even though they're linked from `/releases/_index.md` via template-generated lists. The `_index.md` contains no explicit links—it relies on templates to auto-render child pages.

### Pain Points

| Issue | User Impact | Frequency |
|-------|-------------|-----------|
| `bengal graph` fails | Confusion, trial-and-error | Every new user |
| 4 commands for full picture | Tedious workflow, incomplete analysis | Every audit |
| Orphans not in `check` | Missed SEO issues in standard validation | Every build |
| Verbose output | Can't use in CI, hard to scan | Every run |
| **False orphan reports** | Noise, wasted investigation time | Every analysis |
| **No link type distinction** | Can't prioritize orphan fixes | Every audit |

### User Impact

- **New Users**: Can't discover analysis features without reading docs
- **CI/CD Pipelines**: No way to fail builds on orphan thresholds
- **Content Authors**: Don't see orphan warnings during normal workflow
- **SEO Audits**: Require running multiple commands manually
- **False Positives**: Pages in sections reported as orphans when they're structurally linked

---

## Goals & Non-Goals

### Goals

**CLI Improvements:**
1. **Promote `graph` to top-level**: `bengal graph analyze` instead of `bengal utils graph analyze`
2. **Add unified `analyze` command**: Single command for complete site analysis
3. **Integrate orphans into `check`**: Surface orphan warnings in standard validation
4. **Add CI-friendly output modes**: `--brief`, `--ci`, `--threshold` flags
5. **Add `orphans` subcommand**: Quick access to orphan list

**Link Detection Improvements:**
6. **Add semantic link types**: Track structural relationships (parent-child, next/prev) with appropriate weights
7. **Weighted connectivity scoring**: Continuous score (0-∞) instead of binary orphan/not-orphan
8. **Connectivity levels**: Configurable thresholds for well-connected, adequate, light, and isolated pages

### Non-Goals

- Changing core analysis algorithms (PageRank, community detection, etc.)
- Redesigning graph visualization output format
- Breaking existing `bengal utils graph` paths (maintain for backwards compatibility)
- Real-time link extraction during template rendering (too complex, minimal benefit)

---

## Architecture Impact

### Affected Subsystems

- **CLI** (`bengal/cli/`): Primary changes
  - `__init__.py`: Add `graph_cli` as top-level command
  - `commands/validate.py`: Add connectivity check option
  - `commands/graph/__main__.py`: Add `orphans` and unified `report` commands
- **Health** (`bengal/health/`): Minor changes
  - Add connectivity validator that checks for orphans
- **Analysis** (`bengal/analysis/`): **Semantic link model** (NEW)
  - `knowledge_graph.py`: Add `_analyze_section_hierarchy()` and `_analyze_navigation_links()`
  - `knowledge_graph.py`: Add `LinkType` enum and weighted scoring
  - `graph_analysis.py`: Update `get_orphans()` to return categorized results

### Integration Points

```
bengal check --connectivity
    └── calls → ConnectivityValidator
                    └── uses → GraphAnalyzer.get_orphans()
                                    └── reads → KnowledgeGraph (with semantic links)

bengal analyze (new unified command)
    └── calls → GraphAnalyzer.get_orphans()
              → KnowledgeGraph.suggest_links()
              → community_detection.detect()
              → path_analysis.get_bridges()
    └── formats → unified report (with orphan categories)

KnowledgeGraph.build() (enhanced)
    └── _analyze_cross_references()     # Explicit links (weight: 1.0)
    └── _analyze_taxonomies()           # Shared tags (weight: 1.0)
    └── _analyze_related_posts()        # Algorithm suggestions (weight: 0.75)
    └── _analyze_menus()                # Navigation items (weight: 10.0)
    └── _analyze_section_hierarchy()    # Topical context (weight: 0.5) NEW
    └── _analyze_navigation_links()     # Sequential context (weight: 0.25) NEW
```

---

## Design Options

### Option A: Promote + Alias (Recommended)

**Description**: Add `graph_cli` as a top-level command while keeping `utils graph` as an alias for backwards compatibility.

```python
# bengal/cli/__init__.py
from bengal.cli.commands.graph import graph_cli

# Top-level (new)
main.add_command(graph_cli, name="graph")

# Also add unified analyze command
main.add_command(analyze_cmd, name="analyze")

# Keep backwards compat
# utils_cli already has graph_cli attached
```

**Pros**:
- Zero breaking changes
- Intuitive `bengal graph analyze` path
- Matches user mental model
- Simple implementation (~20 lines)

**Cons**:
- Slight CLI namespace expansion
- `--help` shows more top-level commands

**Complexity**: Simple

---

### Option B: Move graph out of utils entirely

**Description**: Remove `graph_cli` from `utils_cli`, only expose at top-level.

**Pros**:
- Cleaner namespace
- No duplicate paths

**Cons**:
- Breaking change for existing scripts/docs
- Requires deprecation period

**Complexity**: Moderate

---

### Option C: Rename utils to analysis

**Description**: Rename `utils` group to `analysis` and keep graph under it.

**Pros**:
- More descriptive grouping
- Could house future analysis commands

**Cons**:
- Breaking change (`bengal utils` → `bengal analysis`)
- Doesn't address discoverability (still nested)

**Complexity**: Moderate

---

### Recommended: Option A

Option A provides immediate usability improvement with zero breaking changes. Users can use `bengal graph analyze` while existing scripts continue working with `bengal utils graph analyze`.

---

## Detailed Design

### 1. Promote `graph` to Top-Level

```python
# bengal/cli/__init__.py

from bengal.cli.commands.graph import graph_cli

# After existing imports, add:
main.add_command(graph_cli, name="graph")

# Short alias (optional)
main.add_command(graph_cli, name="g")
```

### 2. Add Unified `analyze` Command

New command at `bengal/cli/commands/graph/report.py`:

```python
@click.command("report")
@click.option("--brief", is_flag=True, help="Compact output for CI")
@click.option("--ci", is_flag=True, help="Exit 1 if thresholds exceeded")
@click.option("--threshold-orphans", type=int, default=None, 
              help="Max orphans before CI failure")
@click.option("--threshold-link-density", type=float, default=None,
              help="Min links/page before CI failure")
@click.option("--format", type=click.Choice(["console", "json", "markdown"]),
              default="console")
def report(brief, ci, threshold_orphans, threshold_link_density, format):
    """
    📊 Generate comprehensive site analysis report.
    
    Combines: analyze, suggest, bridges, communities
    
    Examples:
        bengal graph report
        bengal graph report --brief
        bengal graph report --ci --threshold-orphans 10
        bengal graph report --format json > report.json
    """
```

**Brief output format** (for `--brief`):

```
📊 Site Analysis: 124 pages
   Orphans: 43 (35%) ⚠️
   Link density: 1.9/page (low)
   Top bridges: Formatting Directives, Icon Reference
   Communities: 9 major clusters
   
⚠️ 43 orphans exceed recommended threshold (10)
```

### 3. Add `orphans` Subcommand

New command at `bengal/cli/commands/graph/orphans.py`:

```python
@click.command("orphans")
@click.option("--format", type=click.Choice(["table", "json", "paths"]),
              default="table")
@click.option("--limit", type=int, default=None, help="Limit results")
def orphans(format, limit):
    """
    🔍 List pages with no incoming links.
    
    Examples:
        bengal graph orphans
        bengal graph orphans --format paths  # Just file paths
        bengal graph orphans --format json > orphans.json
    """
```

### 4. Integrate Connectivity into `check`

Add new validator at `bengal/health/validators/connectivity.py`:

```python
class ConnectivityValidator(Validator):
    """Validates site connectivity and link structure."""
    
    name = "connectivity"
    
    def validate(self, site: Site) -> list[ValidationResult]:
        graph = KnowledgeGraph(site)
        graph.build()
        analyzer = GraphAnalyzer(graph)
        
        results = []
        
        # Check for orphans
        orphans = analyzer.get_orphans()
        if orphans:
            results.append(ValidationResult(
                level=ValidationLevel.WARNING,
                message=f"{len(orphans)} orphan pages (no incoming links)",
                details=[str(p.source_path) for p in orphans[:10]],
                suggestion="Add links to these pages from navigation or related content"
            ))
        
        # Check link density
        avg_links = graph.total_links / len(site.pages)
        if avg_links < 2.0:
            results.append(ValidationResult(
                level=ValidationLevel.WARNING,
                message=f"Low link density ({avg_links:.1f} links/page)",
                suggestion="Add more internal links for better SEO and navigation"
            ))
        
        return results
```

Enable in `validate.py`:

```python
@click.option("--connectivity/--no-connectivity", default=False,
              help="Include connectivity analysis (orphans, link density)")
```

### 5. API Changes Summary

| Command | Before | After |
|---------|--------|-------|
| Graph analyze | `bengal utils graph analyze` | `bengal graph analyze` ✨ |
| Link suggestions | `bengal utils graph suggest` | `bengal graph suggest` |
| Orphan list | (none) | `bengal graph orphans` ✨ |
| Full report | (4 commands) | `bengal graph report` ✨ |
| Check + orphans | (not available) | `bengal check --connectivity` ✨ |

### 6. Configuration

Add to `bengal.toml` schema:

```toml
[health.connectivity]
enabled = true
orphan_threshold = 10        # Warn if > N orphans
link_density_threshold = 2.0 # Warn if < N links/page
```

---

## Semantic Link Model (New)

### Link Relationship Types

Links carry **semantic meaning** beyond simple connectivity:

| Link Type | Semantic Meaning | Weight | Rationale |
|-----------|------------------|--------|-----------|
| `MENU` | "This is important" | 10.0 | Deliberate navigation prominence |
| `EXPLICIT` | "I recommend this" | 1.0 | Human editorial endorsement |
| `TAXONOMY` | "These share a concept" | 1.0 | Topic clustering |
| `RELATED` | "Algorithm suggests this" | 0.75 | Computed, not curated |
| `TOPICAL` | "This belongs to this topic" | 0.5 | **Parent-child context** (NEW) |
| `SEQUENTIAL` | "Read this in order" | 0.25 | **Next/prev navigation** (NEW) |

### When Would Pages Still Be Isolated?

Even with structural links, some pages may have zero or near-zero connectivity:

| Scenario | Why Isolated | Example |
|----------|--------------|---------|
| **Root-level pages** | No parent `_index.md` | `/random-page.md` in content root |
| **Sections without index** | Directory has no `_index.md` | `/misc/note.md` where `/misc/` has no index |
| **Draft/hidden pages** | Excluded from section rendering | `draft: true` pages |
| **Standalone legal pages** | Intentionally isolated | `/privacy.md`, `/terms.md` (unless in menu) |
| **Misconfigured pages** | Not in `section.pages` due to bug | Edge cases |
| **Orphaned test content** | Forgotten during development | `/test/temp.md` |

These are the **true isolated pages** that need attention—not pages that simply lack explicit cross-references.

### Why Different Weights?

**Topical Context (Parent → Child)**: Weight 0.5

The `releases/_index.md` → `0.1.4.md` relationship means:
- 0.1.4.md **belongs to** the releases topic
- The releases section has **topical authority** over release content
- SEO signal: Topical clustering for search relevance

This is **structural containment with semantic meaning**, not just navigation.

**Sequential Context (Next/Prev)**: Weight 0.25

The `0.1.3.md` ↔ `0.1.4.md` relationship means:
- Content forms a **reading sequence** (upgrade path)
- User journey: "What changed since last version?"
- Lowest editorial intent—pure navigation structure

### Data Model

```python
from enum import Enum
from dataclasses import dataclass

class LinkType(Enum):
    """Semantic relationship types between pages."""
    # Human-authored (high editorial intent)
    EXPLICIT = "explicit"           # [text](url) in content
    MENU = "menu"                   # Navigation menu item
    
    # Algorithmic (medium intent)
    TAXONOMY = "taxonomy"           # Shared tags/categories
    RELATED = "related"             # Computed related posts
    
    # Structural (semantic context, low editorial intent)
    TOPICAL = "topical"             # Parent section → child
    SEQUENTIAL = "sequential"       # Next/prev in section


@dataclass
class LinkMetrics:
    """Detailed link breakdown for a page."""
    explicit: int = 0       # Weight: 1.0
    menu: int = 0           # Weight: 10.0
    taxonomy: int = 0       # Weight: 1.0
    related: int = 0        # Weight: 0.75
    topical: int = 0        # Weight: 0.5 (NEW)
    sequential: int = 0     # Weight: 0.25 (NEW)
    
    def connectivity_score(self) -> float:
        """
        Weighted connectivity score (continuous, 0 to ∞).
        
        Higher = better connected, more discoverable.
        """
        return (
            self.explicit * 1.0 +
            self.menu * 10.0 +
            self.taxonomy * 1.0 +
            self.related * 0.75 +
            self.topical * 0.5 +
            self.sequential * 0.25
        )
    
    def has_human_links(self) -> bool:
        """True if page has any human-authored links."""
        return self.explicit > 0 or self.menu > 0
    
    def has_structural_links(self) -> bool:
        """True if page has structural links (section/nav)."""
        return self.topical > 0 or self.sequential > 0


class ConnectivityLevel(Enum):
    """
    Connectivity classification based on weighted score thresholds.
    
    NOT binary - uses configurable thresholds for nuanced analysis.
    """
    WELL_CONNECTED = "well_connected"     # Score >= 2.0 (no action needed)
    ADEQUATELY_LINKED = "adequately"      # Score 1.0-2.0 (could improve)
    LIGHTLY_LINKED = "lightly"            # Score 0.25-1.0 (should improve)
    ISOLATED = "isolated"                 # Score < 0.25 (needs attention)
    
    @classmethod
    def from_score(cls, score: float, thresholds: dict | None = None) -> "ConnectivityLevel":
        """Classify based on score and configurable thresholds."""
        t = thresholds or DEFAULT_THRESHOLDS
        if score >= t["well_connected"]:
            return cls.WELL_CONNECTED
        elif score >= t["adequately_linked"]:
            return cls.ADEQUATELY_LINKED
        elif score >= t["lightly_linked"]:
            return cls.LIGHTLY_LINKED
        else:
            return cls.ISOLATED


DEFAULT_THRESHOLDS = {
    "well_connected": 2.0,      # Multiple link types
    "adequately_linked": 1.0,   # Has some connections
    "lightly_linked": 0.25,     # Only structural/single taxonomy
    # Below lightly_linked = isolated
}
```

### Implementation: Section Hierarchy Analysis

Add to `bengal/analysis/knowledge_graph.py`:

```python
def _analyze_section_hierarchy(self) -> None:
    """
    Analyze implicit section links (parent _index.md → children).
    
    Section index pages implicitly link to all child pages in their
    directory. This represents topical containment—the parent page
    defines the topic, children belong to that topic.
    
    Weight: 0.5 (structural but semantically meaningful)
    """
    analysis_pages_set = set(self.get_analysis_pages())
    
    for page in self.get_analysis_pages():
        # Only process index pages
        if not getattr(page, 'is_index', False):
            continue
        
        # Get the section this index belongs to
        section = getattr(page, 'section', None)
        if not section:
            continue
        
        # Link to all child pages in this section
        for child in getattr(section, 'pages', []):
            if child != page and child in analysis_pages_set:
                # Topical link: parent defines topic, child belongs to it
                self.incoming_refs[child] += 0.5  # Reduced weight
                self.outgoing_refs[page].add(child)
                
                # Track link type for detailed reporting
                if hasattr(self, 'link_types'):
                    self.link_types[(page, child)] = LinkType.TOPICAL


def _analyze_navigation_links(self) -> None:
    """
    Analyze next/prev sequential relationships.
    
    Pages in a section often have prev/next relationships representing
    a reading order or logical sequence (e.g., tutorial steps, changelogs).
    
    Weight: 0.25 (pure navigation, lowest editorial intent)
    """
    analysis_pages_set = set(self.get_analysis_pages())
    
    for page in self.get_analysis_pages():
        # Check next_in_section
        next_page = getattr(page, 'next_in_section', None)
        if next_page and next_page in analysis_pages_set:
            self.incoming_refs[next_page] += 0.25
            self.outgoing_refs[page].add(next_page)
            if hasattr(self, 'link_types'):
                self.link_types[(page, next_page)] = LinkType.SEQUENTIAL
        
        # Check prev_in_section (bidirectional)
        prev_page = getattr(page, 'prev_in_section', None)
        if prev_page and prev_page in analysis_pages_set:
            self.incoming_refs[prev_page] += 0.25
            self.outgoing_refs[page].add(prev_page)
            if hasattr(self, 'link_types'):
                self.link_types[(page, prev_page)] = LinkType.SEQUENTIAL
```

### Threshold-Based Connectivity Reporting

**Key Insight**: "Orphan" is misleading—it implies binary (linked/not linked). With structural links, almost every page in a section has incoming refs. Better to use **continuous scoring with configurable thresholds**.

#### Why Thresholds Instead of Binary?

| Scenario | With Binary | With Thresholds |
|----------|-------------|-----------------|
| Page in section, no explicit links | "Not orphan" ❌ | "Lightly linked" 🟠 |
| Page with only taxonomy tags | "Not orphan" ❌ | "Adequately linked" 🟡 |
| Page with menu + explicit links | "Not orphan" ✅ | "Well connected" 🟢 |
| Page with no connections at all | "Orphan" | "Isolated" 🔴 |

Binary masks nuance; thresholds reveal opportunities for improvement.

#### Example Scoring

| Page | Explicit | Menu | Taxonomy | Topical | Sequential | **Score** | **Level** |
|------|----------|------|----------|---------|------------|-----------|-----------|
| `/docs/getting-started/` | 5 | 1 | 2 | 1 | 2 | **17.5** | 🟢 Well-Connected |
| `/docs/api/endpoint.md` | 1 | 0 | 1 | 1 | 2 | **3.0** | 🟢 Well-Connected |
| `/releases/0.1.4.md` | 0 | 0 | 1 | 1 | 2 | **2.0** | 🟢 Well-Connected |
| `/releases/0.1.1.md` | 0 | 0 | 1 | 1 | 0 | **1.5** | 🟡 Adequately Linked |
| `/blog/old-post.md` | 0 | 0 | 1 | 0 | 0 | **1.0** | 🟡 Adequately Linked |
| `/releases/0.1.0.md` | 0 | 0 | 0 | 1 | 0 | **0.5** | 🟠 Lightly Linked |
| `/misc/scratch.md` | 0 | 0 | 0 | 0 | 0 | **0.0** | 🔴 Isolated |
| `/privacy.md` | 0 | 1 | 0 | 0 | 0 | **10.0** | 🟢 Well-Connected (menu!) |

#### Updated CLI Output

```
📊 Connectivity Analysis: 124 pages

Distribution:
  🟢 Well-Connected (≥2.0):    81 pages (65%)
  🟡 Adequately Linked (1-2):  28 pages (23%)
  🟠 Lightly Linked (0.25-1):  10 pages (8%)
  🔴 Isolated (<0.25):          5 pages (4%)

🔴 Isolated pages (5) - need immediate attention:
   • /drafts/unpublished-idea.md (score: 0.0)
   • /misc/scratch.md (score: 0.0)
   • /content/orphan.md (score: 0.0)
   • /random/forgotten.md (score: 0.0)
   • /test/temp.md (score: 0.0)
   
🟠 Lightly linked pages (10) - could use more connections:
   • /releases/0.1.0.md (score: 0.5) - only section link
   • /blog/archive/2020.md (score: 0.5) - only section link
   • /docs/advanced/edge-case.md (score: 0.75) - section + taxonomy
   ... and 7 more

💡 Recommendations:
   • 5 isolated pages have no connections - add to navigation or content
   • 10 lightly linked pages rely only on structure - add explicit cross-references
   • Consider linking releases sequentially (upgrade path documentation)
```

### Configuration

```toml
[analysis.link_weights]
# Weights for different link types (configurable per-site)
explicit = 1.0       # Human-authored markdown links
menu = 10.0          # Navigation menu items
taxonomy = 1.0       # Shared tags/categories
related = 0.75       # Algorithm suggestions
topical = 0.5        # Section parent → children (topical context)
sequential = 0.25    # Next/prev in section (sequential context)

[analysis.connectivity_thresholds]
# Thresholds for connectivity levels (score boundaries)
well_connected = 2.0      # Score >= this = no action needed
adequately_linked = 1.0   # Score >= this = could improve
lightly_linked = 0.25     # Score >= this = should improve
# Below lightly_linked = isolated (needs attention)

[analysis.ci_thresholds]
# CI failure conditions
max_isolated = 5          # Fail if more than N isolated pages
max_lightly_linked = 20   # Warn if more than N lightly linked pages
min_avg_connectivity = 1.5  # Warn if site average below this
```

---

## Tradeoffs & Risks

### Tradeoffs

| Tradeoff | Gain | Cost |
|----------|------|------|
| Top-level `graph` | Better discoverability | Larger top-level namespace |
| Unified report | Single command workflow | Slightly slower (runs all analyses) |
| Connectivity in check | Integrated workflow | Adds ~2s to `bengal check` when enabled |
| **Structural link weights** | Fewer false positives | More complex link model |
| **Configurable weights** | Per-site tuning | More configuration surface |
| **Threshold-based levels** | Nuanced prioritization | Learning curve for new terminology |
| **Continuous scoring** | Precise optimization | Less intuitive than binary |

### Risks

**Risk 1: Breaking existing documentation/scripts**
- **Likelihood**: Low (no paths removed)
- **Impact**: Low
- **Mitigation**: Keep `bengal utils graph` working

**Risk 2: Performance of unified report**
- **Likelihood**: Medium
- **Impact**: Low (graph analysis is fast)
- **Mitigation**: Add `--skip-communities` etc. flags for partial reports

**Risk 3: Namespace pollution**
- **Likelihood**: Low
- **Impact**: Low
- **Mitigation**: Only add essential commands (`graph`, optionally `g` alias)

**Risk 4: Weight tuning complexity**
- **Likelihood**: Medium
- **Impact**: Low (defaults work for most sites)
- **Mitigation**: Sensible defaults, make configuration optional

**Risk 5: Metrics change after upgrade**
- **Likelihood**: High (that's the point)
- **Impact**: Low (more accurate analysis is good)
- **Mitigation**: Document in changelog, add `--legacy` flag for old binary behavior

**Risk 6: Terminology confusion ("orphan" vs "isolated")**
- **Likelihood**: Medium
- **Impact**: Low (documentation helps)
- **Mitigation**: Keep `orphans` command as alias, add clear explanations in output

---

## Performance & Compatibility

### Performance Impact

- **Build time**: No change (analysis is separate from build)
- **`bengal check`**: +2-3s when `--connectivity` enabled (graph construction)
- **Memory**: Negligible (graph already exists in analysis module)

### Compatibility

- **Breaking changes**: None (all existing paths preserved)
- **Migration path**: None required (additive changes only)
- **Deprecation timeline**: N/A

---

## Migration & Rollout

### Implementation Phases

**Phase 1: CLI Commands (1-2 days)**
1. Add `graph_cli` to top-level in `__init__.py`
2. Add `orphans` subcommand
3. Add `report` unified command with `--brief` flag

**Phase 2: Semantic Link Model (2-3 days)**
4. Add `LinkType` enum and `LinkMetrics` dataclass
5. Implement `_analyze_section_hierarchy()` in `knowledge_graph.py`
6. Implement `_analyze_navigation_links()` in `knowledge_graph.py`
7. Update `build()` to call new analysis methods
8. Add link type tracking for detailed reporting

**Phase 3: Connectivity Levels (1-2 days)**
9. Add `ConnectivityLevel` enum with threshold-based classification
10. Add `get_connectivity_report()` returning pages grouped by level
11. Update CLI output to show connectivity distribution
12. Add `--level` filter to `orphans`/`isolated` command

**Phase 4: CI Integration (1 day)**
13. Add `--ci` and `--threshold-*` flags to `report`
14. Add exit code logic for threshold violations
15. Support category-specific thresholds

**Phase 5: Health Integration (1-2 days)**
16. Create `ConnectivityValidator`
17. Add `--connectivity` flag to `bengal check`
18. Add configuration schema for link weights and thresholds

**Phase 6: Documentation (1 day)**
19. Update CLI reference docs
20. Add "Site Analysis" how-to guide
21. Document semantic link model and weights
22. Update `bengal --help` quick start

### Rollout Strategy

- **Feature flag**: No (additive, non-breaking)
- **Beta period**: Ship in next release
- **Documentation updates**:
  - CLI reference: Add `bengal graph` section
  - How-to: "Analyze Site Structure"
  - Tutorial: "Optimize Internal Linking"

---

## Open Questions

- [ ] **Q1**: Should `bengal analyze` be a top-level alias for `bengal graph report`? (vs. keeping it under `graph`)
- [ ] **Q2**: Default CI thresholds - what's a reasonable `max_isolated` default? (proposed: 5)
- [ ] **Q3**: Should `--connectivity` be enabled by default in `bengal check` or opt-in?
- [ ] **Q4**: Are the proposed connectivity thresholds appropriate? (well_connected=2.0, adequately=1.0, lightly=0.25)
- [ ] **Q5**: Are the proposed link weights appropriate? (topical=0.5, sequential=0.25)
- [ ] **Q6**: Should we deprecate the term "orphan" entirely in favor of "isolated"?
- [ ] **Q7**: Should the `orphans` command be renamed to `isolated` or `connectivity`?

---

## Evidence & References

### Code Evidence

**CLI Structure:**
- `bengal/cli/__init__.py:118`: `utils_cli` registration
- `bengal/cli/commands/utils.py:23`: `graph_cli` under utils
- `bengal/cli/commands/graph/__main__.py:224-228`: Current graph commands
- `bengal/cli/commands/validate.py`: No connectivity checks

**Link Detection:**
- `bengal/analysis/knowledge_graph.py:242-267`: `_analyze_cross_references()` only processes explicit links
- `bengal/core/page/operations.py:73-108`: `extract_links()` uses regex for markdown/HTML links only
- `bengal/analysis/knowledge_graph.py:351-372`: `_analyze_menus()` gives +10 weight to menu items
- `bengal/analysis/knowledge_graph.py:300-328`: `_analyze_taxonomies()` gives +1 for shared tags

**Missing Link Sources:**
- `bengal/core/page/__init__.py:608-629`: `next_in_section` and `prev_in_section` properties exist but aren't used in graph analysis
- Section hierarchy (parent `_index.md` → children) not analyzed at all

### User Experience Evidence

- Direct testing: `bengal graph analyze` fails with "Unknown command 'graph'"
- Must run 4 separate commands to get complete analysis
- `bengal check --verbose` shows "Skipping Connectivity (disabled by profile)"
- **False orphan case**: `releases/0.1.1.md` reported as orphan despite being linked from `releases/_index.md` via template-generated list (no explicit markdown link)

---

## Quality Checklist

- [x] Problem statement clear with evidence
- [x] Goals and non-goals explicit
- [x] 3 design options analyzed (CLI promotion)
- [x] Recommended option justified (Option A)
- [x] Architecture impact documented (CLI, Health, Analysis)
- [x] Risks identified with mitigations
- [x] Performance and compatibility addressed
- [x] Implementation phases defined (6 phases)
- [x] Open questions flagged (7 questions)
- [x] Semantic link model detailed with weights and rationale
- [x] Data model specified (LinkType, LinkMetrics, ConnectivityLevel)
- [x] Threshold-based connectivity model (continuous, not binary)
- [x] Configuration schema defined (weights + thresholds)
- [x] Example scoring table with real scenarios
- [x] Confidence ≥ 85% (88%)

