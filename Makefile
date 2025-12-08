# Bengal Makefile
# Wraps uv commands to ensure Python 3.14t is used

PYTHON_VERSION ?= 3.14t
VENV_DIR ?= .venv

.PHONY: all help setup install run build serve clean test shell typecheck typecheck-strict

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
	@echo "  make run      - Run bengal CLI (use ARGS='...' to pass arguments)"
	@echo "  make test     - Run the test suite"
	@echo "  make typecheck - Run mypy type checking"
	@echo "  make typecheck-strict - Run mypy with strict mode (for debugging)"
	@echo "  make clean    - Remove venv, build artifacts, and site output"
	@echo "  make shell    - Start a shell with the environment activated"

setup:
	@echo "Creating virtual environment with Python $(PYTHON_VERSION)..."
	uv venv --python $(PYTHON_VERSION) $(VENV_DIR)

install:
	@echo "Installing dependencies..."
	uv pip install -e ".[dev]"

build:
	@echo "Building site..."
	uv run bengal site build site

serve:
	@echo "Starting development server..."
	uv run bengal site serve site

# Example: make run ARGS="site build"
run:
	uv run bengal $(ARGS)

test:
	uv run pytest

typecheck:
	@echo "Running mypy type checking..."
	uv run mypy bengal/ --show-error-codes

typecheck-strict:
	@echo "Running mypy with strict mode (for debugging)..."
	uv run mypy bengal/ --strict --show-error-codes --show-error-context

clean:
	rm -rf $(VENV_DIR)
	rm -rf build/ dist/ *.egg-info site/public
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type d -name ".pytest_cache" -exec rm -rf {} +
	find . -type d -name ".mypy_cache" -exec rm -rf {} +
	find . -type d -name ".ruff_cache" -exec rm -rf {} +

shell:
	@echo "Activating environment with GIL disabled..."
	@bash -c 'source $(VENV_DIR)/bin/activate && export PYTHON_GIL=0 && echo "✓ venv active, GIL disabled" && exec bash'
