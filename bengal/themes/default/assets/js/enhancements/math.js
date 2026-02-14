/**
 * KaTeX math rendering for Bengal.
 *
 * Renders LaTeX in .math (inline) and .math-block (display) elements.
 * Requires KaTeX to be loaded before this script.
 */
(function () {
    if (typeof katex === 'undefined') return;
    document.querySelectorAll('.math, .math-block').forEach(function (el) {
        try {
            var displayMode = el.classList.contains('math-block');
            katex.render(el.textContent.trim(), el, {
                throwOnError: false,
                displayMode: displayMode,
            });
        } catch (e) {
            /* leave raw LaTeX on error */
        }
    });
})();
