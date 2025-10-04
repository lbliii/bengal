# Bengal vs Sphinx: Implementation Next Steps

**Date**: October 4, 2025  
**Status**: Ready to Implement  
**Goal**: Ship v0.3.0 "API Documentation Release"

---

## What We've Designed

### 1. Strategic Analysis
- **File**: `SPHINX_COMPETITIVE_STRATEGY.md` (40 pages)
- **Verdict**: You're 85% of the way there. Missing piece is autodoc.
- **Opportunity**: Ship AST-based autodoc → beat Sphinx at its own game

### 2. Unified Autodoc Architecture
- **File**: `UNIFIED_AUTODOC_ARCHITECTURE.md`
- **Key Insight**: Python, OpenAPI, and CLI docs should share infrastructure
- **Architecture**: Pluggable extractors → unified templates → Bengal pipeline
- **Competitive Advantage**: No other tool does unified documentation

### 3. Python Autodoc Implementation
- **File**: `AUTODOC_IMPLEMENTATION_PLAN.md` (comprehensive spec)
- **Timeline**: 3-4 weeks
- **Innovation**: AST-based (no imports) vs Sphinx's fragile import-based
- **Features**: 
  - Full template customization (templates/autodoc/, templates/api/, templates/sdk/)
  - Cross-reference system ([[ClassName.method]])
  - Google/NumPy/Sphinx docstring support
  - Sphinx migration tool

### 4. Versioned Documentation
- **File**: `VERSIONED_DOCS_IMPLEMENTATION_PLAN.md`
- **Timeline**: 1-2 weeks
- **Features**: 
  - Multi-version builds from git
  - Version selector UI
  - SEO (canonical URLs)
  - Warning banners

---

## Your Question: Template Customization

> "Can we offer users template-based customization? Like if they define templates/api or templates/sdk or templates/autodoc they will be able to define the layout system?"

**Answer**: Yes, and I've designed it comprehensively!

### Template Hierarchy

Users can customize at multiple levels:

```
templates/
├── autodoc/          # Autodoc-specific templates (priority 1)
│   ├── python/       # Python-specific
│   │   ├── module.md
│   │   ├── class.md
│   │   └── function.md
│   ├── openapi/      # OpenAPI-specific
│   │   ├── endpoint.md
│   │   └── schema.md
│   └── cli/          # CLI-specific
│       └── command.md
│
├── api/              # Alternative location (priority 2)
│   └── class.md
│
└── sdk/              # Alternative location (priority 3)
    └── class.md
```

### Template Lookup Order

For a Python class, Bengal looks for:
1. `templates/autodoc/python/class.md`
2. `templates/autodoc/class.md`
3. `templates/api/class.md`
4. `templates/sdk/class.md`
5. Built-in default

**Users control everything.**

### Template Context

Templates receive rich context:

```jinja2
<!-- templates/autodoc/python/class.md -->
---
title: "{{ element.name }}"
---

# {{ element.name }}

{{ element.description }}

**Source:** [{{ element.source_file }}]({{ source_link(element) }})

## Methods

{% for method in element.children %}
### {{ method.name }}

```python
{{ method.metadata.signature }}
```

{{ method.description }}

{% if method.metadata.args %}
**Parameters:**
{% for arg_name, arg_desc in method.metadata.args.items() %}
- `{{ arg_name }}`: {{ arg_desc }}
{% endfor %}
{% endif %}

{% endfor %}
```

### Custom Filters & Functions

```python
# In user's site config or hook
autodoc.templates.register_filter('format_signature', my_formatter)
autodoc.templates.register_function('extract_example', my_example_extractor)
```

**Full Jinja2 power + custom extensions.**

---

## Implementation Roadmap

### Phase 1: Core Autodoc (Weeks 1-3)

#### Week 1: AST Extraction
- [ ] Base `Extractor` interface and `DocElement` model
- [ ] `PythonExtractor` with AST parsing
- [ ] Docstring parsers (Google/NumPy/Sphinx)
- [ ] Tests

#### Week 2: Templates & Customization
- [ ] Template loading system (hierarchy)
- [ ] Default templates (module, class, function)
- [ ] Markdown generation
- [ ] Configuration system
- [ ] Template customization API
- [ ] Tests

#### Week 3: Cross-References & Polish
- [ ] Cross-reference resolver
- [ ] Mistune plugin for [[refs]]
- [ ] Broken reference validation
- [ ] Source code links
- [ ] Coverage reporting
- [ ] Documentation

### Phase 2: Versioning & Launch (Week 4)

#### Week 4: Versioned Docs + Launch
- [ ] VersionManager implementation
- [ ] Version selector UI
- [ ] SEO (canonical URLs)
- [ ] Warning banners
- [ ] Sphinx migration tool
- [ ] API docs theme preset
- [ ] Ship v0.3.0

---

## Deliverables: v0.3.0 "API Documentation Release"

### Core Features
✅ **Python Autodoc**
- AST-based extraction (no imports!)
- Google/NumPy/Sphinx docstring support
- Full template customization
- Cross-reference system
- Sphinx migration tool

✅ **Versioned Documentation**
- Multi-version builds
- Version selector UI
- SEO-friendly
- Git integration

✅ **Unified Architecture**
- Pluggable extractors (foundation for OpenAPI/CLI)
- Shared template system
- Cross-type references

### Templates Included
- `autodoc/python/module.md`
- `autodoc/python/class.md`
- `autodoc/python/function.md`
- `autodoc/index.md`
- API documentation theme preset

### CLI Commands
```bash
# Generate Python API docs
$ bengal autodoc

# With watch mode
$ bengal autodoc --watch

# Build all versions
$ bengal build --versioned

# Migrate from Sphinx
$ bengal migrate --from-sphinx

# Show API coverage
$ bengal autodoc --coverage
```

