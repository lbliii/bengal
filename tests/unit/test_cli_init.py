"""Tests for the 'bengal init' CLI command."""

from datetime import datetime
from pathlib import Path

import pytest
from click.testing import CliRunner

from bengal.cli.commands.init import (
    FileOperation,
    generate_sample_page,
    generate_section_index,
    get_sample_page_names,
    init,
    plan_init_operations,
    slugify,
    titleize,
)


@pytest.mark.unit
@pytest.mark.cli
class TestSlugify:
    """Test slug generation."""

    def test_basic_slugify(self):
        """Test basic slug generation."""
        assert slugify("Hello World") == "hello-world"
        assert slugify("My Blog Post") == "my-blog-post"

    def test_special_characters(self):
        """Test that special characters are removed."""
        assert slugify("Hello! World?") == "hello-world"
        assert slugify("Test @ Home") == "test-home"
        assert slugify("C++") == "c"

    def test_multiple_spaces(self):
        """Test that multiple spaces become single hyphen."""
        assert slugify("Hello    World") == "hello-world"
        assert slugify("Test  -  Page") == "test-page"

    def test_leading_trailing_spaces(self):
        """Test that leading/trailing spaces are removed."""
        assert slugify("  Hello World  ") == "hello-world"

    def test_hyphens_preserved(self):
        """Test that existing hyphens are preserved."""
        assert slugify("hello-world") == "hello-world"
        assert slugify("my-blog-post") == "my-blog-post"

    def test_underscores_to_hyphens(self):
        """Test that underscores become hyphens."""
        assert slugify("hello_world") == "hello-world"

    def test_empty_string(self):
        """Test empty string handling."""
        assert slugify("") == ""
        assert slugify("   ") == ""


@pytest.mark.unit
@pytest.mark.cli
class TestTitleize:
    """Test title generation from slugs."""

    def test_basic_titleize(self):
        """Test basic title generation."""
        assert titleize("hello-world") == "Hello World"
        assert titleize("my-blog-post") == "My Blog Post"

    def test_underscores(self):
        """Test that underscores are converted."""
        assert titleize("hello_world") == "Hello World"

    def test_mixed_separators(self):
        """Test mixed separators."""
        assert titleize("hello-world_test") == "Hello World Test"


@pytest.mark.unit
@pytest.mark.cli
class TestGenerateSectionIndex:
    """Test section index generation."""

    def test_basic_section_index(self):
        """Test basic section index generation."""
        content = generate_section_index("blog", 10)

        assert "title: Blog" in content
        assert "description: Blog section" in content
        assert "type: section" in content
        assert "weight: 10" in content
        assert "# Blog" in content
        assert "<!-- TODO: Customize this section -->" in content

    def test_multi_word_section(self):
        """Test multi-word section names."""
        content = generate_section_index("my-projects", 20)

        assert "title: My Projects" in content
        assert "weight: 20" in content
        assert "# My Projects" in content

    def test_weight_increments(self):
        """Test different weight values."""
        content1 = generate_section_index("section1", 10)
        content2 = generate_section_index("section2", 20)
        content3 = generate_section_index("section3", 30)

        assert "weight: 10" in content1
        assert "weight: 20" in content2
        assert "weight: 30" in content3


@pytest.mark.unit
@pytest.mark.cli
class TestGenerateSamplePage:
    """Test sample page generation."""

    def test_basic_sample_page(self):
        """Test basic sample page generation."""
        test_date = datetime(2025, 10, 12, 12, 0, 0)
        content = generate_sample_page("blog", "welcome-post", 1, test_date)

        assert "title: Welcome Post" in content
        assert "date: 2025-10-12T12:00:00" in content
        assert "draft: false" in content
        assert "description: Sample page in the Blog section" in content
        assert "tags: [sample, generated]" in content
        assert "# Welcome Post" in content
        assert "<!-- TODO: Replace this sample content -->" in content

    def test_multi_word_page(self):
        """Test multi-word page names."""
        content = generate_sample_page("projects", "my-cool-project", 2)

        assert "title: My Cool Project" in content
        assert "Sample page in the Projects section" in content

    def test_date_handling(self):
        """Test that date is generated if not provided."""
        content = generate_sample_page("blog", "test-post", 1)

        # Should have a date field
        assert "date: " in content
        # Should be valid ISO format
        assert "T" in content


