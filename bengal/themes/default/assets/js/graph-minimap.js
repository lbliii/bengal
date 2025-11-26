/**
 * Bengal SSG - Graph Minimap Component
 *
 * Renders a small, interactive graph visualization similar to Obsidian's minimap.
 * Designed to be embedded in the search page or other pages.
 */

(function() {
    'use strict';

    /**
     * Graph Minimap Component
     */
    class GraphMinimap {
        constructor(container, options = {}) {
            this.container = typeof container === 'string'
                ? document.querySelector(container)
                : container;

            if (!this.container) {
                return;
            }

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

            this.options = {
                width: options.width || 242,
                height: options.height || 250,
                dataUrl: options.dataUrl || (baseurl + '/graph/graph.json'),
                expandUrl: options.expandUrl || (baseurl + '/graph/'),
                ...options
            };

            this.data = null;
            this.simulation = null;
            this.svg = null;
            this.g = null;
            this.nodes = null;
            this.links = null;
            this.zoom = null;

            this.init();
        }

        async init() {
            try {
                // Load graph data
                const response = await fetch(this.options.dataUrl);
                if (!response.ok) {
                    throw new Error(`Failed to load graph data: ${response.status}`);
                }
                this.data = await response.json();

                // Create SVG container
                this.createSVG();

                // Render graph
                this.render();

                // Add expand button
                this.addExpandButton();
            } catch (error) {
                this.container.innerHTML = '<div class="graph-minimap-error">Graph unavailable</div>';
            }
        }

        createSVG() {
            // Clear container
            this.container.innerHTML = '';

            // Create wrapper
            const wrapper = document.createElement('div');
            wrapper.className = 'graph-minimap-container';
            this.container.appendChild(wrapper);

            // Create SVG
            this.svg = d3.select(wrapper)
                .append('svg')
                .attr('width', this.options.width)
                .attr('height', this.options.height)
                .style('display', 'block');

            // Create group for zoom/pan
            this.g = this.svg.append('g');

            // Set up zoom behavior (limited zoom for minimap)
            this.zoom = d3.zoom()
                .scaleExtent([0.5, 2])
                .on('zoom', (event) => {
                    this.g.attr('transform', event.transform);
                });

            this.svg.call(this.zoom);

            // Initial transform to center and scale
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

            // Create force simulation (simplified for minimap)
            this.simulation = d3.forceSimulation(this.data.nodes)
                .force('link', d3.forceLink(this.data.edges)
                    .id(d => d.id)
                    .distance(30))
                .force('charge', d3.forceManyBody()
                    .strength(-100))
                .force('center', d3.forceCenter(this.options.width / 2, this.options.height / 2))
                .force('collision', d3.forceCollide()
                    .radius(d => Math.max(d.size || 5, 3)));

            // Render links
            this.links = this.g.append('g')
                .attr('class', 'graph-minimap-links')
                .selectAll('line')
                .data(this.data.edges)
                .enter()
                .append('line')
                .attr('class', 'graph-minimap-link')
                .attr('stroke', 'var(--color-border-light, rgba(0, 0, 0, 0.1))')
                .attr('stroke-width', 0.5);

            // Helper function to resolve CSS variables
            const resolveCSSVariable = (varName) => {
                const cleanVar = varName.replace(/var\(|\s|\)/g, '');
                const root = document.documentElement;
                const value = getComputedStyle(root).getPropertyValue(cleanVar).trim();
                return value || '#9e9e9e';
            };

            // Resolve CSS variables in node colors
            this.resolveNodeColors();

            // Listen for theme changes to re-resolve colors
            this.setupThemeListener();

            // Render nodes
            this.nodes = this.g.append('g')
                .attr('class', 'graph-minimap-nodes')
                .selectAll('circle')
                .data(this.data.nodes)
                .enter()
                .append('circle')
                .attr('class', 'graph-minimap-node')
                .attr('r', d => Math.max((d.size || 5) * 0.3, 2))
                .attr('fill', d => d.color || '#9e9e9e')
                .attr('stroke', 'var(--color-border, rgba(0, 0, 0, 0.2))')
                .attr('stroke-width', 0.5)
                .style('cursor', 'pointer')
                .on('click', (event, d) => {
                    // Navigate to page on click
                    if (d.url) {
                        window.location.href = d.url;
                    }
                })
                .on('mouseover', (event, d) => {
                    // Show tooltip
                    this.showTooltip(event, d);
                    // Highlight connections
                    this.highlightConnections(d);
                })
                .on('mouseout', () => {
                    this.hideTooltip();
                    this.clearHighlights();
                });

            // Update positions on simulation tick
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

            // Stop simulation after a short time (minimap doesn't need continuous animation)
            this._simulationTimeout = setTimeout(() => {
                if (this.simulation) {
                    this.simulation.stop();
                }
                this._simulationTimeout = null;
            }, 2000);
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
            // Remove existing tooltip
            const existing = document.querySelector('.graph-minimap-tooltip');
            if (existing) {
                existing.remove();
            }

            // Create tooltip
            const tooltip = document.createElement('div');
            tooltip.className = 'graph-minimap-tooltip';
            tooltip.innerHTML = `
                <div class="graph-minimap-tooltip-title">${d.label || 'Untitled'}</div>
                <div class="graph-minimap-tooltip-meta">
                    ${d.incoming_refs || 0} incoming • ${d.outgoing_refs || 0} outgoing
                </div>
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
            const tooltip = document.querySelector('.graph-minimap-tooltip');
            if (tooltip) {
                tooltip.remove();
            }
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

        resolveNodeColors() {
            // Helper function to resolve CSS variables
            const resolveCSSVariable = (varName) => {
                const cleanVar = varName.replace(/var\(|\s|\)/g, '');
                const root = document.documentElement;
                const value = getComputedStyle(root).getPropertyValue(cleanVar).trim();
                return value || '#9e9e9e';
            };

            // Resolve CSS variables in node colors
            if (this.data && this.data.nodes) {
                this.data.nodes.forEach(node => {
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
    let minimapInstance = null;

    // Auto-initialize if container exists
    function initMinimap() {
        const minimapContainer = document.querySelector('.graph-minimap');
        if (minimapContainer && typeof d3 !== 'undefined') {
            minimapInstance = new GraphMinimap(minimapContainer);
        }
    }

    // Cleanup function for memory leak prevention
    function cleanup() {
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

    // Cleanup on page unload to prevent memory leaks
    window.addEventListener('beforeunload', cleanup);

    // Export for manual initialization and cleanup
    if (typeof window !== 'undefined') {
        window.GraphMinimap = GraphMinimap;
        window.BengalGraphMinimap = {
            cleanup: cleanup
        };
    }
})();
