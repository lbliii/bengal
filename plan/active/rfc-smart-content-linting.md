# RFC: Smart Content Linting

**Status**: Draft  
**Created**: 2025-12-08  
**Author**: AI Assistant  
**Confidence**: 85% 🟢

---

## Executive Summary

Extend Bengal's health checks from "is this broken?" to "is this good?" Add content-aware linting that catches orphan pages, SEO conflicts, deprecated API references, version mismatches, and stale content—issues that syntax checkers miss.

---

## Problem Statement

### Current State

Bengal's health checks validate:
- Broken internal links
- Missing images
- Frontmatter schema compliance
- Template errors

**Evidence**:
- `bengal/health/validators/`: Link checker, schema validator
- `bengal/health/checks/`: Build health checks

What's missing:
- Content quality analysis
- SEO issue detection
- Cross-reference validation against actual code
- Freshness/staleness detection

### Pain Points

1. **Orphan pages**: Pages with no incoming links (undiscoverable)
2. **SEO conflicts**: Multiple pages targeting same keywords
3. **Stale content**: Docs reference deprecated APIs
4. **Version drift**: Docs say "v1.0" but site is on "v2.0"
5. **Duplicate content**: Same information in multiple places
6. **Missing coverage**: API endpoints without documentation

### User Impact

Documentation accumulates quality issues invisibly. By the time users complain, the problems are systemic. Reactive fixes are expensive; proactive detection is cheap.

---

## Goals & Non-Goals

**Goals**:
- Detect content quality issues automatically
- Validate docs against source code (when available)
- Identify SEO problems before they hurt rankings
- Track content freshness and flag staleness
- Integrate with CI/CD for quality gates

**Non-Goals**:
- Spell checking (use dedicated tools)
- Grammar checking (use Grammarly, etc.)
- Style enforcement (use Vale or similar)
- Auto-fixing issues (report only, for now)

---

## Architecture Impact

**Affected Subsystems**:
- **Health** (`bengal/health/`): New linter validators
- **Analysis** (`bengal/analysis/`): Leverage knowledge graph
- **CLI** (`bengal/cli/`): Enhanced validate command
- **Config** (`bengal/config/`): Linting rules configuration

**New Components**:
- `bengal/health/linters/` - Content linting rules
- `bengal/health/linters/orphan.py` - Orphan page detection
- `bengal/health/linters/seo.py` - SEO issue detection
- `bengal/health/linters/freshness.py` - Staleness detection
- `bengal/health/linters/code_sync.py` - Code reference validation

---

## Proposed Linting Rules

### 1. Orphan Detection

**Rule**: Pages with no incoming links are orphans.

```python
# bengal/health/linters/orphan.py

class OrphanLinter(Linter):
    """Detect pages with no incoming links."""
    
    id = "orphan-pages"
    severity = "warning"
    
    def lint(self, site: Site) -> list[LintIssue]:
        issues = []
        
        # Build incoming link map
        incoming: dict[str, set[str]] = defaultdict(set)
        for page in site.pages:
            for link in page.internal_links:
                incoming[link.target].add(page.path)
        
        # Find orphans (excluding index pages)
        for page in site.pages:
            if page.is_index:
                continue
            
            # Check incoming links
            if not incoming.get(page.path):
                # Also check if in navigation
                if not self._in_navigation(page, site):
                    issues.append(LintIssue(
                        rule=self.id,
                        severity=self.severity,
                        path=page.path,
                        message="Page has no incoming links (orphan)",
                        suggestion="Add links from related pages or include in navigation",
                        metadata={"incoming_count": 0},
                    ))
        
        return issues
```

### 2. SEO Conflicts

**Rule**: Multiple pages shouldn't target the same primary keyword/title.

