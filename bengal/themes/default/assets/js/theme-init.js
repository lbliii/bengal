(function () {
    try {
        // Get config defaults from bengal.toml (if set)
        const defaults = window.BENGAL_THEME_DEFAULTS || { appearance: 'system', palette: '' };

        // Resolve default appearance ('system' → actual light/dark)
        let defaultAppearance = defaults.appearance;
        if (defaultAppearance === 'system') {
            defaultAppearance = (window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches)
                ? 'dark'
                : 'light';
        }

        // Get stored preferences or fall back to config defaults
        const storedTheme = localStorage.getItem('bengal-theme');
        const storedPalette = localStorage.getItem('bengal-palette');

        // Resolve final theme
        let theme;
        if (storedTheme) {
            // Respect user's stored preference
            theme = storedTheme === 'system' ? defaultAppearance : storedTheme;
        } else {
            // Use config default
            theme = defaultAppearance;
        }

        // Resolve final palette (stored preference OR config default)
        const palette = storedPalette !== null ? storedPalette : defaults.palette;

        // Apply to document
        document.documentElement.setAttribute('data-theme', theme);
        if (palette) {
            document.documentElement.setAttribute('data-palette', palette);
        }
    } catch (e) {
        // Fallback to light mode on error
        document.documentElement.setAttribute('data-theme', 'light');
    }
})();
