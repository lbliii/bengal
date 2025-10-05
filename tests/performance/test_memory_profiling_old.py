"""
Memory profiling tests for Bengal SSG.

Tests memory usage at different scales to ensure the system can handle
large sites without running out of memory.
"""

import pytest
from pathlib import Path
import tracemalloc
import gc

from bengal.core.site import Site
from bengal.utils.logger import configure_logging, LogLevel, close_all_loggers, _loggers


@pytest.fixture
def site_generator(tmp_path):
    """Factory fixture for generating test sites of various sizes."""
    
    def _generate_site(page_count: int, sections: int = 5) -> Path:
        """
        Generate a test site with specified number of pages.
        
        Args:
            page_count: Total number of pages to generate
            sections: Number of top-level sections
            
        Returns:
            Path to the generated site root
        """
        site_root = tmp_path / f"site_{page_count}pages"
        site_root.mkdir(exist_ok=True)
        
        # Create config
        config_file = site_root / "bengal.toml"
        config_file.write_text(f"""
[site]
title = "Test Site {page_count} Pages"
baseurl = "https://example.com"

[build]
parallel = false
""")
        
        # Create content directory
        content_dir = site_root / "content"
        content_dir.mkdir(exist_ok=True)
        
        # Create index
        (content_dir / "index.md").write_text("""---
title: Home
---
# Welcome

This is a test site for memory profiling.
""")
        
        # Calculate pages per section
        pages_per_section = (page_count - 1) // sections  # -1 for index
        
        # Create sections with pages
        for section_idx in range(sections):
            section_name = f"section{section_idx:03d}"
            section_dir = content_dir / section_name
            section_dir.mkdir(exist_ok=True)
            
            # Section index
            (section_dir / "_index.md").write_text(f"""---
title: Section {section_idx}
---
# Section {section_idx}

This is section {section_idx}.
""")
            
            # Pages in section
            pages_in_this_section = min(pages_per_section, page_count - 1 - (section_idx * pages_per_section))
            for page_idx in range(pages_in_this_section):
                page_file = section_dir / f"page{page_idx:04d}.md"
                page_file.write_text(f"""---
title: Page {section_idx}-{page_idx}
date: 2025-01-{(page_idx % 28) + 1:02d}
tags: [tag{page_idx % 10}, tag{page_idx % 20}]
---
# Page {section_idx}-{page_idx}

This is test page {page_idx} in section {section_idx}.

## Content

Lorem ipsum dolor sit amet, consectetur adipiscing elit. 
Sed do eiusmod tempor incididunt ut labore et dolore magna aliqua.

### Code Example

```python
def hello_world():
    print("Hello from page {section_idx}-{page_idx}")
    return 42
```

### List

- Item 1
- Item 2
- Item 3

[Link to home](/)
""")
        
        return site_root
    
    return _generate_site


@pytest.fixture(autouse=True)
def reset_loggers_and_memory():
    """Reset logger state and run garbage collection before each test."""
    _loggers.clear()
    gc.collect()
    yield
    close_all_loggers()
    _loggers.clear()
    gc.collect()


