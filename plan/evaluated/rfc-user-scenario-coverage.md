# RFC: User Scenario Coverage & Validation Matrix

**Status**: Evaluated
**Created**: 2025-12-21
**Author**: AI-assisted
**Confidence**: 85% 🟢

---

## Problem Statement

Bengal has been developed primarily against the `site/` documentation site, which is documentation-heavy (177 files, predominantly in `docs/` hierarchy). While the architecture supports diverse site types via the Strategy Pattern (Blog, Docs, Portfolio, Landing, Changelog), validation of non-documentation workflows is limited.

**Current State**:
- 7 site templates: `default`, `docs`, `blog`, `portfolio`, `resume`, `landing`, `changelog`
- 12 test roots, mostly minimal (≤5 files each)
- 6,378 test functions across 396 files
- Primary validation against documentation patterns
- 21 RSS generator unit tests exist (`tests/unit/postprocess/test_rss_generator.py`)

**Pain Points**:
1. Blog pagination untested at scale
2. Mixed content sites (docs + blog + portfolio) not validated
3. Multi-language content workflows undocumented
4. Template scaffolding not integration-tested
5. Real-world blog/portfolio patterns may have untested edge cases

**Impact**:
- Users building blogs may hit untested pagination edge cases
- Portfolio/landing page users have less guidance
- Multi-language site users need workarounds
- First-time users scaffolding from templates may encounter issues

**Evidence**:

Test roots coverage (`tests/roots/`):
```
test-basic/       # 1 page, smoke test
test-baseurl/     # 2 pages, URL handling
test-taxonomy/    # 3 pages, tags
test-assets/      # 1 page + assets
test-directives/  # 4 pages, directive parsing
test-navigation/  # 7 pages, 3-level hierarchy
test-large/       # 100 pages, performance
test-cascade/     # 4 pages, frontmatter inheritance
test-versioned/   # versioned documentation
test-templates/   # template escaping
test-autodoc-*    # autodoc scenarios
```

Missing scenarios:
- ❌ Blog with pagination **integration test** (20+ posts in test root)
- ❌ Mixed content site (docs + blog + landing)
- ⚠️ Multi-language content structure (partial support via `i18n.content_structure: "dir"`)
- ❌ Portfolio with image galleries
- ⚠️ RSS integration test (unit tests exist, but no end-to-end blog+RSS test)

---

## Goals & Non-Goals

**Goals**:
1. Ensure all 7 site templates build and render correctly
2. Add test roots for underrepresented scenarios (blog, mixed, i18n)
3. Create integration tests validating template scaffolding
4. Document i18n content patterns (vs. UI translation)
5. Increase confidence for non-documentation use cases to ≥90%

**Non-Goals**:
- Adding new features (image resizing, new templates)
- Changing existing architecture
- Building a theme marketplace
- Full content translation workflow (future RFC)

---

## Design Options

### Option A: Test Root Expansion

Add 3-4 new test roots covering underrepresented scenarios.

**Proposed Roots**:
```
test-blog-paginated/     # 25 posts, pagination, archives
test-mixed-content/      # docs + blog + portfolio + landing
test-i18n-content/       # en/fr content with language switching
test-portfolio-gallery/  # projects with images
```

**Pros**:
- Minimal code changes (tests only)
- Validates existing functionality
- Catches regressions going forward
- Follows established test-root pattern

**Cons**:
- Test maintenance burden
- May require fixture generation scripts
- Doesn't add new features

### Option B: Template Integration Tests

Add parametrized integration tests that scaffold from each template, build, and validate.

**Proposed Test**:
```python
@pytest.mark.parametrize("template", ["default", "docs", "blog", "portfolio", "resume", "landing", "changelog"])
@pytest.mark.integration
def test_template_scaffolds_and_builds(template, tmp_path):
    """Scaffold from template, build, validate output."""
    site_dir = tmp_path / f"test-{template}"

    # Scaffold
    result = runner.invoke(cli, ["new", "site", str(site_dir), "--template", template])
    assert result.exit_code == 0

    # Build
    result = runner.invoke(cli, ["build"], cwd=site_dir)
    assert result.exit_code == 0

    # Validate
    output_dir = site_dir / "public"
    assert (output_dir / "index.html").exists()
    assert (output_dir / "sitemap.xml").exists()
```

