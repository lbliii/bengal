// Bengal Live Reload (client)
(function() {
  'use strict';

  if (window.__BENGAL_LIVE_RELOAD__) return;
  window.__BENGAL_LIVE_RELOAD__ = true;

  let backoffMs = 1000;
  const maxBackoffMs = 10000;

  function connect() {
    const source = new EventSource('/__bengal_reload__');
    const closeSource = () => { try { source.close(); } catch (e) {} };
    window.addEventListener('beforeunload', closeSource, { once: true });
    window.addEventListener('pagehide', closeSource, { once: true });

    source.onmessage = function(event) {
      let payload = null;
      try { payload = JSON.parse(event.data); } catch (e) {}

      const action = payload && payload.action ? payload.action : event.data;
      const changedPaths = (payload && payload.changedPaths) || [];
      const reason = (payload && payload.reason) || '';

      if (action === 'reload') {
        try {
          sessionStorage.setItem('bengal_scroll_x', String(window.scrollX));
          sessionStorage.setItem('bengal_scroll_y', String(window.scrollY));
        } catch (e) {}
        location.reload();
      } else if (action === 'reload-css') {
        const links = document.querySelectorAll('link[rel="stylesheet"]');
        const now = Date.now();
        links.forEach(link => {
          const href = link.getAttribute('href');
          if (!href) return;
          const url = new URL(href, window.location.origin);
          if (changedPaths.length > 0) {
            const path = url.pathname.replace(/^\//, '');
            if (!changedPaths.includes(path)) return;
          }
          url.searchParams.set('v', String(now));
          const newLink = link.cloneNode();
          newLink.href = url.toString();
          newLink.onload = () => { try { link.remove(); } catch (e) {} };
          link.parentNode.insertBefore(newLink, link.nextSibling);
        });
      } else if (action === 'reload-page') {
        try {
          sessionStorage.setItem('bengal_scroll_x', String(window.scrollX));
          sessionStorage.setItem('bengal_scroll_y', String(window.scrollY));
        } catch (e) {}
        location.reload();
      }
    };

    window.addEventListener('load', function() {
      try {
        const sx = sessionStorage.getItem('bengal_scroll_x');
        const sy = sessionStorage.getItem('bengal_scroll_y');
        if (sx !== null && sy !== null) {
          window.scrollTo(parseInt(sx, 10), parseInt(sy, 10));
          sessionStorage.removeItem('bengal_scroll_x');
          sessionStorage.removeItem('bengal_scroll_y');
        }
      } catch (e) {}
    });

    source.onopen = function() { backoffMs = 1000; };
    source.onerror = function() {
      try { source.close(); } catch (e) {}
      setTimeout(connect, backoffMs);
      backoffMs = Math.min(maxBackoffMs, Math.floor(backoffMs * 1.5));
    };
  }

  connect();
})();


