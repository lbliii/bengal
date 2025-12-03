---
title: Add Dark Mode Toggle
description: Add a dark/light mode toggle to your Bengal site
weight: 10
draft: false
lang: en
tags: [recipe, dark-mode, theming, css]
keywords: [dark mode, light mode, theme toggle, css variables]
category: recipe
---

# Add Dark Mode Toggle

Add a dark/light mode toggle that respects user preferences and remembers their choice.

## Time Required

⏱️ 10-15 minutes

## What You'll Build

- CSS custom properties for light and dark themes
- JavaScript toggle that persists to localStorage
- System preference detection via `prefers-color-scheme`

## Step 1: Add CSS Variables

Create or update your theme's CSS file:

```css
/* static/css/theme.css */

/* Light mode (default) */
:root {
  --color-bg: #ffffff;
  --color-text: #1a1a1a;
  --color-link: #0066cc;
  --color-border: #e0e0e0;
  --color-code-bg: #f5f5f5;
}

/* Dark mode */
[data-theme="dark"] {
  --color-bg: #1a1a1a;
  --color-text: #e0e0e0;
  --color-link: #66b3ff;
  --color-border: #404040;
  --color-code-bg: #2d2d2d;
}

/* Apply variables */
body {
  background-color: var(--color-bg);
  color: var(--color-text);
  transition: background-color 0.3s, color 0.3s;
}

a {
  color: var(--color-link);
}

pre, code {
  background-color: var(--color-code-bg);
}
```

## Step 2: Add Toggle Button

Add to your header partial:

```html
<!-- templates/partials/header.html -->
<button id="theme-toggle" aria-label="Toggle dark mode">
  <span class="light-icon">🌙</span>
  <span class="dark-icon">☀️</span>
</button>

<style>
[data-theme="dark"] .dark-icon { display: none; }
[data-theme="dark"] .light-icon { display: inline; }
:not([data-theme="dark"]) .light-icon { display: none; }
:not([data-theme="dark"]) .dark-icon { display: inline; }
</style>
```

## Step 3: Add JavaScript

Add to your base template or a separate JS file:

```javascript
// static/js/theme-toggle.js
(function() {
  const toggle = document.getElementById('theme-toggle');
  const html = document.documentElement;
  
  // Check for saved preference, then system preference
  const getPreferredTheme = () => {
    const saved = localStorage.getItem('theme');
    if (saved) return saved;
    
    return window.matchMedia('(prefers-color-scheme: dark)').matches 
      ? 'dark' 
      : 'light';
  };
  
  // Apply theme
  const setTheme = (theme) => {
    html.setAttribute('data-theme', theme);
    localStorage.setItem('theme', theme);
  };
  
  // Initialize
  setTheme(getPreferredTheme());
  
  // Toggle
  toggle.addEventListener('click', () => {
    const current = html.getAttribute('data-theme');
    setTheme(current === 'dark' ? 'light' : 'dark');
  });
  
  // Listen for system preference changes
  window.matchMedia('(prefers-color-scheme: dark)')
    .addEventListener('change', (e) => {
      if (!localStorage.getItem('theme')) {
        setTheme(e.matches ? 'dark' : 'light');
      }
    });
})();
```

## Step 4: Prevent Flash

Add this to your `<head>` to prevent flash of wrong theme:

```html
<script>
  (function() {
    const saved = localStorage.getItem('theme');
    const preferred = saved || (window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light');
    document.documentElement.setAttribute('data-theme', preferred);
  })();
</script>
```

## Result

Your site now has:
- ✅ Dark/light mode toggle
- ✅ Persistent user preference
- ✅ Respects system preference
- ✅ No flash on page load

## See Also

- [Theme Customization](/docs/theming/themes/customize/) — More theming options
- [Assets](/docs/theming/assets/) — Managing CSS and JavaScript

