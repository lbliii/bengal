#!/usr/bin/env python3
"""
Quick test: ProcessPoolExecutor vs ThreadPoolExecutor for rendering.

This tests whether switching from threads to processes can break through
the GIL bottleneck and achieve true parallelism.
"""

import concurrent.futures
import multiprocessing
import time
from pathlib import Path
from tempfile import mkdtemp

from bengal.core.site import Site
from bengal.rendering.pipeline import RenderingPipeline


def render_page_process(args):
    """
    Render a single page in a separate process.

    Args:
        args: Tuple of (site, page)

    Returns:
        Tuple of (page_source_path, success, error_msg)
    """
    site, page = args

    try:
        # Create a pipeline for this process (RenderingPipeline doesn't take tracker/stats)
        pipeline = RenderingPipeline(site)
        pipeline.process_page(page)
        return (str(page.source_path), True, None)
    except Exception as e:
        import traceback

        return (str(page.source_path), False, f"{type(e).__name__}: {e}\n{traceback.format_exc()}")


def test_thread_vs_process_rendering():
    """Compare thread-based vs process-based rendering."""

    # Create test site
    print("Creating test site with 200 pages...")
    site_root = Path(mkdtemp(prefix="bengal_process_test_"))

    # Config
    config_file = site_root / "bengal.toml"
    config_file.write_text("""
[site]
title = "Process Test Site"
baseurl = "https://example.com"

[build]
output_dir = "public"
max_workers = 10
""")

    # Content
    content_dir = site_root / "content"
    content_dir.mkdir()

    num_pages = 1000  # Test at 1K pages to see GIL impact
    for i in range(num_pages):
        page_file = content_dir / f"page-{i:03d}.md"
        # Create more complex pages to simulate real CPU load
        page_file.write_text(f"""---
title: "Test Page {i}"
date: 2025-01-{(i % 28) + 1:02d}
tags: ["test", "benchmark", "python", "performance"]
description: "A comprehensive test page with complex markdown to simulate real-world rendering workload"
---

# Test Page {i}

This is a comprehensive test page for comparing parallel rendering performance. The content is designed to be complex enough to create measurable CPU load during markdown parsing and template rendering.

## Section 1: Code Examples

Here's some Python code that needs syntax highlighting:

```python
def fibonacci(n):
    \"\"\"Calculate Fibonacci number recursively.\"\"\"
    if n <= 1:
        return n
    return fibonacci(n-1) + fibonacci(n-2)

class DataProcessor:
    def __init__(self, data):
        self.data = data
        self.results = []

    def process(self):
        for item in self.data:
            result = self.transform(item)
            self.results.append(result)
        return self.results

    def transform(self, item):
        return item * 2 + fibonacci(5)
```

## Section 2: Complex Lists and Tables

### Nested Lists

- Item 1
  - Subitem 1.1
    - Subsubitem 1.1.1
    - Subsubitem 1.1.2
  - Subitem 1.2
- Item 2
  - Subitem 2.1
  - Subitem 2.2
- Item 3

### Data Table

| Framework | Language | Build Time | Pages/Sec |
|-----------|----------|------------|-----------|
| Hugo      | Go       | 2.5s       | 400       |
| Jekyll    | Ruby     | 45s        | 22        |
| Sphinx    | Python   | 300s       | 3.3       |
| Bengal    | Python   | 10s        | {150 + i} |

## Section 3: Mathematical Formulas

Inline math: $E = mc^2$ and $\\int_0^\\infty e^{{-x^2}} dx = \\frac{{\\sqrt{{\\pi}}}}{{2}}$

Block math:

$$
f(x) = \\frac{{1}}{{\\sigma\\sqrt{{2\\pi}}}} e^{{-\\frac{{1}}{{2}}\\left(\\frac{{x-\\mu}}{{\\sigma}}\\right)^2}}
$$

## Section 4: More Code Blocks

JavaScript example:

```javascript
async function fetchData(url) {{
  try {{
    const response = await fetch(url);
    const data = await response.json();
    return data;
  }} catch (error) {{
    console.error('Error fetching data:', error);
    throw error;
  }}
}}
```

SQL query:

```sql
SELECT u.id, u.name, COUNT(p.id) as post_count
FROM users u
LEFT JOIN posts p ON u.id = p.author_id
WHERE u.active = true
GROUP BY u.id, u.name
HAVING COUNT(p.id) > 5
ORDER BY post_count DESC
LIMIT 10;
```

## Section 5: Blockquotes and Links

> "The real problem is not whether machines think but whether men do."
> — B.F. Skinner

Here are some relevant links:
- [Python Documentation](https://docs.python.org/)
- [Markdown Guide](https://www.markdownguide.org/)
- [Static Site Generators](https://jamstack.org/generators/)

## Conclusion

This page contains enough complex markdown (code blocks, tables, math, nested lists) to create measurable CPU load during parsing and rendering. Page {i} of {num_pages}.
""")

    print(f"✓ Created {num_pages} pages in {site_root}")

    # Load site and discover content
    print("\nLoading site and discovering content...")
    site = Site.from_config(site_root)

    from bengal.orchestration.content import ContentOrchestrator

    content_orch = ContentOrchestrator(site)
    content_orch.discover()

    # Set output paths using RenderOrchestrator's method
    from bengal.orchestration.render import RenderOrchestrator

    render_orch = RenderOrchestrator(site)
    render_orch._set_output_paths_for_pages(site.pages)

    print(f"✓ Discovered {len(site.pages)} pages")

    # Get regular pages only (exclude generated)
    pages_to_render = [p for p in site.pages if not p.metadata.get("_generated")]
    print(f"  Pages to render: {len(pages_to_render)}")

    # ========================================================================
    # TEST 1: ThreadPoolExecutor (current approach)
    # ========================================================================
    print("\n" + "=" * 70)
    print("TEST 1: ThreadPoolExecutor (Current - Subject to GIL)")
    print("=" * 70)

    max_workers = 10
    print(f"Workers: {max_workers}")

    start = time.time()

    # Thread-local storage
    import threading

    _thread_local = threading.local()

    def render_with_thread(page):
        if not hasattr(_thread_local, "pipeline"):
            _thread_local.pipeline = RenderingPipeline(site)
        _thread_local.pipeline.process_page(page)
        return str(page.source_path)

    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = [executor.submit(render_with_thread, page) for page in pages_to_render]
        results = [f.result() for f in concurrent.futures.as_completed(futures)]

    thread_time = time.time() - start
    thread_pps = len(pages_to_render) / thread_time

    print(f"\n✓ Completed in {thread_time:.2f}s")
    print(f"  Pages/sec: {thread_pps:.1f}")
    print(f"  Speedup: {len(pages_to_render) / thread_time / 1:.1f}x vs sequential (estimated)")

    # ========================================================================
    # TEST 2: ProcessPoolExecutor (true parallelism)
    # ========================================================================
    print("\n" + "=" * 70)
    print("TEST 2: ProcessPoolExecutor (New - No GIL!)")
    print("=" * 70)

    # Check if Site and Page are picklable
    print("Testing picklability...")
    try:
        import pickle

        pickle.dumps(site)
        print("✓ Site object is picklable")
    except Exception as e:
        print(f"✗ Site object NOT picklable: {e}")
        print("  Cannot test ProcessPoolExecutor without picklable objects")
        return

    try:
        pickle.dumps(pages_to_render[0])
        print("✓ Page objects are picklable")
    except Exception as e:
        print(f"✗ Page objects NOT picklable: {e}")
        print("  Cannot test ProcessPoolExecutor without picklable objects")
        return

    print(f"Workers: {max_workers}")

    start = time.time()

    # Prepare args for each page
    args_list = [(site, page) for page in pages_to_render]

    with concurrent.futures.ProcessPoolExecutor(max_workers=max_workers) as executor:
        futures = [executor.submit(render_page_process, args) for args in args_list]
        results = []
        errors = []

        for future in concurrent.futures.as_completed(futures):
            try:
                path, success, error = future.result()
                results.append(path)
                if not success:
                    errors.append((path, error))
            except Exception as e:
                errors.append(("unknown", str(e)))

    process_time = time.time() - start
    process_pps = len(pages_to_render) / process_time

    print(f"\n✓ Completed in {process_time:.2f}s")
    print(f"  Pages/sec: {process_pps:.1f}")
    print(f"  Speedup: {len(pages_to_render) / process_time / 1:.1f}x vs sequential (estimated)")

    if errors:
        print(f"\n⚠️  Errors encountered: {len(errors)}")
        for path, error in errors[:3]:  # Show first 3
            print(f"  - {path}: {error}")

    # ========================================================================
    # COMPARISON
    # ========================================================================
    print("\n" + "=" * 70)
    print("COMPARISON")
    print("=" * 70)

    speedup = thread_time / process_time
    improvement = (process_pps - thread_pps) / thread_pps * 100

    print(f"\nThreadPoolExecutor:  {thread_time:.2f}s ({thread_pps:.1f} pages/sec)")
    print(f"ProcessPoolExecutor: {process_time:.2f}s ({process_pps:.1f} pages/sec)")
    print(f"\nSpeedup: {speedup:.2f}x faster with ProcessPoolExecutor")
    print(f"Improvement: {improvement:+.1f}% pages/sec")

    if speedup > 1.5:
        print("\n🎉 SIGNIFICANT IMPROVEMENT! ProcessPoolExecutor breaks through GIL!")
        print(
            f"   At 10K pages, this could save ~{300 * (1 - 1/speedup):.0f}s ({300 * (1 - 1/speedup) / 60:.1f} minutes)"
        )
    elif speedup > 1.1:
        print("\n✓ Modest improvement with ProcessPoolExecutor")
    else:
        print("\n⚠️  No significant improvement - pickling overhead may be too high")

    # Cleanup
    import shutil

    shutil.rmtree(site_root, ignore_errors=True)


if __name__ == "__main__":
    # Required for ProcessPoolExecutor on some platforms
    if not multiprocessing.get_start_method(allow_none=True):
        multiprocessing.set_start_method("spawn")

    print("=" * 70)
    print("PARALLEL RENDERING TEST: Threads vs Processes")
    print("=" * 70)
    print(f"\nCPU cores: {multiprocessing.cpu_count()}")
    print(f"Testing with 10 workers on {multiprocessing.cpu_count()} cores")
    print()

    test_thread_vs_process_rendering()
