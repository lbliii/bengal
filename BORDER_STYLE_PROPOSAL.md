# Element Shape & Border Style Exploration for Bengal Theme

**Goal**: Fresh element shapes (border-radius) and border styles that complement the Bengal theme, stand out subtly, and maintain readability for documentation.

---

## Current State

**Existing Element Shapes (Border-Radius)**:
- **Cards**: `8px` radius (`--radius-lg`) - moderately rounded
- **Code blocks**: `12px` radius (`--radius-xl`) - more rounded
- **Buttons**: `4px` radius (`--radius-md`) - minimal rounding
- **Tabs**: `4px` radius (`--radius-md`) - minimal rounding
- **Badges**: Fully rounded (`--radius-full`) - pill shape
- **Forms/Inputs**: `4px` radius (`--border-radius-medium`) - minimal rounding
- **Dropdowns**: `4px` radius (`--radius-md`) - minimal rounding
- **Tables**: `8px` radius on wrapper - moderate rounding
- **Admonitions**: Rounded on right side only (`0 var(--border-radius-large) var(--border-radius-large) 0`)
- **Blockquotes**: **Sharp corners** (`border-radius: 0`) - no rounding
- **Images**: `var(--radius-md)` - minimal rounding

**Many elements are quite sharp/minimal** - opportunity to add cohesive roundedness!

**Theme Identity**: Bengal (tiger/big cat) - suggests strength, elegance, precision, but also fluidity and grace

---

## Element Shape Concepts

### 1. **Cohesive Roundedness** (Refined Minimalism)
**Approach**: Increase border radius consistently across all elements for a softer, more modern feel

**Proposed Changes**:
- **Cards**: `8px` → `12px` (`--radius-lg` → `--radius-xl`)
- **Code blocks**: `12px` → `16px` (`--radius-xl` → `--radius-2xl`)
- **Buttons**: `4px` → `8px` (`--radius-md` → `--radius-lg`)
- **Tabs**: `4px` → `8px` (`--radius-md` → `--radius-lg`)
- **Forms/Inputs**: `4px` → `6px` (new `--radius-md-lg` or use `--radius-lg`)
- **Dropdowns**: `4px` → `8px` (`--radius-md` → `--radius-lg`)
- **Tables**: Keep `8px` or increase to `12px`
- **Blockquotes**: `0` → `8px` (add rounding!)
- **Images**: `4px` → `8px` or `12px`
- **Admonitions**: Increase right-side radius to match

**Rationale**: 
- More approachable, less "boxy"
- Cohesive visual language
- Still clean and professional
- Works well for documentation
- Modern, friendly feel

**Example**:
```css
/* Cards - softer */
.card {
  border-radius: var(--radius-xl); /* 12px instead of 8px */
}

/* Code blocks - more rounded */
pre {
  border-radius: var(--radius-2xl); /* 16px instead of 12px */
}

/* Buttons - more rounded */
.button {
  border-radius: var(--radius-lg); /* 8px instead of 4px */
}

/* Blockquotes - add rounding! */
.prose blockquote {
  border-radius: var(--radius-lg); /* 8px instead of 0 */
}

/* Forms - softer */
.form-input {
  border-radius: var(--radius-lg); /* 8px instead of 4px */
}
```

---

### 2. **Variable Roundedness by Element Type** (Hierarchical)
**Approach**: Different radius levels based on element importance/size

**Proposed Scale**:
- **Small elements** (badges, tags, small buttons): `6px` (`--radius-md-lg`)
- **Medium elements** (buttons, inputs, tabs): `8px` (`--radius-lg`)
- **Large elements** (cards, code blocks): `12px` (`--radius-xl`)
- **Extra large** (hero sections, major containers): `16px` (`--radius-2xl`)

**Rationale**:
- Creates visual hierarchy
- Larger elements feel more substantial
- Smaller elements stay crisp
- Professional, intentional feel

### 3. **Asymmetric Borders** (Bengal-Inspired)
**Approach**: Different border widths/colors on different sides, inspired by tiger stripes

