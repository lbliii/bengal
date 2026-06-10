Added a CI architecture-contract gate: the `Lint & Type Check` workflow now runs
`lint-imports --config .importlinter` (new step in the `lint-and-type` job, feeding the
`lint-ok` branch-protection gate), so any violation of the Site/Page/Section import
contracts fails the build instead of only being catchable by running the linter locally.
Also cleaned up the `.importlinter` baseline so the gate exits green: removed three stale
`ignore_imports` entries that no longer matched any edge (the `bengal.core.site ->
bengal.orchestration.feature_detector` import was removed in `#245`, and neither
`bengal.core.page` nor `bengal.core.section.navigation` imports `bengal.core.site.context`),
and added the live deferred `bengal.core.site -> bengal.orchestration.content` edge that the
contract had been silently broken by. Tightened `RuntimePage._site` from `Any | None` to
`SiteContext | None` to match `Section`, keeping the read-only Site coupling surface explicit.
