Title: Bengal test strategy enhancements (with lessons from Sphinx)

Status: Draft

Owners: testing@bengal, @llane

Motivation
We want Bengal’s test suite to be faster, more reliable, and more ergonomic to author and review. Sphinx’s test suite offers mature patterns we can adapt while keeping Bengal’s simpler, pythonic style.

What Bengal already does well (keep and lean into)
- Failure artifact capture: We persist rich failure details to .pytest_cache/last_failure.txt for quick AI/human debugging.
- Rich console hygiene: Autouse fixture to reset Live displays prevents cross-test interference.
- Property-based tests: Hypothesis-backed tests on URL strategy and text utilities catch edge cases.
- Incremental build coverage: Integration tests exercise full→incremental→full sequences and cache behavior.
- Performance awareness: Dedicated performance tests and micro-benchmarks.
- Parametrized integration assertions: Base URL, link generation, and template variants are covered via parametrization.

High-level goals
- Reliability: Reduce flaky tests and cross-test coupling; deterministic outputs by default.
- Speed: Avoid repeated heavy setup; cache expensive parsing; re-use canonical test roots.
- Ergonomics: One-liners to stand up a site and assert outputs; fewer bespoke setups.
- Observability: Consistent logs, warnings, and metrics capture for assertions.

Scope (what we’ll add)
1) Canonical test roots
- Create tests/roots/<scenario>/ directories with minimal bengal.toml, content/, and optional assets/themes.
- Provide a rootdir fixture resolving to tests/roots (and tests/roots-read-only on CI if needed).
- Guidance: Each root is tiny and focused on one scenario; prefer composition over monolithic roots.

2) Pytest plugin and marker
- tests/_testing/fixtures.py loaded via pytest_plugins for suite-wide fixtures.
- Introduce @pytest.mark.bengal(builder?, testroot?, confoverrides?) that wires a ready site fixture:
  - Resolves testroot into a concrete project path under tests/roots/.
  - Applies confoverrides on top of bengal.toml when constructing the Site.
  - Exposes site, build_site, logs (captured status/warnings) to tests.
- Add pytest_report_header to print versions (Python, Bengal), GIL mode (3.13+), test roots path, and base tmp path.

3) Output normalization and snapshots
- Provide helpers to normalize HTML/JSON (stable whitespace, consistent attribute ordering, strip volatile timestamps/absolute paths).
- Offer assert_matches_golden(path) using either in-repo golden files or pytest-regressions plugin.
- Document snapshot boundaries (what to normalize vs what to assert precisely).

4) HTTP server utilities (deterministic link tests)
- tests/_testing/http.py provides http_server, serve_application, and optional TLS variant.
- Add rewrite_hyperlinks(app, server) to point static localhost:PORT in content to ephemeral ports at runtime.

5) Global cleanup and cache hygiene
- Expand autouse cleanup to include: template/Jinja env resets, assets/font registries, and any in-memory caches (render, content discovery, URL maps).
- Provide package-scoped cached parse fixtures (e.g., cached_etree_parse, cached_yaml_parse) to speed tests doing repeated parsing.

6) CLI runner wrapper
- tests/_testing/cli.py exposes run_cli(args, env=None, timeout=...), capturing exit code, stdout/stderr, and stripping ANSI by default.
- Common asserts: assert_ok, assert_fail_with(code), assert_stderr_contains(...).

7) Marker taxonomy and defaults
- Standardize markers: slow, network, snapshot, hypothesis.
- Default CI selection: -m "not slow and not network"; run slow on nightly.

Design details
Test roots
- Structure: tests/roots/test-<scenario>/{bengal.toml, content/, assets/, theme/}
- Naming: test-<feature> or test-<bug-id>.
- Keep scenarios tiny (≤ 5 files unless necessary) and single-purpose.

Pytest plugin and marker
- tests/_testing/__init__.py
- tests/_testing/fixtures.py
  - rootdir(session)
  - site_factory(tmp_path) → construct Site from root + overrides
  - logs capture: a light wrapper over Bengal logger to buffer status/warnings per test
