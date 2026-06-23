/**
 * Doc-page inline track navigation (#543)
 *
 * Persists the furthest step reached per track in localStorage and
 * restores progress on return visits. Works with <bengal-doc-track-nav>.
 */
(function () {
  'use strict';

  if (!window.BengalUtils) {
    return;
  }

  const { ready } = window.BengalUtils;
  const STORAGE_PREFIX = 'bengal_doc_track_nav_';

  function loadProgress(trackId) {
    try {
      const raw = localStorage.getItem(STORAGE_PREFIX + trackId);
      if (!raw) {
        return { maxIndex: -1 };
      }
      const parsed = JSON.parse(raw);
      return {
        maxIndex: typeof parsed.maxIndex === 'number' ? parsed.maxIndex : -1,
      };
    } catch (_e) {
      return { maxIndex: -1 };
    }
  }

  function saveProgress(trackId, maxIndex) {
    try {
      localStorage.setItem(
        STORAGE_PREFIX + trackId,
        JSON.stringify({ maxIndex, updatedAt: Date.now() })
      );
    } catch (_e) {
      // localStorage unavailable
    }
  }

  function updateProgressBar(nav, effectiveIndex, total) {
    const bar = nav.querySelector('[data-track-nav-progress]');
    if (!bar || total <= 0) {
      return;
    }

    const pct = Math.min(100, Math.max(0, ((effectiveIndex + 1) / total) * 100));
    bar.style.width = pct + '%';
    bar.setAttribute('aria-valuenow', String(Math.round(pct)));

    const root = bar.closest('[role="progressbar"]');
    if (root) {
      root.setAttribute('aria-valuenow', String(Math.round(pct)));
    }

    const stepLabel = nav.querySelector('.track-navigation__step');
    if (stepLabel) {
      stepLabel.textContent = `${effectiveIndex + 1} / ${total}`;
    }
  }

  function initNav(nav) {
    const trackId = nav.dataset.trackId;
    const currentIndex = Number.parseInt(nav.dataset.trackIndex, 10);
    const total = Number.parseInt(nav.dataset.trackTotal, 10);

    if (!trackId || Number.isNaN(currentIndex) || Number.isNaN(total) || total <= 0) {
      return;
    }

    const stored = loadProgress(trackId);
    const effectiveIndex = Math.max(stored.maxIndex, currentIndex);
    saveProgress(trackId, effectiveIndex);
    updateProgressBar(nav, effectiveIndex, total);
  }

  class BengalDocTrackNav extends HTMLElement {
    connectedCallback() {
      initNav(this);
    }
  }

  ready(function () {
    if (!customElements.get('bengal-doc-track-nav')) {
      customElements.define('bengal-doc-track-nav', BengalDocTrackNav);
    }

    document.querySelectorAll('bengal-doc-track-nav').forEach(initNav);
  });
})();
