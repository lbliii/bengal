/**
 * Bengal SSG Default Theme
 * Dark Mode Toggle
 */

(function() {
  'use strict';

  const THEME_KEY = 'bengal-theme';
  const THEMES = {
    LIGHT: 'light',
    DARK: 'dark'
  };

  /**
   * Get current theme from localStorage or system preference
   */
  function getTheme() {
    const stored = localStorage.getItem(THEME_KEY);
    if (stored) {
      return stored;
    }

    // Check system preference
    if (window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches) {
      return THEMES.DARK;
    }

    return THEMES.LIGHT;
  }

  /**
   * Set theme on document
   */
  function setTheme(theme) {
    document.documentElement.setAttribute('data-theme', theme);
    localStorage.setItem(THEME_KEY, theme);

    // Dispatch event for other components
    window.dispatchEvent(new CustomEvent('themechange', { detail: { theme } }));
  }

  /**
   * Toggle between light and dark theme
   */
  function toggleTheme() {
    const current = getTheme();
    const next = current === THEMES.LIGHT ? THEMES.DARK : THEMES.LIGHT;
    setTheme(next);
  }

  /**
   * Initialize theme
   */
  function initTheme() {
    const theme = getTheme();
    setTheme(theme);
  }

  /**
   * Setup theme toggle button
   */
  function setupToggleButton() {
    const toggleBtn = document.querySelector('.theme-toggle');
    if (toggleBtn) {
      toggleBtn.addEventListener('click', toggleTheme);

      // Add keyboard support
      toggleBtn.addEventListener('keydown', function(e) {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault();
          toggleTheme();
        }
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
          // Only auto-switch if user hasn't manually set a preference
          if (!localStorage.getItem(THEME_KEY)) {
            setTheme(e.matches ? THEMES.DARK : THEMES.LIGHT);
          }
        });
      }
      // Older browsers
      else if (mediaQuery.addListener) {
        mediaQuery.addListener(function(e) {
          if (!localStorage.getItem(THEME_KEY)) {
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
    toggle: toggleTheme
  };
})();
