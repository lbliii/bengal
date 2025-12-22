/**
 * Bengal SSG - Graph Minimap Component (v2)
 *
 * Renders a small, interactive graph visualization similar to Obsidian's minimap.
 * Designed to be embedded in the search page or other pages.
 *
 * Performance optimizations (v2):
 * - Removed MutationObserver (use event listeners only)
 * - Faster force simulation with synchronous layout
 * - Debounced theme change handling
 * - Single getComputedStyle call per theme change
 */

(function() {
    'use strict';

    // Debounce utility
    function debounce(fn, delay) {
        let timer = null;
        return function(...args) {
            if (timer) clearTimeout(timer);
            timer = setTimeout(() => {
                timer = null;
                fn.apply(this, args);
            }, delay);
        };
    }

    /**
     * Graph Minimap Component
     */
    class GraphMinimap {
        constructor(container, options = {}) {
            this.container = typeof container === 'string'
                ? document.querySelector(container)
                : container;

            if (!this.container) return;

            // Get baseurl from meta tag if present
            let baseurl = '';
            try {
                const m = document.querySelector('meta[name="bengal:baseurl"]');
                baseurl = (m && m.getAttribute('content')) || '';
                if (baseurl) baseurl = baseurl.replace(/\/$/, '');
            } catch (e) {}

            this.options = {
                width: options.width || 242,
                height: options.height || 250,
                dataUrl: options.dataUrl || (baseurl + '/graph/graph.json'),
                expandUrl: options.expandUrl || (baseurl + '/graph/'),
                // v2: Use synchronous layout by default
                syncLayout: options.syncLayout !== false,
                ...options
            };

            this.data = null;
            this.simulation = null;
            this.svg = null;
            this.g = null;
            this.nodes = null;
            this.links = null;
            this.zoom = null;

            // v2: Store bound handlers for cleanup
            this._boundHandlers = {};

            this.init();
        }

        async init() {
            try {
                const response = await fetch(this.options.dataUrl);
                if (!response.ok) {
                    throw new Error(`Failed to load graph data: ${response.status}`);
                }
                this.data = await response.json();

                this.createSVG();
                this.render();
                this.addExpandButton();
            } catch (error) {
                this.container.innerHTML = '<div class="graph-minimap-error">Graph unavailable</div>';
            }
        }

        createSVG() {
            this.container.innerHTML = '';

            const wrapper = document.createElement('div');
            wrapper.className = 'graph-minimap-container graph-visible';
            this.container.appendChild(wrapper);

            this.svg = d3.select(wrapper)
                .append('svg')
                .attr('width', this.options.width)
                .attr('height', this.options.height)
                .attr('class', 'graph-svg-visible');

            this.g = this.svg.append('g');

            this.zoom = d3.zoom()
                .scaleExtent([0.5, 2])
                .on('zoom', (event) => {
                    this.g.attr('transform', event.transform);
                });

            this.svg.call(this.zoom);

            const initialScale = Math.min(
                this.options.width / 800,
                this.options.height / 600
            ) * 0.8;
            const initialX = (this.options.width - 800 * initialScale) / 2;
            const initialY = (this.options.height - 600 * initialScale) / 2;

            this.svg.call(
                this.zoom.transform,
                d3.zoomIdentity.translate(initialX, initialY).scale(initialScale)
            );
        }

        render() {
            if (!this.data || !this.g) return;

            // v2: Resolve colors once before rendering
            this._resolveNodeColorsOnce();

            // v2: Compute layout synchronously
            if (this.options.syncLayout) {
                this._computeSyncLayout();
            } else {
                this._createAsyncSimulation();
            }

            // Render links
            this.links = this.g.append('g')
                .attr('class', 'graph-minimap-links')
                .selectAll('line')
                .data(this.data.edges)
                .enter()
                .append('line')
                .attr('class', 'graph-minimap-link')
                .attr('stroke', 'var(--color-border-light, rgba(0, 0, 0, 0.1))')
                .attr('stroke-width', 0.5)
                .attr('x1', d => d.source.x)
                .attr('y1', d => d.source.y)
                .attr('x2', d => d.target.x)
                .attr('y2', d => d.target.y);

            // Render nodes
            this.nodes = this.g.append('g')
                .attr('class', 'graph-minimap-nodes')
                .selectAll('circle')
                .data(this.data.nodes)
                .enter()
                .append('circle')
                .attr('class', 'graph-minimap-node')
                .attr('r', d => Math.max((d.size || 5) * 0.3, 2))
                .attr('cx', d => d.x)
                .attr('cy', d => d.y)
                .attr('fill', d => d._resolvedColor || d.color || '#9e9e9e')
                .attr('stroke', 'var(--color-border, rgba(0, 0, 0, 0.2))')
                .attr('stroke-width', 0.5)
                .style('cursor', 'pointer')
                .on('click', (event, d) => {
                    if (d.url) window.location.href = d.url;
                })
                .on('mouseover', (event, d) => {
                    this.showTooltip(event, d);
                    this.highlightConnections(d);
                })
                .on('mouseout', () => {
                    this.hideTooltip();
                    this.clearHighlights();
                });

            // v2: Setup lightweight theme listener
            this._setupThemeListener();
        }

        /**
         * v2: Compute layout synchronously - no animation
         */
        _computeSyncLayout() {
            const simulation = d3.forceSimulation(this.data.nodes)
                .alphaDecay(0.3)
                .alphaMin(0.1)
                .velocityDecay(0.6)
                .force('link', d3.forceLink(this.data.edges).id(d => d.id).distance(30))
                .force('charge', d3.forceManyBody().strength(-100))
                .force('center', d3.forceCenter(this.options.width / 2, this.options.height / 2))
                .force('collision', d3.forceCollide().radius(d => Math.max(d.size || 5, 3)));

            // Run to completion synchronously
            simulation.stop();
            for (let i = 0; i < 100; i++) {
                simulation.tick();
            }

            // No need to store simulation - it's done
            this.simulation = null;
        }

        /**
         * v2: Async simulation (legacy, for compatibility)
         */
        _createAsyncSimulation() {
            this.simulation = d3.forceSimulation(this.data.nodes)
                .alphaDecay(0.15)
                .alphaMin(0.05)
                .velocityDecay(0.5)
                .force('link', d3.forceLink(this.data.edges).id(d => d.id).distance(30))
                .force('charge', d3.forceManyBody().strength(-100))
                .force('center', d3.forceCenter(this.options.width / 2, this.options.height / 2))
                .force('collision', d3.forceCollide().radius(d => Math.max(d.size || 5, 3)));

            this.simulation.on('tick', () => {
                this.links
                    .attr('x1', d => d.source.x)
                    .attr('y1', d => d.source.y)
                    .attr('x2', d => d.target.x)
                    .attr('y2', d => d.target.y);

                this.nodes
                    .attr('cx', d => d.x)
                    .attr('cy', d => d.y);
            });

            // Stop after short time
            this._simulationTimeout = setTimeout(() => {
                if (this.simulation) this.simulation.stop();
                this._simulationTimeout = null;
            }, 300);
        }

        /**
         * v2: Resolve CSS variables once
         */
        _resolveNodeColorsOnce() {
            if (!this.data || !this.data.nodes) return;

            const styles = getComputedStyle(document.documentElement);

            this.data.nodes.forEach(node => {
                if (node.color && node.color.startsWith('var(')) {
                    const varMatch = node.color.match(/var\(([^)]+)\)/);
                    if (varMatch) {
                        const varName = varMatch[1].trim();
                        const resolved = styles.getPropertyValue(varName).trim();
                        node._resolvedColor = resolved || '#9e9e9e';
                    }
                } else {
                    node._resolvedColor = node.color || '#9e9e9e';
                }
            });
        }

        /**
         * v2: Lightweight theme listener - events only, no MutationObserver
         */
        _setupThemeListener() {
            const debouncedUpdate = debounce(() => {
                this._resolveNodeColorsOnce();
                if (this.nodes) {
                    this.nodes.attr('fill', d => d._resolvedColor || '#9e9e9e');
                }
            }, 100);

            this._boundHandlers.themechange = debouncedUpdate;
            this._boundHandlers.palettechange = debouncedUpdate;

            window.addEventListener('themechange', this._boundHandlers.themechange);
            window.addEventListener('palettechange', this._boundHandlers.palettechange);

            // v2: NO MutationObserver - this was causing DevTools crashes
        }

        highlightConnections(d) {
            const connectedNodeIds = new Set([d.id]);

            this.data.edges.forEach(e => {
                if (e.source.id === d.id || e.source === d.id) {
                    connectedNodeIds.add(typeof e.target === 'object' ? e.target.id : e.target);
                }
                if (e.target.id === d.id || e.target === d.id) {
                    connectedNodeIds.add(typeof e.source === 'object' ? e.source.id : e.source);
                }
            });

            this.nodes.classed('graph-minimap-node-highlighted', n => connectedNodeIds.has(n.id));
            this.links.classed('graph-minimap-link-highlighted', e => {
                const sourceId = typeof e.source === 'object' ? e.source.id : e.source;
                const targetId = typeof e.target === 'object' ? e.target.id : e.target;
                return sourceId === d.id || targetId === d.id;
            });
        }

        clearHighlights() {
            this.nodes.classed('graph-minimap-node-highlighted', false);
            this.links.classed('graph-minimap-link-highlighted', false);
        }

        showTooltip(event, d) {
            const existing = document.querySelector('.graph-minimap-tooltip');
            if (existing) existing.remove();

            const tooltip = document.createElement('div');
            tooltip.className = 'graph-minimap-tooltip';
            tooltip.innerHTML = `
                <div class="graph-minimap-tooltip-title">${d.label || 'Untitled'}</div>
                <div class="graph-minimap-tooltip-meta">
                    ${d.incoming_refs || 0} incoming • ${d.outgoing_refs || 0} outgoing
                </div>
            `;
            document.body.appendChild(tooltip);

            const rect = tooltip.getBoundingClientRect();
            let x = event.pageX + 10;
            let y = event.pageY + 10;

            if (x + rect.width > window.innerWidth) {
                x = event.pageX - rect.width - 10;
            }
            if (y + rect.height > window.innerHeight) {
                y = event.pageY - rect.height - 10;
            }

            tooltip.style.left = `${x}px`;
            tooltip.style.top = `${y}px`;
        }

        hideTooltip() {
            const tooltip = document.querySelector('.graph-minimap-tooltip');
            if (tooltip) tooltip.remove();
        }

        addExpandButton() {
            const wrapper = this.container.querySelector('.graph-minimap-container');
            if (!wrapper) return;

            const expandBtn = document.createElement('div');
            expandBtn.className = 'graph-minimap-expand';
            expandBtn.setAttribute('role', 'button');
            expandBtn.setAttribute('aria-label', 'Expand graph');
            expandBtn.setAttribute('data-tooltip-position', 'top');
            expandBtn.innerHTML = `
                <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="svg-icon lucide-arrow-up-right">
                    <path d="M7 7h10v10"></path>
                    <path d="M7 17 17 7"></path>
                </svg>
            `;
            expandBtn.addEventListener('click', () => {
                window.location.href = this.options.expandUrl;
            });
            wrapper.appendChild(expandBtn);
        }

        cleanup() {
            if (this._simulationTimeout) {
                clearTimeout(this._simulationTimeout);
                this._simulationTimeout = null;
            }

            if (this._boundHandlers.themechange) {
                window.removeEventListener('themechange', this._boundHandlers.themechange);
            }
            if (this._boundHandlers.palettechange) {
                window.removeEventListener('palettechange', this._boundHandlers.palettechange);
            }
            this._boundHandlers = {};

            if (this.simulation) {
                this.simulation.stop();
                this.simulation = null;
            }
        }
    }

    // Module-level state
    let minimapInstance = null;
    let intersectionObserver = null;

    function initMinimap() {
        const minimapContainer = document.querySelector('.graph-minimap');
        if (!minimapContainer) return;

        if ('IntersectionObserver' in window) {
            intersectionObserver = new IntersectionObserver((entries) => {
                entries.forEach(entry => {
                    if (entry.isIntersecting) {
                        intersectionObserver.disconnect();
                        intersectionObserver = null;
                        initMinimapWhenD3Ready(minimapContainer);
                    }
                });
            }, { rootMargin: '100px' });

            intersectionObserver.observe(minimapContainer);
        } else {
            initMinimapWhenD3Ready(minimapContainer);
        }
    }

    function initMinimapWhenD3Ready(minimapContainer) {
        if (typeof d3 !== 'undefined') {
            minimapInstance = new GraphMinimap(minimapContainer);
        } else {
            window.addEventListener('d3:ready', () => {
                if (!minimapInstance && typeof d3 !== 'undefined') {
                    minimapInstance = new GraphMinimap(minimapContainer);
                }
            }, { once: true });
        }
    }

    function cleanup() {
        if (intersectionObserver) {
            intersectionObserver.disconnect();
            intersectionObserver = null;
        }
        if (minimapInstance && typeof minimapInstance.cleanup === 'function') {
            minimapInstance.cleanup();
            minimapInstance = null;
        }
    }

    // Initialize when DOM is ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initMinimap);
    } else {
        initMinimap();
    }

    window.addEventListener('d3:ready', initMinimap);
    window.addEventListener('beforeunload', cleanup);
    window.addEventListener('pagehide', cleanup);

    // Export
    if (typeof window !== 'undefined') {
        window.GraphMinimap = GraphMinimap;
        window.BengalGraphMinimap = { cleanup };
    }
})();
