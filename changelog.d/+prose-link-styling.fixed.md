Prose links in the default theme are visible again: they use the theme link color and hover underline instead of inheriting body text styling.

The #540 `@scope` block had `to (...)` nested inside the rule body (invalid CSS that browsers ignore); it now uses the correct prelude form. Palette link tokens no longer wrap already theme-aware primary/accent colors in a second `light-dark()`.