class TestMemoryProfiling:
    """Memory profiling tests at different scales."""
    
    def test_100_page_site_memory(self, site_generator):
        """Test memory usage for a 100-page site."""
        # Enable memory tracking
        tracemalloc.start()
        configure_logging(level=LogLevel.INFO, track_memory=True)
        
        # Generate site
        site_root = site_generator(page_count=100, sections=5)
        
        # Get baseline memory
        gc.collect()
        baseline_memory = tracemalloc.get_traced_memory()[0] / 1024 / 1024  # MB
        
        # Build site
        site = Site.from_config(site_root)
        stats = site.build(parallel=False)
        
        # Get peak memory
        current_memory, peak_memory = tracemalloc.get_traced_memory()
        peak_mb = peak_memory / 1024 / 1024
        memory_used = (current_memory - (baseline_memory * 1024 * 1024)) / 1024 / 1024
        
        tracemalloc.stop()
        
        # Assertions
        assert stats.regular_pages >= 100, f"Should have at least 100 regular pages, got {stats.regular_pages}"
        assert peak_mb < 500, f"Peak memory {peak_mb:.1f}MB exceeds 500MB threshold for 100 pages"
        
        print(f"\n100-page site:")
        print(f"  Baseline: {baseline_memory:.1f}MB")
        print(f"  Peak: {peak_mb:.1f}MB")
        print(f"  Used: {memory_used:.1f}MB")
        print(f"  Per page: {memory_used/100:.2f}MB")
    
    def test_1k_page_site_memory(self, site_generator):
        """Test memory usage for a 1K-page site."""
        # Enable memory tracking
        tracemalloc.start()
        configure_logging(level=LogLevel.INFO, track_memory=True)
        
        # Generate site
        site_root = site_generator(page_count=1000, sections=10)
        
        # Get baseline memory
        gc.collect()
        baseline_memory = tracemalloc.get_traced_memory()[0] / 1024 / 1024  # MB
        
        # Build site
        site = Site.from_config(site_root)
        stats = site.build(parallel=False)
        
        # Get peak memory
        current_memory, peak_memory = tracemalloc.get_traced_memory()
        peak_mb = peak_memory / 1024 / 1024
        memory_used = (current_memory - (baseline_memory * 1024 * 1024)) / 1024 / 1024
        
        tracemalloc.stop()
        
        # Assertions
        assert stats.total_pages >= 1000  # May have taxonomy pages too
        assert peak_mb < 2000, f"Peak memory {peak_mb:.1f}MB exceeds 2GB threshold for 1K pages"
        
        print(f"\n1K-page site:")
        print(f"  Baseline: {baseline_memory:.1f}MB")
        print(f"  Peak: {peak_mb:.1f}MB")
        print(f"  Used: {memory_used:.1f}MB")
        print(f"  Per page: {memory_used/1000:.2f}MB")
    
    def test_500_page_site_memory(self, site_generator):
        """Test memory usage for a 500-page site."""
        # Enable memory tracking
        tracemalloc.start()
        configure_logging(level=LogLevel.INFO, track_memory=True)
        
        # Generate site
        site_root = site_generator(page_count=500, sections=5)
        
        # Get baseline memory
        gc.collect()
        baseline_memory = tracemalloc.get_traced_memory()[0] / 1024 / 1024  # MB
        
        # Build site
        site = Site.from_config(site_root)
        stats = site.build(parallel=False)
        
        # Get peak memory
        current_memory, peak_memory = tracemalloc.get_traced_memory()
        peak_mb = peak_memory / 1024 / 1024
        memory_used = (current_memory - (baseline_memory * 1024 * 1024)) / 1024 / 1024
        
        tracemalloc.stop()
        
        # Assertions
        assert stats.regular_pages >= 500, f"Should have at least 500 regular pages, got {stats.regular_pages}"
        assert peak_mb < 750, f"Peak memory {peak_mb:.1f}MB exceeds 750MB threshold for 500 pages"
        
        print(f"\n500-page site:")
        print(f"  Baseline: {baseline_memory:.1f}MB")
        print(f"  Peak: {peak_mb:.1f}MB")
        print(f"  Used: {memory_used:.1f}MB")
        print(f"  Per page: {memory_used/500:.3f}MB")
    
    def test_1200_page_site_memory(self, site_generator):
        """Test memory usage for a 1.2K-page site."""
        # Enable memory tracking
        tracemalloc.start()
        configure_logging(level=LogLevel.INFO, track_memory=True)
        
        # Generate site
        print("\nGenerating 1.2K-page site...")
        site_root = site_generator(page_count=1200, sections=10)
        print(f"Site generated at: {site_root}")
        
        # Get baseline memory
        gc.collect()
        baseline_memory = tracemalloc.get_traced_memory()[0] / 1024 / 1024  # MB
        
        # Build site
        print("Starting build...")
        site = Site.from_config(site_root)
        stats = site.build(parallel=False)
        
        # Get peak memory
        current_memory, peak_memory = tracemalloc.get_traced_memory()
        peak_mb = peak_memory / 1024 / 1024
        memory_used = (current_memory - (baseline_memory * 1024 * 1024)) / 1024 / 1024
        
        tracemalloc.stop()
        
        # Assertions
        assert stats.regular_pages >= 1200, f"Should have at least 1200 regular pages, got {stats.regular_pages}"
        assert peak_mb < 850, f"Peak memory {peak_mb:.1f}MB exceeds 850MB threshold for 1.2K pages"
        
        print(f"\n1.2K-page site:")
        print(f"  Baseline: {baseline_memory:.1f}MB")
        print(f"  Peak: {peak_mb:.1f}MB")
        print(f"  Used: {memory_used:.1f}MB")
        print(f"  Per page: {memory_used/1200:.3f}MB")
    
    def test_1500_page_site_memory(self, site_generator):
        """Test memory usage for a 1.5K-page site."""
        # Enable memory tracking
        tracemalloc.start()
        configure_logging(level=LogLevel.INFO, track_memory=True)
        
        # Generate site
        print("\nGenerating 1.5K-page site...")
        site_root = site_generator(page_count=1500, sections=10)
        print(f"Site generated at: {site_root}")
        
        # Get baseline memory
        gc.collect()
        baseline_memory = tracemalloc.get_traced_memory()[0] / 1024 / 1024  # MB
        
        # Build site
        print("Starting build...")
        site = Site.from_config(site_root)
        stats = site.build(parallel=False)
        
        # Get peak memory
        current_memory, peak_memory = tracemalloc.get_traced_memory()
        peak_mb = peak_memory / 1024 / 1024
        memory_used = (current_memory - (baseline_memory * 1024 * 1024)) / 1024 / 1024
        
        tracemalloc.stop()
        
        # Assertions
        assert stats.regular_pages >= 1500, f"Should have at least 1500 regular pages, got {stats.regular_pages}"
        assert peak_mb < 900, f"Peak memory {peak_mb:.1f}MB exceeds 900MB threshold for 1.5K pages"
        
        print(f"\n1.5K-page site:")
        print(f"  Baseline: {baseline_memory:.1f}MB")
        print(f"  Peak: {peak_mb:.1f}MB")
        print(f"  Used: {memory_used:.1f}MB")
        print(f"  Per page: {memory_used/1500:.3f}MB")
    
    def test_2k_page_site_memory(self, site_generator):
        """Test memory usage for a 2K-page site."""
        # Enable memory tracking
        tracemalloc.start()
        configure_logging(level=LogLevel.INFO, track_memory=True)
        
        # Generate site
        print("\nGenerating 2K-page site...")
        site_root = site_generator(page_count=2000, sections=10)
        print(f"Site generated at: {site_root}")
        
        # Get baseline memory
        gc.collect()
        baseline_memory = tracemalloc.get_traced_memory()[0] / 1024 / 1024  # MB
        
        # Build site
        print("Starting build...")
        site = Site.from_config(site_root)
        stats = site.build(parallel=False)
        
        # Get peak memory
        current_memory, peak_memory = tracemalloc.get_traced_memory()
        peak_mb = peak_memory / 1024 / 1024
        memory_used = (current_memory - (baseline_memory * 1024 * 1024)) / 1024 / 1024
        
        tracemalloc.stop()
        
        # Assertions
        assert stats.regular_pages >= 2000, f"Should have at least 2000 regular pages, got {stats.regular_pages}"
        assert peak_mb < 1000, f"Peak memory {peak_mb:.1f}MB exceeds 1GB threshold for 2K pages"
        
        print(f"\n2K-page site:")
        print(f"  Baseline: {baseline_memory:.1f}MB")
        print(f"  Peak: {peak_mb:.1f}MB")
        print(f"  Used: {memory_used:.1f}MB")
        print(f"  Per page: {memory_used/2000:.3f}MB")
    
    def test_5k_page_site_memory(self, site_generator):
        """Test memory usage for a 5K-page site."""
        # Enable memory tracking
        tracemalloc.start()
        configure_logging(level=LogLevel.INFO, track_memory=True)
        
        # Generate site
        site_root = site_generator(page_count=5000, sections=10)
        
        # Get baseline memory
        gc.collect()
        baseline_memory = tracemalloc.get_traced_memory()[0] / 1024 / 1024  # MB
        
        # Build site
        site = Site.from_config(site_root)
        stats = site.build(parallel=False)
        
        # Get peak memory
        current_memory, peak_memory = tracemalloc.get_traced_memory()
        peak_mb = peak_memory / 1024 / 1024
        memory_used = (current_memory - (baseline_memory * 1024 * 1024)) / 1024 / 1024
        
        tracemalloc.stop()
        
        # Assertions
        assert stats.regular_pages >= 5000, f"Should have at least 5000 regular pages, got {stats.regular_pages}"
        assert peak_mb < 2000, f"Peak memory {peak_mb:.1f}MB exceeds 2GB threshold for 5K pages"
        
        print(f"\n5K-page site:")
        print(f"  Baseline: {baseline_memory:.1f}MB")
        print(f"  Peak: {peak_mb:.1f}MB")
        print(f"  Used: {memory_used:.1f}MB")
        print(f"  Per page: {memory_used/5000:.3f}MB")
    
    @pytest.mark.slow
    def test_10k_page_site_memory(self, site_generator):
        """Test memory usage for a 10K-page site."""
        # Enable memory tracking
        tracemalloc.start()
        configure_logging(level=LogLevel.INFO, track_memory=True)
        
        # Generate site
        print("\nGenerating 10K-page site...")
        import time
        gen_start = time.time()
        site_root = site_generator(page_count=10000, sections=20)
        gen_time = time.time() - gen_start
        print(f"Site generated in {gen_time:.1f}s at: {site_root}")
        
        # Get baseline memory
        gc.collect()
        baseline_memory = tracemalloc.get_traced_memory()[0] / 1024 / 1024  # MB
        
        # Build site
        print("Loading config...")
        site = Site.from_config(site_root)
        print(f"Starting build... (this will take ~20 minutes)")
        build_start = time.time()
        stats = site.build(parallel=False)
        build_time = time.time() - build_start
        print(f"Build completed in {build_time:.1f}s ({build_time/60:.1f} minutes)")
        
        # Get peak memory
        current_memory, peak_memory = tracemalloc.get_traced_memory()
        peak_mb = peak_memory / 1024 / 1024
        memory_used = (current_memory - (baseline_memory * 1024 * 1024)) / 1024 / 1024
        
        tracemalloc.stop()
        
        # Assertions
        assert stats.total_pages >= 10000  # May have taxonomy pages too
        assert peak_mb < 8000, f"Peak memory {peak_mb:.1f}MB exceeds 8GB threshold for 10K pages"
        
        print(f"\n10K-page site:")
        print(f"  Total pages: {stats.total_pages}")
        print(f"  Build time: {build_time:.1f}s ({build_time/60:.1f} minutes)")
        print(f"  Baseline: {baseline_memory:.1f}MB")
        print(f"  Peak: {peak_mb:.1f}MB")
        print(f"  Used: {memory_used:.1f}MB")
        print(f"  Per page: {memory_used/10000:.2f}MB")
    
    def test_memory_leak_detection(self, site_generator):
        """Test for memory leaks by building multiple times."""
        tracemalloc.start()
        configure_logging(level=LogLevel.WARNING, track_memory=True)
        
        # Generate small site
        site_root = site_generator(page_count=50, sections=3)
        
        # Build 3 times and track memory growth
        memory_samples = []
        baseline_memory = tracemalloc.get_traced_memory()[0]
        
        for i in range(3):
            gc.collect()
            before_memory = tracemalloc.get_traced_memory()[0]
            
            site = Site.from_config(site_root)
            site.build(parallel=False)
            
            gc.collect()
            after_memory = tracemalloc.get_traced_memory()[0]
            memory_delta = (after_memory - before_memory) / 1024 / 1024
            memory_samples.append(after_memory)
            
            print(f"\n  Build {i+1}: delta={memory_delta:.1f}MB, total={after_memory/1024/1024:.1f}MB")
        
        tracemalloc.stop()
        
        # Check for true memory leaks: memory should plateau, not grow linearly
        # First build will allocate, subsequent builds should stabilize
        # A leak would show memory growing on builds 2 and 3
        if len(memory_samples) >= 3:
            build1_to_2_growth = (memory_samples[1] - memory_samples[0]) / 1024 / 1024
            build2_to_3_growth = (memory_samples[2] - memory_samples[1]) / 1024 / 1024
            
            # If memory keeps growing after stabilization, that's a leak
            # Allow first build to allocate, but subsequent builds should be stable
            assert build2_to_3_growth < 5, \
                f"Memory leak detected: grew {build2_to_3_growth:.1f}MB from build 2 to 3 (should be < 5MB)"
            
            print(f"\n  Build 1→2 growth: {build1_to_2_growth:.1f}MB (initial allocation)")
            print(f"  Build 2→3 growth: {build2_to_3_growth:.1f}MB (should be minimal)")
            print(f"  ✓ No memory leak detected")
    
    def test_phase_memory_breakdown(self, site_generator):
        """Test memory usage breakdown by phase."""
        tracemalloc.start()
        configure_logging(level=LogLevel.INFO, track_memory=True, verbose=True)
        
        # Generate site
        site_root = site_generator(page_count=100, sections=5)
        
        # Build site
        site = Site.from_config(site_root)
        site.build(parallel=False)
        
        # Get logger events
        from bengal.utils.logger import get_logger
        logger = get_logger("bengal.orchestration.build")
        events = logger.get_events()
        
        # Extract phase memory usage
        phase_memory = {}
        for event in events:
            if event.message == "phase_complete" and event.memory_mb is not None:
                phase = event.context.get("phase_name", event.phase)
                if phase:
                    phase_memory[phase] = {
                        'delta_mb': event.memory_mb,
                        'peak_mb': event.peak_memory_mb
                    }
        
        tracemalloc.stop()
        
        # Verify we captured memory data
        assert len(phase_memory) > 0, "Should have captured memory data for phases"
        
        # Print breakdown
        print("\nMemory usage by phase:")
        for phase, mem in sorted(phase_memory.items(), key=lambda x: x[1]['delta_mb'], reverse=True):
            print(f"  {phase:25s} Δ{mem['delta_mb']:+7.1f}MB  peak:{mem['peak_mb']:7.1f}MB")
        
        # Check that major phases are tracked
        assert 'discovery' in phase_memory or 'rendering' in phase_memory, \
            "Should track memory for major phases"