**Pros**:
- Tests the actual user workflow (scaffold → build)
- Validates all templates with single test
- Catches template regressions

**Cons**:
- Slower tests (full scaffold + build)
- Requires CLI testing infrastructure
- May be flaky in CI

### Option C: User Scenario Matrix + Docs

Create explicit user scenario documentation and validation checklist.

**Proposed Structure**:
```
docs/reference/user-scenarios/
├── _index.md
├── blog-author.md           # Blog patterns, pagination, RSS
├── docs-maintainer.md       # Documentation patterns (current)
├── portfolio-creator.md     # Portfolio patterns
├── landing-page-builder.md  # Landing page patterns
├── multi-language-site.md   # i18n content patterns
└── mixed-content-site.md    # Combining content types
```

**Pros**:
- Helps users directly
- Documents expected patterns
- Lower maintenance than tests

**Cons**:
- Doesn't catch regressions
- Documentation can drift from code
- Less rigorous than tests

### Recommended: Option A + B (Combined)

Combine test root expansion with template integration tests for comprehensive coverage.

**Rationale**:
- Test roots validate specific scenarios in depth
- Integration tests validate user workflow end-to-end
- Together they catch different classes of issues
- Manageable scope (3 roots + 1 parametrized test for 7 templates)
- Leverages existing pagination/RSS unit tests (21+ tests already exist)

---

## Detailed Design

### Phase 1: Template Integration Tests

Add integration test for all templates:

```python
# tests/integration/test_template_scaffolding.py

@pytest.mark.parametrize("template", [
    "default",
    "docs",
    "blog",
    "portfolio",
    "resume",
    "landing",
    "changelog",
])
@pytest.mark.integration
def test_template_builds_successfully(template, tmp_path, cli_runner):
    """Each template should scaffold and build without errors."""
    site_dir = tmp_path / f"site-{template}"

    # Scaffold
    result = cli_runner.invoke(["new", "site", str(site_dir), "--template", template, "--yes"])
    assert result.exit_code == 0, f"Scaffold failed: {result.output}"

    # Build
    result = cli_runner.invoke(["build"], cwd=site_dir)
    assert result.exit_code == 0, f"Build failed: {result.output}"

    # Basic validation
    output = site_dir / "public"
    assert (output / "index.html").exists()
    assert (output / "sitemap.xml").exists()

    # Template-specific validation
    if template == "blog":
        # Should have RSS feed
        assert (output / "feed.xml").exists() or (output / "rss.xml").exists()
    elif template == "docs":
        # Should have search index
        assert (output / "search-index.json").exists() or (output / "index.json").exists()


@pytest.mark.integration
def test_template_with_custom_content(template, tmp_path, cli_runner):
    """Templates should handle additional user content."""
    # Scaffold, add content, rebuild
    pass
```

### Phase 2: New Test Roots

#### test-blog-paginated

**Purpose**: Validate blog with pagination, archives, RSS

**Structure**:
```
test-blog-paginated/
├── bengal.toml              # pagination: { per_page: 5 }
├── skeleton.yaml            # Declarative structure
└── content/
    ├── _index.md            # Blog home
    ├── posts/
    │   ├── _index.md        # Posts section
    │   ├── post-01.md       # date: 2025-01-01
    │   ├── post-02.md       # date: 2025-01-15
    │   ├── ...
    │   └── post-25.md       # date: 2025-12-15
    └── about.md             # Static page
```

**Config**:
```toml
[site]
title = "Test Blog"

[content]
default_type = "blog"
sort_pages_by = "date"
sort_order = "desc"

[pagination]
per_page = 5
```

**Test Cases**:
```python
@pytest.mark.bengal(testroot="test-blog-paginated")
class TestBlogPagination:
    def test_pagination_pages_created(self, site, build_site):
        build_site()
        # 25 posts / 5 per page = 5 pages
        assert (site.output_dir / "posts/page/2/index.html").exists()
        assert (site.output_dir / "posts/page/5/index.html").exists()
        assert not (site.output_dir / "posts/page/6/index.html").exists()

    def test_rss_feed_generated(self, site, build_site):
        build_site()
        assert (site.output_dir / "feed.xml").exists()
        rss = (site.output_dir / "feed.xml").read_text()
        assert "<item>" in rss
        assert "post-25" in rss  # Most recent

    def test_posts_sorted_by_date(self, site, build_site):
        build_site()
        index_html = (site.output_dir / "posts/index.html").read_text()
        # First page should have most recent posts
        assert "post-25" in index_html
        assert "post-21" in index_html
```

