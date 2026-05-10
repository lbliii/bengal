# Bengal Hardening Proof Notes (May 2026)

**Status**: implementation proof for the steward-prioritized hardening batch.

## Accepted Focus

- Build-scoped state isolation for plugin registries, effect tracers, registry
  page indexes, and diagnostics collection.
- Stale-output prevention for provenance mtime races, section derived caches,
  and dev-server reactive fallbacks.
- Atomic writes for rendered output and user-visible generated artifacts.
- Deep-frozen pipeline records for source, parse, and render handoffs.
- Plugin registry contract validation.

## Proof Matrix

| Area | Proof |
| --- | --- |
| Build-scoped state | `uv run pytest tests/unit/plugins/test_plugin_parser_wiring.py tests/unit/core/test_site_context_protocol.py tests/unit/core/test_diagnostics_collector.py tests/unit/effects/test_render_integration.py -q` |
| Stale output | `uv run pytest tests/unit/build/provenance/test_mtime_short_circuit.py tests/unit/cache/test_build_cache.py tests/unit/core/test_section_sorting.py tests/unit/server/test_build_trigger.py tests/integration/warm_build/test_build_trigger_reactive.py -q` |
| Provenance adjacency | `uv run pytest tests/unit/build/provenance/test_filter.py tests/unit/orchestration/build/test_provenance_filter_path_keys.py tests/integration/test_incremental_cache_stability.py -q` |
| Atomic writes | `uv run pytest tests/unit/rendering/test_write_output_rendered_page.py tests/unit/postprocess/test_special_pages.py tests/unit/postprocess/test_output_formats_hash.py tests/unit/postprocess/test_output_formats_config.py -q` |
| Atomic cache stores | `uv run pytest tests/unit/cache/test_cache_store.py -q` |
| Atomic build badge helper | `uv run pytest tests/unit/orchestration/build/test_finalization.py::TestBuildBadgeIncremental::test_write_if_changed_skips_identical_content tests/unit/orchestration/build/test_finalization.py::TestBuildBadgeIncremental::test_write_if_changed_updates_on_different_content -q` |
| Pipeline records | `uv run pytest tests/unit/core/test_source_page.py tests/unit/core/test_page_record_migration.py tests/unit/core/test_page_core.py tests/unit/core/page/test_yaml_edge_cases.py tests/unit/cache/test_page_discovery_cache.py -q` |
| Plugin contracts | `uv run pytest tests/unit/plugins tests/unit/protocols tests/unit/cli/test_plugin_command.py -q` |
| Site docs | `uv run bengal build` from `site/` |

## Residual Risks

- `uv run bengal build site` is rejected by the current CLI, so the site proof
  was run as `uv run bengal build` from `site/`. That command completed and
  wrote `site/public`, but it still reports existing site diagnostics: URL
  collision at `/docs/content/i18n/`, missing `languages` icon, unserveable
  `/assets/css/style.css` references, and four `dict.enum` autodoc template
  rendering errors in `autodoc/openapi/partials/schema-viewer.html`.
- A broad `tests/unit/postprocess tests/unit/orchestration/build/test_finalization.py`
  run still includes pre-existing failures in finalization tests around
  `MagicMock` serialization and stale patch targets. The narrower postprocess
  proof for changed write paths passed.
- Existing dependency-layer warnings remain unchanged in pre-commit:
  `bengal.orchestration.site_runner -> bengal.server.dev_server`,
  `bengal.errors.* -> bengal.rendering/utils`, and
  `bengal.utils.paths.link_resolution -> bengal.rendering.reference_resolution`.

## Not Now

- Removing the `fast_writes` config key. The implementation now keeps output
  writes atomic while preserving the compatibility flag.
- Widening plugin protocols or adding new hook surfaces. This batch only
  validates the existing registry contract.
