# Contributing to Bengal

This repository uses **uv** and **PEP 735 dependency groups** for development dependencies.

## Development setup (recommended)

```bash
make setup
make install
```

## Common verification commands

```bash
make test
make typecheck
```

Optional:

```bash
uv run ruff format bengal/ tests/
uv run ruff check bengal/ tests/
```

## Documentation

The contributor quickstart lives in the documentation site:

- `site/content/docs/get-started/quickstart-contributor.md`
