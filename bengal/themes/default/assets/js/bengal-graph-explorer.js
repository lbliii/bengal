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
    var LABEL_SCALE = 0.9;     // draw extra labels once zoomed past this
    var GRID_CELL = 80;        // picking grid cell size (world units)
    var MIN_NODE_PX = 3.5;     // minimum on-screen radius (zoomed-out legibility)
    var MIN_HUB_PX = 6;        // minimum for hubs / high-importance nodes
    var HUB_LABEL_COUNT = 18;  // always label the top N hubs, even when zoomed out
    var LOD_ATLAS = 0.35;      // below: topic blobs + labels (atlas view)
    var LOD_NEIGHBORHOOD = 0.85; // below: compact dots; above: full node detail
    var CAMERA_ANIM_MS = 320;  // fly-to duration
    var MINIMAP_SIZE = 120;    // inset atlas minimap (px)
    var DOT_NODE_PX = 3.2;     // uniform radius in neighborhood LOD

    // Note: fit-to-view snaps instantly (no entrance animation), so there is
    // nothing to gate behind prefers-reduced-motion here.

    // ---- State ---------------------------------------------------------------
    var canvas, ctx, container, loadingEl, tooltipEl, searchInput, filterSelect;
    var minimapCanvas, minimapCtx, breadcrumbEl;
    var dpr = window.devicePixelRatio || 1;
    var nodes = [], edges = [], nodeById = {}, adjacency = {};
    var grid = {};             // picking grid: "cx,cy" -> [node, ...]
    var camera = { scale: 1, tx: 0, ty: 0 };
    var cameraAnim = null;     // active fly-to animation frame id
    var colors = {};
    var communityColors = [];   // categorical topic-cluster palette (CSS tokens)
    var communityLabels = {};   // community id -> display label (from stats)
    var communityRegions = [];  // baked bounds + labels for semantic zoom
    var communityById = {};
    var graphStats = null;      // stats block from graph.json (for legend rebuild)
    var labelHubIds = {};       // node ids that always get a label at fit scale
    var colorProbe = null;      // hidden element for resolving CSS vars → rgb()
    var hovered = null;
    var hoveredCluster = null;
    var pinnedNode = null;      // shift+click pins ego-network focus
    var dirty = false;
    var rafPending = false;
    var listeners = [];

    // search / filter
    var query = '';
    var typeFilter = 'all';
    var tagParam = null;
    var communityFilter = null; // when set, isolate one topic cluster (legend click)

    var COMMUNITY_PALETTE_SIZE = 10;

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
    // Canvas fillStyle cannot parse oklch()/light-dark()/color-mix() strings.
    // getPropertyValue on custom props returns those raw values, so resolve each
    // token through a hidden probe element and read the computed rgb() color.
    function ensureColorProbe() {
        if (colorProbe) return colorProbe;
        colorProbe = document.createElement('span');
        colorProbe.setAttribute('aria-hidden', 'true');
        colorProbe.style.cssText =
            'position:absolute;left:-9999px;visibility:hidden;pointer-events:none';
        document.documentElement.appendChild(colorProbe);
        return colorProbe;
    }

    function resolveCssColor(varName, fallback) {
        var probe = ensureColorProbe();
        probe.style.color = fallback;
        probe.style.color = 'var(' + varName + ', ' + fallback + ')';
        var resolved = getComputedStyle(probe).color;
        if (!resolved || resolved === 'rgba(0, 0, 0, 0)' || !/^rgba?\(/i.test(resolved)) {
            return fallback;
        }
        return resolved;
    }

    function resolveColors() {
        colors = {
            hub: resolveCssColor('--graph-node-hub', '#FF9500'),
            regular: resolveCssColor('--graph-node-regular', '#E8E0D8'),
            orphan: resolveCssColor('--graph-node-orphan', '#FF5A5A'),
            generated: resolveCssColor('--graph-node-generated', '#4ECDC4'),
            link: resolveCssColor('--graph-link-color', 'rgba(100,100,100,0.35)'),
            linkHi: resolveCssColor('--graph-link-highlight', 'rgba(255,200,120,0.95)'),
            label: resolveCssColor('--color-text-primary', '#222'),
            labelBg: resolveCssColor('--color-bg-elevated', '#fff'),
            nodeRim: resolveCssColor('--color-bg-primary', '#fff'),
            communityOther: resolveCssColor('--graph-community-other', '#9aa0a6')
        };
        var COMMUNITY_FALLBACKS = [
            '#FF9500', '#4ECDC4', '#A78BFA', '#F472B6', '#34D399',
            '#60A5FA', '#FBBF24', '#FB7185', '#2DD4BF', '#C084FC'
        ];
        communityColors = [];
        for (var i = 0; i < COMMUNITY_PALETTE_SIZE; i++) {
            communityColors.push(
                resolveCssColor('--graph-community-' + i, COMMUNITY_FALLBACKS[i])
            );
        }
    }
    function nodeColor(n) {
        // Colour by topic community (the "map" look); fall back to type colour
        // for unclustered nodes or pre-community data.
        if (typeof n.community === 'number' && n.community >= 0 && communityColors.length) {
            return communityColors[n.community % communityColors.length];
        }
        return colors[n.type] || colors.regular;
    }

    function nodeImportance(n) {
        return (n.incoming_refs || 0) + (n.outgoing_refs || 0) + (n.connectivity || 0);
    }

    function getLodMode() {
        if (communityFilter !== null) return 'detail';
        if (camera.scale < LOD_ATLAS) return 'atlas';
        if (camera.scale < LOD_NEIGHBORHOOD) return 'neighborhood';
        return 'detail';
    }

    function cancelCameraAnim() {
        if (cameraAnim !== null) {
            cancelAnimationFrame(cameraAnim);
            cameraAnim = null;
        }
    }

    function animateCamera(targetScale, targetTx, targetTy, onDone) {
        cancelCameraAnim();
        var startScale = camera.scale;
        var startTx = camera.tx;
        var startTy = camera.ty;
        var t0 = performance.now();
        function frame(now) {
            var u = Math.min(1, (now - t0) / CAMERA_ANIM_MS);
            u = 1 - Math.pow(1 - u, 3);
            camera.scale = startScale + (targetScale - startScale) * u;
            camera.tx = startTx + (targetTx - startTx) * u;
            camera.ty = startTy + (targetTy - startTy) * u;
            requestRedraw();
            if (u < 1) {
                cameraAnim = requestAnimationFrame(frame);
            } else {
                cameraAnim = null;
                if (onDone) onDone();
            }
        }
        cameraAnim = requestAnimationFrame(frame);
    }

    function flyToBounds(minX, minY, maxX, maxY, pad) {
        if (!canvas) return;
        var vw = canvas.width / dpr;
        var vh = canvas.height / dpr;
        pad = pad == null ? 80 : pad;
        var dx = (maxX - minX) || 1;
        var dy = (maxY - minY) || 1;
        var scale = Math.min(MAX_SCALE, Math.min((vw - 2 * pad) / dx, (vh - 2 * pad) / dy));
        scale = Math.max(MIN_SCALE, scale);
        var tx = vw / 2 - scale * (minX + maxX) / 2;
        var ty = vh / 2 - scale * (minY + maxY) / 2;
        animateCamera(scale, tx, ty);
    }

    function regionWorldBounds(r) {
        var pad = 24;
        if (r.min_x == null || r.min_y == null) {
            var wx = worldX(r.x || 0.5);
            var wy = worldY(r.y || 0.5);
            return { minX: wx - 60, minY: wy - 60, maxX: wx + 60, maxY: wy + 60 };
        }
        return {
            minX: worldX(r.min_x) - pad,
            minY: worldY(r.min_y) - pad,
            maxX: worldX(r.max_x) + pad,
            maxY: worldY(r.max_y) + pad
        };
    }

    function flyToCommunity(id) {
        var region = communityById[id];
        if (!region) return;
        communityFilter = id;
        document.querySelectorAll('.graph-legend-community').forEach(function (b) {
            var cid = parseInt(b.getAttribute('data-community'), 10);
            var active = cid === id;
            b.setAttribute('aria-pressed', active ? 'true' : 'false');
            b.classList.toggle('is-active', active);
        });
        updateBreadcrumb();
        var b = regionWorldBounds(region);
        flyToBounds(b.minX, b.minY, b.maxX, b.maxY, 60);
    }

    function flyToNode(n) {
        if (!n) return;
        pinnedNode = n;
        communityFilter = null;
        document.querySelectorAll('.graph-legend-community').forEach(function (b) {
            b.setAttribute('aria-pressed', 'false');
            b.classList.remove('is-active');
        });
        updateBreadcrumb();
        var pad = 120;
        flyToBounds(n.wx - pad, n.wy - pad, n.wx + pad, n.wy + pad, 40);
    }

    function buildCommunityRegions(stats) {
        communityRegions = [];
        communityById = {};
        var regions = (stats && stats.community_regions) || [];
        if (regions.length) {
            communityRegions = regions.slice();
        } else if (stats && stats.communities) {
            communityRegions = stats.communities.slice();
        }
        if (!communityRegions.length) {
            var buckets = {};
            nodes.forEach(function (n) {
                if (typeof n.community !== 'number' || n.community < 0) return;
                (buckets[n.community] || (buckets[n.community] = [])).push(n);
            });
            Object.keys(buckets).sort(function (a, b) {
                return parseInt(a, 10) - parseInt(b, 10);
            }).forEach(function (key) {
                var list = buckets[key];
                var xs = list.map(function (n) { return n.x; });
                var ys = list.map(function (n) { return n.y; });
                communityRegions.push({
                    id: parseInt(key, 10),
                    label: communityLabels[key] || ('Cluster ' + key),
                    size: list.length,
                    x: xs.reduce(function (a, b) { return a + b; }, 0) / xs.length,
                    y: ys.reduce(function (a, b) { return a + b; }, 0) / ys.length,
                    min_x: Math.min.apply(null, xs),
                    min_y: Math.min.apply(null, ys),
                    max_x: Math.max.apply(null, xs),
                    max_y: Math.max.apply(null, ys)
                });
            });
        }
        communityRegions.forEach(function (r) {
            communityById[r.id] = r;
            if (!communityLabels[r.id] && r.label) communityLabels[r.id] = r.label;
        });
    }

    function updateBreadcrumb() {
        if (!breadcrumbEl) return;
        var parts = ['<button type="button" class="graph-crumb graph-crumb-root">All topics</button>'];
        if (communityFilter !== null && communityLabels[communityFilter]) {
            parts.push('<span class="graph-crumb-sep">›</span>');
            parts.push('<span class="graph-crumb-current">' + escapeHtml(communityLabels[communityFilter]) + '</span>');
        } else if (pinnedNode) {
            parts.push('<span class="graph-crumb-sep">›</span>');
            parts.push('<span class="graph-crumb-current">' + escapeHtml(pinnedNode.label || pinnedNode.id) + '</span>');
        }
        breadcrumbEl.innerHTML = parts.join('');
    }

    function ensureBreadcrumb() {
        if (breadcrumbEl) return breadcrumbEl;
        breadcrumbEl = document.createElement('div');
        breadcrumbEl.className = 'graph-breadcrumb';
        breadcrumbEl.setAttribute('aria-label', 'Graph navigation');
        on(breadcrumbEl, 'click', function (e) {
            if (e.target.classList.contains('graph-crumb-root')) {
                communityFilter = null;
                pinnedNode = null;
                document.querySelectorAll('.graph-legend-community').forEach(function (b) {
                    b.setAttribute('aria-pressed', 'false');
                    b.classList.remove('is-active');
                });
                fitToView(true);
                updateBreadcrumb();
                requestRedraw();
            }
        });
        (document.getElementById('container') || document.body).appendChild(breadcrumbEl);
        return breadcrumbEl;
    }

    function ensureMinimap() {
        if (minimapCanvas) return;
        minimapCanvas = document.createElement('canvas');
        minimapCanvas.className = 'graph-minimap';
        minimapCanvas.width = MINIMAP_SIZE;
        minimapCanvas.height = MINIMAP_SIZE;
        minimapCanvas.setAttribute('aria-hidden', 'true');
        minimapCtx = minimapCanvas.getContext('2d');
        (document.getElementById('container') || document.body).appendChild(minimapCanvas);
    }

    function pickCluster(sx, sy) {
        if (!communityRegions.length) return null;
        var wx = toWorldX(sx);
        var wy = toWorldY(sy);
        var best = null;
        var bestArea = Infinity;
        for (var i = 0; i < communityRegions.length; i++) {
            var r = communityRegions[i];
            if (communityFilter !== null && r.id !== communityFilter) continue;
            var b = regionWorldBounds(r);
            if (wx >= b.minX && wx <= b.maxX && wy >= b.minY && wy <= b.maxY) {
                var area = (b.maxX - b.minX) * (b.maxY - b.minY);
                if (area < bestArea) {
                    bestArea = area;
                    best = r;
                }
            }
        }
        return best;
    }

    function nodeDrawRadius(n, mode) {
        if (mode === 'atlas') return 0;
        if (mode === 'neighborhood') return DOT_NODE_PX;
        return nodeScreenRadius(n);
    }

    function shouldDrawEdge(e, mode) {
        if (!e._s || !e._t) return false;
        if (mode === 'atlas') return false;
        if (communityFilter !== null) {
            return e._s.community === communityFilter || e._t.community === communityFilter;
        }
        if (mode === 'neighborhood') {
            return e._s.community === e._t.community;
        }
        return true;
    }

    function drawClusterHulls(vw, vh, pad, mode) {
        if (!communityRegions.length || mode === 'detail') return;
        for (var i = 0; i < communityRegions.length; i++) {
            var r = communityRegions[i];
            if (communityFilter !== null && r.id !== communityFilter) continue;
            var b = regionWorldBounds(r);
            var sx0 = toScreenX(b.minX);
            var sy0 = toScreenY(b.minY);
            var sx1 = toScreenX(b.maxX);
            var sy1 = toScreenY(b.maxY);
            if (sx1 < -pad || sx0 > vw + pad || sy1 < -pad || sy0 > vh + pad) continue;

            var col = communityColorFor(r.id);
            var w = sx1 - sx0;
            var h = sy1 - sy0;
            var rad = Math.min(18, w * 0.12, h * 0.12);
            ctx.fillStyle = col;
            ctx.globalAlpha = hoveredCluster && hoveredCluster.id === r.id ? 0.22 : 0.12;
            ctx.beginPath();
            if (ctx.roundRect) {
                ctx.roundRect(sx0, sy0, w, h, rad);
            } else {
                ctx.rect(sx0, sy0, w, h);
            }
            ctx.fill();
            ctx.strokeStyle = col;
            ctx.lineWidth = hoveredCluster && hoveredCluster.id === r.id ? 2 : 1;
            ctx.globalAlpha = hoveredCluster && hoveredCluster.id === r.id ? 0.55 : 0.28;
            ctx.stroke();

            if (mode === 'atlas') {
                var lx = toScreenX(worldX(r.x || 0.5));
                var ly = toScreenY(worldY(r.y || 0.5));
                var label = r.label || ('Cluster ' + r.id);
                ctx.font = '600 12px system-ui, sans-serif';
                ctx.textAlign = 'center';
                ctx.textBaseline = 'middle';
                ctx.fillStyle = colors.label;
                ctx.globalAlpha = 0.95;
                ctx.fillText(label, lx, ly - 8);
                ctx.font = '500 10px system-ui, sans-serif';
                ctx.fillStyle = colors.label;
                ctx.globalAlpha = 0.65;
                ctx.fillText(String(r.size || 0) + ' pages', lx, ly + 10);
            }
        }
        ctx.globalAlpha = 1;
    }

    function drawMinimap() {
        if (!minimapCanvas || !minimapCtx || !nodes.length) return;
        var m = MINIMAP_SIZE;
        minimapCtx.clearRect(0, 0, m, m);
        var minX = Infinity, maxX = -Infinity, minY = Infinity, maxY = -Infinity;
        nodes.forEach(function (n) {
            minX = Math.min(minX, n.wx); maxX = Math.max(maxX, n.wx);
            minY = Math.min(minY, n.wy); maxY = Math.max(maxY, n.wy);
        });
        var spanX = (maxX - minX) || 1;
        var spanY = (maxY - minY) || 1;
        var inset = 8;
        var scale = Math.min((m - 2 * inset) / spanX, (m - 2 * inset) / spanY);

        function mx(wx) { return inset + (wx - minX) * scale; }
        function my(wy) { return inset + (wy - minY) * scale; }

        minimapCtx.fillStyle = 'rgba(128,128,128,0.08)';
        minimapCtx.fillRect(0, 0, m, m);

        if (communityRegions.length) {
            communityRegions.forEach(function (r) {
                if (r.min_x == null) return;
                var b = regionWorldBounds(r);
                minimapCtx.fillStyle = communityColorFor(r.id);
                minimapCtx.globalAlpha = 0.35;
                minimapCtx.fillRect(mx(b.minX), my(b.minY), mx(b.maxX) - mx(b.minX), my(b.maxY) - my(b.minY));
            });
            minimapCtx.globalAlpha = 1;
        } else {
            nodes.forEach(function (n) {
                minimapCtx.fillStyle = nodeColor(n);
                minimapCtx.globalAlpha = 0.7;
                minimapCtx.beginPath();
                minimapCtx.arc(mx(n.wx), my(n.wy), 1.2, 0, Math.PI * 2);
                minimapCtx.fill();
            });
            minimapCtx.globalAlpha = 1;
        }

        var vw = canvas.width / dpr;
        var vh = canvas.height / dpr;
        var vwx0 = toWorldX(0);
        var vwy0 = toWorldY(0);
        var vwx1 = toWorldX(vw);
        var vwy1 = toWorldY(vh);
        minimapCtx.strokeStyle = 'rgba(255,255,255,0.85)';
        minimapCtx.lineWidth = 1.5;
        minimapCtx.strokeRect(mx(vwx0), my(vwy0), mx(vwx1) - mx(vwx0), my(vwy1) - my(vwy0));
    }

    function nodeScreenRadius(n) {
        var scaled = n.size * Math.min(1, camera.scale * 1.2);
        var floor = (n.type === 'hub' || n.size >= 22) ? MIN_HUB_PX : MIN_NODE_PX;
        if (camera.scale < LABEL_SCALE) {
            if (n.type === 'hub') floor = Math.max(floor, MIN_HUB_PX + 2);
            else if (n.size >= 22) floor = Math.max(floor, MIN_NODE_PX + 2);
            else if (n.size >= 14) floor = Math.max(floor, MIN_NODE_PX + 0.5);
        }
        return Math.max(floor, scaled);
    }

    function buildLabelHubs() {
        labelHubIds = {};
        var sorted = nodes.slice().sort(function (a, b) {
            return nodeImportance(b) - nodeImportance(a);
        });
        for (var i = 0; i < Math.min(HUB_LABEL_COUNT, sorted.length); i++) {
            labelHubIds[sorted[i].id] = true;
        }
    }

    function drawNodeLabel(text, lx, ly, r) {
        if (!text) return;
        ctx.font = '600 11px system-ui, sans-serif';
        ctx.textAlign = 'center';
        ctx.textBaseline = 'top';
        var metrics = ctx.measureText(text);
        var padX = 5;
        var padY = 3;
        var w = metrics.width + padX * 2;
        var h = 13 + padY * 2;
        var x = lx - w / 2;
        var y = ly + r + 3;
        ctx.fillStyle = colors.labelBg;
        ctx.globalAlpha = 0.92;
        ctx.beginPath();
        if (ctx.roundRect) {
            ctx.roundRect(x, y, w, h, 4);
        } else {
            ctx.rect(x, y, w, h);
        }
        ctx.fill();
        ctx.globalAlpha = 1;
        ctx.fillStyle = colors.label;
        ctx.fillText(text, lx, y + padY);
    }

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
        var mode = getLodMode();
        if (mode === 'atlas') return null;
        var wx = toWorldX(sx), wy = toWorldY(sy);
        var cx = Math.floor(wx / GRID_CELL), cy = Math.floor(wy / GRID_CELL);
        var best = null, bestD = Infinity;
        for (var gx = cx - 1; gx <= cx + 1; gx++) {
            for (var gy = cy - 1; gy <= cy + 1; gy++) {
                var bucket = grid[gx + ',' + gy];
                if (!bucket) continue;
                for (var i = 0; i < bucket.length; i++) {
                    var n = bucket[i];
                    if (!isVisible(n)) continue;
                    var dx = n.wx - wx, dy = n.wy - wy;
                    var d2 = dx * dx + dy * dy;
                    var r = nodeDrawRadius(n, mode) + 4;
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
        if (communityFilter !== null && n.community !== communityFilter) return false;
        var matchesSearch = !query ||
            (n.label || '').toLowerCase().indexOf(query) !== -1 ||
            (n.tags || []).some(function (t) { return t.toLowerCase().indexOf(query) !== -1; });
        var matchesType = typeFilter === 'all' || n.type === typeFilter;
        return matchesSearch && matchesType;
    }

    // ---- Community (topic-cluster) legend -----------------------------------
    function communityColorFor(id) {
        if (!communityColors.length) return colors.communityOther;
        return communityColors[id % communityColors.length];
    }
    function buildCommunityLegend(stats) {
        var legend = document.querySelector('.graph-legend');
        if (!legend || !stats || !stats.communities || !stats.communities.length) return;
        communityLabels = {};
        stats.communities.forEach(function (c) { communityLabels[c.id] = c.label; });
        var top = stats.communities.slice(0, 8);
        var frag = document.createElement('div');
        var html = '<h3>Topic clusters</h3>';
        top.forEach(function (c) {
            html += '<button type="button" class="graph-legend-item graph-legend-community" ' +
                'data-community="' + c.id + '" aria-pressed="false">' +
                '<span class="graph-legend-color" style="background:' + communityColorFor(c.id) + '"></span>' +
                '<span class="graph-legend-label">' + escapeHtml(c.label || ('Cluster ' + c.id)) + '</span>' +
                '<span class="graph-legend-count">' + (c.size || 0) + '</span>' +
                '</button>';
        });
        frag.innerHTML = html;
        legend.innerHTML = frag.innerHTML;
        // Click a cluster to isolate it; click again (or another) to toggle.
        legend.querySelectorAll('.graph-legend-community').forEach(function (btn) {
            on(btn, 'click', function () {
                var id = parseInt(btn.getAttribute('data-community'), 10);
                if (communityFilter === id) {
                    communityFilter = null;
                    pinnedNode = null;
                    btn.setAttribute('aria-pressed', 'false');
                    btn.classList.remove('is-active');
                    fitToView(true);
                    updateBreadcrumb();
                } else {
                    flyToCommunity(id);
                }
                requestRedraw();
            });
        });
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
        var mode = getLodMode();
        var focusNode = pinnedNode || hovered;

        var hoverSet = null;
        if (focusNode) {
            hoverSet = adjacency[focusNode.id] || {};
        }

        drawClusterHulls(vw, vh, pad, mode);

        // Edges (LOD: hidden at atlas, intra-community at neighborhood)
        for (var i = 0; i < edges.length; i++) {
            var e = edges[i];
            var s = e._s, t = e._t;
            if (!s || !t) continue;
            if (!shouldDrawEdge(e, mode)) continue;
            var sVis = isVisible(s), tVis = isVisible(t);
            if (!sVis || !tVis) continue;
            var sx = toScreenX(s.wx), sy = toScreenY(s.wy);
            var tx = toScreenX(t.wx), ty = toScreenY(t.wy);
            if ((sx < -pad && tx < -pad) || (sx > vw + pad && tx > vw + pad) ||
                (sy < -pad && ty < -pad) || (sy > vh + pad && ty > vh + pad)) continue;

            var isHi = focusNode && (e.source === focusNode.id || e.target === focusNode.id);
            ctx.strokeStyle = isHi ? colors.linkHi : colors.link;
            ctx.lineWidth = isHi ? 1.5 : (e.weight === 2 ? 1.1 : 0.9);
            var baseAlpha = mode === 'neighborhood' ? 0.35 : (e.weight === 2 ? 0.85 : 0.7);
            ctx.globalAlpha = focusNode ? (isHi ? 1 : 0.12) : baseAlpha;
            ctx.beginPath();
            ctx.moveTo(sx, sy);
            ctx.lineTo(tx, ty);
            ctx.stroke();
        }
        ctx.globalAlpha = 1;

        // Nodes — hidden at atlas LOD (cluster hulls carry the view).
        if (mode !== 'atlas') {
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
                    var dim = (!visible) || (focusNode && focusNode.id !== nd.id &&
                        !(hoverSet && hoverSet[nd.id]));
                    ctx.globalAlpha = visible ? (dim ? (tagParam ? 0 : 0.15) : 1) : (tagParam ? 0 : 0.15);
                    var r = nodeDrawRadius(nd, mode);
                    var sxNd = toScreenX(nd.wx);
                    var syNd = toScreenY(nd.wy);
                    ctx.beginPath();
                    ctx.arc(sxNd, syNd, r, 0, Math.PI * 2);
                    ctx.fill();
                    if (!dim && r >= 2.5 && mode === 'detail') {
                        ctx.strokeStyle = colors.nodeRim;
                        ctx.lineWidth = 1;
                        ctx.globalAlpha = visible ? 0.35 : ctx.globalAlpha;
                        ctx.stroke();
                    }
                }
            }
            ctx.globalAlpha = 1;
        }

        // Labels — detail LOD only (plus pinned/hover focus).
        var showLabels = mode === 'detail' && camera.scale >= LABEL_SCALE;
        if (mode === 'detail' && (showLabels || focusNode || Object.keys(labelHubIds).length)) {
            for (var l = 0; l < nodes.length; l++) {
                var ln = nodes[l];
                if (!isVisible(ln)) continue;
                var labelThis = (focusNode && (ln.id === focusNode.id || (hoverSet && hoverSet[ln.id]))) ||
                                labelHubIds[ln.id] ||
                                (showLabels && (ln.type === 'hub' || camera.scale >= 1.6));
                if (!labelThis) continue;
                var lx = toScreenX(ln.wx);
                var ly = toScreenY(ln.wy);
                if (lx < -pad || lx > vw + pad || ly < -pad || ly > vh + pad) continue;
                drawNodeLabel(ln.label || '', lx, ly, nodeDrawRadius(ln, mode));
            }
        }

        drawMinimap();
    }

    // ---- Camera --------------------------------------------------------------
    function fitToView(animate) {
        if (!nodes.length) return;
        var minX = Infinity, maxX = -Infinity, minY = Infinity, maxY = -Infinity;
        nodes.forEach(function (n) {
            minX = Math.min(minX, n.wx); maxX = Math.max(maxX, n.wx);
            minY = Math.min(minY, n.wy); maxY = Math.max(maxY, n.wy);
        });
        if (animate) {
            var vw = canvas.width / dpr;
            var vh = canvas.height / dpr;
            var pad = 80;
            var dx = (maxX - minX) || 1;
            var dy = (maxY - minY) || 1;
            var scale = Math.min(MAX_SCALE, Math.min((vw - 2 * pad) / dx, (vh - 2 * pad) / dy));
            scale = Math.max(MIN_SCALE, scale);
            if (communityRegions.length > 1 && nodes.length > 80) {
                scale = Math.min(scale, LOD_ATLAS * 0.92);
            }
            var tx = vw / 2 - scale * (minX + maxX) / 2;
            var ty = vh / 2 - scale * (minY + maxY) / 2;
            animateCamera(scale, tx, ty);
            return;
        }
        var vw = canvas.width / dpr, vh = canvas.height / dpr;
        var pad = 80;
        var dx = (maxX - minX) || 1, dy = (maxY - minY) || 1;
        var scale = Math.min(MAX_SCALE, Math.min((vw - 2 * pad) / dx, (vh - 2 * pad) / dy));
        scale = Math.max(MIN_SCALE, scale);
        if (communityRegions.length > 1 && nodes.length > 80) {
            scale = Math.min(scale, LOD_ATLAS * 0.92);
        }
        camera.scale = scale;
        camera.tx = vw / 2 - scale * (minX + maxX) / 2;
        camera.ty = vh / 2 - scale * (minY + maxY) / 2;
    }

    function zoomAt(sx, sy, factor) {
        cancelCameraAnim();
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
        var clusterLine = '';
        if (typeof n.community === 'number' && n.community >= 0 && communityLabels[n.community]) {
            clusterLine = '<p class="graph-tooltip-cluster">' +
                '<span class="graph-tooltip-swatch" style="background:' + communityColorFor(n.community) + '"></span>' +
                escapeHtml(communityLabels[n.community]) + '</p>';
        }
        tooltipEl.innerHTML = '<h4>' + escapeHtml(n.label || 'Untitled') + '</h4>' +
            '<p>' + (n.reading_time || 0) + ' min read · ' +
            (n.incoming_refs || 0) + ' in / ' + (n.outgoing_refs || 0) + ' out</p>' + clusterLine + tags;
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
            cancelCameraAnim();
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
            var sx = e.clientX - rect.left;
            var sy = e.clientY - rect.top;
            var mode = getLodMode();
            var cluster = mode === 'atlas' ? pickCluster(sx, sy) : null;
            var n = cluster ? null : pick(sx, sy);
            if (cluster !== hoveredCluster) {
                hoveredCluster = cluster;
                requestRedraw();
            }
            if (n !== hovered) {
                hovered = n;
                canvas.style.cursor = (n || cluster) ? 'pointer' : 'grab';
                if (!pinnedNode) requestRedraw();
            }
            if (n) showTooltip(e, n);
            else if (cluster) {
                if (tooltipEl) {
                    tooltipEl.style.display = 'block';
                    tooltipEl.style.left = (e.clientX + 12) + 'px';
                    tooltipEl.style.top = (e.clientY + 12) + 'px';
                    tooltipEl.innerHTML = '<h4>' + escapeHtml(cluster.label || ('Cluster ' + cluster.id)) + '</h4>' +
                        '<p>' + (cluster.size || 0) + ' pages — click to explore</p>';
                }
            } else hideTooltip();
        });
        on(canvas, 'mouseleave', function () {
            hovered = null;
            hoveredCluster = null;
            hideTooltip();
            requestRedraw();
        });
        on(canvas, 'click', function (e) {
            if (moved) return;
            var rect = canvas.getBoundingClientRect();
            var sx = e.clientX - rect.left;
            var sy = e.clientY - rect.top;
            var mode = getLodMode();
            if (mode === 'atlas') {
                var cluster = pickCluster(sx, sy);
                if (cluster) {
                    flyToCommunity(cluster.id);
                    return;
                }
            }
            var n = pick(sx, sy);
            if (e.shiftKey && n) {
                pinnedNode = n;
                communityFilter = null;
                updateBreadcrumb();
                requestRedraw();
                return;
            }
            if (n && n.url) window.location.href = normalizeUrl(n.url);
        });
        on(canvas, 'wheel', function (e) {
            e.preventDefault();
            var rect = canvas.getBoundingClientRect();
            var factor = e.deltaY < 0 ? 1.12 : 1 / 1.12;
            zoomAt(e.clientX - rect.left, e.clientY - rect.top, factor);
        }, { passive: false });

        on(window, 'resize', resize);
        on(window, 'themechange', function () {
            resolveColors();
            if (graphStats) buildCommunityLegend(graphStats);
            requestRedraw();
        });
        on(window, 'palettechange', function () {
            resolveColors();
            if (graphStats) buildCommunityLegend(graphStats);
            requestRedraw();
        });

        on(document, 'keydown', function (e) {
            if (e.key === '/' || (e.metaKey && e.key === 'k') || (e.ctrlKey && e.key === 'k')) {
                if (searchInput) { e.preventDefault(); searchInput.focus(); }
            } else if (e.key === 'Escape') {
                if (searchInput) searchInput.value = '';
                if (filterSelect) filterSelect.value = 'all';
                query = ''; typeFilter = 'all'; communityFilter = null;
                pinnedNode = null;
                document.querySelectorAll('.graph-legend-community').forEach(function (b) {
                    b.setAttribute('aria-pressed', 'false');
                    b.classList.remove('is-active');
                });
                fitToView(true);
                updateBreadcrumb();
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
                if (query.length >= 2) {
                    var matches = nodes.filter(function (n) {
                        return isVisible(n) && (
                            (n.label || '').toLowerCase().indexOf(query) !== -1 ||
                            (n.tags || []).some(function (t) { return t.toLowerCase().indexOf(query) !== -1; })
                        );
                    });
                    if (matches.length === 1) {
                        flyToNode(matches[0]);
                    } else if (matches.length > 1) {
                        matches.sort(function (a, b) {
                            return nodeImportance(b) - nodeImportance(a);
                        });
                        flyToNode(matches[0]);
                    }
                }
                requestRedraw();
            }, 200));
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
        buildLabelHubs();
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
                ensureBreadcrumb();
                ensureMinimap();
                buildCommunityRegions(data.stats);
                fitToView(false);
                setupControls();
                setupInteraction();
                buildA11yList();
                graphStats = data.stats;
                buildCommunityLegend(data.stats);
                updateBreadcrumb();

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
