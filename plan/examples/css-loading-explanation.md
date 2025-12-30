# How Directive Base CSS Works: Crystal Clear

## The Loading Order

```
1. Bengal Base CSS (auto-injected)     ← ~50 lines per directive
   └── Handles: show/hide, resets, accessibility

2. Theme CSS (theme's style.css)       ← Theme's full aesthetic
   └── Handles: EVERYTHING visual
```

## CSS Specificity Strategy

**Base CSS uses SAME specificity as theme CSS.**

This works because:
- Base CSS loads FIRST
- Theme CSS loads SECOND  
- Later CSS wins for same specificity (CSS cascade)

```css
/* Base CSS (loaded first) */
.tab-pane { display: none; }
.tab-pane.active { display: block; }

/* Theme CSS (loaded second) */
.tab-pane.active {
  display: block;              /* Same as base - no conflict */
  animation: fadeIn 0.2s;      /* Theme adds animation */
}
```

## What Base CSS Does NOT Do

| ❌ Base CSS Avoids | Why |
|-------------------|-----|
| Layout (`display: flex` on containers) | Themes have different layout opinions |
| Colors | Themes define their palette |
| Borders, shadows | Aesthetic choices |
| Typography | Theme's font system |
| Animations | Bengal's glow vs minimal fade vs none |
| Spacing (margin, padding) | Theme's spacing scale |

## What Base CSS DOES Do

| ✅ Base CSS Handles | Why Universal |
|--------------------|---------------|
| `.tab-pane { display: none }` | ALL tabs need hide |
| `.tab-pane.active { display: block }` | ALL tabs need show |
| List style reset | ALL tabs in prose get contaminated |
| Focus-visible outline | Accessibility requirement |
| prefers-reduced-motion | Accessibility requirement |

## Concrete Example: How Default Theme Uses Base

### Before (Current default theme tabs.css)

```css
/* Lines 1-50ish handle functional stuff */
.tab-nav { list-style: none; margin: 0; padding: 0; }
.tab-pane { display: none; }
.tab-pane.active { display: block; }

/* Lines 51-528 are Bengal's aesthetic */
.tabs { position: relative; border: 1px solid var(--color-border-light); ... }
.tab-nav li.active a::after { /* glowing edge animation */ }
/* ... 400 more lines of beauty ... */
```

### After (With base CSS)

**bengal/assets/css/directives/tabs.css (auto-loaded):**
```css
/* Just the functional ~40 lines */
.tab-nav { list-style: none; margin: 0; padding: 0; }
.tab-pane { display: none; }
.tab-pane.active { display: block; }
/* focus-visible, reduced-motion */
```

**themes/default/assets/css/components/tabs.css:**
```css
/* REMOVED: functional lines (now in base) */

/* KEPT: ALL the aesthetic (~490 lines) */
.tabs { position: relative; border: 1px solid var(--color-border-light); ... }
.tab-nav { display: flex; background-color: var(--color-bg-secondary); ... }
.tab-nav li.active a::after { /* glowing edge animation */ }
/* ... all the Bengal beauty stays here ... */
```

## The Key Insight

**Base CSS is NOT a "default theme lite."**

Base CSS is the **minimum functional requirements** that make directives work at all:
- Show/hide logic
- Prose contamination fixes  
- Accessibility basics

Everything else—including basic layout—is a **theme decision**.

## Why This Works for Default Theme

Default theme changes:
- **Remove**: ~40 lines of functional CSS (now in base)
- **Keep**: ~490 lines of aesthetic CSS
- **Net change**: Delete some redundant lines

Default theme does NOT need to:
- Refactor its layout approach
- Change its visual design
- Override base CSS decisions

Because base CSS makes **zero layout opinions**.

## Why This Works for New Themes

New theme author writes:
- **~40-100 lines** for working tabs
- Focus on their aesthetic
- Don't need to discover show/hide requirements
- Don't need to fix prose contamination bugs
- Don't need to add accessibility features

## Visual: What Each Layer Provides

```
┌────────────────────────────────────────────────────────────┐
│ Default Theme (490 lines)                                  │
│ ┌────────────────────────────────────────────────────────┐ │
│ │ Glowing edges, animations, palette variants,           │ │
│ │ dark mode, responsive, code-tabs, badges...            │ │
│ └────────────────────────────────────────────────────────┘ │
│ ┌────────────────────────────────────────────────────────┐ │
│ │ Layout: flex nav, relative container, border-radius    │ │
│ └────────────────────────────────────────────────────────┘ │
│ ┌────────────────────────────────────────────────────────┐ │
│ │ Colors: --color-border-light, --color-primary, etc.    │ │
│ └────────────────────────────────────────────────────────┘ │
└────────────────────────────────────────────────────────────┘
                              ↑ extends
┌────────────────────────────────────────────────────────────┐
│ Base CSS (40 lines) - AUTO LOADED                          │
│ ┌────────────────────────────────────────────────────────┐ │
│ │ .tab-pane { display: none }                            │ │
│ │ .tab-pane.active { display: block }                    │ │
│ │ .tab-nav { list-style: none; margin: 0; padding: 0 }   │ │
│ │ focus-visible, reduced-motion                          │ │
│ └────────────────────────────────────────────────────────┘ │
└────────────────────────────────────────────────────────────┘
```

```
┌────────────────────────────────────────────────────────────┐
│ Minimal Community Theme (40 lines)                         │
│ ┌────────────────────────────────────────────────────────┐ │
│ │ Simple aesthetic: border, background, active state     │ │
│ └────────────────────────────────────────────────────────┘ │
│ ┌────────────────────────────────────────────────────────┐ │
│ │ Layout: flex nav (theme's choice)                      │ │
│ └────────────────────────────────────────────────────────┘ │
│ ┌────────────────────────────────────────────────────────┐ │
│ │ Colors: theme's palette                                │ │
│ └────────────────────────────────────────────────────────┘ │
└────────────────────────────────────────────────────────────┘
                              ↑ extends
┌────────────────────────────────────────────────────────────┐
│ Base CSS (40 lines) - AUTO LOADED (same as above)          │
└────────────────────────────────────────────────────────────┘
```

## Summary

| Question | Answer |
|----------|--------|
| Does base CSS dictate layout? | **No** |
| Does default theme need refactoring? | **Minimal** (remove ~40 redundant lines) |
| Does default theme keep its aesthetic? | **100%** |
| What does base CSS actually do? | Show/hide, list reset, accessibility |
| How much does a new theme need to write? | ~40-100 lines for working directives |
