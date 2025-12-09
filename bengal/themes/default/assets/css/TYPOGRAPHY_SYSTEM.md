# Typography System Documentation

## Overview

This is a complete rewrite of the typography system with a clean, systematic approach. All typography tokens are now centralized and consistent.

## Architecture

### Token Layers

1. **Foundation Tokens** (`tokens/typography.css`)
   - Raw values: `--font-size-xs`, `--font-weight-bold`, `--line-height-tight`
   - These are the source of truth for all typography values

2. **Semantic Tokens** (`tokens/semantic.css`)
   - Purpose-based aliases: `--text-h1`, `--text-body`, `--weight-heading`
   - Maps foundation tokens to semantic meanings
   - Provides backward compatibility with old token names

3. **Component Styles** (`base/typography.css`)
   - Uses semantic tokens to style elements
   - Provides utility classes

## Typography Scale

### Font Sizes

The scale uses a **Major Third (1.25 ratio)** progression:

| Token | Mobile | Desktop | Use Case |
|-------|--------|---------|----------|
| `--font-size-xs` | 11px | 12px | Captions, badges |
| `--font-size-sm` | 13px | 14px | Small text, labels |
| `--font-size-base` | 15px | 16px | Body text (base) |
| `--font-size-lg` | 18px | 20px | Large body, h6 |
| `--font-size-xl` | 22px | 24px | h5, lead text |
| `--font-size-2xl` | 27px | 30px | h4 |
| `--font-size-3xl` | 32px | 36px | h3 |
| `--font-size-4xl` | 40px | 45px | h2 |
| `--font-size-5xl` | 48px | 56px | h1 |
| `--font-size-6xl` | 60px | 70px | Display text |

All sizes use **fluid typography** (`clamp()`) for responsive scaling between mobile and desktop breakpoints.

### Font Weights

| Token | Value | Use Case |
|-------|-------|----------|
| `--font-weight-light` | 300 | Light text |
| `--font-weight-normal` | 400 | Body text (default) |
| `--font-weight-medium` | 500 | UI elements, h5/h6 |
| `--font-weight-semibold` | 600 | h3/h4, strong text |
| `--font-weight-bold` | 700 | h1/h2, emphasis |
| `--font-weight-extrabold` | 800 | h1 (optional) |
| `--font-weight-black` | 900 | Display text |

### Line Heights

| Token | Value | Use Case |
|-------|-------|----------|
| `--line-height-none` | 1 | Tight, no spacing |
| `--line-height-tight` | 1.2 | Headings |
| `--line-height-snug` | 1.35 | Subheadings |
| `--line-height-normal` | 1.5 | Standard text |
| `--line-height-relaxed` | 1.65 | Body text (comfortable) |
| `--line-height-loose` | 2 | Spacious text |

### Letter Spacing (Tracking)

Letter spacing uses a **tracking gradient** where larger type gets tighter tracking for improved visual cohesion:

| Token | Value | Use Case |
|-------|-------|----------|
| `--letter-spacing-display` | -0.04em | Display text (40px+), h1 |
| `--letter-spacing-tighter` | -0.05em | h2 section headers |
| `--letter-spacing-tight` | -0.025em | h3, h4 subsections |
| `--letter-spacing-normal` | 0 | Body text, h5, h6 |
| `--letter-spacing-wide` | 0.025em | Uppercase text |
| `--letter-spacing-wider` | 0.05em | All-caps labels |
| `--letter-spacing-widest` | 0.1em | Decorative uppercase |

**Heading Tracking Gradient:**
```
h1 → --tracking-display  (-0.04em)  Tightest for large display sizes
h2 → --tracking-tighter  (-0.05em)  Tight for section headers
h3 → --tracking-tight    (-0.025em) Moderate for subsections
h4 → --tracking-tight    (-0.025em) Moderate for subsections
h5 → --tracking-normal   (0)        Normal for body-adjacent
h6 → --tracking-wide     (0.025em)  Wide for uppercase treatment
```

**Rationale**: Large type (40px+) appears optically loose at default tracking. Progressively tighter tracking at larger sizes creates better visual cohesion without affecting body text readability.

### Font Families

| Token | Stack | Use Case |
|-------|-------|----------|
| `--font-family-sans` | System stack | Body text, UI |
| `--font-family-serif` | Georgia, Cambria... | Editorial content |
| `--font-family-mono` | JetBrains Mono, Fira Code... | Code blocks |
| `--font-family-display` | Defaults to sans | h1, hero text (customizable) |
| `--font-family-heading` | Defaults to display | h2-h4 section headings |

**Code Font Priority:**

The monospace stack prioritizes modern developer fonts with ligature support:

```
1. JetBrains Mono    ← Excellent 0O/1lI distinction, ligatures
2. Fira Code         ← Popular VS Code choice, ligatures
3. Cascadia Code     ← Windows Terminal default, ligatures
4. SF Mono           ← macOS system mono
5. Consolas          ← Windows fallback
6. Monaco, Menlo     ← Legacy fallbacks
7. Courier New       ← Universal fallback
```