```python
# bengal/health/linters/seo.py

class SEOConflictLinter(Linter):
    """Detect SEO conflicts between pages."""
    
    id = "seo-conflicts"
    severity = "warning"
    
    def lint(self, site: Site) -> list[LintIssue]:
        issues = []
        
        # Group pages by title similarity
        title_groups = self._group_by_similarity(
            [(p, p.title) for p in site.pages],
            threshold=0.85,  # 85% similar
        )
        
        for pages in title_groups:
            if len(pages) > 1:
                issues.append(LintIssue(
                    rule=self.id,
                    severity=self.severity,
                    path=pages[0].path,
                    message=f"Title too similar to {len(pages)-1} other page(s)",
                    suggestion="Differentiate titles for better SEO",
                    metadata={
                        "similar_pages": [p.path for p in pages[1:]],
                        "titles": [p.title for p in pages],
                    },
                ))
        
        # Check for duplicate meta descriptions
        desc_map: dict[str, list[Page]] = defaultdict(list)
        for page in site.pages:
            if page.description:
                desc_map[page.description.lower()].append(page)
        
        for desc, pages in desc_map.items():
            if len(pages) > 1:
                issues.append(LintIssue(
                    rule=self.id,
                    severity="warning",
                    path=pages[0].path,
                    message=f"Duplicate meta description with {len(pages)-1} other page(s)",
                    suggestion="Write unique descriptions for each page",
                    metadata={"duplicate_pages": [p.path for p in pages]},
                ))
        
        return issues
```

### 3. Freshness/Staleness

**Rule**: Content not updated in N months may be stale.

```python
# bengal/health/linters/freshness.py

class FreshnessLinter(Linter):
    """Detect potentially stale content."""
    
    id = "stale-content"
    severity = "info"
    
    def __init__(self, stale_threshold_days: int = 180):
        self.stale_threshold = timedelta(days=stale_threshold_days)
    
    def lint(self, site: Site) -> list[LintIssue]:
        issues = []
        now = datetime.now()
        
        for page in site.pages:
            # Check last modified date
            last_modified = page.last_modified or page.date
            if not last_modified:
                continue
            
            age = now - last_modified
            
            if age > self.stale_threshold:
                # Check if page has high traffic (more important to update)
                importance = self._calculate_importance(page, site)
                
                severity = "warning" if importance > 0.7 else "info"
                
                issues.append(LintIssue(
                    rule=self.id,
                    severity=severity,
                    path=page.path,
                    message=f"Content not updated in {age.days} days",
                    suggestion="Review for accuracy and update if needed",
                    metadata={
                        "last_modified": last_modified.isoformat(),
                        "age_days": age.days,
                        "importance_score": importance,
                    },
                ))
        
        return issues
    
    def _calculate_importance(self, page: Page, site: Site) -> float:
        """Calculate page importance based on links and position."""
        # Incoming links indicate importance
        incoming_count = len(site.get_incoming_links(page))
        max_incoming = max(len(site.get_incoming_links(p)) for p in site.pages)
        
        link_score = incoming_count / max(max_incoming, 1)
        
        # Top-level pages are more important
        depth_score = 1 / (page.depth + 1)
        
        return (link_score + depth_score) / 2
```

### 4. Code Sync Validation

**Rule**: Code references in docs should match actual source code.

