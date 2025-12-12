# RFC: Flat but Dimensional Aesthetic System

**Status**: Draft  
**Created**: 2025-01-23  
**Author**: Design System Team  
**Related**: `rfc-premium-tactile-theme.md`, `experimental/border-styles-demo.css`  
**Inspiration**: Modern code block designs with subtle depth (Iconoir-style documentation)

---

## Executive Summary

This RFC explores **enhancing Bengal's existing neumorphic style** by incorporating refined shadow layering and shape techniques from modern code block designs. Rather than replacing Bengal's distinctive tactile feel, we'll add multi-layer shadow depth and refined border treatments while preserving the neumorphic keyboard-key aesthetic.

**Key Question**: How can we enhance Bengal's neumorphic shadows with multi-layer depth techniques and refined border/shape treatments while maintaining the tactile, distinctive Bengal identity?

---

## 1. Current State Analysis

### 1.1 Existing Dimensional Systems

Bengal currently uses several depth techniques:

**Neumorphic Shadows** (`tokens/semantic.css:636-655`):
- Inset/outset shadow combinations
- Light/dark mode variants
- Applied to buttons, code copy buttons, language labels

**Elevation System** (`tokens/semantic.css:300-350`):
- `--elevation-card`, `--elevation-card-hover`, `--elevation-subtle`
- Standardized shadow tokens
- Used for cards, modals, overlays

**Code Block Styling** (`components/code.css:25-63`):
- Rounded corners (`--radius-2xl`: 16px)
- Subtle border (`1px solid rgba(0, 0, 0, 0.1)`)
- Animated border glow effect
- Box shadow: `var(--elevation-card)`

**Border Experiments** (`experimental/border-styles-demo.css`):
- 7 different border style options
- Gradient borders, corner accents, shadow borders
- Not yet integrated into main theme

### 1.2 What "Flat but Dimensional" Means

**Flat Design Characteristics**:
- Minimal visual hierarchy
- Clean, simple shapes
- No heavy gradients or textures
- Focus on content over decoration

**Dimensional Additions**:
- Subtle shadows for depth
- Refined borders (not heavy outlines)
- Rounded corners for softness
- Layered shadows (multiple shadow layers)
- Border/shadow combinations

**The Sweet Spot**:
- Elements feel like they exist in 3D space
- But remain visually "flat" (no heavy gradients, no heavy textures)
- Depth is communicated through shadow/border refinement, not heavy effects

---

## 2. Design Inspiration Analysis

### 2.1 Code Block Aesthetic (Iconoir-style)

**Observed Characteristics**:
- **Rounded corners**: Generous border radius (appears ~12-16px)
- **Subtle shadow**: Soft, multi-layer shadow creating depth
- **Refined border**: Thin border (1px) with low opacity
- **Copy button**: Positioned absolutely, rounded, with subtle shadow
- **Background**: Light gray with slight contrast from page background

**Visual Hierarchy**:
1. Background (page) - flat
2. Code block container - elevated with shadow
3. Copy button - further elevated (smaller shadow, positioned above)

**Depth Layers**:
```
Page Background (flat)
  └─ Code Block (elevated ~2-4px via shadow)
      └─ Copy Button (elevated ~1-2px via shadow)
```

### 2.2 Shadow Refinement Patterns

**Multi-Layer Shadows**:
```css
/* Example: Flat but dimensional shadow */
box-shadow:
  0 1px 2px rgba(0, 0, 0, 0.05),      /* Soft outer glow */
  0 0 0 1px rgba(0, 0, 0, 0.08),      /* Subtle border via shadow */
  0 2px 8px rgba(0, 0, 0, 0.04);      /* Depth layer */
```

**Border + Shadow Combinations**:
```css
/* Border defines edge, shadow adds depth */
border: 1px solid rgba(0, 0, 0, 0.1);
box-shadow: 0 2px 4px rgba(0, 0, 0, 0.04);
```

**Layered Depth**:
- Outer shadow: Soft, large blur (defines elevation)
- Border shadow: Tight, defines edge
- Inner shadow: Optional, for inset feel

### 2.3 Shape Refinement

