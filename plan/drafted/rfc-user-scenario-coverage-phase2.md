# RFC: User Scenario Coverage Phase 2 - Extended Validation

**Status**: Draft  
**Created**: 2025-12-21  
**Author**: AI-assisted  
**Depends On**: RFC User Scenario Coverage (Phase 1) - `plan/ready/rfc-user-scenario-coverage.md`  
**Confidence**: 88% 🟢

---

## Problem Statement

Phase 1 of User Scenario Coverage created test infrastructure for core use cases. This RFC extends validation to remaining gaps and adds new content features.

**Current State** (verified against codebase):

| Area | Status | Evidence |
|------|--------|----------|
| Resume/Changelog templates | ✅ Templates exist | `bengal/cli/templates/resume/`, `bengal/cli/templates/changelog/` |
| Resume/Changelog tests | ❌ Missing | No integration tests in `tests/` |
| i18n template functions | ✅ Implemented | `bengal/rendering/template_functions/i18n.py:94-135` |
| i18n content discovery | ✅ Implemented | `bengal/discovery/content_discovery.py:153-173` |
| Language switcher partial | ❌ Missing | No `partials/` directory in default theme |
| i18n integration tests | ❌ Missing | `test-i18n-content/` has config but no content |
| Gallery directive | ❌ Missing | Not in `bengal/directives/` |
| Product template | ❌ Missing | Not in `bengal/cli/templates/` |
| 10k page benchmark | ⚠️ Partial | Referenced in `benchmarks/` but no dedicated test |
| test-blog-paginated | ✅ Exists | `tests/roots/test-blog-paginated/` with 25 posts |

**Verified Existing i18n Functions** (`bengal/rendering/template_functions/i18n.py`):
- `t(key, params, lang)` - UI translation with fallback (line 108)
- `alternate_links(page)` - hreflang generation (line 121, impl 245-276)
- `languages()` - configured languages list (line 118, impl 146-181)
- `current_lang()` - current language detection (line 113)
- `locale_date(date, format, lang)` - localized date formatting (line 124)

**Remaining Gaps**:
1. **Resume/Changelog integration tests** - Templates work but untested
2. **Language switcher UI component** - Backend exists, frontend missing
3. **i18n integration tests** - Functions exist but no end-to-end tests
4. **Gallery directive** - Portfolio users need image galleries
5. **Product template** - E-commerce/product-focused sites unsupported
6. **10k page benchmark** - Performance at scale unvalidated

---

## Goals & Non-Goals

**Goals**:
1. Add integration tests for resume and changelog templates
2. Create language switcher partial for default theme
3. Add integration tests for existing i18n functions
4. Implement `::gallery` directive for image galleries
5. Create product template with JSON-LD structured data
6. Establish 10k+ page performance baseline
7. Achieve ≥95% scenario coverage confidence

**Non-Goals**:
- Reimplementing i18n functions (already exist and work)
- Full e-commerce checkout (use Snipcart/Stripe)
- Complex CMS features (scheduling, drafts, workflows)
- CDN or hosting automation

---

## Design Options

### Option A: Testing Only (Minimal Scope)

Test existing functionality without new features.

**Scope**:
- Resume/changelog integration tests
- i18n integration tests (using existing functions)
- 10k page benchmark
- Document current capabilities

**Pros**: Minimal code, quick to ship, validates current state  
**Cons**: No gallery, no product template, no language switcher UI  
**Estimate**: 2 days

### Option B: Full Feature + Testing (Recommended)

Complete gaps and add comprehensive tests.

**Scope**:
- All testing from Option A
- Language switcher partial (theme)
- Gallery directive (new)
- Product template (new)

**Pros**: Addresses all user-facing gaps, complete solution  
**Cons**: More code to maintain  
**Estimate**: 5-6 days

---

## Detailed Design

### Tier 1: Template Testing & Performance (2 days)

#### 1.1 Resume Template Tests

