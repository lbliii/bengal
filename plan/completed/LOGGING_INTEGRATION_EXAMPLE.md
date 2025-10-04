# Structured Logging Integration Guide

This document shows how to integrate the new structured logging system into Bengal's build pipeline.

## Quick Start

### 1. Configure Logging in CLI

```python
# In bengal/cli.py

import click
from pathlib import Path
from bengal.utils.logger import configure_logging, LogLevel, close_all_loggers, print_all_summaries

@click.command()
@click.option('--verbose', '-v', is_flag=True, help='Show detailed build information')
@click.option('--debug', is_flag=True, help='Show debug output')
@click.option('--log-file', type=click.Path(), help='Write logs to file')
def build(verbose, debug, log_file):
    """Build the site."""
    
    # Configure logging based on flags
    if debug:
        level = LogLevel.DEBUG
    elif verbose:
        level = LogLevel.INFO
    else:
        level = LogLevel.INFO  # Still log, just less verbose output
    
    # Set up log file
    if log_file:
        log_path = Path(log_file)
    else:
        log_path = Path('.bengal-build.log')
    
    configure_logging(
        level=level,
        log_file=log_path,
        verbose=verbose
    )
    
    try:
        # Run build...
        site = Site.from_config()
        orchestrator = BuildOrchestrator(site)
        stats = orchestrator.build(verbose=verbose)
        
        # Print timing summary in verbose mode
        if verbose:
            print_all_summaries()
        
        print(f"\n✅ Build complete in {stats.build_time_ms/1000:.2f}s")
        
    finally:
        # Always close log files
        close_all_loggers()
```

### 2. Update BuildOrchestrator

```python
# In bengal/orchestration/build.py

from bengal.utils.logger import get_logger

class BuildOrchestrator:
    def __init__(self, site: 'Site'):
        self.site = site
        self.stats = BuildStats()
        self.logger = get_logger(__name__)  # ← Add this
        
        # ... rest of init ...
    
    def build(self, parallel: bool = True, incremental: bool = False, 
              verbose: bool = False) -> BuildStats:
        """Execute full build pipeline with structured logging."""
        
        self.logger.info(
            "build_start",
            parallel=parallel,
            incremental=incremental,
            page_count=len(self.site.pages) if self.site.pages else 0
        )
        
        with self.logger.phase("initialization"):
            build_start = time.time()
            self.stats = BuildStats(parallel=parallel, incremental=incremental)
            self.site.build_time = datetime.now()
            cache, tracker = self.incremental.initialize(enabled=incremental)
        
        # Phase 1: Content Discovery
        with self.logger.phase("discovery", root_path=str(self.site.root_path)):
            self.content.discover()
            self.logger.info(
                "discovery_complete",
                pages=len(self.site.pages),
                sections=len(self.site.sections)
            )
        
        # Phase 2: Section Finalization
        with self.logger.phase("section_finalization"):
            self.sections.finalize_sections()
            section_errors = self.sections.validate_sections()
            
            if section_errors:
                self.logger.warning(
                    "section_validation_errors",
                    error_count=len(section_errors),
                    errors=section_errors[:3]  # Log first 3
                )
        
        # Phase 3: Taxonomies
        with self.logger.phase("taxonomies"):
            self.taxonomy.collect_and_generate()
            self.logger.info(
                "taxonomies_built",
                taxonomy_count=len(self.site.taxonomies),
                total_terms=sum(len(terms) for terms in self.site.taxonomies.values())
            )
        
        # Phase 4: Menus
        with self.logger.phase("menus"):
            self.menu.build()
            self.logger.info(
                "menus_built",
                menu_count=len(self.site.menu)
            )
        
        # Phase 5: Incremental filtering
        with self.logger.phase("incremental_filtering", enabled=incremental):
            if incremental:
                pages_to_build, assets_to_process, change_summary = self.incremental.find_work(
                    verbose=verbose
                )
                
                self.logger.info(
                    "incremental_work_identified",
                    pages_to_build=len(pages_to_build),
                    assets_to_process=len(assets_to_process),
                    skipped_pages=len(self.site.pages) - len(pages_to_build)
                )
                
                if not pages_to_build and not assets_to_process:
                    self.logger.info("no_changes_detected")
                    self.stats.skipped = True
                    return self.stats
            else:
                pages_to_build = self.site.pages
                assets_to_process = self.site.assets
        
        # Phase 6: Rendering
        with self.logger.phase("rendering", page_count=len(pages_to_build), parallel=parallel):
            self.render.process(pages_to_build, parallel=parallel, tracker=tracker, stats=self.stats)
            self.logger.info(
                "rendering_complete",
                pages_rendered=len(pages_to_build),
                errors=self.stats.render_errors
            )
        
        # Phase 7: Assets
        with self.logger.phase("assets", asset_count=len(assets_to_process), parallel=parallel):
            self.assets.process(assets_to_process, parallel=parallel)
            self.logger.info(
                "assets_complete",
                assets_processed=len(assets_to_process)
            )
        
        # Phase 8: Post-processing
        with self.logger.phase("postprocessing", parallel=parallel):
            self.postprocess.run(parallel=parallel)
            self.logger.info("postprocessing_complete")
        
        # Phase 9: Cache save
        if incremental or self.site.config.get("cache_enabled", True):
            with self.logger.phase("cache_save"):
                self.incremental.save_cache(pages_to_build, assets_to_process)
        
        # Phase 10: Health check
        with self.logger.phase("health_check"):
            self._run_health_check()
        
        # Final stats
        self.stats.build_time_ms = (time.time() - build_start) * 1000
        
        self.logger.info(
            "build_complete",
            duration_ms=self.stats.build_time_ms,
            total_pages=len(self.site.pages),
            total_assets=len(self.site.assets)
        )
        
        return self.stats
```