@pytest.mark.unit
@pytest.mark.cli
class TestGetSamplePageNames:
    """Test sample page name generation."""

    def test_blog_page_names(self):
        """Test blog-specific page names."""
        names = get_sample_page_names("blog", 5)

        assert len(names) == 5
        assert "welcome-post" in names
        assert "getting-started" in names
        assert "tips-and-tricks" in names

    def test_projects_page_names(self):
        """Test project-specific page names."""
        names = get_sample_page_names("projects", 3)

        assert len(names) == 3
        assert "project-alpha" in names
        assert "project-beta" in names
        assert "project-gamma" in names

    def test_portfolio_page_names(self):
        """Test portfolio uses project names."""
        names = get_sample_page_names("portfolio", 3)

        assert len(names) == 3
        assert "project-alpha" in names

    def test_docs_page_names(self):
        """Test documentation-specific page names."""
        names = get_sample_page_names("docs", 5)

        assert len(names) == 5
        assert "introduction" in names
        assert "quickstart" in names
        assert "installation" in names

    def test_generic_page_names(self):
        """Test generic page names for unknown sections."""
        names = get_sample_page_names("custom-section", 3)

        assert len(names) == 3
        assert "custom-section-page-1" in names
        assert "custom-section-page-2" in names
        assert "custom-section-page-3" in names

    def test_count_limit(self):
        """Test that we only get requested number of names."""
        names = get_sample_page_names("blog", 3)
        assert len(names) == 3

        names = get_sample_page_names("blog", 10)
        assert len(names) == 10


@pytest.mark.unit
@pytest.mark.cli
class TestFileOperation:
    """Test FileOperation class."""

    def test_file_operation_creation(self):
        """Test creating a FileOperation."""
        path = Path("content/blog/_index.md")
        content = "test content"

        op = FileOperation(path, content)

        assert op.path == path
        assert op.content == content
        assert op.is_overwrite is False

    def test_file_operation_size(self):
        """Test file size calculation."""
        content = "Hello, World!"
        op = FileOperation(Path("test.md"), content)

        assert op.size_bytes() == len(content.encode("utf-8"))

    def test_file_operation_unicode(self):
        """Test file size with unicode content."""
        content = "Hello, 世界! 🌍"
        op = FileOperation(Path("test.md"), content)

        # Unicode characters take multiple bytes
        assert op.size_bytes() > len(content)

    def test_file_operation_overwrite_flag(self):
        """Test overwrite flag."""
        op1 = FileOperation(Path("test.md"), "content", is_overwrite=False)
        op2 = FileOperation(Path("test.md"), "content", is_overwrite=True)

        assert op1.is_overwrite is False
        assert op2.is_overwrite is True


