<!-- markdownlint-disable MD013 -->

# #348 chrome-memoization — investigation findings (2026-06-04)

**TL;DR:** #348 ("render the invariant chrome once and reuse") is **not** the cheap,
box-independent win it was scoped as. Its named mechanism — `BlockCache.warm_site_blocks` —
is **silently dead** on the default theme, its block-scope classification is **unsafe**, the
genuinely-invariant chrome is **already** hoisted by a *different* (working) mechanism, and the
large remaining chrome cost is **per-page-varying** work that can't be hoisted without an
architectural change. The honest recommendation is to **reframe #348** as gated on the clean-box
attribution (#345 step 2), not bank it as a free parallel win. None of this needed the clean box
to establish — it's all structural/correctness, reproducible on any machine.

This note backs the guard test `tests/integration/test_nav_chrome_not_hoisted.py` and feeds the
community write-up (#349).

## What #348 assumed

> Most of a rendered page is invariant chrome — header, primary nav/menu, sidebar, footer —
> byte-identical across ~all pages. Rendering it per page is redundant; render it once per build
> and splice it in. Extend the existing site-scoped block cache (`warm_site_blocks` /
> `block_cache_*`).

## What is actually true (all verified on this machine)

### 1. The `BlockCache` is silently dead on the default theme

A cold build (100-page blog fixture, default theme, Kida engine) reports, in **both** sequential
and parallel modes:

```
block_cache_hits = 0   block_cache_misses = 0   block_cache_site_blocks = 0   block_cache_time_saved_ms = 0.0
```

Direct introspection shows the engine *does* advertise `BLOCK_CACHING` and the analysis *does*
classify blocks — but `warm_site_blocks(engine, "base.html", site_ctx)` caches **0** of them.
The reason (surfaced by un-suppressing the `except Exception` at `block_cache.py:302`):

```
TemplateRuntimeError: Runtime Error: NameError: name '_ls' is not defined
  Location: base.html:15  ->  {% let params = params ?? {} %}
```

`base.html` declares template-wide variables with **module-level `{% let %}`** (lines 15–41:
`params`, `_page_url`, `_main_menu`, `_auto_nav`, …). Kida's `render_block` scaffold does not
initialize that let-store (`_ls`) the way a full `render()` does, so **every** block render
throws. The failure is logged at `debug` level only, so the subsystem *looks* implemented while
caching nothing and never being read (`renderer.py:427` gates injection on `_site_blocks` being
non-empty, which it never is).

### 2. The block-scope classification is unsafe

The introspection labels these `base.html` blocks `scope='site'`:
`extra_head, nav_items, content, site_search_modal, mobile_nav_items, site_footer, site_scripts,
extra_js, site_dialogs`. At least three are **not** site-invariant:

- `nav_items` / `mobile_nav_items` read the **per-page** `_page_url` for active state
  (`base.html:51`: `is_active = (item?.active ?? false) or (_page_url == _item_href)`).
- `content` is the per-page body block.

So if the dead warming path were "repaired" without also fixing the scope classification, it would
cache the nav/content rendered with `page=None` and splice **stale nav + duplicated content** onto
every page. (This is why the guard test exists.)

### 3. The nav/header/footer are NOT byte-identical across pages

Rendered `<header>`/`<nav>` are the **same length but different bytes** across pages, each
carrying exactly one `class="active"` + `aria-current="page"`. Concretely, on the `test-navigation`
root: `/docs/` marks "Documentation" active, `/blog/` marks "Blog", the home page marks none.
The active-highlight is **server-rendered per page** — the nav is genuinely page-varying, not
hoistable as-is.

### 4. The genuinely-invariant chrome is already hoisted — by a different mechanism

The static head/scripts/dialogs/speculation fragments are wrapped in Kida's **`{% cache %}`
directive** (e.g. `{% cache 'base-head-assets-' ~ (bengal.build.timestamp ?? '') %}`), keyed
build-wide. That path *works* (it runs inside the normal `render()`), so the safe-to-hoist chrome
is already covered — the dead `BlockCache` has nothing safe left to add there.

### 5. The chrome cost is large but dominated by per-page work

Render time, default theme vs a minimal `base.html` override (100-page blog, sequential,
median-of-3):

| | Rendering phase |
|---|--:|
| default theme | ~2012 ms |
| minimal base (just `{% block content %}`) | ~572 ms |
| delta (all template furniture) | **~1440 ms ≈ 72% of render** |

This 72% is an **upper bound** on chrome cost — the minimal override also skips per-page furniture
(TOC, sidebars, article metadata). The point stands: theme templating is a big slice of render,
but it's dominated by **per-page-varying** work (the auto-nav active-state walk done per page,
page furniture), not by safely-hoistable invariant chrome.

## Decision & recommendation

**Do not build chrome-memoization machinery now, and reframe #348.** Rationale:

- The safe, easy chrome is already hoisted (`{% cache %}`). The dead `BlockCache` can't add to it
  without (a) a Kida `render_block` fix for module-`{% let %}` templates **and** (b) a corrected,
  page-vs-site scope classification — and even then it would double-cache what `{% cache %}` covers.
- The real remaining prize is the **per-page nav active-state walk**. Capturing it safely needs
  either an architectural change (render the nav once, apply active-state cheaply — e.g. client-side
  or a post-render splice, which *changes rendered output semantics*) **or** the native attribution
  (#345 step 2, clean box) to confirm the nav walk — not TOC/sidebars — is where the 72% goes
  before investing. So **#348 is more coupled to the attribution fork than its "ship anytime"
  framing claimed**, not independent of it.

Concrete follow-ups worth filing:

1. **Bug:** `BlockCache.warm_site_blocks` is dead on the default theme (Kida `render_block` +
   module-`{% let %}`), failing silently at debug level. Either make it work *and* fix the unsafe
   scope classification, or remove the warming path (note: `_block_hashes` is separately used by
   block-level incremental builds — don't remove that).
2. **Safety:** the `scope='site'` labels for `nav_items`/`mobile_nav_items`/`content` are wrong;
   any repair must reclassify page-scoped blocks. The guard test
   `tests/integration/test_nav_chrome_not_hoisted.py` will fail if a repair ships stale nav.

## Reproduce

```bash
# 0/0/0 block cache + the render_block _ls failure + 72% chrome delta were measured with
# throwaway scripts against benchmarks/benchmark_gil_speedup.create_site (blog, 100 pages) and the
# tests/roots/test-navigation root. The durable artifact is the guard test:
uv run pytest tests/integration/test_nav_chrome_not_hoisted.py -v
```
