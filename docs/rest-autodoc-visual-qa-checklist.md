# REST autodoc visual QA smoke checklist

Repeatable manual smoke test for the REST/OpenAPI autodoc pages rendered by the
default theme's bespoke catalog/app shell. This is the **manual half** of the
visual QA story for the autodoc redesign (epic #289, child #284).

The **automated half** lives in the test suite and guards the structural
contract that this checklist's eyes-on pass assumes:

| Concern | Automated guard |
| --- | --- |
| Landing/tag/endpoint/schema-index emit the filter + scroll-spy + copy hooks in *built output* | `tests/integration/test_openapi_catalog_nav.py` |
| Schema detail pages render advanced constructs as structured docs (not raw JSON), and are non-blank styled shells | `tests/integration/test_openapi_advanced_schema.py` |
| The `api-catalog` vanilla-JS enhancement is discovered + fingerprinted (no npm) | `tests/integration/test_openapi_catalog_nav.py::test_api_catalog_module_is_fingerprinted` |
| Autodoc reference pages are app-like UIs and are **not** clamped to `--prose-width`; `base.html` emits no `data-variant="None"` | `tests/unit/rendering/test_autodoc_layout_contract.py` |
| The `:focus-visible` rules for catalog/nav/tile targets survive CSS optimization | `tests/unit/orchestration/test_css_optimizer.py` |

Run the automated half first; if it is red, fix that before doing the manual
pass — a structural regression will make the manual pass misleading.

```bash
uv run pytest \
  tests/integration/test_openapi_catalog_nav.py \
  tests/integration/test_openapi_advanced_schema.py \
  tests/unit/rendering/test_autodoc_layout_contract.py \
  tests/unit/orchestration/test_css_optimizer.py \
  -q
```

> **Why manual, not screenshots?** An in-tree headless-browser/screenshot
> regression harness is **intentionally deferred to 0.5.x**. Bengal ships no
> browser automation dependency today, and the catalog-nav work (#287 / PR #325)
> already fell back to a documented manual smoke checklist for exactly this
> reason. The structural contracts above catch the regressions a screenshot diff
> would catch *for free* (missing shells, dropped hooks, prose clamping, focus
> rules); the human pass below covers the genuinely visual concerns (readability,
> reflow, focus-ring visibility) that no assertion can stand in for.

---

## How to build the pages under test

The dogfood site ships an OpenAPI spec (`site/api/openapi.yaml`,
"Bengal Demo Commerce API", tags `users` / `orders` / `payments` /
`inventory`). Build and serve it:

```bash
uv run bengal build --source site
uv run bengal serve --source site      # then open http://localhost:5173/api/
```

The dogfood spec exercises dense endpoint groups, request bodies, response
examples, and code samples. For the *advanced schema* constructs (oneOf /
anyOf / allOf, discriminators, nullable / readOnly / writeOnly / deprecated
flags, numeric / string / array constraints, additionalProperties,
self-referential schemas), build the dedicated test root, which is the same
fixture the automated schema tests assert against:

```bash
uv run bengal build --source tests/roots/test-openapi-advanced
```

### Pages under test (the five shells)

| # | Shell | Dogfood URL | Template |
| --- | --- | --- | --- |
| P1 | Landing catalog | `/api/` | `autodoc/openapi/home.html` |
| P2 | Tag / resource page | `/api/tags/<Tag>/` (e.g. `users`) | `autodoc/openapi/list.html` |
| P3 | Endpoint page | `/api/tags/<Tag>/<operationId>/` | `autodoc/openapi/endpoint.html` |
| P4 | Schema index | `/api/schemas/` | `autodoc/openapi/section-index.html` |
| P5 | Schema detail | `/api/schemas/<Name>/` | `autodoc/openapi/schema.html` |

### Theme modes

- **Light** mode (default).
- **Dark** mode (toggle via the theme switcher in the site header, or set the OS
  to dark and reload).

### Viewports

Use the browser devtools responsive mode. The autodoc shell's breakpoints are
at `max-width: 1200px`, `900px`, `640px`/`480px` (see
`bengal/themes/default/assets/css/components/autodoc.css`), so the four widths
below each land in a distinct layout band:

| Label | Width | Layout band to verify |
| --- | --- | --- |
| Mobile | 390px | single column; rails collapsed / not overlapping content |
| Tablet | 820px | rails reflowed; content remains primary column |
| Laptop | 1280px | full multi-rail shell begins |
| Wide | 1680px | full three-zone shell, generous gutters |

---

## The matrix

Do one full pass per **(mode x viewport)** combination across all five pages.
That is 5 pages x 2 modes x 4 viewports. For a fast smoke, cover at minimum:
**light/laptop**, **dark/laptop**, **light/mobile**, **dark/mobile** (the four
corners that catch the most regressions); do the full grid before a release.

Mark each cell `PASS` / `FAIL` / `N/A`. A cell only passes if **every**
applicable criterion below holds.

```
                       Mobile        Tablet        Laptop        Wide
                     light / dark  light / dark  light / dark  light / dark
P1 Landing catalog    ___ / ___     ___ / ___     ___ / ___     ___ / ___
P2 Tag / resource     ___ / ___     ___ / ___     ___ / ___     ___ / ___
P3 Endpoint           ___ / ___     ___ / ___     ___ / ___     ___ / ___
P4 Schema index       ___ / ___     ___ / ___     ___ / ___     ___ / ___
P5 Schema detail      ___ / ___     ___ / ___     ___ / ___     ___ / ___
```

---

## Pass criteria

Each criterion lists **what to do** and the **observable signal** that means
pass. If you cannot see the signal, the cell FAILS — note where.

### 1. Non-blank, styled bespoke shell

- [ ] Each page renders content (not a blank page, not an error stub, not raw
      Markdown/JSON dump).
- [ ] The page uses the **bespoke catalog/app shell**, not the legacy reference
      layout: the landing page is a card catalog, schema pages show structured
      property/constraint rows, and the `<body>` carries
      `data-type="autodoc-rest"` (inspect the element).
- [ ] Content is **not clamped to the 75ch prose column** — the catalog/grid
      uses the full app width. (Regression guard: a page squeezed into a narrow
      centered column means the prose clamp leaked back in.)

### 2. Rail reflow (no overlap, clean collapse)

- [ ] At **Laptop/Wide**, the left rail (`[data-api-rail]` nav) and any right
      zone sit beside the content without overlapping it.
- [ ] At **Tablet**, rails reflow rather than colliding with the main column.
- [ ] At **Mobile**, rails collapse / stack; no rail text overlaps body content
      and nothing is clipped off-screen or causes horizontal scroll.
- [ ] Long operation paths and schema names in the rail **truncate with an
      ellipsis** instead of forcing the rail wider (the rail link's first span
      uses `text-overflow: ellipsis`).

### 3. Scroll-spy + hash / anchor routing

- [ ] On a page with a left rail (P1, P2, P3, P5), **scrolling** marks the
      section nearest the top as active: the matching rail link gets
      `.api-rail__link--active` and `aria-current="location"` (inspect, or watch
      the highlight move).
- [ ] **Clicking a rail link** jumps to its section and updates the active
      highlight.
- [ ] Loading a page with a **`#fragment` already in the URL** scrolls to and
      activates that section on load (deep-link / anchor routing).
- [ ] From the landing catalog (P1), an **endpoint anchor routes to the correct
      resource-page operation** — the catalog link lands on the right operation,
      not a sibling.
- [ ] Behavior honors `prefers-reduced-motion`: with reduced motion enabled,
      scrolling is instant (no smooth animation).

### 4. Light / dark readability

- [ ] In **both modes**, body text, schema property names, types, and
      constraint/flag chips are legible against their backgrounds (no
      gray-on-gray, no white-on-white).
- [ ] **Code panels / samples** use the theme's gray-scale tokens and stay
      readable in both modes (no hardcoded dark panel washing out in light
      mode).
- [ ] **Schema tiles** (P4) and **schema detail** rows (P5) — including
      `oneOf` / `anyOf` / `allOf` composition blocks, discriminator mapping
      rows, and constraint chips — remain readable in both modes.
- [ ] Method badges (GET / POST / etc.) and status chips keep sufficient
      contrast in both modes.

### 5. Keyboard focus states

- [ ] **Tab through** each page with the keyboard. A clearly visible focus ring
      (the `:focus-visible` outline: `2px solid var(--color-primary)` with a
      `2px` offset) appears on each interactive target.
- [ ] Focus ring is visible on: **catalog links** (`.api-catalog-nav__link`,
      endpoint / schema catalog cards), **rail nav links** (`.openapi-nav a`),
      **schema tiles** (`.api-schema-catalog__tile`), **copy buttons**
      (`.api-copy-btn`), and **code tabs**.
- [ ] Focus order is sensible (follows visual order; no focus traps; no
      off-screen focus you cannot see).
- [ ] The focus ring is visible in **both** light and dark mode (contrast of the
      outline against the surface behind it).

### 6. Filter preserves deep links

- [ ] On a filterable page (P1 landing, P4 schema index), typing in the filter
      box narrows endpoint cards / schema tiles by method / path / name and
      **collapses empty tag groups**.
- [ ] A no-match query shows the **no-results** state (`[data-api-filter-empty]`,
      announced via `aria-live`), and clearing the box restores everything.
- [ ] Filtering only **hides** items (toggles `hidden`) — it never reorders or
      removes anchored nodes, so the **back button and existing deep links keep
      working**.
- [ ] **Navigating to a `#fragment` whose target is currently filtered out
      clears the filter to reveal it**, then scrolls to it. (Type a filter that
      hides a known section, then paste a URL with that section's `#id` and
      reload — the section must appear and be scrolled into view.)
- [ ] With **JavaScript disabled**, rail links are still real anchors and the
      filter box is simply inert — pages remain navigable (progressive
      enhancement).

---

## Residual visual risks (intentionally deferred)

- **No pixel-level screenshot regression.** This checklist catches structural
  and gross-visual regressions but not subtle per-pixel drift (spacing nudges,
  shadow weight, font-rendering deltas). A headless-browser screenshot harness
  is deferred to **0.5.x**; until then, those risks ride on this manual pass.
- **Palette coverage is light/dark only here.** Bengal ships multiple palettes;
  this checklist verifies the two primary modes. Spot-check other palettes if a
  release changes palette tokens.
- **Real-spec breadth.** The dogfood + `test-openapi-advanced` fixtures are
  representative but not exhaustive of every OpenAPI construct in the wild.
