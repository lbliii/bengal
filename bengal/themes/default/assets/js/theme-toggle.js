/**
 * Bengal SSG Default Theme
 * Dark Mode Toggle
 */

(function() {
  'use strict';

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

  function getPalette() {
    return localStorage.getItem(PALETTE_KEY) || '';
  }

  function setPalette(palette) {
    if (palette) {
      document.documentElement.setAttribute('data-palette', palette);
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
   * Initialize theme
   */
  function initTheme() {
    const stored = localStorage.getItem(THEME_KEY) || THEMES.SYSTEM;
    setTheme(stored);
    const palette = getPalette();
    if (palette) setPalette(palette);
  }

  /**
   * Setup theme toggle button
   */
  function setupToggleButton() {
    const toggleBtn = document.querySelector('.theme-toggle');
    if (toggleBtn) {
      toggleBtn.addEventListener('click', toggleTheme);
      toggleBtn.addEventListener('keydown', function(e) {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault();
          toggleTheme();
        }
      });
    }

    const dd = document.querySelector('.theme-dropdown');
    if (dd) {
      const btn = dd.querySelector('.theme-dropdown__button');
      const menu = dd.querySelector('.theme-dropdown__menu');
      function closeMenu() {
        menu.classList.remove('open');
        btn.setAttribute('aria-expanded', 'false');
      }
      function openMenu() {
        menu.classList.add('open');
        btn.setAttribute('aria-expanded', 'true');
      }
      btn.addEventListener('click', function() {
        if (menu.classList.contains('open')) closeMenu(); else openMenu();
      });
      document.addEventListener('click', function(e) {
        if (!dd.contains(e.target)) closeMenu();
      });
      menu.addEventListener('click', function(e) {
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
        closeMenu();
      });
    }
  }

  /**
   * Listen for system theme changes
   */
  function watchSystemTheme() {
    if (window.matchMedia) {
      const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)');

      // Modern browsers
      if (mediaQuery.addEventListener) {
        mediaQuery.addEventListener('change', function(e) {
          // Only auto-switch if user prefers system appearance
          if ((localStorage.getItem(THEME_KEY) || THEMES.SYSTEM) === THEMES.SYSTEM) {
            setTheme(e.matches ? THEMES.DARK : THEMES.LIGHT);
          }
        });
      }
      // Older browsers
      else if (mediaQuery.addListener) {
        mediaQuery.addListener(function(e) {
          if ((localStorage.getItem(THEME_KEY) || THEMES.SYSTEM) === THEMES.SYSTEM) {
            setTheme(e.matches ? THEMES.DARK : THEMES.LIGHT);
          }
        });
      }
    }
  }

  // Initialize immediately to prevent flash of wrong theme
  initTheme();

  // Setup after DOM is ready
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', function() {
      setupToggleButton();
      watchSystemTheme();
    });
  } else {
    setupToggleButton();
    watchSystemTheme();
  }

  // Export for use in other scripts
  window.BengalTheme = {
    get: getTheme,
    set: setTheme,
    toggle: toggleTheme,
    getBrand: getBrand,
    setBrand: setBrand
  };
})();
