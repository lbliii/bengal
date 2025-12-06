# Bengal Default Theme - JavaScript

**Version:** 2.0  
**Dependencies:** Lunr.js (search only)  
**Browser Support:** ES6+ (Chrome 90+, Firefox 88+, Safari 14+)

---

## Overview

All JavaScript is written in vanilla ES6+ with no framework dependencies. The code follows progressive enhancement principles - all core functionality works without JavaScript.

---

## Progressive Enhancement System

Bengal provides a unified **Progressive Enhancement Architecture** for declaring and managing JavaScript enhancements.

### Philosophy

> "Layered enhancement — HTML that works, CSS that delights, JS that elevates"

### Quick Start

Declare enhancements using the `data-bengal` attribute:

```html
<!-- Theme toggle -->
<button data-bengal="theme-toggle">Toggle Theme</button>

<!-- Tabs -->
<div data-bengal="tabs">
  <ul class="tab-nav">
    <li><a data-tab-target="tab-1">Tab 1</a></li>
  </ul>
  <div id="tab-1" class="tab-pane">Content</div>
</div>

<!-- Table of contents with scroll spy -->
<nav data-bengal="toc" data-spy="true">
  <a data-toc-item="#section-1">Section 1</a>
</nav>
```

### Configuration via Data Attributes

Options are passed via additional `data-*` attributes:

```html
<nav data-bengal="toc" data-spy="true" data-offset="80">
```

- **Boolean values**: `data-spy="true"` or just `data-spy`
- **Numbers**: `data-offset="80"`
- **JSON**: `data-config='{"key": "value"}'`

### Available Enhancements

| Enhancement | Description | Options |
|-------------|-------------|---------|
| `theme-toggle` | Dark/light theme switching | `default` |
| `mobile-nav` | Mobile slide-out navigation | `closeOnClick`, `closeOnEscape` |
| `tabs` | Tabbed content panels | `defaultTab` |
| `toc` | Table of contents with scroll spy | `spy`, `offset`, `smooth` |

### Enhancement Loader API

```javascript
// Register a custom enhancement
Bengal.enhance.register('my-feature', function(el, options) {
  // el: The element with data-bengal="my-feature"
  // options: Parsed data attributes
  el.addEventListener('click', () => console.log('Enhanced!'));
});

// List registered enhancements
Bengal.enhance.list();  // ['theme-toggle', 'tabs', 'toc', ...]

// Check if an element is enhanced
Bengal.enhance.isEnhanced(element);  // true/false

// Manually enhance all unenhanced elements
Bengal.enhance.enhanceAll();

// Enhance a specific element
Bengal.enhance.enhanceElement(element);
```

### Creating Custom Enhancements

Create a file in `enhancements/my-feature.js`:

```javascript
(function() {
  'use strict';

  if (!window.Bengal || !window.Bengal.enhance) {
    console.warn('[Bengal] Enhancement system not loaded');
    return;
  }

  Bengal.enhance.register('my-feature', function(el, options) {
    // Your enhancement logic here
    console.log('Enhancing:', el, 'with options:', options);
  });
})();
```

Then use it:

```html
<div data-bengal="my-feature" data-option1="value">Content</div>
```

### Lazy Loading

Non-preloaded enhancements are automatically lazy-loaded when their elements are detected. Scripts are fetched from `/assets/js/enhancements/{name}.js`.

### Configuration

```toml
# bengal.toml (optional)
[enhancements]
watch_dom = true   # Watch for dynamic content (MutationObserver)
debug = false      # Enable debug logging
```

See [`enhancements/README.md`](enhancements/README.md) for full documentation.

---

## Linting

### Biome (Recommended)

A `biome.json` configuration is included for linting JavaScript files:

```bash
# Install Biome (Rust-based, fast, no Node.js required)
brew install biome
# or: cargo install @biomejs/biome

# Lint all JS files
biome check .

# Lint and auto-fix
biome check --apply .
```

### What It Catches

- ❌ **Undeclared variables** (strict mode errors)
- ⚠️ **Unused variables**
- ⚠️ **Use of `var`** (prefer `const`/`let`)
- Recommended best practices

---

## Architecture

### Directory Structure

