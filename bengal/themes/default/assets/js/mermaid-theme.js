/**
 * Bengal SSG Default Theme
 * Mermaid Theme Configuration
 *
 * Maps Bengal CSS variables to Mermaid themeVariables to ensure diagrams
 * match Bengal's color palettes and adapt to light/dark mode.
 */

(function () {
    'use strict';

    // Ensure utils are available
    if (!window.BengalUtils) {
        console.error('BengalUtils not loaded - mermaid-theme.js requires utils.js');
        return;
    }

    const { log, ready } = window.BengalUtils;

    /**
     * Get CSS variable value with fallback
     * @param {string} variable - CSS variable name (e.g., '--color-primary')
     * @param {string} fallback - Fallback value if variable is not set
     * @param {CSSStyleDeclaration} [cachedStyles] - Optional cached getComputedStyle result
     */
    function getCSSVariable(variable, fallback = '#000000', cachedStyles = null) {
        const styles = cachedStyles || getComputedStyle(document.documentElement);
        const value = styles.getPropertyValue(variable).trim();
        return value || fallback;
    }

    /**
     * Check if dark mode is active
     */
    function isDarkMode() {
        const htmlEl = document.documentElement;
        const themeAttr = htmlEl.getAttribute('data-theme');
        if (themeAttr === 'dark') return true;
        if (htmlEl.classList.contains('dark')) return true;
        if (window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches) {
            return true;
        }
        return false;
    }

    /**
     * Map Bengal CSS variables to Mermaid themeVariables
     * This ensures diagrams match Bengal's color palettes
     */
    function getMermaidThemeConfig() {
        const darkMode = isDarkMode();

        // Cache getComputedStyle once for all variable reads (prevents CSSStyleDeclaration object churn)
        // This reduces ~50+ getComputedStyle calls to just 1
        const cachedStyles = getComputedStyle(document.documentElement);

        // Read Bengal CSS variables using cached styles
        const primaryColorRaw = getCSSVariable('--color-primary', '#4FA8A0', cachedStyles);
        const primaryHover = getCSSVariable('--color-primary-hover', '#3D9287', cachedStyles);
        const primaryDark = getCSSVariable('--color-primary-dark', '#236962', cachedStyles);
        const primaryTextColor = getCSSVariable('--color-text-inverse', '#FFFFFF', cachedStyles);
        const textColor = getCSSVariable('--color-text-primary', '#252525', cachedStyles);
        const secondaryTextColor = getCSSVariable('--color-text-secondary', '#5F5B56', cachedStyles);
        const bgPrimary = getCSSVariable('--color-bg-primary', '#FDFCF9', cachedStyles);
        const bgSecondary = getCSSVariable('--color-bg-secondary', '#F9F6F0', cachedStyles);
        const bgTertiary = getCSSVariable('--color-bg-tertiary', '#F2EDE3', cachedStyles);
        const borderColor = getCSSVariable('--color-border', '#E5DFD6', cachedStyles);
        const borderStrong = getCSSVariable('--color-border-strong', '#CFC7BC', cachedStyles);
        const accentColorRaw = getCSSVariable('--color-accent', '#5BB8AF', cachedStyles);
        const accentHover = getCSSVariable('--color-accent-hover', '#4FA8A0', cachedStyles);

        // Semantic colors - use darker variants in light mode for better contrast
        const successColorRaw = getCSSVariable('--color-success', '#2E7D5A', cachedStyles);
        const successDark = getCSSVariable('--color-success-text', '#1B5E42', cachedStyles); // Darker variant
        const warningColorRaw = getCSSVariable('--color-warning', '#D97706', cachedStyles);
        const warningDark = getCSSVariable('--color-warning-text', '#7C3E03', cachedStyles); // Darker variant
        const errorColorRaw = getCSSVariable('--color-error', '#C62828', cachedStyles);
        const errorDark = getCSSVariable('--color-error-text', '#7F1D1D', cachedStyles); // Darker variant
        const infoColorRaw = getCSSVariable('--color-info', '#3D9DAF', cachedStyles);
        const infoDark = getCSSVariable('--color-info-text', '#1E5C6B', cachedStyles); // Darker variant

        // Use darker, more saturated colors in light mode for better contrast
        // In dark mode, use the lighter variants
        const primaryColor = darkMode ? primaryColorRaw : (primaryHover || primaryDark || primaryColorRaw);
        const accentColor = darkMode ? accentColorRaw : (accentHover || accentColorRaw);
        const successColor = darkMode ? successColorRaw : (successDark || successColorRaw);
        const warningColor = darkMode ? warningColorRaw : (warningDark || warningColorRaw);
        const errorColor = darkMode ? errorColorRaw : (errorDark || errorColorRaw);
        const infoColor = darkMode ? infoColorRaw : (infoDark || infoColorRaw);

        // Semantic text colors (designed for text on colored backgrounds)
        // These automatically adapt to light/dark mode and palettes via CSS variables
        const successTextColor = getCSSVariable('--color-success-text', '#000000', cachedStyles);
        const warningTextColor = getCSSVariable('--color-warning-text', '#000000', cachedStyles);
        const errorTextColor = getCSSVariable('--color-error-text', '#000000', cachedStyles);
        const infoTextColor = getCSSVariable('--color-info-text', '#000000', cachedStyles);

        // Text on colored backgrounds - use semantic text colors which handle contrast
        // Note: primaryTextColor in Mermaid is used for ALL node text, not just colored nodes
        // So we use textColor (which adapts to light/dark mode) for regular nodes
        // For nodes with colored backgrounds, we'll use textOnPrimary
        const textOnPrimary = primaryTextColor; // White in light mode, dark in dark mode (for colored nodes)
        const textOnSuccess = successTextColor || textColor;
        const textOnWarning = warningTextColor || textColor;
        const textOnError = errorTextColor || textColor;

        // Map to Mermaid themeVariables
        // Using 'base' theme as foundation, then customizing with Bengal colors
        return {
            theme: 'base', // base is the only theme that can be customized (per Mermaid docs)
            themeVariables: {
                // Core theme setting - affects how Mermaid calculates derived colors
                darkMode: darkMode,

                // Primary colors
                // Note: primaryTextColor is used for ALL node text in Mermaid, not just colored nodes
                // So we use textColor (dark in light mode, light in dark mode) for regular nodes
                primaryColor: primaryColor,
                primaryTextColor: textColor, // Use textColor for regular nodes (adapts to mode/palette)
                primaryBorderColor: borderStrong,

                // Secondary colors
                secondaryColor: accentColor,
                secondaryTextColor: textColor,
                secondaryBorderColor: borderColor,

                // Tertiary colors
                tertiaryColor: accentColor,
                tertiaryTextColor: secondaryTextColor,
                tertiaryBorderColor: borderColor,

                // Backgrounds - use slightly darker in light mode for better contrast
                background: bgPrimary,
                mainBkg: darkMode ? bgSecondary : bgTertiary,
                secondBkg: darkMode ? bgTertiary : borderColor,
                tertiaryBkg: darkMode ? bgTertiary : borderColor,

                // Text colors - use CSS variables which adapt to mode and palette
                textColor: textColor,

                // Line and border colors
                lineColor: borderStrong,
                secondaryBorderColor: borderColor,
                tertiaryBorderColor: borderColor,
                border1: borderColor,
                border2: borderStrong,

                // Edge/arrow colors
                edgeLabelBackground: bgPrimary,
                clusterBkg: bgSecondary,
                clusterBorder: borderColor,

                // Note/annotation colors
                noteBkgColor: bgSecondary,
                noteTextColor: textColor,
                noteBorderColor: borderColor,

                // Actor colors (sequence diagrams)
                actorBkg: bgSecondary,
                actorBorder: borderStrong,
                actorTextColor: textColor,
                actorLineColor: borderStrong,

                // Activation colors
                activationBkgColor: primaryColor,
                activationBorderColor: primaryHover,
                activationTextColor: textOnPrimary,

                // Sequence number colors
                sequenceNumberColor: textOnPrimary,

                // Section colors
                sectionBkgColor: bgTertiary,
                sectionBkgColor2: bgSecondary,
                altSectionBkgColor: bgSecondary,
                excludeBkgColor: bgTertiary,

                // Task colors (gantt charts)
                taskBkgColor: primaryColor,
                taskTextColor: textOnPrimary,
                taskTextLightColor: secondaryTextColor,
                taskTextOutsideColor: textColor,
                taskTextClickableColor: primaryColor,
                activeTaskBkgColor: primaryHover,
                activeTaskBorderColor: borderStrong,
                gridColor: borderColor,
                doneTaskBkgColor: successColor,
                doneTaskBorderColor: borderStrong,
                doneTaskTextColor: textOnSuccess,
                critBorderColor: errorColor,
                critBkgColor: errorColor,
                critTaskTextColor: textOnError,
                todayLineColor: warningColor,

                // State colors
                labelColor: textColor,
                errorBkgColor: errorColor,
                errorTextColor: textOnError,

                // C4 diagram colors
                c4LabelColor: textColor,
                c4LabelBackground: bgPrimary,
                c4LabelBorder: borderColor,

                // Pie chart colors
                pie1: primaryColor,
                pie2: accentColor,
                pie3: successColor,
                pie4: infoColor,
                pie5: warningColor,
                pie6: errorColor,
                pie7: primaryHover,
                pieTitleTextSize: '25px',
                pieTitleTextColor: textColor,
                pieSectionTextSize: '17px',
                pieSectionTextColor: textOnPrimary,
                pieLegendTextSize: '17px',
                pieLegendTextColor: textColor,
                pieStrokeColor: borderStrong,
                pieStrokeWidth: '2px',

                // Requirement diagram colors
                requirementBackground: bgSecondary,
                requirementBorderColor: borderStrong,
                requirementTextColor: textColor,
                relationColor: borderStrong,
                relationLabelBackground: bgPrimary,
                relationLabelColor: textColor,

                // Git graph colors
                commitLabelColor: textOnPrimary,
                commitLabelBackground: primaryColor,
                commitLabelFontSize: '10px',
                branchLabelColor: textColor,
                branchLabelFontSize: '11px',
                tagLabelColor: textOnPrimary,
                tagLabelBackground: accentColor,
                tagLabelFontSize: '10px',
                tagLabelBorder: borderStrong,
                commit0: primaryColor,
                commit1: accentColor,
                commit2: successColor,
                commit3: infoColor,
                commit4: warningColor,
                commit5: errorColor,
                commit6: primaryHover,
                commit7: accentColor,

                // ER diagram colors
                entityBkg: bgSecondary,
                entityBorder: borderStrong,
                attributeBkgOdd: bgPrimary,
                attributeBkgEven: bgSecondary,
                attributeTextColor: textColor,

                // Journey diagram colors
                cScale0: primaryColor,
                cScale1: accentColor,
                cScale2: successColor,

                // User journey colors
                fillType0: primaryColor,
                fillType1: accentColor,
                fillType2: successColor,
                fillType3: infoColor,

                // Quadrant chart colors
                quadrant1Fill: primaryColor,
                quadrant2Fill: accentColor,
                quadrant3Fill: successColor,
                quadrant4Fill: infoColor,
                quadrantPointFill: textColor,
                quadrantPointTextColor: textOnPrimary,
                quadrantXAxisTextColor: textColor,
                quadrantYAxisTextColor: textColor
            }
        };
    }

    /**
     * Store original syntax for all Mermaid diagrams
     * Must be called BEFORE Mermaid renders
     */
    function preserveMermaidSyntax() {
        const mermaidElements = document.querySelectorAll('.mermaid');
        mermaidElements.forEach(function (element) {
            // Only store if not already stored
            if (!element.hasAttribute('data-mermaid-syntax')) {
                // Get text content and decode HTML entities
                const textContent = element.textContent.trim();
                if (textContent) {
                    const decoded = decodeHtmlEntities(textContent);
                    element.setAttribute('data-mermaid-syntax', decoded.trim());
                }
            }
        });
    }

    /**
     * Register common icon packs for Mermaid diagrams
     * Uses lazy loading - icons only load when used in diagrams
     * See: https://docs.mermaidchart.com/mermaid-oss/config/icons.html
     */
    function registerIconPacks() {
        // Only register if mermaid.registerIconPacks exists (v10+)
        if (typeof mermaid !== 'undefined' && mermaid.registerIconPacks) {
            // Register popular icon packs with lazy loading
            // Users can use icons like: fa:fa-ban, mdi:github, logos:python
            mermaid.registerIconPacks([
                {
                    name: 'fa',
                    loader: () =>
                        fetch('https://unpkg.com/@iconify-json/fa@1/icons.json')
                            .then((res) => res.json())
                            .catch(() => null) // Fail silently if CDN unavailable
                },
                {
                    name: 'mdi',
                    loader: () =>
                        fetch('https://unpkg.com/@iconify-json/mdi@1/icons.json')
                            .then((res) => res.json())
                            .catch(() => null)
                },
                {
                    name: 'logos',
                    loader: () =>
                        fetch('https://unpkg.com/@iconify-json/logos@1/icons.json')
                            .then((res) => res.json())
                            .catch(() => null)
                }
            ]);
        }
    }

    /**
     * Initialize Mermaid with Bengal theme configuration
     */
    function initializeMermaid() {
        // Only initialize if Mermaid diagrams are present on the page
        const mermaidElements = document.querySelectorAll('.mermaid');
        if (mermaidElements.length === 0 || typeof mermaid === 'undefined') {
            return;
        }

        // Register icon packs first (optional, lazy-loaded)
        registerIconPacks();

        // Preserve syntax BEFORE Mermaid renders (store original text)
        preserveMermaidSyntax();

        // Also use toolbar's preserveSyntax if available (for consistency)
        if (window.BengalMermaidToolbar && window.BengalMermaidToolbar.preserveSyntax) {
            window.BengalMermaidToolbar.preserveSyntax();
        }

        // Get Bengal theme configuration
        const mermaidConfig = getMermaidThemeConfig();

        // Initialize Mermaid with Bengal theme matching
        // Using 'base' theme as it's the only customizable theme (per Mermaid docs)
        mermaid.initialize({
            startOnLoad: false,
            theme: mermaidConfig.theme,
            themeVariables: mermaidConfig.themeVariables,
            securityLevel: 'loose',
            flowchart: {
                useMaxWidth: true,
                htmlLabels: true
            }
        });

        // Initial render
        mermaid.run().then(() => {
            if (window.BengalMermaidToolbar) {
                window.BengalMermaidToolbar.setupToolbars();
            }
        });
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
     * Restore original Mermaid syntax from stored data attributes
     * This is needed because Mermaid replaces the text content with SVG when rendering
     */
    function restoreMermaidSyntax() {
        const mermaidElements = document.querySelectorAll('.mermaid');
        mermaidElements.forEach(function (element) {
            // Get stored syntax
            let storedSyntax = element.getAttribute('data-mermaid-syntax');

            // If not stored, try to get from textContent (before first render)
            if (!storedSyntax) {
                const textContent = element.textContent.trim();
                if (textContent && !element.querySelector('svg')) {
                    // Element hasn't been rendered yet, decode and store it
                    storedSyntax = decodeHtmlEntities(textContent);
                    element.setAttribute('data-mermaid-syntax', storedSyntax);
                }
            }

            if (storedSyntax) {
                // Clear any rendered SVG content completely
                element.innerHTML = '';

                // Remove any Mermaid data attributes that might prevent re-rendering
                // Mermaid may add data attributes when processing
                Array.from(element.attributes).forEach(function (attr) {
                    if (attr.name.startsWith('data-') && attr.name !== 'data-mermaid-syntax') {
                        element.removeAttribute(attr.name);
                    }
                });

                // Restore the original text content - Mermaid reads from textContent
                // The stored syntax is already decoded, so we can set it directly
                element.textContent = storedSyntax;

                // Ensure the mermaid class is still present (required for mermaid.run())
                if (!element.classList.contains('mermaid')) {
                    element.classList.add('mermaid');
                }
            }
        });
    }

    /**
     * Re-render Mermaid diagrams when theme or palette changes
     * v2: Use event listeners instead of MutationObserver to avoid DevTools issues
     */
    function setupThemeObserver() {
        let reRenderTimeout = null;

        function handleThemeChange() {
            // Check if there are any Mermaid diagrams on the page
            const mermaidElements = document.querySelectorAll('.mermaid');
            if (mermaidElements.length === 0 || typeof mermaid === 'undefined') {
                return;
            }

            // Debounce re-rendering to avoid multiple rapid updates
            // Also gives CSS time to update before we read variables
            if (reRenderTimeout) {
                clearTimeout(reRenderTimeout);
            }

            reRenderTimeout = setTimeout(function () {
                // Restore original syntax before re-rendering
                restoreMermaidSyntax();

                // Get updated theme config with new CSS variables
                const updatedConfig = getMermaidThemeConfig();

                // Re-initialize with updated Bengal theme
                mermaid.initialize({
                    startOnLoad: false,
                    theme: updatedConfig.theme,
                    themeVariables: updatedConfig.themeVariables,
                    securityLevel: 'loose',
                    flowchart: {
                        useMaxWidth: true,
                        htmlLabels: true
                    }
                });

                // Re-render all Mermaid diagrams using mermaid.run() with explicit nodes
                // According to Mermaid docs, this is the preferred way (v10+)
                const elementsToRender = document.querySelectorAll('.mermaid');
                if (elementsToRender.length > 0) {
                    mermaid.run({
                        nodes: Array.from(elementsToRender),
                        suppressErrors: false
                    }).then(() => {
                        if (window.BengalMermaidToolbar) {
                            window.BengalMermaidToolbar.setupToolbars();
                        }
                    }).catch(function (error) {
                        log('Mermaid re-render error:', error);
                        // Fallback: try with querySelector
                        mermaid.run({
                            querySelector: '.mermaid',
                            suppressErrors: true
                        }).then(() => {
                            if (window.BengalMermaidToolbar) {
                                window.BengalMermaidToolbar.setupToolbars();
                            }
                        });
                    });
                }
            }, 50); // Small delay to ensure CSS variables are updated
        }

        // v2: Use event listeners instead of MutationObserver
        // The theme.js dispatches 'themechange' and 'palettechange' events
        window.addEventListener('themechange', handleThemeChange);
        window.addEventListener('palettechange', handleThemeChange);

        // Note: Removed MutationObserver - it was causing DevTools performance issues
        // The theme system dispatches events which is sufficient for detecting changes
    }

    /**
     * Initialize Mermaid when DOM is ready
     */
    function init() {
        ready(function () {
            initializeMermaid();
            setupThemeObserver();
            log('Mermaid theme initialized');
        });
    }

    // Initialize when DOM is ready
    init();

    // Export API
    window.BengalMermaidTheme = {
        getMermaidThemeConfig: getMermaidThemeConfig,
        initializeMermaid: initializeMermaid,
        setupThemeObserver: setupThemeObserver
    };

})();
