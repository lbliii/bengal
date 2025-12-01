# RFC: Typography Refinements for Bengal Theme

**Status**: Phase 1 Implemented  
**Author**: Typography Review  
**Created**: 2024-12-01  
**Priority**: Medium  
**Subsystems**: `themes/default`, `tokens/typography.css`, `tokens/semantic.css`, `base/typography.css`

---

## Executive Summary

Bengal's typography system is architecturally sound but aesthetically generic. This RFC proposes targeted refinements to letter spacing, font weights, font stack ordering, and optional distinctive typeface additions—all while preserving the excellent token-based foundation.

**Goals**:
1. Improve typographic polish through refined tracking and optical adjustments
2. Add visual identity through optional distinctive heading fonts
3. Optimize code font stack for developer experience
4. Maintain zero-cost system font performance for body text

**Non-Goals**:
- Complete typography system rewrite (not needed)
- Mandatory web font loading (performance-sensitive)
- Breaking changes to existing token names

---

## Problem Statement

### Current State

The Bengal theme uses a comprehensive 3-layer token system with:
- ✅ Major Third (1.25) type scale
- ✅ Fluid `clamp()` sizing
- ✅ Semantic token mapping
- ❌ Generic system font stack (no visual identity)
- ❌ Suboptimal display tracking (too loose at large sizes)
- ❌ Code font stack prioritizes legacy fonts over modern developer fonts

### Impact

1. **Visual Identity**: All Bengal-generated sites look identical to any system-font website
2. **Display Polish**: Large headings (h1, display) appear optically loose
3. **Developer Experience**: Users with JetBrains Mono or Fira Code installed don't get them by default

---

## Proposed Changes

### Phase 1: Tracking & Weight Refinements (Zero-Cost)

No new fonts required. Pure CSS refinements.

#### 1.1 Display Tracking Adjustments

**Current**:
```css
h1 {
  letter-spacing: var(--tracking-tighter);  /* -0.05em */
}
```

**Proposed**: Add display-specific tracking token:

```css
/* tokens/typography.css */
--letter-spacing-display: -0.04em;  /* NEW: tighter for 40px+ */

/* tokens/semantic.css */
--tracking-display: var(--letter-spacing-display);

/* base/typography.css */
h1 {
  letter-spacing: var(--tracking-display);  /* was --tracking-tighter */
}

.text-6xl, .text-display {
  letter-spacing: var(--tracking-display);
}
```

**Rationale**: At 48-70px, even `-0.05em` can appear loose. Display sizes benefit from tighter tracking to improve visual cohesion.

#### 1.2 Heading Tracking Gradient

**Current**: All headings use `--tracking-tight` (-0.025em)

**Proposed**: Size-appropriate tracking per heading level:

```css
/* base/typography.css */
h1 { letter-spacing: var(--tracking-display); }   /* -0.04em */
h2 { letter-spacing: var(--tracking-tighter); }   /* -0.05em */
h3 { letter-spacing: var(--tracking-tight); }     /* -0.025em */
h4 { letter-spacing: var(--tracking-tight); }     /* -0.025em */
h5, h6 { letter-spacing: var(--tracking-normal); } /* 0 */
```

**Rationale**: Larger type needs more negative tracking; smaller headings approaching body size need less adjustment.

#### 1.3 Code Font Stack Reordering

**Current**:
```css
--font-family-mono: 'Consolas', 'Monaco', 'SF Mono', 'JetBrains Mono',
  'Fira Code', 'Cascadia Code', 'Courier New', monospace;
```

**Proposed**:
```css
--font-family-mono: 'JetBrains Mono', 'Fira Code', 'Cascadia Code',
  'SF Mono', 'Consolas', 'Monaco', 'Menlo', 'Courier New', monospace;
```

**Rationale**: 
- JetBrains Mono and Fira Code are purpose-built for code with ligatures
- Developers who install these fonts expect them to be used
- Cascadia Code (Windows Terminal default) is increasingly common
- SF Mono and Consolas remain as solid fallbacks

