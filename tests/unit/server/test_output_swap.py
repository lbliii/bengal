"""Tests for output directory double-buffer swap mechanism."""

from __future__ import annotations

from pathlib import Path

from bengal.server.output_swap import (
    SwapConfig,
    cleanup_swap_artifacts,
    commit_staging,
    prepare_staging,
    rollback_staging,
)


class TestSwapConfig:
    """Tests for SwapConfig."""

    def test_from_output_dir(self, tmp_path: Path) -> None:
        output_dir = tmp_path / "public"
        config = SwapConfig.from_output_dir(output_dir)

        assert config.live_dir == output_dir
        assert config.staging_dir == tmp_path / ".staging"
        assert config.old_dir == tmp_path / ".public.old"


class TestPrepareStaging:
    """Tests for prepare_staging."""

    def test_creates_empty_staging(self, tmp_path: Path) -> None:
        config = SwapConfig.from_output_dir(tmp_path / "public")
        staging = prepare_staging(config)

        assert staging.exists()
        assert staging.is_dir()
        assert list(staging.iterdir()) == []

    def test_cleans_leftover_staging(self, tmp_path: Path) -> None:
        config = SwapConfig.from_output_dir(tmp_path / "public")
        config.staging_dir.mkdir(parents=True)
        (config.staging_dir / "stale.html").write_text("old build output")

        staging = prepare_staging(config)

        assert staging.exists()
        assert list(staging.iterdir()) == []


class TestCommitStaging:
    """Tests for commit_staging (atomic swap)."""

    def test_swaps_staging_into_live(self, tmp_path: Path) -> None:
        live = tmp_path / "public"
        live.mkdir()
        (live / "old.html").write_text("old content")

        config = SwapConfig.from_output_dir(live)
        config.staging_dir.mkdir()
        (config.staging_dir / "new.html").write_text("new content")

        commit_staging(config)

        assert live.exists()
        assert (live / "new.html").read_text() == "new content"
        assert not (live / "old.html").exists()

    def test_staging_replaces_live_atomically(self, tmp_path: Path) -> None:
        """Verify the swap is a rename, not copy-delete."""
        live = tmp_path / "public"
        live.mkdir()
        (live / "page.html").write_text("<html>v1</html>")

        config = SwapConfig.from_output_dir(live)
        staging = config.staging_dir
        staging.mkdir()
        (staging / "page.html").write_text("<html>v2</html>")
        (staging / "style.css").write_text("body{}")

        commit_staging(config)

        assert (live / "page.html").read_text() == "<html>v2</html>"
        assert (live / "style.css").read_text() == "body{}"
        assert not staging.exists()

    def test_skips_when_staging_missing(self, tmp_path: Path) -> None:
        live = tmp_path / "public"
        live.mkdir()
        config = SwapConfig.from_output_dir(live)

        commit_staging(config)

        assert live.exists()

    def test_cleans_prior_old_dir(self, tmp_path: Path) -> None:
        live = tmp_path / "public"
        live.mkdir()

        config = SwapConfig.from_output_dir(live)
        config.old_dir.mkdir()
        (config.old_dir / "leftover.html").write_text("stale")

        config.staging_dir.mkdir()
        (config.staging_dir / "fresh.html").write_text("new")

        commit_staging(config)

        assert (live / "fresh.html").exists()


class TestRollbackStaging:
    """Tests for rollback_staging."""

    def test_removes_staging_dir(self, tmp_path: Path) -> None:
        config = SwapConfig.from_output_dir(tmp_path / "public")
        config.staging_dir.mkdir(parents=True)
        (config.staging_dir / "partial.html").write_text("incomplete")

        rollback_staging(config)

        assert not config.staging_dir.exists()

    def test_noop_when_no_staging(self, tmp_path: Path) -> None:
        config = SwapConfig.from_output_dir(tmp_path / "public")

        rollback_staging(config)


class TestCleanupSwapArtifacts:
    """Tests for cleanup_swap_artifacts."""

    def test_cleans_both_artifacts(self, tmp_path: Path) -> None:
        output_dir = tmp_path / "public"
        output_dir.mkdir()

        staging = tmp_path / ".staging"
        staging.mkdir()
        (staging / "orphan.html").write_text("crashed build")

        old = tmp_path / ".public.old"
        old.mkdir()
        (old / "stale.html").write_text("pre-swap")

        cleanup_swap_artifacts(output_dir)

        assert not staging.exists()
        assert not old.exists()
        assert output_dir.exists()

    def test_noop_when_clean(self, tmp_path: Path) -> None:
        output_dir = tmp_path / "public"
        output_dir.mkdir()

        cleanup_swap_artifacts(output_dir)


class TestFullSwapLifecycle:
    """Integration tests for the full prepare → build → commit lifecycle."""

    def test_successful_build_cycle(self, tmp_path: Path) -> None:
        """Simulate: prepare staging → write build output → commit swap."""
        live = tmp_path / "public"
        live.mkdir()
        (live / "index.html").write_text("<html>v1</html>")
        (live / "assets").mkdir()
        (live / "assets" / "style.css").write_text(".v1{}")

        config = SwapConfig.from_output_dir(live)

        staging = prepare_staging(config)
        (staging / "index.html").write_text("<html>v2</html>")
        (staging / "assets").mkdir()
        (staging / "assets" / "style.css").write_text(".v2{}")

        commit_staging(config)

        assert (live / "index.html").read_text() == "<html>v2</html>"
        assert (live / "assets" / "style.css").read_text() == ".v2{}"
        assert not config.staging_dir.exists()

    def test_failed_build_preserves_live(self, tmp_path: Path) -> None:
        """Simulate: prepare staging → build fails → rollback."""
        live = tmp_path / "public"
        live.mkdir()
        (live / "index.html").write_text("<html>good</html>")

        config = SwapConfig.from_output_dir(live)
        staging = prepare_staging(config)
        (staging / "broken.html").write_text("<html>bad</html>")

        rollback_staging(config)

        assert (live / "index.html").read_text() == "<html>good</html>"
        assert not (live / "broken.html").exists()
        assert not config.staging_dir.exists()

    def test_rapid_rebuild_cycle(self, tmp_path: Path) -> None:
        """Simulate rapid rebuilds: v1 → v2 → v3."""
        live = tmp_path / "public"
        live.mkdir()
        (live / "page.html").write_text("v1")

        for version in ("v2", "v3"):
            config = SwapConfig.from_output_dir(live)
            staging = prepare_staging(config)
            (staging / "page.html").write_text(version)
            commit_staging(config)

            assert (live / "page.html").read_text() == version

    def test_server_reads_consistent_state(self, tmp_path: Path) -> None:
        """Verify that the live dir always has complete content."""
        live = tmp_path / "public"
        live.mkdir()
        (live / "index.html").write_text("<html>original</html>")
        (live / "style.css").write_text("body{color:black}")

        config = SwapConfig.from_output_dir(live)
        staging = prepare_staging(config)

        assert (live / "index.html").read_text() == "<html>original</html>"
        assert (live / "style.css").read_text() == "body{color:black}"

        (staging / "index.html").write_text("<html>updated</html>")
        (staging / "style.css").write_text("body{color:red}")

        assert (live / "index.html").read_text() == "<html>original</html>"
        assert (live / "style.css").read_text() == "body{color:black}"

        commit_staging(config)

        assert (live / "index.html").read_text() == "<html>updated</html>"
        assert (live / "style.css").read_text() == "body{color:red}"
