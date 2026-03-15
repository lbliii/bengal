"""
Unit tests for DirectoryWalker.

Tests: walk order, hidden file exclusion, versioning infrastructure,
symlink loop detection, list_directory behavior.
"""

from __future__ import annotations

from pathlib import Path

from bengal.content.discovery.directory_walker import DirectoryWalker


class TestDirectoryWalkerIsContentFile:
    """Test is_content_file filtering."""

    def test_md_is_content(self, tmp_path: Path) -> None:
        """Markdown files are content files."""
        walker = DirectoryWalker(tmp_path)
        assert walker.is_content_file(tmp_path / "page.md") is True

    def test_markdown_is_content(self, tmp_path: Path) -> None:
        """Markdown extension is content."""
        walker = DirectoryWalker(tmp_path)
        assert walker.is_content_file(tmp_path / "page.markdown") is True

    def test_rst_is_content(self, tmp_path: Path) -> None:
        """RST files are content."""
        walker = DirectoryWalker(tmp_path)
        assert walker.is_content_file(tmp_path / "page.rst") is True

    def test_ipynb_is_content(self, tmp_path: Path) -> None:
        """Notebook files are content."""
        walker = DirectoryWalker(tmp_path)
        assert walker.is_content_file(tmp_path / "notebook.ipynb") is True

    def test_txt_is_content(self, tmp_path: Path) -> None:
        """TXT files are content."""
        walker = DirectoryWalker(tmp_path)
        assert walker.is_content_file(tmp_path / "page.txt") is True

    def test_html_not_content(self, tmp_path: Path) -> None:
        """HTML is not a content file."""
        walker = DirectoryWalker(tmp_path)
        assert walker.is_content_file(tmp_path / "page.html") is False

    def test_yaml_not_content(self, tmp_path: Path) -> None:
        """YAML is not a content file."""
        walker = DirectoryWalker(tmp_path)
        assert walker.is_content_file(tmp_path / "data.yaml") is False


class TestDirectoryWalkerShouldSkipItem:
    """Test should_skip_item for hidden files and versioning dirs."""

    def test_hidden_file_skipped(self, tmp_path: Path) -> None:
        """Hidden files are skipped."""
        walker = DirectoryWalker(tmp_path)
        assert walker.should_skip_item(tmp_path / ".hidden") is True

    def test_hidden_dir_skipped(self, tmp_path: Path) -> None:
        """Hidden directories are skipped."""
        walker = DirectoryWalker(tmp_path)
        assert walker.should_skip_item(tmp_path / ".git") is True

    def test_index_md_not_skipped(self, tmp_path: Path) -> None:
        """_index.md is not skipped (section index)."""
        walker = DirectoryWalker(tmp_path)
        assert walker.should_skip_item(tmp_path / "_index.md") is False

    def test_index_markdown_not_skipped(self, tmp_path: Path) -> None:
        """_index.markdown is not skipped."""
        walker = DirectoryWalker(tmp_path)
        assert walker.should_skip_item(tmp_path / "_index.markdown") is False

    def test_underscore_prefix_skipped(self, tmp_path: Path) -> None:
        """Other underscore-prefixed items are skipped."""
        walker = DirectoryWalker(tmp_path)
        assert walker.should_skip_item(tmp_path / "_drafts") is True

    def test_versions_without_versioning_skipped(self, tmp_path: Path) -> None:
        """_versions is skipped when versioning disabled."""
        walker = DirectoryWalker(tmp_path)
        assert walker.should_skip_item(tmp_path / "_versions") is True

    def test_versions_with_versioning_not_skipped(self, tmp_path: Path) -> None:
        """_versions is not skipped when versioning enabled."""
        site = type("Site", (), {"versioning_enabled": True})()
        walker = DirectoryWalker(tmp_path, site=site)
        assert walker.should_skip_item(tmp_path / "_versions") is False


class TestDirectoryWalkerListDirectory:
    """Test list_directory behavior."""

    def test_list_directory_returns_sorted(self, tmp_path: Path) -> None:
        """list_directory returns alphabetically sorted items."""
        (tmp_path / "c").mkdir()
        (tmp_path / "a").mkdir()
        (tmp_path / "b").mkdir()
        walker = DirectoryWalker(tmp_path)
        items = walker.list_directory(tmp_path)
        names = [p.name for p in items]
        assert names == ["a", "b", "c"]

    def test_list_directory_empty(self, tmp_path: Path) -> None:
        """Empty directory returns empty list."""
        walker = DirectoryWalker(tmp_path)
        items = walker.list_directory(tmp_path)
        assert items == []

    def test_list_directory_mixed(self, tmp_path: Path) -> None:
        """Mixed files and dirs are sorted together."""
        (tmp_path / "file.md").write_text("x")
        (tmp_path / "dir").mkdir()
        walker = DirectoryWalker(tmp_path)
        items = walker.list_directory(tmp_path)
        names = [p.name for p in items]
        assert "dir" in names
        assert "file.md" in names


class TestDirectoryWalkerCheckSymlinkLoop:
    """Test symlink loop detection via inode tracking."""

    def test_first_visit_not_loop(self, tmp_path: Path) -> None:
        """First visit to directory is not a loop."""
        subdir = tmp_path / "sub"
        subdir.mkdir()
        walker = DirectoryWalker(tmp_path)
        assert walker.check_symlink_loop(subdir) is False

    def test_second_visit_same_dir_is_loop(self, tmp_path: Path) -> None:
        """Visiting same directory twice (same inode) is a loop."""
        subdir = tmp_path / "sub"
        subdir.mkdir()
        walker = DirectoryWalker(tmp_path)
        walker.check_symlink_loop(subdir)
        assert walker.check_symlink_loop(subdir) is True

    def test_reset_clears_visited(self, tmp_path: Path) -> None:
        """reset() clears visited inodes."""
        subdir = tmp_path / "sub"
        subdir.mkdir()
        walker = DirectoryWalker(tmp_path)
        walker.check_symlink_loop(subdir)
        walker.reset()
        assert walker.check_symlink_loop(subdir) is False


class TestDirectoryWalkerWalkDirectory:
    """Test walk_directory generator."""

    def test_walk_yields_content_files(self, tmp_path: Path) -> None:
        """walk_directory yields content files."""
        (tmp_path / "page.md").write_text("# Page")
        walker = DirectoryWalker(tmp_path)
        items = list(walker.walk_directory(tmp_path))
        assert len(items) == 1
        path, is_file = items[0]
        assert path.name == "page.md"
        assert is_file is True

    def test_walk_yields_dirs(self, tmp_path: Path) -> None:
        """walk_directory yields directories."""
        (tmp_path / "blog").mkdir()
        walker = DirectoryWalker(tmp_path)
        items = list(walker.walk_directory(tmp_path))
        assert len(items) == 1
        path, is_file = items[0]
        assert path.name == "blog"
        assert is_file is False

    def test_walk_skips_hidden(self, tmp_path: Path) -> None:
        """walk_directory skips hidden files."""
        (tmp_path / ".hidden").write_text("x")
        (tmp_path / "page.md").write_text("# Page")
        walker = DirectoryWalker(tmp_path)
        items = list(walker.walk_directory(tmp_path))
        names = [p.name for p, _ in items]
        assert ".hidden" not in names
        assert "page.md" in names

    def test_walk_nonexistent_returns_empty(self, tmp_path: Path) -> None:
        """walk_directory on nonexistent dir yields nothing."""
        walker = DirectoryWalker(tmp_path)
        items = list(walker.walk_directory(tmp_path / "nonexistent"))
        assert items == []
