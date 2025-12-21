---
title: Debug Tools
description: Diagnostic utilities for understanding builds and debugging issues
weight: 80
category: subsystems
tags:
- subsystems
- debug
- diagnostics
- troubleshooting
keywords:
- debug tools
- diagnostics
- troubleshooting
- build analysis
- incremental builds
---

# Debug Tools

Bengal's Debug Tools provide diagnostic utilities for understanding how pages are built, analyzing dependencies, and debugging incremental build issues.

## Overview

The debug system provides a framework for building diagnostic tools that analyze builds, explain behavior, and help troubleshoot issues.

```python
from bengal.debug import PageExplainer, IncrementalBuildDebugger

# Explain how a page is built
explainer = PageExplainer(site=site)
explanation = explainer.explain_page(page_path)
print(explanation.format())

# Debug incremental build issues
debugger = IncrementalBuildDebugger(site=site, cache=cache)
report = debugger.analyze()
print(report.format_summary())
```

## Architecture

```mermaid
graph TB
    subgraph "Debug Tools"
        Explainer[PageExplainer]
        Incremental[IncrementalBuildDebugger]
        Delta[BuildDeltaAnalyzer]
        Dependency[DependencyVisualizer]
        Config[ConfigInspector]
        Migrator[ContentMigrator]
    end

    subgraph "Debug Infrastructure"
        Base[DebugTool<br/>Base Class]
        Registry[DebugRegistry]
        Report[DebugReport]
    end

    subgraph "Data Sources"
        Site[Site Object]
        Cache[Build Cache]
        History[Build History]
    end

    Base --> Explainer
    Base --> Incremental
    Base --> Delta
    Base --> Dependency
    Base --> Config
    Base --> Migrator
    Registry --> Base
    Report --> Base
    Site --> Base
    Cache --> Base
    History --> Delta
```

## Available Tools

### Page Explainer

Explains how a page is built, including template resolution, dependencies, and rendering steps:

```python
from bengal.debug import PageExplainer

explainer = PageExplainer(site=site)
explanation = explainer.explain_page("content/docs/getting-started.md")

print(explanation.format())
# Output:
# Template: docs.html (resolved from section cascade)
# Dependencies: theme/templates/docs.html, content/docs/_index.md
# Rendering: Markdown → HTML → Template → Output
```

### Incremental Build Debugger

Diagnoses incremental build issues:

```python
from bengal.debug import IncrementalBuildDebugger

debugger = IncrementalBuildDebugger(site=site, cache=cache)
report = debugger.analyze()

# Find phantom rebuilds (pages that rebuild without apparent cause)
phantom_rebuilds = debugger.find_phantom_rebuilds()

# Explain why a page was rebuilt
reason = debugger.explain_rebuild("content/post.md")
```

**Features**:
- Explain why pages rebuild
- Find phantom rebuilds
- Validate cache integrity
- Simulate changes

### Build Delta Analyzer

Compares builds and explains changes:

```python
from bengal.debug import BuildDeltaAnalyzer

analyzer = BuildDeltaAnalyzer(site=site)
delta = analyzer.compare_builds(build1_snapshot, build2_snapshot)

print(delta.summary())
# Output:
# Pages added: 5
# Pages removed: 2
# Pages modified: 12
# Assets changed: 3
```

### Dependency Visualizer

Visualizes build dependencies:

```python
from bengal.debug import DependencyVisualizer

visualizer = DependencyVisualizer(site=site, cache=cache)
graph = visualizer.generate_graph()

# Export to DOT format for Graphviz
graph.export_dot("dependencies.dot")
```

### Config Inspector

Advanced config comparison with origin tracking:

```python
from bengal.debug import ConfigInspector

inspector = ConfigInspector(site=site)
comparison = inspector.compare_configs(config1, config2)

for diff in comparison.diffs:
    print(f"{diff.key}: {diff.explanation}")
```

### Content Migrator

Safe content restructuring with link tracking:

```python
from bengal.debug import ContentMigrator

migrator = ContentMigrator(site=site)
preview = migrator.preview_move(
    source="content/old/page.md",
    destination="content/new/page.md",
)

# Preview shows:
# - Files to move
# - Links to update
# - Redirects to create

if preview.is_safe:
    migrator.execute_move(preview)
```

## Debug Tool Framework

### Creating Custom Tools

Subclass `DebugTool` to create custom diagnostic tools:

```python
from bengal.debug import DebugTool, DebugReport, DebugRegistry

@DebugRegistry.register
class MyDebugTool(DebugTool):
    name = "my-tool"
    description = "Analyzes something specific"

    def analyze(self) -> DebugReport:
        report = self.create_report()

        # Perform analysis
        finding = DebugFinding(
            severity=Severity.WARNING,
            message="Found issue",
            details="Detailed explanation",
            recommendations=["Fix this", "Fix that"],
        )
        report.add_finding(finding)

        return report
```

### Debug Registry

The registry enables tool discovery:

```python
from bengal.debug import DebugRegistry

# List all tools
tools = DebugRegistry.list_tools()
# [("page-explainer", "Explains how pages are built"), ...]

# Get a tool
tool_class = DebugRegistry.get("incremental")
tool = DebugRegistry.create("incremental", site=site, cache=cache)
```

## Debug Reports

All tools return structured `DebugReport` objects:

```python
report = tool.analyze()

# Summary
print(report.format_summary())

# Full report
print(report.format())

# Findings
for finding in report.findings:
    print(f"{finding.severity.emoji} {finding.message}")
    for rec in finding.recommendations:
        print(f"  • {rec}")
```

## CLI Integration

Debug tools are accessible via CLI commands:

```bash
# Explain a page
bengal explain content/docs/getting-started.md

# Debug incremental builds
bengal debug incremental

# Compare builds
bengal debug delta build1.json build2.json

# Visualize dependencies
bengal debug dependencies --format dot
```

## Related

- [[docs/reference/architecture/core/orchestration|Orchestration]] - How incremental builds work
- [[docs/reference/architecture/core/cache|Cache]] - Cache system details
- [[docs/reference/architecture/tooling/cli|CLI]] - Command-line interface