---

## What Makes This Win Against Sphinx

### 1. Technical Superiority

| Feature | Sphinx | Bengal |
|---------|--------|--------|
| **Extraction** | Import-based (fragile) | AST-based (reliable) |
| **Speed** | Slow imports | Fast parsing |
| **CI/CD** | Breaks often | Never breaks |
| **Mocking** | `autodoc_mock_imports` hacks | Not needed |
| **Type Hints** | Poor support | Full support |

### 2. Better DX

| Feature | Sphinx | Bengal |
|---------|--------|--------|
| **Format** | RST + conf.py | Markdown + TOML |
| **Templates** | Fragmented Jinja | Full customization |
| **Errors** | Cryptic | Helpful + health checks |
| **Dev Server** | None | Hot reload |
| **Versioning** | Manual, painful | One command |

### 3. Unified Platform

Sphinx only does Python. Bengal does:
- ✅ Python API docs
- ✅ CLI docs (self-documents Bengal!)
- ✅ OpenAPI docs (FastAPI integration)
- ✅ All with cross-references

**No other tool does this.**

---

## Post-v0.3.0 Roadmap

### v0.4.0: CLI Autodoc (2-3 weeks)
- CLI extractor (Click/argparse/typer)
- Self-document Bengal's CLI
- Templates for commands/options
- Man page generation

### v0.5.0: OpenAPI Autodoc (2-3 weeks)
- OpenAPI extractor
- FastAPI/Flask integration
- Endpoint + schema templates
- Try-it-out widgets

### v0.6.0: Advanced Features
- Inherited member documentation
- Type checking integration (mypy)
- Stub file generation
- Search integration
- Coverage dashboard

---

## Launch Strategy

### Pre-Launch (Week 4)
- [ ] Ship v0.3.0
- [ ] Write announcement blog post
- [ ] Create comparison demos
- [ ] Document migration path

### Launch (Week 5)
- [ ] Show HN: "Bengal - Python docs without the pain"
- [ ] Reddit r/Python
- [ ] Python Weekly
- [ ] Tweet thread with demos

### Post-Launch (Week 6+)
- [ ] Migrate 3-5 example projects
- [ ] Find early adopters
- [ ] Collect feedback
- [ ] Iterate

---

## Success Criteria

### 6 Months
- ✅ 100 GitHub stars
- ✅ 50 projects using Bengal for docs
- ✅ 10 migration case studies
- ✅ Featured on Python Weekly

### 12 Months
- ✅ 1,000 stars
- ✅ 500 projects
- ✅ 1+ popular library (10K+ stars) migrated
- ✅ "Recommended for new Python projects"

---

## The Pitch (Final Version)

> **Tired of fighting Sphinx?**
> 
> Bengal gives you Python API docs without the pain.
> 
> ✅ **No import gymnastics**: AST-based extraction  
> ✅ **No conf.py**: Simple TOML configuration  
> ✅ **No slow builds**: 10x faster with incremental caching  
> ✅ **No cryptic errors**: Helpful diagnostics + health checks  
> ✅ **Full customization**: Your templates, your style  
> 
> **Migrate from Sphinx in 5 minutes:**
> ```bash
> $ bengal migrate --from-sphinx
> $ bengal autodoc
> $ bengal build
> ```
> 
> Same API docs. 10x better experience.
> 
> [Try Bengal →]

---

## Risk Assessment

### Low Risk ✅
- **AST parsing**: Well-understood, standard Python
- **Template system**: Jinja2 (proven)
- **Market need**: Clear pain points
- **Timeline**: 4 weeks is achievable

### Managed Risks ⚠️
- **Feature gap**: Focus on 80% use case first
- **Dynamic code**: AST + optional import fallback
- **Adoption**: Migration tool reduces friction
- **Community**: Show, don't tell

---

## Next Actions

### This Week (October 7-11)
1. **Review** these specs with team/stakeholders
2. **Decide** on timeline commitment
3. **Setup** project tracking (GitHub issues/project board)
4. **Start** Week 1: Base classes + PythonExtractor

### Decision Points
- [ ] Approve overall strategy?
- [ ] Approve 4-week timeline?
- [ ] Approve unified architecture (Python + OpenAPI + CLI)?
- [ ] Any concerns or changes?

---

## Files Created

1. `SPHINX_COMPETITIVE_STRATEGY.md` - Strategic analysis (40 pages)
2. `SPHINX_STRATEGY_SUMMARY.md` - Executive summary
3. `AUTODOC_IMPLEMENTATION_PLAN.md` - Detailed Python autodoc spec
4. `UNIFIED_AUTODOC_ARCHITECTURE.md` - Multi-type autodoc design
5. `VERSIONED_DOCS_IMPLEMENTATION_PLAN.md` - Versioning spec
6. `SPHINX_STRATEGY_NEXT_STEPS.md` - This file

**All specs are implementation-ready.**

---

## Questions to Answer

1. **Timeline**: Can we commit 4 weeks to ship v0.3.0?
2. **Scope**: Ship Python autodoc + versioning in v0.3.0, or split?
3. **Migration**: Priority on Sphinx migration tool?
4. **CLI**: Self-document Bengal's CLI in v0.3.0 or v0.4.0?
5. **Launch**: Who handles marketing/community outreach?

---

## The Bottom Line

**You have a complete implementation plan to beat Sphinx.**

- ✅ Strategic positioning clear
- ✅ Technical approach superior
- ✅ Timeline achievable (4 weeks)
- ✅ Templates fully customizable
- ✅ Migration path defined
- ✅ Competitive advantage strong

**Ship autodoc. Own Python documentation.**

The rest takes care of itself.

---

*Ready to start Week 1? Let's build this.*

