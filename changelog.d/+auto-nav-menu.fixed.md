Sites without a manual main menu render the home page again instead of failing during navigation template rendering.

Theme navigation now uses the orchestrated main menu from `get_menu_lang('main')` rather than a separate `get_auto_nav()` template fallback, restoring `index.html` on auto-discovered sites including the Bengal docs site on GitHub Pages.
