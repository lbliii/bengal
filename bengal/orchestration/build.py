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
              verbose: bool = False, profile: 'BuildProfile' = None) -> BuildStats:
        """
        Execute full build pipeline.
        
        Args:
            parallel: Whether to use parallel processing
            incremental: Whether to perform incremental build (only changed files)
            verbose: Whether to show detailed build information
            profile: Build profile (writer, theme-dev, or dev)
            
        Returns:
            BuildStats object with build statistics
        """
        # Import profile utilities
        from bengal.utils.profile import BuildProfile, should_collect_metrics
        
        # Use default profile if not provided
        if profile is None:
            profile = BuildProfile.WRITER
        
        # Get profile configuration
        profile_config = profile.get_config()
        
        # Start timing
        build_start = time.time()
        
        # Initialize performance collection only if profile enables it
        collector = None
        if profile_config.get('collect_metrics', False):
            from bengal.utils.performance_collector import PerformanceCollector
            collector = PerformanceCollector()
            collector.start_build()
        
        # Initialize stats
        self.stats = BuildStats(parallel=parallel, incremental=incremental)
        
        self.logger.info("build_start", parallel=parallel, incremental=incremental, 
                        root_path=str(self.site.root_path))
        
        print(f"   ↪ {self.site.root_path}\n")
        self.site.build_time = datetime.now()
        
        # Initialize cache and tracker for incremental builds
        with self.logger.phase("initialization"):
            cache, tracker = self.incremental.initialize(enabled=incremental)
        
        # Phase 0.5: Font Processing (before asset discovery)
        # Download Google Fonts and generate CSS if configured
        if 'fonts' in self.site.config:
            with self.logger.phase("fonts"):
                fonts_start = time.time()
                try:
                    from bengal.fonts import FontHelper
                    
                    # Ensure assets directory exists
                    assets_dir = self.site.root_path / "assets"
                    assets_dir.mkdir(parents=True, exist_ok=True)
                    
                    # Process fonts (download + generate CSS)
                    font_helper = FontHelper(self.site.config['fonts'])
                    fonts_css = font_helper.process(assets_dir)
                    
                    self.stats.fonts_time_ms = (time.time() - fonts_start) * 1000
                    self.logger.info("fonts_complete")
                except Exception as e:
                    print(f"⚠️  Font processing failed: {e}")
                    print("   Continuing build without custom fonts...")
                    self.logger.warning("fonts_failed", error=str(e))
        
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
        
        # Phase 2: Determine what to build (MOVED UP - before taxonomies/menus)
        # This is the KEY optimization: filter BEFORE expensive operations
        with self.logger.phase("incremental_filtering", enabled=incremental):
            pages_to_build = self.site.pages
            assets_to_process = self.site.assets
            affected_tags = set()
            changed_page_paths = set()
            
            if incremental:
                # Find what changed BEFORE generating taxonomies/menus
                pages_to_build, assets_to_process, change_summary = self.incremental.find_work_early(
                    verbose=verbose
                )
                
                # Track which pages changed (for taxonomy updates)
                changed_page_paths = {p.source_path for p in pages_to_build if not p.metadata.get('_generated')}
                
                # Determine affected tags from changed pages
                for page in pages_to_build:
                    if page.tags and not page.metadata.get('_generated'):
                        for tag in page.tags:
                            affected_tags.add(tag.lower().replace(' ', '-'))
                
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
        
        # Phase 3: Section Finalization (ensure all sections have index pages)
        print("\n✨ Generated pages:")
        with self.logger.phase("section_finalization"):
            self.sections.finalize_sections()
            
            # Invalidate regular_pages cache (section finalization may add generated index pages)
            self.site.invalidate_regular_pages_cache()
            
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
        
        # Phase 4: Taxonomies & Dynamic Pages (INCREMENTAL OPTIMIZATION)
        with self.logger.phase("taxonomies"):
            taxonomy_start = time.time()
            
            if incremental and pages_to_build:
                # Incremental: Only update taxonomies for changed pages
                # This is O(changed) instead of O(all) - major optimization!
                affected_tags = self.taxonomy.collect_and_generate_incremental(
                    pages_to_build,
                    cache
                )
                
                # Store affected tags for later use (related posts, etc.)
                self.site._affected_tags = affected_tags
                
            elif not incremental:
                # Full build: Collect and generate everything
                self.taxonomy.collect_and_generate()
            # else: No pages changed, skip taxonomy updates
            
            self.stats.taxonomy_time_ms = (time.time() - taxonomy_start) * 1000
            if hasattr(self.site, 'taxonomies'):
                self.logger.info("taxonomies_built",
                               taxonomy_count=len(self.site.taxonomies),
                               total_terms=sum(len(terms) for terms in self.site.taxonomies.values()))
            
            # Invalidate regular_pages cache (taxonomy generation adds tag/category pages)
            self.site.invalidate_regular_pages_cache()
        
        # Phase 5: Menus (INCREMENTAL - skip if unchanged)
        with self.logger.phase("menus"):
            menu_start = time.time()
            # Check if config changed (forces menu rebuild)
            config_changed = incremental and self.incremental.check_config_changed()
            
            # Build menus (or reuse cached if unchanged)
            menu_rebuilt = self.menu.build(
                changed_pages=changed_page_paths if incremental else None,
                config_changed=config_changed
            )
            
            self.stats.menu_time_ms = (time.time() - menu_start) * 1000
            self.logger.info("menus_built", 
                           menu_count=len(self.site.menu),
                           rebuilt=menu_rebuilt)
        
        # Phase 5.5: Related Posts Index (NEW - Pre-compute for O(1) template access)
        with self.logger.phase("related_posts_index"):
            from bengal.orchestration.related_posts import RelatedPostsOrchestrator
            
            related_posts_start = time.time()
            related_posts_orchestrator = RelatedPostsOrchestrator(self.site)
            related_posts_orchestrator.build_index(limit=5)
            
            # Log statistics
            pages_with_related = sum(
                1 for p in self.site.pages 
                if hasattr(p, 'related_posts') and p.related_posts and not p.metadata.get('_generated')
            )
            self.stats.related_posts_time_ms = (time.time() - related_posts_start) * 1000
            self.logger.info("related_posts_built", 
                           pages_with_related=pages_with_related,
                           total_pages=len([p for p in self.site.pages if not p.metadata.get('_generated')]))
        
        # Phase 6: Update filtered pages list (add generated pages)
        # Now that we've generated tag pages, update pages_to_build if needed
        if incremental and affected_tags:
            # Add newly generated tag pages to rebuild list
            for page in self.site.pages:
                if page.metadata.get('_generated') and page.metadata.get('type') in ('tag', 'tag-index'):
                    tag_slug = page.metadata.get('_tag_slug')
                    if tag_slug in affected_tags or page.metadata.get('type') == 'tag-index':
                        if page not in pages_to_build:
                            pages_to_build.append(page)
        
        # Phase 7: Render Pages
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
        
        # Phase 10: Health Check (with profile filtering)
        with self.logger.phase("health_check"):
            self._run_health_check(profile=profile)
        
        # Collect memory metrics and save performance data (if enabled by profile)
        if collector:
            self.stats = collector.end_build(self.stats)
            collector.save(self.stats)
        
        # Log build completion
        log_data = {
            'duration_ms': self.stats.build_time_ms,
            'total_pages': self.stats.total_pages,
            'total_assets': self.stats.total_assets,
            'success': True
        }
        
        # Only add memory metrics if they were collected
        if self.stats.memory_rss_mb > 0:
            log_data['memory_rss_mb'] = self.stats.memory_rss_mb
            log_data['memory_heap_mb'] = self.stats.memory_heap_mb
        
        self.logger.info("build_complete", **log_data)
        
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
    
    def _run_health_check(self, profile: 'BuildProfile' = None) -> None:
        """
        Run health check system with profile-based filtering.
        
        Args:
            profile: Build profile to use for filtering validators
        """
        from bengal.health import HealthCheck
        
        health_config = self.site.config.get('health_check', {})
        
        # Check if health checks are enabled
        if isinstance(health_config, bool):
            enabled = health_config
        else:
            enabled = health_config.get('enabled', True)
        
        if not enabled:
            return
        
        # Run health checks with profile filtering
        health_check = HealthCheck(self.site)
        report = health_check.run(profile=profile)
        
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