```
js/
├── utils.js                    # Foundation utilities (load first)
├── bengal-enhance.js           # Progressive enhancement registry
├── main.js                     # Core initialization
│
├── core/                       # Always-loaded modules
│   ├── theme.js               # Theme/palette switching
│   ├── search.js              # Full-text search with Lunr
│   ├── nav-dropdown.js        # Navigation dropdowns
│   └── session-path-tracker.js # Session tracking
│
├── enhancements/              # Core enhancements (explicitly loaded)
│   ├── interactive.js         # Docs nav, back-to-top, scroll spy
│   ├── tabs.js                # Tab component
│   ├── toc.js                 # Table of contents
│   ├── mobile-nav.js          # Mobile navigation
│   ├── action-bar.js          # Action bar component
│   ├── copy-link.js           # Copy heading links
│   ├── holo.js                # Holographic effects
│   ├── lightbox.js            # Image lightbox (feature-gated)
│   ├── lazy-loaders.js        # Lazy loading (Mermaid, D3)
│   └── data-table.js          # Data table enhancements
│
├── vendor/                    # Third-party libraries
│   ├── lunr.min.js           # Full-text search
│   └── tabulator.min.js      # Data tables
│
├── graph-*.js                 # Graph visualization (lazy-loaded)
├── mermaid-*.js               # Mermaid diagrams (lazy-loaded)
│
└── biome.json                 # Linting configuration
```

### Loading Order

Scripts load in this order (configured in `base.html` and `js_bundler.py`):

1. **`utils.js`** - Core utilities (`BengalUtils` namespace)
2. **`bengal-enhance.js`** - Enhancement registry
3. **`core/*.js`** - Always-needed functionality
4. **`main.js`** - Core initialization
5. **`enhancements/*.js`** - Interactive features

### Responsibility Matrix

| Feature | Module | Trigger |
|---------|--------|---------|
| Theme switching | `core/theme.js` | Auto-init |
| Search | `core/search.js` | Auto-init |
| Nav dropdowns | `core/nav-dropdown.js` | Auto-init |
| Code copy buttons | `main.js` | Auto-init |
| External link icons | `main.js` | Auto-init |
| Docs nav toggle | `enhancements/interactive.js` | `data-bengal="docs-nav"` |
| Back to top | `enhancements/interactive.js` | Auto-init |
| Reading progress | `enhancements/interactive.js` | Auto-init |
| TOC + scroll spy | `enhancements/toc.js` | `data-bengal="toc"` |
| Tabs | `enhancements/tabs.js` | `data-bengal="tabs"` |
| Mobile nav | `enhancements/mobile-nav.js` | Auto-init |
| Lightbox | `enhancements/lightbox.js` | Feature-gated |
| Holo effects | `enhancements/holo.js` | Auto-init |

### Module Pattern

Each JavaScript file uses an IIFE (Immediately Invoked Function Expression) module pattern:

```javascript
/**
 * Module description
 * @module ModuleName
 */
(function() {
  'use strict';

  // Module state
  let state = {};

  /**
   * Private helper function
   * @private
   */
  function privateFunction() {
    // Implementation
  }

  /**
   * Public initialization function
   * @public
   */
  function init() {
    // Setup code
  }

  // Auto-initialize on DOM ready
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
```

### Benefits

- **Encapsulation**: No global namespace pollution
- **Privacy**: Private functions not exposed
- **Performance**: Single execution context
- **Auto-init**: Runs when DOM is ready

---

## Files

### Core Files

#### `main.js`
**Purpose:** Entry point and module coordinator

**Features:**
- Smooth scrolling setup
- External link handling
- Code copy buttons
- Lazy loading
- TOC highlighting
- Keyboard detection

**Key Functions:**
```javascript
setupSmoothScroll()     // Smooth anchor navigation
setupExternalLinks()    // Add icons to external links
setupCodeCopyButtons()  // Copy button for code blocks
setupLazyLoading()      // Intersection Observer lazy loading
setupTOCHighlight()     // Table of contents scroll spy
setupKeyboardDetection() // Add .user-is-tabbing class
```

**Usage:**
```html
<script src="assets/js/main.js"></script>
```

---

#### `theme-toggle.js`
**Purpose:** Appearance control (mode + palette)

**Features:**
- Mode selection: System, Light, Dark
- Palette selection via dropdown (e.g., `snow-lynx`)
- System preference detection (`prefers-color-scheme`)
- localStorage persistence for mode (`bengal-theme`) and palette (`bengal-palette`)
- Emits `themechange` and `palettechange` events

