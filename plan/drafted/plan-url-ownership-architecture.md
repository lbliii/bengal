# Plan: URL Ownership Architecture

**RFC**: `rfc-url-ownership-architecture.md`  
**Status**: Draft  
**Created**: 2024-12-20  
**Estimated Time**: 3-4 days

---

## Summary

Implement URL ownership system with claim-time enforcement, priority levels, and clear diagnostics. Enables explicit ownership policy for URLs across content, autodoc, taxonomy, special pages, and redirects.

---

## Tasks

### Phase 1: Foundation (Policy + Reserved Namespaces)

#### Task 1.1: Define Reserved Namespace Configuration
- **Files**: `bengal/config/defaults.py` (or new `bengal/config/url_policy.py`)
- **Action**: Define reserved namespace patterns based on existing generators
  ```python
  RESERVED_NAMESPACES = {
      "tags": {"owner": "taxonomy", "priority": 40},
      "search": {"owner": "special_pages", "priority": 10},
      "404": {"owner": "special_pages", "priority": 10},
      "graph": {"owner": "special_pages", "priority": 10},
      # Autodoc prefixes configured at runtime from site config
  }
  ```
- **Commit**: `config: add reserved URL namespace definitions for ownership policy`

#### Task 1.2: Create URLClaim Dataclass
- **Files**: `bengal/core/url_ownership.py` (new file)
- **Action**: Create immutable dataclass for URL claims
  ```python
  @dataclass(frozen=True)
  class URLClaim:
      owner: str       # "content", "autodoc:python", "taxonomy", etc.
      source: str      # File path or qualified name
      priority: int    # 100=User, 50=Generated, etc.
      version: str | None = None
      lang: str | None = None
  ```
- **Commit**: `core: add URLClaim dataclass for URL ownership tracking`

#### Task 1.3: Create URLCollisionError Exception
- **Files**: `bengal/core/url_ownership.py`
- **Action**: Add exception with helpful diagnostics
  ```python
  class URLCollisionError(Exception):
      def __init__(self, url: str, existing: URLClaim, new_owner: str, new_source: str):
          # Format with source comparison, priority info, fix suggestions
  ```
- **Depends on**: Task 1.2
- **Commit**: `core: add URLCollisionError with diagnostic context`

#### Task 1.4: Create OwnershipPolicyValidator
- **Files**: `bengal/health/validators/ownership_policy.py` (new file)
- **Action**: Validate that user content respects reserved namespaces
  - Check if content pages land in reserved namespaces (`/tags/`, autodoc prefixes, etc.)
  - Warning mode by default (no build failure)
  - Report ownership violations separately from raw collisions
- **Depends on**: Task 1.1
- **Commit**: `health: add OwnershipPolicyValidator for namespace reservation checks`

#### Task 1.5: Register OwnershipPolicyValidator
- **Files**: `bengal/health/health_check.py`
- **Action**: Add validator to default health checks
- **Depends on**: Task 1.4
- **Commit**: `health: register OwnershipPolicyValidator in default checks`

---

### Phase 2: URL Registry (Claim-Time Enforcement)

#### Task 2.1: Create URLRegistry Class
- **Files**: `bengal/core/url_ownership.py`
- **Action**: Implement central registry with claim-time enforcement
  ```python
  class URLRegistry:
      def __init__(self):
          self._claims: dict[str, URLClaim] = {}

      def claim(self, url: str, owner: str, source: str, priority: int = 50, ...) -> None:
          """Claim URL, raise URLCollisionError on conflict."""

      def claim_output_path(self, output_path: Path, *, site: Site, ...) -> str:
          """Claim output path, return canonical URL."""

      def get_claim(self, url: str) -> URLClaim | None:
          """Get existing claim for URL."""

      def all_claims(self) -> dict[str, URLClaim]:
          """Return all current claims."""
  ```
- **Depends on**: Task 1.2, Task 1.3
- **Commit**: `core: add URLRegistry for claim-time URL ownership enforcement`

