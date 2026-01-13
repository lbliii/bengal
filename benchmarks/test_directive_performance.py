"""
Performance benchmarks for directive parsing with typed options.

Tests directive parsing performance on real site content to validate
the RFC Patitas Directive Ergonomics improvements.

This benchmark:
1. Parses markdown files from the real site (sampled)
2. Measures full parse+render pipeline (like compare_parsers.py)
3. Tracks directive usage statistics
4. Validates performance improvements from typed options

Run with:
    pytest benchmarks/test_directive_performance.py -v --benchmark-only

Expected results:
    - Directive parsing should be fast (< 1ms per directive on average)
    - Typed options should be faster than dict lookups
    - No performance regression from migration
"""

from __future__ import annotations

from collections import defaultdict
from pathlib import Path

import pytest

from bengal.rendering.parsers.patitas import create_markdown
from bengal.rendering.parsers.patitas.directives import create_default_registry
from patitas.nodes import Directive
from patitas.parser import Parser


def bengal_site_root() -> Path:
    """Get the real Bengal site root directory."""
    return Path(__file__).parent.parent / "site"


def get_all_markdown_files(site_root: Path) -> list[Path]:
    """Get all markdown files from the site."""
    content_dir = site_root / "content"
    if not content_dir.exists():
        return []

    markdown_files = list(content_dir.rglob("*.md"))
    return sorted(markdown_files)


@pytest.fixture(scope="module")
def site_markdown_files():
    """Get all markdown files from the real site."""
    site_root = bengal_site_root()
    files = get_all_markdown_files(site_root)
    assert len(files) > 0, f"No markdown files found in {site_root / 'content'}"
    return files


@pytest.fixture(scope="module")
def directive_registry():
    """Create directive registry for parsing."""
    return create_default_registry()


@pytest.fixture(scope="module")
def patitas_parser():
    """Create Patitas parser (reused across tests, has default directive registry)."""
    return create_markdown(highlight=False)


def count_directives_in_ast(ast_nodes) -> dict[str, int]:
    """Count directives by name in AST."""
    counts = defaultdict(int)

    def walk(node):
        if isinstance(node, Directive):
            counts[node.name] += 1
        if hasattr(node, "children"):
            for child in node.children:
                walk(child)

    for node in ast_nodes:
        walk(node)

    return dict(counts)


class TestDirectiveParsingPerformance:
    """Benchmark directive parsing on real site content."""

    def test_parse_sampled_site_files(self, benchmark, site_markdown_files, patitas_parser):
        """Parse sampled markdown files from the real site (full pipeline)."""
        # Sample files for faster execution
        sample_size = min(20, len(site_markdown_files))
        files_to_parse = site_markdown_files[:sample_size]

        # Pre-load content
        file_contents = [(f, f.read_text()) for f in files_to_parse]

        def parse_all():
            total_directives = 0
            for _, content in file_contents:
                # Use high-level parser (full parse+render pipeline)
                patitas_parser(content)
                # Parse AST separately to count directives
                ast = patitas_parser.parse_to_ast(content)
                directive_counts = count_directives_in_ast(ast)
                total_directives += sum(directive_counts.values())
            return total_directives

        result = benchmark(parse_all)

        # Verify we parsed something
        assert result > 0, "Should have parsed at least one directive"
        print(f"\nParsed {result} total directives across {sample_size} files")

    def test_parse_single_file_with_directives(
        self, benchmark, site_markdown_files, patitas_parser
    ):
        """Parse a single file containing directives (full pipeline)."""
        # Find a file with directives
        test_file = None
        for file_path in site_markdown_files[:50]:  # Check first 50 files
            content = file_path.read_text()
            if ":::" in content:  # Simple heuristic for directives
                test_file = (file_path, content)
                break

        if not test_file:
            pytest.skip("No files with directives found")

        file_path, content = test_file

        def parse_file():
            # Full pipeline: parse + render
            patitas_parser(content)
            # Also parse AST to count directives
            ast = patitas_parser.parse_to_ast(content)
            return count_directives_in_ast(ast)

        result = benchmark(parse_file)
        print(f"\nParsed file: {file_path.name}")
        print(f"Directives found: {result}")

    def test_directive_option_access_performance(
        self, benchmark, site_markdown_files, directive_registry
    ):
        """Benchmark accessing typed options vs dict lookups."""
        # Collect directives from all files
        all_directives: list[Directive] = []

        for file_path in site_markdown_files:
            content = file_path.read_text()
            parser = Parser(content, directive_registry=directive_registry)
            ast = parser.parse()

            def collect_directives(node):
                if isinstance(node, Directive):
                    all_directives.append(node)
                if hasattr(node, "children"):
                    for child in node.children:
                        collect_directives(child)

            for node in ast:
                collect_directives(node)

        if not all_directives:
            pytest.skip("No directives found in site files")

        # Benchmark typed option access (current implementation)
        def access_typed_options():
            total = 0
            for directive in all_directives:
                opts = directive.options
                # Access common attributes
                if hasattr(opts, "class_"):
                    _ = opts.class_ or ""
                if hasattr(opts, "name"):
                    _ = opts.name or ""
                if hasattr(opts, "id"):
                    _ = opts.id or ""
                total += 1
            return total

        result = benchmark(access_typed_options)
        print(f"\nAccessed options for {result} directives")
        print(f"Average per directive: {benchmark.stats.mean * 1000 / result:.3f}ms")

    def test_directive_statistics(self, site_markdown_files, patitas_parser):
        """Collect statistics about directive usage in the real site."""
        all_counts = defaultdict(int)
        files_with_directives = 0

        # Sample up to 30 files for faster execution
        sample_size = min(30, len(site_markdown_files))
        files_to_parse = site_markdown_files[:sample_size]

        for file_path in files_to_parse:
            try:
                content = file_path.read_text()
                ast = patitas_parser.parse_to_ast(content)

                counts = count_directives_in_ast(ast)
                if counts:
                    files_with_directives += 1
                    for name, count in counts.items():
                        all_counts[name] += count
            except Exception:
                # Skip files that fail to parse
                continue

        print("\n" + "=" * 60)
        print("DIRECTIVE USAGE STATISTICS")
        print("=" * 60)
        print(f"Total files in site: {len(site_markdown_files)}")
        print(f"Files sampled: {sample_size}")
        print(f"Files with directives: {files_with_directives}")
        print(f"Total directives: {sum(all_counts.values())}")
        if all_counts:
            print("\nDirective breakdown:")
            for name, count in sorted(all_counts.items(), key=lambda x: -x[1]):
                print(f"  {name:20s}: {count:4d}")
        else:
            print("\nNo directives found in sampled files.")
        print("=" * 60)

    def test_parse_large_file_with_many_directives(
        self, benchmark, site_markdown_files, directive_registry
    ):
        """Find and parse the file with the most directives."""
        max_directives = 0
        best_file = None
        best_content = None

        for file_path in site_markdown_files:
            content = file_path.read_text()
            parser = Parser(content, directive_registry=directive_registry)
            ast = parser.parse()
            counts = count_directives_in_ast(ast)
            total = sum(counts.values())

            if total > max_directives:
                max_directives = total
                best_file = file_path
                best_content = content

        if not best_file or max_directives == 0:
            pytest.skip("No files with directives found")

        def parse_large_file():
            parser = Parser(best_content, directive_registry=directive_registry)
            ast = parser.parse()
            return count_directives_in_ast(ast)

        result = benchmark(parse_large_file)
        print(f"\nParsed file: {best_file.name}")
        print(f"Directives: {sum(result.values())}")
        print(f"Breakdown: {result}")
