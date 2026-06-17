/**
 * Bengal SSG - Knowledge Graph Explorer (dependency-free, Canvas)
 *
 * Full-page interactive knowledge graph for the /graph/ page. Replaces a
 * D3 + SVG implementation that choked at scale: SVG creates one DOM element per
 * node and per edge, so thousands of them melt the browser's layout/paint.
 *
 * This renderer:
 * - Has NO dependencies (no D3) and runs NO force simulation. Node positions are
 *   baked at build time (deterministic) and shipped in graph.json as normalized
 *   `x`/`y` in [0, 1]. We just draw them — so it never chokes on layout.
 * - Draws everything to a single <canvas> (devicePixelRatio-aware) with viewport
 *   culling, color-batched nodes, and level-of-detail labels.
 * - Supports pan (drag), zoom-toward-cursor (wheel), fit-to-view, hover
 *   tooltips + neighbor highlighting, click-to-navigate, debounced search, type
 *   filter, and ?tag= filtering with the existing badge.
 * - Resolves theme colors from CSS custom properties, re-resolving on
 *   `themechange` / `palettechange`.
 * - Emits a hidden-but-in-DOM <ul> of real <a> links so the graph's
 *   relationships are crawlable and screen-reader / keyboard navigable.
 *
 * @module bengal-graph-explorer
 */

