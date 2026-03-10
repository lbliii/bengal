"""JavaScript client script for live reload."""

LIVE_RELOAD_SCRIPT = r"""
<script>
(function() {
    // Bengal Live Reload — double-buffered output eliminates FOUC
    let backoffMs = 1000;
    const maxBackoffMs = 10000;

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
            var action = payload && payload.action ? payload.action : event.data;
            var changedPaths = (payload && payload.changedPaths) || [];

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
