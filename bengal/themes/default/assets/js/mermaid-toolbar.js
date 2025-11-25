/**
 * Bengal SSG Default Theme
 * Mermaid Diagram Toolbar
 *
 * Adds interactive controls to Mermaid diagrams:
 * - Enlarge (lightbox/modal view) with Pan/Zoom
 * - Copy diagram syntax to clipboard
 * - Download as SVG
 * - Download as PNG
 */

(function () {
    'use strict';

    // Ensure utils are available
    if (!window.BengalUtils) {
        console.error('BengalUtils not loaded - mermaid-toolbar.js requires utils.js');
        return;
    }

    const { log, copyToClipboard, ready } = window.BengalUtils;

    let lightbox = null;
    let currentDiagram = null;
    let panZoomState = {
        scale: 1,
        panning: false,
        pointX: 0,
        pointY: 0,
        startX: 0,
        startY: 0
    };

    // Icons
    const ICONS = {
        close: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="18" y1="6" x2="6" y2="18"></line><line x1="6" y1="6" x2="18" y2="18"></line></svg>`,
        enlarge: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M15 3h6v6M9 21H3v-6M21 3l-7 7M3 21l7-7"></path></svg>`,
        copy: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path></svg>`,
        downloadSvg: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path><polyline points="7 10 12 15 17 10"></polyline><line x1="12" y1="15" x2="12" y2="3"></line></svg>`,
        downloadPng: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="3" width="18" height="18" rx="2" ry="2"></rect><circle cx="8.5" cy="8.5" r="1.5"></circle><polyline points="21 15 16 10 5 21"></polyline></svg>`,
        zoomIn: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="11" cy="11" r="8"></circle><line x1="21" y1="21" x2="16.65" y2="16.65"></line><line x1="11" y1="8" x2="11" y2="14"></line><line x1="8" y1="11" x2="14" y2="11"></line></svg>`,
        zoomOut: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="11" cy="11" r="8"></circle><line x1="21" y1="21" x2="16.65" y2="16.65"></line><line x1="8" y1="11" x2="14" y2="11"></line></svg>`,
        reset: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M3 12a9 9 0 1 0 9-9 9.75 9.75 0 0 0-6.74 2.74L3 8"></path><path d="M3 3v5h5"></path></svg>`
    };

    /**
     * Create lightbox element for enlarged diagrams
     */
    function createLightbox() {
        if (lightbox) return lightbox;

        lightbox = document.createElement('div');
        lightbox.className = 'mermaid-lightbox';
        lightbox.setAttribute('role', 'dialog');
        lightbox.setAttribute('aria-label', 'Enlarged diagram');
        lightbox.setAttribute('aria-hidden', 'true');

        // Create container for diagram
        const container = document.createElement('div');
        container.className = 'mermaid-lightbox__container';

        // Create close button
        const closeButton = document.createElement('button');
        closeButton.className = 'mermaid-lightbox__close';
        closeButton.setAttribute('aria-label', 'Close lightbox');
        closeButton.innerHTML = ICONS.close;

        // Create toolbar for lightbox
        const toolbar = document.createElement('div');
        toolbar.className = 'mermaid-lightbox__toolbar';

        // Create controls for pan/zoom
        const controls = document.createElement('div');
        controls.className = 'mermaid-lightbox__controls';
        
        const zoomInBtn = createButton('zoom-in', 'Zoom In', ICONS.zoomIn);
        const zoomOutBtn = createButton('zoom-out', 'Zoom Out', ICONS.zoomOut);
        const resetBtn = createButton('reset', 'Reset View', ICONS.reset);

        zoomInBtn.addEventListener('click', () => zoom(0.2));
        zoomOutBtn.addEventListener('click', () => zoom(-0.2));
        resetBtn.addEventListener('click', resetPanZoom);

        controls.appendChild(zoomInBtn);
        controls.appendChild(resetBtn);
        controls.appendChild(zoomOutBtn);

        // Assemble lightbox
        lightbox.appendChild(container);
        lightbox.appendChild(toolbar);
        lightbox.appendChild(controls); // Add separate controls container
        lightbox.appendChild(closeButton);

        // Add to document
        document.body.appendChild(lightbox);

        // Event listeners
        closeButton.addEventListener('click', closeLightbox);
        lightbox.addEventListener('click', function (e) {
            // Close when clicking backdrop (not the container or controls)
            if (e.target === lightbox) {
                closeLightbox();
            }
        });

        // Keyboard controls
        document.addEventListener('keydown', handleKeyboard);
        
        // Pan/Zoom Events
        container.addEventListener('mousedown', startPan);
        container.addEventListener('mousemove', pan);
        container.addEventListener('mouseup', endPan);
        container.addEventListener('mouseleave', endPan);
        container.addEventListener('wheel', handleWheel, { passive: false });
        
        // Touch support
        container.addEventListener('touchstart', handleTouchStart, { passive: false });
        container.addEventListener('touchmove', handleTouchMove, { passive: false });
        container.addEventListener('touchend', endPan);

        return lightbox;
    }

    // Pan/Zoom Logic
    function setTransform() {
        const container = lightbox.querySelector('.mermaid-lightbox__container svg');
        if (container) {
            container.style.transform = `translate(${panZoomState.pointX}px, ${panZoomState.pointY}px) scale(${panZoomState.scale})`;
        }
    }

    function zoom(delta) {
        const newScale = panZoomState.scale + delta;
        if (newScale > 0.1 && newScale < 10) {
            panZoomState.scale = newScale;
            setTransform();
        }
    }

    function resetPanZoom() {
        panZoomState = {
            scale: 1,
            panning: false,
            pointX: 0,
            pointY: 0,
            startX: 0,
            startY: 0
        };
        setTransform();
    }

    function startPan(e) {
        if (e.target.closest('.mermaid-lightbox__controls') || e.target.closest('.mermaid-lightbox__toolbar')) return;
        e.preventDefault();
        panZoomState.panning = true;
        panZoomState.startX = e.clientX - panZoomState.pointX;
        panZoomState.startY = e.clientY - panZoomState.pointY;
        lightbox.querySelector('.mermaid-lightbox__container').style.cursor = 'grabbing';
    }

    function pan(e) {
        if (!panZoomState.panning) return;
        e.preventDefault();
        panZoomState.pointX = e.clientX - panZoomState.startX;
        panZoomState.pointY = e.clientY - panZoomState.startY;
        setTransform();
    }

    function endPan() {
        panZoomState.panning = false;
        const container = lightbox.querySelector('.mermaid-lightbox__container');
        if (container) container.style.cursor = 'grab';
    }

    function handleWheel(e) {
        e.preventDefault();
        const delta = e.deltaY > 0 ? -0.1 : 0.1;
        zoom(delta);
    }

    let lastTouchDist = 0;
    
    function handleTouchStart(e) {
        if (e.touches.length === 1) {
            const touch = e.touches[0];
            panZoomState.panning = true;
            panZoomState.startX = touch.clientX - panZoomState.pointX;
            panZoomState.startY = touch.clientY - panZoomState.pointY;
        } else if (e.touches.length === 2) {
            lastTouchDist = Math.hypot(
                e.touches[0].clientX - e.touches[1].clientX,
                e.touches[0].clientY - e.touches[1].clientY
            );
        }
    }

    function handleTouchMove(e) {
        e.preventDefault();
        if (e.touches.length === 1 && panZoomState.panning) {
            const touch = e.touches[0];
            panZoomState.pointX = touch.clientX - panZoomState.startX;
            panZoomState.pointY = touch.clientY - panZoomState.startY;
            setTransform();
        } else if (e.touches.length === 2) {
            const dist = Math.hypot(
                e.touches[0].clientX - e.touches[1].clientX,
                e.touches[0].clientY - e.touches[1].clientY
            );
            const delta = dist - lastTouchDist;
            lastTouchDist = dist;
            zoom(delta * 0.01);
        }
    }

    /**
     * Open lightbox with a diagram
     */
    function openLightbox(diagramElement) {
        if (!lightbox) {
            lightbox = createLightbox();
        }

        currentDiagram = diagramElement;
        const container = lightbox.querySelector('.mermaid-lightbox__container');
        const toolbar = lightbox.querySelector('.mermaid-lightbox__toolbar');

        if (!container || !toolbar) {
            log('Error: Lightbox container or toolbar not found');
            return;
        }

        // Clone the diagram SVG
        const svg = diagramElement.querySelector('svg');
        if (!svg) {
            log('Error: No SVG found in diagram element');
            return;
        }

        const clonedSvg = svg.cloneNode(true);

        // Remove fixed dimensions and rely on transform
        clonedSvg.removeAttribute('width');
        clonedSvg.removeAttribute('height');
        clonedSvg.style.width = '100%';
        clonedSvg.style.height = '100%';
        clonedSvg.style.maxWidth = 'none';
        clonedSvg.style.maxHeight = 'none';
        
        // Ensure viewbox exists
        if (!clonedSvg.hasAttribute('viewBox')) {
             const w = parseInt(svg.getAttribute('width')) || 800;
             const h = parseInt(svg.getAttribute('height')) || 600;
             clonedSvg.setAttribute('viewBox', `0 0 ${w} ${h}`);
        }

        // Clear container
        container.innerHTML = '';
        container.appendChild(clonedSvg);

        // Add standard toolbar buttons (Copy, Download)
        toolbar.innerHTML = '';
        const buttonsContainer = createToolbarButtons(diagramElement, true);
        if (buttonsContainer && buttonsContainer.children.length > 0) {
            while (buttonsContainer.firstChild) {
                toolbar.appendChild(buttonsContainer.firstChild);
            }
        }

        // Show lightbox
        lightbox.classList.add('active');
        lightbox.setAttribute('aria-hidden', 'false');
        document.body.style.overflow = 'hidden';
        
        // Reset pan/zoom state
        resetPanZoom();
        
        // Set initial cursor
        container.style.cursor = 'grab';
        
        lightbox.focus();
    }

    /**
     * Close lightbox
     */
    function closeLightbox() {
        if (!lightbox) return;

        lightbox.classList.remove('active');
        lightbox.setAttribute('aria-hidden', 'true');
        document.body.style.overflow = '';

        if (currentDiagram) {
            currentDiagram.focus();
        }
        currentDiagram = null;
    }

    /**
     * Handle keyboard controls
     */
    function handleKeyboard(e) {
        if (!lightbox || !lightbox.classList.contains('active')) return;

        if (e.key === 'Escape') {
            closeLightbox();
        }
    }

    /**
     * Decode HTML entities
     */
    function decodeHtmlEntities(text) {
        const textarea = document.createElement('textarea');
        textarea.innerHTML = text;
        return textarea.value;
    }

    /**
     * Get Mermaid diagram syntax from element
     */
    function getDiagramSyntax(element) {
        const storedSyntax = element.getAttribute('data-mermaid-syntax');
        if (storedSyntax) {
            return storedSyntax;
        }
        const textContent = element.textContent.trim();
        return decodeHtmlEntities(textContent);
    }

    /**
     * Store original syntax before Mermaid renders
     */
    function storeOriginalSyntax(element) {
        if (!element.hasAttribute('data-mermaid-syntax')) {
            const textContent = element.textContent.trim();
            const decoded = decodeHtmlEntities(textContent);
            element.setAttribute('data-mermaid-syntax', decoded.trim());
        }
    }

    /**
     * Copy diagram syntax to clipboard
     */
    async function copySyntax(diagramElement, button) {
        const syntax = getDiagramSyntax(diagramElement);
        try {
            await copyToClipboard(syntax);
            showSuccessFeedback(button, 'Copied!');
        } catch (err) {
            log('Failed to copy syntax:', err);
            showErrorFeedback(button, 'Failed to copy');
        }
    }

    /**
     * Download diagram as SVG
     */
    function downloadSVG(diagramElement, button) {
        const svg = diagramElement.querySelector('svg');
        if (!svg) {
            showErrorFeedback(button, 'No SVG found');
            return;
        }

        const clonedSvg = svg.cloneNode(true);
        const width = clonedSvg.viewBox?.baseVal?.width || clonedSvg.getAttribute('width') || 800;
        const height = clonedSvg.viewBox?.baseVal?.height || clonedSvg.getAttribute('height') || 600;
        
        clonedSvg.setAttribute('width', width);
        clonedSvg.setAttribute('height', height);
        clonedSvg.setAttribute('xmlns', 'http://www.w3.org/2000/svg');

        const serializer = new XMLSerializer();
        const svgString = serializer.serializeToString(clonedSvg);
        const blob = new Blob([svgString], { type: 'image/svg+xml;charset=utf-8' });
        const url = URL.createObjectURL(blob);

        const link = document.createElement('a');
        link.href = url;
        link.download = `diagram-${Date.now()}.svg`;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);

        setTimeout(() => URL.revokeObjectURL(url), 100);
        showSuccessFeedback(button, 'Downloaded!');
    }

    /**
     * Download diagram as PNG
     */
    function downloadPNG(diagramElement, button) {
        const svg = diagramElement.querySelector('svg');
        if (!svg) {
            showErrorFeedback(button, 'No SVG found');
            return;
        }

        const clonedSvg = svg.cloneNode(true);
        let width, height;
        
        if (clonedSvg.viewBox && clonedSvg.viewBox.baseVal) {
            width = clonedSvg.viewBox.baseVal.width;
            height = clonedSvg.viewBox.baseVal.height;
        } else {
            width = parseInt(clonedSvg.getAttribute('width')) || 800;
            height = parseInt(clonedSvg.getAttribute('height')) || 600;
        }

        // Scale up for better quality
        const scale = 2; 
        const scaledWidth = width * scale;
        const scaledHeight = height * scale;

        clonedSvg.setAttribute('width', scaledWidth);
        clonedSvg.setAttribute('height', scaledHeight);
        clonedSvg.setAttribute('xmlns', 'http://www.w3.org/2000/svg');

        const serializer = new XMLSerializer();
        const svgString = serializer.serializeToString(clonedSvg);
        const svgDataUrl = 'data:image/svg+xml;charset=utf-8,' + encodeURIComponent(svgString);

        const canvas = document.createElement('canvas');
        canvas.width = scaledWidth;
        canvas.height = scaledHeight;
        const ctx = canvas.getContext('2d');
        ctx.fillStyle = '#ffffff';
        ctx.fillRect(0, 0, scaledWidth, scaledHeight);

        const img = new Image();
        img.crossOrigin = 'anonymous';
        img.onload = function () {
            try {
                ctx.drawImage(img, 0, 0);
                canvas.toBlob(function (blob) {
                    if (!blob) {
                        showErrorFeedback(button, 'Failed to create PNG');
                        return;
                    }
                    const pngUrl = URL.createObjectURL(blob);
                    const link = document.createElement('a');
                    link.href = pngUrl;
                    link.download = `diagram-${Date.now()}.png`;
                    document.body.appendChild(link);
                    link.click();
                    document.body.removeChild(link);
                    setTimeout(() => URL.revokeObjectURL(pngUrl), 100);
                    showSuccessFeedback(button, 'Downloaded!');
                }, 'image/png');
            } catch (error) {
                log('Error converting to PNG:', error);
                downloadSVG(diagramElement, button);
                showErrorFeedback(button, 'PNG failed, saved as SVG');
            }
        };
        img.onerror = function (error) {
            log('Error loading SVG for PNG:', error);
            downloadSVG(diagramElement, button);
            showErrorFeedback(button, 'PNG failed, saved as SVG');
        };
        img.src = svgDataUrl;
    }

    function createButton(action, label, icon) {
        const button = document.createElement('button');
        button.className = `mermaid-toolbar__button mermaid-toolbar__button--${action}`;
        button.setAttribute('aria-label', label);
        button.setAttribute('title', label);
        button.innerHTML = icon;
        return button;
    }

    function showSuccessFeedback(button, message) {
        const originalTitle = button.getAttribute('title');
        button.setAttribute('title', message);
        button.classList.add('success');
        setTimeout(() => {
            button.setAttribute('title', originalTitle);
            button.classList.remove('success');
        }, 2000);
    }

    function showErrorFeedback(button, message) {
        const originalTitle = button.getAttribute('title');
        button.setAttribute('title', message);
        button.classList.add('error');
        setTimeout(() => {
            button.setAttribute('title', originalTitle);
            button.classList.remove('error');
        }, 2000);
    }

    function createToolbarButtons(diagramElement, isLightbox = false) {
        const toolbar = document.createElement('div');
        toolbar.className = 'mermaid-toolbar';

        if (!isLightbox) {
            const enlargeBtn = createButton('enlarge', 'Enlarge', ICONS.enlarge);
            enlargeBtn.addEventListener('click', (e) => {
                e.stopPropagation();
                openLightbox(diagramElement);
            });
            toolbar.appendChild(enlargeBtn);
        }

        const copyBtn = createButton('copy', 'Copy syntax', ICONS.copy);
        copyBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            copySyntax(diagramElement, copyBtn);
        });
        toolbar.appendChild(copyBtn);

        const svgBtn = createButton('download-svg', 'Download SVG', ICONS.downloadSvg);
        svgBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            downloadSVG(diagramElement, svgBtn);
        });
        toolbar.appendChild(svgBtn);

        const pngBtn = createButton('download-png', 'Download PNG', ICONS.downloadPng);
        pngBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            downloadPNG(diagramElement, pngBtn);
        });
        toolbar.appendChild(pngBtn);

        return toolbar;
    }

    function setupDiagramToolbar(diagramElement) {
        if (diagramElement.querySelector('.mermaid-toolbar')) {
            return;
        }

        // Ensure SVG is present
        if (!diagramElement.querySelector('svg')) {
            return;
        }

        storeOriginalSyntax(diagramElement);

        // Create wrapper if needed
        let wrapper = diagramElement.parentElement;
        if (!wrapper.classList.contains('mermaid-wrapper')) {
            wrapper = document.createElement('div');
            wrapper.className = 'mermaid-wrapper';
            diagramElement.parentElement.insertBefore(wrapper, diagramElement);
            wrapper.appendChild(diagramElement);
        }

        const toolbar = createToolbarButtons(diagramElement, false);
        wrapper.appendChild(toolbar);
    }

    function setupMermaidToolbars() {
        const diagrams = document.querySelectorAll('.mermaid');
        diagrams.forEach(diagram => {
            setupDiagramToolbar(diagram);
        });
    }

    /**
     * Preserve original syntax for all diagrams
     * Must be called BEFORE Mermaid renders
     */
    function preserveSyntax() {
        const diagrams = document.querySelectorAll('.mermaid');
        diagrams.forEach(diagram => {
            storeOriginalSyntax(diagram);
        });
    }

    // Export API
    window.BengalMermaidToolbar = {
        setupToolbars: setupMermaidToolbars,
        openLightbox: openLightbox,
        preserveSyntax: preserveSyntax
    };

})();
