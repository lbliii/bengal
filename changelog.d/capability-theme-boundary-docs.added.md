Added a theming guide, `site/content/docs/theming/capabilities-vs-theme.md`
("What Bengal Provides vs What Your Theme Provides"), documenting the
capability-vs-presentation boundary for theme authors. It diagrams the template
resolution / fallback chain (site `templates/` -> theme chain via `extends`,
child to parent -> the bundled `default` theme, always appended as the final
filesystem fallback -> library provider loaders; first match wins, else
`TemplateNotFoundError`) and explains the directive-vs-shortcode asymmetry:
directives are a fixed, core-registered set that always render through a Python
`render()` fallback even with zero theme templates (extensible only via plugins,
not themes), whereas shortcodes are an open set with no engine fallback — a
missing `shortcodes/{name}.html` passes the raw shortcode through (or errors in
strict mode), making the default theme's shortcode templates the de-facto
standard library. The page cross-links issues #335/#337/#338 as the path to
portable capability templates. Also corrected `theme-creation.md`, which claimed
the engine "automatically includes base CSS for all directives": that base CSS
actually lives in the default theme at
`bengal/themes/default/assets/css/components/`, so it is inherited only when a
theme extends `default` (or is layered over it) — a non-extending theme must
supply its own directive CSS.
