# Component Interaction Patterns

This document defines the interaction patterns used in Bengal's theme components.
Each pattern has specific naming conventions to make the implementation clear.

## Pattern Overview

| Pattern | Trigger | Browser API | JS Role | CSS Role |
|---------|---------|-------------|---------|----------|
| **Dialog** | Click | `<dialog>` | Minimal (close on link click) | Styling, animations |
| **Popover** | Click | `[popover]` | Positioning, state persistence | Styling, animations |
| **Hover Menu** | Hover | None (JS) | State management, a11y | Positioning, styling |
| **CSS State** | Click (URL) | `:target` | None or sync only | Full control |

---

## 1. Dialog Pattern (`dialog-*`)

**Use for:** Full-screen or modal experiences that trap focus.

**Browser handles:** Focus trap, escape key, backdrop, `inert` on background.

**Naming:**
- HTML: `<dialog id="*-dialog" class="*-dialog">`
- CSS: `.mobile-nav-dialog`, `.search-dialog`
- JS: Minimal - just for closing on events

**Example:**
```html
<dialog id="mobile-nav-dialog" class="mobile-nav-dialog">
  <form method="dialog">
    <button type="submit" value="close">Close</button>
  </form>
</dialog>
<button onclick="document.getElementById('mobile-nav-dialog').showModal()">
  Open
</button>
```

**Files:**
- `enhancements/mobile-nav.js` - Minimal dialog helpers
- `layouts/header.css` - `.mobile-nav-dialog` styles

**Other Dialog Components:**
- **Search Modal** (`#search-modal`) - Command palette search (Cmd/Ctrl+K)
  - Files: `core/search.js`, `components/search-modal.css`
  - Opens via: keyboard shortcut, trigger buttons
  - Uses: `showModal()` / `close()` native methods

- **Image Lightbox** (`#lightbox-dialog`) - Full-screen image viewer
  - Files: `enhancements/lightbox.js`, `components/interactive.css`
  - Opens via: clicking content images with `[data-lightbox]`
  - Uses: `showModal()` / `close()` native methods
  - Features: Arrow key navigation between images

---

## 2. Popover Pattern (`popover-*` or `--popover`)

**Use for:** Click-triggered overlays with light dismiss (settings, menus).

**Browser handles:** Show/hide, light dismiss, escape key, top layer.

**JS handles:** Positioning relative to trigger, state persistence.

**Naming:**
- HTML: `<div id="*-menu" popover class="*--popover">`
- CSS: `.*--popover` suffix indicates popover behavior
- JS: `setupPopoverMenus()`, `positionPopover()`
- Data: `[popovertarget="menu-id"]` on trigger

**Example:**
```html
<button popovertarget="theme-menu">Appearance</button>
<div id="theme-menu" popover class="theme-dropdown__menu--popover">
  <!-- menu content -->
</div>
```

**Files:**
- `core/theme.js` - Popover positioning + theme logic
- `layouts/header.css` - `.theme-dropdown__menu--popover` styles
- `enhancements/action-bar.js` - Share dropdown positioning + actions
- `components/action-bar.css` - `.action-bar-share-dropdown--popover` styles
- `components/page-hero.css` - `.page-hero__share-dropdown--popover` styles

**Components Using Popover:**
- Theme menu (header)
- Share dropdown (action-bar)
- Share dropdown (page-hero)
- Metadata panel (action-bar)

---

## 3. Hover Menu Pattern (`hover-*` or `[data-state]`)

**Use for:** Navigation dropdowns that open on hover.

**JS handles:** Open/close state, hover timing, keyboard navigation.

**CSS handles:** Positioning (absolute within parent), visibility.

**Naming:**
- HTML: `[data-state="open|closed"]` on container and trigger
- CSS: `[data-state="open"]` selectors for visibility
- JS: Event listeners for mouseenter/mouseleave
- Classes: `.has-dropdown`, `.submenu`

**Example:**
```html
<li class="has-dropdown" data-state="closed">
  <a href="/docs" data-state="closed" aria-haspopup="true">Docs</a>
  <ul class="submenu"><!-- items --></ul>
</li>
```

**Files:**
- `core/nav-dropdown.js` - Hover state management
- `layouts/header.css` - `.submenu` positioning
- `components/navigation.css` - Navigation styles

---

## 3b. Click Menu Pattern (`aria-expanded`) - DEPRECATED

> **Note:** This pattern has been superseded by native `[popover]` for most use cases.
> Share dropdowns in `action-bar.html` and `page-hero/_share-dropdown.html` now use popover.

**Use for:** Legacy components not yet migrated to popover.

**JS handles:** Toggle aria-expanded, show/hide menu.

**CSS handles:** Positioning (absolute), visibility based on aria-expanded.

**Migrated to Popover:**
- Share dropdown (`partials/page-hero/_share-dropdown.html`) → `*--popover`
- Action bar share (`partials/action-bar.html`) → `*--popover`
- Action bar metadata panel → `*--popover`

**Why Popover is Better:**
- Browser handles light dismiss (click outside closes)
- Browser handles escape key
- Top layer (no z-index battles)
- Native focus management

---

## 4. CSS State Machine Pattern (`:target`)

**Use for:** Components that can work without JS (tabs, accordions).

**Browser handles:** `:target` pseudo-class based on URL fragment.

**CSS handles:** Visibility via `:target`, active states via `:has()`.

**JS role:** Optional - sync across instances, enhanced keyboard nav.

**Naming:**
- HTML: `id` on panels, `href="#panel-id"` on triggers
- CSS: `*-native.css` suffix for CSS-only implementations
- Data: `[data-sync-group]` for optional JS sync

**Example:**
```html
<div class="tabs" role="tablist">
  <nav class="tab-nav">
    <a href="#tab-python" role="tab">Python</a>
    <a href="#tab-js" role="tab">JavaScript</a>
  </nav>
  <div class="tab-content">
    <section id="tab-python" class="tab-pane">...</section>
    <section id="tab-js" class="tab-pane">...</section>
  </div>
</div>
```

**Files:**
- `components/tabs-native.css` - CSS-only tab logic
- `enhancements/tabs.js` - Optional sync enhancement

---

## File Naming Conventions

### CSS Files
- `*-native.css` - CSS-only implementation (no JS required)
- Regular names - May require JS enhancement

### JS Files  
- `core/*.js` - Essential functionality, loads on every page
- `enhancements/*.js` - Progressive enhancement, can be deferred

### Data Attributes
- `data-state="open|closed"` - JS-managed visibility state
- `data-sync-group="key"` - Sync state across instances
- `[popover]` - Native popover API
- `[popovertarget="id"]` - Popover trigger

---

## When to Use Each Pattern

```
Need focus trap + backdrop?
  └─ YES → Use <dialog>
  └─ NO ↓

Triggered by hover?
  └─ YES → Use Hover Menu (JS + data-state)
  └─ NO ↓

Needs light dismiss (click outside closes)?
  └─ YES → Use [popover]
  └─ NO ↓

Can work with URL fragments?
  └─ YES → Use CSS State Machine (:target)
  └─ NO → Use JS state management
```

---

## Migration Notes

When CSS Anchor Positioning (`anchor-name`, `position-anchor`) has broader support,
popover positioning can move from JS to pure CSS. The `--popover` class suffix
will indicate which components to update.
