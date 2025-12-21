# RFC: URL Ownership Architecture

**Status**: Evaluated  
**Created**: 2024-12-20  
**Author**: TBD  
**Supersedes**: `rfc-url-collision-detection.md` (elevates from tactical collision detection to ownership + policy)  
**Confidence**: 86% 🟢 (see “Confidence scoring”)

## Executive Summary

Bengal already detects URL collisions proactively during the build, and can fail builds in strict mode. The remaining gap is **policy** (who is allowed to own a URL namespace) and **early enforcement** (claim-time) rather than after generation.

This RFC proposes a `URLRegistry` (or equivalent) to make URL ownership explicit, prevent invalid states earlier in the pipeline, and provide clear diagnostics for collisions across content, autodoc, taxonomies, special pages, and redirects.

## Problem Statement

### Current state (verified)

**Collision detection exists**, but it is:

- **post-generation**: detects collisions after all producers have created pages
- **policy-less**: detects “duplicates”, but does not encode *ownership rules* like “user content cannot silently shadow `/tags/…` or `/cli/…`”
- **not claim-time**: producers do not claim namespaces/paths as they generate pages

Evidence:

- Proactive build-phase collision detection: `bengal/orchestration/build/__init__.py:368-379`
- Collision detection implementation: `bengal/core/site/core.py:576-640`
- Health validator for collisions: `bengal/health/validators/url_collisions.py:25-98`

### Why this RFC still matters

Even with collision detection:

- Multiple producers still compute output paths independently (content, taxonomy, autodoc, special pages, redirects).
- A collision is detected only after the fact, which makes it harder to attach ownership context (“this URL belongs to taxonomy, not content”).
- Some generators include their own ad-hoc override checks (e.g., search page) rather than a unified ownership contract.

Examples of independent generators and their output roots (verified):

- **Taxonomy pages**: `/tags/<tag>/…` via `URLStrategy.compute_tag_output_path()` (`bengal/utils/url_strategy.py:203-237`)
- **Autodoc section index pages**: `/<prefix>/index.html` via `create_index_pages()` (`bengal/autodoc/orchestration/index_pages.py:19-88`)
- **Autodoc element pages**: `/<prefix>/<path>/index.html` via `create_pages()` (`bengal/autodoc/orchestration/page_builders.py:92-132`)
- **Search special page**: `/search/index.html` by default, with a limited “content/search.md exists” override (`bengal/postprocess/special_pages.py:182-273`)
- **Redirects**: alias pages that skip generation if the output path already exists (`bengal/postprocess/redirects.py:110-142`)

## Collision Scenarios (verified / qualified)

### Already possible today (or possible under specific config)

| Scenario | Condition | What collides | Current behavior |
|----------|-----------|--------------|------------------|
| Content + Tags | User creates `content/tags/<tag>.md` | `/tags/<tag>/` (taxonomy) vs content | Collision detected by `Site.validate_no_url_collisions()` |
| Content + Search | User creates `content/search.md` | `/search/` (special page) vs content | Special generator skips when `content/search.md` exists (`bengal/postprocess/special_pages.py:211-218`) |
| Content + 404 | `pretty_urls = false` and user creates `content/404.md` | `public/404.html` (content) vs special 404 | Possible overwrite: special generator always writes `public/404.html` (`bengal/postprocess/special_pages.py:152-175`) |
| Redirects + Content | Alias target already exists on disk | `/<alias>/index.html` (redirect) vs existing file | Redirect generator skips when output path exists (`bengal/postprocess/redirects.py:133-142`) |
| Autodoc root-group | CLI root command-group would output to `/cli/` | section index vs root element page | Fixed by skipping root command-group page creation (`bengal/autodoc/orchestration/page_builders.py:92-102`) |

### Future Risks

| Scenario | Trigger | Impact |
|----------|---------|--------|
| Plugins | Third-party plugin creates pages | No URL coordination |
| Custom content types | New type with own URL strategy | Conflicts with existing |
| Multi-site | Shared content across sites | Cross-site URL conflicts |
| Dynamic routes | API routes in dev server | Static pages shadow routes |
| i18n edge cases | Default language handling | `/en/about/` vs `/about/` |

## Evidence: Existing protections

### 1) Proactive URL collision detection (build phase)

