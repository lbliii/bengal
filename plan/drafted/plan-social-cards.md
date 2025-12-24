# Plan: Auto-Generated Social Cards

| Field | Value |
|-------|-------|
| **RFC** | `plan/drafted/rfc-social-cards.md` |
| **Author** | AI + Human reviewer |
| **Date** | 2025-12-22 |
| **Status** | Draft |
| **Estimated Effort** | 7-8 days |

---

## Executive Summary

Implementation plan for auto-generated social cards (Open Graph images). Breaks down the RFC into atomic, testable tasks organized by subsystem with pre-drafted commit messages.

**Key Deliverables**:
1. `bengal/postprocess/social_cards.py` - Core generator module
2. Configuration schema in `bengal/config/`
3. Build integration via PostprocessOrchestrator
4. Template injection in `seo.py`
5. Bundled Inter font for card generation
6. Comprehensive test coverage

---

## Phase 1: Core Generator (3-4 days)

### 1.1 Create SocialCardGenerator Class

**File**: `bengal/postprocess/social_cards.py`

**What**: Create the main `SocialCardGenerator` class with Pillow-based image generation.

**Tasks**:
- [ ] Create module with comprehensive docstring
- [ ] Define `SocialCardConfig` dataclass for card configuration
- [ ] Implement `SocialCardGenerator` class following SitemapGenerator pattern
- [ ] Implement `generate_card()` method for single card generation
- [ ] Implement `generate_all()` method for batch generation with parallelism
- [ ] Add text wrapping utility for long titles/descriptions

**Implementation Notes**:
```python
# Key signatures
@dataclass
class SocialCardConfig:
    enabled: bool = True
    template: str = "default"
    background_color: str = "#1a1a2e"
    text_color: str = "#ffffff"
    accent_color: str = "#4f46e5"
    title_font: str = "Inter-Bold"
    body_font: str = "Inter-Regular"
    logo: str | None = None
    show_site_name: bool = True
    output_dir: str = "assets/social"
    format: str = "png"
    quality: int = 90
    cache: bool = True

class SocialCardGenerator:
    def __init__(self, site: Site, config: SocialCardConfig) -> None: ...
    def generate_card(self, page: Page, output_path: Path) -> Path | None: ...
    def generate_all(self, pages: list[Page], output_dir: Path) -> int: ...
```

**Evidence**: `bengal/postprocess/sitemap.py:35-65` (generator pattern)

**Commit**:
```bash
git add -A && git commit -m "postprocess: add SocialCardGenerator with Pillow-based OG image generation"
```

---

### 1.2 Implement Card Templates

**File**: `bengal/postprocess/social_cards.py` (continue)

**What**: Implement the default and minimal card templates with proper text layout.

**Tasks**:
- [ ] Implement `_render_default_template()` - branded layout with logo, title, description
- [ ] Implement `_render_minimal_template()` - centered title only
- [ ] Add text truncation with ellipsis for overflow
- [ ] Add multi-line text wrapping using Pillow's `textbbox()`
- [ ] Support custom background colors (solid and gradient)

**Implementation Notes**:
```python
def _render_default_template(
    self,
    title: str,
    description: str,
    site_name: str,
    logo_path: Path | None,
) -> Image.Image:
    """Render default branded template (1200x630)."""
    img = Image.new('RGB', (1200, 630), self.config.background_color)
    draw = ImageDraw.Draw(img)

    # Logo + site name header
    # Title (large, bold, wrapped)
    # Description (smaller, wrapped)
    # Footer with URL

    return img
```

**Commit**:
```bash
git add -A && git commit -m "postprocess(social_cards): implement default and minimal card templates with text wrapping"
```

---

### 1.3 Add Configuration Schema

**File**: `bengal/config/social_cards.py` (new)

**What**: Define and validate the `[social_cards]` configuration section.

**Tasks**:
- [ ] Create configuration schema with defaults
- [ ] Add validation for color formats (hex colors)
- [ ] Add validation for font names (bundled or system)
- [ ] Add per-page override parsing from frontmatter
- [ ] Integrate with main config loading

**Implementation Notes**:
```python
def parse_social_cards_config(config: dict[str, Any]) -> SocialCardConfig:
    """Parse [social_cards] section from bengal.toml."""
    social_config = config.get("social_cards", {})
    return SocialCardConfig(
        enabled=social_config.get("enabled", True),
        template=social_config.get("template", "default"),
        background_color=social_config.get("background_color", "#1a1a2e"),
        # ... etc
    )
```

