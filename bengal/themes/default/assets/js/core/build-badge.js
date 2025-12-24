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
 * 1. If `data-bengal-build-badge-path` is provided, try that URL first (avoids 404s).
 * 2. For HTTP(S), try root-relative path `/<dir_name>/build.json`.
 * 3. Fall back to relative path walking (`../` prefixes) for:
 *    - baseurl deployments (site hosted under a subpath)
 *    - i18n prefix strategy (artifacts mirrored under language subdirs)
 *    - file:// browsing of built output (relative paths)
 *
 * Data attributes:
 * - data-bengal-build-badge: Marker attribute for badge elements
 * - data-bengal-build-badge-dir: Directory name for artifacts (default: "bengal")
 * - data-bengal-build-badge-path: Optional absolute path hint to build.json
 * - data-bengal-build-badge-label: Label text (default: "built in")
 *
 * Features:
 * - Hover card showing full build stats (like link previews)
 * - Links to build.json for detailed inspection
 */
(function () {
  'use strict';

  const log = window.BengalUtils?.log || (() => {});

  const MAX_PARENT_SEARCH_DEPTH = 12;
  const HOVER_DELAY = 150;
  const HIDE_DELAY = 100;

  // State for hover card
  let activeCard = null;
  let hoverTimeout = null;
  let hideTimeout = null;

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

  async function resolveAndLoadBuildJson(dirName, pathHint) {
    const baseDir = new URL('.', window.location.href);
    const dir = normalizeDirName(dirName);

    // If a path hint is provided (from template), try it first.
    // This avoids 404 noise for the common HTTP case.
    if (pathHint) {
      const hintUrl = new URL(pathHint, window.location.href);
      const hintPayload = await tryFetchJson(hintUrl);
      if (hintPayload) return { url: hintUrl, payload: hintPayload };
    }

    // For HTTP(S) without hint, try root-relative path.
    if (window.location.protocol.startsWith('http') && !pathHint) {
      const absoluteCandidate = new URL('/' + dir + '/build.json', window.location.origin);
      const absolutePayload = await tryFetchJson(absoluteCandidate);
      if (absolutePayload) return { url: absoluteCandidate, payload: absolutePayload };
    }

    // Fall back to relative path walking for file:// browsing.
    for (let depth = 0; depth <= MAX_PARENT_SEARCH_DEPTH; depth++) {
      const prefix = '../'.repeat(depth);
      const candidate = new URL(prefix + dir + '/build.json', baseDir);
      const payload = await tryFetchJson(candidate);
      if (payload) return { url: candidate, payload };
    }

    return null;
  }

  // ============================================================
  // Hover Card (Build Stats Preview)
  // ============================================================

  function formatTimestamp(timestamp) {
    if (!timestamp) return null;
    try {
      const date = new Date(timestamp);
      return date.toLocaleString(undefined, {
        month: 'short',
        day: 'numeric',
        hour: 'numeric',
        minute: '2-digit',
      });
    } catch {
      return timestamp;
    }
  }

  function createStatItem(icon, label, value) {
    if (value === undefined || value === null) return '';
    return `
      <div class="build-stats-card__stat">
        <span class="build-stats-card__icon">${icon}</span>
        <span class="build-stats-card__label">${label}</span>
        <span class="build-stats-card__value">${value}</span>
      </div>
    `;
  }

  function createCard(payload, jsonUrl) {
    const card = document.createElement('div');
    card.className = 'build-stats-card';
    card.setAttribute('role', 'tooltip');

    const stats = [];

    // Build time (primary stat)
    if (payload.build_time_human) {
      stats.push(createStatItem('⚡', 'Build time', payload.build_time_human));
    }

    // Pages rendered
    if (typeof payload.total_pages === 'number') {
      stats.push(createStatItem('📄', 'Pages', payload.total_pages.toLocaleString()));
    }

    // Assets copied
    if (typeof payload.total_assets === 'number') {
      stats.push(createStatItem('📦', 'Assets', payload.total_assets.toLocaleString()));
    }

    // Timestamp
    const formattedTime = formatTimestamp(payload.timestamp);
    if (formattedTime) {
      stats.push(createStatItem('🕐', 'Built', formattedTime));
    }

    card.innerHTML = `
      <div class="build-stats-card__header">
        <span class="build-stats-card__title">Build Stats</span>
        <a href="${jsonUrl}" class="build-stats-card__link" rel="noopener" aria-label="View raw JSON">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M18 13v6a2 2 0 01-2 2H5a2 2 0 01-2-2V8a2 2 0 012-2h6"/>
            <polyline points="15 3 21 3 21 9"/>
            <line x1="10" y1="14" x2="21" y2="3"/>
          </svg>
        </a>
      </div>
      <div class="build-stats-card__stats">
        ${stats.join('')}
      </div>
    `;

    return card;
  }

  function positionCard(card, badgeEl) {
    document.body.appendChild(card);

    const badgeRect = badgeEl.getBoundingClientRect();
    const cardRect = card.getBoundingClientRect();
    const viewportHeight = window.innerHeight;
    const viewportWidth = window.innerWidth;
    const gap = 8;

    // Default: position above the badge
    let top = badgeRect.top - cardRect.height - gap;
    let positionClass = 'build-stats-card--above';

    // If not enough space above, show below
    if (top < gap) {
      top = badgeRect.bottom + gap;
      positionClass = 'build-stats-card--below';
    }

    // Center horizontally on badge
    let left = badgeRect.left + (badgeRect.width / 2) - (cardRect.width / 2);

    // Keep within viewport bounds
    if (left < gap) {
      left = gap;
    } else if (left + cardRect.width > viewportWidth - gap) {
      left = viewportWidth - cardRect.width - gap;
    }

    card.style.top = `${top + window.scrollY}px`;
    card.style.left = `${left}px`;
    card.classList.add(positionClass);
  }

  function showCard(badgeEl) {
    clearTimeout(hideTimeout);

    // Already showing for this badge?
    if (activeCard && activeCard._badgeEl === badgeEl) return;

    // Hide any existing card
    hideCard();

    const payload = badgeEl._buildPayload;
    const jsonUrl = badgeEl._buildJsonUrl;
    if (!payload) return;

    const card = createCard(payload, jsonUrl);
    card._badgeEl = badgeEl;

    // Add hover handlers to card itself
    card.addEventListener('mouseenter', () => {
      clearTimeout(hideTimeout);
    });
    card.addEventListener('mouseleave', scheduleHide);

    positionCard(card, badgeEl);
    activeCard = card;
  }

  function hideCard() {
    if (activeCard) {
      activeCard.remove();
      activeCard = null;
    }
  }

  function scheduleShow(badgeEl) {
    clearTimeout(hoverTimeout);
    clearTimeout(hideTimeout);
    hoverTimeout = setTimeout(() => showCard(badgeEl), HOVER_DELAY);
  }

  function scheduleHide() {
    clearTimeout(hoverTimeout);
    clearTimeout(hideTimeout);
    hideTimeout = setTimeout(hideCard, HIDE_DELAY);
  }

  function attachHoverListeners(badgeEl) {
    // Remove title to prevent native tooltip competing with card
    badgeEl.removeAttribute('title');

    badgeEl.addEventListener('mouseenter', () => scheduleShow(badgeEl));
    badgeEl.addEventListener('mouseleave', scheduleHide);
    badgeEl.addEventListener('focus', () => scheduleShow(badgeEl));
    badgeEl.addEventListener('blur', scheduleHide);

    // Close on Escape
    badgeEl.addEventListener('keydown', (e) => {
      if (e.key === 'Escape') {
        hideCard();
        badgeEl.blur();
      }
    });
  }

  // ============================================================
  // Initialization
  // ============================================================

  async function initOne(badgeEl) {
    const dirName = badgeEl.getAttribute('data-bengal-build-badge-dir') || 'bengal';
    const pathHint = badgeEl.getAttribute('data-bengal-build-badge-path') || '';
    const label = getLabelText(badgeEl);

    // Default: keep hidden until populated (prevents showing placeholder text).
    setBadgeHidden(badgeEl, true);

    const resolved = await resolveAndLoadBuildJson(dirName, pathHint);
    if (!resolved) return;

    const payload = resolved.payload || {};
    const human = String(payload.build_time_human || '').trim();
    if (!human) return;

    const valueEl = getValueEl(badgeEl);
    valueEl.textContent = human;

    // Store payload for hover card
    badgeEl._buildPayload = payload;
    badgeEl._buildJsonUrl = resolved.url.toString();

    badgeEl.classList.add('bengal-build-time--ready');
    badgeEl.setAttribute('href', resolved.url.toString());
    badgeEl.setAttribute('rel', 'noopener');
    badgeEl.setAttribute('aria-label', `${label} ${human}`);

    setBadgeHidden(badgeEl, false);

    // Attach hover card listeners
    attachHoverListeners(badgeEl);
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
