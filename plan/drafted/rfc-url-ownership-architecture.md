# RFC: URL Ownership Architecture

**Status**: Draft
**Created**: 2024-12-20
**Supersedes**: rfc-url-collision-detection.md (elevates from tactical fix to architectural solution)

## Problem Statement

Bengal has **7+ independent systems** that can generate pages, each computing URLs independently with no coordination:

| System | Location | Example Output |
|--------|----------|----------------|
| Content Discovery | `discovery/content_discovery.py` | `/docs/guide/` |
| Autodoc Pages | `autodoc/orchestration/page_builders.py` | `/api/bengal/core/` |
| Autodoc Section Index | `autodoc/orchestration/index_pages.py` | `/cli/` |
| Section Archives | `orchestration/section.py` | `/blog/` (auto-generated) |
| Taxonomy (Tags) | `orchestration/taxonomy.py` | `/tags/python/` |
| Special Pages | `postprocess/special_pages.py` | `/404.html`, `/search/` |
| Redirects | `postprocess/redirects.py` | Any alias path |

### Current State: Hope-Based Architecture

Each system **hopes** its URLs don't collide with others. No central authority validates or coordinates.

```
┌─────────────────┐   ┌─────────────────┐   ┌─────────────────┐
│    Content      │   │    Autodoc      │   │   Taxonomy      │
│   Discovery     │   │   Generation    │   │   Generator     │
└────────┬────────┘   └────────┬────────┘   └────────┬────────┘
         │                     │                     │
         │  "I'll use /api/"   │  "I'll use /api/"   │  "I'll use /tags/"
         │                     │                     │
         ▼                     ▼                     ▼
┌─────────────────────────────────────────────────────────────┐
│                     site.pages                               │
│                                                              │
│   Last one wins. No validation. Silent overwrites.           │
└─────────────────────────────────────────────────────────────┘
```

## Collision Scenarios

### Already Possible Today

| Scenario | User Action | System Action | Result |
|----------|-------------|---------------|--------|
| Content + Autodoc | Create `content/api/index.md` | Autodoc outputs to `/api/` | Collision |
| Content + Tags | Create `content/tags/python.md` | Tag system creates `/tags/python/` | Collision |
| Content + Search | Create `content/search.md` | Special pages creates `/search/` | Collision |
| Content + 404 | Create `content/404.md` | Special pages creates `/404.html` | Collision |
| Redirects + Content | Set `aliases: [/about/]` | Content exists at `/about/` | Redirect overwrites content |
| Autodoc internal | CLI section index at `/cli/` | CLI root command at `/cli/` | **THE BUG WE JUST FIXED** |

### Future Risks

| Scenario | Trigger | Impact |
|----------|---------|--------|
| Plugins | Third-party plugin creates pages | No URL coordination |
| Custom content types | New type with own URL strategy | Conflicts with existing |
| Multi-site | Shared content across sites | Cross-site URL conflicts |
| Dynamic routes | API routes in dev server | Static pages shadow routes |
| i18n edge cases | Default language handling | `/en/about/` vs `/about/` |

## Evidence: Partial Protections That Exist

Some systems have ad-hoc collision detection:

### Redirects (Good Example)
```python
# postprocess/redirects.py:82-90
for alias, claimants in alias_map.items():
    if len(claimants) > 1:
        self.logger.warning(
            "redirect_alias_conflict",
            alias=alias,
            claimants=[...],
            hint="Multiple pages claim the same alias; only the first will be used",
        )
```

### Special Pages (Partial)
```python
# special_pages.py checks if user content exists before generating
# But doesn't handle all edge cases
```

### Most Systems (No Protection)
```python
# Most systems just append to site.pages without checking
site.pages.append(page)  # Hope for the best!
```

## Goals

1. **Make invalid states unrepresentable** - Can't create two pages at same URL
2. **Explicit ownership** - Clear rules for who "owns" each URL pattern
3. **Fail-fast** - Collisions detected at creation time, not render time
4. **Extensible** - Plugins can participate in URL coordination

## Non-Goals

- Changing how existing URLs are computed (backward compatibility)
- Supporting multiple pages at the same URL (never valid)
- Runtime URL resolution (static site generator)

## Design Options

### Option A: URL Registry (Centralized Authority)

```python
class URLRegistry:
    """Central authority for all URL claims."""

    def __init__(self):
        self._claims: dict[str, URLClaim] = {}

    def claim(
        self,
        url: str,
        owner: str,
        source: str,
        priority: int = 0,
    ) -> None:
        """
        Claim a URL for output.

        Args:
            url: The URL being claimed (e.g., "/cli/")
            owner: System claiming it ("content", "autodoc:cli", "taxonomy", etc.)
            source: Specific source (file path, element name, etc.)
            priority: Higher priority wins ties (section > page > generated)

        Raises:
            URLCollisionError: If URL already claimed
        """
        normalized = self._normalize(url)

        if normalized in self._claims:
            existing = self._claims[normalized]
            if existing.priority >= priority:
                raise URLCollisionError(
                    url=url,
                    existing_owner=existing.owner,
                    existing_source=existing.source,
                    new_owner=owner,
                    new_source=source,
                )
            # New claim has higher priority - warn and override
            logger.warning(
                "url_claim_override",
                url=url,
                old_owner=existing.owner,
                new_owner=owner,
            )

        self._claims[normalized] = URLClaim(
            owner=owner,
            source=source,
            priority=priority,
        )

    def is_claimed(self, url: str) -> bool:
        """Check if URL is already claimed."""
        return self._normalize(url) in self._claims

    def get_owner(self, url: str) -> str | None:
        """Get the owner of a URL."""
        claim = self._claims.get(self._normalize(url))
        return claim.owner if claim else None
```

**Usage:**

