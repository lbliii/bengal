# RFC: URL Collision Detection and Autodoc Navigation Improvements

**Status**: Implemented  
**Created**: 2024-12-20  
**Implemented**: 2024-12-20  
**Author**: AI Assistant (based on debugging session)

## Problem Statement

Debugging autodoc navigation issues is extremely difficult because:

1. **URL collisions are silent** - when two pages output to the same URL, the last one wins with no warning. The `NavTree._flat_nodes` index (a dictionary comprehension) silently overwrites previous entries during build.
2. **Post-build detection is too late** - While `SitemapValidator` detects duplicates, it runs during Phase 17 (Post-processing), after the build has already "succeeded" with broken navigation.
3. **Complex multi-system interaction** - autodoc → sections → pages → NavTree → templates.
4. **No visibility into NavTree building** - node overwrites happen silently in memory.

### Evidence: The Bug We Just Fixed

**Symptom**: CLI navigation was completely empty at `/cli/`

**Root Cause**: Two things outputting to `/cli/index.html`:
1. CLI section index page (`__virtual__/cli/section-index.md`)
2. Root CLI command page (`cli.md` for "bengal" command)

**Current Status**: A manual guard was added to `bengal/autodoc/orchestration/section_builders.py` to skip the root command group, but this is a reactive fix that doesn't protect other subsystems.

**Time to Diagnose**: ~2 hours of tracing through multiple systems. With proactive detection, this would be < 5 minutes.

## Goals

1. **Fail-fast on URL collisions** - Build should error (or warn) when two outputs claim same URL
2. **Better debugging** - Clear logs when navigation nodes are unexpectedly overwritten
3. **Test coverage** - Integration tests that verify autodoc navigation works end-to-end
4. **Clearer contracts** - Document which system "owns" each URL pattern

## Non-Goals

