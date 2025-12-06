# Bengal Enhancement Modules

This directory contains progressive enhancement modules for the Bengal theme. Each module registers with the central enhancement system (`bengal-enhance.js`) to provide JavaScript functionality that layers on top of working HTML.

## Philosophy

"Layered enhancement — HTML that works, CSS that delights, JS that elevates"

All enhancements follow progressive enhancement principles:
- HTML is functional without JavaScript
- Enhancements add interactivity when JS is available
- Graceful degradation on errors

## Usage

Declare enhancements using the `data-bengal` attribute:

```html
<!-- Theme toggle button -->
<button data-bengal="theme-toggle">Toggle Theme</button>

<!-- Tabs container -->
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

<!-- Mobile navigation -->
<nav data-bengal="mobile-nav">...</nav>
```

## Configuration

Options are passed via additional `data-*` attributes:

```html
<nav data-bengal="toc" data-spy="true" data-offset="80">
```

Boolean values: `data-spy="true"` or just `data-spy`
Numbers: `data-offset="80"`
JSON: `data-config='{"key": "value"}'`

## Available Enhancements

| Name | Description | Options |
|------|-------------|---------|
| `theme-toggle` | Dark/light theme switching | `default` |
| `mobile-nav` | Mobile slide-out navigation | `closeOnClick`, `closeOnEscape` |
| `tabs` | Tabbed content panels | `defaultTab` |
| `toc` | Table of contents with scroll spy | `spy`, `offset`, `smooth` |

## Creating Custom Enhancements

```javascript
// enhancements/my-feature.js
(function() {
  'use strict';

  // Ensure enhancement system is available
  if (!window.Bengal || !window.Bengal.enhance) {
    console.warn('[Bengal] Enhancement system not loaded');
    return;
  }

  Bengal.enhance.register('my-feature', function(el, options) {
    // el: The element with data-bengal="my-feature"
    // options: Parsed data attributes { optionName: value }

    // Add your enhancement logic here
    el.addEventListener('click', () => {
      console.log('Enhanced!', options);
    });
  });
})();
```

## Lazy Loading

Enhancements not preloaded are automatically lazy-loaded when their `data-bengal` elements are detected. Scripts are loaded from `/assets/js/enhancements/{name}.js`.

## API

```javascript
// List registered enhancements
Bengal.enhance.list();

// Check if an element is enhanced
Bengal.enhance.isEnhanced(element);

// Manually trigger enhancement discovery
Bengal.enhance.enhanceAll();

// Enhance a specific element
Bengal.enhance.enhanceElement(element);
```

## See Also

- [RFC: Progressive Enhancements Architecture](../../../../../../plan/active/rfc-progressive-enhancements.md)
- [bengal-enhance.js](../bengal-enhance.js) - The enhancement loader
