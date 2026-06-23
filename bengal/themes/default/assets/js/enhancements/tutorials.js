/**
 * Tutorial page enhancements — scroll-driven step progress + localStorage (#543).
 *
 * Custom element: <bengal-tutorial-progress>
 * Data attributes:
 *   data-tutorial-id — localStorage key suffix
 *   data-tutorial-step — TOC/sidebar step link (1-based index)
 */
(function () {
  'use strict';

  if (!window.BengalUtils) {
    console.error('BengalUtils not loaded - tutorials.js requires utils.js');
    return;
  }

  const { throttleScroll, ready } = window.BengalUtils;
  const STORAGE_PREFIX = 'bengal_tutorial_progress_';

  let root = null;
  let tutorialId = null;
  let steps = [];
  let stepLinks = [];
  let progressBar = null;
  let progressLabel = null;
  let currentIndex = -1;
  let scrollHandler = null;
  let progress = { visited: [], lastStep: 0 };

  function storageKey() {
    return STORAGE_PREFIX + (tutorialId || 'default');
  }

  function loadProgress() {
    try {
      const stored = localStorage.getItem(storageKey());
      if (stored) {
        const parsed = JSON.parse(stored);
        progress = {
          visited: Array.isArray(parsed.visited) ? parsed.visited : [],
          lastStep: typeof parsed.lastStep === 'number' ? parsed.lastStep : 0
        };
      }
    } catch (_e) {
      progress = { visited: [], lastStep: 0 };
    }
  }

  function saveProgress() {
    try {
      localStorage.setItem(storageKey(), JSON.stringify(progress));
    } catch (_e) {
      /* storage full or unavailable */
    }
  }

  function markVisited(index) {
    if (!progress.visited.includes(index)) {
      progress.visited.push(index);
      saveProgress();
    }
    const link = stepLinks[index];
    if (link) {
      link.setAttribute('data-tutorial-visited', '');
    }
  }

  function restoreVisited() {
    progress.visited.forEach((index) => {
      const link = stepLinks[index];
      if (link) {
        link.setAttribute('data-tutorial-visited', '');
      }
    });
  }

  function getCurrentIndex() {
    const offset = 150;
    for (let i = steps.length - 1; i >= 0; i--) {
      const rect = steps[i].getBoundingClientRect();
      if (rect.top <= offset) {
        return i;
      }
    }
    return 0;
  }

  function updateHeader(index) {
    const total = steps.length;
    const current = index + 1;
    const pct = total > 0 ? (current / total) * 100 : 0;

    if (progressLabel) {
      progressLabel.textContent = `Step ${current} of ${total}`;
    }

    document.querySelectorAll('#tutorial-header-progress .tutorial-progress__step').forEach((el, i) => {
      const stepNum = i + 1;
      el.classList.toggle('tutorial-progress__step--current', stepNum === current);
      el.classList.toggle('tutorial-progress__step--complete', stepNum < current);
      const num = el.querySelector('.tutorial-progress__number');
      if (num) {
        num.textContent = stepNum < current ? '✓' : String(stepNum);
      }
    });

    document.querySelectorAll('#tutorial-header-progress .tutorial-progress__connector').forEach((conn, i) => {
      conn.classList.toggle('tutorial-progress__connector--complete', i < index);
    });

    if (progressBar) {
      progressBar.style.width = `${pct}%`;
      progressBar.setAttribute('aria-valuenow', String(Math.round(pct)));
      const host = progressBar.closest('[role="progressbar"]');
      if (host) {
        host.setAttribute('aria-valuenow', String(Math.round(pct)));
      }
    }
  }

  function updateActiveStep() {
    const index = getCurrentIndex();
    if (index === currentIndex) {
      return;
    }
    currentIndex = index;
    progress.lastStep = currentIndex;
    saveProgress();
    markVisited(currentIndex);
    updateHeader(currentIndex);

    stepLinks.forEach((link, i) => {
      const active = i === currentIndex;
      link.classList.toggle('is-active', active);
      link.toggleAttribute('aria-current', active);
    });
  }

  function initTutorialProgress(element) {
    root = element || document.querySelector('bengal-tutorial-progress');
    if (!root) {
      return;
    }

    tutorialId = root.getAttribute('data-tutorial-id') || window.location.pathname;
    stepLinks = Array.from(root.querySelectorAll('.tutorial-sidebar .toc a[href^="#"], .toc a[href^="#"]'));
    steps = stepLinks.map((link) => {
      const id = (link.getAttribute('href') || '').slice(1);
      return id ? document.getElementById(id) : null;
    }).filter(Boolean);
    if (!steps.length) {
      steps = Array.from(document.querySelectorAll('.tutorial-content h2[id]'));
    }
    progressBar = document.getElementById('tutorial-progress-bar');
    progressLabel = document.querySelector('#tutorial-header-progress .tutorial-progress__label');

    if (!steps.length) {
      return;
    }

    loadProgress();
    restoreVisited();

    scrollHandler = throttleScroll(updateActiveStep);
    window.addEventListener('scroll', scrollHandler, { passive: true });
    updateActiveStep();

    stepLinks.forEach((link) => {
      link.addEventListener('click', () => {
        currentIndex = -1;
        window.setTimeout(updateActiveStep, 100);
      });
    });

    root.setAttribute('data-enhanced', 'true');
  }

  function cleanup() {
    if (scrollHandler) {
      window.removeEventListener('scroll', scrollHandler);
      scrollHandler = null;
    }
  }

  if (window.Bengal && window.Bengal.define) {
    window.Bengal.define('bengal-tutorial-progress', class extends window.Bengal.Base {
      init() {
        initTutorialProgress(this);
      }
      teardown() {
        cleanup();
      }
    });
  }

  ready(function () {
    if (!document.querySelector('bengal-tutorial-progress')) {
      initTutorialProgress(null);
    }
  });

  window.BengalTutorials = {
    init: initTutorialProgress,
    cleanup,
    getProgress: () => ({ ...progress })
  };
})();
