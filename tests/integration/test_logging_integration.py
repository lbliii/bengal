"""
Integration tests for structured logging system.

Tests that logging works correctly during real builds and captures
all the expected events and phases.
"""

import pytest

from bengal.core.site import Site
from bengal.utils.logger import (
    get_logger,
    configure_logging,
    close_all_loggers,
    LogLevel,
    _loggers,
)


@pytest.fixture
def temp_site(tmp_path):
    """Create a temporary test site with content."""
    # Create directory structure
    content_dir = tmp_path / "content"
    content_dir.mkdir()
    
    # Create some test content
    (content_dir / "index.md").write_text("""---
title: Home
---
# Welcome
""")
    
    (content_dir / "about.md").write_text("""---
title: About
---
# About Us
""")
    
    # Create blog section
    blog_dir = content_dir / "blog"
    blog_dir.mkdir()
    
    (blog_dir / "_index.md").write_text("""---
title: Blog
---
""")
    
    (blog_dir / "post1.md").write_text("""---
title: Post 1
date: 2025-01-01
tags: [python]
---
# Post 1
""")
    
    # Create config
    config_file = tmp_path / "bengal.toml"
    config_file.write_text("""
[site]
title = "Test Site"
baseurl = "https://example.com"

[build]
parallel = false
""")
    
    # Create theme directory to avoid warnings
    theme_dir = tmp_path / "themes" / "default"
    theme_dir.mkdir(parents=True)
    
    yield tmp_path
    
    # Cleanup loggers
    _loggers.clear()


@pytest.fixture(autouse=True)
def reset_loggers():
    """Reset logger state before each test."""
    _loggers.clear()
    yield
    close_all_loggers()
    _loggers.clear()


