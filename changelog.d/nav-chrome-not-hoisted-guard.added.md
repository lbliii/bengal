Added `tests/integration/test_nav_chrome_not_hoisted.py` — a discriminating guard that the
default theme's navigation active-state is rendered per page and never hoisted as page-invariant
chrome. It builds a multi-section site and asserts each section's page marks its own nav entry
active (`/docs/` → "Documentation", `/blog/` → "Blog") and not the other's, so any future
"render the chrome once" optimization (#348) that cached the page-scoped nav block as if it were
site-scoped would fail here instead of silently shipping stale navigation. Backed by the
investigation note `benchmarks/348-chrome-memoization-findings.md`.