**Test Root**: `tests/roots/test-resume/`

Uses existing template data schema from `bengal/cli/templates/resume/data/resume.yaml`.

```python
@pytest.mark.bengal(testroot="test-resume")
class TestResumeTemplate:
    def test_resume_data_loaded(self, site):
        """Resume data from YAML should be accessible."""
        data = site.data.get("resume", {})
        assert data.get("name")
        assert len(data.get("experience", [])) >= 1
        assert len(data.get("skills", [])) >= 1

    def test_resume_builds_successfully(self, site, build_site):
        """Resume site should build without errors."""
        build_site()
        assert (site.output_dir / "index.html").exists()

    def test_resume_renders_all_sections(self, site, build_site):
        """Built resume should render experience, education, skills."""
        build_site()
        html = (site.output_dir / "index.html").read_text()
        # Verify key sections from resume.yaml
        assert "experience" in html.lower() or "work" in html.lower()
        assert "education" in html.lower()
        assert "skills" in html.lower()
```

#### 1.2 Changelog Template Tests

**Test Root**: `tests/roots/test-changelog/`

Uses existing template data schema from `bengal/cli/templates/changelog/data/changelog.yaml`.

```python
@pytest.mark.bengal(testroot="test-changelog")
class TestChangelogTemplate:
    def test_changelog_data_loaded(self, site):
        """Changelog releases should be accessible."""
        data = site.data.get("changelog", {})
        releases = data.get("releases", [])
        assert len(releases) >= 2

    def test_changelog_builds_successfully(self, site, build_site):
        """Changelog site should build without errors."""
        build_site()
        assert (site.output_dir / "index.html").exists()

    def test_changelog_displays_versions(self, site, build_site):
        """Changelog should display version numbers."""
        build_site()
        html = (site.output_dir / "index.html").read_text()
        assert "1.0.0" in html or "0.9.0" in html
```

#### 1.3 Performance Benchmark (10k Pages)

**Location**: `benchmarks/test_10k_site.py`

```python
import tracemalloc
import pytest
from pathlib import Path

def generate_large_site(root: Path, sections: int = 100, pages_per_section: int = 100):
    """Generate a 10k page site for benchmarking."""
    content_dir = root / "content"
    content_dir.mkdir(parents=True, exist_ok=True)

    for s in range(sections):
        section_dir = content_dir / f"section-{s:03d}"
        section_dir.mkdir(exist_ok=True)
        (section_dir / "_index.md").write_text(f"---\ntitle: Section {s}\n---\n")

        for p in range(pages_per_section):
            (section_dir / f"page-{p:03d}.md").write_text(
                f"---\ntitle: Page {s}-{p}\ndate: 2025-01-{(p % 28) + 1:02d}\n---\n\nContent for page {s}-{p}.\n"
            )

@pytest.mark.slow
@pytest.mark.benchmark
def test_10k_site_discovery_performance(tmp_path, benchmark):
    """Benchmark content discovery for 10k pages."""
    from bengal.core import Site

    generate_large_site(tmp_path, sections=100, pages_per_section=100)
    (tmp_path / "bengal.toml").write_text('[site]\ntitle = "Benchmark"\nbaseurl = "/"')

    site = Site.from_config(tmp_path)
    result = benchmark(site.discover_content)

    assert len(site.pages) == 10000 + 100  # pages + section indexes
    # Gate: discovery should complete in <30s
    assert benchmark.stats.stats.mean < 30.0

@pytest.mark.slow  
@pytest.mark.benchmark
def test_10k_site_memory_usage(tmp_path):
    """Verify memory stays reasonable for 10k pages."""
    from bengal.core import Site

    generate_large_site(tmp_path, sections=100, pages_per_section=100)
    (tmp_path / "bengal.toml").write_text('[site]\ntitle = "Benchmark"\nbaseurl = "/"')

    tracemalloc.start()
    site = Site.from_config(tmp_path)
    site.discover_content()

    current, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    # Gate: peak memory <2GB for 10k pages
    assert peak < 2 * 1024 * 1024 * 1024, f"Peak {peak / 1e9:.2f}GB exceeds 2GB"
```