```python
# bengal/health/linters/code_sync.py

class CodeSyncLinter(Linter):
    """Validate code references against source code."""
    
    id = "code-sync"
    severity = "error"
    
    def __init__(self, source_dirs: list[Path]):
        self.source_dirs = source_dirs
        self.code_index = self._build_code_index()
    
    def lint(self, site: Site) -> list[LintIssue]:
        issues = []
        
        for page in site.pages:
            # Extract code references from content
            refs = self._extract_code_refs(page)
            
            for ref in refs:
                if ref.type == "function":
                    if not self._function_exists(ref.name, ref.module):
                        issues.append(LintIssue(
                            rule=self.id,
                            severity=self.severity,
                            path=page.path,
                            line=ref.line,
                            message=f"Function '{ref.name}' not found in source code",
                            suggestion="Update reference or check function name",
                            metadata={"reference": ref.raw},
                        ))
                
                elif ref.type == "class":
                    if not self._class_exists(ref.name, ref.module):
                        issues.append(LintIssue(
                            rule=self.id,
                            severity=self.severity,
                            path=page.path,
                            line=ref.line,
                            message=f"Class '{ref.name}' not found in source code",
                            suggestion="Update reference or check class name",
                        ))
                
                elif ref.type == "config":
                    if not self._config_option_exists(ref.name):
                        issues.append(LintIssue(
                            rule=self.id,
                            severity="warning",
                            path=page.path,
                            line=ref.line,
                            message=f"Config option '{ref.name}' may not exist",
                            suggestion="Verify config option name",
                        ))
        
        return issues
    
    def _extract_code_refs(self, page: Page) -> list[CodeReference]:
        """Extract code references from page content."""
        refs = []
        
        # Inline code that looks like function calls
        for match in re.finditer(r'`(\w+)\(\)`', page.content):
            refs.append(CodeReference(
                type="function",
                name=match.group(1),
                raw=match.group(0),
                line=page.content[:match.start()].count('\n') + 1,
            ))
        
        # Class references (CamelCase in backticks)
        for match in re.finditer(r'`([A-Z][a-zA-Z]+)`', page.content):
            refs.append(CodeReference(
                type="class",
                name=match.group(1),
                raw=match.group(0),
                line=page.content[:match.start()].count('\n') + 1,
            ))
        
        # Config options (snake_case in backticks)
        for match in re.finditer(r'`([a-z][a-z_]+)`', page.content):
            refs.append(CodeReference(
                type="config",
                name=match.group(1),
                raw=match.group(0),
                line=page.content[:match.start()].count('\n') + 1,
            ))
        
        return refs
```

### 5. Version Mismatch

**Rule**: Docs should reference the current product version.

```python
# bengal/health/linters/version.py

class VersionLinter(Linter):
    """Detect version mismatches in content."""
    
    id = "version-mismatch"
    severity = "warning"
    
    def __init__(self, current_version: str, deprecated_versions: list[str]):
        self.current_version = current_version
        self.deprecated_versions = deprecated_versions
    
    def lint(self, site: Site) -> list[LintIssue]:
        issues = []
        
        version_pattern = re.compile(r'v?(\d+\.\d+(?:\.\d+)?)')
        
        for page in site.pages:
            for match in version_pattern.finditer(page.content):
                version = match.group(1)
                
                if version in self.deprecated_versions:
                    issues.append(LintIssue(
                        rule=self.id,
                        severity="warning",
                        path=page.path,
                        line=page.content[:match.start()].count('\n') + 1,
                        message=f"References deprecated version '{version}'",
                        suggestion=f"Update to current version '{self.current_version}'",
                        metadata={
                            "found_version": version,
                            "current_version": self.current_version,
                        },
                    ))
        
        return issues
```

### 6. Coverage Analysis

**Rule**: All public APIs should have documentation.

```python
# bengal/health/linters/coverage.py

class CoverageLinter(Linter):
    """Check documentation coverage of public APIs."""
    
    id = "api-coverage"
    severity = "warning"
    
    def __init__(self, api_source: Path):
        self.api_source = api_source
        self.public_apis = self._discover_public_apis()
    
    def lint(self, site: Site) -> list[LintIssue]:
        issues = []
        
        # Find documented APIs
        documented = set()
        for page in site.pages:
            if page.section.path.startswith("api/"):
                # Extract API references from page
                documented.update(self._extract_documented_apis(page))
        
        # Find undocumented APIs
        undocumented = self.public_apis - documented
        
        for api in undocumented:
            issues.append(LintIssue(
                rule=self.id,
                severity=self.severity,
                path="(missing)",
                message=f"Public API '{api}' has no documentation",
                suggestion=f"Create documentation for {api}",
                metadata={"api": api},
            ))
        
        # Summary issue
        coverage = len(documented) / len(self.public_apis) * 100
        if coverage < 80:
            issues.append(LintIssue(
                rule=self.id,
                severity="warning",
                path="(summary)",
                message=f"API documentation coverage is {coverage:.0f}%",
                suggestion="Document remaining public APIs",
                metadata={
                    "coverage_percent": coverage,
                    "documented_count": len(documented),
                    "total_count": len(self.public_apis),
                },
            ))
        
        return issues
```