Developers who install JetBrains Mono or Fira Code will see their preferred font by default.

**Custom Heading Fonts:**

**Option 1: Configure in bengal.toml (Recommended)**

The easiest way to add custom heading fonts is via Bengal's built-in font system:

```toml
# bengal.toml
[fonts]
display = "Instrument Serif:400,700"
```

This automatically:
- Downloads the font from Google Fonts during build
- Generates `@font-face` rules in `fonts.css`
- Creates `--font-display` CSS variable
- Connects to `--font-family-display` token

**Option 2: Override in Custom CSS**

For self-hosted fonts or more control:

```css
:root {
  /* Elegant serif for headings */
  --font-family-display: 'Instrument Serif', Georgia, serif;
}
```

**Recommended Fonts** (all OFL licensed, Google Fonts):

| Font | bengal.toml Config | Load Cost | Best For |
|------|-------------------|-----------|----------|
| Instrument Serif | `display = "Instrument Serif:400,700"` | ~25KB | Premium docs |
| Fraunces | `display = "Fraunces:400,700"` | ~35KB | Friendly technical |
| DM Serif Display | `display = "DM Serif Display:700"` | ~15KB | Traditional reference |
| Newsreader | `display = "Newsreader:400,700"` | ~30KB | Long-form content |

**Fallback Chain:**
```
--font-display (from bengal.toml) → --font-family-sans (system fonts)
```

**Note**: Default is system sans (zero load cost). Custom fonts add load time but provide visual identity.

## Usage

### In Components

Always use semantic tokens:

```css
.my-heading {
  font-size: var(--text-h1);
  font-weight: var(--weight-heading);
  line-height: var(--leading-heading);
  letter-spacing: var(--tracking-display);
}
```

### Semantic Token Names

**Headings:**
- `--text-h1` through `--text-h6`
- `--type-h1` through `--type-h6` (legacy alias)

**Body Text:**
- `--text-body` (base)
- `--text-body-sm` (small)
- `--text-body-lg` (large)

**UI Elements:**
- `--text-caption` (captions, small labels)
- `--text-label` (form labels)
- `--text-button` (button text)
- `--text-link` (link text)

**Special:**
- `--text-display` (large display text)
- `--text-lead` (lead paragraph)
- `--text-code` (code text)

**Weights:**
- `--weight-light`, `--weight-normal`, `--weight-medium`
- `--weight-semibold`, `--weight-bold`, `--weight-extrabold`
- `--weight-heading` (semantic: bold)
- `--weight-body` (semantic: normal)
- `--weight-strong` (semantic: semibold)

**Line Heights:**
- `--leading-heading` (tight, for headings)
- `--leading-body` (relaxed, for body text)
- `--leading-tight`, `--leading-normal`, `--leading-relaxed`, etc.

**Letter Spacing (Tracking):**
- `--tracking-display` (tightest, for h1/display text)
- `--tracking-tighter` (tight, for h2)
- `--tracking-tight` (moderate, for h3/h4)
- `--tracking-normal` (default, for body/h5)
- `--tracking-wide`, `--tracking-wider` (for uppercase/small caps)

**Font Families (Semantic):**
- `--font-sans`, `--font-serif`, `--font-mono` (base stacks)
- `--font-display` (for h1, hero text - customizable)
- `--font-heading` (for h2-h4 section headers)
- `--font-heading-display`, `--font-heading-section` (role-specific)

## Migration Guide

### Old → New

| Old Token | New Token |
|-----------|-----------|
| `--text-xs` | `--text-xs` (same) |
| `--text-base` | `--text-body` or `--text-base` |
| `--type-h1` | `--text-h1` or `--type-h1` (both work) |
| `--font-bold` | `--weight-bold` or `--font-bold` (both work) |
| `--leading-relaxed` | `--leading-relaxed` (same) |

**Backward Compatibility:** Old token names still work via aliases in `semantic.css`, but prefer the new names for clarity.

## Key Improvements

1. **Single Source of Truth**: All sizes defined in one place (`typography.css`)
2. **Consistent Naming**: Clear, predictable token names
3. **Fluid Typography**: Responsive sizing with `clamp()`
4. **Semantic Mapping**: Foundation → Semantic → Component
5. **No Hardcoded Values**: Everything uses tokens
6. **Better Documentation**: Clear scale and usage guidelines

## Files Changed

- ✅ `tokens/typography.css` - New foundation tokens
- ✅ `tokens/semantic.css` - Updated to reference new tokens
- ✅ `base/typography.css` - Rewritten to use new tokens
- ✅ `style.css` - Added typography.css import

## Testing

After migration, verify:
- [ ] All headings render correctly
- [ ] Body text is readable
- [ ] Links and buttons use correct sizes
- [ ] Mobile responsive sizing works
- [ ] No hardcoded font sizes remain
- [ ] All components use tokens (not direct values)