- Build orchestrator runs collision detection before rendering:
  - `bengal/orchestration/build/__init__.py:373-379`
- Collision detector reports all collisions and can fail in strict mode:
  - `bengal/core/site/core.py:576-640`
- Integration tests cover detection + strict behavior:
  - `tests/integration/test_autodoc_navigation.py:235-363`

### 2) Redirects: alias conflicts + “do not overwrite real content”

- Multiple pages claiming the same alias logs a warning and “first claimant wins”:
  - `bengal/postprocess/redirects.py:66-106`
  - `tests/unit/postprocess/test_redirects.py:165-182`
- Redirect generation skips if the output file already exists:
  - `bengal/postprocess/redirects.py:133-142`
  - `tests/unit/postprocess/test_redirects.py:139-163`

### 3) Special pages: limited opt-out for user content

- Search generation skips only when `content/search.md` exists:
  - `bengal/postprocess/special_pages.py:211-218`

## Gap statement

These protections detect collisions, but **do not define ownership policy**. Today, any producer can generate into any namespace as long as it does not collide, and generators encode ad-hoc “override rules” in different places.

## Goals

1. **Make invalid states unrepresentable** - Can't create two pages at same URL
2. **Explicit ownership** - Clear rules for who "owns" each URL pattern
3. **Fail-fast** - Collisions detected at creation time, not render time
4. **Incremental Safety** - Persist claims across builds to prevent shadowing by new content
5. **Extensible** - Plugins can participate in URL coordination

## Non-Goals

- Changing how existing URLs are computed (backward compatibility)
- Supporting multiple pages at the same URL (never valid)
- Runtime URL resolution (static site generator)

## Design Options

### Option A: URL registry (claim-time authority)

Introduce a stateful `URLRegistry` on `Site` that is the single authority for URL claims.

```python
@dataclass
class URLClaim:
    owner: str       # "content", "autodoc:python", "taxonomy", etc.
    source: str      # File path or qualified name
    priority: int    # 100=User, 50=Generated, etc.
    version: str | None = None  # For versioned content support
    lang: str | None = None     # For i18n support

class URLRegistry:
    """Central authority for URL claims (policy + conflict detection)."""

    def __init__(self):
        self._claims: dict[str, URLClaim] = {}

    def claim(
        self,
        url: str,
        owner: str,
        source: str,
        priority: int = 50,
        version: str | None = None,
        lang: str | None = None,
    ) -> None:
        """
        Claim a URL for output.
        """
        normalized = self._normalize(url)

        if normalized in self._claims:
            existing = self._claims[normalized]
            if existing.priority > priority:
                raise URLCollisionError(url, existing, owner, source)

            if existing.priority == priority and existing.source != source:
                # Same priority collision (e.g., two content files with same slug)
                raise URLCollisionError(url, existing, owner, source)

            # Higher priority wins - override and log
            logger.warning("url_override", url=url, old=existing.owner, new=owner)

        self._claims[normalized] = URLClaim(owner, source, priority, version, lang)
```

### Notes on incremental builds

Today, incremental mode still discovers the full site (often via cached metadata / proxies), and collision detection runs against `site.pages` during the build (`bengal/orchestration/build/__init__.py:373-379`, `bengal/orchestration/build/initialization.py:175-237`).

If we add claim-time enforcement, we should confirm whether `site.pages` is always fully populated in all incremental contexts (especially dev server “site.pages was cleared” cases; see taxonomy phase comments in `bengal/orchestration/build/content.py:118-123`).

### i18n and versioning

The `URLRegistry` is **prefix-aware but globally unique**.

- **i18n**: If `i18n.strategy` is `prefix`, the URL passed to `claim()` must already be prefixed (e.g., `/en/about/`).
- **Versioning**: URLs for older versions (e.g., `/docs/v1/guide/`) are claimed just like any other URL. The `URLClaim` stores the `version` metadata to help with diagnostic reporting.

### Ownership policy questions (partially resolved)

#### 1) Autodoc section index vs. root element page

This collision exists historically and is now avoided by not creating a root page for the CLI command-group (`bengal/autodoc/orchestration/page_builders.py:92-102`). A registry-based system should encode this as policy (section index owns `/<prefix>/`).

#### 2) URLStrategy interaction

`URLStrategy` is already a pure utility for URL/output computation (`bengal/utils/url_strategy.py:19-31`). Option A should preserve that: producers compute output path/URL via `URLStrategy`, then immediately claim via `URLRegistry`.