### 3. Add Logging to Individual Orchestrators

Each orchestrator can have its own logger:

```python
# In bengal/orchestration/content.py

from bengal.utils.logger import get_logger

class ContentOrchestrator:
    def __init__(self, site):
        self.site = site
        self.logger = get_logger(__name__)
    
    def discover(self):
        """Discover all content files."""
        from bengal.discovery.content_discovery import ContentDiscovery
        
        self.logger.debug("starting_discovery", content_dir=str(self.site.content_dir))
        
        discovery = ContentDiscovery(self.site.content_dir)
        pages, sections = discovery.discover()
        
        self.logger.debug(
            "discovered_raw_content",
            page_count=len(pages),
            section_count=len(sections)
        )
        
        # ... rest of discovery ...
        
        self._setup_page_references()
        self.logger.debug("page_references_setup")
        
        self._apply_section_cascade()
        self.logger.debug("cascades_applied")
        
        self._build_xref_index()
        self.logger.debug("xref_index_built", index_size=len(self.site.xref_index['by_path']))
```

### 4. Add Detailed Logging to Parser

```python
# In bengal/rendering/parser.py

from bengal.utils.logger import get_logger

class MistuneParser(BaseMarkdownParser):
    def __init__(self):
        super().__init__()
        self.logger = get_logger(__name__)
    
    def parse(self, content: str, metadata: dict) -> tuple[str, str]:
        """Parse markdown with logging."""
        
        self.logger.debug(
            "parse_start",
            content_length=len(content),
            has_metadata=bool(metadata)
        )
        
        # Variable substitution
        if '{{' in content:
            self.logger.debug("applying_variable_substitution")
            content = self._substitute_variables(content, metadata)
        
        # Parse to HTML
        html = self.md.parse(content)
        self.logger.debug("markdown_parsed", html_length=len(html))
        
        # Extract TOC
        toc = self._extract_toc(html)
        self.logger.debug("toc_extracted", toc_items=len(toc))
        
        return html, toc
```

## Example Output

### Normal Mode (not verbose):
```
● build_start parallel=True incremental=False page_count=42
  ● [discovery] phase_start
  ● discovery_complete pages=42 sections=5
  ● [discovery] phase_complete (123.4ms)
  ● [rendering] phase_start page_count=42
  ● rendering_complete pages_rendered=42 errors=0
  ● [rendering] phase_complete (1234.5ms)
● build_complete duration_ms=2456.7
```