**Border Radius Scale**:
- **Small elements** (buttons, badges): `8-12px` (soft but not pill-shaped)
- **Medium elements** (cards, code blocks): `12-16px` (generous rounding)
- **Large containers**: `16-24px` (very soft, modern feel)

**Asymmetric Rounding** (optional):
- Top corners more rounded than bottom
- Creates subtle "floating" effect

---

## 3. Design Options

### Option 1: Refined Shadow System (Recommended)

**Approach**: Enhance existing elevation tokens with multi-layer shadows that feel flat but dimensional.

**Implementation**:
```css
/* New tokens for flat-dimensional aesthetic */
:root {
  /* Flat-dimensional shadows - multi-layer for depth */
  --shadow-flat-subtle:
    0 1px 2px rgba(0, 0, 0, 0.04),
    0 0 0 1px rgba(0, 0, 0, 0.06);

  --shadow-flat-base:
    0 1px 3px rgba(0, 0, 0, 0.05),
    0 0 0 1px rgba(0, 0, 0, 0.08),
    0 2px 6px rgba(0, 0, 0, 0.04);

  --shadow-flat-elevated:
    0 2px 4px rgba(0, 0, 0, 0.06),
    0 0 0 1px rgba(0, 0, 0, 0.1),
    0 4px 12px rgba(0, 0, 0, 0.05);

  --shadow-flat-hover:
    0 4px 8px rgba(0, 0, 0, 0.08),
    0 0 0 1px rgba(0, 0, 0, 0.12),
    0 8px 16px rgba(0, 0, 0, 0.06);
}

/* Dark mode variants */
[data-theme="dark"] {
  --shadow-flat-subtle:
    0 1px 2px rgba(0, 0, 0, 0.3),
    0 0 0 1px rgba(255, 255, 255, 0.05);

  --shadow-flat-base:
    0 1px 3px rgba(0, 0, 0, 0.4),
    0 0 0 1px rgba(255, 255, 255, 0.08),
    0 2px 6px rgba(0, 0, 0, 0.3);

  --shadow-flat-elevated:
    0 2px 4px rgba(0, 0, 0, 0.5),
    0 0 0 1px rgba(255, 255, 255, 0.1),
    0 4px 12px rgba(0, 0, 0, 0.4);

  --shadow-flat-hover:
    0 4px 8px rgba(0, 0, 0, 0.6),
    0 0 0 1px rgba(255, 255, 255, 0.12),
    0 8px 16px rgba(0, 0, 0, 0.5);
}
```

**Application**:
- Code blocks: `--shadow-flat-base`
- Cards: `--shadow-flat-subtle` → `--shadow-flat-hover` on hover
- Buttons: `--shadow-flat-base` → `--shadow-flat-elevated` on hover
- Copy buttons: `--shadow-flat-subtle` → `--shadow-flat-base` on hover

**Pros**:
- ✅ Maintains flat aesthetic
- ✅ Adds subtle depth
- ✅ Works with existing elevation system
- ✅ Easy to apply via tokens

**Cons**:
- ⚠️ May conflict with existing neumorphic system
- ⚠️ Requires careful integration

---

### Option 2: Refined Border + Enhanced Neumorphic Shadow

**Approach**: Combine refined border opacity with enhanced neumorphic shadows for cleaner edges while maintaining tactile feel.

**Implementation**:
```css
/* Refined borders for code blocks and cards */
:root {
  /* Softer border opacity (current: 0.1, proposed: 0.08) */
  --border-refined-subtle: 1px solid rgba(0, 0, 0, 0.06);
  --border-refined-base: 1px solid rgba(0, 0, 0, 0.08);
  --border-refined-strong: 1px solid rgba(0, 0, 0, 0.1);

  /* Enhanced neumorphic shadows (from Option 1) */
  --neumorphic-enhanced-base: /* ... */;
  --neumorphic-enhanced-hover: /* ... */;
}

/* Combined application - refined border + enhanced neumorphic */
.code-block-enhanced {
  border: var(--border-refined-base);  /* Softer border */
  border-radius: var(--radius-soft-xl);  /* Enhanced radius */
  box-shadow: var(--neumorphic-enhanced-base);  /* Enhanced neumorphic */
  transition: box-shadow var(--transition-base), border-color var(--transition-base);
}

.code-block-enhanced:hover {
  border-color: var(--border-refined-strong);
  box-shadow: var(--neumorphic-enhanced-hover);
}
```