#### Task 2.2: Add URLRegistry to Site
- **Files**: `bengal/core/site/core.py`, `bengal/core/site/__init__.py`
- **Action**:
  - Add `url_registry: URLRegistry` attribute to Site
  - Initialize in `__init__` or `__post_init__`
  - Reset on `clear_pages()` if appropriate
- **Depends on**: Task 2.1
- **Commit**: `core(site): add url_registry attribute for claim-time ownership`

#### Task 2.3: Add URL Reverse Lookup to URLStrategy
- **Files**: `bengal/utils/url_strategy.py`
- **Action**: Add `url_from_output_path()` method for direct writers
  ```python
  @staticmethod
  def url_from_output_path(output_path: Path, site: Site) -> str:
      """Compute canonical URL from output path."""
  ```
- **Commit**: `utils(url_strategy): add url_from_output_path for registry integration`

#### Task 2.4: Integrate Registry with ContentDiscovery
- **Files**: `bengal/discovery/content_discovery.py`
- **Action**: After computing output path via URLStrategy, claim URL in registry
  - Use priority 100 for user content
  - Include source_path in claim
- **Depends on**: Task 2.2, Task 2.3
- **Commit**: `discovery: claim URLs in registry during content discovery`

#### Task 2.5: Integrate Registry with SectionOrchestrator
- **Files**: `bengal/orchestration/section_orchestrator.py`
- **Action**: Claim section index URLs with priority 50
- **Depends on**: Task 2.2
- **Commit**: `orchestration(section): claim section index URLs in registry`

#### Task 2.6: Integrate Registry with TaxonomyOrchestrator
- **Files**: `bengal/orchestration/taxonomy_orchestrator.py`
- **Action**: Claim taxonomy URLs with priority 40
  - `/tags/<tag>/` pages
  - `/tags/` list page
- **Depends on**: Task 2.2
- **Commit**: `orchestration(taxonomy): claim taxonomy URLs in registry`

#### Task 2.7: Integrate Registry with AutodocOrchestrator
- **Files**: `bengal/autodoc/orchestration/index_pages.py`, `bengal/autodoc/orchestration/page_builders.py`
- **Action**:
  - Claim section index URLs (priority 90)
  - Claim element page URLs (priority 80)
  - Use owner format "autodoc:<section_id>"
- **Depends on**: Task 2.2
- **Commit**: `autodoc: claim autodoc page URLs in registry with section context`

#### Task 2.8: Integrate Registry with RedirectGenerator
- **Files**: `bengal/postprocess/redirects.py`
- **Action**:
  - Use `claim_output_path()` before writing redirect
  - Priority 5 (lowest)
  - Replace `output_path.exists()` check with registry claim
- **Depends on**: Task 2.2, Task 2.3
- **Commit**: `postprocess(redirects): use URLRegistry claim-before-write pattern`

#### Task 2.9: Integrate Registry with SpecialPagesGenerator
- **Files**: `bengal/postprocess/special_pages.py`
- **Action**:
  - Claim `/search/`, `/404.html`, `/graph/` with priority 10
  - Replace ad-hoc "content/search.md exists" check with registry lookup
- **Depends on**: Task 2.2, Task 2.3
- **Commit**: `postprocess(special_pages): use URLRegistry for ownership checks`

---

### Phase 3: Cache Persistence & Incremental Safety

#### Task 3.1: Add URL Claims to BuildCache
- **Files**: `bengal/cache/build_cache.py`
- **Action**:
  - Add `url_claims: dict[str, dict]` section to cache
  - Serialize/deserialize URLClaim objects
  - Support incremental builds by loading prior claims
- **Depends on**: Task 2.1
- **Commit**: `cache: persist URL claims for incremental build safety`

#### Task 3.2: Load Cached Claims on Incremental Build
- **Files**: `bengal/orchestration/build/initialization.py`
- **Action**:
  - Load prior claims from cache
  - Pre-populate registry for pages not being rebuilt
- **Depends on**: Task 3.1
- **Commit**: `orchestration(build): load cached URL claims for incremental safety`

