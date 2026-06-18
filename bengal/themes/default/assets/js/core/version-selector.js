/**
 * Version Selector / Switcher
 *
 * Two shapes share this file:
 *
 *   1. <select id="version-select">          — the boxed dropdown still used on
 *      non-docs pages (page.html / index.html). Navigates on `change` via each
 *      option's pre-computed, baseurl-correct data-target.
 *
 *   2. <details data-version-switcher>        — the compact sidebar switcher that
 *      merges into the docs-nav "Documentation · Latest ▾" header. The native
 *      <details>/<summary> disclosure and the real <a> options mean version
 *      switching works with zero JS; this script only adds the niceties:
 *      close-on-outside-click, Escape-to-close, and arrow-key navigation.
 */

(function () {
  'use strict';

  /* ----- 1. Native <select> version selector ----- */

  function handleVersionChange(event) {
    const selectedOption = event.target.selectedOptions[0];
    if (selectedOption && selectedOption.dataset.target) {
      window.location.href = selectedOption.dataset.target;
    }
  }

  function initSelect() {
    const versionSelect = document.getElementById('version-select');
    if (versionSelect) {
      versionSelect.addEventListener('change', handleVersionChange);
    }
  }

  /* ----- 2. <details>-based sidebar version switcher ----- */

  function enhanceSwitcher(details) {
    const summary = details.querySelector('summary');
    const links = Array.prototype.slice.call(
      details.querySelectorAll('.docs-nav-vswitch__link')
    );
    if (!summary) {
      return;
    }

    function close(focusSummary) {
      if (!details.open) {
        return;
      }
      details.open = false;
      if (focusSummary) {
        summary.focus();
      }
    }

    function focusLink(index) {
      if (!links.length) {
        return;
      }
      const i = (index + links.length) % links.length;
      links[i].focus();
    }

    // Open + focus the first option when arrowing down from the summary.
    summary.addEventListener('keydown', function (e) {
      if (e.key === 'ArrowDown' || e.key === 'Down') {
        e.preventDefault();
        details.open = true;
        focusLink(0);
      }
    });

    // Arrow / Home / End / Escape while focus is inside the open menu.
    details.addEventListener('keydown', function (e) {
      if (e.key === 'Escape' || e.key === 'Esc') {
        close(true);
        return;
      }
      const current = links.indexOf(document.activeElement);
      if (current === -1) {
        return;
      }
      if (e.key === 'ArrowDown' || e.key === 'Down') {
        e.preventDefault();
        focusLink(current + 1);
      } else if (e.key === 'ArrowUp' || e.key === 'Up') {
        e.preventDefault();
        focusLink(current - 1);
      } else if (e.key === 'Home') {
        e.preventDefault();
        focusLink(0);
      } else if (e.key === 'End') {
        e.preventDefault();
        focusLink(links.length - 1);
      }
    });

    // Close when a click or focus leaves the widget.
    document.addEventListener('click', function (e) {
      if (details.open && !details.contains(e.target)) {
        close(false);
      }
    });
    details.addEventListener('focusout', function (e) {
      if (!details.contains(e.relatedTarget)) {
        close(false);
      }
    });
  }

  function initSwitchers() {
    const switchers = document.querySelectorAll('details[data-version-switcher]');
    Array.prototype.forEach.call(switchers, enhanceSwitcher);
  }

  function init() {
    initSelect();
    initSwitchers();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
