/**
 * Bengal Core: Theme Management
 *
 * Merged from:
 * - theme-toggle.js (theme switching functionality)
 * - theme-init.js (initialization - note: immediate init stays inline in base.html for FOUC prevention)
 *
 * Provides theme and palette switching functionality:
 * - Light/Dark/System theme switching
 * - Palette selection
 * - Theme toggle buttons and dropdowns
 * - System theme preference watching
 *
 * Note: Immediate theme initialization (to prevent FOUC) is kept inline in base.html.
 * This module provides the toggle functionality and DOM-ready initialization.
 *
 * @requires bengal-enhance.js (for enhancement registration)
 */

(function () {
  'use strict';

  // ============================================================
  // Dependencies
  // ============================================================

  // Utils are optional - graceful degradation if not available
  const log = window.BengalUtils?.log || (() => {});

  // ============================================================
  // Constants
  // ============================================================

  const THEME_KEY = 'bengal-theme';
  const PALETTE_KEY = 'bengal-palette';
  const THEMES = {
    SYSTEM: 'system',
    LIGHT: 'light',
    DARK: 'dark'
  };

  // ============================================================
  // State
  // ============================================================

  let cachedDropdowns = [];

  // ============================================================
  // Private Functions
  // ============================================================

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
   * Initialize theme (runs after DOM ready, not immediately)
   * Note: Immediate init (to prevent FOUC) is kept inline in base.html
   */
  function initTheme() {
    const stored = localStorage.getItem(THEME_KEY) || THEMES.SYSTEM;
    setTheme(stored);
    const palette = getPalette();
    if (palette) setPalette(palette);
  }

  /**
   * Cache all dropdown elements and their menus
   */
  function cacheDropdowns() {
    const dropdowns = document.querySelectorAll('.theme-dropdown');
    cachedDropdowns = Array.from(dropdowns).map(function (dd) {
      const menu = dd.querySelector('.theme-dropdown__menu');
      return {
        menu: menu,
        appearanceButtons: menu ? menu.querySelectorAll('button[data-appearance]') : [],
        paletteButtons: menu ? menu.querySelectorAll('button[data-palette]') : []
      };
    }).filter(function (cache) {
      return cache.menu !== null;
    });
  }

  /**
   * Update active states in all dropdown menus using cached elements
   */
  function updateActiveStates() {
    // Get current settings once
    const currentAppearance = localStorage.getItem(THEME_KEY) || THEMES.SYSTEM;
    const currentPalette = getPalette();

    cachedDropdowns.forEach(function (cache) {
      // Update appearance buttons
      cache.appearanceButtons.forEach(function (btn) {
        const appearance = btn.getAttribute('data-appearance');
        if (appearance === currentAppearance) {
          btn.classList.add('active');
        } else {
          btn.classList.remove('active');
        }
      });

      // Update palette buttons
      cache.paletteButtons.forEach(function (btn) {
        const palette = btn.getAttribute('data-palette');
        if (palette === currentPalette) {
          btn.classList.add('active');
        } else {
          btn.classList.remove('active');
        }
      });
    });
  }

  /**
   * Setup theme toggle button
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

    // Cache dropdown elements once during initialization
    cacheDropdowns();

    // Handle all theme dropdowns (desktop and mobile)
    const dropdowns = document.querySelectorAll('.theme-dropdown');
    dropdowns.forEach(function (dd) {
      const btn = dd.querySelector('.theme-dropdown__button');
      const menu = dd.querySelector('.theme-dropdown__menu');

      if (!btn || !menu) return;

      function closeMenu() {
        menu.classList.remove('open');
        btn.setAttribute('aria-expanded', 'false');
      }
      function openMenu() {
        menu.classList.add('open');
        btn.setAttribute('aria-expanded', 'true');
        updateActiveStates();
      }
      btn.addEventListener('click', function () {
        if (menu.classList.contains('open')) closeMenu(); else openMenu();
      });
      document.addEventListener('click', function (e) {
        if (!dd.contains(e.target)) closeMenu();
      });
      menu.addEventListener('click', function (e) {
        const t = e.target.closest('button');
        if (!t) return;
        const appearance = t.getAttribute('data-appearance');
        const palette = t.getAttribute('data-palette');
        if (appearance) {
          setTheme(appearance);
        }
        if (palette !== null) {
          setPalette(palette);
        }
        updateActiveStates();
        closeMenu();
      });

      // Set initial active states
      updateActiveStates();
    });
  }

  /**
   * Listen for system theme changes
   */
  function watchSystemTheme() {
    if (window.matchMedia) {
      const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)');

      // Modern browsers
      if (mediaQuery.addEventListener) {
        mediaQuery.addEventListener('change', function (e) {
          // Only auto-switch if user prefers system appearance
          if ((localStorage.getItem(THEME_KEY) || THEMES.SYSTEM) === THEMES.SYSTEM) {
            // Update resolved theme without changing localStorage (keep 'system' preference)
            updateResolvedTheme();
          }
        });
      }
      // Older browsers
      else if (mediaQuery.addListener) {
        mediaQuery.addListener(function (e) {
          if ((localStorage.getItem(THEME_KEY) || THEMES.SYSTEM) === THEMES.SYSTEM) {
            // Update resolved theme without changing localStorage (keep 'system' preference)
            updateResolvedTheme();
          }
        });
      }
    }
  }

  // ============================================================
  // Public API
  // ============================================================

  // Export for use in other scripts
  window.BengalTheme = {
    get: getTheme,
    set: setTheme,
    toggle: toggleTheme,
    getPalette: getPalette,
    setPalette: setPalette
  };

  // ============================================================
  // Registration
  // ============================================================

  // Register with progressive enhancement system if available
  // This allows data-bengal="theme-toggle" elements to work with
  // the new enhancement loader while maintaining backward compatibility
  if (window.Bengal && window.Bengal.enhance) {
    Bengal.enhance.register('theme-toggle', function(el, options) {
      // Simple toggle handler - delegates to BengalTheme API
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

      // Ensure button role if not already a button
      if (el.tagName !== 'BUTTON') {
        el.setAttribute('role', 'button');
        el.setAttribute('tabindex', '0');
      }
    }, { override: true });
  }

  // ============================================================
  // Auto-initialize
  // ============================================================

  // Setup after DOM is ready
  // Note: Immediate theme init (to prevent FOUC) is kept inline in base.html
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', function () {
      initTheme(); // Re-apply theme after DOM ready (in case inline init didn't run)
      setupToggleButton();
      watchSystemTheme();
    });
  } else {
    initTheme();
    setupToggleButton();
    watchSystemTheme();
  }

  log('[BengalTheme] Initialized');

})();
