Cleared the dogfood-site health blockers that were obscuring REST autodoc QA
(#288). The `important` admonition (a standard docutils/MyST type) is now
registered, fixing the H201 "Unknown directive" error and the cascading
"PosixPath is not JSON serializable" error it triggered. Six icon names
referenced by docs content (`external`, `languages`, `python`, `robot`,
`stethoscope`, `arrows`) now resolve: `external` was aliased to a non-existent
`arrow-square-out` (in both `ICON_MAP` and `theme.yaml`) despite `external.svg`
existing, and the other five gained aliases to existing theme SVGs. The
`/docs/content/i18n/` URL collision is resolved by renaming the standalone
`i18n.md` to `multilingual.md` so it no longer collides with the canonical
`i18n/` section index. Thirty-one real broken navigation links across the docs
were corrected (the dominant bug was relative `./sibling` / `.md`-suffixed links
that don't resolve under pretty URLs — corrected to the `../sibling/` form), and
the stale `/assets/css/style.css` reference in two self-contained demo HTML files
was removed. Build health quality rose from 60% (Fair) to 80% (Good); broken
internal links dropped from 43 to 9 — the remaining nine are illustrative example
paths inside autodoc'd Python docstrings (e.g. the link-validator module's own
docstring demonstrates `./sibling.md`) and one shortcode-syntax example, not real
navigation, and are left as documented false positives. Added guard tests for the
admonition registry and icon aliases.
