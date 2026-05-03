# Health Steward

Health checks validate source content and author-facing policy. They should find
problems early, explain next steps, and stay distinct from generated artifact
audits.

Related docs:
- root `../../AGENTS.md`
- `../../site/content/docs/reference/architecture/subsystems/health.md`
- `../../site/content/docs/content/validation/validate-and-fix.md`
- `../../plan/rfc-health-diagnostics-audit.md`

## Point Of View

Health represents authors trying to trust a site before publishing. It should
surface broken links, policy issues, and quality risks with evidence and
actionable recommendations.

## Protect

- Source policy checks under `bengal check` and compatibility alias behavior.
- Validator independence, result envelopes, severity ordering, and diagnostics.
- Separation from `bengal audit` artifact scanning.
- Link/reference truth shared with rendering registries without duplicating
  ownership.

## Contract Checklist

- Tests under `tests/unit/health/` and health validator integration tests.
- CLI output envelopes, JSON formats, docs, and troubleshooting snippets.
- Rendering/reference registry collateral for link and anchor validation.
- Config docs when validator enablement, thresholds, or defaults change.
- Changelog for user-visible validation behavior.

## Advocate

- Validator messages that name the file/page, why it matters, and the fix.
- Narrow validators with cheap execution and clear failure boundaries.
- Regression fixtures for malformed content, broken links, and false positives.

## Serve Peers

- Give rendering precise feedback when generated references are ambiguous.
- Give CLI structured result envelopes and progressive human output.
- Give docs and scaffolds checks that keep examples publishable.

## Do Not

- Mix generated artifact audit policy back into source health checks.
- Swallow validator crashes without a result that names the validator and site
  context.
- Treat all link failures as the same class of problem.
- Add validators that require broad global state or unpredictable network work
  in normal builds.

## Own

- `bengal/health/`
- `site/content/docs/reference/architecture/subsystems/health.md`
- `site/content/docs/content/validation/validate-and-fix.md`
- Tests: `tests/unit/health/`
- Checks: `uv run pytest tests/unit/health -q`
- Checks: `uv run ruff check bengal/health tests/unit/health`
