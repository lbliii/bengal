# RFC: Premium Tactile Theme Polish

**Status**: Draft  
**Created**: 2025-12-05  
**Author**: Design System Team  
**Related**: Competitor analysis (Supabase docs)

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

### 1.3 Frosted Glass Effects

- **Header**: `backdrop-filter: blur(12px) saturate(180%)` with fallback
- **Code header**: `backdrop-filter: blur(4px)` on language labels
- **Dark mode variants**: Adjusted opacity for both

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

**Recommendation**: Audit focus states across all interactive elements.

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

### 3.5 Transition Timing Audit

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

### 3.6 Edge-to-Edge Header

**Current**: Header content is constrained to `.container`

**App-like pattern**: Header spans full width, with branding at left edge and controls at right edge:

```css
/* Full-width header with edge alignment */
header[role="banner"] {
  /* Remove container constraint */
}

header .header-inner {
  display: flex;
  justify-content: space-between;
  padding-inline: var(--space-6);
  max-width: none;  /* Full width */
}

/* Logo touches left edge (minus safe padding) */
.logo {
  margin-inline-start: 0;
}

/* Controls touch right edge */
.header-actions {
  margin-inline-end: 0;
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
- [ ] Audit and standardize focus states
- [ ] Add heading anchor links (hover reveal)
- [ ] Ensure keyboard navigation is excellent
- [ ] Test with screen readers

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

## Conclusion

Bengal doesn't need a redesign—it needs **recognition and polish**. The breed palettes and neumorphic system are already distinctive. The main polish opportunities are:

1. **Typography**: Add a display serif font
2. **Focus states**: Audit and strengthen
3. **Brand identity**: Consider making Brown Bengal the default

**Philosophy**: Bengal should feel like using a well-crafted notebook or a premium keyboard—warm, tactile, and distinctly NOT another Tailwind template.

---

*Tactile: from Latin tactilis "tangible," from tangere "to touch." A premium theme should feel like you can reach out and touch it.*