**Key Functions (exposed as `window.BengalTheme`):**
```javascript
get()                  // Get resolved theme ('light'|'dark') respecting 'system'
set(theme)             // Set theme ('system'|'light'|'dark')
toggle()               // Optional: toggle between light/dark if you add a button
getPalette()           // Get current palette key or ''
setPalette(palette)    // Set color palette key or '' to clear
```

**Storage:**
```javascript
localStorage.getItem('bengal-theme')   // 'system' | 'light' | 'dark'
localStorage.getItem('bengal-palette') // '' | palette key
```

**Usage (default theme):**
```html
<!-- Dropdown-only control -->
<div class="theme-dropdown">
  <button class="theme-dropdown__button" aria-haspopup="menu" aria-expanded="false">Theme</button>
  <ul class="theme-dropdown__menu" role="menu">
    <li role="menuitem"><button data-appearance="system">System</button></li>
    <li role="menuitem"><button data-appearance="light">Light</button></li>
    <li role="menuitem"><button data-appearance="dark">Dark</button></li>
    <li role="separator" class="separator"></li>
    <li role="menuitem"><button data-palette="">Default</button></li>
    <li role="menuitem"><button data-palette="snow-lynx">Snow Lynx</button></li>
  </ul>
  <script src="assets/js/theme-toggle.js"></script>
```

Note: The legacy single-button `.theme-toggle` is no longer used in the default markup. If present, the script will still wire it up for backwards compatibility.

---

#### `toc.js`
**Purpose:** Table of contents with scroll spy

**Features:**
- Sticky sidebar TOC
- Active item highlighting on scroll
- Smooth scroll to heading
- Collapsible groups
- Reading progress bar
- State persistence (localStorage)
- Keyboard navigation

**Key Functions:**
```javascript
updateProgress()     // Update reading progress bar
updateActiveItem()   // Highlight current section
updateOnScroll()     // Debounced scroll handler
toggleGroup(group)   // Collapse/expand TOC group
initGroupToggles()   // Setup group collapse buttons
initSmoothScroll()   // Setup anchor link scrolling
initKeyboardNavigation() // Arrow key navigation
```

**State Management:**
```javascript
// Persists in localStorage
{
  collapsedGroups: ['group-1', 'group-2'],
  activeMode: 'default' | 'compact'
}
```

**Usage:**
```html
<div class="toc-sidebar">
  <nav class="toc-nav">
    <!-- TOC items -->
  </nav>
</div>
<script src="assets/js/toc.js"></script>
```

---

#### `search.js`
**Purpose:** Full-text search with Lunr.js

**Features:**
- Full-text search across all pages
- Fuzzy matching
- Result grouping (by section/type)
- Search filters (section, type, tag, author)
- Highlighted search terms
- Keyboard navigation (↑↓ Enter Esc)

**Key Functions:**
```javascript
loadSearchIndex()      // Load search index JSON
search(query, filters) // Perform search
groupResults(results)  // Group by section
applyFilters(results, filters) // Filter results
highlightMatches(text, terms)  // Highlight search terms
createHighlightedExcerpt(text, terms, length) // Generate excerpt
```

**Search Index Format:**
```json
{
  "documents": [
    {
      "id": "/path/to/page/",
      "title": "Page Title",
      "content": "Page content...",
      "section": "Documentation",
      "type": "doc",
      "tags": ["tag1", "tag2"],
      "author": "Author Name",
      "url": "/path/to/page/"
    }
  ]
}
```

**Usage:**
```html
<input type="search" class="search__input" placeholder="Search...">
<div class="search__results"></div>
<script src="assets/js/lunr.min.js"></script>
<script src="assets/js/search.js"></script>
```

---

#### `tabs.js`
**Purpose:** Tab component behavior

**Features:**
- Tab switching
- Keyboard navigation (← → Home End)
- State persistence (localStorage)
- ARIA attributes
- Code tabs support

**Key Functions:**
```javascript
initTabs()           // Initialize all tab containers
switchTab(container, index) // Switch to tab by index
handleTabKeyboard(e, tabLinks, currentIndex) // Keyboard navigation
saveTabState(containerId, index) // Save active tab
restoreTabState(containerId)     // Restore active tab
```

**Keyboard Controls:**
- `←` / `→` - Navigate tabs
- `Home` - First tab
- `End` - Last tab
- `Enter` / `Space` - Activate tab

**Usage:**
```html
<div class="tabs" id="my-tabs">
  <ul class="tab-nav" role="tablist">
    <li role="presentation">
      <a href="#tab1" role="tab" aria-selected="true">Tab 1</a>
    </li>
  </ul>
  <div class="tab-content">
    <div id="tab1" class="tab-pane active" role="tabpanel">
      Content 1
    </div>
  </div>
</div>
<script src="assets/js/tabs.js"></script>
```