**Commit**:
```bash
git add -A && git commit -m "config: add [social_cards] configuration section with validation"
```

---

### 1.4 Bundle Inter Font

**File**: `bengal/fonts/social/` (new directory)

**What**: Bundle Inter font family for consistent card rendering.

**Tasks**:
- [ ] Create `bengal/fonts/social/` directory
- [ ] Add Inter-Regular.ttf and Inter-Bold.ttf (SIL Open Font License)
- [ ] Add LICENSE file for Inter font
- [ ] Create helper function to locate bundled fonts
- [ ] Add fallback to system fonts if bundled not found

**Implementation Notes**:
```python
def get_font_path(font_name: str) -> Path:
    """Get path to bundled or system font."""
    bundled = Path(__file__).parent / "social" / f"{font_name}.ttf"
    if bundled.exists():
        return bundled
    # Fallback to system font discovery
    return _find_system_font(font_name)
```

**Evidence**: `bengal/fonts/__init__.py:1-50` (existing font infrastructure)

**Commit**:
```bash
git add -A && git commit -m "fonts: bundle Inter font family for social card generation (SIL OFL)"
```

---

### 1.5 Add Unit Tests for Generator

**File**: `tests/unit/test_social_cards.py` (new)

**What**: Comprehensive unit tests for social card generation.

**Tasks**:
- [ ] Test card generation with correct dimensions (1200x630)
- [ ] Test text wrapping for long titles
- [ ] Test color parsing and validation
- [ ] Test template selection (default, minimal)
- [ ] Test frontmatter override (`social_card: false`)
- [ ] Test cache behavior

**Test Cases**:
```python
def test_social_card_dimensions(tmp_path):
    """Card generates with correct dimensions."""

def test_social_card_caching(tmp_path):
    """Same content uses cached card."""

def test_frontmatter_override():
    """Manual image in frontmatter takes precedence."""

def test_disable_per_page():
    """social_card: false disables generation."""
```

**Commit**:
```bash
git add -A && git commit -m "tests: add unit tests for SocialCardGenerator"
```

---

## Phase 2: Build Integration (2 days)

### 2.1 Integrate with PostprocessOrchestrator

**File**: `bengal/orchestration/postprocess.py`

**What**: Hook social card generation into the post-processing phase.

**Tasks**:
- [ ] Import SocialCardGenerator
- [ ] Add social cards task to `run()` method
- [ ] Generate cards after content render, before sitemap
- [ ] Add progress reporting for card generation
- [ ] Handle errors gracefully (log and continue)

**Implementation Notes**:
```python
# In PostprocessOrchestrator.run()
social_config = parse_social_cards_config(self.site.config)
if social_config.enabled:
    tasks.append(("social cards", lambda: self._generate_social_cards(social_config)))
```

**Evidence**: `bengal/orchestration/postprocess.py:129-137` (task pattern)

**Commit**:
```bash
git add -A && git commit -m "orchestration(postprocess): integrate social card generation into build pipeline"
```

---

### 2.2 Implement Card Caching

**File**: `bengal/postprocess/social_cards.py` (update)

**What**: Add content-based caching to skip unchanged cards.

**Tasks**:
- [ ] Compute content hash from title + description + config
- [ ] Store hash → output path mapping
- [ ] Skip regeneration if hash matches existing card
- [ ] Integrate with Bengal's cache system (BuildCache)
- [ ] Add cache invalidation on config change

**Implementation Notes**:
```python
def _compute_card_hash(self, page: Page) -> str:
    """Compute hash for cache key."""
    content = f"{page.title}|{page.description or ''}|{self.config.background_color}"
    return hashlib.md5(content.encode()).hexdigest()[:12]

def _should_regenerate(self, page: Page, output_path: Path) -> bool:
    """Check if card needs regeneration."""
    if not output_path.exists():
        return True
    current_hash = self._compute_card_hash(page)
    cached_hash = self._cache.get(str(page.source_path))
    return current_hash != cached_hash
```

**Commit**:
```bash
git add -A && git commit -m "postprocess(social_cards): add content-based caching for incremental builds"
```

---

### 2.3 Update SEO Template Functions

**File**: `bengal/rendering/template_functions/seo.py`

**What**: Auto-inject generated card path into `og:image` meta tag.

**Tasks**:
- [ ] Extend `og_image()` function to check for generated card
- [ ] Respect manual `image:` frontmatter override
- [ ] Build generated card path from page URL
- [ ] Add `get_social_card_path()` helper function

