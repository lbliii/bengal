(function () {
    try {
        const theme = localStorage.getItem('bengal-theme') ||
            (window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light');
        const brand = localStorage.getItem('bengal-brand') || '';
        document.documentElement.setAttribute('data-theme', theme);
        if (brand) {
            document.documentElement.setAttribute('data-brand', brand);
        }
    } catch (e) {
        // No-op
    }
})();