---

### Phase 2: Optional Heading Typeface (Web Font)

Add an optional distinctive heading font for sites that want visual identity.

#### 2.1 Recommended Heading Fonts

| Font | License | Character | Load Cost |
|------|---------|-----------|-----------|
| **Instrument Serif** | OFL | Refined, modern | ~25KB (2 weights) |
| **Fraunces** | OFL | Soft, optical | ~35KB (variable) |
| **DM Serif Display** | OFL | Classic, bold | ~15KB (1 weight) |
| **Newsreader** | OFL | Editorial | ~30KB (2 weights) |

**Recommendation**: Start with **Instrument Serif**—elegant, modern, distinctive without being quirky.

#### 2.2 Implementation: Optional Display Font Token

```css
/* tokens/typography.css */

/* Display font - override in site config if using web fonts */
--font-family-display: var(--font-family-sans);  /* Default: same as body */

/* When Instrument Serif is loaded: */
/* --font-family-display: 'Instrument Serif', Georgia, serif; */
```

```css
/* tokens/semantic.css */
--font-display: var(--font-family-display);
--font-heading: var(--font-family-display);  /* Can differ from display */
```

```css
/* base/typography.css */
h1, h2 {
  font-family: var(--font-heading);
}

.text-display, .hero-title {
  font-family: var(--font-display);
}
```

#### 2.3 Theme Configuration

Allow sites to opt-in via bengal.toml:

```toml
[theme.typography]
heading_font = "instrument-serif"  # Loads from Google Fonts or local
body_font = "system"               # Keep system fonts for body
code_font = "jetbrains-mono"       # Optional code font loading
```

**Generates**:
```html
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Instrument+Serif:ital@0;1&display=swap" rel="stylesheet">
```

---

### Phase 3: Body Text Refinements (Optional)

For sites wanting full typographic control.

#### 3.1 Alternative Sans Stack: IBM Plex

```css
/* Option: Technical documentation optimized */
--font-family-sans: 'IBM Plex Sans', -apple-system, BlinkMacSystemFont,
  'Segoe UI', 'Roboto', 'Helvetica Neue', sans-serif;

--font-family-mono: 'IBM Plex Mono', 'JetBrains Mono', 'Fira Code',
  'SF Mono', 'Consolas', monospace;
```

**Rationale**: IBM Plex was designed for technical content and documentation. The matching mono creates visual harmony.

#### 3.2 Alternative Sans Stack: Geist

```css
/* Option: Modern developer aesthetic (Vercel-style) */
--font-family-sans: 'Geist', -apple-system, BlinkMacSystemFont,
  'Segoe UI', 'Roboto', 'Helvetica Neue', sans-serif;

--font-family-mono: 'Geist Mono', 'JetBrains Mono', 'Fira Code',
  'SF Mono', 'Consolas', monospace;
```

---

## Implementation Plan

### Phase 1: Tracking & Code Fonts ✅ IMPLEMENTED

| Task | File | Status |
|------|------|--------|
| 1.1 | Add `--letter-spacing-display` token | `tokens/typography.css` | ✅ Done |
| 1.2 | Add `--tracking-display` semantic token | `tokens/semantic.css` | ✅ Done |
| 1.3 | Update h1/h2 letter-spacing | `base/typography.css` | ✅ Done |
| 1.4 | Implement heading tracking gradient | `base/typography.css` | ✅ Done |
| 1.5 | Reorder code font stack | `tokens/typography.css` | ✅ Done |
| 1.6 | Update TYPOGRAPHY_SYSTEM.md | Documentation | ✅ Done |

**Commit**: `d9323809`

### Phase 2: Optional Heading Font (Future)

| Task | File | Effort |
|------|------|--------|
| 2.1 | Add `--font-family-display` token | `tokens/typography.css` | 5 min |
| 2.2 | Add semantic heading font tokens | `tokens/semantic.css` | 10 min |
| 2.3 | Update h1/h2 to use heading font | `base/typography.css` | 10 min |
| 2.4 | Add theme config for font loading | `config/` | 30 min |
| 2.5 | Add font preload injection | `rendering/` | 45 min |
| 2.6 | Document font configuration | `site/content/` | 20 min |