**Implementation Notes**:
```python
def og_image_with_site(image_path: str, page: Any | None = None) -> str:
    """Get og:image URL, preferring manual override then generated card."""
    # Manual override takes precedence
    if image_path:
        return og_image(image_path, base_url)

    # Check for generated social card
    if page and hasattr(page, 'social_card_path') and page.social_card_path:
        return og_image(page.social_card_path, base_url)

    # Fall back to site default
    return og_image(site.config.get('og_image', ''), base_url)
```

**Evidence**: `bengal/rendering/template_functions/seo.py:26-44` (existing pattern)

**Commit**:
```bash
git add -A && git commit -m "rendering(seo): auto-inject generated social card path into og:image"
```

---

### 2.4 Update base.html Template

**File**: `bengal/themes/default/templates/base.html`

**What**: Update OG image meta tag logic to use auto-generated cards.

**Tasks**:
- [ ] Update og:image meta tag to use new function signature
- [ ] Ensure manual override still works
- [ ] Add fallback chain: frontmatter → generated → site default

**Implementation Notes**:
```html
{% if _has_page %}
  {% set og_img = og_image(_page.metadata.get('image', ''), _page) %}
{% else %}
  {% set og_img = og_image(site.config.get('og_image', '')) %}
{% endif %}
{% if og_img %}
<meta property="og:image" content="{{ og_img }}">
{% endif %}
```

**Evidence**: `bengal/themes/default/templates/base.html:63-67` (existing OG logic)

**Commit**:
```bash
git add -A && git commit -m "themes(default): update base.html to use auto-generated social cards"
```

---

### 2.5 Add Integration Tests

**File**: `tests/integration/test_social_cards_build.py` (new)

**What**: Integration tests for full build with social cards.

**Tasks**:
- [ ] Test full build generates cards in correct location
- [ ] Test cards referenced in HTML output
- [ ] Test cache works across incremental builds
- [ ] Test per-page disable works
- [ ] Test configuration changes trigger regeneration

**Test Cases**:
```python
def test_build_generates_cards(test_site):
    """Full build generates social cards."""

def test_cards_referenced_in_html(test_site):
    """Generated HTML includes og:image meta tags."""

def test_incremental_build_caching(test_site):
    """Incremental build skips unchanged cards."""
```

**Commit**:
```bash
git add -A && git commit -m "tests: add integration tests for social card build pipeline"
```

---

## Phase 3: Templates & Polish (2 days)

### 3.1 Add Documentation Template

**File**: `bengal/postprocess/social_cards.py` (update)

**What**: Add documentation-specific template with category badges.

**Tasks**:
- [ ] Implement `_render_documentation_template()`
- [ ] Add content type badge (Tutorial, Reference, How-To, etc.)
- [ ] Add section/category indicator
- [ ] Support dark mode auto-detection (optional)

**Implementation Notes**:
```python
def _render_documentation_template(
    self,
    title: str,
    description: str,
    site_name: str,
    content_type: str | None = None,
    category: str | None = None,
) -> Image.Image:
    """Render documentation template with content type badges."""
    img = Image.new('RGB', (1200, 630), self.config.background_color)
    # ... render with badges
    return img
```

**Commit**:
```bash
git add -A && git commit -m "postprocess(social_cards): add documentation template with content type badges"
```

---

### 3.2 Add CLI Progress Feedback

**File**: `bengal/postprocess/social_cards.py` (update)

**What**: Add progress reporting during card generation.

**Tasks**:
- [ ] Integrate with CLIOutput for consistent formatting
- [ ] Show progress: "Generating social cards... (15/100)"
- [ ] Report cache hits vs regenerations
- [ ] Add card count to build summary

**Implementation Notes**:
```python
from bengal.output import CLIOutput

def generate_all(self, pages: list[Page], output_dir: Path) -> int:
    cli = CLIOutput()
    cli.section("Social Cards")

    generated = 0
    cached = 0
    for page in pages:
        if self._should_regenerate(page, output_path):
            self.generate_card(page, output_path)
            generated += 1
        else:
            cached += 1

    cli.detail(f"Generated: {generated}, Cached: {cached}", icon=cli.icons.tree_end)
    return generated
```

**Evidence**: `bengal/fonts/__init__.py:214-258` (CLI feedback pattern)

**Commit**:
```bash
git add -A && git commit -m "postprocess(social_cards): add CLI progress feedback during generation"
```

---

### 3.3 Add Parallel Generation

**File**: `bengal/postprocess/social_cards.py` (update)

**What**: Add parallel card generation for large sites.

