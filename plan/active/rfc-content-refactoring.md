# RFC: Content-Aware Refactoring

**Status**: Draft  
**Created**: 2025-12-08  
**Author**: AI Assistant  
**Confidence**: 85% 🟢

---

## Executive Summary

Add CLI commands for content operations that understand the document graph: move, rename, merge, and split pages while automatically updating all internal links, navigation, and generating redirects.

---

## Problem Statement

### Current State

Refactoring content in Bengal (or any SSG) is manual and error-prone:

1. Move/rename file in filesystem
2. Manually find and update all internal links
3. Manually update navigation/menu files
4. Manually create redirects for old URLs
5. Hope you didn't miss anything

**Evidence**:
- No existing refactoring commands in `bengal/cli/`
- Link validation exists (`bengal/health/`) but doesn't fix issues
- Knowledge graph tracks relationships but doesn't use them for refactoring

### Pain Points

1. **Broken links**: Renaming a popular page breaks links across the site
2. **SEO damage**: Old URLs return 404 instead of redirecting
3. **Manual tedium**: Searching for links is slow and error-prone
4. **Fear of refactoring**: Teams avoid reorganizing docs because it's painful

### User Impact

Documentation sites accumulate technical debt. Pages end up in wrong sections, naming is inconsistent, but nobody wants to fix it because the cost is too high.

---

## Goals & Non-Goals

**Goals**:
- Safe content operations with automatic link updates
- Preview changes before applying
- Generate redirects for SEO preservation
- Support common operations: move, rename, merge, split
- Undo capability (or git-friendly workflow)

**Non-Goals**:
- Cross-site refactoring (external links)
- Content rewriting (just structural changes)
- Real-time collaboration (single-user CLI tool)

---

## Architecture Impact

**Affected Subsystems**:
- **CLI** (`bengal/cli/`): New refactor command group
- **Core** (`bengal/core/`): Link extraction and updating
- **Health** (`bengal/health/`): Integration with link validation
- **Analysis** (`bengal/analysis/`): Leverage knowledge graph for impact analysis

**New Components**:
- `bengal/refactor/` - Refactoring engine
- `bengal/refactor/operations.py` - Move, rename, merge, split
- `bengal/refactor/link_updater.py` - Link rewriting
- `bengal/refactor/redirect_generator.py` - Redirect file generation

---

## Proposed CLI Interface

### Move

```bash
# Move a single page
bengal refactor move docs/old-guide.md docs/new-section/guide.md

# Move a section
bengal refactor move docs/tutorials/ docs/learn/tutorials/

# Preview without applying
bengal refactor move docs/old.md docs/new.md --dry-run

# Skip redirect generation
bengal refactor move docs/old.md docs/new.md --no-redirect
```

### Rename

```bash
# Rename page (updates slug)
bengal refactor rename docs/tutoral.md docs/tutorial.md

# Rename with custom slug
bengal refactor rename docs/guide.md --slug getting-started
```

### Merge

```bash
# Merge multiple pages into one
bengal refactor merge docs/part1.md docs/part2.md docs/part3.md \
    --into docs/complete-guide.md

# Merge section into single page
bengal refactor merge docs/api/v1/ --into docs/api/v1-reference.md
```

### Split

```bash
# Split page by headings
bengal refactor split docs/monolith.md --by h2 --into docs/sections/

# Split with custom mapping
bengal refactor split docs/guide.md --config split-config.yaml
```

### Analyze Impact

```bash
# Show what would change without doing it
bengal refactor analyze docs/important-page.md

# Output:
# Impact Analysis: docs/important-page.md
# ├─ Incoming links: 47 pages link here
# ├─ Outgoing links: 12 pages linked from here
# ├─ Navigation: Appears in 3 menus
# ├─ Taxonomies: Tagged in 2 categories
# └─ External links: 5 external sites link here (via search)
```

---

## Detailed Design

### Core Data Structures

```python
# bengal/refactor/types.py
from dataclasses import dataclass
from pathlib import Path

@dataclass
class RefactorOperation:
    """Base class for refactoring operations."""
    dry_run: bool = True
    generate_redirects: bool = True

@dataclass
class MoveOperation(RefactorOperation):
    source: Path
    destination: Path

@dataclass
class RenameOperation(RefactorOperation):
    source: Path
    new_name: str
    new_slug: str | None = None

@dataclass
class MergeOperation(RefactorOperation):
    sources: list[Path]
    destination: Path
    strategy: str = "concatenate"  # or "sections"

@dataclass
class SplitOperation(RefactorOperation):
    source: Path
    destination_dir: Path
    split_by: str = "h2"  # heading level

@dataclass
class RefactorPlan:
    """Complete plan for a refactoring operation."""
    operation: RefactorOperation
    file_moves: list[tuple[Path, Path]]
    link_updates: list[LinkUpdate]
    nav_updates: list[NavUpdate]
    redirects: list[Redirect]
    warnings: list[str]
```

