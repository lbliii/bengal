"""
Benchmark suite for Rosettes syntax highlighting.

Rosettes is Bengal's default and only built-in syntax highlighter:
- 55 languages supported
- Lock-free, thread-safe (designed for Python 3.14t free-threading)
- 3.4x faster than Pygments

Run with:
    pytest benchmarks/test_highlighting_performance.py -v --benchmark-only

Requirements:
    - pytest-benchmark
    - rosettes
"""

from __future__ import annotations

# Sample code snippets for benchmarking
PYTHON_SIMPLE = """def hello():
    print("Hello, World!")
"""

PYTHON_MEDIUM = '''
import os
from pathlib import Path
from typing import Any

class FileHandler:
    """A class for handling file operations."""

    def __init__(self, path: str) -> None:
        self.path = Path(path)
        self._cache: dict[str, Any] = {}

    def read(self) -> str:
        """Read file contents."""
        if str(self.path) in self._cache:
            return self._cache[str(self.path)]

        with open(self.path) as f:
            content = f.read()

        self._cache[str(self.path)] = content
        return content

    def write(self, content: str) -> int:
        """Write content to file."""
        with open(self.path, "w") as f:
            return f.write(content)

    @property
    def exists(self) -> bool:
        return self.path.exists()


def process_files(directory: str) -> list[str]:
    """Process all files in a directory."""
    results = []
    for item in Path(directory).iterdir():
        if item.is_file():
            handler = FileHandler(str(item))
            results.append(handler.read())
    return results


if __name__ == "__main__":
    files = process_files(".")
    print(f"Processed {len(files)} files")
'''

PYTHON_LARGE = PYTHON_MEDIUM * 10  # ~60 lines

RUST_CODE = """
use std::collections::HashMap;
use std::io::{self, Read, Write};

#[derive(Debug, Clone)]
pub struct Cache<K, V> {
    data: HashMap<K, V>,
    capacity: usize,
}

impl<K: Eq + std::hash::Hash, V: Clone> Cache<K, V> {
    pub fn new(capacity: usize) -> Self {
        Self {
            data: HashMap::with_capacity(capacity),
            capacity,
        }
    }

    pub fn get(&self, key: &K) -> Option<&V> {
        self.data.get(key)
    }

    pub fn insert(&mut self, key: K, value: V) -> Option<V> {
        if self.data.len() >= self.capacity {
            // Simple eviction: remove first key
            if let Some(first_key) = self.data.keys().next().cloned() {
                self.data.remove(&first_key);
            }
        }
        self.data.insert(key, value)
    }
}

fn main() -> io::Result<()> {
    let mut cache = Cache::new(100);
    cache.insert("key1".to_string(), 42);

    if let Some(val) = cache.get(&"key1".to_string()) {
        println!("Value: {}", val);
    }

    Ok(())
}
"""

JAVASCRIPT_CODE = """
import { useState, useEffect, useCallback } from 'react';

interface User {
  id: number;
  name: string;
  email: string;
}

export function useUsers() {
  const [users, setUsers] = useState<User[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);

  const fetchUsers = useCallback(async () => {
    try {
      setLoading(true);
      const response = await fetch('/api/users');

      if (!response.ok) {
        throw new Error(`HTTP error: ${response.status}`);
      }

      const data = await response.json();
      setUsers(data);
    } catch (err) {
      setError(err instanceof Error ? err : new Error('Unknown error'));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchUsers();
  }, [fetchUsers]);

  return { users, loading, error, refetch: fetchUsers };
}

export default function UserList() {
  const { users, loading, error } = useUsers();

  if (loading) return <div>Loading...</div>;
  if (error) return <div>Error: {error.message}</div>;

  return (
    <ul>
      {users.map(user => (
        <li key={user.id}>{user.name}</li>
      ))}
    </ul>
  );
}
"""