@pytest.mark.unit
@pytest.mark.cli
class TestPlanInitOperations:
    """Test operation planning logic."""

    def test_basic_planning(self, tmp_path):
        """Test basic operation planning."""
        content_dir = tmp_path / "content"
        content_dir.mkdir()

        operations, warnings = plan_init_operations(
            content_dir, ["blog", "projects"], with_content=False
        )

        assert len(warnings) == 0
        assert len(operations) == 2  # 2 section indexes

        # Check paths
        paths = [op.path for op in operations]
        assert content_dir / "blog" / "_index.md" in paths
        assert content_dir / "projects" / "_index.md" in paths

    def test_planning_with_content(self, tmp_path):
        """Test planning with sample content."""
        content_dir = tmp_path / "content"
        content_dir.mkdir()

        operations, warnings = plan_init_operations(
            content_dir, ["blog"], with_content=True, pages_per_section=3
        )

        assert len(warnings) == 0
        assert len(operations) == 4  # 1 index + 3 pages

        # Check that we have the index
        index_ops = [op for op in operations if op.path.name == "_index.md"]
        assert len(index_ops) == 1

        # Check that we have 3 pages
        page_ops = [op for op in operations if op.path.name != "_index.md"]
        assert len(page_ops) == 3

    def test_existing_section_warning(self, tmp_path):
        """Test warning for existing sections."""
        content_dir = tmp_path / "content"
        content_dir.mkdir()

        # Create existing section
        blog_dir = content_dir / "blog"
        blog_dir.mkdir()

        operations, warnings = plan_init_operations(
            content_dir, ["blog", "projects"], with_content=False, force=False
        )

        assert len(warnings) == 1
        assert "blog" in warnings[0]
        assert "already exists" in warnings[0]

        # Should only plan projects
        assert len(operations) == 1
        assert operations[0].path.parent.name == "projects"

    def test_force_flag(self, tmp_path):
        """Test force flag overwrites existing."""
        content_dir = tmp_path / "content"
        content_dir.mkdir()

        # Create existing section
        blog_dir = content_dir / "blog"
        blog_dir.mkdir()

        operations, warnings = plan_init_operations(
            content_dir, ["blog", "projects"], with_content=False, force=True
        )

        assert len(warnings) == 0
        assert len(operations) == 2  # Both sections

        # Check for overwrite flag
        blog_op = [op for op in operations if op.path.parent.name == "blog"][0]
        assert blog_op.is_overwrite is False  # File doesn't exist yet, just dir

    def test_weight_increments(self, tmp_path):
        """Test that weights increment correctly."""
        content_dir = tmp_path / "content"
        content_dir.mkdir()

        operations, _ = plan_init_operations(
            content_dir, ["section1", "section2", "section3"], with_content=False
        )

        # Check weights in content
        assert "weight: 10" in operations[0].content
        assert "weight: 20" in operations[1].content
        assert "weight: 30" in operations[2].content


@pytest.mark.integration
@pytest.mark.cli
class TestInitCLI:
    """Integration tests for the init CLI command."""

    def test_init_requires_content_directory(self, tmp_path):
        """Test that init fails outside a Bengal site."""
        runner = CliRunner()

        with runner.isolated_filesystem(temp_dir=tmp_path):
            result = runner.invoke(init, ["--sections", "blog"])

            assert result.exit_code != 0
            assert "Not in a Bengal site directory" in result.output

    def test_init_requires_sections(self, tmp_path):
        """Test that init requires --sections flag."""
        runner = CliRunner()

        with runner.isolated_filesystem(temp_dir=tmp_path):
            Path("content").mkdir()
            result = runner.invoke(init, [])

            assert result.exit_code != 0
            assert "Please provide --sections" in result.output

    def test_basic_init(self, tmp_path):
        """Test basic section initialization."""
        runner = CliRunner()

        with runner.isolated_filesystem(temp_dir=tmp_path):
            Path("content").mkdir()

            result = runner.invoke(init, ["--sections", "blog,projects"])

            assert result.exit_code == 0
            assert "Site initialized successfully" in result.output
            assert Path("content/blog/_index.md").exists()
            assert Path("content/projects/_index.md").exists()

    def test_init_with_content(self, tmp_path):
        """Test initialization with sample content."""
        runner = CliRunner()

        with runner.isolated_filesystem(temp_dir=tmp_path):
            Path("content").mkdir()

            result = runner.invoke(
                init, ["--sections", "blog", "--with-content", "--pages-per-section", "3"]
            )

            assert result.exit_code == 0
            assert "Site initialized successfully" in result.output

            # Check files exist
            assert Path("content/blog/_index.md").exists()
            assert Path("content/blog/welcome-post.md").exists()
            assert Path("content/blog/getting-started.md").exists()
            assert Path("content/blog/tips-and-tricks.md").exists()

    def test_dry_run(self, tmp_path):
        """Test dry-run mode."""
        runner = CliRunner()

        with runner.isolated_filesystem(temp_dir=tmp_path):
            Path("content").mkdir()

            result = runner.invoke(init, ["--sections", "blog", "--dry-run"])

            assert result.exit_code == 0
            assert "Dry run - no files will be created" in result.output
            assert "Would create:" in result.output

            # Files should NOT be created
            assert not Path("content/blog/_index.md").exists()

    def test_name_sanitization(self, tmp_path):
        """Test that section names are sanitized."""
        runner = CliRunner()

        with runner.isolated_filesystem(temp_dir=tmp_path):
            Path("content").mkdir()

            result = runner.invoke(init, ["--sections", "My Blog,Cool Projects"])

            assert result.exit_code == 0
            assert "Section names sanitized" in result.output
            assert "'My Blog' → 'my-blog'" in result.output
            assert "'Cool Projects' → 'cool-projects'" in result.output

            # Check sanitized directories exist
            assert Path("content/my-blog/_index.md").exists()
            assert Path("content/cool-projects/_index.md").exists()

    def test_existing_section_warning(self, tmp_path):
        """Test warning for existing sections."""
        runner = CliRunner()

        with runner.isolated_filesystem(temp_dir=tmp_path):
            Path("content").mkdir()

            # First init
            result = runner.invoke(init, ["--sections", "blog"])
            assert result.exit_code == 0

            # Try again without force
            result = runner.invoke(init, ["--sections", "blog,projects"])

            assert result.exit_code == 0
            assert "Warnings:" in result.output
            assert "already exists" in result.output

            # Should still create projects
            assert Path("content/projects/_index.md").exists()

    def test_force_flag(self, tmp_path):
        """Test force flag overwrites existing."""
        runner = CliRunner()

        with runner.isolated_filesystem(temp_dir=tmp_path):
            Path("content").mkdir()

            # First init
            result = runner.invoke(init, ["--sections", "blog"])
            assert result.exit_code == 0

            # Write custom content
            blog_index = Path("content/blog/_index.md")
            blog_index.write_text("CUSTOM CONTENT")

            # Init again with force
            result = runner.invoke(init, ["--sections", "blog", "--force"])

            assert result.exit_code == 0

            # Content should be regenerated
            new_content = blog_index.read_text()
            assert new_content != "CUSTOM CONTENT"
            assert "title: Blog" in new_content

    def test_help_text(self):
        """Test help text is displayed."""
        runner = CliRunner()
        result = runner.invoke(init, ["--help"])

        assert result.exit_code == 0
        assert "Initialize site structure" in result.output
        assert "--sections" in result.output
        assert "--with-content" in result.output
        assert "--dry-run" in result.output
        assert "--force" in result.output
        assert "Examples:" in result.output


