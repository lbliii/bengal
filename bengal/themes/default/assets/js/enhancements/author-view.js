/**
 * Author archive post-list view toggle (replaces inline script).
 */
(function () {
  'use strict';

  const { ready } = window.BengalUtils || { ready: (fn) => document.addEventListener('DOMContentLoaded', fn) };

  ready(function () {
    const toggle = document.querySelector('.posts-view-toggle');
    if (!toggle) return;

    toggle.addEventListener('click', (event) => {
      const button = event.target.closest('.view-btn');
      if (!button) return;

      const view = button.dataset.view;
      toggle.querySelectorAll('.view-btn').forEach((btn) => {
        btn.classList.toggle('active', btn === button);
      });
      document.querySelectorAll('[data-view-content]').forEach((panel) => {
        panel.classList.toggle('hidden', panel.dataset.viewContent !== view);
      });
    });
  });
})();