---

#### `lightbox.js`
**Purpose:** Image zoom gallery

**Features:**
- Click to zoom images
- Image navigation (prev/next)
- Keyboard navigation (← → Esc)
- Smooth animations
- Image captions
- Responsive

**Key Functions:**
```javascript
createLightbox()       // Create lightbox DOM elements
openLightbox(img)      // Open lightbox with image
closeLightbox()        // Close lightbox
navigateImages(direction) // Navigate (1 or -1)
handleKeyboard(e)      // Keyboard controls
```

**Keyboard Controls:**
- `Esc` - Close lightbox
- `←` - Previous image
- `→` - Next image

**Usage:**
```html
<img src="image.jpg" alt="Description" data-lightbox>
<script src="assets/js/lightbox.js"></script>
```

---

#### `interactive.js`
**Purpose:** Interactive UI features

**Features:**
- Back to top button
- Reading progress bar
- Smooth scrolling
- Scroll spy for navigation
- Docs navigation (expand/collapse)
- Mobile sidebar toggle

**Key Functions:**
```javascript
setupBackToTop()        // Show/hide back-to-top button
setupReadingProgress()  // Update reading progress bar
setupSmoothScroll()     // Smooth anchor navigation
setupScrollSpy()        // Highlight active nav items
setupDocsNavigation()   // Docs sidebar expand/collapse
setupMobileSidebar()    // Mobile sidebar toggle
```

**Usage:**
```html
<button class="back-to-top" aria-label="Back to top">↑</button>
<div class="reading-progress">
  <div class="reading-progress__fill"></div>
</div>
<script src="assets/js/interactive.js"></script>
```

---

#### `mobile-nav.js`
**Purpose:** Responsive mobile navigation

**Features:**
- Hamburger menu toggle
- Smooth animations
- Body scroll lock when open
- Click outside to close
- Esc key to close
- Submenu toggle

**Key Functions:**
```javascript
openNav()           // Open mobile navigation
closeNav()          // Close mobile navigation
toggleNav()         // Toggle open/closed
handleEscape(e)     // Close on Esc key
handleOutsideClick(e) // Close on outside click
```

**Usage:**
```html
<button class="mobile-nav-toggle" aria-label="Toggle menu">
  <svg>...</svg>
</button>
<nav class="mobile-nav">
  <ul>
    <li><a href="/">Home</a></li>
  </ul>
</nav>
<script src="assets/js/mobile-nav.js"></script>
```

---

#### `copy-link.js`
**Purpose:** Copy heading anchor links

**Features:**
- Copy heading permalinks
- Visual feedback (✓ animation)
- Keyboard accessible
- Clipboard API with fallback

**Key Functions:**
```javascript
setupCopyLinkButtons()  // Initialize all copy buttons
copyToClipboard(text, button) // Copy text to clipboard
showCopySuccess(button) // Show success animation
showCopyError(button)   // Show error state
```

**Usage:**
```html
<h2 id="heading">
  Heading
  <button class="copy-link" data-url="#heading" aria-label="Copy link">
    🔗
  </button>
</h2>
<script src="assets/js/copy-link.js"></script>
```

---

### Third-Party Libraries

#### `lunr.min.js`
**Purpose:** Full-text search engine

**Version:** 2.3.9  
**License:** MIT  
**Size:** ~8KB minified  
**Docs:** https://lunrjs.com/

**Why Lunr:**
- Client-side search (no server required)
- Fast indexing and search
- Fuzzy matching
- Small footprint
- No dependencies

---

## Performance

### Optimization Techniques

**1. Event Delegation**
```javascript
// ✅ Good: Single listener
document.addEventListener('click', (e) => {
  if (e.target.matches('.button')) {
    // Handle click
  }
});

// ❌ Bad: Multiple listeners
document.querySelectorAll('.button').forEach(btn => {
  btn.addEventListener('click', handler);
});
```

**2. Debouncing**
```javascript
let timeout;
window.addEventListener('scroll', () => {
  clearTimeout(timeout);
  timeout = setTimeout(updateScrollPosition, 100);
});
```

**3. Lazy Loading**
```javascript
// Load search index only when needed
let searchIndex = null;
async function loadSearchIndex() {
  if (!searchIndex) {
    const response = await fetch('/search-index.json');
    searchIndex = await response.json();
  }
  return searchIndex;
}
```