@pytest.mark.integration
@pytest.mark.cli
class TestInitContentQuality:
    """Test the quality of generated content."""

    def test_section_index_quality(self, tmp_path):
        """Test that section indexes have good quality."""
        runner = CliRunner()

        with runner.isolated_filesystem(temp_dir=tmp_path):
            Path("content").mkdir()

            runner.invoke(init, ["--sections", "blog"])

            content = Path("content/blog/_index.md").read_text()

            # Check frontmatter
            assert "---" in content
            assert "title: Blog" in content
            assert "description:" in content
            assert "type: section" in content
            assert "weight:" in content

            # Check body
            assert "# Blog" in content
            assert "TODO:" in content

    def test_sample_page_quality(self, tmp_path):
        """Test that sample pages have good quality."""
        runner = CliRunner()

        with runner.isolated_filesystem(temp_dir=tmp_path):
            Path("content").mkdir()

            runner.invoke(
                init, ["--sections", "blog", "--with-content", "--pages-per-section", "1"]
            )

            content = Path("content/blog/welcome-post.md").read_text()

            # Check frontmatter
            assert "---" in content
            assert "title:" in content
            assert "date:" in content
            assert "draft: false" in content
            assert "description:" in content
            assert "tags:" in content

            # Check body
            assert "# " in content
            assert "TODO:" in content

    def test_date_staggering(self, tmp_path):
        """Test that blog post dates are staggered."""
        runner = CliRunner()

        with runner.isolated_filesystem(temp_dir=tmp_path):
            Path("content").mkdir()

            runner.invoke(
                init, ["--sections", "blog", "--with-content", "--pages-per-section", "3"]
            )

            # Read dates from files
            files = ["welcome-post.md", "getting-started.md", "tips-and-tricks.md"]
            dates = []

            for file in files:
                content = Path(f"content/blog/{file}").read_text()
                # Extract date line
                for line in content.split("\n"):
                    if line.startswith("date:"):
                        dates.append(line)
                        break

            # Dates should be different
            assert len(set(dates)) == 3


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
