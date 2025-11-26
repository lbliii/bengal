/**
 * Bengal SSG - Contextual Graph Minimap Component
 *
 * Renders a small, filtered graph visualization showing only connections
 * to the current page. Similar to Obsidian's contextual graph view.
 * Designed to be embedded in the right sidebar above the TOC.
 */

(function() {
    'use strict';

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
                // Try page JSON first, fallback to global graph.json
                dataUrl: options.dataUrl || this._getPageJsonUrl(),
                currentPageUrl: options.currentPageUrl || window.location.pathname,
                maxConnections: options.maxConnections || 15, // Limit nodes for performance
                usePageJson: options.usePageJson !== false, // Default to true
                ...options
            };

            this.data = null;
            this.filteredData = null;
            this.simulation = null;
            this.svg = null;
            this.g = null;
            this.nodes = null;
            this.links = null;

            this.init();
        }

        _getPageJsonUrl() {
            // Get current page path and construct JSON URL
            // JSON files are named index.json and placed next to HTML files
            const path = window.location.pathname;
            // Ensure path ends with /index.json (Bengal's convention)
            if (path.endsWith('/')) {
                return path + 'index.json';
            } else {
                // If path doesn't end with /, it's likely a file path
                // Remove filename and add /index.json
                return path.substring(0, path.lastIndexOf('/') + 1) + 'index.json';
            }
        }

        async init() {
            try {
                let jsonData = null;
                let loadedFromPageJson = false;

                // Try loading from page JSON first (if enabled)
                if (this.options.usePageJson) {
                    try {
                        const pageJsonUrl = this._getPageJsonUrl();
                        const response = await fetch(pageJsonUrl);
                        if (response.ok) {
                            jsonData = await response.json();
                            // Check if page JSON has graph data
                            if (jsonData && jsonData.graph) {
                                // Data is already filtered in page JSON
                                // BUT: We need to re-validate isCurrent flags because
                                // the page JSON might have been generated for a different page
                                // (e.g., if you're on /docs/guides/blog-from-scratch/ but
                                // the JSON was cached for /docs/guides/)
                                this.filteredData = jsonData.graph;
                                this.data = jsonData.graph; // Keep for reference

                                // Re-validate isCurrent flags - clear all and set only the actual current page
                                const currentUrl = this.normalizeUrl(this.options.currentPageUrl);
                                this.filteredData.nodes.forEach(node => {
                                    delete node.isCurrent; // Clear existing flag
                                    const nodeUrl = this.normalizeUrl(node.url);
                                    // Only mark as current if URL matches exactly (not parent/child)
                                    if (nodeUrl === currentUrl) {
                                        node.isCurrent = true;
                                    }
                                });

                                loadedFromPageJson = true;
                            }
                        }
                    } catch (e) {
                        // Page JSON doesn't exist or failed - fall through to global graph.json
                        // Silently fall back - this is expected for pages without graph data
                    }
                }

                // Fallback to global graph.json if page JSON didn't work
                if (!loadedFromPageJson) {
                    // Get baseurl from meta tag if present
                    let baseurl = '';
                    try {
                        const m = document.querySelector('meta[name="bengal:baseurl"]');
                        baseurl = (m && m.getAttribute('content')) || '';
                        if (baseurl) {
                            baseurl = baseurl.replace(/\/$/, '');
                        }
                    } catch (e) {
                        // Ignore errors
                    }
                    const fallbackUrl = baseurl + '/graph/graph.json';
                    const response = await fetch(fallbackUrl);
                    if (!response.ok) {
                        throw new Error(`Failed to load graph data: ${response.status}`);
                    }
                    jsonData = await response.json();
                    // Loading from global graph.json - need to filter
                    this.data = jsonData;
                    this.filterData();
                }

                // Only create SVG and render if we have data
                if (this.filteredData && this.filteredData.nodes && this.filteredData.nodes.length > 0) {
                    // Create SVG container
                    this.createSVG();

                    // Render graph
                    this.render();
                } else {
                    // No connections - hide container but keep header visible
                    const graphContainer = this.container.querySelector('.graph-contextual-container');
                    if (graphContainer) {
                        graphContainer.style.display = 'none';
                    } else {
                        // Replace loading placeholder with "No connections" message
                        this.container.innerHTML = '<div class="graph-contextual-container" style="padding: var(--space-4); text-align: center; color: var(--color-text-secondary); font-size: 12px;">No connections</div>';
                    }
                }
            } catch (error) {
                // Replace loading placeholder with error message
                const graphContainer = this.container.querySelector('.graph-contextual-container');
                if (graphContainer) {
                    graphContainer.innerHTML = '<div style="padding: var(--space-4); text-align: center; color: var(--color-text-secondary); font-size: 12px;">Graph unavailable</div>';
                } else {
                    // If container doesn't exist yet, create error message
                    this.container.innerHTML = '<div class="graph-contextual-container" style="padding: var(--space-4); text-align: center; color: var(--color-text-secondary); font-size: 12px;">Graph unavailable</div>';
                }
            }
        }

        filterData() {
            if (!this.data || !this.data.nodes || !this.data.edges) {
                this.filteredData = { nodes: [], edges: [] };
                return;
            }

            // Normalize current page URL for matching
            const currentUrl = this.normalizeUrl(this.options.currentPageUrl);

            // Find current page node - exact match only (don't match parent/child paths)
            const currentNode = this.data.nodes.find(node => {
                const nodeUrl = this.normalizeUrl(node.url);
                return nodeUrl === currentUrl;
            });

            if (!currentNode) {
                // Current page not in graph (might be excluded)
                this.filteredData = { nodes: [], edges: [] };
                return;
            }

            // Collect connected node IDs
            const connectedNodeIds = new Set([currentNode.id]);

            // Find all edges connected to current page
            const connectedEdges = this.data.edges.filter(edge => {
                const sourceId = typeof edge.source === 'object' ? edge.source.id : edge.source;
                const targetId = typeof edge.target === 'object' ? edge.target.id : edge.target;
                return sourceId === currentNode.id || targetId === currentNode.id;
            });

            // Collect all connected nodes
            connectedEdges.forEach(edge => {
                const sourceId = typeof edge.source === 'object' ? edge.source.id : edge.source;
                const targetId = typeof edge.target === 'object' ? edge.target.id : edge.target;

                if (sourceId === currentNode.id) {
                    connectedNodeIds.add(targetId);
                } else {
                    connectedNodeIds.add(sourceId);
                }
            });

            // Limit to maxConnections (keep current page + most connected)
            const connectedNodes = this.data.nodes.filter(node => connectedNodeIds.has(node.id));

            // Sort by connectivity (incoming + outgoing refs) and limit
            connectedNodes.sort((a, b) => {
                const aConn = (a.incoming_refs || 0) + (a.outgoing_refs || 0);
                const bConn = (b.incoming_refs || 0) + (b.outgoing_refs || 0);
                return bConn - aConn;
            });

            const limitedNodes = connectedNodes.slice(0, this.options.maxConnections);
            const limitedNodeIds = new Set(limitedNodes.map(n => n.id));

            // Filter edges to only include connections between limited nodes
            const filteredEdges = this.data.edges.filter(edge => {
                const sourceId = typeof edge.source === 'object' ? edge.source.id : edge.source;
                const targetId = typeof edge.target === 'object' ? edge.target.id : edge.target;
                return limitedNodeIds.has(sourceId) && limitedNodeIds.has(targetId);
            });

            // Mark current page - clear any existing isCurrent flags first
            // IMPORTANT: Only mark the exact current page, not parent/child pages
            limitedNodes.forEach(node => {
                // Clear existing flags (in case they were set in page JSON)
                delete node.isCurrent;
                delete node.isPreviousPage;
                // Set only for the actual current node (exact URL match)
                if (node.id === currentNode.id) {
                    node.isCurrent = true;
                }
            });

            // Mark previous page node (if visible)
            this.markPreviousPageNode(limitedNodes);

            this.filteredData = {
                nodes: limitedNodes,
                edges: filteredEdges
            };
        }

        /**
         * Mark the previous page node (if visible in graph)
         * @param {Array} nodes - Array of node objects
         */
        markPreviousPageNode(nodes) {
            // Check if session path tracker is available
            if (typeof window === 'undefined' || !window.bengalSessionPath) {
                return;
            }

            const pathTracker = window.bengalSessionPath;
            const previousPageUrl = pathTracker.getPreviousPage();

            if (!previousPageUrl) {
                return; // No previous page tracked
            }

            // Mark the node that matches the previous page
            nodes.forEach(node => {
                const nodeUrl = this.normalizeUrl(node.url);
                if (pathTracker.isPreviousPage(nodeUrl)) {
                    node.isPreviousPage = true;
                }
            });
        }

        normalizeUrl(url) {
            if (!url) return '';
            // Normalize URL for comparison - remove trailing slashes and baseurl
            let normalized = url;

            // Remove protocol/host if present (absolute URL)
            if (normalized.startsWith('http://') || normalized.startsWith('https://')) {
                try {
                    const urlObj = new URL(normalized);
                    normalized = urlObj.pathname;
                } catch (e) {
                    // Invalid URL, try to extract path manually
                    const match = normalized.match(/https?:\/\/[^\/]+(\/.*)/);
                    if (match) {
                        normalized = match[1];
                    }
                }
            }

            // Remove trailing slashes for comparison (both should match)
            // But preserve the distinction between /docs/guides/ and /docs/guides/blog-from-scratch/
            normalized = normalized.replace(/\/+$/, '') || '/';

            // Ensure it starts with / for consistency
            if (!normalized.startsWith('/')) {
                normalized = '/' + normalized;
            }

            return normalized;
        }

        createSVG() {
            // Get or create wrapper
            let wrapper = this.container.querySelector('.graph-contextual-container');
            if (!wrapper) {
                // Create wrapper if it doesn't exist
                wrapper = document.createElement('div');
                wrapper.className = 'graph-contextual-container';
                this.container.appendChild(wrapper);
            } else {
                // Clear existing content (including loading placeholder)
                wrapper.innerHTML = '';
            }

            // Get actual container dimensions (use computed style to match CSS)
            const containerRect = wrapper.getBoundingClientRect();
            const width = containerRect.width || Number(this.options.width) || 200;
            const height = containerRect.height || Number(this.options.height) || 200; // Match CSS height

            // Ensure proper spacing in viewBox string - explicitly format with spaces
            const viewBoxValue = '0 0 ' + width + ' ' + height;

            this.svg = d3.select(wrapper)
                .append('svg')
                .attr('width', width)
                .attr('height', height)
                .attr('viewBox', viewBoxValue)
                .style('display', 'block');

            // Create group for panning
            this.g = this.svg.append('g');

            // Add pan/zoom behavior (limited for contextual view)
            const zoom = d3.zoom()
                .scaleExtent([0.8, 3]) // Zoom in more by default (0.8x = 125% zoom)
                .on('zoom', (event) => {
                    // Constrain panning to prevent nodes from going too far outside view
                    const transform = event.transform;
                    const k = transform.k;
                    const tx = Math.max(-width * (k - 1), Math.min(0, transform.x));
                    const ty = Math.max(-height * (k - 1), Math.min(0, transform.y));
                    this.g.attr('transform', d3.zoomIdentity.translate(tx, ty).scale(k));
                });

            // Set initial zoom to be closer (1.2x = zoomed in)
            // Reuse width/height from above
            const initialZoom = d3.zoomIdentity.scale(1.2).translate(
                width * 0.1, // Slight offset to center better
                height * 0.1
            );
            this.svg.call(zoom.transform, initialZoom);

            this.svg.call(zoom);
        }

        render() {
            // Ensure filteredData is set
            if (!this.filteredData && this.data) {
                this.filterData();
            }

            if (!this.filteredData || !this.filteredData.nodes || this.filteredData.nodes.length === 0) {
                // Hide only the graph container, not the whole section
                const graphContainer = this.container.querySelector('.graph-contextual-container');
                if (graphContainer) {
                    graphContainer.style.display = 'none';
                }
                return;
            }

            // Prepare edges for D3 (convert IDs to node references)
            const nodeMap = new Map(this.filteredData.nodes.map(n => [n.id, n]));
            const preparedEdges = this.filteredData.edges.map(edge => {
                const sourceId = typeof edge.source === 'object' ? edge.source.id : edge.source;
                const targetId = typeof edge.target === 'object' ? edge.target.id : edge.target;
                return {
                    source: nodeMap.get(sourceId),
                    target: nodeMap.get(targetId)
                };
            }).filter(e => e.source && e.target); // Filter out invalid edges

            // Get numeric dimensions for simulation
            const width = Number(this.options.width) || 200;
            const height = Number(this.options.height) || 200;

            // Create force simulation with faster cooling to stop sooner
            this.simulation = d3.forceSimulation(this.filteredData.nodes)
                .alphaDecay(0.1) // Faster decay (default 0.0228) - stops animation sooner
                .velocityDecay(0.4) // More friction (default 0.4) - reduces jitter
                .force('link', d3.forceLink(preparedEdges)
                    .id(d => d.id)
                    .distance(20))
                .force('charge', d3.forceManyBody()
                    .strength(-60))
                .force('center', d3.forceCenter(width / 2, height / 2))
                .force('collision', d3.forceCollide()
                    .radius(d => Math.max((d.size || 5) * 0.25, 2)));

            // Render links (use same class as full graph for shared styling)
            this.links = this.g.append('g')
                .attr('class', 'graph-links')
                .selectAll('line')
                .data(preparedEdges)
                .enter()
                .append('line')
                .attr('class', 'graph-link');

            // Resolve CSS variables in node colors before rendering
            try {
                this.resolveNodeColors();
            } catch (e) {
                console.warn('ContextualGraphMinimap: Error resolving node colors', e);
            }

            // Render nodes (use same class as full graph, smaller sizes for contextual)
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
                .attr('r', d => {
                    // Current page: largest, previous page: medium, others: smallest
                    if (d.isCurrent) return 3;
                    if (d.isPreviousPage) return 2.5;
                    return 2;
                })
                .attr('fill', d => d.color || '#9e9e9e')
                .style('cursor', 'pointer')
                .style('pointer-events', 'all') // Ensure clicks are captured
                .on('click', (event, d) => {
                    event.preventDefault();
                    event.stopPropagation();

                    // Only navigate if node has URL and isn't current page
                    if (d.url && !d.isCurrent) {
                        // Normalize URL for navigation
                        let targetUrl = d.url;

                        // Remove baseurl if present (extract path from absolute URL)
                        if (targetUrl.startsWith('http://') || targetUrl.startsWith('https://')) {
                            try {
                                const urlObj = new URL(targetUrl);
                                targetUrl = urlObj.pathname;
                            } catch (e) {
                                // Invalid URL, use as-is
                            }
                        }

                        // Ensure trailing slash for directory-like URLs (Bengal convention)
                        // This handles index files correctly: /docs/page/ -> /docs/page/
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

            // Listen for theme changes to re-resolve colors (after nodes are rendered)
            try {
                this.setupThemeListener();
            } catch (e) {
                // Silently fail - theme changes won't update colors, but graph will still work
            }

            // Constrain nodes to container bounds (use same dimensions as simulation)
            const padding = 5; // Padding from edges

            // Update positions on simulation tick with boundary constraints
            this.simulation.on('tick', () => {
                // Constrain node positions to stay within bounds
                this.filteredData.nodes.forEach(node => {
                    node.x = Math.max(padding, Math.min(width - padding, node.x));
                    node.y = Math.max(padding, Math.min(height - padding, node.y));
                });

                this.links
                    .attr('x1', d => d.source.x)
                    .attr('y1', d => d.source.y)
                    .attr('x2', d => d.target.x)
                    .attr('y2', d => d.target.y);

                this.nodes
                    .attr('cx', d => d.x)
                    .attr('cy', d => d.y);
            });

            // Add expand button
            this.addExpandButton();

            // Stop simulation after initial layout (shorter timeout to prevent jitter)
            // Also stop when simulation naturally cools down
            this.simulation.on('end', () => {
                if (this._simulationTimeout) {
                    clearTimeout(this._simulationTimeout);
                    this._simulationTimeout = null;
                }
            });

            this._simulationTimeout = setTimeout(() => {
                if (this.simulation) {
                    this.simulation.stop();
                }
                this._simulationTimeout = null;
            }, 1000); // Reduced from 1500ms to stop sooner
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
                // Get baseurl from meta tag if present
                let baseurl = '';
                try {
                    const m = document.querySelector('meta[name="bengal:baseurl"]');
                    baseurl = (m && m.getAttribute('content')) || '';
                    if (baseurl) {
                        baseurl = baseurl.replace(/\/$/, '');
                    }
                } catch (e) {
                    // Ignore errors
                }
                const graphUrl = baseurl + '/graph/';
                window.location.href = graphUrl;
            });
            wrapper.appendChild(expandBtn);
        }

        showTooltip(event, d) {
            // Remove existing tooltip
            const existing = document.querySelector('.graph-contextual-tooltip');
            if (existing) {
                existing.remove();
            }

            // Create tooltip
            const tooltip = document.createElement('div');
            tooltip.className = 'graph-contextual-tooltip';
            tooltip.innerHTML = `
                <div class="graph-contextual-tooltip-title">${d.label || 'Untitled'}</div>
            `;
            document.body.appendChild(tooltip);

            // Position tooltip
            const rect = tooltip.getBoundingClientRect();
            const x = event.pageX + 10;
            const y = event.pageY + 10;

            tooltip.style.left = `${x}px`;
            tooltip.style.top = `${y}px`;

            // Adjust if tooltip goes off screen
            if (x + rect.width > window.innerWidth) {
                tooltip.style.left = `${event.pageX - rect.width - 10}px`;
            }
            if (y + rect.height > window.innerHeight) {
                tooltip.style.top = `${event.pageY - rect.height - 10}px`;
            }
        }

        hideTooltip() {
            const tooltip = document.querySelector('.graph-contextual-tooltip');
            if (tooltip) {
                tooltip.remove();
            }
        }

        resolveNodeColors() {
            // Helper function to resolve CSS variables
            const resolveCSSVariable = (varName) => {
                const cleanVar = varName.replace(/var\(|\s|\)/g, '');
                const root = document.documentElement;
                const value = getComputedStyle(root).getPropertyValue(cleanVar).trim();
                return value || '#9e9e9e';
            };

            // Resolve CSS variables in node colors
            if (this.filteredData && this.filteredData.nodes) {
                this.filteredData.nodes.forEach(node => {
                    if (node.color && node.color.startsWith('var(')) {
                        const varMatch = node.color.match(/var\(([^)]+)\)/);
                        if (varMatch) {
                            const varName = varMatch[1].trim();
                            node.color = resolveCSSVariable(varName);
                        }
                    }
                });

                // Update rendered nodes if they exist
                if (this.nodes) {
                    this.nodes.attr('fill', d => d.color || '#9e9e9e');
                }
            }
        }

        setupThemeListener() {
            // Store references for cleanup
            this._themeChangeHandler = () => this.resolveNodeColors();
            this._paletteChangeHandler = () => this.resolveNodeColors();

            // Listen for theme changes (light/dark mode toggle)
            window.addEventListener('themechange', this._themeChangeHandler);

            // Listen for palette changes (color variant changes)
            window.addEventListener('palettechange', this._paletteChangeHandler);

            // Also watch for data-theme/data-palette attribute changes (MutationObserver)
            this._themeObserver = new MutationObserver((mutations) => {
                mutations.forEach((mutation) => {
                    if (mutation.type === 'attributes' &&
                        (mutation.attributeName === 'data-theme' || mutation.attributeName === 'data-palette')) {
                        this.resolveNodeColors();
                    }
                });
            });

            this._themeObserver.observe(document.documentElement, {
                attributes: true,
                attributeFilter: ['data-theme', 'data-palette']
            });
        }

        cleanup() {
            // Clear timeout if pending
            if (this._simulationTimeout) {
                clearTimeout(this._simulationTimeout);
                this._simulationTimeout = null;
            }

            // Remove event listeners
            if (this._themeChangeHandler) {
                window.removeEventListener('themechange', this._themeChangeHandler);
                this._themeChangeHandler = null;
            }
            if (this._paletteChangeHandler) {
                window.removeEventListener('palettechange', this._paletteChangeHandler);
                this._paletteChangeHandler = null;
            }

            // Disconnect MutationObserver
            if (this._themeObserver) {
                this._themeObserver.disconnect();
                this._themeObserver = null;
            }

            // Stop simulation if running
            if (this.simulation) {
                this.simulation.stop();
                this.simulation = null;
            }
        }
    }

    // Store instance for cleanup
    let contextualGraphInstance = null;

    // Auto-initialize if container exists
    function initContextualGraph() {
        const contextualContainer = document.querySelector('.graph-contextual');
        if (!contextualContainer) return;

        // Wait for D3.js to be available (with timeout)
        let retries = 0;
        const maxRetries = 50; // 5 seconds max wait

        function checkD3() {
            if (typeof d3 !== 'undefined') {
                // D3.js ready, initialize component
                const currentPageUrl = contextualContainer.dataset.pageUrl || window.location.pathname;
                try {
                    contextualGraphInstance = new ContextualGraphMinimap(contextualContainer, {
                        currentPageUrl: currentPageUrl
                    });
                } catch (error) {
                    // Replace loading placeholder with error
                    const container = contextualContainer.querySelector('.graph-contextual-container');
                    if (container) {
                        container.innerHTML = '<div style="padding: var(--space-4); text-align: center; color: var(--color-text-secondary); font-size: 12px;">Initialization error</div>';
                    }
                }
            } else if (retries < maxRetries) {
                retries++;
                setTimeout(checkD3, 100);
            } else {
                // Replace loading placeholder with error
                const container = contextualContainer.querySelector('.graph-contextual-container');
                if (container) {
                    container.innerHTML = '<div style="padding: var(--space-4); text-align: center; color: var(--color-text-secondary); font-size: 12px;">D3.js not loaded</div>';
                }
            }
        }

        checkD3();
    }

    // Cleanup function for memory leak prevention
    function cleanup() {
        if (contextualGraphInstance && typeof contextualGraphInstance.cleanup === 'function') {
            contextualGraphInstance.cleanup();
            contextualGraphInstance = null;
        }
    }

    // Initialize when DOM is ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initContextualGraph);
    } else {
        // DOM already ready, initialize immediately (but still wait for D3)
        initContextualGraph();
    }

    // Cleanup on page unload to prevent memory leaks
    window.addEventListener('beforeunload', cleanup);

    // Export for manual initialization and cleanup
    if (typeof window !== 'undefined') {
        window.ContextualGraphMinimap = ContextualGraphMinimap;
        window.BengalContextualGraph = {
            cleanup: cleanup
        };
    }
})();
