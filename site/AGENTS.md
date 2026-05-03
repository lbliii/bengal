# Site Documentation Steward

The `site/` tree is Bengal's dogfood documentation site. It represents the
reader, site author, plugin developer, and contributor experience before the
project asks anyone else to trust the tool.

Related docs:
- root `../AGENTS.md`
- `content/docs/about/philosophy.md`
- `content/docs/get-started/`
- `content/docs/reference/`
- `../docs/b-stack-changelog-strategy.md`

## Point Of View

Site docs represent readers trying to complete tasks: install, scaffold, build,
theme, extend, debug, migrate, and understand architecture.

## Protect

- Docs that match current CLI behavior, config shape, template context, and
  extension contracts.
- Reader task completion for site authors, plugin developers, theme developers,
  and contributors.
- Runnable examples and snippets that do not depend on unstated local state.
- Release notes and migration guidance that say what changed, who is affected,
  and what to do next.

## Contract Checklist

- Authored docs under `site/content/`, snippets, config, data, and hand-maintained
  assets.
- README/CONTRIBUTING parity when quickstarts or contributor flows change.
- CLI help and command examples for command docs.
- Package stewards for architecture, protocols, config, rendering, theme, and
  output claims.
- `uv run bengal build site` for substantial docs or template changes.

## Advocate

- Docs that reveal the fastest successful path for each audience before diving
  into internals.
- Better diagnostics, examples, snippets, and commands when documentation has
  to explain around product friction.
- Migration notes and release pages that treat breaking or surprising behavior
  as reader work, not maintainer trivia.

## Serve Peers

- Give CLI, rendering, theme, protocol, and orchestration stewards feedback
  when their behavior is hard to explain.
- Keep docs examples aligned with real commands, template context, and config
  so package stewards do not inherit outdated promises.
- Turn recurring support questions into docs issues or clearer examples.

## Do Not

- Document aspirational behavior as shipped behavior.
- Let generated output under `.bengal/` or `public/` become the source of truth
  for authored docs.
- Add prose that requires knowing Bengal internals before completing a user
  task.
- Hide sharp edges behind marketing language; if the behavior is limited,
  document the limit.

## Own

- `site/content/`, `site/config/`, `site/data/`, and hand-maintained site assets
- Snippets in `site/content/_snippets/`
- Architecture, public API, plugin hook, and theme docs in coordination with
  package stewards
- Checks: `uv run bengal build site`
- Checks: `rg "TODO|TBD|coming soon|not yet implemented" site/content`
- For command docs, compare examples with `uv run bengal --help` or subcommand help.
