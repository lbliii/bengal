# RFC: Auto-Generated Social Cards

| Field | Value |
|-------|-------|
| **Title** | Auto-Generated Social Cards |
| **Author** | AI + Human reviewer |
| **Date** | 2025-12-10 |
| **Status** | Draft |
| **Confidence** | 88% 🟢 |

---

## Executive Summary

Add automatic social card (Open Graph image) generation to Bengal. When sharing documentation links on social media, Slack, Discord, or other platforms, users will see beautiful preview cards with the page title, description, and site branding — without manually creating images for every page.

**Strategic Context**: MkDocs users rely on Material for MkDocs' social cards plugin. With MkDocs development stagnating, this feature would make Bengal a compelling migration target.

---

## Problem Statement

### Current State

Bengal supports OG image meta tags via manual specification:

```yaml
# Frontmatter approach
---
image: /assets/images/my-custom-card.png
---
```

```toml
# Site-wide default in bengal.toml
[site]
og_image = "/assets/images/default-social.png"
```

**Evidence**: `bengal/themes/default/templates/base.html:63-67`
```html
{% if _has_page and _page.metadata.get('image') %}
<meta property="og:image" content="{{ og_image(_page.metadata.get('image')) }}">
{% elif site.config.get('og_image') %}
<meta property="og:image" content="{{ og_image(site.config.get('og_image')) }}">
{% endif %}
```

### Pain Points

1. **Manual Image Creation**: Users must create social images for each page manually
2. **Inconsistent Branding**: Without automation, social cards vary in style
3. **Missing Images**: Most pages have no social image, leading to blank previews
4. **Competitive Gap**: Material for MkDocs generates these automatically

### User Impact

| Scenario | Without Auto-Generation | With Auto-Generation |
|----------|------------------------|---------------------|
| Share docs on Twitter | Generic link, no preview | Beautiful branded card |
| Paste in Slack | Plain URL | Title + description + image |
| SEO/discoverability | Lower click-through | Higher engagement |

---

## Goals & Non-Goals

### Goals

1. **Zero-Config Default**: Social cards generate automatically for all pages
2. **Customizable Templates**: Users can customize card design (colors, fonts, layout)
3. **Performance**: Cards generated during build, not on-demand
4. **Caching**: Only regenerate cards when content changes
5. **Override Support**: Manual `image:` in frontmatter takes precedence

### Non-Goals

- **Runtime generation**: We won't generate cards on-demand (build-time only)
- **External services**: No dependency on external APIs (Cloudinary, etc.)
- **Video previews**: Focus on static images only
- **Animated cards**: No GIF/video generation

---

## Architecture Impact

### Affected Subsystems

- **Postprocess** (`bengal/postprocess/`):
  - New `social_cards.py` module for card generation

- **Config** (`bengal/config/`):
  - New `social_cards` configuration section

- **Cache** (`bengal/cache/`):
  - Card generation caching (content hash → image)

- **Assets** (`bengal/assets/`):
  - Generated cards output to `public/assets/social/`

- **Rendering** (`bengal/rendering/`):
  - `template_functions/seo.py`: Auto-inject generated card path

### Integration Points

```
Build Pipeline
      │
      ▼
┌─────────────────┐
│ Content Render  │──► Pages with metadata
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Social Card Gen │──► For each page:
│                 │    1. Check cache
│                 │    2. Generate if needed
│                 │    3. Write to public/assets/social/
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Template Render │──► Inject og:image with generated path
└─────────────────┘
```

---

## Design Options

### Option A: Pillow-Based Generation (Recommended)

**Approach**: Use Pillow (PIL) for image generation with custom templates.

**Pros**:
- Pure Python, no external dependencies
- Full control over design
- Fast (can generate 100+ cards/second)
- Works offline

**Cons**:
- Font rendering can be tricky
- Limited to raster graphics

**Implementation**:
```python
from PIL import Image, ImageDraw, ImageFont

def generate_social_card(
    title: str,
    description: str,
    site_name: str,
    output_path: Path,
    template: SocialCardTemplate,
) -> None:
    """Generate a social card image."""
    img = Image.new('RGB', (1200, 630), template.background_color)
    draw = ImageDraw.Draw(img)

    # Draw title
    title_font = ImageFont.truetype(template.title_font, 48)
    draw.text((60, 200), title, font=title_font, fill=template.text_color)

    # Draw description
    desc_font = ImageFont.truetype(template.body_font, 24)
    draw.text((60, 300), description[:120], font=desc_font, fill=template.secondary_color)

    # Draw site branding
    # ... logo, site name, etc.

    img.save(output_path, 'PNG', optimize=True)
```