### Link Update Engine

```python
# bengal/refactor/link_updater.py
from bengal.core import Site, Page
import re

class LinkUpdater:
    """Updates internal links across the site."""

    def __init__(self, site: Site):
        self.site = site
        self.link_index = self._build_link_index()

    def _build_link_index(self) -> dict[str, list[LinkReference]]:
        """Build index of all internal links."""
        index = defaultdict(list)
        for page in self.site.pages:
            for link in self._extract_links(page):
                index[link.target].append(LinkReference(
                    source_page=page.path,
                    link=link,
                ))
        return index

    def find_incoming_links(self, page_path: str) -> list[LinkReference]:
        """Find all pages linking to the given page."""
        # Normalize path variations
        targets = self._get_path_variations(page_path)
        incoming = []
        for target in targets:
            incoming.extend(self.link_index.get(target, []))
        return incoming

    def update_links(
        self,
        old_path: str,
        new_path: str,
        dry_run: bool = True
    ) -> list[LinkUpdate]:
        """Update all links from old_path to new_path."""
        incoming = self.find_incoming_links(old_path)
        updates = []

        for ref in incoming:
            # Calculate new relative link
            new_link = self._calculate_relative_link(
                from_page=ref.source_page,
                to_page=new_path,
            )

            update = LinkUpdate(
                file=ref.source_page,
                old_link=ref.link.raw,
                new_link=new_link,
                line=ref.link.line,
            )
            updates.append(update)

            if not dry_run:
                self._apply_update(update)

        return updates

    def _extract_links(self, page: Page) -> list[Link]:
        """Extract all links from page content."""
        links = []

        # Markdown links: [text](url)
        for match in re.finditer(r'\[([^\]]+)\]\(([^)]+)\)', page.raw_content):
            links.append(Link(
                text=match.group(1),
                target=match.group(2),
                raw=match.group(0),
                line=page.raw_content[:match.start()].count('\n') + 1,
            ))

        # Reference links: [text][ref]
        # ... handle reference-style links

        # HTML links: <a href="">
        # ... handle HTML links

        return [l for l in links if self._is_internal(l.target)]
```

### Redirect Generator

```python
# bengal/refactor/redirect_generator.py

class RedirectGenerator:
    """Generate redirect configuration for moved pages."""

    def __init__(self, site: Site):
        self.site = site
        self.redirect_format = site.config.get("redirects.format", "netlify")

    def generate(self, moves: list[tuple[str, str]]) -> str:
        """Generate redirect rules for the configured platform."""

        redirects = []
        for old_url, new_url in moves:
            old_url = self._path_to_url(old_url)
            new_url = self._path_to_url(new_url)
            redirects.append(Redirect(
                from_url=old_url,
                to_url=new_url,
                status=301,  # Permanent redirect
            ))

        if self.redirect_format == "netlify":
            return self._format_netlify(redirects)
        elif self.redirect_format == "vercel":
            return self._format_vercel(redirects)
        elif self.redirect_format == "nginx":
            return self._format_nginx(redirects)
        elif self.redirect_format == "apache":
            return self._format_apache(redirects)
        else:
            return self._format_bengal_native(redirects)

    def _format_netlify(self, redirects: list[Redirect]) -> str:
        """Format for Netlify _redirects file."""
        lines = []
        for r in redirects:
            lines.append(f"{r.from_url} {r.to_url} {r.status}")
        return "\n".join(lines)

    def _format_bengal_native(self, redirects: list[Redirect]) -> str:
        """Format for Bengal's native redirect handling."""
        return yaml.dump({
            "redirects": [
                {"from": r.from_url, "to": r.to_url, "status": r.status}
                for r in redirects
            ]
        })
```

### Interactive Preview

