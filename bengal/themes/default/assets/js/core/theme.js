/**
 * Bengal Core: Theme Management
 *
 * Pattern: POPOVER (see COMPONENT-PATTERNS.md)
 * - Element: <div id="theme-menu" popover class="*--popover">
 * - Browser handles: Show/hide, light dismiss, escape key, top layer
 * - JS handles: Positioning relative to trigger, theme/palette persistence
 *
 * Theme features:
 * - Light/Dark/System theme switching
 * - Palette selection
 * - System theme preference watching
 *
 * Note: Immediate theme initialization (to prevent FOUC) is kept inline in base.html.
 */

(function () {
  'use strict';

  // Utils are optional - graceful degradation if not available
  const log = window.BengalUtils?.log || (() => {});

  // Constants
  const THEME_KEY = 'bengal-theme';
  const PALETTE_KEY = 'bengal-palette';
  const THEMES = {
    SYSTEM: 'system',
    LIGHT: 'light',
    DARK: 'dark'
  };

  /**
   * Get current theme from localStorage or system preference
   */
  function getTheme() {
    const stored = localStorage.getItem(THEME_KEY);
    if (stored && stored !== THEMES.SYSTEM) {
      return stored;
    }
    // System preference
    if (window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches) {
      return THEMES.DARK;
    }
    return THEMES.LIGHT;
  }

  /**
   * Set theme on document
   */
  function setTheme(theme) {
    const resolved = theme === THEMES.SYSTEM ? getTheme() : theme;
    document.documentElement.setAttribute('data-theme', resolved);
    localStorage.setItem(THEME_KEY, theme);
    window.dispatchEvent(new CustomEvent('themechange', { detail: { theme: resolved } }));
  }

  /**
   * Update resolved theme without changing localStorage preference
   * Used when system preference changes but user wants to keep 'system' selected
   */
  function updateResolvedTheme() {
    const stored = localStorage.getItem(THEME_KEY);
    if (stored === THEMES.SYSTEM || !stored) {
      const resolved = getTheme();
      document.documentElement.setAttribute('data-theme', resolved);
      window.dispatchEvent(new CustomEvent('themechange', { detail: { theme: resolved } }));
    }
  }

  function getPalette() {
    return localStorage.getItem(PALETTE_KEY) || '';
  }

  function setPalette(palette) {
    if (palette !== null) {
      if (palette) {
        document.documentElement.setAttribute('data-palette', palette);
      } else {
        document.documentElement.removeAttribute('data-palette');
      }
      localStorage.setItem(PALETTE_KEY, palette);
    } else {
      document.documentElement.removeAttribute('data-palette');
      localStorage.removeItem(PALETTE_KEY);
    }
    window.dispatchEvent(new CustomEvent('palettechange', { detail: { palette } }));
  }

  /**
   * Toggle between light and dark theme
   */
  function toggleTheme() {
    const stored = localStorage.getItem(THEME_KEY) || THEMES.SYSTEM;
    const current = stored === THEMES.SYSTEM ? getTheme() : stored;
    const next = current === THEMES.LIGHT ? THEMES.DARK : THEMES.LIGHT;
    setTheme(next);
  }

  /**
   * Initialize theme (runs after DOM ready)
   * Note: Immediate init (to prevent FOUC) is kept inline in base.html
   */
  function initTheme() {
    const stored = localStorage.getItem(THEME_KEY) || THEMES.SYSTEM;
    setTheme(stored);
    const palette = getPalette();
    if (palette) setPalette(palette);
  }

  /**
   * Setup theme toggle button (simple toggle, no dropdown)
   */
  function setupToggleButton() {
    const toggleBtn = document.querySelector('.theme-toggle');
    if (toggleBtn) {
      toggleBtn.addEventListener('click', toggleTheme);
      toggleBtn.addEventListener('keydown', function (e) {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault();
          toggleTheme();
        }
      });
    }
  }

  /**
   * Setup native popover-based theme menus
   * Browser handles open/close via popover API
   * JS handles: theme persistence, active states, positioning
   * Note: Multiple menus may exist (desktop/mobile) with unique IDs
   */
  function setupPopoverMenus() {
    const popoverMenus = document.querySelectorAll('.theme-dropdown__menu--popover[popover]');

    popoverMenus.forEach(function (menu) {
      // Find the trigger button for this popover
      const triggerId = menu.id;
      const triggerBtn = triggerId
        ? document.querySelector('[popovertarget="' + triggerId + '"]')
        : menu.previousElementSibling;

      // Handle theme option clicks
      menu.addEventListener('click', function (e) {
        const btn = e.target.closest('.theme-option, [data-appearance], [data-palette]');
        if (!btn) return;

        const appearance = btn.getAttribute('data-appearance');
        const palette = btn.getAttribute('data-palette');

        if (appearance) {
          setTheme(appearance);
        }
        if (palette !== null && palette !== undefined) {
          setPalette(palette);
        }

        updatePopoverActiveStates(menu);

        // Close the popover after selection
        if (menu.hidePopover) {
          menu.hidePopover();
        }
      });

      // Position and update states when popover opens
      menu.addEventListener('toggle', function (e) {
        if (e.newState === 'open') {
          positionPopover(menu, triggerBtn);
          updatePopoverActiveStates(menu);
        }
      });

      // Initial active states
      updatePopoverActiveStates(menu);
    });
  }

  /**
   * Position popover relative to its trigger button
   */
  function positionPopover(popover, trigger) {
    if (!trigger) return;

    const triggerRect = trigger.getBoundingClientRect();
    const popoverRect = popover.getBoundingClientRect();
    const viewportWidth = window.innerWidth;

    // Position below the trigger, aligned to right edge
    let top = triggerRect.bottom + 8;
    let right = viewportWidth - triggerRect.right;

    // Ensure it doesn't go off-screen left
    const left = viewportWidth - right - popoverRect.width;
    if (left < 8) {
      right = viewportWidth - popoverRect.width - 8;
    }

    popover.style.top = top + 'px';
    popover.style.right = right + 'px';
    popover.style.left = 'auto';
  }

  /**
   * Update active states for popover-based menus
   */
  function updatePopoverActiveStates(menu) {
    const currentAppearance = localStorage.getItem(THEME_KEY) || THEMES.SYSTEM;
    const currentPalette = getPalette();

    // Update appearance buttons
    menu.querySelectorAll('[data-appearance]').forEach(function (btn) {
      const appearance = btn.getAttribute('data-appearance');
      btn.classList.toggle('active', appearance === currentAppearance);
    });

    // Update palette buttons
    menu.querySelectorAll('[data-palette]').forEach(function (btn) {
      const palette = btn.getAttribute('data-palette');
      btn.classList.toggle('active', palette === currentPalette);
    });
  }

  /**
   * Listen for system theme changes
   */
  function watchSystemTheme() {
    if (window.matchMedia) {
      const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)');
      mediaQuery.addEventListener('change', function () {
        // Only auto-switch if user prefers system appearance
        if ((localStorage.getItem(THEME_KEY) || THEMES.SYSTEM) === THEMES.SYSTEM) {
          updateResolvedTheme();
        }
      });
    }
  }

  // Export public API
  window.BengalTheme = {
    get: getTheme,
    set: setTheme,
    toggle: toggleTheme,
    getPalette: getPalette,
    setPalette: setPalette
  };

  // Register with progressive enhancement system if available
  if (window.Bengal && window.Bengal.enhance) {
    Bengal.enhance.register('theme-toggle', function(el, options) {
      el.addEventListener('click', function(e) {
        e.preventDefault();
        toggleTheme();
      });
      el.addEventListener('keydown', function(e) {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault();
          toggleTheme();
        }
      });
      if (el.tagName !== 'BUTTON') {
        el.setAttribute('role', 'button');
        el.setAttribute('tabindex', '0');
      }
    }, { override: true });
  }

  // Auto-initialize after DOM is ready
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', function () {
      initTheme();
      setupToggleButton();
      setupPopoverMenus();
      watchSystemTheme();
    });
  } else {
    initTheme();
    setupToggleButton();
    setupPopoverMenus();
    watchSystemTheme();
  }

  log('[BengalTheme] Initialized');

})();
