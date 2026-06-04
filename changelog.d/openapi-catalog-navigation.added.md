REST autodoc catalog pages gained first-class navigation interactions (#287),
shipped as one lazy-loaded vanilla-JS enhancement (`api-catalog`, no npm). The
API landing catalog and the schema index now have client-side filtering: typing
in the filter box narrows endpoint cards and schema tiles by method/path/name,
collapses empty tag groups, and announces a no-results state via `aria-live`.
The left rail on the landing catalog and on the resource/schema/endpoint shells
is now a scroll-spy: it marks the active section (`aria-current` +
`.api-rail__link--active`) as you scroll and on direct hash navigation, honoring
`prefers-reduced-motion` (the smooth-scroll gap `toc.js` leaves open).
Operation paths gained copy buttons that ride the existing global `[data-copy]`
handler, so base URLs, operation paths, and code samples now copy consistently,
with a screen-reader announcement on copy. Filtering only toggles the `hidden`
attribute and never reorders or removes anchored nodes, so deep links and the
back button keep working; a hash navigation to a filtered-out section clears the
filter to reveal it. Everything degrades gracefully with JavaScript disabled —
rail links are real anchors and the filter input is simply inert. Covered by
template/CSS contract tests, an end-to-end build that asserts the hooks render
in output across the landing, tag, endpoint, and schema-index pages, and a
fingerprinted-asset check.
