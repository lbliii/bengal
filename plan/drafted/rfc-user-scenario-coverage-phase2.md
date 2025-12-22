# RFC: User Scenario Coverage Phase 2 - Extended Validation

**Status**: Draft
**Created**: 2025-12-21
**Author**: AI-assisted
**Depends On**: RFC User Scenario Coverage (Phase 1) ✅ Implemented
**Confidence**: 75% 🟡

---

## Problem Statement

Phase 1 of User Scenario Coverage validated core use cases (docs, blogs, portfolios, mixed content, basic i18n). However, several scenarios remain under-validated or unsupported:

**Current Gaps**:

| Area | Status | Impact |
|------|--------|--------|
| Resume/Changelog templates | 🟡 Moderate | Templates exist but lack integration tests |
| Full i18n workflow | 🟡 Partial | Directory structure works; UI strings, hreflang, language switcher untested |
| Image galleries | 🟠 Unknown | Portfolio users need image galleries; no validation |
| E-commerce/Product pages | 🟠 Limited | Growing use case with no template support |
| Extreme scale (10k+ pages) | 🟡 Partial | Only 100-page test exists; unknown perf at scale |

**User Impact**:
- Resume/changelog users may hit untested edge cases in data-driven rendering
- Multi-language site authors lack clear workflow documentation and tested patterns
- Portfolio creators need manual gallery implementation
- Performance-sensitive users have no confidence data for large sites

---

## Goals & Non-Goals

**Goals**:
1. Validate resume and changelog templates with integration tests
2. Complete i18n workflow with UI translation, hreflang, and language switcher
3. Add image gallery directive and portfolio gallery patterns
4. Create product/e-commerce template for product-focused sites
5. Establish 10k+ page performance baseline and optimization guide
6. Increase scenario coverage confidence to ≥95%

**Non-Goals**:
- Full e-commerce with checkout (external services like Snipcart/Stripe handle this)
- Complex CMS features (content scheduling, drafts, approval workflows)
- Real-time features (comments, live updates)
- CDN or hosting automation

---

## Design Options

### Option A: Incremental Validation Only

Add tests for existing templates without new features.

**Scope**:
- Resume template tests (data-driven content)
- Changelog template tests (version entries)
- 10k page performance benchmark
- Document current i18n limitations

**Pros**:
- Minimal code changes
- Quick to implement
- Documents current state accurately

**Cons**:
- Doesn't address image gallery or e-commerce gaps
- i18n remains incomplete
- Users still need workarounds

**Estimate**: 2 days

### Option B: Feature Completion + Validation

Complete missing features then validate them.

**Scope**:
- Resume/changelog integration tests
- i18n: Add UI translation loading, hreflang helper, language switcher component
- Add `::gallery` directive for image galleries
- Add `product` template with structured data
- 10k page benchmark with optimization guide

**Pros**:
- Addresses all identified gaps
- Provides complete solutions users need
- Increases Bengal's competitive positioning

**Cons**:
- More code to maintain
- Longer implementation time
- New features need documentation

**Estimate**: 8-10 days

### Option C: Tiered Approach (Recommended)

Prioritize by user impact, implement in phases.

**Tier 1 (High Impact, Quick Wins)** - 2 days:
- Resume/changelog integration tests
- 10k page performance benchmark
- Document i18n current state + limitations

**Tier 2 (Complete i18n)** - 3 days:
- UI translation file loading (`i18n/en.yaml`, `i18n/fr.yaml`)
- `t()` template function for UI strings
- `alternate_links()` for hreflang SEO tags
- `languages()` for language switcher
- Language switcher partial in default theme

**Tier 3 (Content Features)** - 3 days:
- `::gallery` directive for image galleries
- Product template with JSON-LD structured data
- Product listing and detail page layouts

**Pros**:
- Delivers value incrementally
- Can ship Tier 1 quickly
- Prioritizes by user impact
- Each tier is independently valuable

**Cons**:
- More planning overhead
- Risk of incomplete tiers

**Estimate**: 8 days total (can ship Tier 1 in 2 days)

---

## Detailed Design

### Tier 1: Validation & Performance

#### 1.1 Resume Template Tests

**Test Root**: `tests/roots/test-resume/`