**Pros**:
- ✅ Refined border creates cleaner edge
- ✅ Enhanced neumorphic maintains tactile feel
- ✅ Works with existing border system
- ✅ Easy to apply incrementally

**Cons**:
- ⚠️ Border + shadow combination may feel heavy
- ⚠️ Requires careful opacity balance

---

### Option 3: Shadow-Only Borders

**Approach**: Use shadows to create border-like edges without actual borders.

**Implementation**:
```css
/* Shadow creates border effect */
:root {
  --shadow-border-only-subtle:
    0 0 0 1px rgba(0, 0, 0, 0.06),
    0 1px 2px rgba(0, 0, 0, 0.04);

  --shadow-border-only-base:
    0 0 0 1px rgba(0, 0, 0, 0.08),
    0 2px 4px rgba(0, 0, 0, 0.05);

  --shadow-border-only-elevated:
    0 0 0 1px rgba(0, 0, 0, 0.1),
    0 4px 8px rgba(0, 0, 0, 0.06);
}

/* Application - no border property needed */
.flat-dimensional-card {
  border: none;  /* No actual border */
  border-radius: var(--radius-xl);
  box-shadow: var(--shadow-border-only-base);
}
```

**Pros**:
- ✅ Purest "flat" aesthetic (no visible borders)
- ✅ Depth still communicated via shadow
- ✅ Very modern feel

**Cons**:
- ⚠️ Less edge definition (may feel less structured)
- ⚠️ Harder to achieve consistent appearance across backgrounds

---

### Option 4: Enhanced Border Radius Scale

**Approach**: Increase border radius values for softer, more modern shapes.

**Current Radius Scale** (`tokens/foundation.css:174-181`):
```css
--radius-sm: 0.125rem;   /* 2px */
--radius-md: 0.25rem;     /* 4px */
--radius-lg: 0.5rem;      /* 8px */
--radius-xl: 0.75rem;     /* 12px */
--radius-2xl: 1rem;      /* 16px */
--radius-3xl: 1.5rem;    /* 24px */
```

**Proposed Enhanced Scale**:
```css
/* Keep existing for backward compatibility */
/* Add new "soft" variants for flat-dimensional aesthetic */
:root {
  --radius-soft-sm: 0.375rem;   /* 6px - between sm and md */
  --radius-soft-md: 0.5rem;     /* 8px - matches current lg */
  --radius-soft-lg: 0.75rem;    /* 12px - matches current xl */
  --radius-soft-xl: 1rem;       /* 16px - matches current 2xl */
  --radius-soft-2xl: 1.25rem;   /* 20px - new, very soft */
  --radius-soft-3xl: 1.5rem;    /* 24px - matches current 3xl */
}
```

**Application**:
- Code blocks: `--radius-soft-xl` (16px) or `--radius-soft-2xl` (20px)
- Cards: `--radius-soft-lg` (12px) or `--radius-soft-xl` (16px)
- Buttons: `--radius-soft-md` (8px) or `--radius-soft-lg` (12px)
- Copy buttons: `--radius-soft-md` (8px)

**Pros**:
- ✅ Softer, more modern feel
- ✅ Maintains backward compatibility
- ✅ Easy to apply incrementally

**Cons**:
- ⚠️ May feel too rounded for some use cases
- ⚠️ Requires design review for each component

---

### Option 5: Layered Shadow Depth System

**Approach**: Create a systematic depth scale using layered shadows.

