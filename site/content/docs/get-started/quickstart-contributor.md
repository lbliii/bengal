---
title: Contributor Quickstart
nav_title: Contributors
description: Set up Bengal for development and start contributing
draft: false
weight: 40
lang: en
type: doc
tags:
- onboarding
- contributing
- development
keywords:
- contributing
- development
- pull-requests
category: onboarding
id: contributor-qs
icon: code
---

# Contributor Quickstart

Set up Bengal for development and start contributing.

## Prerequisites

:::{checklist} Development Setup
:style: numbered
:show-progress:
- [ ] Python 3.14 or later (3.14t recommended for parallel builds)
- [ ] Git installed and configured
- [ ] A GitHub account
- [ ] Code editor (VS Code, PyCharm, or similar)
:::{/checklist}

## Clone and Install

```bash
# Fork the repo on GitHub first, then:
git clone https://github.com/YOUR-USERNAME/bengal.git
cd bengal

# Create virtual environment (Python 3.14t recommended)
make setup

# Install dependencies (PEP 735 dependency groups) into .venv
make install

# Verify installation
uv run bengal --version
```

## Run Tests

```bash
# Run all tests
make test

# Run specific test file
uv run pytest tests/unit/test_page.py

# Run with coverage
uv run pytest --cov=bengal

# Run tests in parallel
uv run pytest -n auto
```

## Project Structure

```tree
bengal/
├── bengal/
│   ├── core/           # Passive data models (no I/O)
│   ├── orchestration/  # Build coordination
│   ├── rendering/      # Templates and content rendering
│   ├── parsing/        # Markdown parsing and AST helpers
│   ├── content/        # Content discovery + remote sources
│   ├── cache/          # Caching infrastructure
│   ├── health/         # Validation and health checks
│   ├── config/         # Configuration loading
│   ├── directives/     # MyST directive implementations
│   ├── server/         # Dev server with live reload
│   └── cli/            # Command-line interface
├── tests/
│   ├── unit/           # Fast, isolated tests
│   ├── integration/    # Multi-component tests
│   └── roots/          # Test fixtures (sample sites)
├── benchmarks/         # Performance benchmarks
└── site/               # Documentation site
```

## Development Workflow

:::{steps}
:::{step} Create a Branch
:description: Start with a descriptive branch name for your feature or fix.
:duration: 1 min

```bash
git checkout -b feature/my-feature
```

:::{/step}

:::{step} Make Changes
:description: Edit code in the appropriate module following existing patterns.
:duration: varies

Edit code in `bengal/`, following existing patterns. Core modules are passive data structures. Operations go in orchestrators.
:::{/step}

:::{step} Add Tests
:description: All changes need tests. Unit tests for isolated logic, integration tests for workflows.
:duration: 10-30 min

Add tests in `tests/unit/` or `tests/integration/`.
:::{/step}

:::{step} Run Linters
:description: Format and lint your code before committing.
:duration: 1 min

```bash
# Format code
uv run ruff format bengal/ tests/

# Lint and auto-fix
uv run ruff check bengal/ tests/ --fix

# Type check
uv run mypy bengal/
```

:::{/step}

:::{step} Commit
:description: Use descriptive atomic commits that read like a changelog.
:duration: 2 min

```bash
git add -A && git commit -m "core: add feature description"
```

Follow the commit message format described in `CONTRIBUTING.md`.
:::{/step}

:::{step} Push and Create PR
:description: Push your branch and create a pull request for review.
:duration: 5 min

```bash
git push origin feature/my-feature
```

Then create a Pull Request on GitHub.
:::{/step}
:::{/steps}

## Build the Docs Site

From the repository root:

```bash
cd site
uv run bengal serve
```

Visit http://localhost:5173 to preview documentation changes.

:::{tip}
To use `bengal` directly without `uv run`, activate the virtual environment first: `source .venv/bin/activate`
:::

## Key Principles

- **Core modules are passive** — No I/O, no logging in `bengal/core/`
- **Orchestration coordinates** — Build logic lives in `bengal/orchestration/`
- **Tests are essential** — All changes need tests
- **Type hints required** — Use Python type hints everywhere
- **Docstrings required** — All public functions need Google-style docstrings

## CLI Overview

Bengal provides a comprehensive CLI with aliases for common operations:

| Command | Alias | Description |
|---------|-------|-------------|
| `bengal build` | `bengal b` | Build the site |
| `bengal serve` | `bengal s` | Start dev server |
| `bengal clean` | `bengal c` | Clean output directory |
| `bengal validate` | `bengal v` | Validate site configuration |
| `bengal new site` | — | Create a new site |
| `bengal new page` | — | Create a new page |
| `bengal explain` | — | Introspect a page |

## Next Steps

- **[[docs/reference/architecture|Architecture]]** — Understand Bengal's internals
- **[[docs/reference/architecture/meta/testing|Testing Patterns]]** — Test best practices
- **[[docs/about|About Bengal]]** — Philosophy, benchmarks, and FAQ
- **`CONTRIBUTING.md`** — Full contribution guidelines (in repo root)