**Total**: ~2 hours

### Phase 3: Alternative Body Stacks (Future)

| Task | File | Effort |
|------|------|--------|
| 3.1 | Create font stack presets | `tokens/` | 30 min |
| 3.2 | Add theme preset selector | `config/` | 30 min |
| 3.3 | Document preset options | `site/content/` | 30 min |

**Total**: ~1.5 hours

---

## Token Reference

### New Tokens (Phase 1)

```css
/* Foundation */
--letter-spacing-display: -0.04em;

/* Semantic */
--tracking-display: var(--letter-spacing-display);
```

### New Tokens (Phase 2)

```css
/* Foundation */
--font-family-display: var(--font-family-sans);

/* Semantic */
--font-display: var(--font-family-display);
--font-heading: var(--font-family-display);
```

---

## Breaking Changes

**None.** All changes are:
- Additive tokens
- Refinements to existing values
- Optional configuration

Existing sites will continue to work unchanged.

---

## Testing Checklist

### Phase 1

- [ ] h1 tracking appears tighter at 48-56px sizes
- [ ] h2 tracking is visibly tighter than h3
- [ ] h5/h6 tracking matches body text
- [ ] Code blocks render JetBrains Mono (if installed)
- [ ] Fallback to system monospace works correctly
- [ ] No layout shifts from tracking changes

### Phase 2

- [ ] Sites without config use system fonts (no change)
- [ ] Sites with `heading_font` config load web font
- [ ] Font preload prevents FOIT
- [ ] Fallback serif renders during font load
- [ ] Dark mode works with custom fonts

---

## Alternatives Considered

### 1. Full Web Font Stack

**Rejected**: Performance cost too high for default theme. Web fonts should be opt-in.

### 2. Variable Font with Optical Sizing

**Deferred**: Would require more complex font loading and browser support considerations. Good future enhancement.

### 3. Different Type Scale Ratio

**Rejected**: Current Major Third (1.25) is appropriate for documentation. No change needed.

---

## Success Metrics

1. **Visual Polish**: Side-by-side comparison shows improved heading cohesion
2. **Developer Experience**: Users with modern code fonts see them by default
3. **Zero Regression**: Existing sites unchanged unless they opt-in
4. **Performance**: No additional load time for Phase 1 changes

---

## Appendix: Font Specimens

### Heading Font Options

```
Instrument Serif
ABCDEFGHIJKLMNOPQRSTUVWXYZ
abcdefghijklmnopqrstuvwxyz
0123456789

Fraunces
ABCDEFGHIJKLMNOPQRSTUVWXYZ
abcdefghijklmnopqrstuvwxyz
0123456789

DM Serif Display
ABCDEFGHIJKLMNOPQRSTUVWXYZ
abcdefghijklmnopqrstuvwxyz
0123456789
```

### Code Font Comparison

| Font | Ligatures | Distinctiveness | Default Platform |
|------|-----------|-----------------|------------------|
| JetBrains Mono | ✅ Yes | `0O` `1lI` excellent | IntelliJ, JetBrains IDEs |
| Fira Code | ✅ Yes | `0O` `1lI` excellent | VS Code popular choice |
| Cascadia Code | ✅ Yes | `0O` `1lI` good | Windows Terminal |
| SF Mono | ❌ No | `0O` `1lI` good | macOS Terminal |
| Consolas | ❌ No | `0O` okay, `1lI` okay | Windows legacy |

---

## References

- [Practical Typography: Letterspacing](https://practicaltypography.com/letterspacing.html)
- [Google Fonts: Instrument Serif](https://fonts.google.com/specimen/Instrument+Serif)
- [Type Scale Calculator](https://typescale.com/)
- [Variable Fonts Guide](https://web.dev/variable-fonts/)