**Depth Levels**:
```css
:root {
  /* Level 0: Flat (no shadow, or minimal) */
  --depth-0: none;

  /* Level 1: Subtle elevation (floating slightly) */
  --depth-1:
    0 1px 2px rgba(0, 0, 0, 0.04),
    0 0 0 1px rgba(0, 0, 0, 0.06);

  /* Level 2: Base elevation (cards, code blocks) */
  --depth-2:
    0 1px 3px rgba(0, 0, 0, 0.05),
    0 0 0 1px rgba(0, 0, 0, 0.08),
    0 2px 6px rgba(0, 0, 0, 0.04);

  /* Level 3: Elevated (hover states, modals) */
  --depth-3:
    0 2px 4px rgba(0, 0, 0, 0.06),
    0 0 0 1px rgba(0, 0, 0, 0.1),
    0 4px 12px rgba(0, 0, 0, 0.05);

  /* Level 4: High elevation (dropdowns, popovers) */
  --depth-4:
    0 4px 8px rgba(0, 0, 0, 0.08),
    0 0 0 1px rgba(0, 0, 0, 0.12),
    0 8px 16px rgba(0, 0, 0, 0.06);

  /* Level 5: Highest (modals, overlays) */
  --depth-5:
    0 8px 16px rgba(0, 0, 0, 0.1),
    0 0 0 1px rgba(0, 0, 0, 0.15),
    0 16px 32px rgba(0, 0, 0, 0.08);
}
```

**Application**:
- Code blocks: `--depth-2` (base) → `--depth-3` (hover)
- Cards: `--depth-1` (base) → `--depth-2` (hover)
- Buttons: `--depth-1` (base) → `--depth-2` (hover) → `--depth-0` (active)
- Copy buttons: `--depth-1` (base) → `--depth-2` (hover)
- Dropdowns: `--depth-4`
- Modals: `--depth-5`

**Pros**:
- ✅ Systematic depth scale
- ✅ Easy to understand and apply
- ✅ Consistent visual hierarchy

**Cons**:
- ⚠️ May feel too rigid
- ⚠️ Requires careful tuning per component

---

## 4. Integration Strategy

### 4.1 Enhancement Approach (Not Replacement)

**Current State**: Bengal uses neumorphic shadows for tactile feel (buttons, code copy buttons, language labels).

**Strategy**: Enhance existing neumorphic tokens with multi-layer depth while preserving tactile feel:

```css
/* Current neumorphic (keep for backward compatibility) */
--neumorphic-base: inset/outset shadows...

/* Enhanced neumorphic (adds multi-layer depth) */
--neumorphic-enhanced-base:
  /* All existing neumorphic layers */
  /* PLUS border-defining shadow */
  /* PLUS depth layers */

/* Components can opt-in to enhanced version */
.code-block {
  box-shadow: var(--neumorphic-enhanced-base);  /* Enhanced */
}

.button {
  box-shadow: var(--neumorphic-base);  /* Keep current tactile feel */
}
```

**Migration Path**:
1. **Phase 1**: Add enhanced neumorphic tokens alongside existing
2. **Phase 2**: Apply enhanced version to code blocks and cards
3. **Phase 3**: Keep buttons on current neumorphic (or make configurable)
4. **Phase 4**: Optionally enhance copy buttons (test with frosted glass)

### 4.2 Component-Specific Application

**Code Blocks** (`components/code.css:25-40`):
- **Current**:
  - `border: 1px solid rgba(0, 0, 0, 0.1)`
  - `box-shadow: var(--elevation-card)` + animated glow
  - `border-radius: var(--radius-2xl)` (16px)
- **Proposed Enhancement**:
  - `border: 1px solid rgba(0, 0, 0, 0.08)` (softer opacity)
  - `box-shadow: var(--neumorphic-enhanced-base)` + animated glow
  - `border-radius: var(--radius-soft-xl)` (16px) or `--radius-soft-2xl` (20px)
- **Rationale**: Enhanced neumorphic adds depth layers while keeping tactile feel; refined border creates cleaner edge

**Cards** (`components/cards.css:10-23`):
- **Current**:
  - `border: 1px solid var(--color-border)`
  - `box-shadow: var(--elevation-low)`
  - `border-radius: var(--radius-xl)` (12px)
- **Proposed Enhancement**:
  - `border: 1px solid rgba(0, 0, 0, 0.08)` (refined opacity)
  - `box-shadow: var(--neumorphic-enhanced-subtle)` (enhanced version)
  - Hover: `box-shadow: var(--neumorphic-enhanced-hover)`
  - `border-radius: var(--radius-soft-lg)` (12px) or `--radius-soft-xl` (16px)
