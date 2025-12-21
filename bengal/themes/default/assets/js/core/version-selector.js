/**
 * Version Selector
 *
 * Handles version switching for versioned documentation.
 * Uses pre-computed target URLs for instant navigation without 404 errors.
 */

(function () {
  'use strict';

  function handleVersionChange(event) {
    const selectedOption = event.target.selectedOptions[0];
    if (selectedOption && selectedOption.dataset.target) {
      window.location.href = selectedOption.dataset.target;
    }
  }

  function init() {
    const versionSelect = document.getElementById('version-select');
    if (versionSelect) {
      versionSelect.addEventListener('change', handleVersionChange);
    }
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