**Tasks**:
- [ ] Use ThreadPoolExecutor for parallel generation
- [ ] Apply parallel threshold (>5 cards)
- [ ] Handle errors per-card without failing entire batch
- [ ] Thread-safe cache updates

**Implementation Notes**:
```python
from concurrent.futures import ThreadPoolExecutor, as_completed

PARALLEL_THRESHOLD = 5

def generate_all(self, pages: list[Page], output_dir: Path) -> int:
    pages_to_generate = [p for p in pages if self._should_regenerate(p, ...)]

    if len(pages_to_generate) < PARALLEL_THRESHOLD:
        # Sequential
        for page in pages_to_generate:
            self.generate_card(page, ...)
    else:
        # Parallel
        with ThreadPoolExecutor() as executor:
            futures = {executor.submit(self.generate_card, p, ...): p for p in pages_to_generate}
            for future in as_completed(futures):
                try:
                    future.result()
                except Exception as e:
                    logger.warning(f"Card generation failed: {e}")
```

**Evidence**: `bengal/orchestration/render.py:200-250` (parallel pattern)

**Commit**:
```bash
git add -A && git commit -m "postprocess(social_cards): add parallel generation with ThreadPoolExecutor"
```

---

### 3.4 Export from postprocess Package

**File**: `bengal/postprocess/__init__.py`

**What**: Export SocialCardGenerator from package.

**Tasks**:
- [ ] Import SocialCardGenerator in `__init__.py`
- [ ] Add to `__all__` list
- [ ] Update module docstring

**Commit**:
```bash
git add -A && git commit -m "postprocess: export SocialCardGenerator in package __init__"
```

---

### 3.5 Add Documentation

**Files**:
- `site/content/reference/social-cards.md` (new)
- `site/content/configuration/social-cards.md` (new)

**What**: User-facing documentation for social cards feature.

**Tasks**:
- [ ] Configuration reference page
- [ ] Customization guide with examples
- [ ] Per-page override documentation
- [ ] Troubleshooting section

**Commit**:
```bash
git add -A && git commit -m "docs: add social cards configuration and customization guide"
```

---

## Open Questions (from RFC)

Decisions needed before implementation:

1. **Default enabled?**
   - Recommendation: Opt-in for v1 (`enabled = true` explicit)
   - Rationale: Avoids surprising users with new asset generation

2. **Font licensing**:
   - Recommendation: Bundle Inter (SIL Open Font License)
   - Rationale: Known-good, excellent legibility, open source

3. **Dark mode cards?**
   - Recommendation: Defer to v2
   - Rationale: Adds complexity; base feature more important

4. **Category badges?**
   - Recommendation: Add "documentation" template with badges
   - Rationale: Useful for docs sites, can be opt-in

---

## Dependencies

### External (already in requirements)
- **Pillow** ≥ 10.0 - Already widely used in ecosystem

### Bundled
- **Inter font** - Add to `bengal/fonts/social/` (~300KB)

---

## Risk Mitigations

| Risk | Mitigation |
|------|------------|
| Font rendering issues on Linux | Bundle fonts + test in CI |
| Large build time increase | Aggressive caching + parallel |
| Pillow not installed | Graceful degradation with warning |
| Memory for large sites | Stream processing, don't hold all |

---

## Testing Strategy

| Test Type | Location | Coverage |
|-----------|----------|----------|
| Unit | `tests/unit/test_social_cards.py` | Generator, templates, config |
| Integration | `tests/integration/test_social_cards_build.py` | Full build pipeline |
| Roots | `tests/roots/test-social-cards/` | Test fixture site |

---

## Success Criteria

- [ ] Cards generate for all pages by default (1200x630 PNG)
- [ ] Manual `image:` frontmatter overrides auto-generation
- [ ] `social_card: false` disables per-page
- [ ] Cache prevents unnecessary regeneration
- [ ] Parallel generation for sites >50 pages
- [ ] CLI shows generation progress
- [ ] Documentation covers all options
- [ ] Tests pass on Linux, macOS, Windows

---

## Task Summary

| Phase | Tasks | Estimated Time |
|-------|-------|----------------|
| Phase 1: Core Generator | 5 tasks | 3-4 days |
| Phase 2: Build Integration | 5 tasks | 2 days |
| Phase 3: Templates & Polish | 5 tasks | 2 days |
| **Total** | **15 tasks** | **7-8 days** |

---

## Pre-Implementation Checklist

- [ ] RFC reviewed and approved
- [ ] Open questions decided
- [ ] Inter font files obtained (SIL OFL)
- [ ] Test site fixtures prepared
- [ ] Dependencies verified (Pillow ≥ 10.0)
