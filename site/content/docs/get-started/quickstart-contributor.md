---
title: Contributor Quickstart
description: Set up Bengal for development and start contributing
weight: 40
type: doc
draft: false
lang: en
tags: [onboarding, contributing, development]
keywords: [contributing, development, pull-requests]
category: onboarding
aliases:
  - /docs/getting-started/contributor-quickstart/
---

# Contributor Quickstart

Set up Bengal for development and start contributing.

## Prerequisites

- Python 3.12+ (3.14t recommended)
- Git
- A GitHub account

## Clone and Install

```bash
# Fork the repo on GitHub first, then:
git clone https://github.com/YOUR-USERNAME/bengal.git
cd bengal

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install in development mode with all dependencies
pip install -e ".[dev]"

# Verify installation
bengal --version
```

## Run Tests

```bash
# Run all tests
pytest

# Run specific test file
pytest tests/unit/test_page.py

# Run with coverage
pytest --cov=bengal
```

## Project Structure

```
bengal/
├── bengal/
│   ├── core/           # Passive data models (no I/O)
│   ├── orchestration/  # Build coordination
│   ├── rendering/      # Templates and content
│   ├── discovery/      # Content/asset discovery
│   ├── cache/          # Caching infrastructure
│   ├── health/         # Validation and checks
│   └── cli/            # Command-line interface
├── tests/
│   ├── unit/           # Fast, isolated tests
│   ├── integration/    # Multi-component tests
│   └── roots/          # Test fixtures
└── site/               # Documentation site
```

## Development Workflow

### 1. Create a Branch

```bash
git checkout -b feature/my-feature
```

### 2. Make Changes

Edit code in `bengal/`, following existing patterns.

### 3. Add Tests

Add tests in `tests/unit/` or `tests/integration/`.

### 4. Run Linters

```bash
# Format code
ruff format bengal/ tests/

# Lint
ruff check bengal/ tests/ --fix
```

### 5. Commit

```bash
git add -A && git commit -m "core: add feature description"
```

Follow the [commit message format](/docs/about/contributing/).

### 6. Push and Create PR

```bash
git push origin feature/my-feature
```

Then create a Pull Request on GitHub.

## Build the Docs Site

```bash
cd site
bengal site serve
```

Visit http://localhost:5173 to preview documentation changes.

## Key Principles

- **Core modules are passive** — No I/O, no logging in `bengal/core/`
- **Orchestration coordinates** — Build logic lives in `bengal/orchestration/`
- **Tests are essential** — All changes need tests
- **Type hints required** — Use Python type hints everywhere

## Next Steps

- **[Architecture](/docs/extending/architecture/)** — Understand Bengal's internals
- **[Testing Patterns](/docs/extending/validation/)** — Test best practices
- **[Contributing Guide](/docs/about/)** — Full contribution guidelines