```python
# bengal/refactor/preview.py

class RefactorPreview:
    """Interactive preview of refactoring changes."""

    def show(self, plan: RefactorPlan) -> bool:
        """Display plan and get confirmation."""

        console.print("\n[bold]📋 Refactoring Plan[/bold]\n")

        # File operations
        console.print("[bold]File Changes:[/bold]")
        for old, new in plan.file_moves:
            console.print(f"  [red]- {old}[/red]")
            console.print(f"  [green]+ {new}[/green]")

        # Link updates
        console.print(f"\n[bold]Link Updates:[/bold] {len(plan.link_updates)} files")
        if len(plan.link_updates) <= 10:
            for update in plan.link_updates:
                console.print(f"  {update.file}:{update.line}")
                console.print(f"    [red]{update.old_link}[/red] → [green]{update.new_link}[/green]")
        else:
            console.print(f"  ... and {len(plan.link_updates) - 5} more")

        # Redirects
        if plan.redirects:
            console.print(f"\n[bold]Redirects:[/bold] {len(plan.redirects)} rules")
            for r in plan.redirects[:5]:
                console.print(f"  {r.from_url} → {r.to_url}")

        # Warnings
        if plan.warnings:
            console.print("\n[yellow][bold]⚠️ Warnings:[/bold][/yellow]")
            for warning in plan.warnings:
                console.print(f"  [yellow]• {warning}[/yellow]")

        # Confirmation
        return Confirm.ask("\nApply these changes?")
```

---

## Configuration

```toml
# bengal.toml
[refactor]
# Redirect file format
redirect_format = "netlify"  # or "vercel", "nginx", "apache", "bengal"

# Where to write redirects
redirect_file = "_redirects"  # or "vercel.json", etc.

# Auto-commit after refactoring
auto_commit = false

# Backup before applying
backup = true

# Patterns to exclude from link updates
exclude_patterns = [
    "node_modules/**",
    ".git/**",
]
```

---

## Example Session

```bash
$ bengal refactor move docs/getting-started/installation.md docs/setup/install.md

📋 Refactoring Plan

File Changes:
  - docs/getting-started/installation.md
  + docs/setup/install.md

Link Updates: 23 files
  docs/index.md:45
    [installation guide](getting-started/installation.md) → [installation guide](setup/install.md)
  docs/tutorials/quickstart.md:12
    [Install Bengal](../getting-started/installation.md) → [Install Bengal](../setup/install.md)
  ... and 21 more

Navigation Updates: 2 files
  docs/getting-started/_index.md: Remove from section
  docs/setup/_index.md: Add to section

Redirects: 1 rule
  /docs/getting-started/installation/ → /docs/setup/install/

Apply these changes? [y/N]: y

✅ Refactoring complete!
  • Moved 1 file
  • Updated 23 links
  • Updated 2 navigation files
  • Generated 1 redirect

💡 Tip: Run `bengal validate` to verify no broken links remain.
```

---

## Implementation Plan

### Phase 1: Foundation (2 weeks)
- [ ] Link extraction and indexing
- [ ] Basic move operation
- [ ] Dry-run preview

### Phase 2: Full Move Support (2 weeks)
- [ ] Section moves
- [ ] Navigation updates
- [ ] Redirect generation (multiple formats)

### Phase 3: Additional Operations (2 weeks)
- [ ] Rename command
- [ ] Merge command
- [ ] Split command

### Phase 4: Polish (1 week)
- [ ] Impact analysis command
- [ ] Undo/rollback support
- [ ] Integration with `bengal validate`

---

## Risks & Mitigations

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| Missed link patterns | High | Medium | Comprehensive regex + user-defined patterns |
| Corrupted content | High | Low | Backup before apply, dry-run default |
| Complex merge conflicts | Medium | Medium | Clear merge strategies, manual fallback |
| Performance on large sites | Medium | Low | Incremental indexing, caching |

---

## Open Questions

1. **How to handle ambiguous links?**
   - e.g., `[guide](guide.md)` could match multiple files
   - Proposal: Warn and ask user to disambiguate

2. **Should we support regex-based bulk moves?**
   - e.g., `bengal refactor move 'docs/v1/(.*)' 'docs/archive/v1/$1'`
   - Proposal: Yes, in Phase 3

3. **How to handle external link shorteners?**
   - Some sites use `/go/foo` style redirects
   - Proposal: Flag but don't auto-update

4. **Git integration?**
   - Auto-stage changes? Auto-commit?
   - Proposal: Opt-in via `--commit` flag

---

## Success Criteria

- [ ] Move operation updates 100% of internal links correctly
- [ ] Preview mode shows complete change plan
- [ ] Redirects generated for all supported platforms
- [ ] No data loss (backup or undo available)
- [ ] Performance: <5s for 1000-page site analysis

---

## References

- [IntelliJ Refactoring](https://www.jetbrains.com/help/idea/refactoring-source-code.html)
- [VS Code Rename Symbol](https://code.visualstudio.com/docs/editor/refactoring)
- [Docusaurus File Naming](https://docusaurus.io/docs/docs-introduction)
- [Netlify Redirects](https://docs.netlify.com/routing/redirects/)