#### test-mixed-content

**Purpose**: Validate site with multiple content types

**Structure**:
```
test-mixed-content/
├── bengal.toml
└── content/
    ├── _index.md             # Landing page (type: landing)
    ├── docs/
    │   ├── _index.md         # cascade: type: doc
    │   ├── getting-started.md
    │   └── reference.md
    ├── blog/
    │   ├── _index.md         # cascade: type: blog
    │   ├── post-1.md
    │   └── post-2.md
    └── projects/
        ├── _index.md         # cascade: type: portfolio
        ├── project-alpha.md
        └── project-beta.md
```

**Test Cases**:
```python
@pytest.mark.bengal(testroot="test-mixed-content")
class TestMixedContent:
    def test_each_section_uses_correct_type(self, site):
        site.discover_content()

        doc = next(p for p in site.pages if "getting-started" in str(p.source_path))
        assert doc.content_type == "doc"

        post = next(p for p in site.pages if "post-1" in str(p.source_path))
        assert post.content_type == "blog"

        project = next(p for p in site.pages if "project-alpha" in str(p.source_path))
        assert project.content_type == "portfolio"

    def test_correct_sorting_per_section(self, site):
        site.discover_content()

        # Docs sorted by weight
        docs = [p for p in site.pages if "/docs/" in str(p.source_path)]
        # Blog sorted by date (newest first)
        posts = [p for p in site.pages if "/blog/" in str(p.source_path)]

    def test_navigation_spans_sections(self, site, build_site):
        build_site()
        # Main menu should have Docs, Blog, Projects
```

#### test-i18n-content

**Purpose**: Validate multi-language content patterns

**Existing Support** (verified in `bengal/discovery/content_discovery.py:158-173`):
- `i18n.strategy` config option
- `i18n.content_structure: "dir"` for directory-based content (e.g., `content/en/`, `content/fr/`)
- Language code extraction from directory prefixes
- `i18n.languages` configuration with code, name, weight

**Structure**:
```
test-i18n-content/
├── bengal.toml
├── i18n/
│   ├── en.yaml              # UI strings
│   └── fr.yaml
└── content/
    ├── en/
    │   ├── _index.md        # lang: en
    │   └── about.md
    └── fr/
        ├── _index.md        # lang: fr
        └── about.md
```

**Config**:
```toml
[i18n]
default_language = "en"
content_structure = "dir"
languages = [
    { code = "en", name = "English", weight = 1 },
    { code = "fr", name = "Français", weight = 2 },
]
```

**What Needs Testing** (not new features):
- Directory-based content discovery with language prefixes
- `alternate_links()` template function for hreflang tags
- `languages()` template function for language switcher
- Language fallback behavior

**Note**: The infrastructure exists in `content_discovery.py`. This phase validates existing functionality rather than implementing new features.

### Phase 3: Documentation Updates

Add user scenario guide:

```markdown
# docs/tutorials/user-scenarios.md

## Blog Author Workflow

1. Scaffold: `bengal new site myblog --template blog`
2. Configure pagination in `bengal.toml`
3. Add posts to `content/posts/`
4. Customize templates for archives

## Mixed Content Site

[Patterns for combining docs + blog + landing]

## Multi-Language Site

[Current limitations and workarounds]
```

---

## Architecture Impact

| Subsystem | Impact | Changes |
|-----------|--------|---------|
| Core | None | No changes |
| Orchestration | None | No changes |
| Rendering | None | No changes |
| Cache | None | No changes |
| Health | Minor | May add scenario validation |
| CLI | Minor | Integration test coverage |
| Tests | **Major** | New roots, new integration tests |

