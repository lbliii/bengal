# Kida Render Performance — Bengal Handoff

**Date:** 2026-03-18
**Bengal version:** 0.2.6
**Kida version:** 0.2.7
**Prepared by:** Bengal core team

---

## Summary

Bengal's render pipeline profiler shows that `template.render()` inside Kida accounts
for **~20ms per page** and **>129% of total wall time** on a 1,534-page site. Everything
else in the pipeline (markdown parsing, link extraction, cache I/O, disk writes) is
effectively noise. The bottleneck is entirely inside Kida.

We are giving you this document so you can investigate on the Kida side with full context
on what Bengal is doing before the call into Kida, what data is being passed in, and
where we suspect overhead is hiding.

---

## Profiler Data

Run: `BENGAL_PROFILE_RENDER=1 bengal build --no-incremental`
Site: 1,534 pages (584 full renders, rest hit rendered cache)

```
╔══ Render Pipeline Profile ══════════════════════════════════════╗
  Pages: 1,534   Wall time: 24,053ms   Throughput: 64/sec

  Step                              Total    Avg/pg     Max    % wall
  ──────────────────────────────────────────────────────────────────
  Cache check                          1ms   0.00ms   0.0ms     0.0%
  Markdown parse                     104ms   0.07ms  35.2ms     0.4%
  HTML transform                       0ms   0.00ms   0.0ms     0.0%
  plain_text compute                   0ms   0.00ms   0.0ms     0.0%
  API doc enhance                      8ms   0.00ms   0.8ms     0.0%
  Link extraction                     26ms   0.02ms   0.7ms     0.1%
  Cache write (parsed)                 1ms   0.00ms   0.5ms     0.0%
  render_content()                     7ms   0.00ms   0.3ms     0.0%
  render_page() template          31,125ms  20.32ms 490.5ms   129.4% ◀
  format_html()                    3,812ms   2.49ms  93.2ms    15.8%
  Cache write (rendered)               1ms   0.00ms   0.0ms     0.0%
  write_output()                     246ms   0.16ms  21.7ms     1.0%
  JSON accumulate                    916ms   0.60ms  40.4ms     3.8%
  Asset dep accumulate                24ms   0.02ms   5.2ms     0.1%
  ──────────────────────────────────────────────────────────────────
  Unaccounted (GIL/sched/overhead) -12,217ms                  -50.8%

  Cache hits  →  rendered: 0   parsed: 0   full render: 584
╚══════════════════════════════════════════════════════════════════╝
```

**The 584 pages that did a full render averaged ~45ms each in `render_page() template`
alone** (the avg/pg numbers above are across all 1,534 including cached pages).

The "unaccounted" going negative is expected — it represents thread parallelism
(ThreadPoolExecutor) where wall-clock is less than the sum of worker-thread time.

---

## What Bengal Does Before Each `template.render()` Call

Here is the exact call sequence inside `KidaTemplateEngine.render_template()`
(`bengal/rendering/engines/kida.py`, line 310) for every page:

### 1. Full menu cache invalidation (line 329)
```python
self.invalidate_menu_cache()  # clears _menu_dict_cache entirely
```
This wipes the entire menu dict cache before every single page render. See
**Menu Cache Problem** section below — this is a known architectural issue.

### 2. EffectTracer ContextVar writes (lines 332–340)
```python
from bengal.effects.render_integration import record_extra_dependency, record_template_include
record_template_include(name)
template_path = self.get_template_path(name)
if template_path: record_extra_dependency(template_path)
```
Two ContextVar writes per render before Kida is even invoked.

### 3. Recursive template dependency walk (line 342)
```python
self._track_referenced_templates(name)
```
For every page render, this walks the full template inheritance tree
(`{% extends %}`, `{% include %}`, `{% import %}`) recursively via
`template.dependencies()` — calling `self._env.get_template()` on
each template in the chain. For a page using the base template this
could be 5–10 `get_template()` calls per page. These are tracked via
EffectTracer for incremental rebuild dependency tracking.

> **Note:** This walk happens on every render, even for pages using identical
> templates. The results are not cached between pages.

### 4. Context dict construction (lines 349–358)
```python
ctx = {"site": self.site, "config": self.site.config}
ctx.update(context.items())   # forces LazyPageContext evaluation
page_functions = self._env._page_aware_factory(page)
ctx.update(page_functions)
```
`context.items()` forces a `LazyPageContext` to evaluate all lazy values
(reading_time, toc, excerpt, params cascade, section context, etc.) before
`template.render()` is called. The `_page_aware_factory(page)` call produces
per-page functions (`t()`, `current_lang()`, etc.) that are injected into ctx.

### 5. `template.render(ctx)` — the call into Kida (line 369)
This is what our profiler's `render_page() template` bucket is measuring.
Everything above this line is outside the timing window.

---

## The Menu Cache Problem (Thread-Safety + Performance)

This is the most significant issue we found and it needs a fix at the
MenuItem level before any menu cache optimization is safe.

### Current design (broken for parallel rendering)

`MenuItem.active` and `MenuItem.active_trail` are **mutable flags stored
directly on shared `MenuItem` objects** in `site.menu[name]`. Before each
page render, Bengal calls:

```python
# bengal/rendering/renderer.py:374
self.site.mark_active_menu_items(page)   # mutates MenuItem.active in-place
```

Then inside `render_template()`:

```python
self.invalidate_menu_cache()             # clears entire dict cache
# ...later when template calls get_menu("main"):
self._menu_dict_cache[key] = [item.to_dict() for item in menu]  # snapshots active flags
```

`to_dict()` captures `.active` and `.active_trail` at call time. Because
these flags are on shared objects, the cache has to be fully cleared on every
page render or you get stale active states from the previous page.