---

### Tier 2: i18n Testing & Language Switcher (1 day)

**Note**: i18n template functions already exist. This tier focuses on testing and the missing language switcher UI.

#### 2.1 Populate test-i18n-content Test Root

**Existing**: `tests/roots/test-i18n-content/bengal.toml` (config ready)  
**Missing**: Content directories

```
tests/roots/test-i18n-content/
├── bengal.toml          # ✅ Exists
├── i18n/
│   ├── en.yaml          # NEW
│   └── fr.yaml          # NEW
└── content/
    ├── en/
    │   ├── _index.md    # NEW
    │   └── about.md     # NEW
    └── fr/
        ├── _index.md    # NEW
        └── about.md     # NEW
```

#### 2.2 i18n Integration Tests

Test the **existing** functions in `bengal/rendering/template_functions/i18n.py`:

```python
@pytest.mark.bengal(testroot="test-i18n-content")
class TestI18nIntegration:
    def test_t_function_translates(self, site, build_site):
        """t() should translate UI strings."""
        build_site()
        en_html = (site.output_dir / "en" / "index.html").read_text()
        fr_html = (site.output_dir / "fr" / "index.html").read_text()

        # Verify different translations rendered
        assert "Home" in en_html or "Welcome" in en_html
        assert "Accueil" in fr_html or "Bienvenue" in fr_html

    def test_alternate_links_generated(self, site, build_site):
        """alternate_links() should generate hreflang tags."""
        build_site()
        html = (site.output_dir / "en" / "about" / "index.html").read_text()

        assert 'hreflang="en"' in html
        assert 'hreflang="fr"' in html
        assert 'hreflang="x-default"' in html

    def test_languages_returns_configured(self, site):
        """languages() should return configured language list."""
        from bengal.rendering.template_functions.i18n import _languages

        langs = _languages(site)
        codes = [l["code"] for l in langs]

        assert "en" in codes
        assert "fr" in codes
```

#### 2.3 Language Switcher Partial

**New File**: `bengal/themes/default/layouts/partials/language-switcher.html`

```html
{#- Language Switcher Component
    Requires: page with translations, i18n configured
    Uses: alternate_links(page), languages(), current_lang()
-#}
{% set current = current_lang() %}
{% set alternates = alternate_links(page) %}
{% set langs = languages() %}

{% if langs|length > 1 %}
<div class="language-switcher" role="navigation" aria-label="{{ t('ui.language_selection', 'Language') }}">
  <button class="language-switcher__toggle" aria-expanded="false" aria-haspopup="listbox">
    <span class="language-switcher__current">{{ current|upper }}</span>
    <svg class="language-switcher__icon" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor">
      <path d="M12 21a9 9 0 1 0 0-18 9 9 0 0 0 0 18z"/>
      <path d="M3.6 9h16.8M3.6 15h16.8"/>
      <path d="M12 3a15 15 0 0 1 0 18 15 15 0 0 1 0-18z"/>
    </svg>
  </button>
  <ul class="language-switcher__menu" role="listbox">
    {% for alt in alternates if alt.hreflang != 'x-default' %}
    {% set lang_info = langs|selectattr('code', 'equalto', alt.hreflang)|first %}
    <li role="option" {% if alt.hreflang == current %}aria-selected="true" class="active"{% endif %}>
      <a href="{{ alt.href }}" hreflang="{{ alt.hreflang }}">
        {{ lang_info.name if lang_info else alt.hreflang|upper }}
      </a>
    </li>
    {% endfor %}
  </ul>
</div>
{% endif %}
```

**CSS** (add to theme stylesheet):

