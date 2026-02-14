#!/usr/bin/env python3
"""Benchmark parallel vs sequential tokenization in Rosettes.

Tests the speedup from using highlight_many() vs sequential highlight()
on Python 3.14t free-threaded.
"""

import os
import sys
import time
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from rosettes import highlight, highlight_many  # noqa: E402


def find_real_source_files() -> list[tuple[str, str]]:
    """Find real source files in the project for realistic benchmarking."""
    items = []

    # Search in bengal source
    for py_file in (PROJECT_ROOT / "bengal").rglob("*.py"):
        if py_file.stat().st_size < 50000:  # Skip huge files
            try:
                code = py_file.read_text()
                items.append((code, "python"))
            except Exception:
                pass

    return items[:100]  # Limit to 100 files


def generate_test_code(language: str, size: str = "medium") -> str:
    """Generate representative test code for a language."""
    samples = {
        "python": '''
def fibonacci(n: int) -> int:
    """Calculate the nth Fibonacci number."""
    if n <= 1:
        return n
    return fibonacci(n - 1) + fibonacci(n - 2)

class DataProcessor:
    """Process data with various transformations."""

    def __init__(self, data: list[dict]) -> None:
        self.data = data
        self._cache: dict[str, any] = {}

    async def process(self) -> list[dict]:
        results = []
        for item in self.data:
            processed = await self._transform(item)
            results.append(processed)
        return results

    async def _transform(self, item: dict) -> dict:
        # Apply transformations
        return {k: v.upper() if isinstance(v, str) else v for k, v in item.items()}

# Usage example
if __name__ == "__main__":
    processor = DataProcessor([{"name": "test", "value": 42}])
    import asyncio
    result = asyncio.run(processor.process())
    print(f"Processed: {result}")
''',
        "javascript": """
// Modern JavaScript with ES2024 features
const fibonacci = (n) => n <= 1 ? n : fibonacci(n - 1) + fibonacci(n - 2);

class DataProcessor {
    #cache = new Map();

    constructor(data) {
        this.data = data;
    }

    async process() {
        const results = [];
        for (const item of this.data) {
            const processed = await this.#transform(item);
            results.push(processed);
        }
        return results;
    }

    async #transform(item) {
        return Object.fromEntries(
            Object.entries(item).map(([k, v]) =>
                [k, typeof v === 'string' ? v.toUpperCase() : v]
            )
        );
    }
}

// Usage with top-level await
const processor = new DataProcessor([{ name: "test", value: 42 }]);
const result = await processor.process();
console.log(`Processed: ${JSON.stringify(result)}`);
""",
        "rust": """
use std::collections::HashMap;

/// Calculate the nth Fibonacci number
fn fibonacci(n: u64) -> u64 {
    match n {
        0 | 1 => n,
        _ => fibonacci(n - 1) + fibonacci(n - 2),
    }
}

struct DataProcessor<T> {
    data: Vec<T>,
    cache: HashMap<String, String>,
}

impl<T: Clone> DataProcessor<T> {
    fn new(data: Vec<T>) -> Self {
        Self {
            data,
            cache: HashMap::new(),
        }
    }

    async fn process(&mut self) -> Vec<T> {
        let mut results = Vec::new();
        for item in &self.data {
            let processed = self.transform(item.clone()).await;
            results.push(processed);
        }
        results
    }

    async fn transform(&self, item: T) -> T {
        // Apply transformations
        item
    }
}

fn main() {
    let fib_10 = fibonacci(10);
    println!("Fibonacci(10) = {}", fib_10);
}
""",
        "go": """
package main

import (
    "fmt"
    "sync"
)

// fibonacci calculates the nth Fibonacci number
func fibonacci(n int) int {
    if n <= 1 {
        return n
    }
    return fibonacci(n-1) + fibonacci(n-2)
}

// DataProcessor processes data with transformations
type DataProcessor struct {
    data  []map[string]interface{}
    cache sync.Map
}

// NewDataProcessor creates a new processor
func NewDataProcessor(data []map[string]interface{}) *DataProcessor {
    return &DataProcessor{data: data}
}

// Process applies transformations to all data
func (p *DataProcessor) Process() []map[string]interface{} {
    results := make([]map[string]interface{}, 0, len(p.data))
    for _, item := range p.data {
        processed := p.transform(item)
        results = append(results, processed)
    }
    return results
}

func (p *DataProcessor) transform(item map[string]interface{}) map[string]interface{} {
    result := make(map[string]interface{})
    for k, v := range item {
        if s, ok := v.(string); ok {
            result[k] = strings.ToUpper(s)
        } else {
            result[k] = v
        }
    }
    return result
}

func main() {
    fmt.Printf("Fibonacci(10) = %d\\n", fibonacci(10))
}
""",
        "typescript": """
// Modern TypeScript with advanced types
type Transform<T> = (item: T) => Promise<T>;

interface ProcessorConfig<T> {
    data: T[];
    transform?: Transform<T>;
}

class DataProcessor<T extends Record<string, unknown>> {
    private cache = new Map<string, T>();

    constructor(private readonly config: ProcessorConfig<T>) {}

    async process(): Promise<T[]> {
        const results: T[] = [];
        for (const item of this.config.data) {
            const processed = await this.transform(item);
            results.push(processed);
        }
        return results;
    }

    private async transform(item: T): Promise<T> {
        if (this.config.transform) {
            return this.config.transform(item);
        }
        return Object.fromEntries(
            Object.entries(item).map(([k, v]) =>
                [k, typeof v === 'string' ? v.toUpperCase() : v]
            )
        ) as T;
    }
}

// Usage
const processor = new DataProcessor<{ name: string; value: number }>({
    data: [{ name: "test", value: 42 }]
});
const result = await processor.process();
console.log(result);
""",
    }

    code = samples.get(language, samples["python"])

    # Scale based on size
    if size == "small":
        return code[: len(code) // 3]
    elif size == "large":
        return code * 5
    return code


def benchmark_sequential(items: list[tuple[str, str]], iterations: int = 3) -> float:
    """Benchmark sequential highlighting."""
    times = []
    for _ in range(iterations):
        start = time.perf_counter()
        results = [highlight(code, lang) for code, lang in items]
        elapsed = time.perf_counter() - start
        times.append(elapsed)
        assert len(results) == len(items)
    return min(times)


def benchmark_parallel(
    items: list[tuple[str, str]], iterations: int = 3, max_workers: int | None = None
) -> float:
    """Benchmark parallel highlighting."""
    times = []
    for _ in range(iterations):
        start = time.perf_counter()
        results = highlight_many(items, max_workers=max_workers)
        elapsed = time.perf_counter() - start
        times.append(elapsed)
        assert len(results) == len(items)
    return min(times)


def main():
    # Check Python version and GIL status
    print(f"Python {sys.version}")
    try:
        gil_enabled = sys._is_gil_enabled()
        print(f"GIL enabled: {gil_enabled}")
        is_free_threaded = not gil_enabled
    except AttributeError:
        print("GIL: standard (not free-threaded)")
        is_free_threaded = False

    cpu_count = os.cpu_count() or 4
    print(f"CPU cores: {cpu_count}")
    print()

    # Test configurations
    languages = ["python", "javascript", "rust", "go", "typescript"]
    batch_sizes = [10, 25, 50, 100, 200]

    print("=" * 80)
    print("PARALLEL TOKENIZATION BENCHMARK")
    print("=" * 80)
    print()

    for batch_size in batch_sizes:
        # Generate test items - mix of languages
        items = []
        for i in range(batch_size):
            lang = languages[i % len(languages)]
            code = generate_test_code(lang, "medium")
            items.append((code, lang))

        print(f"Batch size: {batch_size} code blocks")
        print("-" * 50)

        # Sequential
        seq_time = benchmark_sequential(items)
        print(f"  Sequential: {seq_time * 1000:.2f} ms")

        # Parallel with different worker counts
        for workers in [2, 4, 8, None]:
            worker_label = workers if workers else "auto"
            par_time = benchmark_parallel(items, max_workers=workers)
            speedup = seq_time / par_time

            indicator = "🚀" if speedup > 1.5 else ("✅" if speedup > 1.0 else "⚠️")
            par_ms = par_time * 1000
            msg = f"  Parallel ({worker_label} workers): {par_ms:.2f} ms ({speedup:.2f}x)"
            print(f"{msg} {indicator}")

        print()

    # Large file test
    print("=" * 80)
    print("LARGE FILES TEST (simulating many large code blocks)")
    print("=" * 80)
    print()

    # 50 large code blocks
    items = [
        (generate_test_code(languages[i % len(languages)], "large"), languages[i % len(languages)])
        for i in range(50)
    ]

    seq_time = benchmark_sequential(items)
    par_time = benchmark_parallel(items)
    speedup = seq_time / par_time

    print("50 large code blocks:")
    print(f"  Sequential: {seq_time * 1000:.2f} ms")
    print(f"  Parallel:   {par_time * 1000:.2f} ms")
    print(f"  Speedup:    {speedup:.2f}x {'🚀' if speedup > 2.0 else '✅'}")
    print()

    # Real-world test with actual source files
    print("=" * 80)
    print("REAL-WORLD TEST (actual source files from bengal/)")
    print("=" * 80)
    print()

    real_items = find_real_source_files()
    if real_items:
        total_chars = sum(len(code) for code, _ in real_items)
        print(f"Found {len(real_items)} Python files ({total_chars:,} total characters)")
        print()

        seq_time = benchmark_sequential(real_items)
        par_time = benchmark_parallel(real_items, max_workers=4)
        speedup = seq_time / par_time

        print(f"  Sequential: {seq_time * 1000:.2f} ms")
        print(f"  Parallel (4 workers): {par_time * 1000:.2f} ms")
        print(f"  Speedup: {speedup:.2f}x {'🚀' if speedup > 1.5 else '✅'}")
        print(f"  Throughput: {total_chars / par_time / 1_000_000:.2f} MB/s")
    else:
        print("  No source files found for real-world test")
    print()

    # Summary
    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)
    if is_free_threaded:
        print("✅ Running on free-threaded Python (GIL disabled)")
        print("   Parallel tokenization provides TRUE parallelism!")
    else:
        print("⚠️  Running on GIL Python")
        print("   Parallel benefits limited to I/O overlapping")
        print("   For maximum speedup, use Python 3.14t with PYTHON_GIL=0")


if __name__ == "__main__":
    main()
