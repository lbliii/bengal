#!/usr/bin/env python3
"""
Demo of Bengal's structured logging system.

Run this to see logging in action:
    python examples/logging_demo.py

Or in verbose mode:
    python examples/logging_demo.py --verbose
"""

import time
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from bengal.utils.logger import get_logger, configure_logging, LogLevel, print_all_summaries


def simulate_discovery(logger):
    """Simulate content discovery phase."""
    files = ["index.md", "about.md", "blog/post1.md", "blog/post2.md"]
    
    logger.debug("scanning_content_directory", path="/content")
    
    for i, file in enumerate(files):
        time.sleep(0.01)  # Simulate work
        logger.debug("discovered_file", file=file, index=i+1, total=len(files))
    
    logger.info("discovery_complete", files=len(files))


def simulate_rendering(logger):
    """Simulate page rendering phase."""
    pages = [
        {"title": "Home", "size": 1024},
        {"title": "About", "size": 512},
        {"title": "Post 1", "size": 2048},
        {"title": "Post 2", "size": 1536},
    ]
    
    for page in pages:
        time.sleep(0.02)  # Simulate work
        logger.debug("rendering_page", page=page["title"], size=page["size"])
    
    logger.info("rendering_complete", pages=len(pages), total_size=sum(p["size"] for p in pages))


def simulate_assets(logger):
    """Simulate asset processing phase."""
    assets = ["style.css", "script.js", "logo.png"]
    
    for asset in assets:
        time.sleep(0.01)  # Simulate work
        logger.debug("processing_asset", asset=asset)
    
    logger.info("assets_complete", count=len(assets))


def simulate_postprocessing(logger):
    """Simulate post-processing phase."""
    tasks = ["sitemap", "rss", "search_index"]
    
    for task in tasks:
        time.sleep(0.01)  # Simulate work
        logger.debug(f"generating_{task}")
    
    logger.info("postprocessing_complete", tasks=len(tasks))


def simulate_build(verbose=False):
    """Simulate a complete build with logging."""
    # Configure logging
    log_file = Path(".demo-build.log")
    configure_logging(
        level=LogLevel.DEBUG if verbose else LogLevel.INFO,
        log_file=log_file,
        verbose=verbose
    )
    
    # Get logger
    logger = get_logger("demo.build")
    
    # Start build
    logger.info("build_start", mode="demo", verbose=verbose)
    print("\n🔨 Building demo site...\n")
    
    # Phase 1: Discovery
    with logger.phase("discovery", content_dir="/content"):
        simulate_discovery(logger)
    
    # Phase 2: Rendering
    with logger.phase("rendering", parallel=False):
        simulate_rendering(logger)
    
    # Phase 3: Assets
    with logger.phase("assets", count=3):
        simulate_assets(logger)
    
    # Phase 4: Post-processing
    with logger.phase("postprocessing"):
        simulate_postprocessing(logger)
    
    # Complete
    logger.info("build_complete", success=True)
    
    # Print timing summary
    print_all_summaries()
    
    print(f"\n📝 Log file written to: {log_file}")
    print(f"   View with: cat {log_file} | jq '.'")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Demo Bengal's logging system")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    args = parser.parse_args()
    
    simulate_build(verbose=args.verbose)