```css
/* Language Switcher */
.language-switcher {
  position: relative;
  display: inline-block;
}

.language-switcher__toggle {
  display: flex;
  align-items: center;
  gap: 0.25rem;
  padding: 0.5rem 0.75rem;
  background: transparent;
  border: 1px solid var(--color-border, #e5e7eb);
  border-radius: var(--radius-md, 0.375rem);
  cursor: pointer;
  font-size: 0.875rem;
  color: inherit;
}

.language-switcher__toggle:hover {
  background: var(--color-surface-hover, #f9fafb);
}

.language-switcher__menu {
  display: none;
  position: absolute;
  top: 100%;
  right: 0;
  min-width: 120px;
  margin-top: 0.25rem;
  padding: 0.25rem 0;
  background: var(--color-surface, #fff);
  border: 1px solid var(--color-border, #e5e7eb);
  border-radius: var(--radius-md, 0.375rem);
  box-shadow: var(--shadow-md);
  list-style: none;
  z-index: 50;
}

.language-switcher__menu.open {
  display: block;
}

.language-switcher__menu a {
  display: block;
  padding: 0.5rem 1rem;
  color: inherit;
  text-decoration: none;
}

.language-switcher__menu a:hover {
  background: var(--color-surface-hover, #f9fafb);
}

.language-switcher__menu .active a {
  font-weight: 600;
  color: var(--color-primary, #3b82f6);
}
```

---

### Tier 3: Content Features (3 days)

#### 3.1 Gallery Directive

**New File**: `bengal/directives/gallery.py`

```python
"""
Gallery directive for responsive image galleries.

Usage:
    :::{gallery}
    :columns: 3
    :lightbox: true
    :gap: 1rem

    ![Alt 1](/images/photo1.jpg)
    ![Alt 2](/images/photo2.jpg)
    :::
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from bengal.directives.base import Directive, DirectiveResult


@dataclass
class GalleryImage:
    """Parsed image from markdown syntax."""
    src: str
    alt: str


class GalleryDirective(Directive):
    """Render responsive image gallery with optional lightbox."""

    name = "gallery"

    # Markdown image pattern: ![alt](src)
    IMAGE_PATTERN = re.compile(r'!\[([^\]]*)\]\(([^)]+)\)')

    def render(self, content: str, options: dict[str, Any]) -> DirectiveResult:
        columns = options.get("columns", 3)
        lightbox = options.get("lightbox", True)
        gap = options.get("gap", "1rem")

        images = self._parse_images(content)

        if not images:
            return DirectiveResult(html="<!-- gallery: no images found -->")

        html_parts = [
            f'<div class="gallery" ',
            f'style="--gallery-columns: {columns}; --gallery-gap: {gap};" ',
            f'data-lightbox="{str(lightbox).lower()}">',
        ]

        for img in images:
            html_parts.append(
                f'<figure class="gallery__item">'
                f'<img src="{img.src}" alt="{img.alt}" loading="lazy">'
                f'{"<figcaption>" + img.alt + "</figcaption>" if img.alt else ""}'
                f'</figure>'
            )

        html_parts.append('</div>')

        return DirectiveResult(
            html=''.join(html_parts),
            requires_js="gallery" if lightbox else None,
        )

    def _parse_images(self, content: str) -> list[GalleryImage]:
        """Extract images from markdown content."""
        return [
            GalleryImage(src=match.group(2), alt=match.group(1))
            for match in self.IMAGE_PATTERN.finditer(content)
        ]
```

**Register** in `bengal/directives/__init__.py`:

```python
from bengal.directives.gallery import GalleryDirective
# Add to registry
```

**Gallery CSS** (add to theme):

