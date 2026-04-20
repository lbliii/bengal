"""JavaScript client script for live reload."""

LIVE_RELOAD_SCRIPT = r"""
<script>
(function() {
    // Bengal Live Reload — double-buffered output eliminates FOUC
    let backoffMs = 1000;
    const maxBackoffMs = 10000;
    var BENGAL_OVERLAY_ID = 'bengal-build-error-overlay';

    function saveScroll() {
        sessionStorage.setItem('bengal_scroll_x', window.scrollX.toString());
        sessionStorage.setItem('bengal_scroll_y', window.scrollY.toString());
    }

    function cacheBustReload() {
        saveScroll();
        var url = new URL(location.href);
        url.searchParams.set('_bengal', Date.now().toString());
        location.replace(url.toString());
    }

    function escapeHTML(s) {
        return String(s == null ? '' : s)
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#39;');
    }

    function renderErrorOverlay(payload) {
        var errors = (payload && payload.errors) || [];
        if (!errors.length) { dismissErrorOverlay(); return; }
        var err = errors[0];
        var existing = document.getElementById(BENGAL_OVERLAY_ID);
        if (existing) existing.remove();

        var lines = (err.frame && err.frame.lines) || [];
        var frameHtml = lines.map(function(line) {
            var cls = line.is_error ? 'bengal-line is-error' : 'bengal-line';
            return '<div class="' + cls + '"><span class="bengal-ln">'
                + String(line.n) + '</span>' + escapeHTML(line.text) + '</div>';
        }).join('');

        var sugg = err.suggestions || [];
        var altsBlock = '';
        if (sugg.length > 0) {
            var topName = escapeHTML(sugg[0].value);
            var topHtml = '<p class="bengal-alt-top">Did you mean <code class="bengal-alt-top-name">'
                + topName + '</code>?</p>';
            var restHtml = '';
            if (sugg.length > 1) {
                var restItems = sugg.slice(1).map(function(s) {
                    return '<li>' + escapeHTML(s.value) + '</li>';
                }).join('');
                restHtml = '<p class="bengal-alt-others-label">Other close matches</p>'
                    + '<ul class="bengal-alts">' + restItems + '</ul>';
            }
            altsBlock = '<div class="bengal-section"><h4>Did you mean?</h4>'
                + topHtml + restHtml + '</div>';
        }

        var fileLoc = '';
        if (err.frame) {
            fileLoc = escapeHTML(err.frame.file_abs || err.frame.file || '');
            if (err.frame.line) {
                fileLoc += ':' + err.frame.line;
                if (err.frame.column) fileLoc += ':' + err.frame.column;
            }
        }

        var docs = err.docs_url ? '<div class="bengal-section"><a class="bengal-link" href="' + escapeHTML(err.docs_url) + '" target="_blank">' + escapeHTML(err.docs_url) + '</a></div>' : '';

        var hint = err.hint ? '<div class="bengal-section bengal-hint">' + escapeHTML(err.hint) + '</div>' : '';

        var moreCount = errors.length - 1;
        var moreNote = moreCount > 0 ? '<div class="bengal-more">+ ' + moreCount + ' more error' + (moreCount === 1 ? '' : 's') + '</div>' : '';

        var overlay = document.createElement('div');
        overlay.id = BENGAL_OVERLAY_ID;
        overlay.innerHTML = ''
            + '<div class="bengal-backdrop"></div>'
            + '<div class="bengal-card" role="alertdialog" aria-modal="true" aria-labelledby="bengal-overlay-title">'
            +   '<header class="bengal-header">'
            +     '<span class="bengal-badge">' + escapeHTML(err.code || 'ERROR') + '</span>'
            +     '<span class="bengal-subtitle">' + escapeHTML(err.title || 'Build Error') + '</span>'
            +   '</header>'
            +   '<h1 id="bengal-overlay-title" class="bengal-title">' + escapeHTML(err.message || 'Build error') + '</h1>'
            +   '<div class="bengal-fileloc">' + fileLoc + '</div>'
            +   (frameHtml ? '<pre class="bengal-frame">' + frameHtml + '</pre>' : '')
            +   hint
            +   altsBlock
            +   docs
            +   moreNote
            + '</div>';
        document.body.appendChild(overlay);
        injectOverlayStyles();
    }

    function injectOverlayStyles() {
        if (document.getElementById('bengal-overlay-styles')) return;
        var style = document.createElement('style');
        style.id = 'bengal-overlay-styles';
        style.textContent = ''
            + '#' + BENGAL_OVERLAY_ID + ' { position: fixed; inset: 0; z-index: 2147483647; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; color: #e6e6e6; }'
            + '#' + BENGAL_OVERLAY_ID + ' .bengal-backdrop { position: absolute; inset: 0; background: rgba(13, 17, 23, 0.92); }'
            + '#' + BENGAL_OVERLAY_ID + ' .bengal-card { position: relative; max-width: 920px; margin: 4vh auto; background: #161b22; border: 1px solid #30363d; border-radius: 8px; padding: 1.5rem; box-shadow: 0 20px 60px rgba(0,0,0,0.5); max-height: 92vh; overflow-y: auto; }'
            + '#' + BENGAL_OVERLAY_ID + ' .bengal-badge { display: inline-block; padding: 0.15rem 0.5rem; border-radius: 4px; background: rgba(255,92,92,0.12); color: #ff5c5c; font: 600 0.78rem/1.2 ui-monospace, SFMono-Regular, Menlo, monospace; letter-spacing: 0.04em; text-transform: uppercase; margin-right: 0.6rem; }'
            + '#' + BENGAL_OVERLAY_ID + ' .bengal-subtitle { color: #9aa0a6; font-size: 0.92rem; }'
            + '#' + BENGAL_OVERLAY_ID + ' .bengal-title { font-size: 1.5rem; font-weight: 600; color: #ff5c5c; margin: 0.5rem 0 0.4rem 0; }'
            + '#' + BENGAL_OVERLAY_ID + ' .bengal-fileloc { color: #9aa0a6; font: 400 0.92rem/1.4 ui-monospace, SFMono-Regular, Menlo, monospace; margin-bottom: 1rem; }'
            + '#' + BENGAL_OVERLAY_ID + ' .bengal-frame { margin: 0 0 1rem 0; padding: 0.75rem 0; background: #0d1117; border: 1px solid #30363d; border-radius: 6px; font: 400 0.85rem/1.5 ui-monospace, SFMono-Regular, Menlo, monospace; overflow-x: auto; }'
            + '#' + BENGAL_OVERLAY_ID + ' .bengal-line { display: block; padding: 0.05rem 1rem; white-space: pre; }'
            + '#' + BENGAL_OVERLAY_ID + ' .bengal-line.is-error { background: rgba(255,92,92,0.12); border-left: 3px solid #ff5c5c; padding-left: calc(1rem - 3px); }'
            + '#' + BENGAL_OVERLAY_ID + ' .bengal-ln { display: inline-block; width: 3.5em; color: #9aa0a6; text-align: right; user-select: none; margin-right: 0.75em; }'
            + '#' + BENGAL_OVERLAY_ID + ' .bengal-section { margin-top: 0.75rem; }'
            + '#' + BENGAL_OVERLAY_ID + ' .bengal-hint { color: #6ee7b7; }'
            + '#' + BENGAL_OVERLAY_ID + ' .bengal-section h4 { margin: 0 0 0.4rem 0; font: 600 0.78rem/1.2 ui-monospace, SFMono-Regular, Menlo, monospace; color: #9aa0a6; letter-spacing: 0.04em; text-transform: uppercase; }'
            + '#' + BENGAL_OVERLAY_ID + ' .bengal-alt-top { margin: 0 0 0.5rem 0; font-size: 1rem; color: #e6e6e6; }'
            + '#' + BENGAL_OVERLAY_ID + ' .bengal-alt-top-name { padding: 0.1rem 0.4rem; border-radius: 4px; background: #1f242c; border: 1px solid #30363d; color: #6ee7b7; font: 600 0.95rem/1.3 ui-monospace, SFMono-Regular, Menlo, monospace; }'
            + '#' + BENGAL_OVERLAY_ID + ' .bengal-alt-others-label { margin: 0.4rem 0 0.3rem 0; color: #9aa0a6; font: 400 0.85rem/1.2 ui-monospace, SFMono-Regular, Menlo, monospace; text-transform: uppercase; letter-spacing: 0.04em; }'
            + '#' + BENGAL_OVERLAY_ID + ' .bengal-alts { list-style: none; margin: 0; padding: 0; }'
            + '#' + BENGAL_OVERLAY_ID + ' .bengal-alts li { display: inline-block; margin: 0.15rem 0.4rem 0.15rem 0; padding: 0.15rem 0.5rem; border-radius: 4px; background: #1f242c; border: 1px solid #30363d; font: 400 0.85rem/1.2 ui-monospace, SFMono-Regular, Menlo, monospace; }'
            + '#' + BENGAL_OVERLAY_ID + ' .bengal-link { color: #58a6ff; }'
            + '#' + BENGAL_OVERLAY_ID + ' .bengal-more { margin-top: 0.75rem; color: #9aa0a6; font-size: 0.85rem; }';
        document.head.appendChild(style);
    }

    function dismissErrorOverlay() {
        var overlay = document.getElementById(BENGAL_OVERLAY_ID);
        if (overlay) overlay.remove();
    }

    function isOnOverlayPage() {
        // The HTML overlay renderer marks the document with this attribute,
        // so we can tell when the *page itself* is the error placeholder
        // (vs. a healthy page that has a live overlay drawn on top).
        return document.documentElement.getAttribute('data-bengal-overlay') === '1';
    }

    function executeReload(action, changedPaths) {
        if (action === 'reload' || action === 'reload-page') {
            console.log(action === 'reload' ? '🔄 Bengal: Reloading page...' : '📄 Bengal: Reloading current page...');
            cacheBustReload();
        } else if (action === 'reload-css') {
            console.log('🎨 Bengal: Reloading CSS...', changedPaths);
            var links = document.querySelectorAll('link[rel="stylesheet"]');
            var now = Date.now();
            links.forEach(function(link) {
                var href = link.getAttribute('href');
                if (!href) return;
                var url = new URL(href, window.location.origin);
                if (changedPaths.length > 0) {
                    var path = url.pathname.replace(/^\//, '');
                    if (!changedPaths.includes(path)) return;
                }
                url.searchParams.set('v', now.toString());
                var newLink = link.cloneNode();
                newLink.href = url.toString();
                newLink.onload = function() { link.remove(); };
                link.parentNode.insertBefore(newLink, link.nextSibling);
            });
        }
    }

    function connect() {
        var source = new EventSource('/__bengal_reload__');
        var closeSource = function() { try { source.close(); } catch (e) {} };
        window.addEventListener('beforeunload', closeSource, { once: true });
        window.addEventListener('pagehide', closeSource, { once: true });

        source.onmessage = function(event) {
            var payload = null;
            try { payload = JSON.parse(event.data); } catch (e) {}
            var type = payload && payload.type;
            var action = payload && payload.action ? payload.action : event.data;
            var changedPaths = (payload && payload.changedPaths) || [];

            if (type === 'build_error') {
                console.log('🔴 Bengal: Build error');
                renderErrorOverlay(payload);
                return;
            }
            if (type === 'build_ok') {
                console.log('✅ Bengal: Build recovered');
                dismissErrorOverlay();
                // If the page itself is the error placeholder, we have to
                // do a full reload to fetch the now-healthy page; otherwise
                // dismissing the overlay leaves the previously-good page
                // intact for the user.
                if (isOnOverlayPage()) cacheBustReload();
                return;
            }

            if (action === 'fragment') {
                var selector = payload.selector || '#main-content';
                var html = payload.html;
                var permalink = payload.permalink || '';
                var norm = function(s) {
                    return s === '/' ? '/' : (s.replace(/\/$/, '') || '/');
                };
                var match = !permalink || norm(location.pathname) === norm(permalink);
                if (html && match) {
                    var target = document.querySelector(selector);
                    if (target) {
                        target.innerHTML = html;
                        console.log('📄 Bengal: Content updated');
                    } else {
                        cacheBustReload();
                    }
                }
                return;
            }

            executeReload(action, changedPaths);
        };

        window.addEventListener('load', function() {
            var scrollX = sessionStorage.getItem('bengal_scroll_x');
            var scrollY = sessionStorage.getItem('bengal_scroll_y');
            if (scrollX !== null && scrollY !== null) {
                window.scrollTo(parseInt(scrollX, 10), parseInt(scrollY, 10));
                sessionStorage.removeItem('bengal_scroll_x');
                sessionStorage.removeItem('bengal_scroll_y');
            }
            var clean = new URL(location.href);
            if (clean.searchParams.has('_bengal')) {
                clean.searchParams.delete('_bengal');
                history.replaceState(null, '', clean.toString());
            }
        });

        source.onopen = function() {
            backoffMs = 1000;
            console.log('🚀 Bengal: Live reload connected');
        };

        source.onerror = function() {
            console.log('⚠️  Bengal: Live reload disconnected - retrying soon');
            try { source.close(); } catch (e) {}
            setTimeout(connect, backoffMs);
            backoffMs = Math.min(maxBackoffMs, Math.floor(backoffMs * 1.5));
        };
    }

    connect();
})();
</script>
"""