**Concept**: 
- Thicker top border (like a tiger's forehead stripe)
- Thinner side borders
- Accent color on one side

**Implementation**:
```css
.card {
  border-top: 2px solid var(--color-primary);
  border-right: 1px solid var(--color-border);
  border-bottom: 1px solid var(--color-border);
  border-left: 1px solid var(--color-border);
  border-radius: var(--radius-xl);
}

.card:hover {
  border-top-color: var(--color-primary-hover);
  border-right-color: var(--color-border-dark);
  border-bottom-color: var(--color-border-dark);
  border-left-color: var(--color-border-dark);
}
```

**Rationale**:
- Unique, memorable
- Subtle reference to Bengal theme
- Draws attention to top (natural reading flow)

**Considerations**:
- May be too bold for some contexts
- Test with different card types

---

### 3. **Gradient Borders** (Modern Accent)
**Approach**: Subtle gradient borders using CSS gradients

**Implementation**:
```css
.card {
  position: relative;
  background: var(--color-bg-primary);
  border-radius: var(--radius-xl);
}

.card::before {
  content: '';
  position: absolute;
  inset: 0;
  border-radius: var(--radius-xl);
  padding: 1px;
  background: linear-gradient(
    135deg,
    var(--color-primary) 0%,
    var(--color-accent) 50%,
    var(--color-primary) 100%
  );
  -webkit-mask: 
    linear-gradient(#fff 0 0) content-box, 
    linear-gradient(#fff 0 0);
  -webkit-mask-composite: xor;
  mask-composite: exclude;
  pointer-events: none;
}
```

**Rationale**:
- Modern, eye-catching
- Subtle enough for docs
- Works with existing color system

**Considerations**:
- More complex CSS
- Browser support (modern browsers only)

---

### 4. **Double Border** (Elegant Frame)
**Approach**: Two-tone border effect (outer + inner)

**Implementation**:
```css
.card {
  border: 1px solid var(--color-border);
  border-radius: var(--radius-xl);
  box-shadow: 
    0 0 0 1px var(--color-bg-primary),
    0 0 0 2px var(--color-border-light);
  /* Creates double border effect */
}
```

**Alternative (using outline)**:
```css
.card {
  border: 1px solid var(--color-border);
  border-radius: var(--radius-xl);
  outline: 1px solid var(--color-border-light);
  outline-offset: -2px;
}
```

**Rationale**:
- Elegant, refined
- Adds depth without distraction
- Classic design pattern

---

### 5. **Corner Accents** (Bengal Signature)
**Approach**: Small accent marks in corners (like tiger paw marks)

**Implementation**:
```css
.card {
  border: 1px solid var(--color-border);
  border-radius: var(--radius-xl);
  position: relative;
}

.card::before,
.card::after {
  content: '';
  position: absolute;
  width: 8px;
  height: 8px;
  border: 2px solid var(--color-primary);
  border-radius: 50%;
  opacity: 0.3;
}

.card::before {
  top: 12px;
  left: 12px;
}

.card::after {
  bottom: 12px;
  right: 12px;
}

.card:hover::before,
.card:hover::after {
  opacity: 0.6;
}
```

**Rationale**:
- Unique, memorable
- Subtle Bengal reference
- Doesn't interfere with content

**Considerations**:
- May be too decorative for some
- Could use different shapes (squares, triangles)

---

### 6. **Soft Shadow Borders** (Depth Without Lines)
**Approach**: Replace solid borders with soft shadows for depth

**Implementation**:
```css
.card {
  border: none;
  border-radius: var(--radius-xl);
  box-shadow: 
    0 1px 3px rgba(0, 0, 0, 0.05),
    0 0 0 1px var(--color-border-light);
  /* Soft shadow + subtle border */
}

.card:hover {
  box-shadow: 
    0 4px 12px rgba(0, 0, 0, 0.08),
    0 0 0 1px var(--color-border);
}
```

**Rationale**:
- Modern, clean
- Less visual weight
- Focus on content

---

### 7. **Rounded with Notch** (Modern Tech)
**Approach**: Rounded corners with a small notch/cutout (like modern UI design)

**Implementation**:
```css
.card {
  border: 1px solid var(--color-border);
  border-radius: var(--radius-xl);
  clip-path: polygon(
    0% 0%,
    100% 0%,
    100% 100%,
    0% 100%,
    0% calc(100% - 8px),
    8px calc(100% - 8px),
    8px 100%,
    0% 100%
  );
  /* Creates small notch in bottom-left */
}
```

**Rationale**:
- Unique, modern
- Tech-forward feel
- Subtle detail

**Considerations**:
- More complex
- May not work for all card types

---

## Recommended Combinations

### **Option A: Cohesive Roundedness** (Safest & Recommended)
- Increase border radius consistently across all elements
- Cards: 8px → 12px
- Code blocks: 12px → 16px  
- Buttons/Forms/Tabs: 4px → 8px
- Blockquotes: 0 → 8px (add rounding!)
- Images: 4px → 8px or 12px
- Keep existing border styles (1px solid, etc.)
- **Risk**: Low
- **Impact**: Noticeable improvement, more modern feel
- **Best for**: Quick win, immediate visual upgrade

### **Option B: Variable Roundedness** (Hierarchical)
- Different radius levels by element size/importance
- Small: 6px, Medium: 8px, Large: 12px, XL: 16px
- Creates visual hierarchy
- **Risk**: Low-Medium
- **Impact**: More sophisticated, intentional feel

### **Option C: Roundedness + Subtle Accents** (Balanced)
- Cohesive roundedness (Option A)
- Plus asymmetric top border on cards
- Plus corner accents on feature cards
- **Risk**: Low-Medium
- **Impact**: Stands out more, Bengal-themed touches

### **Option D: Modern Gradient Borders** (Bold)
- Cohesive roundedness
- Plus gradient borders on cards
- Plus soft shadows
- **Risk**: Medium
- **Impact**: Very modern, stands out significantly

---

## Implementation Strategy

### Phase 1: Cohesive Roundedness (Recommended Starting Point)
**Goal**: Add consistent roundedness across all elements

1. **Update Core Elements**:
   - Cards: `--radius-lg` → `--radius-xl` (8px → 12px)
   - Code blocks: `--radius-xl` → `--radius-2xl` (12px → 16px)
   - Buttons: `--radius-md` → `--radius-lg` (4px → 8px)
   - Forms/Inputs: `--radius-md` → `--radius-lg` (4px → 8px)
   - Tabs: `--radius-md` → `--radius-lg` (4px → 8px)
   - Dropdowns: `--radius-md` → `--radius-lg` (4px → 8px)

2. **Fix Sharp Elements**:
   - Blockquotes: `border-radius: 0` → `var(--radius-lg)` (add 8px rounding!)
   - Images: `var(--radius-md)` → `var(--radius-lg)` or `var(--radius-xl)`
   - Admonitions: Increase right-side radius

3. **Test Across Site**:
   - All card types
   - All form elements
   - Code examples
   - Tables
   - Dark mode
   - Mobile responsiveness

4. **Gather Feedback**

### Phase 2: Add Subtle Accents (Optional Enhancement)
**Only if Phase 1 is successful and you want more personality**

1. Add asymmetric top border to cards (Bengal-inspired)
2. Add corner accents to feature cards
3. Test with different content types

### Phase 3: Advanced Styles (Future Consideration)
**Only if you want to stand out significantly**

1. Implement gradient borders
2. Add soft shadow variants
3. Create border style variants (utilities)

---

## CSS Variables to Add (if needed)

```css
/* Border Radius Variants (if using hierarchical approach) */
--radius-md-lg: 0.375rem; /* 6px - between md and lg */
--radius-card: var(--radius-xl); /* 12px for cards */
--radius-code: var(--radius-2xl); /* 16px for code blocks */
--radius-button: var(--radius-lg); /* 8px for buttons */
--radius-form: var(--radius-lg); /* 8px for form inputs */

/* Border Style Variants (for accent styles) */
--border-style-default: 1px solid var(--color-border);
--border-style-accent: 2px solid var(--color-primary);
--border-style-subtle: 1px solid var(--color-border-light);

/* Border Accent Colors */
--border-accent-top: var(--color-primary);
--border-accent-side: var(--color-border);
```

**Note**: Most of these can use existing variables (`--radius-lg`, `--radius-xl`, etc.) - only add new ones if you need intermediate sizes.

---

## Testing Checklist

**Element Shapes (Border-Radius)**:
- [ ] Cards (all variants: `.card`, `.article-card`, `.feature-card`, `.stat-card`)
- [ ] Code blocks (`pre`, `.code-block-wrapper`)
- [ ] Buttons (all sizes and styles)
- [ ] Forms (inputs, textareas, selects)
- [ ] Tabs (`.tabs`, `.code-tabs`)
- [ ] Dropdowns (`details.dropdown`)
- [ ] Tables (`.bengal-data-table-wrapper`)
- [ ] Admonitions (all types)
- [ ] **Blockquotes** (currently sharp - add rounding!)
- [ ] Images (`.prose img`)
- [ ] Badges (already rounded - verify consistency)

**Visual Consistency**:
- [ ] Dark mode (all elements)
- [ ] Mobile responsiveness (rounded corners work on small screens)
- [ ] Print styles (may need to reduce/remove rounding)
- [ ] Accessibility (focus states maintain rounded corners)
- [ ] Nested elements (cards in cards, etc.)

**Edge Cases**:
- [ ] Code blocks with headers
- [ ] Cards with images
- [ ] Forms with errors
- [ ] Tables with many columns
- [ ] Long content in rounded containers

---

## Questions to Consider

1. **How rounded do we want to be?**
   - Subtle increase (Option A - Recommended)
   - Variable by size (Option B)
   - Maximum roundedness (everything 12px+)

2. **Which elements are priority?**
   - **High**: Cards, code blocks, buttons, blockquotes (currently sharp!)
   - **Medium**: Forms, tabs, dropdowns
   - **Low**: Badges (already rounded), small utility elements

3. **Consistency vs Hierarchy?**
   - Same radius for similar elements (consistent)
   - Different radius by element size (hierarchical)

4. **Dark mode considerations?**
   - Same roundedness in dark mode?
   - Any visual adjustments needed?

5. **Mobile considerations?**
   - Keep same radius on mobile?
   - Slightly smaller radius on very small screens?

---

## Next Steps

1. **Review this proposal** ✅
2. **Choose preferred direction**:
   - **Option A** (Recommended): Cohesive roundedness - quick win, modern feel
   - **Option B**: Variable roundedness - more sophisticated
   - **Option C**: Roundedness + accents - more personality
   - **Option D**: Maximum modern - bold statement
3. **Create test implementation** for selected option
4. **Test across site** (use checklist above)
5. **Iterate based on feedback**

## Quick Start: Option A Implementation

If choosing Option A (Cohesive Roundedness), here's what to update:

**Files to modify**:
- `components/cards.css` - Cards: `--radius-lg` → `--radius-xl`
- `components/code.css` - Code blocks: `--radius-xl` → `--radius-2xl`
- `components/buttons.css` - Buttons: `--radius-md` → `--radius-lg`
- `components/forms.css` - Forms: `--border-radius-medium` → `--radius-lg`
- `components/tabs.css` - Tabs: `--radius-md` → `--radius-lg`
- `components/dropdowns.css` - Dropdowns: `--radius-md` → `--radius-lg`
- `base/typography.css` - Blockquotes: `border-radius: 0` → `var(--radius-lg)`
- `base/typography.css` - Images: `var(--radius-md)` → `var(--radius-lg)` or `var(--radius-xl)`
- `components/admonitions.css` - Increase right-side radius

**Estimated impact**: ~15-20 file changes, immediate visual improvement, low risk

---

## References

- Current border radius values: `tokens/foundation.css`
- Card styles: `components/cards.css`
- Code block styles: `components/code.css`
- Admonition styles: `components/admonitions.css`

