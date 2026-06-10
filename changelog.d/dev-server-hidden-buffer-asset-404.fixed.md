Fixed a dev-server (`bengal serve`) bug where the theme would repeatedly "drop" to unstyled
HTML for long stretches while editing — every CSS/JS/font/icon request returning `404` even
though the files were present on disk. The double-buffer stages builds in `<root>/.bengal/staging`
and serves from whichever buffer is active after a swap; Pounce's static handler rejects any path
whose resolved absolute path contains a hidden (dot-prefixed) component, so whenever the
`.bengal/staging` buffer was the active one (≈half the time under rapid edits) it 404'd *every*
asset — while HTML kept loading (it is served by Bengal's own `_serve_static`, which has no such
restriction), producing the characteristic fully-rendered-but-unstyled page. Bengal now detects a
hidden serving directory and routes asset requests around Pounce to `_serve_static` (correct
content types, no HTML injection for non-HTML), so assets serve regardless of which buffer is
active. A live reproduction went from 53% of CSS requests 404ing to 0%. Also covers the rarer
case of a project rooted under a dot-directory. Tracked upstream as
[lbliii/pounce#74](https://github.com/lbliii/pounce/issues/74).