- Rewriting the entire autodoc system
- Changing how NavTree works fundamentally
- Supporting multiple pages at the same URL (that's never valid)

## Design Options

### Option A: URL Collision Detection at Build Time

**Add validation in `Site._set_output_paths()` or a new `_validate_urls()` method:**

```python
def _validate_no_url_collisions(self) -> None:
    """Detect when multiple pages output to the same URL."""
    urls_seen: dict[str, str] = {}  # url -> source description

    for page in self.pages:
        url = page.relative_url
        source = str(getattr(page, 'source_path', page.title))

        if url in urls_seen:
            raise ValueError(
                f"URL collision detected: {url}\n"
                f"  Already claimed by: {urls_seen[url]}\n"
                f"  Also claimed by: {source}\n"
                f"Tip: Check for duplicate slugs or conflicting autodoc output"
            )
        urls_seen[url] = source
```

**Pros**:
- Immediate, clear error message
- Catches the problem at source, not at symptom
- Easy to implement

**Cons**:
- May surface existing collisions (breaking change?)
- Need to decide: error or warning?

### Option B: NavTree Collision Logging

**Add debug logging when `_flat_nodes` overwrites an existing entry:**

```python
# In NavTree._build_node_recursive() or _index_nodes()
if url in self._flat_nodes:
    existing = self._flat_nodes[url]
    logger.warning(
        "nav_node_collision",
        url=url,
        existing_id=existing.id,
        existing_type="section" if existing.section else "page",
        new_id=node.id,
        new_type="section" if node.section else "page",
    )
```

**Pros**:
- Non-breaking (just logs)
- Helps diagnose issues faster
- Shows exactly where collision happens

**Cons**:
- Doesn't prevent the problem, just surfaces it
- Easy to miss in logs

### Option C: URL Registry (Architectural Solution)

**Create a central registry that all systems must register URLs with. This registry should be consulted during Phase 12 (Update Pages List) of the build.**

```python
class URLRegistry:
    """Central registry for all output URLs with priority handling."""

    def __init__(self):
        self._urls: dict[str, URLClaim] = {}

    def claim(self, url: str, source: str, priority: int = 0) -> None:
        """
        Priority levels:
        - 100: Manual content (explicit overrides)
        - 50:  Structural indexes (_index.md)
        - 10:  Generated autodoc content
        """
        # ... logic ...
```

**Usage:**
```python
# In autodoc section builder
site.url_registry.claim("/cli/", "autodoc:cli:section", priority=10)

# In autodoc page builder  
site.url_registry.claim("/cli/build/", "autodoc:cli:page:build", priority=5)

# If both try to claim /cli/:
# URLCollisionError: URL /cli/ already claimed by autodoc:cli:section
```

**Pros**:
- Architectural solution - prevents the class of bugs
- Clear ownership and priority
- Good debugging info

**Cons**:
- More invasive change
- Need to update all systems that create pages/sections
- Priority rules need careful design

### Option D: Integration Tests for Autodoc Navigation

**Add tests that verify autodoc navigation works end-to-end:**

```python
# tests/integration/test_autodoc_navigation.py

class TestCLIAutodocNavigation:
    """Verify CLI autodoc pages appear in navigation correctly."""

    def test_cli_section_has_navigation(self, built_site):
        """CLI section should have navigable children."""
        nav = NavTree.build(built_site)
        cli_node = nav.find("/cli/")

        assert cli_node is not None, "CLI section missing from NavTree"
        assert cli_node.section is not None, "CLI node should be a section, not page"
        assert len(cli_node.children) > 0, "CLI section has no children"

    def test_cli_commands_are_navigable(self, built_site):
        """Individual CLI commands should appear in navigation."""
        nav = NavTree.build(built_site)

        # Check known commands exist
        for cmd in ["build", "serve", "clean"]:
            node = nav.find(f"/cli/{cmd}/")
            assert node is not None, f"CLI command {cmd} missing from navigation"

    def test_no_url_collisions(self, built_site):
        """No two pages should have the same URL."""
        urls_seen: dict[str, str] = {}

        for page in built_site.pages:
            url = page.relative_url
            if url in urls_seen:
                pytest.fail(
                    f"URL collision: {url}\n"
                    f"  Page 1: {urls_seen[url]}\n"
                    f"  Page 2: {page.source_path}"
                )
            urls_seen[url] = str(page.source_path)


class TestPythonAutodocNavigation:
    """Verify Python autodoc sections work but pages are excluded."""

    def test_python_sections_navigable(self, built_site):
        """Python package sections should appear in navigation."""
        nav = NavTree.build(built_site)
        api_node = nav.find("/api/")

        assert api_node is not None
        assert len(api_node.children) > 0

    def test_python_pages_excluded(self, built_site):
        """Individual Python class/function pages should NOT be in nav."""
        nav = NavTree.build(built_site)

        # Classes and functions are too granular for nav
        for page in built_site.pages:
            if page.metadata.get("type") in ("python-class", "python-function"):
                url = page.relative_url
                node = nav.find(url)
                # Should not find a node for granular items
                assert node is None or node.page != page
```

**Pros**:
- Catches regressions
- Documents expected behavior
- Fast feedback loop

**Cons**:
- Doesn't prevent bugs, just catches them
- Need fixtures for autodoc content

## Recommended Approach

**Implement in phases:**

### Phase 1: Quick Wins (This PR)
1. ✅ Fix the immediate bug (skip root CLI command-group page)
2. Add NavTree collision logging (Option B)
3. Add basic integration test (Option D subset)

### Phase 2: Build Validation
1. Add `_validate_no_url_collisions()` (Option A)
2. Make it a warning by default, error in strict mode
3. Add to health check system

### Phase 3: Comprehensive Testing
1. Full integration test suite for autodoc navigation
2. Tests for Python, CLI, and OpenAPI autodoc types
3. Add to CI

### Phase 4: (Optional) URL Registry
1. If collisions keep happening, implement Option C
2. Add priority system for section vs page vs generated content

## Architecture Impact

### Systems Affected

| System | Change | Impact |
|--------|--------|--------|
| `Site` | Add `_validate_no_url_collisions()` | Low - new validation step |
| `NavTree` | Add collision logging | Low - debug logging only |
| `autodoc/page_builders` | Skip root elements | Done ✅ |
| `tests/` | Add integration tests | Medium - new test files |

### Risks

1. **Surfacing existing collisions** - May break builds that have silent collisions
   - Mitigation: Make warning by default, opt-in error

2. **Performance** - URL validation adds O(n) pass
   - Mitigation: Only run in non-incremental builds, or sample-check

## Success Criteria

- [x] CLI autodoc navigation works correctly (verified)
- [x] URL collisions produce clear warning/error
- [x] Integration tests catch navigation regressions
- [x] Debugging time for similar issues reduced from hours to minutes

## Implementation Summary

**Phase 1 (Implemented):**
- ✅ NavTree collision logging (`bengal/core/nav_tree.py`)
- ✅ `Site.validate_no_url_collisions()` method (`bengal/core/site/core.py`)
- ✅ `URLCollisionValidator` health check (`bengal/health/validators/url_collisions.py`)
- ✅ Build orchestrator integration with proactive validation
- ✅ Comprehensive integration tests (`tests/integration/test_autodoc_navigation.py`)

## Open Questions

1. Should URL collision be error or warning by default?
2. Should we validate during discovery or after all pages are created?
3. Do we need priority rules (section > page > generated)?

## Related

- `bengal/core/nav_tree.py` - NavTree building logic
- `bengal/autodoc/orchestration/page_builders.py` - Autodoc page creation
- `bengal/autodoc/orchestration/index_pages.py` - Section index creation
- Previous fix: Skip root CLI command-group to prevent collision

## Appendix: Debugging Timeline

The actual debugging session that inspired this RFC:

1. **Symptom observed**: CLI navigation empty at `/cli/`
2. **First hypothesis**: Sections not being added to site (wrong)
3. **Second hypothesis**: NavTree not finding CLI section (wrong)
4. **Third hypothesis**: Relative vs absolute paths (wrong - but surfaced a potential separate issue)
5. **Fourth hypothesis**: Multiple pages at same URL (correct!)
6. **Root cause found**: Root CLI command page colliding with section index
7. **Fix implemented**: Skip root command-group in page builder

Total time: ~2 hours. With URL collision detection, this would have been ~5 minutes.
