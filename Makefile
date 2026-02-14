# Bengal Makefile (Legacy)
# =============================================================================
# PREFERRED: Use `poe <task>` instead (poethepoet)
# Run `poe --help` to see all available tasks
# =============================================================================
# This Makefile is kept for compatibility but poe is the preferred task runner.
# Wraps uv commands to ensure Python 3.14t is used

PYTHON_VERSION ?= 3.14t
VENV_DIR ?= .venv

.PHONY: all help setup install run build serve clean test shell ty deploy-test dist publish release gh-release

all: help

help:
	@echo "Bengal Development CLI"
	@echo "======================"
	@echo "Python Version: $(PYTHON_VERSION)"
	@echo ""
	@echo "Available commands:"
	@echo "  make setup    - Create virtual environment with Python $(PYTHON_VERSION)"
	@echo "  make install  - Install dependencies in development mode"
	@echo "  make build    - Build the documentation site (site/)"
	@echo "  make serve    - Start the development server for site/"
	@echo "  make deploy-test - Build production & serve (simulates GitHub Pages)"
	@echo "  make run      - Run bengal CLI (use ARGS='...' to pass arguments)"
	@echo "  make test     - Run the test suite"
	@echo "  make ty        - Run ty type checker (fast, Rust-based)"
	@echo "  make dist     - Build distribution packages"
	@echo "  make publish  - Publish to PyPI (uses .env for token)"
	@echo "  make release  - Build and publish in one step"
	@echo "  make gh-release - Create GitHub release (triggers PyPI via workflow), uses site release notes"
	@echo "  make clean    - Remove venv, build artifacts, and site output"
	@echo "  make shell    - Start a shell with the environment activated"

setup:
	@echo "Creating virtual environment with Python $(PYTHON_VERSION)..."
	uv venv --python $(PYTHON_VERSION) $(VENV_DIR)

install:
	@echo "Installing dependencies..."
	@if [ ! -d "$(VENV_DIR)" ]; then \
		echo "Error: $(VENV_DIR) not found. Run 'make setup' first."; \
		exit 1; \
	fi
	@bash -c 'source "$(VENV_DIR)/bin/activate" && uv sync --active --group dev --frozen'

build:
	@echo "Building site..."
	uv run bengal site build site

serve:
	@echo "Starting development server..."
	uv run bengal site serve site

deploy-test:
	@echo "Building with production config (simulates GitHub Pages)..."
	cd site && uv run bengal build -e production
	@echo ""
	@echo "Verifying CSS exists..."
	@ls -la site/public/assets/css/style.css || (echo "ERROR: CSS not found!" && exit 1)
	@echo ""
	@echo "Starting server at http://localhost:8000/bengal/"
	@echo "Press Ctrl+C to stop"
	cd site/public && python3 -m http.server 8000

# Example: make run ARGS="site build"
run:
	uv run bengal $(ARGS)

test:
	uv run pytest

ty:
	@echo "Running ty type checker (Astral, Rust-based)..."
	uv run ty check bengal/

# =============================================================================
# Build & Release
# =============================================================================

dist:
	@echo "Building distribution packages..."
	rm -rf dist/
	uv build
	@echo "✓ Built:"
	@ls -la dist/

publish:
	@echo "Publishing to PyPI..."
	@if [ -f .env ]; then \
		export $$(cat .env | xargs) && uv publish; \
	else \
		echo "Warning: No .env file found, trying without token..."; \
		uv publish; \
	fi

release: dist publish
	@echo "✓ Release complete"

# Create GitHub release from site release notes; triggers python-publish workflow → PyPI
# Strips YAML frontmatter (--- ... ---) from notes before passing to gh
gh-release:
	@VERSION=$$(grep '^version = ' pyproject.toml | sed 's/version = "\(.*\)"/\1/'); \
	PROJECT=$$(grep '^name = ' pyproject.toml | sed 's/name = "\(.*\)"/\1/'); \
	NOTES="site/content/releases/$$VERSION.md"; \
	if [ ! -f "$$NOTES" ]; then echo "Error: $$NOTES not found"; exit 1; fi; \
	echo "Creating release v$$VERSION for $$PROJECT..."; \
	git push origin main 2>/dev/null || true; \
	git push origin v$$VERSION 2>/dev/null || true; \
	awk '/^---$$/{c++;next}c>=2' "$$NOTES" | gh release create v$$VERSION \
		--title "$$PROJECT $$VERSION" \
		-F -; \
	echo "✓ GitHub release v$$VERSION created (PyPI publish will run via workflow)"

# =============================================================================
# Cleanup
# =============================================================================

clean:
	rm -rf $(VENV_DIR)
	rm -rf build/ dist/ *.egg-info site/public
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type d -name ".pytest_cache" -exec rm -rf {} +
	find . -type d -name ".ruff_cache" -exec rm -rf {} +
	find . -type d -name ".ty_cache" -exec rm -rf {} +

shell:
	@echo "Activating environment with GIL disabled..."
	@bash -c 'source $(VENV_DIR)/bin/activate && export PYTHON_GIL=0 && echo "✓ venv active, GIL disabled" && exec bash'
