# Git & Testing Setup - Quick Start

**Date:** October 2, 2025

---

## 📚 Planning Documents Created

1. **`GIT_SETUP.md`** - Complete git repository setup guide
2. **`TEST_STRATEGY.md`** - Comprehensive testing strategy

---

## 🚀 Quick Start: Initialize Git

```bash
cd /Users/llane/Documents/github/python/bengal

# 1. Clean up first
rm -rf examples/quickstart/public
find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
find . -type f -name "*.pyc" -delete

# 2. Create CHANGELOG
cat > CHANGELOG.md << 'EOF'
# Changelog

All notable changes to Bengal SSG.

## [0.1.0] - 2025-10-02

### Added
- Initial release
- Core SSG functionality (Site, Page, Section, Asset)
- Rendering pipeline with Jinja2
- Markdown parsing
- CLI tools (build, serve, clean, new)
- Development server with hot reload
- Production-ready default theme
- Pagination system
- Taxonomy support (tags, categories)
- Breadcrumb navigation
- 404 error page

[0.1.0]: https://github.com/YOUR_USERNAME/bengal/releases/tag/v0.1.0
EOF

# 3. Initialize git
git init
git branch -M main

# 4. Initial commit
git add .
git commit -m "feat: initial Bengal SSG implementation

Complete static site generator with:
- Modular architecture (Site, Page, Section, Asset)
- Rendering pipeline with Jinja2
- Markdown parsing with extensions
- CLI interface (build, serve, clean, new)
- Development server with hot reload
- Configuration system (TOML/YAML)
- Post-processing (sitemap, RSS)
- Production-ready default theme with pagination
- Taxonomy support (tags, categories)
- Comprehensive documentation

Version: 0.1.0
"

# 5. Tag v0.1.0
git tag -a v0.1.0 -m "Initial release - MVP complete"

# 6. Create GitHub repo and push
# (Do this on GitHub first)
git remote add origin https://github.com/YOUR_USERNAME/bengal.git
git push -u origin main --tags
```

---

## 🧪 Quick Start: Set Up Testing

```bash
# 1. Install test dependencies
pip install -e ".[dev]"  # After adding [dev] to pyproject.toml

# Or install individually:
pip install pytest pytest-cov pytest-mock pytest-xdist ruff mypy

# 2. Create test directory
mkdir -p tests/{unit,integration,e2e,performance,fixtures}
mkdir -p tests/unit/{core,rendering,discovery,utils,config,postprocess}

# 3. Create conftest.py
# (See TEST_STRATEGY.md for content)

# 4. Write your first test
# See TEST_STRATEGY.md for examples

# 5. Run tests
pytest                           # All tests
pytest --cov=bengal              # With coverage
pytest -v                        # Verbose
pytest -n auto                   # Parallel
```

---

## 📊 Testing Progress

**Target: 85% overall coverage**

Start with these priorities:
1. ✅ Core components (Page, Site) - 90%+ target
2. ✅ Pagination utility - 95%+ target  
3. ✅ Rendering pipeline - 85%+ target
4. ⏳ CLI commands - 80%+ target
5. ⏳ Integration tests
6. ⏳ Performance benchmarks

---

## 🔧 Add to pyproject.toml

```toml
[project.optional-dependencies]
dev = [
    "pytest>=7.4.0",
    "pytest-cov>=4.1.0",
    "pytest-mock>=3.11.0",
    "pytest-xdist>=3.3.0",
    "ruff>=0.1.0",
    "mypy>=1.5.0",
    "black>=23.7.0",
]

[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = "test_*.py"
addopts = "--cov=bengal --cov-report=html --cov-report=term-missing"

[tool.coverage.run]
source = ["bengal"]

[tool.coverage.report]
fail_under = 85
exclude_lines = [
    "pragma: no cover",
    "def __repr__",
    "raise NotImplementedError",
    "if __name__ == .__main__.:",
    "if TYPE_CHECKING:",
]

[tool.ruff]
line-length = 100
target-version = "py310"

[tool.mypy]
python_version = "3.10"
warn_return_any = true
warn_unused_configs = true
```

---

## 📁 File Cleanup Before Git Init

**Keep:**
- All code files (`bengal/`)
- Core docs (README, LICENSE, CONTRIBUTING, ARCHITECTURE)
- Examples (without public/ output)
- pyproject.toml, requirements.txt

**Move to plan/completed/:**
- PHASE_2_ANALYSIS.md
- PHASE_2B_COMPLETE.md
- THEME_PLANNING.md (duplicate at root)

**Consider consolidating:**
- Multiple status/summary docs at root
- Keep one "getting started" guide

---

## ✅ Pre-Commit Checklist

Before your first commit:
- [ ] Review .gitignore is complete
- [ ] Remove all `public/` and `__pycache__/` directories
- [ ] Create CHANGELOG.md
- [ ] Version is 0.1.0 in pyproject.toml
- [ ] README has project description
- [ ] LICENSE file exists
- [ ] All docs are up to date

After git init:
- [ ] Create GitHub repository
- [ ] Push code and tags
- [ ] Add description and topics to GitHub repo
- [ ] Consider adding badges to README

---

## 🎯 Next Steps

### Option 1: Git First
1. Initialize git (see commands above)
2. Push to GitHub
3. Set up CI/CD (GitHub Actions)
4. Then add tests incrementally

### Option 2: Tests First
1. Set up test infrastructure
2. Write core tests (Page, Site, Paginator)
3. Get to 85% coverage
4. Then initialize git with tests included

### Option 3: Both Together (Recommended)
1. Initialize git with current code
2. Create first commit (v0.1.0)
3. Create feature branch for tests
4. Implement tests in phases
5. Merge when coverage target met

---

## 📖 Full Documentation

See the complete planning documents:
- **`plan/GIT_SETUP.md`** - 400+ lines of git strategy
- **`plan/TEST_STRATEGY.md`** - 700+ lines of test planning

Both documents include:
- Detailed workflows
- Code examples
- Best practices
- Checklists

---

**Ready to start? Pick an option above and begin!**