```yaml
# data/resume.yaml
name: "Test Developer"
title: "Senior Engineer"
contact:
  email: "test@example.com"
  github: "testdev"
experience:
  - title: "Lead Engineer"
    company: "Tech Corp"
    dates: "2022-Present"
    highlights:
      - "Led team of 5"
      - "Reduced build time 50%"
education:
  - degree: "B.S. Computer Science"
    school: "State University"
    year: 2018
skills:
  - category: "Languages"
    items: ["Python", "TypeScript", "Go"]
```

**Tests**:
```python
@pytest.mark.bengal(testroot="test-resume")
class TestResumeTemplate:
    def test_resume_data_loaded(self, site):
        """Resume data from YAML should be accessible."""
        data = site.data.get("resume", {})
        assert data.get("name") == "Test Developer"
        assert len(data.get("experience", [])) >= 1

    def test_resume_builds_successfully(self, site, build_site):
        """Resume site should build without errors."""
        build_site()
        assert (site.output_dir / "index.html").exists()

    def test_resume_contains_data_sections(self, site, build_site):
        """Built resume should render all data sections."""
        build_site()
        html = (site.output_dir / "index.html").read_text()
        assert "Test Developer" in html
        assert "Lead Engineer" in html
        assert "Tech Corp" in html
```

#### 1.2 Changelog Template Tests

**Test Root**: `tests/roots/test-changelog/`

```yaml
# data/changelog.yaml
releases:
  - version: "2.0.0"
    date: 2025-06-01
    changes:
      - type: added
        description: "Major new feature"
      - type: changed
        description: "Breaking API change"
      - type: deprecated
        description: "Old method deprecated"
  - version: "1.5.0"
    date: 2025-03-15
    changes:
      - type: added
        description: "Minor feature"
      - type: fixed
        description: "Bug fix"
```

**Tests**:
```python
@pytest.mark.bengal(testroot="test-changelog")
class TestChangelogTemplate:
    def test_changelog_data_loaded(self, site):
        """Changelog data from YAML should be accessible."""
        data = site.data.get("changelog", {})
        releases = data.get("releases", [])
        assert len(releases) >= 2

    def test_changelog_sorted_by_version(self, site, build_site):
        """Changelog should display versions in order."""
        build_site()
        html = (site.output_dir / "index.html").read_text()
        # 2.0.0 should appear before 1.5.0
        pos_2 = html.find("2.0.0")
        pos_1 = html.find("1.5.0")
        assert pos_2 < pos_1, "Versions should be in descending order"

    def test_changelog_groups_by_change_type(self, site, build_site):
        """Changelog should group changes by type (added, fixed, etc.)."""
        build_site()
        html = (site.output_dir / "index.html").read_text().lower()
        assert "added" in html
        assert "changed" in html or "fixed" in html
```

#### 1.3 Performance Benchmark (10k Pages)

**Benchmark Script**: `benchmarks/test_10k_site.py`

```python
@pytest.mark.slow
@pytest.mark.benchmark
def test_10k_site_build_performance(tmp_path, benchmark):
    """Benchmark build performance for 10k page site."""
    # Generate 10k pages across 100 sections
    generate_large_site(tmp_path, sections=100, pages_per_section=100)

    site = Site.from_config(tmp_path)

    # Benchmark discovery
    discovery_time = benchmark(site.discover_content)

    # Benchmark build
    build_time = benchmark(lambda: site.build(parallel=True))

    # Performance gates
    assert discovery_time < 30.0, "Discovery should complete in <30s for 10k pages"
    assert build_time < 120.0, "Build should complete in <2min for 10k pages"

def test_10k_site_memory_usage(tmp_path):
    """Verify memory usage stays reasonable for large sites."""
    import tracemalloc

    generate_large_site(tmp_path, sections=100, pages_per_section=100)

    tracemalloc.start()
    site = Site.from_config(tmp_path)
    site.discover_content()
    site.build(parallel=True)

    current, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    # Peak memory should stay under 2GB for 10k pages
    assert peak < 2 * 1024 * 1024 * 1024, f"Peak memory {peak / 1e9:.2f}GB exceeds 2GB limit"
```

---

### Tier 2: Complete i18n Workflow

#### 2.1 UI Translation Files

**Structure**:
```
i18n/
├── en.yaml      # English UI strings
├── fr.yaml      # French UI strings
└── es.yaml      # Spanish UI strings
```

