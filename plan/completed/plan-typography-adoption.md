# Plan: Typography System Adoption

**Status**: Active  
**Created**: 2025-12-05  
**Parent RFC**: `rfc-premium-tactile-theme.md`  
**Source Analysis**: Supabase docs CSS extraction

---

## Executive Summary

Bengal's typography foundation is **already excellent**—fluid sizing, proper scales, semantic tokens, letter-spacing gradients. The gaps are:

1. **No display font shipped** (falls back to system sans)
2. **Heading weights could be heavier** (Supabase uses 800→700→600)
3. **Body line-height slightly tight** (1.65 vs 1.75)
4. **Prose elements need alignment** (figcaption, tables)

---

## Gap Analysis: Bengal vs Supabase

| Property | Bengal Current | Supabase | Action |
|----------|---------------|----------|--------|
| **Display font** | System fallback | Circular (custom) | Ship Instrument Serif |
| **H1 weight** | 700 | 800 | Bump to 800 |
| **H2 weight** | 600 | 700 | Bump to 700 |
| **H3 weight** | 500 | 600 | Bump to 600 |
| **H4 weight** | 500 | 600 | Bump to 600 |
| **Body line-height** | 1.65 | 1.75 | Bump to 1.7 |
| **Figcaption** | `--text-caption` | 0.875em, mono font | Use mono font |
| **Table font** | `--text-body-sm` | 0.875em | ✅ Same |
| **Letter-spacing** | Full scale | Full scale | ✅ Already done |

---

## Tasks

### Phase 1: Font Configuration (Low Risk)

#### 1.1 Ship Default Display Font
**File**: `bengal/themes/default/assets/css/tokens/typography.css`

```css
/* Before */
--font-family-display: var(--font-display, var(--font-family-sans));

/* After - add serif fallback before sans */
--font-family-display: var(--font-display, 'Instrument Serif', Georgia, serif);
```

**Also needed**:
- [ ] Add `@font-face` for Instrument Serif in theme assets
- [ ] Configure WOFF2 subset (Latin only, ~25KB)
- [ ] Document `[fonts]` override in bengal.toml example

#### 1.2 Update Font Loading Strategy
**File**: `bengal/themes/default/assets/css/base/typography.css`

Add font-display: swap to prevent FOIT:

```css
@font-face {
  font-family: 'Instrument Serif';
  src: url('../fonts/InstrumentSerif-Regular.woff2') format('woff2');
  font-weight: 400;
  font-style: normal;
  font-display: swap;
}
```

---

### Phase 2: Weight Adjustments (Medium Risk)

#### 2.1 Bump Heading Weights
**File**: `bengal/themes/default/assets/css/base/typography.css`

```css
/* Before */
h1 { font-weight: var(--weight-bold); }      /* 700 */
h2 { font-weight: var(--weight-semibold); }  /* 600 */
h3 { font-weight: var(--weight-medium); }    /* 500 */
h4 { font-weight: var(--weight-medium); }    /* 500 */

/* After - heavier gradient like Supabase */
h1 { font-weight: var(--weight-extrabold); } /* 800 */
h2 { font-weight: var(--weight-bold); }      /* 700 */
h3 { font-weight: var(--weight-semibold); }  /* 600 */
h4 { font-weight: var(--weight-semibold); }  /* 600 */
```

**Testing**:
- [ ] Test with all 5 breed palettes
- [ ] Test with and without display font
- [ ] Verify h1 in hero sections doesn't feel too heavy

---

### Phase 3: Line Height Adjustment (Low Risk)

#### 3.1 Bump Body Line-Height
**File**: `bengal/themes/default/assets/css/tokens/typography.css`

```css
/* Before */
--line-height-relaxed: 1.65;

/* After - closer to Supabase's 1.75 */
--line-height-relaxed: 1.7;
```

**Rationale**: 1.75 is more readable for long-form docs, 1.7 is a good middle ground.

---

