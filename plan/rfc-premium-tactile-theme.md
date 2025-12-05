# RFC: Premium Tactile Theme Polish

**Status**: Draft  
**Created**: 2025-12-05  
**Author**: Design System Team  
**Related**: Competitor analysis (Supabase docs)  
**References**: [Apple HIG: Color](https://developer.apple.com/design/human-interface-guidelines/color), [Apple HIG: Layout](https://developer.apple.com/design/human-interface-guidelines/layout)

---

## Executive Summary

Bengal already has a **premium, distinctive theme system**—far beyond generic Tailwind/React sites. This RFC documents what Bengal has achieved and identifies remaining polish opportunities.

**Bengal's unique identity**: The breed-inspired palettes (Snow Lynx, Brown Bengal, Silver Bengal, Blue Bengal, Charcoal Bengal) combined with neumorphic tactile interactions create a distinctive, recognizable brand.

---

## 1. Current State: What Bengal Already Has ✅

### 1.1 Breed Color Palettes (Distinctive!)

Bengal has **5 carefully crafted palettes**, each inspired by Bengal cat coat variations:

| Palette | Character | Light Accent | Dark Mode |
|---------|-----------|--------------|-----------|
| **Snow Lynx** | Ice blue eyes, cream backgrounds | `#4FA8A0` teal | Cool ash-gray |
| **Brown Bengal** | Classic warm amber/gold | `#D4850F` amber | Warm espresso |
| **Silver Bengal** | Pure monochrome, high contrast | `#6B7280` gray | True black |
| **Blue Bengal** | Soft powder blues | `#7FA3C3` powder | Gentle blue wash |
| **Charcoal Bengal** | Editorial moody grays | `#3E4C5A` slate | Deep editorial black |

**Verdict**: These are distinctive and NOT generic. This is Bengal's identity. ✅

### 1.2 Neumorphic Tactile System

Already implemented throughout:
- **Buttons**: `--neumorphic-base`, `--neumorphic-hover`, `--neumorphic-pressed`
- **Theme dropdown**: Full neumorphic shadow progression
- **TOC count badges**: Subtle neumorphic shadows with dark mode variants
- **Outline buttons**: Skeuomorphic pressed state (`inset` shadows)
- **Code copy button**: Frosted glass with neumorphic shadows

**Verdict**: Bengal already feels tactile. ✅

### 1.3 Frosted Glass Effects (Vibrancy)

- **Header**: `backdrop-filter: blur(12px) saturate(180%)` with fallback
- **Code header**: `backdrop-filter: blur(4px)` on language labels
- **Dark mode variants**: Adjusted opacity for both

**Apple HIG alignment**: Apple calls this "vibrancy"—translucent materials that allow background content to inform foreground appearance. Bengal's implementation aligns with Apple's material system.

| Apple Material | Bengal Equivalent | Use Case |
|----------------|-------------------|----------|
| `.ultraThinMaterial` | `blur(4px)` | Code labels, subtle overlays |
| `.regularMaterial` | `blur(12px)` | Headers, navigation |
| `.thickMaterial` | `blur(20px)` | Modals, popovers (future) |

**Verdict**: Already implemented. ✅

### 1.4 Motion & Transitions

- **Fluid blob animations**: Cards have morphing gradient backgrounds on hover
- **Elevation on hover**: Cards lift with `translate3d` and shadow increase
- **Reduced motion support**: `@media (prefers-reduced-motion)` throughout
- **Standardized tokens**: `--transition-fast`, `--transition-base`, `--transition-smooth`

**Verdict**: Motion system is comprehensive. ✅

### 1.5 Code Blocks

- **Syntax highlighting**: Full token-based colors per palette
- **Copy button**: With "Copied!" tooltip feedback
- **Responsive**: Line numbers hide on mobile
- **Scrollbars**: Custom styled
- **Dark mode**: Adjusted syntax colors per palette

**Verdict**: Code blocks are solid. Minor polish possible. 🟡

### 1.6 Layout System

- **Three-column docs layout**: Sidebar, content, TOC
- **Responsive breakpoints**: Tablet hides TOC, mobile collapses sidebar
- **CUBE CSS methodology**: Composition, utilities, blocks, exceptions
- **Container queries**: Modern responsive approach

**Verdict**: Layout is well-architected. ✅

### 1.7 Cards & Components

- **Motion gradient blobs**: `color-mix()` with fallbacks
- **Gradient borders**: Utility class support
- **Feature cards**: Icon + content with hover states
- **Article cards**: Blog-style with image + meta

**Verdict**: Card system is comprehensive. ✅

---

## 2. Gap Analysis: What Needs Polish

### 2.1 Typography (Priority: High)

**Current State**: System font stack for display; display font config exists but defaults to sans.

**Opportunity**: The typography system has `--font-family-display` ready for a distinctive serif, but it falls back to system sans.

```css
/* Current - defaults to system */
--font-family-display: var(--font-display, var(--font-family-sans));
```

**Recommendation**:
- Ship with a recommended display font (Instrument Serif, Newsreader, or Fraunces)
- Document the `[fonts]` config in `bengal.toml`
- Consider adding the font to default theme assets

**Why it matters**: Display typography is the #1 differentiator from generic sites.

---

### 2.2 Search / Command Palette (Priority: Medium)

**Current State**: Unknown (need to check if search exists)

**Premium Pattern** (Supabase): Command palette button with `⌘K` keyboard hint

```html
<button class="search-trigger">
  <span>Search...</span>
  <kbd>⌘K</kbd>
</button>
```

**Recommendation**: If search exists, add keyboard shortcut styling. If not, consider DocSearch integration.

---

### 2.3 Heading Anchor Links (Priority: Low)

**Current State**: Unknown (need to check implementation)

**Premium Pattern**: Hover-reveal `#` links next to headings

```css
.heading-anchor {
  opacity: 0;
  transition: opacity 150ms;
}

h2:hover .heading-anchor,
h3:hover .heading-anchor {
  opacity: 0.5;
}
```

**Recommendation**: Add subtle hover-reveal anchor links if not present.

---

### 2.4 Focus States (Priority: Medium)

**Current State**: Present but could be more visible

**Premium Pattern**: Strong, consistent focus rings

```css
:focus-visible {
  outline: 2px solid var(--color-primary);
  outline-offset: 2px;
}
```

**Apple HIG Contrast Requirements** (WCAG AA + Apple HIG alignment):
| Element | Minimum Contrast | Rationale |
|---------|------------------|-----------|
| Body text | 4.5:1 | WCAG AA standard |
| Large text (18px+) | 3:1 | Reduced threshold for large type |
| UI components | 3:1 | Focus rings, borders, icons |
| Non-text contrast | 3:1 | Buttons, form controls |

**Recommendations**:
- [ ] Audit focus states across all interactive elements
- [ ] Verify all 5 breed palettes meet contrast minimums
- [ ] Test focus visibility in both light and dark modes
- [ ] Ensure focus ring color adapts per palette (not hard-coded blue)

---

### 2.5 Default Palette Identity (Priority: Medium)

**Current State**: Default palette uses standard blue

**Issue**: The default (no palette selected) should feel distinctly "Bengal"

**Recommendation**: Consider making Brown Bengal the default, or create a unique "Classic Bengal" default that uses amber/gold as the primary color.

---

## 3. Layout & Interaction Polish (Priority: High)

### 3.1 Dropdown Hover Gap (The Flicker Bug)

**Current State**: Hacky negative margin workaround in `header.css`:

```css
.nav-main .submenu {
  padding-top: calc(var(--space-1) + var(--space-2));
  margin-top: calc(-1 * var(--space-1));  /* HACK: bridge the gap */
}
```

**Problem**: When user moves mouse from nav item to dropdown, there's a gap where hover is lost, causing dropdown to flicker away.

**Supabase Solution**: They use a transparent "bridge" element or larger padding zone:

```css
/* Better approach: invisible hover bridge */
.nav-item::after {
  content: '';
  position: absolute;
  top: 100%;
  left: 0;
  right: 0;
  height: 12px;  /* Bridge zone */
  background: transparent;
}

.submenu {
  top: calc(100% + 8px);  /* Visual gap without hover gap */
  /* No negative margin hack needed */
}
```

**Alternative**: Use `pointer-events` on a pseudo-element or increase the hover zone properly.

---

### 3.2 Full-Width "App-Like" Layout Option

**Current State**: Traditional centered containers with max-width:
```css
.container {
  max-width: var(--container-xl);  /* 1280px */
  margin-inline: auto;
  padding-inline: var(--space-5);
}
```

**Modern Trend**: App-like sites use full viewport width with content padding:

| Site | Approach |
|------|----------|
| Supabase | Full-width header, full-width sidebar layout |
| Linear | Full-width, content-only has max-width |
| Vercel | Full-width app shell, docs constrained |
| Stripe | Traditional centered (but very wide) |
| Apple | Edge-to-edge with safe area insets |

#### Safe Area Principles (Apple HIG-informed)

Apple's safe area concept translates directly to web layouts:

| Apple Concept | Web Implementation | Bengal Token |
|---------------|-------------------|--------------|
| Safe area insets | Edge padding for content | `--safe-area-inline` |
| Readable content width | Prose max-width (~80 chars) | `--prose-max-width` |
| Minimum margins | Responsive spacing | `--content-margin-inline` |

```css
/* Safe area tokens (Apple HIG-informed) */
:root {
  --safe-area-inline: var(--space-6);       /* 24px - minimum edge padding */
  --safe-area-block: var(--space-4);        /* 16px - vertical safe zone */
  --prose-max-width: 65ch;                  /* ~80 chars optimal reading */

  /* Responsive margins */
  --content-margin-inline: var(--space-4);  /* Mobile: 16px */
}

@media (min-width: 768px) {
  :root {
    --content-margin-inline: var(--space-6); /* Tablet+: 24px */
  }
}

@media (min-width: 1024px) {
  :root {
    --content-margin-inline: var(--space-8); /* Desktop: 32px */
  }
}
```

**Recommendation**: Offer two layout modes:

```css
/* Mode 1: Classic (current) - centered max-width */
:root[data-layout="classic"] .container {
  max-width: var(--container-xl);
  margin-inline: auto;
}

/* Mode 2: App-like - full width with edge-to-edge */
:root[data-layout="app"] {
  /* Header spans full width */
  header[role="banner"] {
    max-width: 100%;
    padding-inline: var(--space-6);
  }

  /* Sidebar touches edge */
  .docs-sidebar {
    padding-inline-start: var(--space-6);
  }

  /* Only content has max-width */
  .docs-main .prose {
    max-width: var(--prose-max-width);
  }

  /* TOC touches right edge */
  .docs-toc {
    padding-inline-end: var(--space-6);
  }
}
```

**Config option** in `bengal.toml`:
```toml
[theme]
layout = "app"  # or "classic"
```

---

### 3.3 Dropdown Polish

**Current Issues**:
- Basic fade-in, not snappy
- No visual hierarchy/grouping in menus
- Missing icons (Supabase has icons for each item)

**Supabase Dropdown Polish**:
- Dark background (consistent in both modes)
- Icons next to menu items
- Subtle rounded corners
- Snappy animation (150ms)

**Recommendations**:

```css
/* Snappier dropdown animation */
.nav-main .submenu {
  /* Current: all var(--transition-fast) var(--ease-out) */
  /* Better: separate properties for snappier feel */
  opacity: 0;
  transform: translateY(-4px);  /* Reduced from -8px */
  transition:
    opacity 100ms ease-out,      /* Faster fade */
    transform 150ms ease-out,    /* Slightly slower position */
    visibility 0ms 100ms;        /* Delay hide */
}

.nav-main li:hover > .submenu {
  transition:
    opacity 100ms ease-out,
    transform 150ms ease-out,
    visibility 0ms;  /* Instant show */
}
```

---

### 3.4 Icon Support in Navigation

**Current State**: Text-only navigation items

**Supabase Pattern**: Icons before each menu item:
```
📖 Glossary
📋 Changelog  
✓  Status
♥  Contributing
```

**Recommendation**: Support icon frontmatter in menu items:
```yaml
# Menu item with icon
menu:
  - text: "Glossary"
    url: "/glossary/"
    icon: "book"  # Mapped to SVG or emoji
```

---

### 3.5 Touch Target Requirements (Apple HIG)

**Apple's minimum**: 44×44 points for all interactive elements.

**Why it matters**: Mobile users need adequately sized tap targets. Even desktop users benefit from generous click zones.

```css
/* Touch target minimum */
.interactive-element {
  min-height: 44px;
  min-width: 44px;
  /* Or use padding to achieve equivalent */
}

/* Adjacent targets need spacing */
.nav-item + .nav-item {
  margin-block-start: var(--space-1);  /* Prevent mis-taps */
}
```

**Audit checklist**:
- [ ] All buttons ≥ 44×44px (including icon-only buttons)
- [ ] Dropdown menu items have adequate touch zones
- [ ] Mobile nav hamburger/close ≥ 44×44px
- [ ] Sidebar links have adequate vertical padding
- [ ] Theme switcher dropdown items ≥ 44px tall
- [ ] TOC links have adequate touch zones on tablet
- [ ] Code copy button ≥ 44×44px
- [ ] Prev/next navigation links ≥ 44px height

---

### 3.6 Transition Timing Audit

**Issue**: Inconsistent transition speeds across components

**Current tokens**:
```css
--transition-fast: 150ms;
--transition-base: 200ms;
--transition-smooth: 300ms;
```

**Audit needed**:
- [ ] All hover states use consistent timing
- [ ] Dropdowns feel "snappy" not "floaty"
- [ ] Page transitions feel instant
- [ ] Scroll animations respect reduced motion

**Snappiness targets**:
| Interaction | Target | Feel |
|-------------|--------|------|
| Button hover | 100ms | Instant |
| Dropdown open | 150ms | Snappy |
| Dropdown close | 100ms | Quick dismiss |
| Page transition | 200ms | Smooth |
| Sidebar expand | 200ms | Responsive |

---

### 3.7 Edge-to-Edge Header

**Current**: Header content is constrained to `.container`

**App-like pattern**: Header spans full width, with branding at left edge and controls at right edge.

**Apple HIG alignment**: Apple's navigation bars extend edge-to-edge while respecting safe areas for content. The header chrome (background, blur) extends fully, but interactive elements stay within safe zones.

```css
/* Full-width header with safe area alignment */
header[role="banner"] {
  /* Background/blur extends full width */
  width: 100%;
}

header .header-inner {
  display: flex;
  justify-content: space-between;
  /* Safe area padding keeps interactive elements accessible */
  padding-inline: var(--safe-area-inline);
  max-width: none;  /* Full width */
}

/* Logo at left safe edge */
.logo {
  margin-inline-start: 0;
}

/* Controls at right safe edge */
.header-actions {
  margin-inline-end: 0;
  gap: var(--space-2);  /* Adequate spacing between controls */
}

/* Each control meets touch target minimum */
.header-actions > * {
  min-height: 44px;
  min-width: 44px;
  display: flex;
  align-items: center;
  justify-content: center;
}
```

---

## 4. Distinctive Style Principles

### What Makes Bengal NOT Generic

1. **Breed palettes** - No other SSG has cat-inspired color themes
2. **Warm vs cold options** - Brown Bengal (warm) vs Silver Bengal (cold) vs editorial (Charcoal)
3. **Neumorphic depth** - Tactile, keyboard-key feel
4. **Motion blobs** - Organic, living hover effects
5. **Editorial palettes** - Magazine-quality color choices (especially Charcoal Bengal)

### What to Avoid (Generic Patterns)

| Generic Pattern | Bengal Alternative |
|-----------------|-------------------|
| `#3B82F6` Tailwind blue | Brown Bengal amber `#D4850F` |
| Inter/system fonts | Instrument Serif for display |
| Pure white `#FFFFFF` | Snow Lynx cream `#FDFCF9` |
| Cold gray `#F3F4F6` | Warm paper tones |
| `rounded-lg` everywhere | Mix of sharp + rounded |
| Black shadows | Warm-tinted neumorphic |

### Quick Test: "Is This Generic?"

1. **Color**: Could this be Tailwind's default? → Change it
2. **Font**: Is display text using system/Inter? → Use serif
3. **Shadow**: Pure black? → Use warm-tinted
4. **Identity**: Would users recognize this as Bengal? → Add signature element

---

## 4. Recommended Polish Tasks

### Phase 1: Typography (Week 1)
- [ ] Configure Instrument Serif as default `--font-family-display`
- [ ] Document `[fonts]` config in user docs
- [ ] Test with all 5 breed palettes
- [ ] Ensure font loading doesn't cause layout shift

### Phase 2: Interaction Polish (Week 2)
- [ ] Audit and standardize focus states (see Section 2.4 contrast requirements)
- [ ] Verify all 5 palettes meet WCAG AA contrast (4.5:1 text, 3:1 UI)
- [ ] Touch target audit: all interactive elements ≥ 44×44px (see Section 3.5)
- [ ] Add heading anchor links (hover reveal)
- [ ] Ensure keyboard navigation is excellent
- [ ] Test with screen readers
- [ ] Verify safe area padding on mobile devices

### Phase 3: Brand Identity (Week 3)
- [ ] Consider Brown Bengal as default palette
- [ ] Add subtle Bengal signature (rosette pattern option?)
- [ ] Document the "Bengal aesthetic" in theme guide
- [ ] Create palette showcase page

### Phase 4: Optional Enhancements
- [ ] Command palette search with `⌘K`
- [ ] Page progress indicator
- [ ] Reading time estimate
- [ ] Table of contents progress sync

---

## 5. What NOT to Change

Bengal's existing systems are excellent. Do NOT:

- ❌ Replace breed palettes with generic colors
- ❌ Remove neumorphic effects
- ❌ Flatten the tactile interactions
- ❌ Add heavy JavaScript animations
- ❌ Converge toward Tailwind defaults
- ❌ Remove motion blob effects

---

## 6. Success Criteria

### Visual Identity
- [ ] Users can identify Bengal theme without seeing logo
- [ ] Each breed palette feels distinct and intentional
- [ ] Display typography adds editorial quality
- [ ] Interactions feel tactile and responsive

### Technical Quality
- [ ] Zero layout shift from font loading
- [ ] All focus states visible and consistent
- [ ] Reduced motion respected throughout
- [ ] Print styles preserve readability

### Accessibility (Apple HIG + WCAG AA)
- [ ] All body text meets 4.5:1 contrast ratio
- [ ] All large text meets 3:1 contrast ratio
- [ ] All UI components (focus rings, borders) meet 3:1 contrast
- [ ] All interactive elements ≥ 44×44px touch target
- [ ] Edge content respects safe area insets (24px minimum)
- [ ] Each of the 5 breed palettes passes contrast audit

### Performance
- [ ] No JS added for visual effects
- [ ] CSS-only animations
- [ ] Font subsetting keeps payload small
- [ ] Works without JavaScript enabled

---

## Appendix A: Bengal's Existing CSS Assets

### Token System
```
bengal/themes/default/assets/css/tokens/
├── foundation.css       # Raw color scales, spacing
├── semantic.css         # Mapped semantic tokens
├── typography.css       # Type scale, weights
└── palettes/
    ├── snow-lynx.css
    ├── brown-bengal.css
    ├── silver-bengal.css
    ├── blue-bengal.css
    └── charcoal-bengal.css
```

### Component System
```
bengal/themes/default/assets/css/components/
├── buttons.css          # Full neumorphic system
├── cards.css            # Motion blobs, variants
├── code.css             # Syntax highlighting
├── navigation.css       # Prev/next links
├── toc.css              # Table of contents
└── ...
```

### Layout System
```
bengal/themes/default/assets/css/
├── layouts/header.css   # Frosted glass header
└── composition/layouts.css  # Docs layout grid
```

---

## Appendix B: Color Identity Per Palette

### Snow Lynx
- **Inspiration**: White/cream Bengal cats with ice-blue eyes
- **Character**: Cool, ethereal, clean
- **Use case**: Technical docs, clinical feel

### Brown Bengal
- **Inspiration**: Classic spotted Bengal with amber/gold markings
- **Character**: Warm, inviting, premium
- **Use case**: Product docs, marketing-adjacent

### Silver Bengal
- **Inspiration**: Rare silver-coated Bengal cats
- **Character**: High contrast, editorial, dramatic
- **Use case**: Minimalist preferences, print-like

### Blue Bengal
- **Inspiration**: Rare blue/gray Bengal coat variation
- **Character**: Soft, approachable, calming
- **Use case**: User-friendly docs, tutorials

### Charcoal Bengal
- **Inspiration**: Melanistic (black) Bengal cats
- **Character**: Moody, sophisticated, editorial
- **Use case**: Developer tools, dark-mode-first

---

## Appendix C: Apple HIG-Informed Design Tokens

### Proposed Token Additions

```css
/* ============================================
   SAFE AREA & LAYOUT TOKENS (Apple HIG-informed)
   ============================================ */

:root {
  /* Safe areas - minimum edge padding for interactive elements */
  --safe-area-inline: var(--space-6);       /* 24px */
  --safe-area-block: var(--space-4);        /* 16px */

  /* Touch targets - Apple minimum 44pt */
  --touch-target-min: 44px;

  /* Readable content width (~80 chars optimal) */
  --prose-max-width: 65ch;

  /* Responsive content margins */
  --content-margin-inline: var(--space-4);  /* Base: 16px */
}

@media (min-width: 768px) {
  :root {
    --content-margin-inline: var(--space-6); /* Tablet: 24px */
  }
}

@media (min-width: 1024px) {
  :root {
    --content-margin-inline: var(--space-8); /* Desktop: 32px */
  }
}

/* ============================================
   VIBRANCY/MATERIAL TOKENS (Apple HIG-informed)
   ============================================ */

:root {
  /* Blur intensities matching Apple's material system */
  --vibrancy-ultra-thin: blur(4px);
  --vibrancy-regular: blur(12px);
  --vibrancy-thick: blur(20px);

  /* Saturation boost for vibrancy */
  --vibrancy-saturation: saturate(180%);
}

/* ============================================
   ACCESSIBILITY CONTRAST TOKENS
   ============================================ */

:root {
  /* Minimum contrast ratios (WCAG AA) */
  --contrast-text-min: 4.5;        /* Body text */
  --contrast-large-text-min: 3;    /* 18px+ or 14px bold */
  --contrast-ui-min: 3;            /* Borders, icons, focus rings */
}
```

### Contrast Audit Matrix

| Palette | Light BG | Dark BG | Primary on Light | Primary on Dark | Status |
|---------|----------|---------|------------------|-----------------|--------|
| Snow Lynx | `#FDFCF9` | `#1A1918` | TBD | TBD | 🔲 Audit |
| Brown Bengal | `#FAF8F5` | `#1C1917` | TBD | TBD | 🔲 Audit |
| Silver Bengal | `#FFFFFF` | `#000000` | TBD | TBD | 🔲 Audit |
| Blue Bengal | `#F8FAFC` | `#0F172A` | TBD | TBD | 🔲 Audit |
| Charcoal Bengal | `#F9FAFB` | `#111827` | TBD | TBD | 🔲 Audit |

---

## Conclusion

Bengal doesn't need a redesign—it needs **recognition and polish**. The breed palettes and neumorphic system are already distinctive. The main polish opportunities are:

1. **Typography**: Add a display serif font
2. **Focus states**: Audit and strengthen (meet WCAG AA contrast)
3. **Touch targets**: Ensure all interactive elements ≥ 44×44px
4. **Safe areas**: Implement Apple HIG-informed edge padding
5. **Brand identity**: Consider making Brown Bengal the default

**Philosophy**: Bengal should feel like using a well-crafted notebook or a premium keyboard—warm, tactile, and distinctly NOT another Tailwind template.

**Design System Alignment**: Where applicable, Bengal aligns with Apple Human Interface Guidelines for accessibility (contrast ratios), touch targets (44px minimum), and material vibrancy (backdrop-filter tiers). This ensures a familiar, quality feel for users accustomed to native experiences.

---

*Tactile: from Latin tactilis "tangible," from tangere "to touch." A premium theme should feel like you can reach out and touch it.*
