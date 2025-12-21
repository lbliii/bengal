/**
 * Bengal Core: Build Badge (Build Time)
 *
 * Populates a footer build-time badge from the build-time artifact written during
 * build finalization:
 *   - <output>/<dir_name>/build.json
 *
 * Why JS:
 * - Final build duration is only known after templates render.
 * - Reading output artifacts during template rendering would require I/O.
 *
 * How URL resolution works:
 * - We try progressively higher relative paths from the current page until we
 *   find `<dir_name>/build.json`. This supports:
 *   - baseurl deployments (site hosted under a subpath)
 *   - i18n prefix strategy (artifacts mirrored under language subdirs)
 *   - file:// browsing of built output (relative paths)
 */
(function () {
  'use strict';

  const log = window.BengalUtils?.log || (() => {});

  const MAX_PARENT_SEARCH_DEPTH = 12;

  function normalizeDirName(dirName) {
    const s = String(dirName || 'bengal').trim();
    return s.replace(/^\/+/, '').replace(/\/+$/, '') || 'bengal';
  }

  function getBadgeElements() {
    return Array.from(document.querySelectorAll('[data-bengal-build-badge]'));
  }

  function getValueEl(badgeEl) {
    const existing = badgeEl.querySelector('[data-bengal-build-badge-value]');
    if (existing) return existing;
    const span = document.createElement('span');
    span.setAttribute('data-bengal-build-badge-value', '');
    span.className = 'bengal-build-time__value';
    badgeEl.appendChild(span);
    return span;
  }

  function getLabelText(badgeEl) {
    const data = badgeEl.getAttribute('data-bengal-build-badge-label');
    const s = (data || '').trim();
    return s || 'built in';
  }

  function setBadgeHidden(badgeEl, hidden) {
    if (hidden) {
      badgeEl.setAttribute('hidden', 'hidden');
      badgeEl.classList.remove('bengal-build-time--ready');
    } else {
      badgeEl.removeAttribute('hidden');
    }
  }

  async function tryFetchJson(url) {
    try {
      const resp = await fetch(url.toString(), { cache: 'no-store' });
      if (!resp.ok) return null;
      return await resp.json();
    } catch (e) {
      return null;
    }
  }

  async function resolveAndLoadBuildJson(dirName) {
    const baseDir = new URL('.', window.location.href);
    const dir = normalizeDirName(dirName);

    for (let depth = 0; depth <= MAX_PARENT_SEARCH_DEPTH; depth++) {
      const prefix = '../'.repeat(depth);
      const candidate = new URL(prefix + dir + '/build.json', baseDir);
      const payload = await tryFetchJson(candidate);
      if (payload) return { url: candidate, payload };
    }

    return null;
  }

  function formatTitle(payload) {
    const parts = [];
    if (payload.build_time_human) parts.push(`Build: ${payload.build_time_human}`);
    if (typeof payload.total_pages === 'number') parts.push(`Pages: ${payload.total_pages}`);
    if (typeof payload.total_assets === 'number') parts.push(`Assets: ${payload.total_assets}`);
    if (payload.timestamp) parts.push(`Timestamp: ${payload.timestamp}`);
    return parts.join(' • ');
  }

  async function initOne(badgeEl) {
    const dirName = badgeEl.getAttribute('data-bengal-build-badge-dir') || 'bengal';
    const label = getLabelText(badgeEl);

    // Default: keep hidden until populated (prevents showing placeholder text).
    setBadgeHidden(badgeEl, true);

    const resolved = await resolveAndLoadBuildJson(dirName);
    if (!resolved) return;

    const payload = resolved.payload || {};
    const human = String(payload.build_time_human || '').trim();
    if (!human) return;

    const valueEl = getValueEl(badgeEl);
    valueEl.textContent = human;

    badgeEl.classList.add('bengal-build-time--ready');
    badgeEl.setAttribute('href', resolved.href.toString());
    badgeEl.setAttribute('rel', 'noopener');
    badgeEl.setAttribute('aria-label', `${label} ${human}`);
    badgeEl.setAttribute('title', formatTitle(payload) || `${label} ${human}`);

    setBadgeHidden(badgeEl, false);
  }

  async function initAll() {
    const badges = getBadgeElements();
    if (!badges.length) return;

    await Promise.allSettled(badges.map(initOne));
    log('[BuildBadge] Initialized');
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initAll);
  } else {
    initAll();
  }
})();