### Option B: SVG + Conversion

**Approach**: Generate SVG templates, convert to PNG via CairoSVG.

**Pros**:
- Vector precision
- Easy template editing (just edit SVG)
- Better text rendering

**Cons**:
- Requires CairoSVG (C library dependency)
- More complex setup

### Option C: Headless Browser (Playwright/Puppeteer)

**Approach**: Render HTML templates via headless Chrome.

**Pros**:
- Full HTML/CSS support
- Pixel-perfect rendering
- Easy for web developers to customize

**Cons**:
- Heavy dependency (Chrome)
- Slow (1-2 seconds per card)
- Not suitable for large sites

### Recommendation

**Option A (Pillow)** for v1:
- Zero external dependencies beyond Pillow (already common)
- Fast enough for 1000+ page sites
- Matches Bengal's "batteries included" philosophy

Consider Option B as future enhancement for users who need precise typography.

---

## Proposed Configuration

```toml
# bengal.toml

[social_cards]
enabled = true  # Default: true

# Template selection
template = "default"  # Options: default, minimal, branded

# Colors (CSS color values)
background_color = "#1a1a2e"
text_color = "#ffffff"
accent_color = "#4f46e5"

# Typography
title_font = "Inter-Bold"  # Bundled fonts or system fonts
body_font = "Inter-Regular"

# Branding
logo = "assets/logo.png"  # Optional site logo
show_site_name = true

# Output
output_dir = "assets/social"  # Relative to public/
format = "png"  # png or jpg
quality = 90  # For jpg

# Cache behavior
cache = true  # Cache generated cards
```

### Per-Page Override

```yaml
---
title: Custom Page
description: This page has a custom card
social_card:
  background_color: "#2d3748"
  accent_color: "#48bb78"
---
```

### Disable for Specific Pages

```yaml
---
title: No Card Page
social_card: false
---
```

---

## Card Template Designs

### Default Template (1200x630px)

```
┌────────────────────────────────────────────────────────┐
│                                                        │
│  ┌──────┐                                              │
│  │ LOGO │  Site Name                                   │
│  └──────┘                                              │
│                                                        │
│  ┌────────────────────────────────────────────────┐    │
│  │                                                │    │
│  │  Page Title Goes Here                          │    │
│  │  (Large, Bold)                                 │    │
│  │                                                │    │
│  │  Description text that gives context about    │    │
│  │  what this page contains...                   │    │
│  │                                                │    │
│  └────────────────────────────────────────────────┘    │
│                                                        │
│  ─────────────────────────────────────────────────     │
│  📚 docs.example.com                                   │
│                                                        │
└────────────────────────────────────────────────────────┘
```

### Minimal Template

```
┌────────────────────────────────────────────────────────┐
│                                                        │
│                                                        │
│                                                        │
│        Page Title                                      │
│        (Centered, Large)                               │
│                                                        │
│        ───────────────                                 │
│                                                        │
│        Site Name                                       │
│                                                        │
│                                                        │
└────────────────────────────────────────────────────────┘
```

---

## Implementation Plan

### Phase 1: Core Generator (3-4 days)

1. Create `bengal/postprocess/social_cards.py`:
   - `SocialCardGenerator` class
   - Default template rendering
   - Pillow-based image generation

2. Add configuration schema to `bengal/config/`:
   - `social_cards` section validation
   - Default values

3. Bundle fonts:
   - Inter (open source, excellent for UI)
   - Store in `bengal/fonts/social/`

### Phase 2: Build Integration (2 days)

1. Hook into post-processing phase:
   - Generate cards after content render
   - Before sitemap/RSS generation

2. Implement caching:
   - Hash: title + description + config
   - Skip regeneration if hash matches

3. Update `base.html`:
   - Auto-inject generated card path
   - Respect manual `image:` override

### Phase 3: Templates & Polish (2 days)

1. Create template variants:
   - Default (branded)
   - Minimal (clean)
   - Documentation (with category badges)

2. Add CLI feedback:
   - Progress during generation
   - Card count in build summary

3. Documentation:
   - Configuration reference
   - Customization guide

---

## Testing Strategy

### Unit Tests

