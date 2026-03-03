"""
Tests for purge module of the incremental package.

RFC: stale-output-purge - purge_stale_outputs removes files not in manifest.
"""

from bengal.orchestration.incremental.purge import purge_stale_outputs


class TestPurgeStaleOutputs:
    """Test purge_stale_outputs function."""

    def test_no_purge_when_output_dir_missing(self, tmp_path):
        """Returns 0 when output_dir does not exist."""
        missing_dir = tmp_path / "nonexistent"
        manifest = frozenset({"page/index.html"})

        count = purge_stale_outputs(missing_dir, manifest)

        assert count == 0

    def test_keeps_files_in_manifest(self, tmp_path):
        """Files in manifest are not deleted."""
        output_dir = tmp_path / "public"
        output_dir.mkdir()
        kept = output_dir / "page" / "index.html"
        kept.parent.mkdir(parents=True)
        kept.write_text("<html></html>")

        manifest = frozenset({"page/index.html"})
        count = purge_stale_outputs(output_dir, manifest)

        assert count == 0
        assert kept.exists()

    def test_deletes_files_not_in_manifest(self, tmp_path):
        """Files not in manifest are deleted."""
        output_dir = tmp_path / "public"
        output_dir.mkdir()
        stale = output_dir / "stale" / "index.html"
        stale.parent.mkdir(parents=True)
        stale.write_text("<html>stale</html>")

        manifest = frozenset({"page/index.html"})
        count = purge_stale_outputs(output_dir, manifest)

        assert count == 1
        assert not stale.exists()

    def test_preserves_keep_files(self, tmp_path):
        """Files in keep_files (e.g. .nojekyll) are never deleted."""
        output_dir = tmp_path / "public"
        output_dir.mkdir()
        nojekyll = output_dir / ".nojekyll"
        nojekyll.write_text("")
        gitignore = output_dir / ".gitignore"
        gitignore.write_text("*.log")

        manifest = frozenset()
        count = purge_stale_outputs(output_dir, manifest)

        assert count == 0
        assert nojekyll.exists()
        assert gitignore.exists()

    def test_removes_empty_directories(self, tmp_path):
        """Empty directories are removed after file deletion."""
        output_dir = tmp_path / "public"
        output_dir.mkdir()
        stale = output_dir / "orphan" / "index.html"
        stale.parent.mkdir(parents=True)
        stale.write_text("<html></html>")

        manifest = frozenset()
        count = purge_stale_outputs(output_dir, manifest)

        assert count == 1
        assert not stale.exists()
        assert not stale.parent.exists()

    def test_posix_normalization(self, tmp_path):
        """Manifest paths use posix normalization for cross-platform."""
        output_dir = tmp_path / "public"
        output_dir.mkdir()
        kept = output_dir / "blog" / "post" / "index.html"
        kept.parent.mkdir(parents=True)
        kept.write_text("<html></html>")

        manifest = frozenset({"blog/post/index.html"})
        count = purge_stale_outputs(output_dir, manifest)

        assert count == 0
        assert kept.exists()
