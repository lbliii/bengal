---
name: check-and-fix
description: Validate a Bengal site with bengal check, apply safe fixes with bengal fix, and audit generated output with bengal audit. Use when content fails to build, links break, directives error, or before publishing.
---

# Check and Fix a Bengal Site

Validate and repair a site as a **site author**. Use the flags printed by
`--help`. When a command fails, **read the error and the finding code it
prints**. Do not invent health codes, validator names, or flags.

Run from the site root.

```bash
bengal check --help
bengal fix --help
bengal audit --help
```

## Validate content

```bash
bengal check
```

Useful flags from help:

```bash
bengal check --file content/docs/getting-started.md
bengal check --changed
bengal check --verbose
bengal check --suggestions
bengal check --watch
bengal check --templates
```

- `--file` takes comma-separated paths.
- `--changed` validates changed files (requires build cache).
- `--profile` values: `writer`, `theme-dev`, `developer`.
- `--style`: `dense`, `ascii`, or `ci`. `--limit` caps findings (`0` = all).
- `--focus` shows one finding by the **display code printed in the report**
  (help example shape: `H101-001`). Use the code you actually received.
- `--ignore` skips codes from the report (help example shape: `H101,H202`).
  Copy codes from output; do not guess.

On failure: read the validator, path, and recommendation. Then either edit the
source or run `bengal fix` if the finding looks auto-fixable.

## Auto-fix

Preview first:

```bash
bengal fix --dry-run
```

Apply safe fixes (default):

```bash
bengal fix
```

Other flags from help:

```bash
bengal fix --confirm
bengal fix --all
bengal fix --validator Directives
```

`--validator` examples in help: `Directives`, `Links`. Use a validator name
from the check report if it differs.

Safety (from the validation docs): safe fixes apply by default; confirm-level
fixes need `--all` or `--confirm`; unsafe fixes stay manual.

## Audit generated output

`bengal audit` checks **built artifacts**, not source. Build first:

```bash
bengal build
bengal audit
```

Flags from help:

```bash
bengal audit --json
bengal audit --output public
bengal audit --style ci --limit 0
```

`--focus` uses a code from the audit report (help example shape: `A101-001`).
If focus misses, the command tells you to use a code from `bengal audit`.

## CI / strict builds

```bash
bengal check --verbose
bengal build --strict
bengal audit
```

`--strict` is on `bengal build --help` (fail on template errors; recommended
for CI). `--validate` on build validates templates before building.

## Optional: link inspect

Registered command for link-only checks (from `bengal inspect links --help`):

```bash
bengal inspect links
bengal inspect links --internal-only
```

Prefer `bengal check` for the full health pass.

## Docs to read

- [/docs/ship/validate/](https://lbliii.github.io/bengal/docs/ship/validate/)
- [/docs/ship/validate/validate-and-fix/](https://lbliii.github.io/bengal/docs/ship/validate/validate-and-fix/)
- [/docs/reference/errors/health-codes/](https://lbliii.github.io/bengal/docs/reference/errors/health-codes/)
  — look up a code **after** the CLI prints it.

## Checklist

- [ ] `bengal check` was run; failures were read, not guessed
- [ ] Fixes previewed with `bengal fix --dry-run` before applying
- [ ] `bengal build` then `bengal audit` before publish
- [ ] No health/audit codes were invented