### Verbose Mode (`--verbose`):
```
12:34:56 ● build_start parallel=True incremental=False page_count=42
12:34:56   ● [discovery] phase_start root_path=/path/to/site
12:34:56   ● starting_discovery content_dir=/path/to/site/content
12:34:56   ● discovered_raw_content page_count=42 section_count=5
12:34:56   ● page_references_setup
12:34:56   ● cascades_applied
12:34:56   ● xref_index_built index_size=42
12:34:56   ● discovery_complete pages=42 sections=5
12:34:56   ● [discovery] phase_complete (123.4ms)
12:34:57   ● [section_finalization] phase_start
12:34:57   ● [section_finalization] phase_complete (45.6ms)
12:34:57   ● [taxonomies] phase_start
12:34:57   ● taxonomies_built taxonomy_count=1 total_terms=8
12:34:57   ● [taxonomies] phase_complete (78.9ms)
12:34:57   ● [menus] phase_start
12:34:57   ● menus_built menu_count=1
12:34:57   ● [menus] phase_complete (12.3ms)
12:34:57   ● [rendering] phase_start page_count=42 parallel=True
12:34:58   ● rendering_complete pages_rendered=42 errors=0
12:34:58   ● [rendering] phase_complete (1234.5ms)
12:34:58   ● [assets] phase_start asset_count=15 parallel=True
12:34:58   ● assets_complete assets_processed=15
12:34:58   ● [assets] phase_complete (234.5ms)
12:34:58   ● [postprocessing] phase_start parallel=True
12:34:58   ● postprocessing_complete
12:34:58   ● [postprocessing] phase_complete (123.4ms)
12:34:58   ● [health_check] phase_start
12:34:58   ● [health_check] phase_complete (45.6ms)
12:34:58 ● build_complete duration_ms=2456.7 total_pages=42 total_assets=15

============================================================
Build Phase Timings:
============================================================
  rendering                      1234.5ms ( 50.2%)
  assets                          234.5ms (  9.5%)
  discovery                       123.4ms (  5.0%)
  postprocessing                  123.4ms (  5.0%)
  taxonomies                       78.9ms (  3.2%)
  section_finalization             45.6ms (  1.9%)
  health_check                     45.6ms (  1.9%)
  menus                            12.3ms (  0.5%)
------------------------------------------------------------
  TOTAL                          2456.7ms (100.0%)
============================================================
```

### Debug Mode (`--debug`):
Shows everything, including:
- File reads
- Frontmatter parsing
- Variable substitutions
- Template selections
- Link extractions
- Every decision made

### Log File (`.bengal-build.log`)
JSON format for machine parsing:
```json
{"timestamp":"2025-10-04T12:34:56.123456","level":"INFO","logger_name":"bengal.orchestration.build","event_type":"info","message":"build_start","context":{"parallel":true,"incremental":false,"page_count":42}}
{"timestamp":"2025-10-04T12:34:56.234567","level":"INFO","logger_name":"bengal.orchestration.content","event_type":"info","message":"discovery_complete","phase":"discovery","phase_depth":1,"context":{"pages":42,"sections":5}}
...
```

## Benefits

### 1. Troubleshooting
When a user reports an issue:
```bash
# Ask them to run with verbose logging
$ bengal build --verbose --log-file=debug.log

# They send you debug.log, you can see EXACTLY what happened
$ cat debug.log | jq '.message, .context'
```

### 2. Performance Analysis
```bash
# See where time is spent
$ bengal build --verbose | grep "phase_complete"

# Or parse the log file
$ cat .bengal-build.log | jq 'select(.event_type=="phase_complete") | {phase: .phase, duration: .context.duration_ms}'
```

### 3. Debugging Phase Order Issues
```bash
# See exact execution order
$ cat .bengal-build.log | jq 'select(.message | contains("phase_")) | {time: .timestamp, phase: .phase, event: .message}'
```

### 4. Testing
In tests, you can inspect events:
```python
def test_build_phases():
    logger = get_logger("bengal.orchestration.build")
    
    site = Site.from_config()
    orchestrator = BuildOrchestrator(site)
    orchestrator.build()
    
    events = logger.get_events()
    
    # Assert phases ran in correct order
    phase_starts = [e for e in events if e.event_type == "phase_start"]
    assert phase_starts[0].phase == "discovery"
    assert phase_starts[1].phase == "section_finalization"
    # ... etc
```

## Migration Strategy

**Phase 1: Add logging infrastructure** ✅ (Done)
- Create logger module
- Write tests
- Document API

**Phase 2: Integrate into build orchestrator** (Next)
- Update BuildOrchestrator.build()
- Update CLI to configure logging
- Test output formats

**Phase 3: Add to orchestrators** (Week 2)
- ContentOrchestrator
- RenderOrchestrator
- AssetOrchestrator
- PostprocessOrchestrator

**Phase 4: Add to rendering pipeline** (Week 3)
- Parser logging
- Template engine logging
- Variable substitution logging

**Phase 5: Polish** (Week 4)
- Add memory tracking events
- Add performance markers
- Update documentation

## Next Steps

1. ✅ Implement logger (done)
2. ✅ Write tests (done)
3. Update CLI (5 lines of code)
4. Update BuildOrchestrator (30 lines of code)
5. Test with example site
6. Iterate on output format based on usability

Want me to make these changes to the actual files?

