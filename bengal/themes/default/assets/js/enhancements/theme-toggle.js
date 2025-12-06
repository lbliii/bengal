/**
 * Bengal Enhancement: Theme Toggle
 *
 * Provides dark/light/system theme switching with palette support.
 * Registers with Bengal.enhance for data-bengal="theme-toggle" elements.
 *
 * Usage:
 *   <button data-bengal="theme-toggle">Toggle Theme</button>
 *   <button data-bengal="theme-toggle" data-default="dark">Toggle</button>
 *
 * Options:
 *   - default: Default theme ('light', 'dark', 'system')
 *
 * @requires bengal-enhance.js
 * @see theme-toggle.js for full theme API (BengalTheme)
 */

(function() {
  'use strict';

  // Ensure enhancement system is available
  if (!window.Bengal || !window.Bengal.enhance) {
    console.warn('[Bengal] Enhancement system not loaded - theme-toggle enhancement cannot register');
    return;
  }

  const THEME_KEY = 'bengal-theme';
  const THEMES = {
    SYSTEM: 'system',
    LIGHT: 'light',
    DARK: 'dark'
  };

  /**
   * Get current resolved theme
   * @returns {string} 'light' or 'dark'
   */
  function getResolvedTheme() {
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
   * Toggle between light and dark theme
   */
  function toggleTheme() {
    // Use existing BengalTheme API if available
    if (window.BengalTheme && window.BengalTheme.toggle) {
      window.BengalTheme.toggle();
      return;
    }

    // Fallback implementation
    const current = getResolvedTheme();
    const next = current === THEMES.LIGHT ? THEMES.DARK : THEMES.LIGHT;
    document.documentElement.setAttribute('data-theme', next);
    localStorage.setItem(THEME_KEY, next);
    window.dispatchEvent(new CustomEvent('themechange', { detail: { theme: next } }));
  }

  /**
   * Update button aria-pressed state
   * @param {HTMLElement} el - Button element
   */
  function updateAriaState(el) {
    const isDark = document.documentElement.getAttribute('data-theme') === 'dark';
    el.setAttribute('aria-pressed', isDark ? 'true' : 'false');
  }

  // Register the enhancement
  Bengal.enhance.register('theme-toggle', function(el, options) {
    // Set up click handler
    el.addEventListener('click', (e) => {
      e.preventDefault();
      toggleTheme();
    });

    // Set up keyboard handler for accessibility
    el.addEventListener('keydown', (e) => {
      if (e.key === 'Enter' || e.key === ' ') {
        e.preventDefault();
        toggleTheme();
      }
    });

    // Update aria-pressed on theme change
    updateAriaState(el);
    window.addEventListener('themechange', () => updateAriaState(el));

    // Ensure button role if not already a button
    if (el.tagName !== 'BUTTON') {
      el.setAttribute('role', 'button');
      el.setAttribute('tabindex', '0');
    }
  });

})();