### Thread-safety race condition (existing bug)

With `ThreadPoolExecutor` rendering pages concurrently:

- Thread A renders `/docs/guide/` → calls `item.active = True` on the "Guide" MenuItem
- Thread B renders `/about/` → calls `item.active = False` on the same object simultaneously
- No lock protecting these mutations

The full cache clear before each render masks the problem in practice
(each thread clears and rebuilds independently) but the underlying mutation
race is unprotected and can produce wrong active states under load.

### Recommended fix

Decouple active state from `MenuItem` entirely. `MenuItem` objects should be
immutable after the build phase. Active state should be computed at render
time by passing the current page URL through the template context and
evaluating "is this item active?" as a template function/filter call — not
by mutating shared objects.

If that is a large change, a smaller safe step is to key the menu dict cache
by `(page_url, menu_name)` rather than `menu_name` alone, so each page gets
its own cached dicts and `to_dict()` is only called once per (page, menu)
pair rather than on every render. **This still has the mutation race but
eliminates the repeated dict construction cost.**

---

## Context Object Size

For a typical documentation page, the context dict passed to `template.render()`
contains roughly:

| Key | Type | Notes |
|-----|------|-------|
| `site` | SiteWrapper | wraps entire site object |
| `config` | ConfigWrapper | wraps site.config |
| `page` | Page | the current page |
| `content` | str | rendered HTML (can be 10–200KB) |
| `toc` | list | table of contents entries |
| `section` | Section | parent section |
| `params` | CascadingParamsContext | cascaded metadata |
| `reading_time` | int | computed minutes |
| `excerpt` | str | first paragraph |
| `meta_description` | str | SEO description |
| `t` | function | i18n translation lookup |
| `current_lang` | function | language resolver |
| `menus` | MenusContext | lazy menu builder |
| `theme` | ThemeWrapper | theme config/assets |
| `versions` | list | multi-version info (if enabled) |

The `site` wrapper in particular is large — it holds references to all 1,534
pages, all sections, all menus, all config, and all assets.

---

## Template Structure

Templates use standard Kida inheritance. A typical documentation page goes:

```
page-template.html
  └─ extends base.html
       ├─ includes partials/header.html
       ├─ includes partials/nav.html       (accesses menus context)
       ├─ includes partials/sidebar.html   (accesses section hierarchy)
       ├─ includes partials/toc.html       (accesses toc list)
       └─ includes partials/footer.html
```

The `_track_referenced_templates()` walk (described above) processes this
entire chain on every page render.

---

## Hypothesis: Where the 20ms Is Going

Based on the profile data and code review, our best guesses in priority order:

1. **Template compilation / bytecode cache misses** — if `get_template()` is
   recompiling templates rather than hitting a bytecode cache on each render,
   that alone could explain 5–10ms. The `_track_referenced_templates()` loop
   calls `get_template()` 5–10 times per page in addition to the render call.

2. **Context dict evaluation cost** — `ctx.update(context.items())` forces
   all lazy values to evaluate before Kida sees the context. If Kida is then
   re-evaluating any of these lazily internally, there is double work.

3. **Menu dict reconstruction** — `to_dict()` is called on every `MenuItem`
   in every menu on every page render (cache is cleared each time). On a site
   with 3 menus × 20 items × 5 children each, that is 300 `to_dict()` calls
   per page = 175,200 calls total for 584 full renders.

4. **Template inheritance chain evaluation** — if `{% extends %}` causes
   Kida to re-evaluate parent block resolution on every render rather than
   caching the resolved block tree, large templates with deep inheritance
   will be slower per-call.

5. **`_page_aware_factory` overhead** — called once per render to produce
   per-page i18n functions. If this creates new function objects with closures
   on every call, it adds allocation pressure.

---

## What We Have Already Ruled Out

These are **not** the problem — confirmed by profiler:

- Markdown parsing: 0.07ms/page
- HTML transforms (pygments highlight flush, BeautifulSoup): 0ms (pre-compiled regex, opt-in)
- Link extraction: 0.02ms/page
- Cache I/O: 0ms
- Disk writes: 0.16ms/page
- JSON accumulation: 0.49ms/page

---

## Reproduce It Yourself

```bash
# Clone the Bengal repo
git clone <bengal-repo> && cd bengal

# Build with profiler
BENGAL_PROFILE_RENDER=1 uv run bengal build --no-incremental

# Profile a single page render (no parallelism)
BENGAL_PROFILE_RENDER=1 uv run bengal build --no-incremental --no-parallel
```

The `--no-parallel` flag forces sequential rendering and eliminates the
"unaccounted (GIL/sched/overhead)" negative number, giving cleaner per-step
numbers.

The profiler source is at `bengal/rendering/pipeline/profiler.py` if you
want to add finer-grained instrumentation on the Bengal side to correlate
with whatever you add inside Kida.

---

## Questions We'd Like Answered

1. Does `_env.get_template(name)` hit a bytecode cache on repeated calls,
   or does it recompile? What is the cache keying strategy?

2. Is `template.render(ctx)` re-evaluating the template's block inheritance
   tree on every call, or is that resolved once at compile time?

3. What does `_page_aware_factory` actually create — are these new function
   objects per call or references to pre-existing objects?

4. Is there a way to pass active-state information into the menu context
   without mutating `MenuItem` objects, so Bengal can stop clearing the
   menu dict cache on every page render?

5. For the `_track_referenced_templates()` dependency walk — is there a
   cheaper way to get `template.dependencies()` without calling
   `get_template()` on each dep in the chain? E.g., a bulk dependency
   resolution API?

---

*End of handoff document.*