- tests/_testing/markers.py
  - implements pytest_collection_modifyitems to recognize @pytest.mark.bengal and inject fixtures/params

Output normalization
- HTML: tidy whitespace, collapse attributes ordering (via lxml or BeautifulSoup), normalize file:// and absolute paths to placeholders, strip build timestamps.
- JSON: sort keys, stable indent, strip fields known to be time/host dependent.

HTTP server utilities
- Threaded HTTP/HTTPS server with context managers; wait-until-listen guard; terminate reliably on teardown.
- rewrite_hyperlinks hook: Replace localhost:7777 with actual ephemeral port; keep test-fixture content simple.

Cleanup and caches
- Identify caches/singletons to reset:
  - Template/Jinja environment
  - Asset pipeline state (hash caches)
  - Fonts/pygments registries (if any)
  - Discovery caches and page registries
  - Global logger handlers

CLI runner
- Prefer subprocess for end-to-end parity; consider click.testing for speed where applicable.
- Strip ANSI by default; optionally preserve when asserting style output.

Adoption plan (phased)
Phase 1 (infra, ~1–2 days)
- Add tests/_testing/ package (fixtures, markers, http, cli, snapshots, normalize utils, cached parses, header).
- Add pytest.ini markers and defaults.
- Add tests/roots/ with 3–5 canonical roots (root, html-assets, baseurl, taxonomy-minimal, templates-minimal).

Phase 2 (pilot migrations, ~1–2 days)
- Convert 5–10 representative integration tests to @pytest.mark.bengal with testroot.
- Replace ad-hoc CLI calls with run_cli and add normalization.
- Add first golden snapshots for a narrow HTML subset (e.g., head block).

Phase 3 (broader migration, ~3–5 days)
- Migrate remaining integration tests to use roots + marker.
- Introduce http_server for link-related tests.
- Remove duplicated per-test setup in favor of site_factory/build_site.

Phase 4 (optimization, ~1–2 days)
- Introduce package-scoped cached parse fixtures for hot paths.
- Optional: shard tests on CI; pre-build selected roots for speed.

Phase 5 (stabilization, ongoing)
- Deflake: add normalization rules as we discover sources of nondeterminism.
- Track metrics and enforce budgets (see below).

CI and tooling
- pytest.ini: register markers; set default selection; ensure color=no for non-TTY to stabilize outputs.
- CI jobs: fast (PR) vs full (nightly). Upload artifacts on failure (stdout, stderr, normalized outputs, snapshot diffs).
- Coverage: stable measurement per job; gate only on lines we care about (exclude generated code and test roots).

Metrics and success criteria
- End-to-end test duration reduced by 25–40% on PR workflow.
- Flake rate (<0.5% reruns) and retry depth (≤1) across 7 days.
- Deterministic diffs: snapshot churn only when templates change.
- Authoring time: new E2E test in ≤ 10 lines (marker + a few asserts).

Risk management
- Snapshot brittleness: mitigate by normalizing and scoping snapshots (small, focused files/sections).
- Cross-platform variance: normalize newlines/paths; prefer ephemeral-port rewrite for link tests.
- Over-mocking: keep tests as black-box where possible; reserve unit tests for internals.

Backout/Compatibility
- Maintain old-style tests while migrating; remove only after parity is demonstrated.
- Marker and fixtures are additive; opt-in migration.

Deliverables checklist
- tests/_testing/{__init__.py, fixtures.py, markers.py, http.py, cli.py, normalize.py, snapshots.py, cached_parsers.py}
- tests/roots/test-*/ minimal scenarios
- pytest.ini marker and config updates
- Docs: CONTRIBUTING.md section "Writing tests" updated with examples

Next steps
- Implement Phase 1 infra and migrate 3–5 tests as examples.
- Review ergonomics, iterate on APIs, and proceed to Phase 2.