**Example** (`i18n/en.yaml`):
```yaml
# Navigation
nav.home: "Home"
nav.docs: "Documentation"
nav.blog: "Blog"

# Common UI
ui.read_more: "Read more"
ui.posted_on: "Posted on"
ui.by_author: "by"
ui.search_placeholder: "Search..."
ui.no_results: "No results found"

# Footer
footer.copyright: "© {year} {site_title}. All rights reserved."
footer.powered_by: "Powered by Bengal"
```

#### 2.2 Translation Template Function

**Implementation**: `bengal/rendering/template_functions/i18n.py`

```python
def t(key: str, **kwargs) -> str:
    """
    Translate a UI string key with optional interpolation.

    Usage in templates:
        {{ t('nav.home') }}
        {{ t('footer.copyright', year=2025, site_title='My Site') }}
    """
    lang = get_current_language()
    translations = load_translations(lang)

    template = translations.get(key, key)  # Fallback to key if missing

    if kwargs:
        template = template.format(**kwargs)

    return template
```

#### 2.3 Hreflang Helper

**Implementation**: Add to existing `bengal/rendering/template_functions/i18n.py`

```python
def alternate_links(page: Page) -> list[dict]:
    """
    Generate alternate language links for SEO hreflang tags.

    Usage in templates:
        {% for alt in alternate_links(page) %}
        <link rel="alternate" hreflang="{{ alt.lang }}" href="{{ alt.url }}">
        {% endfor %}

    Returns:
        List of dicts with 'lang' and 'url' keys
    """
    alternates = []

    for lang_config in site.i18n.languages:
        lang = lang_config.code
        translated_page = find_translation(page, lang)

        if translated_page:
            alternates.append({
                'lang': lang,
                'url': translated_page.url,
                'name': lang_config.name,
            })

    # Add x-default pointing to default language
    alternates.append({
        'lang': 'x-default',
        'url': find_translation(page, site.i18n.default_language).url,
    })

    return alternates
```

#### 2.4 Language Switcher Component

**Theme Partial**: `themes/default/partials/language-switcher.html`

```html
{% set current_lang = page.lang or site.i18n.default_language %}
{% set alternates = alternate_links(page) %}

{% if alternates|length > 1 %}
<div class="language-switcher">
  <button class="language-switcher-toggle" aria-label="{{ t('ui.select_language') }}">
    <span class="current-lang">{{ current_lang|upper }}</span>
    <svg class="icon"><use href="#icon-globe"></use></svg>
  </button>
  <ul class="language-switcher-menu">
    {% for alt in alternates if alt.lang != 'x-default' %}
    <li {% if alt.lang == current_lang %}class="active"{% endif %}>
      <a href="{{ alt.url }}" hreflang="{{ alt.lang }}">
        {{ alt.name }}
      </a>
    </li>
    {% endfor %}
  </ul>
</div>
{% endif %}
```

#### 2.5 i18n Integration Tests

**Test Root**: `tests/roots/test-i18n-full/`

```python
@pytest.mark.bengal(testroot="test-i18n-full")
class TestI18nFullWorkflow:
    def test_ui_translations_loaded(self, site):
        """UI translation files should be loaded."""
        translations = site.get_translations("en")
        assert translations.get("nav.home") == "Home"

        translations_fr = site.get_translations("fr")
        assert translations_fr.get("nav.home") == "Accueil"

    def test_t_function_interpolates(self, site, build_site):
        """t() function should interpolate variables."""
        build_site()
        html = (site.output_dir / "en" / "index.html").read_text()
        assert "© 2025" in html  # footer.copyright interpolated

    def test_hreflang_tags_generated(self, site, build_site):
        """Pages should have hreflang tags for SEO."""
        build_site()
        html = (site.output_dir / "en" / "about" / "index.html").read_text()
        assert 'hreflang="en"' in html
        assert 'hreflang="fr"' in html
        assert 'hreflang="x-default"' in html

    def test_language_switcher_renders(self, site, build_site):
        """Language switcher should appear on pages."""
        build_site()
        html = (site.output_dir / "en" / "index.html").read_text()
        assert "language-switcher" in html
```

---

### Tier 3: Content Features

#### 3.1 Gallery Directive

**Directive**: `::gallery`

