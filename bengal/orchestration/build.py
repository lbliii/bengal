"""
Build orchestration for Bengal SSG.

Main coordinator that delegates build phases to specialized orchestrators.
"""

import time
from datetime import datetime
from typing import TYPE_CHECKING

from bengal.utils.build_stats import BuildStats
from bengal.utils.logger import get_logger
from bengal.orchestration.content import ContentOrchestrator
from bengal.orchestration.section import SectionOrchestrator
from bengal.orchestration.taxonomy import TaxonomyOrchestrator
from bengal.orchestration.menu import MenuOrchestrator
from bengal.orchestration.render import RenderOrchestrator
from bengal.orchestration.asset import AssetOrchestrator
from bengal.orchestration.postprocess import PostprocessOrchestrator
from bengal.orchestration.incremental import IncrementalOrchestrator

if TYPE_CHECKING:
    from bengal.core.site import Site


class BuildOrchestrator:
    """
    Main build coordinator that orchestrates the entire build process.
    
    Delegates to specialized orchestrators for each phase:
        - ContentOrchestrator: Discovery and setup
        - TaxonomyOrchestrator: Taxonomies and dynamic pages
        - MenuOrchestrator: Navigation menus
        - RenderOrchestrator: Page rendering
        - AssetOrchestrator: Asset processing
        - PostprocessOrchestrator: Sitemap, RSS, validation
        - IncrementalOrchestrator: Change detection and caching
    """
    
    def __init__(self, site: 'Site'):
        """
        Initialize build orchestrator.
        
        Args:
            site: Site instance to build
        """
        self.site = site
        self.stats = BuildStats()
        self.logger = get_logger(__name__)
        
        # Initialize orchestrators
        self.content = ContentOrchestrator(site)
        self.sections = SectionOrchestrator(site)
        self.taxonomy = TaxonomyOrchestrator(site)
        self.menu = MenuOrchestrator(site)
        self.render = RenderOrchestrator(site)
        self.assets = AssetOrchestrator(site)
        self.postprocess = PostprocessOrchestrator(site)
        self.incremental = IncrementalOrchestrator(site)
    
    def build(self, parallel: bool = True, incremental: bool = False, 
              verbose: bool = False) -> BuildStats:
        """
        Execute full build pipeline.
        
        Args:
            parallel: Whether to use parallel processing
            incremental: Whether to perform incremental build (only changed files)
            verbose: Whether to show detailed build information
            
        Returns:
            BuildStats object with build statistics
        """
        # Start timing
        build_start = time.time()
        
        # Initialize stats
        self.stats = BuildStats(parallel=parallel, incremental=incremental)
        
        self.logger.info("build_start", parallel=parallel, incremental=incremental, 
                        root_path=str(self.site.root_path))
        
        print(f"   ↪ {self.site.root_path}\n")
        self.site.build_time = datetime.now()
        
        # Initialize cache and tracker for incremental builds
        with self.logger.phase("initialization"):
            cache, tracker = self.incremental.initialize(enabled=incremental)
        
        # Phase 1: Content Discovery
        content_dir = self.site.root_path / "content"
        with self.logger.phase("discovery", content_dir=str(content_dir)):
            discovery_start = time.time()
            self.content.discover()
            self.stats.discovery_time_ms = (time.time() - discovery_start) * 1000
            self.logger.info("discovery_complete", 
                           pages=len(self.site.pages), 
                           sections=len(self.site.sections))
        
        # Check if config changed (forces full rebuild)
        if incremental and self.incremental.check_config_changed():
            print("  Config file changed - performing full rebuild")
            incremental = False
            cache.clear()
        
        # Phase 2: Section Finalization (ensure all sections have index pages)
        print("\n✨ Generated pages:")
        with self.logger.phase("section_finalization"):
            self.sections.finalize_sections()
            
            # Validate section structure
            section_errors = self.sections.validate_sections()
            if section_errors:
                self.logger.warning("section_validation_errors", 
                                  error_count=len(section_errors),
                                  errors=section_errors[:3])
                strict_mode = self.site.config.get('strict_mode', False)
                if strict_mode:
                    print("\n❌ Section validation errors:")
                    for error in section_errors:
                        print(f"   • {error}")
                    raise Exception(f"Build failed: {len(section_errors)} section validation error(s)")
                else:
                    # Warn but continue in non-strict mode
                    for error in section_errors[:3]:  # Show first 3
                        print(f"⚠️  {error}")
                    if len(section_errors) > 3:
                        print(f"⚠️  ... and {len(section_errors) - 3} more errors")
        
        # Phase 3: Taxonomies & Dynamic Pages
        with self.logger.phase("taxonomies"):
            taxonomy_start = time.time()
            self.taxonomy.collect_and_generate()
            self.stats.taxonomy_time_ms = (time.time() - taxonomy_start) * 1000
            self.logger.info("taxonomies_built",
                           taxonomy_count=len(self.site.taxonomies),
                           total_terms=sum(len(terms) for terms in self.site.taxonomies.values()))
        
        # Phase 4: Menus
        with self.logger.phase("menus"):
            self.menu.build()
            self.logger.info("menus_built", menu_count=len(self.site.menu))
        
        # Phase 5: Determine what to build (incremental)
        with self.logger.phase("incremental_filtering", enabled=incremental):
            pages_to_build = self.site.pages
            assets_to_process = self.site.assets
            
            if incremental:
                pages_to_build, assets_to_process, change_summary = self.incremental.find_work(
                    verbose=verbose
                )
                
                self.logger.info("incremental_work_identified",
                               pages_to_build=len(pages_to_build),
                               assets_to_process=len(assets_to_process),
                               skipped_pages=len(self.site.pages) - len(pages_to_build))
                
                if not pages_to_build and not assets_to_process:
                    print("✓ No changes detected - skipping build")
                    self.logger.info("no_changes_detected")
                    self.stats.skipped = True
                    self.stats.build_time_ms = (time.time() - build_start) * 1000
                    return self.stats
                
                print(f"  Incremental build: {len(pages_to_build)} pages, "
                      f"{len(assets_to_process)} assets")
                
                if verbose and change_summary:
                    print(f"\n  📝 Changes detected:")
                    for change_type, items in change_summary.items():
                        if items:
                            print(f"    • {change_type}: {len(items)} file(s)")
                            for item in items[:5]:  # Show first 5
                                print(f"      - {item.name if hasattr(item, 'name') else item}")
                            if len(items) > 5:
                                print(f"      ... and {len(items) - 5} more")
                    print()
        
        # Phase 6: Render Pages
        quiet_mode = not verbose
        if quiet_mode:
            print(f"\n📄 Rendering content:")
        
        with self.logger.phase("rendering", page_count=len(pages_to_build), parallel=parallel):
            rendering_start = time.time()
            original_pages = self.site.pages
            self.site.pages = pages_to_build  # Temporarily replace with subset
            
            self.render.process(pages_to_build, parallel=parallel, tracker=tracker, stats=self.stats)
            
            self.site.pages = original_pages  # Restore full page list
            self.stats.rendering_time_ms = (time.time() - rendering_start) * 1000
            self.logger.info("rendering_complete", 
                           pages_rendered=len(pages_to_build),
                           errors=len(self.stats.template_errors) if hasattr(self.stats, 'template_errors') else 0)
        
        # Print rendering summary in quiet mode
        if quiet_mode:
            self._print_rendering_summary()
        
        # Phase 7: Process Assets
        with self.logger.phase("assets", asset_count=len(assets_to_process), parallel=parallel):
            assets_start = time.time()
            original_assets = self.site.assets
            self.site.assets = assets_to_process  # Temporarily replace with subset
            
            self.assets.process(assets_to_process, parallel=parallel)
            
            self.site.assets = original_assets  # Restore full asset list
            self.stats.assets_time_ms = (time.time() - assets_start) * 1000
            self.logger.info("assets_complete", assets_processed=len(assets_to_process))
        
        # Phase 8: Post-processing
        with self.logger.phase("postprocessing", parallel=parallel):
            postprocess_start = time.time()
            self.postprocess.run(parallel=parallel)
            self.stats.postprocess_time_ms = (time.time() - postprocess_start) * 1000
            self.logger.info("postprocessing_complete")
        
        # Phase 9: Update cache
        if incremental or self.site.config.get("cache_enabled", True):
            with self.logger.phase("cache_save"):
                self.incremental.save_cache(pages_to_build, assets_to_process)
                self.logger.info("cache_saved")
        
        # Collect final stats (before health check so we can include them in report)
        self.stats.total_pages = len(self.site.pages)
        self.stats.regular_pages = len([p for p in self.site.pages if not p.metadata.get('_generated')])
        self.stats.generated_pages = len([p for p in self.site.pages if p.metadata.get('_generated')])
        self.stats.total_assets = len(self.site.assets)
        self.stats.total_sections = len(self.site.sections)
        self.stats.taxonomies_count = sum(len(terms) for terms in self.site.taxonomies.values())
        self.stats.build_time_ms = (time.time() - build_start) * 1000
        
        # Store stats for health check validators to access
        self.site._last_build_stats = {
            'build_time_ms': self.stats.build_time_ms,
            'rendering_time_ms': self.stats.rendering_time_ms,
            'total_pages': self.stats.total_pages,
            'total_assets': self.stats.total_assets,
        }
        
        # Phase 10: Health Check
        with self.logger.phase("health_check"):
            self._run_health_check()
        
        # Log build completion
        self.logger.info("build_complete",
                        duration_ms=self.stats.build_time_ms,
                        total_pages=self.stats.total_pages,
                        total_assets=self.stats.total_assets,
                        success=True)
        
        return self.stats
    
    def _print_rendering_summary(self) -> None:
        """Print summary of rendered pages (quiet mode)."""
        # Count page types
        tag_pages = sum(1 for p in self.site.pages if p.metadata.get('_generated') and 'tag' in p.output_path.parts)
        archive_pages = sum(1 for p in self.site.pages if p.metadata.get('_generated') and p.metadata.get('template') == 'archive.html')
        pagination_pages = sum(1 for p in self.site.pages if p.metadata.get('_generated') and '/page/' in str(p.output_path))
        regular_pages = sum(1 for p in self.site.pages if not p.metadata.get('_generated'))
        
        print(f"   ├─ Regular pages:    {regular_pages}")
        if tag_pages:
            print(f"   ├─ Tag pages:        {tag_pages}")
        if archive_pages:
            print(f"   ├─ Archive pages:    {archive_pages}")
        if pagination_pages:
            print(f"   ├─ Pagination:       {pagination_pages}")
        print(f"   └─ Total:            {len(self.site.pages)} ✓")
    
    def _run_health_check(self) -> None:
        """Run health check system."""
        from bengal.health import HealthCheck
        
        health_config = self.site.config.get('health_check', {})
        
        # Check if health checks are enabled
        if isinstance(health_config, bool):
            enabled = health_config
        else:
            enabled = health_config.get('enabled', True)
        
        if not enabled:
            return
        
        # Run health checks
        health_check = HealthCheck(self.site)
        report = health_check.run()
        
        # Print report
        if health_config.get('verbose', False):
            print(report.format_console(verbose=True))
        else:
            # Only print if there are issues
            if report.has_errors() or report.has_warnings():
                print(report.format_console(verbose=False))
        
        # Store report in stats
        self.stats.health_report = report
        
        # Fail build in strict mode if there are errors
        strict_mode = health_config.get('strict_mode', False)
        if strict_mode and report.has_errors():
            raise Exception(
                f"Build failed health checks: {report.error_count} error(s) found. "
                "Review output or disable strict_mode."
            )