class TestRosettesHighlightingPerformance:
    """Benchmarks for Rosettes backend (default).

    Rosettes is Bengal's default syntax highlighter:
    - 55 languages supported
    - Lock-free, thread-safe
    - 3.4x faster than Pygments
    """

    def test_rosettes_python_simple(self, benchmark) -> None:
        """Benchmark Rosettes on simple Python code."""
        import rosettes

        result = benchmark(rosettes.highlight, PYTHON_SIMPLE, "python")
        assert "<span" in result

    def test_rosettes_python_medium(self, benchmark) -> None:
        """Benchmark Rosettes on medium Python code (~50 lines)."""
        import rosettes

        result = benchmark(rosettes.highlight, PYTHON_MEDIUM, "python")
        assert "<span" in result

    def test_rosettes_python_large(self, benchmark) -> None:
        """Benchmark Rosettes on large Python code (~500 lines)."""
        import rosettes

        result = benchmark(rosettes.highlight, PYTHON_LARGE, "python")
        assert "<span" in result

    def test_rosettes_rust(self, benchmark) -> None:
        """Benchmark Rosettes on Rust code."""
        import rosettes

        result = benchmark(rosettes.highlight, RUST_CODE, "rust")
        assert "<span" in result

    def test_rosettes_javascript(self, benchmark) -> None:
        """Benchmark Rosettes on JavaScript/TSX code."""
        import rosettes

        result = benchmark(rosettes.highlight, JAVASCRIPT_CODE, "javascript")
        assert "<span" in result

    def test_rosettes_with_linenos(self, benchmark) -> None:
        """Benchmark Rosettes with line numbers enabled."""
        import rosettes

        result = benchmark(rosettes.highlight, PYTHON_MEDIUM, "python", show_linenos=True)
        # Rosettes outputs highlighted code; line numbers may be CSS-based
        assert "<span" in result or "<pre" in result

    def test_rosettes_with_hl_lines(self, benchmark) -> None:
        """Benchmark Rosettes with line highlighting."""
        import rosettes

        result = benchmark(rosettes.highlight, PYTHON_MEDIUM, "python", hl_lines={1, 5, 10, 15})
        # Rosettes outputs highlighted code; hl_lines affects specific lines
        assert "<span" in result or "<pre" in result


class TestHighlightingComparison:
    """Rosettes performance benchmarks."""

    def test_rosettes_baseline(self, benchmark) -> None:
        """
        Rosettes baseline on medium Python code.

        This is the default backend, expected to be fast and lock-free.
        """
        import rosettes

        result = benchmark(rosettes.highlight, PYTHON_MEDIUM, "python")
        assert "<span" in result


class TestBulkHighlighting:
    """Test highlighting many code blocks (simulates real site build)."""

    def test_rosettes_100_blocks(self, benchmark) -> None:
        """Benchmark Rosettes on 100 code blocks."""
        import rosettes

        codes = [PYTHON_SIMPLE, PYTHON_MEDIUM, RUST_CODE, JAVASCRIPT_CODE] * 25

        def highlight_all():
            results = []
            for code in codes:
                lang = "python" if "def " in code else "rust" if "fn " in code else "javascript"
                results.append(rosettes.highlight(code, lang))
            return results

        results = benchmark(highlight_all)
        assert len(results) == 100
        assert all("<span" in r for r in results)

    def test_rosettes_100_blocks_parallel(self, benchmark) -> None:
        """Benchmark Rosettes parallel highlighting on 100 code blocks.

        Uses rosettes.highlight_many() for parallel execution on Python 3.14t.
        """
        import rosettes

        items = []
        for _ in range(25):
            items.append((PYTHON_SIMPLE, "python"))
            items.append((PYTHON_MEDIUM, "python"))
            items.append((RUST_CODE, "rust"))
            items.append((JAVASCRIPT_CODE, "javascript"))

        results = benchmark(rosettes.highlight_many, items)
        assert len(results) == 100
        assert all("<span" in r for r in results)
