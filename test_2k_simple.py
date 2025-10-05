#!/usr/bin/env python
"""Simple 2K page test without tracemalloc."""

import sys
import tempfile
from pathlib import Path
import time
import psutil
import os

from bengal.core.site import Site
from bengal.utils.logger import configure_logging, LogLevel

def get_memory_mb():
    """Get current process memory in MB."""
    process = psutil.Process(os.getpid())
    return process.memory_info().rss / 1024 / 1024

print('='*60)
print('SIMPLE 2K PAGE TEST (psutil memory tracking)')
print('='*60)

# Generate site
print('\n[1/4] Generating 2K-page test site...')
tmp_path = Path(tempfile.mkdtemp())
site_root = tmp_path / 'site_2k'
site_root.mkdir()

# Config
(site_root / 'bengal.toml').write_text('''[site]
title = "Test"
baseurl = "https://example.com"
[build]
parallel = false
''')

# Content
content_dir = site_root / 'content'
content_dir.mkdir()
(content_dir / 'index.md').write_text('---\ntitle: Home\n---\n# Home')

print('Creating 2000 pages across 10 sections...')
gen_start = time.time()
for s in range(10):
    sd = content_dir / f's{s:02d}'
    sd.mkdir()
    (sd / '_index.md').write_text(f'---\ntitle: S{s}\n---\n# S{s}')
    
    for p in range(200):
        (sd / f'p{p:03d}.md').write_text(
            f'---\ntitle: P{s}-{p}\ndate: 2025-01-01\ntags: [t{p%10}]\n---\n# Page\n\nContent'
        )
    
    print(f'  Section {s+1}/10 complete')

gen_time = time.time() - gen_start
print(f'\n✓ Site generated in {gen_time:.1f}s')

# Setup
print('\n[2/4] Starting memory tracking...')
configure_logging(level=LogLevel.WARNING, track_memory=False)
baseline_mb = get_memory_mb()
print(f'  Baseline memory: {baseline_mb:.1f}MB')

# Build
print('\n[3/4] Building site...')
print('  Loading config...')
site = Site.from_config(site_root)
after_load_mb = get_memory_mb()
print(f'  Memory after config load: {after_load_mb:.1f}MB')

print('  Running build (estimated 3-5 minutes)...')
build_start = time.time()
stats = site.build(parallel=False)
build_time = time.time() - build_start

print(f'\n✓ Build complete in {build_time:.1f}s ({build_time/60:.1f} minutes)')

# Results
print('\n[4/4] Memory results:')
final_mb = get_memory_mb()
used_mb = final_mb - baseline_mb

print(f'  Total pages: {stats.total_pages}')
print(f'  Regular pages: {stats.regular_pages}')
print(f'  Build time: {build_time:.1f}s')
print(f'  Baseline memory: {baseline_mb:.1f}MB')
print(f'  Final memory: {final_mb:.1f}MB')
print(f'  Memory used: {used_mb:.1f}MB')
print(f'  Per page: {used_mb/stats.regular_pages:.3f}MB')

print('\n' + '='*60)
print('Test complete!')

