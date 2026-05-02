# Site Documentation Steward

The `site/` tree is Bengal's dogfood documentation site. It represents the
reader, site author, plugin developer, and contributor experience before the
project asks anyone else to trust the tool.

Related architecture docs:

- `../AGENTS.md`
- `content/docs/about/philosophy.md`
- `content/docs/get-started/`
- `content/docs/reference/`

## Protect

- Docs that match current CLI behavior, config shape, template context, and
  extension contracts.
- Reader task completion: install, scaffold, build, theme, extend, debug, and
  migrate.
- Runnable examples and snippets that do not depend on unstated local state.
- Clear audience paths for site authors, plugin developers, theme developers,
  and contributors.
- Release notes and migration guidance that say what changed, who is affected,
  and what to do next.

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

- Own authored content under `site/content/`, `site/config/`, `site/data/`, and
  hand-maintained site assets.
- Keep snippets in `site/content/_snippets/` synchronized with installation,
  configuration, and command examples.
- Coordinate with package stewards when docs explain architecture, public API,
  plugin hooks, or theme behavior owned outside `site/`.
- `uv run bengal build site`
- `uv run bengal serve site`
- `rg "TODO|TBD|coming soon|not yet implemented" site/content`
- For command docs, compare examples with `uv run bengal --help` or the
  relevant subcommand help.