```python
# In an Orchestrator
output_path = URLStrategy.compute_regular_page_output_path(page, site)
url = URLStrategy.url_from_output_path(output_path, site)

site.url_registry.claim(
    url=url,
    owner="content",
    source=str(page.source_path),
    priority=100
)
```

### Option B: Keep post-generation detection; add namespace reservation + policy validator

Build on today’s system:

- keep `Site.validate_no_url_collisions()` as the primary collision detector
- add an explicit “reserved namespace” contract (e.g., `/tags/`, `/cli/`, `/api/…`, `/search/`, `/graph/`) and validate that user-authored pages do not land in those namespaces unless explicitly configured
- prefer adding a dedicated **policy validator** (ownership rules) over adding claim-time state, unless we have strong evidence we need earlier enforcement

Pros:

- Smaller change surface area; aligns with existing build structure
- Keeps URL computation centralized in `URLStrategy`, and enforcement centralized in validators

Cons:

- Still not claim-time; producers can build conflicting pages before validation
- Harder to express fine-grained ownership (priority, overrides) without reintroducing ad-hoc logic

## Recommended Approach

### Phase 1: Define ownership policy + reporting (low-risk foundation)

1. Document “reserved namespaces” based on existing generators (tags, autodoc prefixes, special pages).
2. Add a policy validator (warning mode by default) that reports ownership violations separately from raw collisions.

### Phase 2: URL registry (Option A), if policy needs claim-time enforcement

1. **Add `URLRegistry` to `Site`**: Implement the centralized claim system with priority levels.
2. **Persistence**: Add `url_claims` to `BuildCache` to support incremental collision detection.
3. **Integration**: Update `ContentDiscovery`, `AutodocOrchestrator`, `TaxonomyOrchestrator`, and `SectionOrchestrator` to call `claim()` after computing paths via `URLStrategy`.
4. **Warning mode**: Keep warnings by default to avoid breaking existing sites; allow strict failure via existing `--strict` behavior.

Notes:

- CLI strict mode already exists and is used for collision detection (`bengal/orchestration/build/__init__.py:373-379`).
- `URLCollisionValidator` already exists and is registered in health checks (`bengal/health/health_check.py:150-153`).

### Phase 3: Cleanup & documentation

1. **Migrate Legacy Protections**: Move redirect and special page collision detection to the registry.
2. **Document Ownership**: Update `architecture/object-model.md` to include URL Ownership as a core concept.

## Priority levels (if Option A is adopted)

Suggested priority levels for URL claims:

| Priority | Owner | Rationale |
|----------|-------|-----------|
| 100 | User content | User intent always wins |
| 90 | Autodoc sections | Explicitly configured by user |
| 80 | Autodoc pages | Derived from sections |
| 50 | Section indexes | Structural authority |
| 50 | Section archives | Auto-generated |
| 40 | Taxonomy | Auto-generated |
| 10 | Special pages | Fallback utility pages |
| 5 | Redirects | Should never shadow actual content |

## Success Criteria

- [ ] Collisions are reported with both sources (already true; see `bengal/core/site/core.py:616-623`)
- [ ] Ownership violations (namespace/policy) are reported separately from collisions
- [ ] Existing sites continue to work with warnings by default
- [ ] Strict builds fail fast (already possible; see `bengal/core/site/core.py:637-639`)

## Related

- `rfc-url-collision-detection.md` - Tactical fix (now superseded)
- The autodoc bug we just fixed - Motivating example
- `postprocess/redirects.py` - Example of existing collision detection

## Confidence scoring

**Confidence**: 86% 🟢  

- **Evidence (36/40)**: Strong evidence for current behavior (build-phase collision detection, validators, redirects/search behavior). The registry itself is a proposal (no code yet), so evidence is not “direct implementation”.  
- **Consistency (25/30)**: Code + tests agree on collision detection and key generators. Some ownership-policy claims remain to be validated (e.g., which namespaces are “reserved” by convention vs. config).  
- **Recency (15/15)**: Evidence files modified recently (`git log` shows recent changes on 2025-12-20).  
- **Tests (10/15)**: Direct tests exist for collision detection and redirects; no tests yet for ownership-policy rules (because they do not exist yet).  
