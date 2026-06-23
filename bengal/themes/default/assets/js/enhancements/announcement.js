/**
 * Site announcement bar — localStorage-persisted dismiss.
 */
(function () {
  'use strict';

  if (!window.Bengal?.define) return;

  const STORAGE_PREFIX = 'bengal-announcement-dismissed:';

  window.Bengal.define('bengal-site-announcement', class extends window.Bengal.Base {
    connectedCallback() {
      if (this._wired) return;
      this._wired = true;

      const id = this.dataset.announcementId || 'default';
      const dismissible = this.dataset.dismissible !== 'false';
      const storageKey = STORAGE_PREFIX + id;

      try {
        if (dismissible && localStorage.getItem(storageKey) === '1') {
          this.hidden = true;
          return;
        }
      } catch (e) {
        /* localStorage unavailable — show bar */
      }

      this.hidden = false;

      if (!dismissible) return;

      const dismissBtn = this.querySelector('.site-announcement__dismiss');
      dismissBtn?.addEventListener('click', () => {
        this.hidden = true;
        try {
          localStorage.setItem(storageKey, '1');
        } catch (e) {
          /* ignore */
        }
      });
    }
  });
})();