(function () {
    'use strict';

    var WORLD = 2000;          // world extent that [0,1] coords map into
    var MIN_SCALE = 0.05;
    var MAX_SCALE = 5;
    var LABEL_SCALE = 0.9;     // draw labels once zoomed past this
    var GRID_CELL = 80;        // picking grid cell size (world units)

    // Note: fit-to-view snaps instantly (no entrance animation), so there is
    // nothing to gate behind prefers-reduced-motion here.

    // ---- State ---------------------------------------------------------------
    var canvas, ctx, container, loadingEl, tooltipEl, searchInput, filterSelect;
    var dpr = window.devicePixelRatio || 1;
    var nodes = [], edges = [], nodeById = {}, adjacency = {};
    var grid = {};             // picking grid: "cx,cy" -> [node, ...]
    var camera = { scale: 1, tx: 0, ty: 0 };
    var colors = {};
    var hovered = null;
    var dirty = false;
    var rafPending = false;
    var listeners = [];

    // search / filter
    var query = '';
    var typeFilter = 'all';
    var tagParam = null;

    function on(target, event, handler, opts) {
        target.addEventListener(event, handler, opts);
        listeners.push([target, event, handler, opts]);
    }

    // ---- Coordinate transforms ----------------------------------------------
    function worldX(nx) { return nx * WORLD; }
    function worldY(ny) { return ny * WORLD; }
    function toScreenX(wx) { return wx * camera.scale + camera.tx; }
    function toScreenY(wy) { return wy * camera.scale + camera.ty; }
    function toWorldX(sx) { return (sx - camera.tx) / camera.scale; }
    function toWorldY(sy) { return (sy - camera.ty) / camera.scale; }

    function requestRedraw() {
        dirty = true;
        if (rafPending) return;
        rafPending = true;
        requestAnimationFrame(function () {
            rafPending = false;
            if (dirty) draw();
        });
    }

    // ---- Theme colors --------------------------------------------------------
    function resolveColors() {
        var cs = getComputedStyle(document.documentElement);
        function v(name, fallback) {
            return (cs.getPropertyValue(name) || '').trim() || fallback;
        }
        colors = {
            hub: v('--graph-node-hub', '#FF9500'),
            regular: v('--graph-node-regular', '#E8E0D8'),
            orphan: v('--graph-node-orphan', '#FF5A5A'),
            generated: v('--graph-node-generated', '#4ECDC4'),
            link: v('--graph-link-color', 'rgba(100,100,100,0.25)'),
            linkHi: v('--graph-link-highlight', 'rgba(255,200,120,0.95)'),
            label: v('--color-text', '#222'),
            labelBg: v('--color-bg', '#fff')
        };
    }
    function nodeColor(n) { return colors[n.type] || colors.regular; }

    // ---- Picking grid --------------------------------------------------------
    function gridKey(wx, wy) {
        return Math.floor(wx / GRID_CELL) + ',' + Math.floor(wy / GRID_CELL);
    }
    function buildGrid() {
        grid = {};
        nodes.forEach(function (n) {
            var k = gridKey(n.wx, n.wy);
            (grid[k] || (grid[k] = [])).push(n);
        });
    }
    function pick(sx, sy) {
        var wx = toWorldX(sx), wy = toWorldY(sy);
        var cx = Math.floor(wx / GRID_CELL), cy = Math.floor(wy / GRID_CELL);
        var best = null, bestD = Infinity;
        for (var gx = cx - 1; gx <= cx + 1; gx++) {
            for (var gy = cy - 1; gy <= cy + 1; gy++) {
                var bucket = grid[gx + ',' + gy];
                if (!bucket) continue;
                for (var i = 0; i < bucket.length; i++) {
                    var n = bucket[i];
                    var dx = n.wx - wx, dy = n.wy - wy;
                    var d2 = dx * dx + dy * dy;
                    var r = n.size + 4;
                    if (d2 <= r * r && d2 < bestD) { bestD = d2; best = n; }
                }
            }
        }
        return best;
    }

    // ---- Visibility / filtering ---------------------------------------------
    function nodeMatchesTag(n) {
        if (!tagParam) return true;
        return (n.tags || []).some(function (t) {
            return t.toLowerCase() === tagParam.toLowerCase();
        });
    }
    function isVisible(n) {
        if (tagParam && !nodeMatchesTag(n)) return false;
        var matchesSearch = !query ||
            (n.label || '').toLowerCase().indexOf(query) !== -1 ||
            (n.tags || []).some(function (t) { return t.toLowerCase().indexOf(query) !== -1; });
        var matchesType = typeFilter === 'all' || n.type === typeFilter;
        return matchesSearch && matchesType;
    }

    // ---- Rendering -----------------------------------------------------------
    function draw() {
        dirty = false;
        var W = canvas.width, H = canvas.height;
        ctx.setTransform(1, 0, 0, 1, 0, 0);
        ctx.clearRect(0, 0, W, H);
        ctx.scale(dpr, dpr);

        var vw = W / dpr, vh = H / dpr;
        var pad = 50;

        var hoverSet = null;
        if (hovered) {
            hoverSet = adjacency[hovered.id] || {};
        }

        // Edges
        ctx.lineWidth = 1;
        for (var i = 0; i < edges.length; i++) {
            var e = edges[i];
            var s = e._s, t = e._t;
            if (!s || !t) continue;
            var sVis = isVisible(s), tVis = isVisible(t);
            if (!sVis || !tVis) continue;
            var sx = toScreenX(s.wx), sy = toScreenY(s.wy);
            var tx = toScreenX(t.wx), ty = toScreenY(t.wy);
            // cull: both endpoints off the same side
            if ((sx < -pad && tx < -pad) || (sx > vw + pad && tx > vw + pad) ||
                (sy < -pad && ty < -pad) || (sy > vh + pad && ty > vh + pad)) continue;

            var isHi = hovered && (e.source === hovered.id || e.target === hovered.id);
            ctx.strokeStyle = isHi ? colors.linkHi : colors.link;
            ctx.globalAlpha = hovered ? (isHi ? 1 : 0.08) : (e.weight === 2 ? 0.7 : 0.5);
            ctx.beginPath();
            ctx.moveTo(sx, sy);
            ctx.lineTo(tx, ty);
            ctx.stroke();
        }
        ctx.globalAlpha = 1;

        // Nodes — batch by color to minimize fillStyle churn.
        var batches = {};
        for (var j = 0; j < nodes.length; j++) {
            var n = nodes[j];
            var sxn = toScreenX(n.wx), syn = toScreenY(n.wy);
            if (sxn < -pad || sxn > vw + pad || syn < -pad || syn > vh + pad) continue;
            var col = nodeColor(n);
            (batches[col] || (batches[col] = [])).push(n);
        }
        for (var col2 in batches) {
            if (!Object.prototype.hasOwnProperty.call(batches, col2)) continue;
            ctx.fillStyle = col2;
            var list = batches[col2];
            for (var b = 0; b < list.length; b++) {
                var nd = list[b];
                var visible = isVisible(nd);
                var dim = (!visible) || (hovered && hovered.id !== nd.id && !(hoverSet && hoverSet[nd.id]));
                ctx.globalAlpha = visible ? (dim ? (tagParam ? 0 : 0.12) : 1) : (tagParam ? 0 : 0.12);
                var r = Math.max(1.5, nd.size * Math.min(1, camera.scale * 1.2));
                ctx.beginPath();
                ctx.arc(toScreenX(nd.wx), toScreenY(nd.wy), r, 0, Math.PI * 2);
                ctx.fill();
            }
        }
        ctx.globalAlpha = 1;

        // Labels — only when zoomed in, or for hubs / the hovered node.
        var showLabels = camera.scale >= LABEL_SCALE;
        if (showLabels || hovered) {
            ctx.fillStyle = colors.label;
            ctx.font = '11px system-ui, sans-serif';
            ctx.textAlign = 'center';
            ctx.textBaseline = 'top';
            for (var l = 0; l < nodes.length; l++) {
                var ln = nodes[l];
                if (!isVisible(ln)) continue;
                var labelThis = (hovered && (ln.id === hovered.id || (hoverSet && hoverSet[ln.id]))) ||
                                (showLabels && (ln.type === 'hub' || camera.scale >= 1.6));
                if (!labelThis) continue;
                var lx = toScreenX(ln.wx), ly = toScreenY(ln.wy);
                if (lx < -pad || lx > vw + pad || ly < -pad || ly > vh + pad) continue;
                ctx.fillText(ln.label || '', lx, ly + ln.size + 2);
            }
        }
    }

    // ---- Camera --------------------------------------------------------------
    function fitToView() {
        if (!nodes.length) return;
        var minX = Infinity, maxX = -Infinity, minY = Infinity, maxY = -Infinity;
        nodes.forEach(function (n) {
            minX = Math.min(minX, n.wx); maxX = Math.max(maxX, n.wx);
            minY = Math.min(minY, n.wy); maxY = Math.max(maxY, n.wy);
        });
        var vw = canvas.width / dpr, vh = canvas.height / dpr;
        var pad = 80;
        var dx = (maxX - minX) || 1, dy = (maxY - minY) || 1;
        var scale = Math.min(MAX_SCALE, Math.min((vw - 2 * pad) / dx, (vh - 2 * pad) / dy));
        scale = Math.max(MIN_SCALE, scale);
        camera.scale = scale;
        camera.tx = vw / 2 - scale * (minX + maxX) / 2;
        camera.ty = vh / 2 - scale * (minY + maxY) / 2;
    }

    function zoomAt(sx, sy, factor) {
        var newScale = Math.max(MIN_SCALE, Math.min(MAX_SCALE, camera.scale * factor));
        var wx = toWorldX(sx), wy = toWorldY(sy);
        camera.scale = newScale;
        camera.tx = sx - wx * newScale;
        camera.ty = sy - wy * newScale;
        requestRedraw();
    }

    // ---- Tooltip -------------------------------------------------------------
    function showTooltip(evt, n) {
        if (!tooltipEl) return;
        var tags = (n.tags && n.tags.length)
            ? '<div class="tags">' + n.tags.map(function (t) {
                return '<span class="tag">' + escapeHtml(t) + '</span>';
            }).join('') + '</div>'
            : '';
        tooltipEl.innerHTML = '<h4>' + escapeHtml(n.label || 'Untitled') + '</h4>' +
            '<p>' + (n.reading_time || 0) + ' min read · ' +
            (n.incoming_refs || 0) + ' in / ' + (n.outgoing_refs || 0) + ' out</p>' + tags;
        tooltipEl.style.display = 'block';
        tooltipEl.style.left = (evt.clientX + 12) + 'px';
        tooltipEl.style.top = (evt.clientY + 12) + 'px';
    }
    function hideTooltip() { if (tooltipEl) tooltipEl.style.display = 'none'; }

    function escapeHtml(s) {
        return String(s).replace(/[&<>"']/g, function (c) {
            return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c];
        });
    }
    function normalizeUrl(url) {
        if (!url) return '';
        var n = url;
        if (n.indexOf('http://') === 0 || n.indexOf('https://') === 0) {
            try { n = new URL(n).pathname; } catch (e) { /* keep */ }
        }
        if (n.charAt(n.length - 1) !== '/' && n.indexOf('#') === -1) n += '/';
        return n;
    }

    // ---- Sizing --------------------------------------------------------------
    function resize() {
        var rect = container.getBoundingClientRect();
        var w = rect.width || window.innerWidth;
        var h = rect.height || window.innerHeight;
        dpr = window.devicePixelRatio || 1;
        canvas.width = Math.round(w * dpr);
        canvas.height = Math.round(h * dpr);
        canvas.style.width = w + 'px';
        canvas.style.height = h + 'px';
        requestRedraw();
    }

    // ---- Interaction ---------------------------------------------------------
    function setupInteraction() {
        var dragging = false, moved = false, lastX = 0, lastY = 0;

        on(canvas, 'mousedown', function (e) {
            dragging = true; moved = false; lastX = e.clientX; lastY = e.clientY;
        });
        on(window, 'mouseup', function () { dragging = false; });
        on(canvas, 'mousemove', function (e) {
            var rect = canvas.getBoundingClientRect();
            if (dragging) {
                var dx = e.clientX - lastX, dy = e.clientY - lastY;
                if (Math.abs(dx) + Math.abs(dy) > 2) moved = true;
                camera.tx += dx; camera.ty += dy;
                lastX = e.clientX; lastY = e.clientY;
                hideTooltip();
                requestRedraw();
                return;
            }
            var n = pick(e.clientX - rect.left, e.clientY - rect.top);
            if (n !== hovered) {
                hovered = n;
                canvas.style.cursor = n ? 'pointer' : 'grab';
                requestRedraw();
            }
            if (n) showTooltip(e, n); else hideTooltip();
        });
        on(canvas, 'mouseleave', function () { hovered = null; hideTooltip(); requestRedraw(); });
        on(canvas, 'click', function (e) {
            if (moved) return;
            var rect = canvas.getBoundingClientRect();
            var n = pick(e.clientX - rect.left, e.clientY - rect.top);
            if (n && n.url) window.location.href = normalizeUrl(n.url);
        });
        on(canvas, 'wheel', function (e) {
            e.preventDefault();
            var rect = canvas.getBoundingClientRect();
            var factor = e.deltaY < 0 ? 1.12 : 1 / 1.12;
            zoomAt(e.clientX - rect.left, e.clientY - rect.top, factor);
        }, { passive: false });

        on(window, 'resize', resize);
        on(window, 'themechange', function () { resolveColors(); requestRedraw(); });
        on(window, 'palettechange', function () { resolveColors(); requestRedraw(); });

        on(document, 'keydown', function (e) {
            if (e.key === '/' || (e.metaKey && e.key === 'k') || (e.ctrlKey && e.key === 'k')) {
                if (searchInput) { e.preventDefault(); searchInput.focus(); }
            } else if (e.key === 'Escape') {
                if (searchInput) searchInput.value = '';
                if (filterSelect) filterSelect.value = 'all';
                query = ''; typeFilter = 'all';
                requestRedraw();
            }
        });
    }

    function debounce(fn, ms) {
        var t = null;
        return function () {
            var args = arguments, self = this;
            if (t) clearTimeout(t);
            t = setTimeout(function () { t = null; fn.apply(self, args); }, ms);
        };
    }

    function setupControls() {
        searchInput = document.getElementById('search');
        filterSelect = document.getElementById('filter-type');
        if (searchInput) {
            on(searchInput, 'input', debounce(function () {
                query = searchInput.value.toLowerCase();
                requestRedraw();
            }, 150));
        }
        if (filterSelect) {
            on(filterSelect, 'change', function () {
                typeFilter = filterSelect.value;
                requestRedraw();
            });
        }

        // ?tag= filter
        var params = new URLSearchParams(window.location.search);
        tagParam = params.get('tag');
        if (tagParam) {
            if (searchInput) searchInput.value = tagParam;
            var badge = document.getElementById('tag-filter-badge');
            var valueEl = document.getElementById('tag-filter-value');
            if (badge && valueEl) { valueEl.textContent = tagParam; badge.classList.remove('hidden'); }
        }
    }

    // ---- Accessibility list --------------------------------------------------
    function buildA11yList() {
        var existing = document.getElementById('graph-a11y-list');
        if (existing) existing.remove();
        var ul = document.createElement('ul');
        ul.id = 'graph-a11y-list';
        ul.className = 'graph-a11y-list';
        ul.setAttribute('aria-label', 'All pages in the graph');
        var sorted = nodes.slice().sort(function (a, b) {
            return (a.label || '').localeCompare(b.label || '');
        });
        sorted.forEach(function (n) {
            if (!n.url) return;
            var li = document.createElement('li');
            var a = document.createElement('a');
            a.href = normalizeUrl(n.url);
            a.textContent = n.label || n.url;
            li.appendChild(a);
            ul.appendChild(li);
        });
        (document.getElementById('container') || document.body).appendChild(ul);
    }

    // ---- Boot ----------------------------------------------------------------
    function prepareData(data) {
        nodes = (data.nodes || []).map(function (n) {
            return Object.assign({}, n, { wx: worldX(n.x), wy: worldY(n.y) });
        });
        nodeById = {};
        adjacency = {};
        nodes.forEach(function (n) { nodeById[n.id] = n; adjacency[n.id] = {}; });
        edges = (data.edges || []).map(function (e) {
            var s = typeof e.source === 'object' ? e.source.id : e.source;
            var t = typeof e.target === 'object' ? e.target.id : e.target;
            if (adjacency[s] && adjacency[t]) { adjacency[s][t] = true; adjacency[t][s] = true; }
            return { source: s, target: t, weight: e.weight || 1, _s: nodeById[s], _t: nodeById[t] };
        });
        buildGrid();
    }

    function boot() {
        container = document.getElementById('graph');
        loadingEl = document.getElementById('graph-loading');
        tooltipEl = document.getElementById('tooltip');
        if (!container) return;

        var url = window.BENGAL_GRAPH_JSON_URL || 'graph.json';
        var controller = ('AbortController' in window) ? new AbortController() : null;

        fetch(url, controller ? { signal: controller.signal } : undefined)
            .then(function (r) {
                if (!r.ok) throw new Error(r.statusText || ('HTTP ' + r.status));
                return r.json();
            })
            .then(function (data) {
                prepareData(data);

                canvas = document.createElement('canvas');
                canvas.className = 'graph-canvas';
                canvas.style.display = 'block';
                canvas.style.cursor = 'grab';
                container.appendChild(canvas);
                ctx = canvas.getContext('2d');

                resolveColors();
                resize();
                fitToView();
                setupControls();
                setupInteraction();
                buildA11yList();

                if (loadingEl) loadingEl.classList.add('hidden');
                requestRedraw();
            })
            .catch(function (err) {
                if (loadingEl) {
                    loadingEl.innerHTML = '<p>Failed to load graph. ' +
                        escapeHtml(err && err.message ? err.message : 'Unknown error') + '</p>';
                }
            });
    }

    function cleanup() {
        listeners.forEach(function (l) { l[0].removeEventListener(l[1], l[2], l[3]); });
        listeners = [];
    }
    window.addEventListener('pagehide', cleanup);
    window.addEventListener('beforeunload', cleanup);

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', boot);
    } else {
        boot();
    }
})();