---

## CLI Interface

### Basic Linting

```bash
bengal lint

# Output:
# 
# 🔍 Content Lint Results
# 
# ❌ Errors: 2
#   docs/api/deprecated.md:45 - Function 'old_api()' not found in source
#   docs/api/removed.md:12 - Class 'RemovedClass' not found in source
# 
# ⚠️ Warnings: 5
#   docs/hidden-guide.md - Page has no incoming links (orphan)
#   docs/setup.md - Title too similar to "docs/installation.md"
#   docs/old-feature.md - Content not updated in 245 days
#   docs/config.md:78 - References deprecated version '1.0'
#   (summary) - API documentation coverage is 72%
# 
# ℹ️ Info: 3
#   docs/advanced/edge-cases.md - Content not updated in 190 days
#   ...
# 
# Summary: 2 errors, 5 warnings, 3 info
```

### Specific Rules

```bash
# Run only specific linters
bengal lint --rules orphan-pages,seo-conflicts

# Exclude rules
bengal lint --exclude stale-content

# Set severity threshold
bengal lint --min-severity warning
```

### CI Integration

```bash
# Exit with error code if issues found
bengal lint --strict

# Output JSON for CI parsing
bengal lint --format json

# Generate report file
bengal lint --output lint-report.json
```

### Interactive Fixing

```bash
# Show suggestions with quick actions
bengal lint --interactive

# Output:
# 
# [1/5] docs/hidden-guide.md
#   ⚠️ Page has no incoming links (orphan)
#   
#   Suggestions:
#   [a] Add to navigation (docs/_index.md)
#   [l] Show pages that could link here
#   [s] Skip
#   [q] Quit
#   
#   Choice: a
#   ✅ Added to docs/_index.md navigation
```

---

## Configuration

```toml
# bengal.toml
[lint]
# Enable/disable specific rules
rules = [
    "orphan-pages",
    "seo-conflicts",
    "stale-content",
    "code-sync",
    "version-mismatch",
    "api-coverage",
]

# Exclude rules
exclude_rules = []

# Severity threshold for CI failure
fail_on = "error"  # or "warning"

# Rule-specific configuration
[lint.stale-content]
threshold_days = 180
ignore_paths = ["changelog/**", "archive/**"]

[lint.code-sync]
source_dirs = ["src/", "lib/"]
ignore_patterns = ["test_*", "*_test"]

[lint.version-mismatch]
current_version = "2.0"
deprecated_versions = ["1.0", "1.1"]

[lint.api-coverage]
api_source = "src/api/"
minimum_coverage = 80
```

---

## Implementation Plan

### Phase 1: Core Infrastructure (1 week)
- [ ] Linter base class and registry
- [ ] Issue collection and reporting
- [ ] CLI integration

### Phase 2: Basic Linters (2 weeks)
- [ ] Orphan page detection
- [ ] SEO conflict detection
- [ ] Freshness/staleness detection

### Phase 3: Advanced Linters (2 weeks)
- [ ] Code sync validation
- [ ] Version mismatch detection
- [ ] API coverage analysis

### Phase 4: Polish (1 week)
- [ ] Interactive mode
- [ ] CI integration
- [ ] Configuration system

---

## Success Criteria

- [ ] Orphan pages detected with 100% accuracy
- [ ] SEO conflicts flagged for similar titles
- [ ] Code references validated against source
- [ ] <10s lint time for 1000-page site
- [ ] CI exit codes work correctly

---

## References

- [Vale (Prose Linter)](https://vale.sh/)
- [markdownlint](https://github.com/DavidAnson/markdownlint)
- [Lighthouse SEO Audits](https://developer.chrome.com/docs/lighthouse/seo/)
- [Documentation Coverage Tools](https://coverage.readthedocs.io/)