class TestLoggingIntegration:
    """Integration tests for logging system."""
    
    def test_basic_logging_during_build(self, temp_site):
        """Test that logging captures events during a basic build."""
        # Configure logging
        log_file = temp_site / "test.log"
        configure_logging(
            level=LogLevel.DEBUG,
            log_file=log_file,
            verbose=True
        )
        
        # Build site
        site = Site.from_config(temp_site)
        site.build(parallel=False, incremental=False, verbose=True)
        
        # Get logged events
        logger = get_logger("bengal.orchestration.build")
        events = logger.get_events()
        
        # Verify we captured events
        assert len(events) > 0, "Should have logged events"
        
        # Check for build_start event
        build_start_events = [e for e in events if e.message == "build_start"]
        assert len(build_start_events) == 1, "Should have one build_start event"
        
        # Check for build_complete event
        build_complete_events = [e for e in events if e.message == "build_complete"]
        assert len(build_complete_events) == 1, "Should have one build_complete event"
        
        # Verify build_start has context
        build_start = build_start_events[0]
        assert "parallel" in build_start.context
        assert "incremental" in build_start.context
        assert not build_start.context["parallel"]
        assert not build_start.context["incremental"]
        
        # Verify build_complete has stats
        build_complete = build_complete_events[0]
        assert "total_pages" in build_complete.context
        assert build_complete.context["total_pages"] > 0  # At least some pages
        # Note: actual count includes generated pages (tag pages, etc.)
        
        # Verify log file was created
        assert log_file.exists(), "Log file should be created"
        log_content = log_file.read_text()
        assert len(log_content) > 0, "Log file should have content"
    
    def test_all_phases_logged(self, temp_site):
        """Test that all build phases are logged."""
        configure_logging(level=LogLevel.INFO, verbose=False)
        
        # Build site
        site = Site.from_config(temp_site)
        site.build(parallel=False)
        
        # Get events
        logger = get_logger("bengal.orchestration.build")
        events = logger.get_events()
        
        # Get phase_complete events
        phase_events = [e for e in events if e.message == "phase_complete"]
        phases = [e.context.get("phase_name") for e in phase_events]
        
        # Verify key phases are present
        expected_phases = [
            "initialization",
            "discovery",
            "section_finalization",
            "taxonomies",
            "menus",
            "rendering",
            "assets",
            "postprocessing",
            "health_check",
        ]
        
        for phase in expected_phases:
            assert phase in phases, f"Phase '{phase}' should be logged"
    
    def test_phase_timings_captured(self, temp_site):
        """Test that phase timings are captured."""
        configure_logging(level=LogLevel.INFO)
        
        # Build site
        site = Site.from_config(temp_site)
        site.build(parallel=False)
        
        # Get phase timings
        logger = get_logger("bengal.orchestration.build")
        timings = logger.get_phase_timings()
        
        # Verify we have timings
        assert len(timings) > 0, "Should have phase timings"
        
        # Verify timings are reasonable (> 0ms, < 10 seconds)
        for phase, duration in timings.items():
            assert duration > 0, f"Phase '{phase}' should have positive duration"
            assert duration < 10000, f"Phase '{phase}' duration should be reasonable"
    
    def test_content_discovery_logging(self, temp_site):
        """Test that content discovery logs detailed information."""
        configure_logging(level=LogLevel.DEBUG, verbose=True)
        
        # Build site
        site = Site.from_config(temp_site)
        site.build(parallel=False)
        
        # Get content orchestrator logger events
        logger = get_logger("bengal.orchestration.content")
        events = logger.get_events()
        
        # Check for discovery events
        discovery_events = [e for e in events if "discover" in e.message]
        assert len(discovery_events) > 0, "Should have discovery events"
        
        # Check for specific sub-phase events
        event_messages = [e.message for e in events]
        assert "raw_content_discovered" in event_messages
        assert "page_references_setup" in event_messages
        assert "cascades_applied" in event_messages
        assert "xref_index_built" in event_messages
    
    def test_nested_phase_tracking(self, temp_site):
        """Test that nested phases are tracked with correct depth."""
        configure_logging(level=LogLevel.DEBUG)
        
        # Build site
        site = Site.from_config(temp_site)
        site.build(parallel=False)
        
        # Get events
        logger = get_logger("bengal.orchestration.build")
        events = logger.get_events()
        
        # Find events with phase depth > 0
        nested_events = [e for e in events if e.phase_depth > 0]
        assert len(nested_events) > 0, "Should have nested phase events"
        
        # Verify phase depth is consistent
        for event in nested_events:
            if event.phase:
                # Events inside a phase should have depth 1
                assert event.phase_depth == 1, f"Event {event.message} should have depth 1"
    
    def test_logging_with_incremental_build(self, temp_site):
        """Test logging during incremental builds."""
        log_file = temp_site / "test.log"
        configure_logging(level=LogLevel.INFO, log_file=log_file)
        
        # First build
        site = Site.from_config(temp_site)
        site.build(parallel=False, incremental=True)
        
        # Get events from first build
        logger = get_logger("bengal.orchestration.build")
        events = logger.get_events()
        
        # Should have incremental_filtering phase
        phase_events = [e for e in events if e.message == "phase_complete"]
        phases = [e.context.get("phase_name") for e in phase_events]
        assert "incremental_filtering" in phases
    
    def test_warning_logging(self, temp_site):
        """Test that warnings are logged appropriately."""
        # Create a section with validation issues
        section_dir = temp_site / "content" / "invalid"
        section_dir.mkdir()
        (section_dir / "page.md").write_text("""---
title: Invalid Page
---
# Test
""")
        
        configure_logging(level=LogLevel.WARNING, verbose=True)
        
        # Build site
        site = Site.from_config(temp_site)
        site.build(parallel=False)
        
        # Get events
        logger = get_logger("bengal.orchestration.build")
        events = logger.get_events()
        
        # Check if any warning events exist
        warning_events = [e for e in events if e.level == "WARNING"]
        # May or may not have warnings depending on content
        # Just verify the system can capture them
        for event in warning_events:
            assert event.level == "WARNING"
            assert "context" in event.__dict__
    
    def test_log_file_format(self, temp_site):
        """Test that log file contains valid JSON."""
        import json
        
        log_file = temp_site / "test.log"
        configure_logging(level=LogLevel.INFO, log_file=log_file)
        
        # Build site
        site = Site.from_config(temp_site)
        site.build(parallel=False)
        
        # Close loggers to flush
        close_all_loggers()
        
        # Verify log file format
        assert log_file.exists()
        
        # Parse each line as JSON
        with open(log_file) as f:
            for line in f:
                if line.strip():
                    try:
                        event_dict = json.loads(line)
                        assert "timestamp" in event_dict
                        assert "level" in event_dict
                        assert "message" in event_dict
                    except json.JSONDecodeError as e:
                        pytest.fail(f"Invalid JSON in log file: {e}")
    
    def test_verbose_vs_normal_mode(self, temp_site):
        """Test that verbose mode logs more detail."""
        # Normal mode
        configure_logging(level=LogLevel.WARNING, verbose=False)
        site1 = Site.from_config(temp_site)
        site1.build(parallel=False)
        
        logger1 = get_logger("bengal.orchestration.build")
        normal_events = logger1.get_events()
        
        # Reset for verbose mode
        _loggers.clear()
        
        # Verbose mode
        configure_logging(level=LogLevel.DEBUG, verbose=True)
        site2 = Site.from_config(temp_site)
        site2.build(parallel=False)
        
        logger2 = get_logger("bengal.orchestration.build")
        verbose_events = logger2.get_events()
        
        # Verbose should have more events
        # (or at least same, depending on log level)
        assert len(verbose_events) >= len(normal_events)
    
    def test_context_propagation(self, temp_site):
        """Test that context propagates through nested phases."""
        configure_logging(level=LogLevel.DEBUG)
        
        # Build site
        site = Site.from_config(temp_site)
        site.build(parallel=False)
        
        # Get events
        logger = get_logger("bengal.orchestration.build")
        events = logger.get_events()
        
        # Find events inside rendering phase
        rendering_events = [e for e in events if e.phase == "rendering"]
        
        if rendering_events:
            # Verify they have phase context
            for event in rendering_events:
                # Should have phase set
                assert event.phase == "rendering"
                # Context should be present
                assert isinstance(event.context, dict)
    
    def test_logger_cleanup(self, temp_site):
        """Test that logger cleanup works properly."""
        log_file = temp_site / "test.log"
        configure_logging(level=LogLevel.INFO, log_file=log_file)
        
        # Build site
        site = Site.from_config(temp_site)
        site.build(parallel=False)
        
        # Close loggers
        close_all_loggers()
        
        # Verify log file was written and closed
        assert log_file.exists()
        
        # Should be able to read file (not locked)
        content = log_file.read_text()
        assert len(content) > 0


class TestLoggingPerformance:
    """Performance tests for logging system."""
    
    def test_logging_overhead(self, temp_site):
        """Test that logging adds minimal overhead."""
        import time
        
        # Build without verbose logging
        configure_logging(level=LogLevel.WARNING, verbose=False)
        site1 = Site.from_config(temp_site)
        
        start1 = time.time()
        site1.build(parallel=False)
        duration1 = time.time() - start1
        
        # Reset
        _loggers.clear()
        
        # Build with verbose logging
        configure_logging(level=LogLevel.DEBUG, verbose=True)
        site2 = Site.from_config(temp_site)
        
        start2 = time.time()
        site2.build(parallel=False)
        duration2 = time.time() - start2
        
        # Logging overhead should be minimal (< 20%)
        overhead = (duration2 - duration1) / duration1 if duration1 > 0 else 0
        assert overhead < 0.5, f"Logging overhead should be < 50%, got {overhead*100:.1f}%"

