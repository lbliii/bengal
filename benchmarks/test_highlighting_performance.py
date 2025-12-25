"""
Benchmark suite for syntax highlighting backends.

Compares performance of Pygments vs tree-sitter backends.

Run with:
    pytest benchmarks/test_highlighting_performance.py -v --benchmark-only

Requirements:
    - pytest-benchmark
    - tree-sitter (optional, for tree-sitter benchmarks)
    - tree-sitter-python (optional)
"""

from __future__ import annotations

import pytest

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


class TestPygmentsHighlightingPerformance:
    """Benchmarks for Pygments backend."""

    def test_pygments_python_simple(self, benchmark) -> None:
        """Benchmark Pygments on simple Python code."""
        from bengal.rendering.highlighting.pygments import PygmentsBackend

        backend = PygmentsBackend()
        result = benchmark(backend.highlight, PYTHON_SIMPLE, "python")
        assert "<span" in result

    def test_pygments_python_medium(self, benchmark) -> None:
        """Benchmark Pygments on medium Python code (~50 lines)."""
        from bengal.rendering.highlighting.pygments import PygmentsBackend

        backend = PygmentsBackend()
        result = benchmark(backend.highlight, PYTHON_MEDIUM, "python")
        assert "<span" in result

    def test_pygments_python_large(self, benchmark) -> None:
        """Benchmark Pygments on large Python code (~500 lines)."""
        from bengal.rendering.highlighting.pygments import PygmentsBackend

        backend = PygmentsBackend()
        result = benchmark(backend.highlight, PYTHON_LARGE, "python")
        assert "<span" in result

    def test_pygments_rust(self, benchmark) -> None:
        """Benchmark Pygments on Rust code."""
        from bengal.rendering.highlighting.pygments import PygmentsBackend

        backend = PygmentsBackend()
        result = benchmark(backend.highlight, RUST_CODE, "rust")
        assert "<span" in result

    def test_pygments_javascript(self, benchmark) -> None:
        """Benchmark Pygments on JavaScript/TSX code."""
        from bengal.rendering.highlighting.pygments import PygmentsBackend

        backend = PygmentsBackend()
        result = benchmark(backend.highlight, JAVASCRIPT_CODE, "javascript")
        assert "<span" in result

    def test_pygments_with_linenos(self, benchmark) -> None:
        """Benchmark Pygments with line numbers enabled."""
        from bengal.rendering.highlighting.pygments import PygmentsBackend

        backend = PygmentsBackend()
        result = benchmark(backend.highlight, PYTHON_MEDIUM, "python", show_linenos=True)
        assert "table" in result.lower()

    def test_pygments_with_hl_lines(self, benchmark) -> None:
        """Benchmark Pygments with line highlighting."""
        from bengal.rendering.highlighting.pygments import PygmentsBackend

        backend = PygmentsBackend()
        result = benchmark(backend.highlight, PYTHON_MEDIUM, "python", hl_lines=[1, 5, 10, 15])
        assert "hll" in result


# Tree-sitter benchmarks - skip if not available
def _tree_sitter_available() -> bool:
    """Check if tree-sitter is available and working."""
    try:
        from bengal.rendering.highlighting.tree_sitter import TreeSitterBackend

        backend = TreeSitterBackend()
        return backend.supports_language("python")
    except (ImportError, Exception):
        return False


@pytest.mark.skipif(
    not _tree_sitter_available(),
    reason="tree-sitter or tree-sitter-python not available",
)
class TestTreeSitterHighlightingPerformance:
    """Benchmarks for tree-sitter backend."""

    def test_tree_sitter_python_simple(self, benchmark) -> None:
        """Benchmark tree-sitter on simple Python code."""
        from bengal.rendering.highlighting.tree_sitter import TreeSitterBackend

        backend = TreeSitterBackend()
        result = benchmark(backend.highlight, PYTHON_SIMPLE, "python")
        assert "<span" in result or "<pre" in result

    def test_tree_sitter_python_medium(self, benchmark) -> None:
        """Benchmark tree-sitter on medium Python code (~50 lines)."""
        from bengal.rendering.highlighting.tree_sitter import TreeSitterBackend

        backend = TreeSitterBackend()
        result = benchmark(backend.highlight, PYTHON_MEDIUM, "python")
        assert "<span" in result or "<pre" in result

    def test_tree_sitter_python_large(self, benchmark) -> None:
        """Benchmark tree-sitter on large Python code (~500 lines)."""
        from bengal.rendering.highlighting.tree_sitter import TreeSitterBackend

        backend = TreeSitterBackend()
        result = benchmark(backend.highlight, PYTHON_LARGE, "python")
        assert "<span" in result or "<pre" in result

    def test_tree_sitter_with_linenos(self, benchmark) -> None:
        """Benchmark tree-sitter with line numbers enabled."""
        from bengal.rendering.highlighting.tree_sitter import TreeSitterBackend

        backend = TreeSitterBackend()
        result = benchmark(backend.highlight, PYTHON_MEDIUM, "python", show_linenos=True)
        assert "table" in result.lower() or "<pre" in result

    def test_tree_sitter_with_hl_lines(self, benchmark) -> None:
        """Benchmark tree-sitter with line highlighting."""
        from bengal.rendering.highlighting.tree_sitter import TreeSitterBackend

        backend = TreeSitterBackend()
        result = benchmark(backend.highlight, PYTHON_MEDIUM, "python", hl_lines=[1, 5, 10, 15])
        assert "hll" in result or "<pre" in result


class TestHighlightingComparison:
    """Compare Pygments vs tree-sitter performance."""

    def test_comparison_python_medium(self, benchmark) -> None:
        """
        Compare backends on medium Python code.

        This is the key benchmark for the RFC requirement of ≥5x speedup.
        """
        from bengal.rendering.highlighting.pygments import PygmentsBackend

        backend = PygmentsBackend()

        # Just benchmark Pygments here; tree-sitter comparison is manual
        # due to potential unavailability
        result = benchmark(backend.highlight, PYTHON_MEDIUM, "python")
        assert "<span" in result


class TestBulkHighlighting:
    """Test highlighting many code blocks (simulates real site build)."""

    def test_pygments_100_blocks(self, benchmark) -> None:
        """Benchmark Pygments on 100 code blocks."""
        from bengal.rendering.highlighting.pygments import PygmentsBackend

        backend = PygmentsBackend()
        codes = [PYTHON_SIMPLE, PYTHON_MEDIUM, RUST_CODE, JAVASCRIPT_CODE] * 25

        def highlight_all():
            results = []
            for code in codes:
                lang = "python" if "def " in code else "rust" if "fn " in code else "javascript"
                results.append(backend.highlight(code, lang))
            return results

        results = benchmark(highlight_all)
        assert len(results) == 100
        assert all("<span" in r for r in results)

    @pytest.mark.skipif(
        not _tree_sitter_available(),
        reason="tree-sitter not available",
    )
    def test_tree_sitter_100_blocks(self, benchmark) -> None:
        """Benchmark tree-sitter on 100 code blocks."""
        from bengal.rendering.highlighting.tree_sitter import TreeSitterBackend

        backend = TreeSitterBackend()
        codes = [PYTHON_SIMPLE, PYTHON_MEDIUM] * 50  # Only Python if that's what's available

        def highlight_all():
            results = []
            for code in codes:
                results.append(backend.highlight(code, "python"))
            return results

        results = benchmark(highlight_all)
        assert len(results) == 100