```css
/* Gallery Directive */
.gallery {
  display: grid;
  grid-template-columns: repeat(var(--gallery-columns, 3), 1fr);
  gap: var(--gallery-gap, 1rem);
}

.gallery__item {
  position: relative;
  overflow: hidden;
  border-radius: var(--radius-md, 0.375rem);
  aspect-ratio: 4/3;
  margin: 0;
}

.gallery__item img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  transition: transform 0.3s ease;
}

.gallery__item:hover img {
  transform: scale(1.05);
}

.gallery__item figcaption {
  position: absolute;
  bottom: 0;
  left: 0;
  right: 0;
  padding: 0.5rem;
  background: linear-gradient(transparent, rgba(0,0,0,0.7));
  color: white;
  font-size: 0.875rem;
}

@media (max-width: 768px) {
  .gallery { grid-template-columns: repeat(2, 1fr); }
}

@media (max-width: 480px) {
  .gallery { grid-template-columns: 1fr; }
}
```

#### 3.2 Product Template

**New Template**: `bengal/cli/templates/product/`

Structure:
```
product/
├── __init__.py
├── template.py
├── skeleton.yaml
├── data/
│   └── products.yaml
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
  - /images/products/item-1.jpg
  - /images/products/item-1-alt.jpg
features:
  - "Feature one description"
  - "Feature two description"
structured_data: true  # Generate JSON-LD for SEO
---
```

**JSON-LD Partial** (`partials/product-jsonld.html`):

```html
{% if page.structured_data and page.type == 'product' %}
<script type="application/ld+json">
{
  "@context": "https://schema.org/",
  "@type": "Product",
  "name": {{ page.title | tojson }},
  "description": {{ page.description | default(page.summary) | tojson }},
  "image": {{ page.images | default([]) | tojson }},
  "sku": {{ page.sku | tojson }},
  "offers": {
    "@type": "Offer",
    "price": {{ page.price | string | tojson }},
    "priceCurrency": {{ page.currency | default("USD") | tojson }},
    "availability": "https://schema.org/{% if page.in_stock %}InStock{% else %}OutOfStock{% endif %}"
  }
}
</script>
{% endif %}
```

#### 3.3 Tests

```python
@pytest.mark.bengal(testroot="test-gallery")
class TestGalleryDirective:
    def test_gallery_renders_grid(self, site, build_site):
        """Gallery should render as CSS grid."""
        build_site()
        html = (site.output_dir / "gallery" / "index.html").read_text()
        assert 'class="gallery"' in html
        assert 'gallery__item' in html

    def test_gallery_parses_images(self, site, build_site):
        """Gallery should parse markdown images."""
        build_site()
        html = (site.output_dir / "gallery" / "index.html").read_text()
        assert html.count('gallery__item') >= 3

    def test_gallery_lightbox_attribute(self, site, build_site):
        """Gallery should include lightbox data attribute."""
        build_site()
        html = (site.output_dir / "gallery" / "index.html").read_text()
        assert 'data-lightbox="true"' in html


@pytest.mark.bengal(testroot="test-product")
class TestProductTemplate:
    def test_product_jsonld_generated(self, site, build_site):
        """Product pages should include JSON-LD structured data."""
        build_site()
        html = (site.output_dir / "products" / "product-1" / "index.html").read_text()
        assert 'application/ld+json' in html
        assert '"@type": "Product"' in html

    def test_product_listing(self, site, build_site):
        """Product index should list all products."""
        build_site()
        html = (site.output_dir / "products" / "index.html").read_text()
        assert "product-1" in html.lower() or "Product 1" in html
```

---

## Architecture Impact

| Subsystem | Tier 1 | Tier 2 | Tier 3 |
|-----------|--------|--------|--------|
| Core | None | None | None |
| Orchestration | None | None | None |
| Rendering | None | None | Gallery directive |
| Discovery | None | None | None |
| Cache | None | None | None |
| CLI | None | None | Product template |
| Tests | **+3 test files** | **+1 test file** | **+2 test files** |
| Themes | None | Language switcher partial + CSS | Gallery CSS, product layouts |

