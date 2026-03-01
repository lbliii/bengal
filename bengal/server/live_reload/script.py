"""JavaScript client script for live reload."""

LIVE_RELOAD_SCRIPT = r"""
<script>
(function() {
    // Bengal Live Reload
    let backoffMs = 1000;
    const maxBackoffMs = 10000;

    function connect() {
        const source = new EventSource('/__bengal_reload__');
        // Ensure the connection is closed on page unload/navigation to free server threads quickly
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
                console.log('🔄 Bengal: Reloading page...');
                // Save scroll position before reload
                sessionStorage.setItem('bengal_scroll_x', window.scrollX.toString());
                sessionStorage.setItem('bengal_scroll_y', window.scrollY.toString());
                // Cache-bust: location.reload() can serve cached HTML despite Cache-Control
                const url = new URL(location.href);
                url.searchParams.set('_bengal', Date.now().toString());
                location.replace(url.toString());
            } else if (action === 'reload-css') {
                console.log('🎨 Bengal: Reloading CSS...', reason || '', changedPaths);
                const links = document.querySelectorAll('link[rel="stylesheet"]');
                const now = Date.now();
                links.forEach(link => {
                    const href = link.getAttribute('href');
                    if (!href) return;
                    const url = new URL(href, window.location.origin);
                    // If targeted list provided, only reload those
                    if (changedPaths.length > 0) {
                        const path = url.pathname.replace(/^\//, '');
                        if (!changedPaths.includes(path)) return;
                    }
                    // Bust cache with a version param
                    url.searchParams.set('v', now.toString());
                    // Replace the link to trigger reload
                    const newLink = link.cloneNode();
                    newLink.href = url.toString();
                    newLink.onload = () => {
                        // Remove old link after new CSS loads
                        link.remove();
                    };
                    link.parentNode.insertBefore(newLink, link.nextSibling);
                });
            } else if (action === 'reload-page') {
                console.log('📄 Bengal: Reloading current page...');
                // Save scroll position before reload
                sessionStorage.setItem('bengal_scroll_x', window.scrollX.toString());
                sessionStorage.setItem('bengal_scroll_y', window.scrollY.toString());
                // Cache-bust: location.reload() can serve cached HTML despite Cache-Control
                const url = new URL(location.href);
                url.searchParams.set('_bengal', Date.now().toString());
                location.replace(url.toString());
            }
        };

        // Restore scroll position after page load
        window.addEventListener('load', function() {
            const scrollX = sessionStorage.getItem('bengal_scroll_x');
            const scrollY = sessionStorage.getItem('bengal_scroll_y');
            if (scrollX !== null && scrollY !== null) {
                window.scrollTo(parseInt(scrollX, 10), parseInt(scrollY, 10));
                // Clear stored position after restoring
                sessionStorage.removeItem('bengal_scroll_x');
                sessionStorage.removeItem('bengal_scroll_y');
            }
        });

        source.onopen = function() {
            backoffMs = 1000; // reset on successful connection
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
