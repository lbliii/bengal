/**
 * Bengal SSG - Contextual Graph Minimap (v3, dependency-free)
 *
 * Renders the small "graph node per page" minimap in the right sidebar: the
 * current page plus its directly-connected pages.
 *
 * v3 removes D3 and the runtime force simulation entirely. Layout is now baked
 * at BUILD time (deterministic, seeded) and shipped in each page's per-page JSON
 * under `.graph` — every node already carries normalized `x`/`y` in [0, 1]. This
 * file just maps those coordinates into a tiny inline <svg>. The data is fetched
 * the same way link previews fetch per-page JSON.
 *
 * Why so small now: no layout math, no physics, no zoom library, no
 * getComputedStyle color resolution (theme colors are applied via
 * `style="fill: var(--graph-node-*)"`, which the CSS cascade re-resolves on
 * theme/palette switch automatically — no event listeners needed).
 *
 * @module graph-contextual
 */

(function () {
    'use strict';

    var SVG_NS = 'http://www.w3.org/2000/svg';
    var XHTML_NS = 'http://www.w3.org/1999/xhtml';
    var VIEW = 200;        // viewBox extent (coords are scaled from [0,1])
    var PAD = 14;          // inset so nodes/labels aren't clipped at the edge
    var MAX_CONNECTIONS = 15;

    function pageJsonUrl() {
        var path = window.location.pathname;
        var dir = path.charAt(path.length - 1) === '/'
            ? path
            : path.substring(0, path.lastIndexOf('/') + 1);
        return dir + 'index.json';
    }

    function baseurl() {
        try {
            var m = document.querySelector('meta[name="bengal:baseurl"]');
            return ((m && m.getAttribute('content')) || '').replace(/\/$/, '');
        } catch (e) {
            return '';
        }
    }

    function normalizeUrl(url) {
        if (!url) return '';
        var n = url;
        if (n.indexOf('http://') === 0 || n.indexOf('https://') === 0) {
            try { n = new URL(n).pathname; } catch (e) { /* keep raw */ }
        }
        n = n.replace(/\/+$/, '') || '/';
        if (n.charAt(0) !== '/') n = '/' + n;
        return n;
    }

    /** Project a baked [0,1] coordinate into the viewBox. */
    function project(v) {
        return PAD + v * (VIEW - 2 * PAD);
    }

    function el(name, attrs) {
        var node = document.createElementNS(SVG_NS, name);
        if (attrs) {
            for (var k in attrs) {
                if (Object.prototype.hasOwnProperty.call(attrs, k)) {
                    node.setAttribute(k, attrs[k]);
                }
            }
        }
        return node;
    }

    /**
     * Build the inline <svg> for a baked neighborhood graph.
     * @param {{nodes: Array, edges: Array}} graph
     * @returns {SVGElement}
     */
    function buildSvg(graph) {
        var svg = el('svg', {
            width: VIEW,
            height: VIEW,
            viewBox: '0 0 ' + VIEW + ' ' + VIEW,
            class: 'graph-svg-visible',
            role: 'img',
            'aria-label': 'Graph of pages linked to this page'
        });

        var byId = {};
        graph.nodes.forEach(function (n) { byId[n.id] = n; });

        // Edges first (behind nodes).
        var linksGroup = el('g', { class: 'graph-links' });
        (graph.edges || []).forEach(function (e) {
            var s = byId[typeof e.source === 'object' ? e.source.id : e.source];
            var t = byId[typeof e.target === 'object' ? e.target.id : e.target];
            if (!s || !t) return;
            linksGroup.appendChild(el('line', {
                class: 'graph-link',
                x1: project(s.x), y1: project(s.y),
                x2: project(t.x), y2: project(t.y)
            }));
        });
        svg.appendChild(linksGroup);

        // Nodes (each wrapped in a link, except the current page).
        var nodesGroup = el('g', { class: 'graph-nodes' });
        graph.nodes.forEach(function (n) {
            var r = n.isCurrent ? 8 : (n.isPreviousPage ? 6 : 5);
            var cls = 'graph-node graph-node-' + (n.type || 'regular');
            if (n.isCurrent) cls += ' graph-node-current';
            if (n.isPreviousPage) cls += ' graph-node-previous';

            var circle = el('circle', {
                class: cls,
                cx: project(n.x),
                cy: project(n.y),
                r: r,
                // Theme-aware fill via CSS var — re-resolves on theme switch with
                // zero JS (the payload's color is e.g. "var(--graph-node-hub)").
                style: 'fill: ' + (n.color || 'var(--graph-node-regular)')
            });
            var title = el('title');
            title.textContent = n.label || 'Untitled';
            circle.appendChild(title);

            if (n.isCurrent || !n.url) {
                nodesGroup.appendChild(circle);
            } else {
                var link = el('a');
                var href = n.url;
                link.setAttributeNS('http://www.w3.org/1999/xlink', 'href', href);
                link.setAttribute('href', href); // SVG2 / modern browsers
                link.appendChild(circle);
                nodesGroup.appendChild(link);
            }
        });
        svg.appendChild(nodesGroup);

        return svg;
    }

    function markPreviousPage(nodes) {
        var tracker = window.bengalSessionPath;
        if (!tracker || !tracker.getPreviousPage || !tracker.getPreviousPage()) return;
        nodes.forEach(function (n) {
            if (tracker.isPreviousPage && tracker.isPreviousPage(normalizeUrl(n.url))) {
                n.isPreviousPage = true;
            }
        });
    }

    /** Filter a full graph.json down to the current page's neighborhood. */
    function filterGlobal(data, currentUrl) {
        if (!data || !data.nodes || !data.edges) return null;
        var cur = normalizeUrl(currentUrl);
        var current = data.nodes.find(function (n) { return normalizeUrl(n.url) === cur; });
        if (!current) return null;

        var keep = {};
        keep[current.id] = true;
        var edges = data.edges.filter(function (e) {
            var s = typeof e.source === 'object' ? e.source.id : e.source;
            var t = typeof e.target === 'object' ? e.target.id : e.target;
            return s === current.id || t === current.id;
        });
        edges.forEach(function (e) {
            var s = typeof e.source === 'object' ? e.source.id : e.source;
            var t = typeof e.target === 'object' ? e.target.id : e.target;
            keep[s === current.id ? t : s] = true;
        });

        var nodes = data.nodes
            .filter(function (n) { return keep[n.id]; })
            .sort(function (a, b) {
                return ((b.incoming_refs || 0) + (b.outgoing_refs || 0)) -
                       ((a.incoming_refs || 0) + (a.outgoing_refs || 0));
            })
            .slice(0, MAX_CONNECTIONS)
            .map(function (n) { return Object.assign({}, n); });

        var ids = {};
        nodes.forEach(function (n) {
            ids[n.id] = true;
            n.isCurrent = n.id === current.id;
        });
        var filteredEdges = data.edges.filter(function (e) {
            var s = typeof e.source === 'object' ? e.source.id : e.source;
            var t = typeof e.target === 'object' ? e.target.id : e.target;
            return ids[s] && ids[t];
        });

        // Without baked positions (global fallback path) place radially so the
        // minimap still renders. Current page centered; others on a ring.
        var hasPositions = nodes.every(function (n) {
            return typeof n.x === 'number' && typeof n.y === 'number';
        });
        if (!hasPositions) {
            var others = nodes.filter(function (n) { return !n.isCurrent; });
            nodes.forEach(function (n) { if (n.isCurrent) { n.x = 0.5; n.y = 0.5; } });
            others.forEach(function (n, i) {
                var a = (2 * Math.PI * i) / Math.max(others.length, 1);
                n.x = 0.5 + 0.36 * Math.cos(a);
                n.y = 0.5 + 0.36 * Math.sin(a);
            });
        }

        return { nodes: nodes, edges: filteredEdges };
    }

    function addExpandButton(wrapper) {
        var btn = document.createElement('div');
        btn.className = 'graph-contextual-expand';
        btn.setAttribute('role', 'button');
        btn.setAttribute('aria-label', 'Expand to full graph');
        btn.setAttribute('data-tooltip-position', 'top');
        btn.innerHTML = '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" ' +
            'viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" ' +
            'stroke-linecap="round" stroke-linejoin="round" class="svg-icon lucide-arrow-up-right">' +
            '<path d="M7 7h10v10"></path><path d="M7 17 17 7"></path></svg>';
        btn.addEventListener('click', function () {
            window.location.href = baseurl() + '/graph/';
        });
        wrapper.appendChild(btn);
    }

    function render(container, graph) {
        if (!graph || !graph.nodes || graph.nodes.length === 0) {
            container.style.display = 'none';
            return;
        }
        var wrapper = container.querySelector('.graph-contextual-container');
        if (!wrapper) {
            wrapper = document.createElement('div');
            wrapper.className = 'graph-contextual-container';
            container.appendChild(wrapper);
        }
        wrapper.classList.remove('graph-loading');
        wrapper.innerHTML = '';
        wrapper.appendChild(buildSvg(graph));
        wrapper.classList.add('graph-loaded', 'graph-visible');
        container.classList.add('graph-has-data');
        addExpandButton(wrapper);
    }

    function hide(container) {
        var wrapper = container.querySelector('.graph-contextual-container');
        if (wrapper) wrapper.style.display = 'none';
        container.style.display = 'none';
    }

    function load(container) {
        var currentUrl = container.dataset.pageUrl || window.location.pathname;
        var controller = ('AbortController' in window) ? new AbortController() : null;
        var signal = controller ? controller.signal : undefined;
        container._graphAbort = controller;

        // Preferred: this page's own JSON, which already carries a baked,
        // pre-filtered `.graph` neighborhood.
        fetch(pageJsonUrl(), { signal: signal })
            .then(function (r) { return r.ok ? r.json() : null; })
            .then(function (data) {
                if (data && data.graph && data.graph.nodes && data.graph.nodes.length) {
                    var graph = data.graph;
                    var cur = normalizeUrl(currentUrl);
                    graph.nodes.forEach(function (n) {
                        n.isCurrent = normalizeUrl(n.url) === cur;
                    });
                    markPreviousPage(graph.nodes);
                    render(container, graph);
                    return;
                }
                // Fallback: derive the neighborhood from the global graph.json.
                return fetch(baseurl() + '/graph/graph.json', { signal: signal })
                    .then(function (r) { return r.ok ? r.json() : null; })
                    .then(function (full) {
                        var graph = filterGlobal(full, currentUrl);
                        if (graph) markPreviousPage(graph.nodes);
                        if (graph) render(container, graph); else hide(container);
                    });
            })
            .catch(function () { hide(container); });
    }

    var observer = null;

    function init() {
        var container = document.querySelector('.graph-contextual');
        if (!container) return;

        if ('IntersectionObserver' in window) {
            observer = new IntersectionObserver(function (entries) {
                entries.forEach(function (entry) {
                    if (entry.isIntersecting) {
                        observer.disconnect();
                        observer = null;
                        load(container);
                    }
                });
            }, { rootMargin: '100px' });
            observer.observe(container);
        } else {
            load(container);
        }
    }

    function cleanup() {
        if (observer) { observer.disconnect(); observer = null; }
        var container = document.querySelector('.graph-contextual');
        if (container && container._graphAbort) {
            try { container._graphAbort.abort(); } catch (e) { /* noop */ }
        }
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }

    window.addEventListener('pagehide', cleanup);
    window.addEventListener('beforeunload', cleanup);
    document.addEventListener('turbo:load', function () { cleanup(); init(); });
    document.addEventListener('turbo:before-visit', cleanup);
    document.addEventListener('pjax:end', function () { cleanup(); init(); });
})();
