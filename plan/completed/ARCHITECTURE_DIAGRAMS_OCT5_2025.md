# ARCHITECTURE.md Diagrams Added

**Date**: October 5, 2025  
**Status**: ✅ Completed  
**Goal**: Add visual diagrams to ARCHITECTURE.md for quick developer onboarding

---

## Summary

Added 5 comprehensive Mermaid diagrams to ARCHITECTURE.md to visualize the system architecture, making it much easier for developers to quickly understand Bengal's design.

---

## Diagrams Added

### 1. High-Level Architecture (Lines 16-65)

**Type**: Graph with subgraphs  
**Location**: After "Overview" section, before "Core Components"

**Shows**:
- Entry points (CLI, Dev Server)
- Core build pipeline (Discovery → Orchestration → Rendering → Post-Process)
- Object model (Site, Pages, Sections, Assets, Menus)
- Supporting systems (Cache, Health, Autodoc, Config)
- Key relationships and data flows

**Value**: Gives developers immediate understanding of Bengal's major components and how they connect.

---

### 2. Object Model Relationships (Lines 246-314)

**Type**: Class diagram  
**Location**: End of "Object Model" section (section 1)

**Shows**:
- Site, Page, Section, Asset, Menu, MenuItem classes
- Key attributes and methods for each class
- Relationships: Site manages Pages/Sections/Assets, Section groups Pages, Pages have next/prev navigation
- Multiplicity (1:*, *:*, etc.)

**Value**: Helps developers understand the core data structures and their relationships before diving into code.

---

### 3. Build Pipeline Flow (Lines 385-433)

**Type**: Sequence diagram  
**Location**: End of "Cache System" section (section 2)

**Shows**:
- Complete build flow: CLI → Site → Discovery → Orchestration → Rendering → Post-Process
- Cache check logic during page rendering
- Parallel processing of pages and assets
- Final steps: sitemap, RSS, search index generation

**Value**: Developers can trace exactly what happens during a `bengal build` command, step by step.

---

### 4. Rendering Flow Detail (Lines 452-488)

**Type**: Flowchart  
**Location**: Start of "Rendering Pipeline" section (section 3)

**Shows**:
- Markdown file → Parse → AST
- Plugin chain (Variable Substitution → Cross-Reference → Admonitions → etc.)
- Template context building (page, site, config, 120+ functions)
- Jinja2 template engine processing
- Final HTML output

**Value**: Clarifies the two-layer processing model (Markdown plugins then Jinja2 templates) and rich context available to templates.

---

### 5. Autodoc Architecture (Lines 668-721)

**Type**: Flowchart with subgraphs  
**Location**: Start of "Autodoc System" section (section 4)

**Shows**:
- Input sources (Python source, CLI apps)
- Extraction phase (AST Parser → PythonExtractor/CLIExtractor)
- Unified DocElement data model
- Generation phase (DocumentationGenerator → Jinja2 templates)
- Output: Markdown files that feed into regular Bengal build pipeline
- Final HTML output

**Value**: Shows autodoc as a separate but integrated system that generates markdown content, which then goes through the normal build pipeline.

---

### 6. Incremental Build Cache Flow (Lines 351-385)

**Type**: Flowchart with decision logic  
**Location**: "Incremental Build Flow" subsection in Cache System

**Shows**:
- Load cache → check config → compare hashes
- Decision tree: config changed? templates changed? content changed? assets changed?
- Selective rebuild logic
- Dependency tracking during rendering
- Cache update and save

**Value**: Makes the intelligent caching system's decision logic transparent, helping developers understand why certain pages rebuild and others don't.

---

## Design Principles Used

### Color Coding
- **Blue (#e3f2fd)**: Input/starting points
- **Orange (#fff3e0 / #fff4e6)**: Processing/transformation steps
- **Green (#e8f5e9)**: Data models/successful operations
- **Purple (#f3e5f5)**: Generation/output preparation
- **Pink (#fce4ec / #ffebee)**: Final output/results
- **Yellow (#fff3e0)**: Decision points

### Diagram Types Selection
- **Graph/Flowchart**: For system architecture and flows
- **Sequence**: For time-based processes (build pipeline)
- **Class**: For object relationships
- **Flowchart with decisions**: For conditional logic (cache)

### Mermaid Benefits
- ✅ Text-based (git-friendly, easy to review)
- ✅ Renders on GitHub, GitLab, many markdown viewers
- ✅ Easy to update (no external tool needed)
- ✅ Consistent styling
- ✅ Supports complex diagrams

---

## Impact on Onboarding

**Before**: 
- New developers had to read 1500+ lines of text to understand architecture
- Relationships between components not immediately clear
- Build flow required mental model construction

**After**:
- Quick visual overview in first 100 lines
- See all components and relationships at a glance
- Trace build flow visually before reading detailed text
- Understand object model structure immediately
- Incremental build logic becomes transparent

**Estimated Time Savings**: 
- Previous onboarding: 2-3 hours to read and understand
- New onboarding: 30-45 minutes with diagrams, then selective deep reading

---

## Diagram Maintenance

**When to Update**:
1. Major architecture changes (new core component)
2. Build pipeline changes (new stage, reordering)
3. Object model changes (new class, relationship changes)
4. Cache logic changes (new decision points)
5. Autodoc system changes (new extractors)

**How to Update**:
```bash
# Edit the mermaid code directly in ARCHITECTURE.md
# Preview with GitHub or a mermaid live editor
# Test rendering with: grip ARCHITECTURE.md
```

**Tools**:
- [Mermaid Live Editor](https://mermaid.live/) - for testing complex diagrams
- GitHub preview - built-in rendering
- VS Code extensions: "Markdown Preview Mermaid Support"

---

## Related Files

- ✅ `ARCHITECTURE.md` - Updated with 5 diagrams
- ✅ `plan/ARCHITECTURE_DIAGRAMS_OCT5_2025.md` - This document
- 📋 Consider: Add diagram to README.md (high-level only)
- 📋 Consider: Add rendering pipeline diagram to template documentation

---

## Future Diagram Opportunities

1. **Health Check System**: Validator flow and error aggregation
2. **Dev Server**: File watching → change detection → incremental rebuild → browser refresh
3. **Taxonomy System**: Tag collection → dynamic page generation
4. **Menu Building**: Config + frontmatter → hierarchical menu → active state marking
5. **Theme System**: Theme discovery → asset loading → template override resolution

---

**Status**: ARCHITECTURE.md now has comprehensive visual documentation for quick developer onboarding.