**Files Changed**:
```
tests/roots/test-blog-paginated/       # NEW
tests/roots/test-mixed-content/        # NEW
tests/integration/test_template_scaffolding.py  # NEW
tests/integration/test_blog_scenarios.py        # NEW
tests/integration/test_mixed_content.py         # NEW
site/content/docs/tutorials/user-scenarios.md   # NEW
```

---

## Testing Strategy

1. **Unit Tests**: None needed (no code changes)

2. **Integration Tests**:
   - Template scaffolding test (parametrized, 7 templates)
   - Blog pagination scenarios (extends existing RSS unit tests)
   - Mixed content type switching
   - RSS feed validation (integration-level, complements 21 existing unit tests)

3. **Performance Tests**:
   - Existing `test-large` covers performance
   - May add blog-specific perf test with 1000 posts

4. **Manual Validation**:
   - Scaffold each template locally
   - Build and inspect output
   - Verify dev server works

---

## Risks & Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Test maintenance burden | Medium | Low | Keep roots minimal, use skeleton.yaml |
| Flaky integration tests | Medium | Medium | Use `tmp_path`, isolate filesystem |
| i18n content needs feature work | **Low** | Medium | Infrastructure exists in `content_discovery.py`; likely just needs testing |
| Slows CI pipeline | Low | Low | Mark as `@pytest.mark.slow` |
| Test roots drift from templates | Medium | Medium | Generate roots from templates |

---

## Implementation Plan

**Phase 1: Template Integration Tests** (1 day)
- [ ] Create `tests/integration/test_template_scaffolding.py`
- [ ] Parametrized test for all 7 templates (default, docs, blog, portfolio, resume, landing, changelog)
- [ ] Add to CI

**Phase 2: Blog Test Root** (1 day)
- [ ] Create `test-blog-paginated/` with 25 posts
- [ ] Add generation script for posts
- [ ] Write pagination tests
- [ ] Write RSS tests

**Phase 3: Mixed Content Test Root** (1 day)
- [ ] Create `test-mixed-content/` structure
- [ ] Write content type switching tests
- [ ] Write cross-section navigation tests

**Phase 4: Documentation** (0.5 day)
- [ ] Add user scenario guide
- [ ] Document i18n limitations
- [ ] Update limitations.md

**Phase 5: i18n Content Validation** (0.5 day)
- [ ] Verify `i18n.content_structure: "dir"` works with `content/en/`, `content/fr/` structure
- [ ] Test `alternate_links()` template function generates correct hreflang tags
- [ ] Test `languages()` template function returns configured languages
- [ ] Test language fallback behavior (`fallback_to_default: true`)
- [ ] Document working patterns or create feature RFC for gaps

**Total Estimate**: 4 days

---

## Open Questions

- [ ] Should test roots be generated from templates (DRY) or hand-crafted (explicit)?
- [x] Is content-level i18n (not just UI strings) in scope for 1.0? → **Partially supported**: `content_discovery.py` has `content_structure: "dir"` support; needs validation testing
- [ ] Should we add a `test-real-world` root that clones an actual user site?
- [ ] Do we need Windows-specific test runs in CI?
- [ ] Should the `default` template be included in integration tests? (It's minimal but validates base scaffolding)

---

## Success Criteria

1. ✅ All 7 templates scaffold and build without errors
2. ✅ Blog pagination works for 25+ posts
3. ✅ Mixed content site renders with correct types/sorting
4. ✅ i18n directory-based content structure validated
5. ✅ User scenario documentation exists
6. ✅ Confidence for non-documentation use cases ≥ 90%

---

## References

- **Evidence**: `tests/roots/README.md` - current test root documentation
- **Templates**: `bengal/cli/templates/` - site template implementations (7 templates)
- **Content Types**: `bengal/content_types/strategies.py` - strategy pattern implementation
- **i18n UI**: `bengal/rendering/template_functions/i18n.py` - UI translation support
- **i18n Content**: `bengal/discovery/content_discovery.py:158-173` - content structure i18n
- **Pagination**: `bengal/utils/pagination.py`, `bengal/rendering/template_functions/pagination_helpers.py`
- **RSS Tests**: `tests/unit/postprocess/test_rss_generator.py` - 21 unit tests
- **Pagination Tests**: `tests/unit/utils/test_pagination.py`, `tests/unit/template_functions/test_pagination_helpers.py`
