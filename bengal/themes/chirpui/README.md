# Bengal Chirp UI Theme

Experimental bundled theme that renders Bengal sites with Chirp UI 0.7
components.

This theme is separate from `default` and does not inherit its assets. It uses
the Bengal theme-library provider contract in `theme.toml`:

```toml
name = "chirpui"
libraries = ["chirp_ui"]
```

Install `chirp-ui` in the build environment before selecting this theme:

```bash
uv add chirp-ui
```

Then set:

```toml
[site]
theme = "chirpui"
```

The first version is intentionally static and server-rendered. It uses Chirp UI
0.7 macros for the site shell, navbar, drawer-backed mobile docs menu, document
headers, detail headers, profile headers, rendered markdown content, docs side
panels, nav trees, resource indexes, index cards, post cards, timelines, badges,
metrics, and search headers. A small Bengal bridge stylesheet handles the docs
grid, grouped search filtering surface, skip link, and footer spacing. It does
not load the default theme CSS or JavaScript.
