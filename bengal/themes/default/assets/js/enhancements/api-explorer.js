/**
 * Bengal Enhancement: OpenAPI Interactive API Explorer
 *
 * "Try it" panel: sends real API requests via fetch() from the docs page.
 * Client-side only — no server proxy. Opt-in via autodoc.openapi.interactive: true.
 *
 * @requires utils.js (optional, for copyToClipboard)
 * @requires bengal-enhance.js (for enhancement registration)
 */

(function () {
  'use strict';

  const log = window.BengalUtils?.log || (() => {});
  const ready = window.BengalUtils?.ready || ((fn) => {
    if (document.readyState === 'loading') {
      document.addEventListener('DOMContentLoaded', fn);
    } else {
      fn();
    }
  });

  function init() {
    document.querySelectorAll('[data-api-explorer]').forEach((panel) => {
      initPanel(panel);
    });
    log('[Bengal] API Explorer initialized');
  }

  function initPanel(panel) {
    const urlInput = panel.querySelector('[data-try-it-url]');
    const methodSelect = panel.querySelector('[data-try-it-method]');
    const sendBtn = panel.querySelector('[data-try-it-send]');
    const bodyInput = panel.querySelector('[data-try-it-body]');
    const responseEl = panel.querySelector('[data-try-it-response]');
    const statusEl = panel.querySelector('[data-try-it-status]');
    const timeEl = panel.querySelector('[data-try-it-time]');
    const bodyEl = panel.querySelector('[data-try-it-response-body]');
    const loadingEl = panel.querySelector('[data-try-it-loading]');
    const errorEl = panel.querySelector('[data-try-it-error]');

    if (!sendBtn || !urlInput) return;

    sendBtn.addEventListener('click', async () => {
      const url = urlInput.value.trim();
      const method = methodSelect ? methodSelect.value : 'GET';
      let body = null;

      if (bodyInput && bodyInput.value.trim()) {
        try {
          body = JSON.parse(bodyInput.value.trim());
          body = JSON.stringify(body);
        } catch {
          errorEl.textContent = 'Invalid JSON in request body';
          errorEl.hidden = false;
          responseEl.hidden = true;
          loadingEl.hidden = true;
          setTimeout(() => { errorEl.hidden = true; }, 3000);
          return;
        }
      }

      const headers = buildHeaders(panel);

      loadingEl.hidden = false;
      responseEl.hidden = true;
      errorEl.hidden = true;
      sendBtn.disabled = true;

      const start = performance.now();
      try {
        const res = await fetch(url, {
          method,
          headers,
          body: method !== 'GET' && method !== 'HEAD' ? body : undefined,
          mode: 'cors',
        });
        const elapsed = Math.round(performance.now() - start);

        const contentType = res.headers.get('content-type') || '';
        let text = await res.text();
        let display = text;
        if (contentType.includes('application/json') && text) {
          try {
            display = JSON.stringify(JSON.parse(text), null, 2);
          } catch {
            /* use raw text */
          }
        }

        statusEl.textContent = `${res.status} ${res.statusText}`;
        statusEl.className = 'api-try-it__status api-try-it__status--' + (res.ok ? 'success' : 'error');
        timeEl.textContent = `${elapsed} ms`;
        if (bodyEl) {
          bodyEl.textContent = display || '(empty)';
          bodyEl.className = 'language-json';
        }
        responseEl.hidden = false;
      } catch (err) {
        statusEl.textContent = 'Error';
        statusEl.className = 'api-try-it__status api-try-it__status--error';
        timeEl.textContent = '';
        if (bodyEl) {
          bodyEl.textContent = err.message || String(err);
          bodyEl.className = '';
        }
        responseEl.hidden = false;
        errorEl.textContent = err.message || 'Request failed';
        errorEl.hidden = false;
      } finally {
        loadingEl.hidden = true;
        sendBtn.disabled = false;
      }
    });
  }

  function buildHeaders(panel) {
    const headers = {
      'Accept': 'application/json',
      'Content-Type': 'application/json',
    };

    const apiKeyInput = panel.querySelector('[data-try-it-api-key]');
    if (apiKeyInput && apiKeyInput.value.trim()) {
      const name = apiKeyInput.placeholder || 'X-API-Key';
      headers[name] = apiKeyInput.value.trim();
    }

    const bearerInput = panel.querySelector('[data-try-it-bearer]');
    if (bearerInput && bearerInput.value.trim()) {
      headers['Authorization'] = 'Bearer ' + bearerInput.value.trim();
    }

    return headers;
  }

  if (window.Bengal && window.Bengal.enhance) {
    window.Bengal.enhance.register('api-explorer', (el) => initPanel(el));
  }

  ready(init);
})();