**4. IntersectionObserver**
```javascript
// Efficient visibility detection
const observer = new IntersectionObserver(entries => {
  entries.forEach(entry => {
    if (entry.isIntersecting) {
      // Element is visible
    }
  });
});
```

---

## Accessibility

### ARIA Attributes

All interactive components use proper ARIA:

```javascript
// Tab component
tabLink.setAttribute('role', 'tab');
tabLink.setAttribute('aria-selected', isActive);
tabLink.setAttribute('aria-controls', panelId);

// Expandable sections
button.setAttribute('aria-expanded', isOpen);
button.setAttribute('aria-controls', contentId);

// Mobile menu
navToggle.setAttribute('aria-label', 'Toggle navigation menu');
navToggle.setAttribute('aria-expanded', isOpen);
```

### Keyboard Navigation

All components support keyboard:

```javascript
element.addEventListener('keydown', (e) => {
  switch(e.key) {
    case 'Enter':
    case ' ':
      e.preventDefault();
      activate();
      break;
    case 'Escape':
      close();
      break;
    case 'ArrowUp':
    case 'ArrowDown':
      navigate(e.key === 'ArrowDown' ? 1 : -1);
      break;
  }
});
```

### Focus Management

```javascript
// Trap focus in modal
function trapFocus(container) {
  const focusable = container.querySelectorAll(
    'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
  );
  const firstFocusable = focusable[0];
  const lastFocusable = focusable[focusable.length - 1];

  container.addEventListener('keydown', (e) => {
    if (e.key === 'Tab') {
      if (e.shiftKey && document.activeElement === firstFocusable) {
        e.preventDefault();
        lastFocusable.focus();
      } else if (!e.shiftKey && document.activeElement === lastFocusable) {
        e.preventDefault();
        firstFocusable.focus();
      }
    }
  });
}
```

---

## Browser Compatibility

### Supported Features

✅ **Modern browsers (ES6+)**
- Arrow functions
- Template literals
- Destructuring
- `const`/`let`
- Promises
- `async`/`await`
- `classList`
- `querySelector`/`querySelectorAll`

✅ **APIs used:**
- IntersectionObserver
- Clipboard API (with fallback)
- localStorage
- matchMedia (dark mode)
- fetch (search index)

### Fallbacks

**Clipboard API:**
```javascript
async function copyToClipboard(text) {
  if (navigator.clipboard) {
    await navigator.clipboard.writeText(text);
  } else {
    // Fallback for older browsers
    const textarea = document.createElement('textarea');
    textarea.value = text;
    document.body.appendChild(textarea);
    textarea.select();
    document.execCommand('copy');
    document.body.removeChild(textarea);
  }
}
```

**IntersectionObserver:**
```javascript
if ('IntersectionObserver' in window) {
  // Use IntersectionObserver
} else {
  // Fallback to scroll events
}
```

---

## Development

### Adding New Modules

**Recommended: Use the Progressive Enhancement Pattern**

1. **Create enhancement file** (`enhancements/new-feature.js`)

```javascript
/**
 * Bengal Enhancement: New Feature
 * Description of what this enhancement does
 * @requires bengal-enhance.js
 */
(function() {
  'use strict';

  if (!window.Bengal || !window.Bengal.enhance) {
    console.warn('[Bengal] Enhancement system not loaded');
    return;
  }

  Bengal.enhance.register('new-feature', function(el, options) {
    // el: Element with data-bengal="new-feature"
    // options: Parsed data-* attributes

    console.log('Enhanced:', el, options);
  });
})();
```

2. **Use in HTML**

```html
<div data-bengal="new-feature" data-option="value">Content</div>
```

The enhancement will be lazy-loaded automatically when the element is detected.

---

**Alternative: Standalone Module Pattern** (for complex features)

1. **Create module file** (`new-feature.js`)

```javascript
/**
 * New Feature Module
 * Description of what this module does
 * @module NewFeature
 */
(function() {
  'use strict';

  /**
   * Initialize the new feature
   * @public
   */
  function init() {
    console.log('New feature initialized');
  }

  // Auto-initialize
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }

  // Optional: Register with enhancement system for hybrid approach
  if (window.Bengal && window.Bengal.enhance) {
    Bengal.enhance.register('new-feature', function(el, options) {
      // Enhancement-specific init
    }, { override: true });
  }
})();
```