### Phase 4: Prose Element Alignment (Low Risk)

#### 4.1 Figcaption Styling
**File**: `bengal/themes/default/assets/css/base/typography.css`

```css
/* Current */
figcaption {
  margin-top: var(--space-2);
  font-size: var(--text-caption);
  text-align: center;
  color: var(--color-text-muted);
}

/* Updated - add monospace font like Supabase */
figcaption {
  margin-top: var(--space-2);
  font-size: var(--text-caption);
  font-family: var(--font-family-mono);
  text-align: center;
  color: var(--color-text-muted);
  line-height: var(--leading-snug);
  letter-spacing: var(--tracking-wide);
}
```

#### 4.2 Code Block Line-Height
**File**: `bengal/themes/default/assets/css/base/typography.css`

```css
/* Current */
pre { line-height: 1.5; }

/* Updated - match Supabase's 1.714 */
pre { line-height: 1.7; }
```

---

## Implementation Order

```
Phase 1 (Day 1): Font Configuration
├── 1.1 Download Instrument Serif WOFF2
├── 1.2 Add @font-face rule
├── 1.3 Update --font-family-display fallback
└── 1.4 Test font loading (no FOIT)

Phase 2 (Day 1-2): Weight Adjustments  
├── 2.1 Update heading weights
├── 2.2 Test all palettes
└── 2.3 Test light/dark modes

Phase 3 (Day 2): Line Height
├── 3.1 Bump --line-height-relaxed
└── 3.2 Visual regression test

Phase 4 (Day 2): Prose Elements
├── 4.1 Update figcaption
├── 4.2 Update pre line-height
└── 4.3 Final review
```

---

## Files to Modify

| File | Changes |
|------|---------|
| `tokens/typography.css` | Line-height, display font fallback |
| `base/typography.css` | Heading weights, figcaption, pre |
| `themes/default/assets/fonts/` | Add Instrument Serif WOFF2 |
| `bengal.toml.example` | Document `[fonts]` config |

---

## Rollback Plan

All changes are CSS-only. Rollback by reverting the specific CSS files.

No database, no migrations, no breaking API changes.

---

## Testing Checklist

- [ ] **Font loading**: No FOIT, swap works correctly
- [ ] **Heading hierarchy**: Visual weight gradient clear
- [ ] **Readability**: Body text comfortable to read
- [ ] **Code blocks**: Proper spacing, scrollable
- [ ] **Figcaptions**: Monospace looks intentional
- [ ] **All palettes**: Test Snow Lynx, Brown, Silver, Blue, Charcoal
- [ ] **Dark mode**: All typography visible
- [ ] **Mobile**: Responsive sizing works
- [ ] **Print**: Print stylesheet still works

---

## Success Criteria

- [ ] Display font (Instrument Serif) loads and renders for h1/h2
- [ ] Heading weight gradient matches premium docs sites
- [ ] Body text line-height improved readability
- [ ] Figcaptions use mono font (editorial touch)
- [ ] No layout shift from font loading
- [ ] All tests pass

---

## Commit Plan

```bash
# Phase 1
git add -A && git commit -m "theme(fonts): add Instrument Serif as default display font; configure font-display: swap"

# Phase 2
git add -A && git commit -m "theme(typography): increase heading weights for stronger hierarchy (h1=800, h2=700, h3/h4=600)"

# Phase 3
git add -A && git commit -m "theme(typography): bump body line-height to 1.7 for improved readability"

# Phase 4
git add -A && git commit -m "theme(typography): align prose elements with premium patterns (figcaption mono, pre line-height)"
```

---

## References

- **Source**: `.compeitor/supabase.css` (extracted 2025-12-05)
- **Parent RFC**: `plan/rfc-premium-tactile-theme.md`
- **Bengal typography tokens**: `bengal/themes/default/assets/css/tokens/typography.css`
- **Bengal typography styles**: `bengal/themes/default/assets/css/base/typography.css`