```python
def test_social_card_generation():
    """Card generates with correct dimensions."""
    generator = SocialCardGenerator(config)
    path = generator.generate(
        title="Test Page",
        description="Test description",
        output_path=tmp_path / "card.png"
    )

    img = Image.open(path)
    assert img.size == (1200, 630)

def test_card_caching():
    """Same content uses cached card."""
    generator = SocialCardGenerator(config, cache_dir=tmp_path)

    path1 = generator.generate(title="Test", description="Desc")
    path2 = generator.generate(title="Test", description="Desc")

    assert path1 == path2  # Same cached file

def test_frontmatter_override():
    """Manual image in frontmatter takes precedence."""
    page = Page(metadata={"image": "/custom.png"})
    card_path = get_og_image(page, site)

    assert card_path == "/custom.png"
```

### Integration Tests

```python
def test_build_generates_cards(test_site):
    """Full build generates social cards."""
    result = build_site(test_site)

    card_dir = test_site / "public/assets/social"
    assert card_dir.exists()
    assert len(list(card_dir.glob("*.png"))) > 0

def test_cards_referenced_in_html(test_site):
    """Generated HTML includes og:image meta tags."""
    build_site(test_site)

    html = (test_site / "public/docs/index.html").read_text()
    assert 'og:image' in html
    assert '/assets/social/' in html
```

---

## Migration Path

### For Existing Sites

**No breaking changes**. Social cards are opt-in by default for v1:

```toml
# Explicit opt-in for v1
[social_cards]
enabled = true
```

Future versions may enable by default.

### For Sites with Manual Images

Existing `image:` frontmatter continues to work and takes precedence:

```yaml
---
image: /my-custom-image.png  # This still works, overrides auto-generation
---
```

---

## Performance Considerations

### Benchmarks (Estimated)

| Site Size | Cards | Generation Time | With Cache |
|-----------|-------|-----------------|------------|
| 50 pages | 50 | ~2s | ~0.1s |
| 500 pages | 500 | ~15s | ~0.5s |
| 2000 pages | 2000 | ~60s | ~2s |

### Optimizations

1. **Parallel generation**: Use ThreadPoolExecutor
2. **Font caching**: Load fonts once, reuse
3. **Content hashing**: Skip unchanged pages
4. **Incremental builds**: Integrate with Bengal's cache system

---

## Dependencies

### Required

- **Pillow** >= 10.0: Image generation (already widely used)

### Optional (Future)

- **CairoSVG**: For SVG-based templates
- **fonttools**: For advanced font subsetting

### Bundled

- **Inter font family**: Open source, excellent legibility
  - License: SIL Open Font License
  - Size: ~300KB for Regular + Bold

---

## Risks & Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Font rendering issues on Linux | Medium | Medium | Bundle fonts, test CI environments |
| Large build time increase | Low | Medium | Aggressive caching, parallel generation |
| Pillow not installed | Low | Low | Graceful degradation, clear error message |
| Memory usage for large sites | Low | Medium | Stream processing, don't hold all in memory |

---

## Success Metrics

1. **Adoption**: 50%+ of new Bengal sites enable social cards
2. **Performance**: < 30 seconds for 1000-page site (with cache: < 2s)
3. **Quality**: Cards render correctly on Twitter, LinkedIn, Slack, Discord
4. **Migration**: Feature cited as reason for MkDocs → Bengal migration

---

## Open Questions

1. **Default enabled?** Should social cards be enabled by default in v1, or opt-in?
2. **Font licensing**: Should we bundle fonts or use system fonts by default?
3. **Dark mode cards?** Should cards auto-detect page/site dark mode?
4. **Category badges?** Show content type (Tutorial, Reference, etc.) on cards?

---

## References

- Material for MkDocs Social Cards: https://squidfunk.github.io/mkdocs-material/setup/setting-up-social-cards/
- Open Graph Protocol: https://ogp.me/
- Twitter Card Validator: https://cards-dev.twitter.com/validator
- Pillow Documentation: https://pillow.readthedocs.io/
- Inter Font: https://rsms.me/inter/

---

## Appendix: Competitive Analysis

| Feature | Bengal (Proposed) | Material for MkDocs |
|---------|-------------------|---------------------|
| Auto-generation | ✅ | ✅ |
| Custom templates | ✅ | ✅ (limited) |
| Per-page override | ✅ | ✅ |
| Caching | ✅ | ✅ |
| Custom fonts | ✅ | ✅ (Insiders only) |
| Custom colors | ✅ | ✅ |
| Logo support | ✅ | ✅ |
| Pure Python | ✅ | ❌ (requires Cairo) |
| Offline | ✅ | ✅ |

Bengal advantage: Pure Python implementation, no Cairo dependency.