---

### Phase 4: Cleanup & Documentation

#### Task 4.1: Migrate validate_no_url_collisions to Use Registry
- **Files**: `bengal/core/site/core.py`
- **Action**:
  - Refactor `validate_no_url_collisions()` to query registry
  - Add ownership context to collision messages
- **Depends on**: Task 2.2
- **Commit**: `core(site): refactor validate_no_url_collisions to use URLRegistry`

#### Task 4.2: Update URLCollisionValidator
- **Files**: `bengal/health/validators/url_collisions.py`
- **Action**:
  - Use registry claims for enhanced collision reporting
  - Include ownership context in error messages
- **Depends on**: Task 2.2
- **Commit**: `health: enhance URLCollisionValidator with ownership context from registry`

#### Task 4.3: Add Unit Tests for URLRegistry
- **Files**: `tests/unit/core/test_url_ownership.py` (new file)
- **Action**:
  - Test URLClaim dataclass
  - Test URLRegistry claim/collision logic
  - Test priority-based resolution
  - Test claim_output_path
- **Depends on**: Task 2.1
- **Commit**: `tests: add comprehensive URLRegistry unit tests`

#### Task 4.4: Add Integration Tests
- **Files**: `tests/integration/test_url_ownership.py` (new file)
- **Action**:
  - Test content vs taxonomy collision (registry rejects)
  - Test redirect vs content (priority wins)
  - Test special page opt-out (user content overrides)
  - Test incremental build with cached claims
- **Depends on**: Task 3.2
- **Commit**: `tests: add URL ownership integration tests`

#### Task 4.5: Document URL Ownership in Architecture
- **Files**: `site/content/docs/reference/architecture/core/object-model.md`
- **Action**:
  - Add "URL Ownership" section
  - Document URLRegistry API
  - Document priority levels
  - Document reserved namespaces
- **Depends on**: Phase 2 complete
- **Commit**: `docs: document URL ownership architecture in object-model.md`

---

### Phase 5: Validation & Verification

- [ ] Unit tests pass (`pytest tests/unit/core/test_url_ownership.py`)
- [ ] Integration tests pass (`pytest tests/integration/test_url_ownership.py`)
- [ ] All existing tests pass (`pytest tests/`)
- [ ] Linter passes (`ruff check bengal/`)
- [ ] Type checker passes (`mypy bengal/core/url_ownership.py`)
- [ ] Health validators pass on test-basic site
- [ ] Build succeeds with strict mode on documentation site

---

## Priority Levels Reference

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

---

## Risk Mitigation

1. **Backward Compatibility**: Warning mode by default; strict mode opt-in via `--strict`
2. **Incremental Adoption**: Phase 1 can ship independently as policy reporting
3. **Dev Server Safety**: Ensure `site.clear_pages()` resets registry appropriately
4. **Performance**: Registry is O(1) lookup; minimal overhead

---

## Success Criteria

- [ ] Collisions reported with both sources and ownership context
- [ ] Ownership violations (namespace policy) reported separately from collisions
- [ ] Existing sites continue to work with warnings by default
- [ ] Strict builds fail fast on collision
- [ ] Redirects and special pages cannot overwrite real content (claim-before-write)
- [ ] Cache persists claims for incremental safety

---

## Changelog Entry

```markdown
### Added
- **URL Ownership System**: Explicit URL ownership with claim-time enforcement
  - `URLRegistry` on `Site` for centralized claim management
  - Priority-based conflict resolution (user content wins)
  - `claim_output_path()` API for direct file writers
  - Incremental build safety via cached claims
- **Ownership Policy Validator**: Warns when content lands in reserved namespaces
- Reserved namespace configuration for `/tags/`, autodoc prefixes, special pages

### Changed
- Redirect generator uses claim-before-write pattern
- Special pages generator checks registry before writing
- `validate_no_url_collisions()` includes ownership context

### Fixed
- Redirects no longer silently overwrite content (claim-time rejection)
- Special pages respect user content at `/search/`, etc.
```
