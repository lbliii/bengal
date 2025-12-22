/**
 * Bengal SSG - Contextual Graph Minimap Component (v2)
 *
 * Renders a small, filtered graph visualization showing only connections
 * to the current page. Similar to Obsidian's contextual graph view.
 * Designed to be embedded in the right sidebar above the TOC.
 *
 * Performance optimizations (v2):
 * - Removed MutationObserver (use CSS custom properties for theming)
 * - Faster force simulation with early termination
 * - Static layout option for minimal CPU usage
 * - Debounced theme change handling
 * - Single getComputedStyle call per theme change
 */

(function() {
    'use strict';

    // Debounce utility (avoid importing utils.js dependency)
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
     * Contextual Graph Minimap Component
     * Shows only the current page and its direct connections
     */
    class ContextualGraphMinimap {
        constructor(container, options = {}) {
            this.container = typeof container === 'string'
                ? document.querySelector(container)
                : container;

            if (!this.container) {
                console.warn('ContextualGraphMinimap: Container not found');
                return;
            }

            this.options = {
                width: options.width || 200,
                height: options.height || 200,
                dataUrl: options.dataUrl || this._getPageJsonUrl(),
                currentPageUrl: options.currentPageUrl || window.location.pathname,
                maxConnections: options.maxConnections || 15,
                usePageJson: options.usePageJson !== false,
                // Use force simulation for organic feel (static layout available as fallback)
                staticLayout: options.staticLayout || false,
                ...options
            };

            this.data = null;
            this.filteredData = null;
            this.simulation = null;
            this.svg = null;
            this.g = null;
            this.nodes = null;
            this.links = null;

            // v2: Store bound handlers for cleanup
            this._boundHandlers = {};

            this.init();
        }

        _getPageJsonUrl() {
            const path = window.location.pathname;
            if (path.endsWith('/')) {
                return path + 'index.json';
            } else {
                return path.substring(0, path.lastIndexOf('/') + 1) + 'index.json';
            }
        }

        async init() {
            try {
                let jsonData = null;
                let loadedFromPageJson = false;

                if (this.options.usePageJson) {
                    try {
                        const pageJsonUrl = this._getPageJsonUrl();
                        const response = await fetch(pageJsonUrl);
                        if (response.ok) {
                            jsonData = await response.json();
                            if (jsonData && jsonData.graph) {
                                this.filteredData = jsonData.graph;
                                this.data = jsonData.graph;

                                const currentUrl = this.normalizeUrl(this.options.currentPageUrl);
                                this.filteredData.nodes.forEach(node => {
                                    delete node.isCurrent;
                                    const nodeUrl = this.normalizeUrl(node.url);
                                    if (nodeUrl === currentUrl) {
                                        node.isCurrent = true;
                                    }
                                });

                                loadedFromPageJson = true;
                            }
                        }
                    } catch (e) {
                        // Fall through to global graph.json
                    }
                }

                if (!loadedFromPageJson) {
                    let baseurl = '';
                    try {
                        const m = document.querySelector('meta[name="bengal:baseurl"]');
                        baseurl = (m && m.getAttribute('content')) || '';
                        if (baseurl) baseurl = baseurl.replace(/\/$/, '');
                    } catch (e) {}

                    const fallbackUrl = baseurl + '/graph/graph.json';
                    const response = await fetch(fallbackUrl);
                    if (!response.ok) {
                        throw new Error(`Failed to load graph data: ${response.status}`);
                    }
                    jsonData = await response.json();
                    this.data = jsonData;
                    this.filterData();
                }

                if (this.filteredData && this.filteredData.nodes && this.filteredData.nodes.length > 0) {
                    const graphContainer = this.container.querySelector('.graph-contextual-container');
                    if (graphContainer) {
                        graphContainer.classList.remove('graph-loading');
                    }

                    this.createSVG();
                    this.render();
                } else {
                    this._hideContainer();
                }
            } catch (error) {
                this._hideContainer();
            }
        }

        _hideContainer() {
            const graphContainer = this.container.querySelector('.graph-contextual-container');
            if (graphContainer) {
                graphContainer.style.display = 'none';
            }
            this.container.style.display = 'none';
        }

        filterData() {
            if (!this.data || !this.data.nodes || !this.data.edges) {
                this.filteredData = { nodes: [], edges: [] };
                return;
            }

            const currentUrl = this.normalizeUrl(this.options.currentPageUrl);
            const currentNode = this.data.nodes.find(node => {
                const nodeUrl = this.normalizeUrl(node.url);
                return nodeUrl === currentUrl;
            });

            if (!currentNode) {
                this.filteredData = { nodes: [], edges: [] };
                return;
            }

            const connectedNodeIds = new Set([currentNode.id]);
            const connectedEdges = this.data.edges.filter(edge => {
                const sourceId = typeof edge.source === 'object' ? edge.source.id : edge.source;
                const targetId = typeof edge.target === 'object' ? edge.target.id : edge.target;
                return sourceId === currentNode.id || targetId === currentNode.id;
            });

            connectedEdges.forEach(edge => {
                const sourceId = typeof edge.source === 'object' ? edge.source.id : edge.source;
                const targetId = typeof edge.target === 'object' ? edge.target.id : edge.target;
                if (sourceId === currentNode.id) {
                    connectedNodeIds.add(targetId);
                } else {
                    connectedNodeIds.add(sourceId);
                }
            });

            const connectedNodes = this.data.nodes.filter(node => connectedNodeIds.has(node.id));
            connectedNodes.sort((a, b) => {
                const aConn = (a.incoming_refs || 0) + (a.outgoing_refs || 0);
                const bConn = (b.incoming_refs || 0) + (b.outgoing_refs || 0);
                return bConn - aConn;
            });

            const limitedNodes = connectedNodes.slice(0, this.options.maxConnections);
            const limitedNodeIds = new Set(limitedNodes.map(n => n.id));

            const filteredEdges = this.data.edges.filter(edge => {
                const sourceId = typeof edge.source === 'object' ? edge.source.id : edge.source;
                const targetId = typeof edge.target === 'object' ? edge.target.id : edge.target;
                return limitedNodeIds.has(sourceId) && limitedNodeIds.has(targetId);
            });

            limitedNodes.forEach(node => {
                delete node.isCurrent;
                delete node.isPreviousPage;
                if (node.id === currentNode.id) {
                    node.isCurrent = true;
                }
            });

            this.markPreviousPageNode(limitedNodes);

            this.filteredData = {
                nodes: limitedNodes,
                edges: filteredEdges
            };
        }

        markPreviousPageNode(nodes) {
            if (typeof window === 'undefined' || !window.bengalSessionPath) return;

            const pathTracker = window.bengalSessionPath;
            const previousPageUrl = pathTracker.getPreviousPage();
            if (!previousPageUrl) return;

            nodes.forEach(node => {
                const nodeUrl = this.normalizeUrl(node.url);
                if (pathTracker.isPreviousPage(nodeUrl)) {
                    node.isPreviousPage = true;
                }
            });
        }

        normalizeUrl(url) {
            if (!url) return '';
            let normalized = url;

            if (normalized.startsWith('http://') || normalized.startsWith('https://')) {
                try {
                    const urlObj = new URL(normalized);
                    normalized = urlObj.pathname;
                } catch (e) {
                    const match = normalized.match(/https?:\/\/[^\/]+(\/.*)/);
                    if (match) normalized = match[1];
                }
            }

            normalized = normalized.replace(/\/+$/, '') || '/';
            if (!normalized.startsWith('/')) normalized = '/' + normalized;

            return normalized;
        }

        createSVG() {
            let wrapper = this.container.querySelector('.graph-contextual-container');
            if (!wrapper) {
                wrapper = document.createElement('div');
                wrapper.className = 'graph-contextual-container';
                this.container.appendChild(wrapper);
            } else {
                wrapper.classList.remove('graph-loading');
                wrapper.innerHTML = '';
            }

            const containerRect = wrapper.getBoundingClientRect();
            const width = containerRect.width || Number(this.options.width) || 200;
            const height = containerRect.height || Number(this.options.height) || 200;
            const viewBoxValue = '0 0 ' + width + ' ' + height;

            wrapper.classList.add('graph-loaded', 'graph-visible');

            this.svg = d3.select(wrapper)
                .append('svg')
                .attr('width', width)
                .attr('height', height)
                .attr('viewBox', viewBoxValue)
                .attr('class', 'graph-svg-visible');

            this.g = this.svg.append('g');

            // v2: Simpler zoom - no initial transform offset
            // The static layout already centers the current node at (width/2, height/2)
            const zoom = d3.zoom()
                .scaleExtent([0.5, 3])
                .on('zoom', (event) => {
                    this.g.attr('transform', event.transform);
                });

            this.svg.call(zoom);
        }

        render() {
            if (!this.filteredData && this.data) {
                this.filterData();
            }

            if (!this.filteredData || !this.filteredData.nodes || this.filteredData.nodes.length === 0) {
                const graphContainer = this.container.querySelector('.graph-contextual-container');
                if (graphContainer) graphContainer.style.display = 'none';
                return;
            }

            const nodeMap = new Map(this.filteredData.nodes.map(n => [n.id, n]));
            const preparedEdges = this.filteredData.edges.map(edge => {
                const sourceId = typeof edge.source === 'object' ? edge.source.id : edge.source;
                const targetId = typeof edge.target === 'object' ? edge.target.id : edge.target;
                return {
                    source: nodeMap.get(sourceId),
                    target: nodeMap.get(targetId)
                };
            }).filter(e => e.source && e.target);

            const width = Number(this.options.width) || 200;
            const height = Number(this.options.height) || 200;

            // v2: Resolve colors once before rendering (not on every tick)
            this._resolveNodeColorsOnce();

            // v2: Use static layout or very fast simulation
            if (this.options.staticLayout) {
                this._computeStaticLayout(width, height);
            } else {
                this._createSimulation(preparedEdges, width, height);
            }

            // Render links
            this.links = this.g.append('g')
                .attr('class', 'graph-links')
                .selectAll('line')
                .data(preparedEdges)
                .enter()
                .append('line')
                .attr('class', 'graph-link')
                .attr('x1', d => d.source.x)
                .attr('y1', d => d.source.y)
                .attr('x2', d => d.target.x)
                .attr('y2', d => d.target.y);

            // Render nodes
            this.nodes = this.g.append('g')
                .attr('class', 'graph-nodes')
                .selectAll('circle')
                .data(this.filteredData.nodes)
                .enter()
                .append('circle')
                .attr('class', d => {
                    let classes = 'graph-node';
                    if (d.isCurrent) classes += ' graph-node-current';
                    if (d.isPreviousPage) classes += ' graph-node-previous';
                    return classes;
                })
                .attr('r', d => d.isCurrent ? 8 : (d.isPreviousPage ? 6 : 5))
                .attr('cx', d => d.x)
                .attr('cy', d => d.y)
                .attr('fill', d => d._resolvedColor || d.color || '#9e9e9e')
                .style('cursor', 'pointer')
                .style('pointer-events', 'all')
                .on('click', (event, d) => {
                    event.preventDefault();
                    event.stopPropagation();
                    if (d.url && !d.isCurrent) {
                        let targetUrl = d.url;
                        if (targetUrl.startsWith('http://') || targetUrl.startsWith('https://')) {
                            try {
                                targetUrl = new URL(targetUrl).pathname;
                            } catch (e) {}
                        }
                        if (!targetUrl.endsWith('/') && !targetUrl.includes('#')) {
                            targetUrl += '/';
                        }
                        window.location.href = targetUrl;
                    }
                })
                .on('mouseover', (event, d) => {
                    this.showTooltip(event, d);
                    this.highlightConnections(d);
                })
                .on('mouseout', () => {
                    this.hideTooltip();
                    this.clearHighlights();
                });

            // v2: Setup lightweight theme listener (event-only, no MutationObserver)
            this._setupThemeListener();

            this.addExpandButton();

            const wrapper = this.container.querySelector('.graph-contextual-container');
            if (wrapper) wrapper.classList.add('graph-visible');
        }

        /**
         * v2: Compute static layout (radial around center node)
         * No animation = no DevTools performance issues
         */
        _computeStaticLayout(width, height) {
            const centerX = width / 2;
            const centerY = height / 2;
            const radius = Math.min(width, height) * 0.38;

            // Find current node and place at center
            const currentNode = this.filteredData.nodes.find(n => n.isCurrent);
            const otherNodes = this.filteredData.nodes.filter(n => !n.isCurrent);

            if (currentNode) {
                currentNode.x = centerX;
                currentNode.y = centerY;
            }

            // Distribute other nodes in a circle
            const angleStep = (2 * Math.PI) / Math.max(otherNodes.length, 1);
            otherNodes.forEach((node, i) => {
                const angle = i * angleStep - Math.PI / 2; // Start from top
                node.x = centerX + radius * Math.cos(angle);
                node.y = centerY + radius * Math.sin(angle);
            });
        }

        /**
         * Create animated force simulation for organic feel
         */
        _createSimulation(preparedEdges, width, height) {
            const padding = 5;

            this.simulation = d3.forceSimulation(this.filteredData.nodes)
                .alphaDecay(0.05)       // Gentle decay for smooth animation
                .alphaMin(0.01)         // Stop when stable
                .velocityDecay(0.4)     // Some friction
                .force('link', d3.forceLink(preparedEdges).id(d => d.id).distance(40))
                .force('charge', d3.forceManyBody().strength(-80))
                .force('center', d3.forceCenter(width / 2, height / 2))
                .force('collision', d3.forceCollide().radius(8));

            // Animate positions on each tick
            this.simulation.on('tick', () => {
                // Constrain to bounds
                this.filteredData.nodes.forEach(node => {
                    node.x = Math.max(padding, Math.min(width - padding, node.x));
                    node.y = Math.max(padding, Math.min(height - padding, node.y));
                });

                // Update link positions
                if (this.links) {
                    this.links
                        .attr('x1', d => d.source.x)
                        .attr('y1', d => d.source.y)
                        .attr('x2', d => d.target.x)
                        .attr('y2', d => d.target.y);
                }

                // Update node positions
                if (this.nodes) {
                    this.nodes
                        .attr('cx', d => d.x)
                        .attr('cy', d => d.y);
                }
            });

            // Stop after reasonable time to save CPU
            this._simulationTimeout = setTimeout(() => {
                if (this.simulation) {
                    this.simulation.stop();
                }
                this._simulationTimeout = null;
            }, 2000);
        }

        /**
         * v2: Resolve CSS variables once, not on every update
         */
        _resolveNodeColorsOnce() {
            if (!this.filteredData || !this.filteredData.nodes) return;

            // Single getComputedStyle call
            const styles = getComputedStyle(document.documentElement);

            this.filteredData.nodes.forEach(node => {
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
         * Debounced to prevent rapid fire updates
         */
        _setupThemeListener() {
            // Debounced handler to prevent thrashing
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

            // Note: NO MutationObserver - this was causing DevTools crashes
            // The theme.js dispatches themechange/palettechange events which is sufficient
        }

        highlightConnections(d) {
            const connectedNodeIds = new Set([d.id]);

            this.filteredData.edges.forEach(e => {
                const sourceId = typeof e.source === 'object' ? e.source.id : e.source;
                const targetId = typeof e.target === 'object' ? e.target.id : e.target;
                if (sourceId === d.id || targetId === d.id) {
                    connectedNodeIds.add(sourceId === d.id ? targetId : sourceId);
                }
            });

            this.nodes.classed('highlighted', n => connectedNodeIds.has(n.id));
            this.links.classed('highlighted', e => {
                const sourceId = typeof e.source === 'object' ? e.source.id : e.source;
                const targetId = typeof e.target === 'object' ? e.target.id : e.target;
                return sourceId === d.id || targetId === d.id;
            });
        }

        clearHighlights() {
            this.nodes.classed('highlighted', false);
            this.links.classed('highlighted', false);
        }

        addExpandButton() {
            const wrapper = this.container.querySelector('.graph-contextual-container');
            if (!wrapper) return;

            const expandBtn = document.createElement('div');
            expandBtn.className = 'graph-contextual-expand';
            expandBtn.setAttribute('role', 'button');
            expandBtn.setAttribute('aria-label', 'Expand to full graph');
            expandBtn.setAttribute('data-tooltip-position', 'top');
            expandBtn.innerHTML = `
                <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="svg-icon lucide-arrow-up-right">
                    <path d="M7 7h10v10"></path>
                    <path d="M7 17 17 7"></path>
                </svg>
            `;
            expandBtn.addEventListener('click', () => {
                let baseurl = '';
                try {
                    const m = document.querySelector('meta[name="bengal:baseurl"]');
                    baseurl = (m && m.getAttribute('content')) || '';
                    if (baseurl) baseurl = baseurl.replace(/\/$/, '');
                } catch (e) {}
                window.location.href = baseurl + '/graph/';
            });
            wrapper.appendChild(expandBtn);
        }

        showTooltip(event, d) {
            const existing = document.querySelector('.graph-contextual-tooltip');
            if (existing) existing.remove();

            const tooltip = document.createElement('div');
            tooltip.className = 'graph-contextual-tooltip';
            tooltip.innerHTML = `<div class="graph-contextual-tooltip-title">${d.label || 'Untitled'}</div>`;
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
            const tooltip = document.querySelector('.graph-contextual-tooltip');
            if (tooltip) tooltip.remove();
        }

        cleanup() {
            // Clear simulation timeout
            if (this._simulationTimeout) {
                clearTimeout(this._simulationTimeout);
                this._simulationTimeout = null;
            }

            // Stop simulation
            if (this.simulation) {
                this.simulation.stop();
                this.simulation = null;
            }

            // Remove event listeners
            if (this._boundHandlers.themechange) {
                window.removeEventListener('themechange', this._boundHandlers.themechange);
            }
            if (this._boundHandlers.palettechange) {
                window.removeEventListener('palettechange', this._boundHandlers.palettechange);
            }
            this._boundHandlers = {};
        }
    }

    // Module-level state
    let contextualGraphInstance = null;
    let intersectionObserver = null;

    function initContextualGraph() {
        const contextualContainer = document.querySelector('.graph-contextual');
        if (!contextualContainer) return;

        // Use IntersectionObserver for lazy initialization
        if ('IntersectionObserver' in window) {
            intersectionObserver = new IntersectionObserver((entries) => {
                entries.forEach(entry => {
                    if (entry.isIntersecting) {
                        intersectionObserver.disconnect();
                        intersectionObserver = null;
                        initGraphWhenD3Ready(contextualContainer);
                    }
                });
            }, { rootMargin: '100px' });

            intersectionObserver.observe(contextualContainer);
        } else {
            initGraphWhenD3Ready(contextualContainer);
        }
    }

    function initGraphWhenD3Ready(contextualContainer) {
        let retries = 0;
        const maxRetries = 50;

        function checkD3() {
            if (typeof d3 !== 'undefined') {
                const currentPageUrl = contextualContainer.dataset.pageUrl || window.location.pathname;
                try {
                    contextualGraphInstance = new ContextualGraphMinimap(contextualContainer, {
                        currentPageUrl: currentPageUrl
                    });
                } catch (error) {
                    contextualContainer.classList.add('graph-hidden');
                }
            } else if (retries < maxRetries) {
                retries++;
                setTimeout(checkD3, 100);
            } else {
                contextualContainer.classList.add('graph-hidden');
            }
        }

        checkD3();
    }

    function cleanup() {
        if (intersectionObserver) {
            intersectionObserver.disconnect();
            intersectionObserver = null;
        }
        if (contextualGraphInstance && typeof contextualGraphInstance.cleanup === 'function') {
            contextualGraphInstance.cleanup();
            contextualGraphInstance = null;
        }
    }

    // Initialize when DOM is ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initContextualGraph);
    } else {
        initContextualGraph();
    }

    window.addEventListener('d3:ready', initContextualGraph);
    window.addEventListener('beforeunload', cleanup);
    window.addEventListener('pagehide', cleanup);

    // Export
    if (typeof window !== 'undefined') {
        window.ContextualGraphMinimap = ContextualGraphMinimap;
        window.BengalContextualGraph = { cleanup };
    }
})();
