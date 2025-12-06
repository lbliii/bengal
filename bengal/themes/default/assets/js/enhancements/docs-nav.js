/**
 * Bengal SSG - Documentation Navigation Enhancement
 *
 * Handles scroll spy and active state management for docs navigation.
 * The actual functionality is implemented in interactive.js, this file
 * exists to satisfy the auto-loading enhancement system.
 *
 * @see enhancements/interactive.js for implementation
 */

(function() {
  'use strict';

  // The docs-nav enhancement is registered in interactive.js
  // This file exists to prevent 404 errors when the enhancement system
  // tries to auto-load enhancements/docs-nav.js
  //
  // Since interactive.js is loaded before this would be needed,
  // the enhancement is already registered. This is just a placeholder
  // to satisfy the auto-loader.

  // If interactive.js hasn't loaded yet, register a minimal handler
  // that will be replaced when interactive.js loads
  if (window.Bengal && window.Bengal.enhance) {
    // Check if already registered (by interactive.js)
    if (!window.Bengal.enhance.get('docs-nav')) {
      // Register a no-op - interactive.js will override this when it loads
      window.Bengal.enhance.register('docs-nav', function(el, options) {
        // No-op - functionality is in interactive.js
        // This prevents errors if docs-nav.js loads before interactive.js
      });
    }
  }

})();