**Usage**:
```markdown
:::{gallery}
:columns: 3
:lightbox: true

![Photo 1](/images/gallery/photo1.jpg)
![Photo 2](/images/gallery/photo2.jpg)
![Photo 3](/images/gallery/photo3.jpg)
![Photo 4](/images/gallery/photo4.jpg)
:::
```

**Implementation**: `bengal/directives/gallery.py`

```python
from bengal.directives.base import Directive, DirectiveResult

class GalleryDirective(Directive):
    """
    Render a responsive image gallery with optional lightbox.

    Options:
        columns: Number of columns (default: 3)
        lightbox: Enable lightbox mode (default: true)
        gap: Gap between images (default: 1rem)
    """
    name = "gallery"

    def render(self, content: str, options: dict) -> DirectiveResult:
        columns = options.get("columns", 3)
        lightbox = options.get("lightbox", True)
        gap = options.get("gap", "1rem")

        # Parse images from content (markdown image syntax)
        images = self.parse_images(content)

        html = f'''
        <div class="gallery"
             style="--gallery-columns: {columns}; --gallery-gap: {gap};"
             data-lightbox="{str(lightbox).lower()}">
        '''

        for img in images:
            html += f'''
            <figure class="gallery-item">
                <img src="{img.src}" alt="{img.alt}" loading="lazy">
                {f'<figcaption>{img.alt}</figcaption>' if img.alt else ''}
            </figure>
            '''

        html += '</div>'

        return DirectiveResult(html=html, requires_js="gallery")
```

**CSS** (add to theme):
```css
.gallery {
  display: grid;
  grid-template-columns: repeat(var(--gallery-columns, 3), 1fr);
  gap: var(--gallery-gap, 1rem);
}

.gallery-item {
  overflow: hidden;
  border-radius: var(--radius-md);
}

.gallery-item img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  transition: transform 0.3s ease;
}

.gallery-item:hover img {
  transform: scale(1.05);
}

@media (max-width: 768px) {
  .gallery {
    grid-template-columns: repeat(2, 1fr);
  }
}

@media (max-width: 480px) {
  .gallery {
    grid-template-columns: 1fr;
  }
}
```

#### 3.2 Product Template

**Template Structure**:
```
bengal/cli/templates/product/
├── __init__.py
├── template.py
├── skeleton.yaml
└── pages/
    ├── _index.md
    ├── products/
    │   ├── _index.md
    │   ├── product-1.md
    │   └── product-2.md
    ├── features.md
    ├── pricing.md
    └── contact.md
```

**Product Frontmatter Schema**:
```yaml
---
title: "Product Name"
type: product
price: 99.99
currency: USD
sku: "PROD-001"
in_stock: true
images:
  - /images/product-1.jpg
  - /images/product-1-alt.jpg
features:
  - "Feature 1"
  - "Feature 2"
structured_data: true  # Generate JSON-LD
---
```

**JSON-LD Generation** (for SEO):
```html
{% if page.structured_data and page.type == 'product' %}
<script type="application/ld+json">
{
  "@context": "https://schema.org/",
  "@type": "Product",
  "name": "{{ page.title }}",
  "description": "{{ page.description }}",
  "image": {{ page.images | tojson }},
  "sku": "{{ page.sku }}",
  "offers": {
    "@type": "Offer",
    "price": "{{ page.price }}",
    "priceCurrency": "{{ page.currency }}",
    "availability": "{% if page.in_stock %}https://schema.org/InStock{% else %}https://schema.org/OutOfStock{% endif %}"
  }
}
</script>
{% endif %}
```

#### 3.3 Gallery & Product Tests

```python
@pytest.mark.bengal(testroot="test-gallery")
class TestGalleryDirective:
    def test_gallery_renders_images(self, site, build_site):
        """Gallery directive should render responsive grid."""
        build_site()
        html = (site.output_dir / "gallery" / "index.html").read_text()
        assert 'class="gallery"' in html
        assert 'gallery-item' in html.count >= 3

    def test_gallery_lightbox_enabled(self, site, build_site):
        """Gallery should include lightbox data attribute."""
        build_site()
        html = (site.output_dir / "gallery" / "index.html").read_text()
        assert 'data-lightbox="true"' in html


@pytest.mark.bengal(testroot="test-product")
class TestProductTemplate:
    def test_product_jsonld_generated(self, site, build_site):
        """Product pages should generate JSON-LD structured data."""
        build_site()
        html = (site.output_dir / "products" / "product-1" / "index.html").read_text()
        assert 'application/ld+json' in html
        assert '"@type": "Product"' in html

    def test_product_listing_page(self, site, build_site):
        """Product listing should show all products."""
        build_site()
        html = (site.output_dir / "products" / "index.html").read_text()
        assert "product-1" in html.lower()
        assert "product-2" in html.lower()
```