**New Files**:
- `tests/roots/test-resume/` (test root)
- `tests/roots/test-changelog/` (test root)
- `tests/integration/test_resume_changelog.py`
- `benchmarks/test_10k_site.py`
- `bengal/themes/default/layouts/partials/language-switcher.html`
- `bengal/directives/gallery.py`
- `bengal/cli/templates/product/` (template package)

---

## Implementation Plan

### Tier 1 (2 days)

**Day 1**:
- [ ] Create `test-resume/` test root (scaffold from template)
- [ ] Create `test-changelog/` test root (scaffold from template)
- [ ] Write resume integration tests (3+ tests)
- [ ] Write changelog integration tests (3+ tests)

**Day 2**:
- [ ] Create `benchmarks/test_10k_site.py`
- [ ] Implement `generate_large_site()` helper
- [ ] Write discovery benchmark test
- [ ] Write memory usage test
- [ ] Document baseline performance

### Tier 2 (1 day)

**Day 3**:
- [ ] Populate `test-i18n-content/` with content directories
- [ ] Add `i18n/en.yaml` and `i18n/fr.yaml` to test root
- [ ] Write i18n integration tests for existing functions
- [ ] Create language switcher partial
- [ ] Add language switcher CSS
- [ ] Test language switcher rendering

### Tier 3 (3 days)

**Day 4**:
- [ ] Implement `GalleryDirective` in `bengal/directives/gallery.py`
- [ ] Register gallery directive
- [ ] Add gallery CSS to default theme
- [ ] Create `test-gallery/` test root
- [ ] Write gallery tests

**Day 5**:
- [ ] Create product template package structure
- [ ] Implement product template.py
- [ ] Create product data schema and sample products
- [ ] Implement JSON-LD partial

**Day 6**:
- [ ] Create `test-product/` test root
- [ ] Write product template tests
- [ ] Add product CSS to theme
- [ ] Update documentation
- [ ] Final review

**Total**: 6 days

---

## Risks & Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| 10k benchmark too slow for CI | High | Low | Mark `@pytest.mark.slow`, run nightly only |
| Gallery lightbox JS complexity | Medium | Medium | Use existing library (GLightbox) |
| Product template too opinionated | Low | Medium | Make `structured_data` opt-in |
| Test root maintenance burden | Medium | Low | Generate from templates where possible |

---

## Success Criteria

1. ✅ Resume template has ≥3 passing integration tests
2. ✅ Changelog template has ≥3 passing integration tests
3. ✅ 10k page site discovery completes in <30s
4. ✅ 10k page site uses <2GB peak memory
5. ✅ Existing i18n functions have integration tests
6. ✅ Language switcher renders in multi-language sites
7. ✅ Gallery directive renders responsive grid
8. ✅ Product template generates valid JSON-LD
9. ✅ All new code has tests
10. ✅ Overall scenario coverage confidence ≥95%

---

## Open Questions

- [x] ~~Should `t()` support pluralization?~~ → Already implemented with fallback, pluralization is v2
- [x] ~~Do i18n functions exist?~~ → **Yes**, fully implemented in `i18n.py`
- [ ] Should gallery support video? (Recommendation: Images only in v1)
- [ ] Should product template include cart integration examples? (Recommendation: Document Snipcart/Stripe only)
- [ ] What's acceptable performance degradation for i18n? (<5% build time)

---

## References

- **Phase 1 RFC**: `plan/ready/rfc-user-scenario-coverage.md`
- **i18n Implementation**: `bengal/rendering/template_functions/i18n.py:94-135`
- **i18n Content Discovery**: `bengal/discovery/content_discovery.py:153-173`
- **Existing Test Roots**: `tests/roots/test-blog-paginated/`, `tests/roots/test-i18n-content/`
- **Directives**: `bengal/directives/`
- **Templates**: `bengal/cli/templates/`
- **Benchmarks**: `benchmarks/`
- **Resume Data Schema**: `bengal/cli/templates/resume/data/resume.yaml`
- **Changelog Data Schema**: `bengal/cli/templates/changelog/data/changelog.yaml`