```python
# In content discovery
for page in discovered_pages:
    site.url_registry.claim(
        url=page.relative_url,
        owner="content",
        source=str(page.source_path),
        priority=10,  # Content has high priority
    )

# In autodoc
for element in elements:
    site.url_registry.claim(
        url=element_url,
        owner=f"autodoc:{doc_type}",
        source=element.qualified_name,
        priority=5,  # Autodoc has medium priority
    )

# In taxonomy
for tag in tags:
    site.url_registry.claim(
        url=f"/tags/{tag_slug}/",
        owner="taxonomy",
        source=f"tag:{tag}",
        priority=1,  # Generated content has low priority
    )
```

**Pros:**
- Single source of truth
- Clear error messages
- Extensible (plugins just call `claim()`)
- Priority system handles intentional overrides

**Cons:**
- Requires touching all page-generating code
- Migration path needed for existing sites

### Option B: Namespace Contracts (Convention-Based)

Define explicit contracts for which system owns which URL patterns:

```yaml
# config/_default/url_namespaces.yaml
namespaces:
  # Content owns everything by default
  content:
    patterns: ["**/*"]
    priority: 100
    conflicts: error

  # Autodoc owns /api/ and /cli/
  autodoc:
    patterns:
      - "/api/**"
      - "/cli/**"
    priority: 90
    conflicts: error

  # Taxonomy owns /tags/ and /categories/
  taxonomy:
    patterns:
      - "/tags/**"
      - "/categories/**"
    priority: 50
    conflicts: warn  # User content wins

  # Special pages
  special:
    patterns:
      - "/404.html"
      - "/search/"
      - "/graph/"
    priority: 10
    conflicts: skip  # User content always wins
```

**Validation:**

```python
def validate_url_namespaces(site: Site) -> list[str]:
    """Validate that all pages respect namespace contracts."""
    errors = []

    for page in site.pages:
        url = page.relative_url
        owner = get_page_owner(page)  # Infer from source
        namespace = get_namespace_for_url(url)

        if namespace.owner != owner:
            if namespace.conflicts == "error":
                errors.append(f"{url}: owned by {namespace.owner}, claimed by {owner}")
            elif namespace.conflicts == "warn":
                logger.warning(f"{url}: namespace conflict ({namespace.owner} vs {owner})")
            # "skip" = silently allow override

    return errors
```

**Pros:**
- Declarative, easy to understand
- No code changes to page generators
- Clear documentation of ownership

**Cons:**
- Pattern matching can be ambiguous
- Doesn't prevent collisions within a namespace
- Less precise than explicit registration

### Option C: Section-Centric Model (Architectural Refactor)

Make Sections the sole authority for their URL space:

```python
class Section:
    """Section owns all URLs under its path."""

    def claim_url(self, relative_path: str, page: Page) -> None:
        """
        Claim a URL within this section.

        Args:
            relative_path: Path relative to section (e.g., "guide/" for /docs/guide/)
            page: Page claiming the URL

        Raises:
            URLCollisionError: If URL already claimed within this section
        """
        full_url = f"{self.relative_url}{relative_path}"

        if relative_path in self._url_claims:
            existing = self._url_claims[relative_path]
            raise URLCollisionError(
                url=full_url,
                existing=existing,
                new=page,
            )

        self._url_claims[relative_path] = page

    @property
    def index_page(self) -> Page | None:
        """The page at this section's root URL."""
        return self._url_claims.get("")
```

**All page creation goes through sections:**

```python
# Instead of site.pages.append(page)
section.claim_url("guide/", page)

# Section index is explicit
section.set_index_page(page)
```

**Pros:**
- Natural hierarchy matches URL structure
- Sections are already the organizational unit
- Collision detection is localized

**Cons:**
- Major refactor of page creation
- What about pages without sections (homepage)?
- Cross-section links still possible

## Recommended Approach

**Phase 1: URL Registry (Option A)**

1. Add `URLRegistry` to `Site`
2. Add `claim()` calls to all page-generating code
3. Default to warning mode (don't break existing sites)
4. Add `--strict-urls` flag for error mode

**Phase 2: Namespace Contracts (Option B)**

1. Add namespace configuration
2. Validate pages against namespaces
3. Document ownership conventions

**Phase 3: Cleanup**

1. Fix any detected collisions in default site
2. Add integration tests for namespace boundaries
3. Document URL ownership in architecture docs

## Priority Levels

Suggested priority levels for URL claims:

| Priority | Owner | Rationale |
|----------|-------|-----------|
| 100 | User content | User intent always wins |
| 90 | Autodoc sections | Configured by user |
| 80 | Autodoc pages | Derived from sections |
| 50 | Section archives | Auto-generated, can be overridden |
| 40 | Taxonomy | Auto-generated |
| 10 | Special pages | Fallback only |
| 5 | Redirects | Should never shadow content |

## Migration Path

1. **Add registry** - All existing code continues to work (no claims = no validation)
2. **Add claims incrementally** - One system at a time
3. **Warning mode** - Log collisions but don't fail
4. **Error mode** - Opt-in via config or CLI flag
5. **Default to error** - After sites have been validated

## Success Criteria

- [ ] No two pages can output to the same URL without explicit error/warning
- [ ] Clear error messages identify both conflicting sources
- [ ] Plugins can participate in URL coordination
- [ ] Existing sites continue to work (backward compatible)
- [ ] URL ownership is documented and queryable

## Open Questions

1. Should section index pages and element pages be separate concepts?
2. How do we handle versioned URLs (same logical page, different version URLs)?
3. Should i18n URLs be in the same registry or separate per-language?

## Related

- `rfc-url-collision-detection.md` - Tactical fix (now superseded)
- The autodoc bug we just fixed - Motivating example
- `postprocess/redirects.py` - Example of existing collision detection