---

## Architecture Impact

| Subsystem | Tier 1 | Tier 2 | Tier 3 |
|-----------|--------|--------|--------|
| Core | None | None | None |
| Orchestration | None | None | None |
| Rendering | None | `t()` function | Gallery directive |
| Discovery | None | i18n file loading | None |
| Cache | None | None | None |
| CLI | None | None | Product template |
| Tests | **Major** | **Major** | **Major** |
| Themes | None | Language switcher | Gallery CSS, product layouts |

---

## Implementation Plan

### Tier 1 (2 days)

**Day 1**:
- [ ] Create `test-resume/` test root with data
- [ ] Create `test-changelog/` test root with data
- [ ] Write resume template integration tests
- [ ] Write changelog template integration tests

**Day 2**:
- [ ] Create 10k page generation script
- [ ] Write performance benchmark tests
- [ ] Document performance baseline
- [ ] Update limitations.md with current i18n state

### Tier 2 (3 days)

**Day 3**:
- [ ] Implement i18n file loading in discovery
- [ ] Implement `t()` template function
- [ ] Write unit tests for translation loading

**Day 4**:
- [ ] Implement `alternate_links()` function
- [ ] Implement `languages()` function
- [ ] Create language switcher partial

**Day 5**:
- [ ] Create `test-i18n-full/` test root
- [ ] Write i18n integration tests
- [ ] Update i18n documentation

### Tier 3 (3 days)

**Day 6**:
- [ ] Implement `::gallery` directive
- [ ] Add gallery CSS to default theme
- [ ] Write gallery tests

**Day 7**:
- [ ] Create product template scaffold
- [ ] Implement JSON-LD generation
- [ ] Add product CSS to theme

**Day 8**:
- [ ] Write product template tests
- [ ] Update template documentation
- [ ] Final review and polish

---

## Risks & Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| i18n complexity scope creep | Medium | High | Stick to defined API; no pluralization in v1 |
| Gallery lightbox JS complexity | Medium | Medium | Use existing lightbox library (GLightbox) |
| Product template too opinionated | Low | Medium | Make structured_data opt-in |
| 10k benchmark too slow for CI | High | Low | Mark as `@pytest.mark.slow`, run nightly only |
| Breaking changes to i18n config | Medium | High | Maintain backward compatibility with current config |

---

## Success Criteria

1. ✅ Resume and changelog templates have ≥3 integration tests each
2. ✅ 10k page site builds in <2 minutes, <2GB peak memory
3. ✅ Full i18n workflow documented with working example
4. ✅ `t()`, `alternate_links()`, `languages()` functions work correctly
5. ✅ Language switcher component in default theme
6. ✅ Gallery directive renders responsive grid with lightbox
7. ✅ Product template with JSON-LD structured data
8. ✅ All scenarios covered with integration tests
9. ✅ Overall scenario coverage confidence ≥95%

---

## Open Questions

- [ ] Should `t()` support pluralization in v1? (Recommendation: No, add in v2)
- [ ] Should gallery support video? (Recommendation: Images only in v1)
- [ ] Should product template include cart integration examples? (Recommendation: Document Snipcart/Stripe but don't implement)
- [ ] What's the acceptable performance degradation for i18n overhead? (<5% build time)
- [ ] Should language switcher use dropdown or inline links? (Recommendation: Dropdown for >3 languages)

---

## References

- **Phase 1 RFC**: `plan/ready/rfc-user-scenario-coverage.md` ✅
- **i18n Current State**: `bengal/discovery/content_discovery.py:158-173`
- **Template Functions**: `bengal/rendering/template_functions/`
- **Directives**: `bengal/directives/`
- **Performance Benchmarks**: `benchmarks/`
- **Existing Templates**: `bengal/cli/templates/`
