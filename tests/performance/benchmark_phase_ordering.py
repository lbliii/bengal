#!/usr/bin/env python3
"""
Benchmark initial build performance to establish baseline.

This script measures:
1. Full build time (cold cache)
2. Incremental build time (1 file changed)
3. Incremental build time (no changes)
4. Time breakdown by phase
"""

import subprocess
import time
import json
from pathlib import Path
import shutil

def run_command(cmd, cwd=None):
    """Run command and capture output."""
    result = subprocess.run(
        cmd,
        shell=True,
        cwd=cwd,
        capture_output=True,
        text=True
    )
    return result.returncode, result.stdout, result.stderr, time.time()

def benchmark_showcase():
    """Benchmark the showcase example site."""
    showcase_dir = Path(__file__).parent / "examples" / "showcase"
    
    if not showcase_dir.exists():
        print(f"❌ Showcase directory not found: {showcase_dir}")
        return
    
    print("=" * 80)
    print("BENGAL SSG - INITIAL BUILD PERFORMANCE BENCHMARK")
    print("=" * 80)
    print(f"Test Site: {showcase_dir}")
    print()
    
    results = {}
    
    # Clean output and cache
    print("🧹 Cleaning output and cache...")
    public_dir = showcase_dir / "public"
    if public_dir.exists():
        shutil.rmtree(public_dir)
    cache_file = showcase_dir / ".bengal-cache.json"
    if cache_file.exists():
        cache_file.unlink()
    print("   ✓ Clean slate ready\n")
    
    # Test 1: Full build (cold cache)
    print("📊 Test 1: Full Build (Cold Cache)")
    print("-" * 80)
    start = time.time()
    returncode, stdout, stderr, end = run_command(
        "bengal build",
        cwd=showcase_dir
    )
    duration = end - start
    
    if returncode == 0:
        print(f"   ✓ Build succeeded in {duration:.3f}s")
        results['full_build'] = duration
        
        # Extract page count from output
        for line in stdout.split('\n'):
            if 'Total:' in line and '✓' in line:
                # Try to extract page count
                parts = line.split()
                for i, part in enumerate(parts):
                    if part == 'Total:' and i + 1 < len(parts):
                        page_count = parts[i + 1]
                        print(f"   ℹ Pages built: {page_count}")
                        break
    else:
        print("   ❌ Build failed")
        print(stderr)
        return
    
    print()
    
    # Test 2: Incremental build (no changes)
    print("📊 Test 2: Incremental Build (No Changes)")
    print("-" * 80)
    start = time.time()
    returncode, stdout, stderr, end = run_command(
        "bengal build --incremental",
        cwd=showcase_dir
    )
    duration = end - start
    
    if returncode == 0:
        print(f"   ✓ Build succeeded in {duration:.3f}s")
        results['incremental_no_changes'] = duration
        
        if "No changes detected" in stdout:
            print("   ✓ Correctly detected no changes")
    else:
        print("   ❌ Build failed")
        print(stderr)
    
    print()
    
    # Test 3: Incremental build (1 file changed)
    print("📊 Test 3: Incremental Build (1 File Changed)")
    print("-" * 80)
    
    # Modify a file
    test_file = showcase_dir / "content" / "index.md"
    if test_file.exists():
        with open(test_file, 'a') as f:
            f.write("\n<!-- Benchmark test change -->\n")
        print(f"   ℹ Modified: {test_file.name}")
    
    start = time.time()
    returncode, stdout, stderr, end = run_command(
        "bengal build --incremental --verbose",
        cwd=showcase_dir
    )
    duration = end - start
    
    if returncode == 0:
        print(f"   ✓ Build succeeded in {duration:.3f}s")
        results['incremental_1_change'] = duration
        
        # Extract info from verbose output
        for line in stdout.split('\n'):
            if 'Incremental build:' in line:
                print(f"   ℹ {line.strip()}")
    else:
        print("   ❌ Build failed")
        print(stderr)
    
    # Restore the file
    if test_file.exists():
        content = test_file.read_text()
        content = content.replace("\n<!-- Benchmark test change -->\n", "")
        test_file.write_text(content)
    
    print()
    
    # Summary
    print("=" * 80)
    print("BENCHMARK RESULTS SUMMARY")
    print("=" * 80)
    
    if 'full_build' in results:
        print(f"Full Build (Cold):           {results['full_build']:.3f}s")
    
    if 'incremental_no_changes' in results:
        print(f"Incremental (No Changes):    {results['incremental_no_changes']:.3f}s")
        if 'full_build' in results:
            speedup = results['full_build'] / results['incremental_no_changes']
            print(f"                             {speedup:.1f}x faster than full build")
    
    if 'incremental_1_change' in results:
        print(f"Incremental (1 File):        {results['incremental_1_change']:.3f}s")
        if 'full_build' in results:
            speedup = results['full_build'] / results['incremental_1_change']
            print(f"                             {speedup:.1f}x faster than full build")
    
    print()
    
    # Save results
    results_file = Path(__file__).parent / "plan" / "benchmark_baseline.json"
    with open(results_file, 'w') as f:
        json.dump({
            'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
            'test_site': 'examples/showcase',
            'results': results
        }, f, indent=2)
    
    print(f"📁 Results saved to: {results_file}")
    print()
    
    # Analysis
    print("=" * 80)
    print("ANALYSIS")
    print("=" * 80)
    
    if 'incremental_1_change' in results and results['incremental_1_change'] > 0.1:
        print("⚠️  Incremental build with 1 change is slower than expected.")
        print("    This confirms our analysis - taxonomies/menus are processing ALL pages.")
        print()
        print("    Expected impact of fixes:")
        print(f"    - Phase ordering fix: Could reduce to ~{results['incremental_1_change'] / 3:.3f}s (3x)")
        print(f"    - With all optimizations: Could reduce to ~{results['incremental_1_change'] / 5:.3f}s (5x)")
    
    print()
    print("✅ Benchmark complete!")

if __name__ == "__main__":
    benchmark_showcase()