2. **Add to base template**

```html
<script src="{{ url_for('assets/js/new-feature.js') }}" defer></script>
```

3. **Test**

```bash
# Open in browser
python -m http.server 8000
# Navigate to test page
```

### Code Style

**Naming Conventions:**
```javascript
// Variables and functions: camelCase
let userName = 'John';
function getUserName() {}

// Constants: UPPER_SNAKE_CASE
const API_KEY = 'abc123';
const MAX_RETRIES = 3;

// Classes (if used): PascalCase
class UserManager {}
```

**Comments:**
```javascript
/**
 * Function description
 *
 * @param {string} name - Parameter description
 * @param {number} age - Parameter description
 * @returns {Object} Return value description
 *
 * @example
 * createUser('John', 30);
 */
function createUser(name, age) {
  // Implementation comment
  return { name, age };
}
```

---

## Testing

### Manual Testing

**Checklist:**
- [ ] Works without JavaScript enabled
- [ ] Keyboard navigation (Tab, Enter, Arrows, Esc)
- [ ] Screen reader (VoiceOver/NVDA)
- [ ] Mobile touch events
- [ ] Multiple browsers (Chrome, Firefox, Safari)
- [ ] Different viewport sizes
- [ ] Light and dark modes
- [ ] localStorage persistence

### Browser Console Testing

```javascript
// Test theme toggle
window.ThemeToggle.setTheme('dark');
window.ThemeToggle.getTheme(); // 'dark'

// Test search
window.Search.search('bengal').then(results => {
  console.log('Results:', results);
});

// Test TOC
window.TOC.updateProgress();
console.log('Current progress:', window.TOC.getProgress());
```

### Performance Testing

```javascript
// Measure execution time
console.time('feature-init');
initFeature();
console.timeEnd('feature-init');

// Check memory usage
console.memory; // Chrome only

// Profile functions
console.profile('feature-name');
doExpensiveOperation();
console.profileEnd('feature-name');
```

---

## Debugging

### Debug Mode

Enable debug logging:

```html
<script>
window.Bengal = window.Bengal || {};
window.Bengal.debug = true;
</script>
```

Then in modules:

```javascript
function log(...args) {
  if (window.Bengal && window.Bengal.debug) {
    console.log('[ModuleName]', ...args);
  }
}

log('Feature initialized', { state: 'ready' });
```

### Common Issues

**Q: JavaScript not running**
```javascript
// Check if script loaded
console.log('Script loaded');

// Check DOM ready
console.log('DOM ready:', document.readyState);

// Check errors
window.addEventListener('error', (e) => {
  console.error('Error:', e.message, e.filename, e.lineno);
});
```

**Q: Event not firing**
```javascript
// Check element exists
console.log('Element:', document.querySelector('.selector'));

// Check event listener
element.addEventListener('click', (e) => {
  console.log('Click event:', e);
});
```

**Q: localStorage not working**
```javascript
// Check if available
if (typeof Storage !== 'undefined') {
  localStorage.setItem('test', 'value');
  console.log('Test:', localStorage.getItem('test'));
} else {
  console.error('localStorage not available');
}
```

---

## Best Practices

### ✅ Do

- Use semantic HTML
- Progressive enhancement
- Debounce scroll/resize events
- Use event delegation
- Add ARIA attributes
- Handle keyboard navigation
- Test without JavaScript
- Keep modules small and focused
- Use meaningful variable names
- Comment complex logic

### ❌ Don't

- Pollute global namespace
- Use inline event handlers
- Block main thread
- Ignore accessibility
- Use jQuery (not needed)
- Add unnecessary dependencies
- Use `eval()` or `Function()`
- Ignore browser compatibility
- Use `var` (use `const`/`let`)
- Leave `console.log` in production

---

## Resources

### Documentation
- [MDN Web Docs](https://developer.mozilla.org/)
- [Web.dev](https://web.dev/)
- [ARIA Authoring Practices](https://www.w3.org/WAI/ARIA/apg/)

### Tools
- [ESLint](https://eslint.org/) - Linting
- [Prettier](https://prettier.io/) - Code formatting
- [Lighthouse](https://developers.google.com/web/tools/lighthouse) - Performance audit

### Libraries
- [Lunr.js](https://lunrjs.com/) - Search
- [Marked](https://marked.js.org/) - Markdown parsing (if needed)

---

## License

MIT License - See [LICENSE](../../../../../LICENSE) for details