- **Rationale**: Enhanced neumorphic maintains tactile feel while adding refined depth

**Buttons** (`components/buttons.css`):
- **Current**: Neumorphic system (`--neumorphic-base`, `--neumorphic-hover`, `--neumorphic-pressed`)
- **Proposed**: **Keep as-is** (tactile feel is core to Bengal's identity)
- **Optional**: Add enhanced variant for users who want more depth

**Copy Buttons** (`components/code.css:276-468`):
- **Current**: Neumorphic with frosted glass (`backdrop-filter: blur(12px)`)
- **Proposed Enhancement**:
  - Keep neumorphic base (works well with frosted glass)
  - Optionally add depth layer on hover: `var(--neumorphic-enhanced-hover)`
- **Rationale**: Frosted glass + neumorphic is distinctive; enhance hover state only

### 4.3 Configuration Option (Optional)

**Theme Config** (`bengal.toml`):
```toml
[theme]
# Shadow enhancement: "standard" (current) or "enhanced" (adds multi-layer depth)
shadow_enhancement = "enhanced"  # default: enhanced

# Border radius scale: "standard" (current) or "soft" (slightly more rounded)
border_radius_scale = "soft"  # default: standard (backward compatible)
```

**CSS Variable Override**:
```css
/* User can override via CSS custom properties */
:root {
  --use-enhanced-shadows: 1;  /* 1 = enhanced, 0 = standard */
  --use-soft-radius: 1;  /* 1 = soft, 0 = standard */
}

/* Components check these flags */
.code-block {
  box-shadow: var(--use-enhanced-shadows, 1)
    ? var(--neumorphic-enhanced-base)
    : var(--elevation-card);

  border-radius: var(--use-soft-radius, 1)
    ? var(--radius-soft-xl)
    : var(--radius-2xl);
}
```

**Note**: Configuration is optional - enhanced versions can be default with standard as fallback.

---

## 5. Implementation Plan

### Phase 1: Enhanced Neumorphic Tokens (Week 1)

**Tasks**:
- [ ] Add enhanced neumorphic tokens to `tokens/semantic.css`
  - `--neumorphic-enhanced-base` (adds border-defining + depth layers)
  - `--neumorphic-enhanced-hover` (enhanced hover state)
  - `--neumorphic-enhanced-subtle` (for smaller elements)
- [ ] Add refined border opacity tokens (`--border-refined-*`)
- [ ] Add soft border radius variants (`--radius-soft-*`)
- [ ] Create dark mode variants for all enhanced tokens
- [ ] Test with all 5 breed palettes
- [ ] Document token usage in design system docs

**Deliverables**:
- Updated `tokens/semantic.css` with enhanced neumorphic tokens
- Token reference documentation
- Visual comparison (standard vs enhanced)

### Phase 2: Code Block Enhancement (Week 2)

**Tasks**:
- [ ] Update code block styling to use enhanced neumorphic shadows
  - Replace `var(--elevation-card)` with `var(--neumorphic-enhanced-base)`
  - Keep animated glow effect (signature Bengal feature)
- [ ] Refine border opacity (0.1 → 0.08)
- [ ] Optionally increase border radius to soft scale (16px → 20px)
- [ ] Enhance copy button hover state with enhanced neumorphic
- [ ] Test with all 5 breed palettes
- [ ] Verify dark mode appearance
- [ ] Ensure animated glow still works with enhanced shadows

**Deliverables**:
- Updated `components/code.css`
- Visual comparison (before/after)
- Palette compatibility test results

### Phase 3: Card System Enhancement (Week 3)

**Tasks**:
- [ ] Update card base styling to use enhanced neumorphic
  - Replace `var(--elevation-low)` with `var(--neumorphic-enhanced-subtle)`
- [ ] Enhance hover states with `var(--neumorphic-enhanced-hover)`
- [ ] Refine border opacity (keep existing or use refined variant)
- [ ] Optionally increase border radius to soft scale
- [ ] Test card variants (feature cards, article cards)
- [ ] Verify motion blob effects still work
- [ ] Verify responsive behavior

**Deliverables**:
- Updated `components/cards.css`
- Card showcase page
- Motion blob compatibility verification

### Phase 4: Polish & Documentation (Week 4)

**Tasks**:
- [ ] Review all enhanced components for consistency
- [ ] Add configuration option for shadow enhancement (optional)
- [ ] Document enhancement approach and rationale
- [ ] Create visual style guide showing before/after
- [ ] Update design system documentation
- [ ] Performance audit (shadow complexity impact)

**Deliverables**:
- Configuration documentation (if implemented)
- Visual style guide
- Design system documentation update
- Performance audit results

---

## 6. Design Decisions

### 6.1 Shadow Opacity Values

**Light Mode**:
- Outer shadow: `rgba(0, 0, 0, 0.04-0.08)` (very subtle)
- Border shadow: `rgba(0, 0, 0, 0.06-0.12)` (subtle edge)
- Depth shadow: `rgba(0, 0, 0, 0.04-0.06)` (soft depth)

**Dark Mode**:
- Outer shadow: `rgba(0, 0, 0, 0.3-0.5)` (more visible)
- Border shadow: `rgba(255, 255, 255, 0.05-0.12)` (light edge)
- Depth shadow: `rgba(0, 0, 0, 0.3-0.5)` (stronger depth)

**Rationale**: Dark mode needs higher opacity for visibility, but maintains flat aesthetic.

### 6.2 Border Radius Values

**Current → Proposed**:
- Code blocks: `16px` → `16-20px` (maintain or slightly increase)
- Cards: `12px` → `12-16px` (maintain or slightly increase)
- Buttons: `8px` → `8-12px` (maintain or slightly increase)
- Copy buttons: `8px` → `8px` (maintain)

**Rationale**: Slight increases create softer feel without being too rounded.

### 6.3 Shadow Layer Count

**Base Elements**: 2-3 layers
- Border-defining shadow (tight blur)
- Depth shadow (larger blur)

**Elevated Elements**: 3 layers
- Border-defining shadow
- Depth shadow (medium blur)
- Outer glow (large blur)

**Rationale**: More layers = more depth, but keep it subtle to maintain flat aesthetic.

---

## 7. Tradeoffs & Considerations

### 7.1 Enhanced Neumorphic vs Standard Neumorphic

**Standard Neumorphic (Current)**:
- ✅ Tactile, keyboard-key feel
- ✅ Distinctive Bengal identity
- ✅ Works well with frosted glass
- ✅ Proven and tested
- ⚠️ Can feel heavy if overused
- ⚠️ Less refined depth than enhanced version

**Enhanced Neumorphic (Proposed)**:
- ✅ Preserves tactile, keyboard-key feel
- ✅ Maintains Bengal identity
- ✅ Adds refined depth via multi-layer shadows
- ✅ Border-defining shadow creates cleaner edge
- ✅ More sophisticated appearance
- ⚠️ More complex shadow definitions
- ⚠️ Requires testing with all palettes

**Recommendation**: Enhance neumorphic system by adding multi-layer depth layers while preserving all existing inset/outset tactile characteristics. Apply to code blocks and cards; keep buttons on standard neumorphic (or make configurable).

### 7.2 Performance Considerations

**Shadow Complexity**:
- Multi-layer shadows have minimal performance impact
- Modern browsers handle `box-shadow` efficiently
- No JavaScript required

**Border Radius**:
- Larger border radius values have no performance impact
- CSS-only, hardware-accelerated

**Recommendation**: No performance concerns with proposed approach.

### 7.3 Accessibility

**Contrast**:
- Shadows don't affect text contrast
- Border shadows may affect edge visibility
- Ensure borders meet WCAG contrast requirements

**Visual Hierarchy**:
- Flat-dimensional shadows create clear elevation hierarchy
- Helps users understand interactive elements
- Maintains focus state visibility

**Recommendation**: Audit contrast for border shadows, ensure focus states remain visible.

### 7.4 Backward Compatibility

**Token System**:
- New tokens don't break existing styles
- Existing components continue using neumorphic
- Migration is opt-in

**Border Radius**:
- New "soft" variants are additive
- Existing `--radius-*` tokens unchanged
- Components can opt-in to soft variants

**Recommendation**: Fully backward compatible approach.

---

## 8. Success Criteria

### Visual Quality
- [ ] Code blocks feel elevated but not heavy
- [ ] Cards have clear depth hierarchy
- [ ] Shadows feel subtle and refined
- [ ] Border radius creates soft, modern feel
- [ ] Works well with all 5 breed palettes

### Technical Quality
- [ ] All new tokens documented
- [ ] Dark mode variants tested
- [ ] Responsive behavior verified
- [ ] Performance impact negligible
- [ ] Backward compatible

### Design System Integration
- [ ] Coexists with neumorphic system
- [ ] Clear usage guidelines
- [ ] Configuration options available
- [ ] Visual style guide updated

---

## 9. Open Questions

1. **Should enhanced neumorphic be default or opt-in?**
   - **Option A**: Default for code blocks/cards (recommended)
   - **Option B**: Opt-in via configuration
   - **Option C**: Both (default enhanced, config to use standard)

2. **Should border radius scale be increased globally or per-component?**
   - **Option A**: Per-component only (code blocks: 16px → 20px, cards: 12px → 16px, buttons: keep 8px)
   - **Option B**: Global increase via soft variants (all components get softer)
   - **Option C**: Configuration option (user chooses standard vs soft)

3. **Should buttons use enhanced neumorphic?**
   - **Option A**: Keep standard neumorphic (preserves tactile feel)
   - **Option B**: Use enhanced neumorphic (more depth)
   - **Option C**: Configuration option (user chooses)

4. **How should copy buttons be styled?**
   - **Option A**: Keep standard neumorphic (works well with frosted glass)
   - **Option B**: Use enhanced neumorphic hover only
   - **Option C**: Full enhanced neumorphic (base + hover)

---

## 10. References

### Internal
- `bengal/themes/default/assets/css/tokens/semantic.css` - Current shadow/elevation tokens
- `bengal/themes/default/assets/css/components/code.css` - Code block styling
- `bengal/themes/default/assets/css/components/cards.css` - Card styling
- `bengal/themes/default/assets/css/experimental/border-styles-demo.css` - Border experiments
- `plan/rfc-premium-tactile-theme.md` - Related tactile theme RFC

### External
- [Apple HIG: Materials](https://developer.apple.com/design/human-interface-guidelines/materials) - Vibrancy and depth
- [Material Design: Elevation](https://m3.material.io/styles/elevation/overview) - Shadow depth system
- Modern code block designs (Iconoir, Supabase, Linear) - Inspiration

---

## Conclusion

This RFC proposes **enhancing Bengal's existing neumorphic style** by incorporating multi-layer shadow depth techniques and refined border/shape treatments from modern code block designs. Rather than replacing Bengal's distinctive tactile feel, we'll add sophisticated depth layers while preserving all neumorphic characteristics.

**Recommended Approach**:
- **Option 1** (Enhanced Neumorphic with Multi-Layer Depth) + **Option 2** (Refined Border) + **Option 4** (Enhanced Border Radius)
- Enhance code blocks and cards with multi-layer depth
- Keep standard neumorphic for buttons (or make configurable)
- Refine border opacity for cleaner edges
- Optionally increase border radius for softer shapes

**Key Principles**:
1. **Preserve Bengal Identity**: Keep neumorphic tactile feel, enhance with depth layers
2. **Refined Edges**: Softer border opacity creates cleaner appearance
3. **Multi-Layer Depth**: Border-defining + depth shadows add sophistication
4. **Selective Application**: Enhance containers (code blocks, cards), keep buttons tactile

**Next Steps**:
1. Review and refine enhanced neumorphic shadow definitions
2. Create visual mockups showing before/after comparison
3. Implement Phase 1 (enhanced neumorphic tokens)
4. Test with all 5 breed palettes (light + dark modes)
5. Gather feedback before full implementation

---

*"Enhanced neumorphic" - where Bengal's tactile identity meets refined depth, and distinctive meets sophisticated.*
