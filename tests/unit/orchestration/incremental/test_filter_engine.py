"""Tests for IncrementalFilterEngine component.

RFC: rfc-rebuild-decision-hardening

Tests cover:
- Decision pipeline ordering
- Full rebuild triggers (output missing, incremental disabled, autodoc missing)
- Skip conditions
- Fingerprint cascade
- Legacy decision bridge
- Regress-to-bug tests (Bug 1: output_html_missing, Bug 2: stale reference)
"""

from pathlib import Path
from unittest.mock import Mock

import pytest

from bengal.cache import BuildCache
from bengal.core.asset import Asset
from bengal.core.page import Page
from bengal.orchestration.incremental.filter_engine import (
    DefaultOutputChecker,
    FilterDecision,
    FilterDecisionLog,
    FilterDecisionType,
    FullRebuildTrigger,
    IncrementalFilterEngine,
    OutputPresenceResult,
)


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def tmp_output_dir(tmp_path: Path) -> Path:
    """Create a temporary output directory with minimal structure."""
    output_dir = tmp_path / "public"
    output_dir.mkdir(parents=True)
    # Create minimal assets
    assets_dir = output_dir / "assets"
    assets_dir.mkdir()
    (assets_dir / "main.css").write_text("/* css */")
    (assets_dir / "main.js").write_text("// js")
    (assets_dir / "icons.svg").write_text("<svg></svg>")
    return output_dir


@pytest.fixture
def empty_output_dir(tmp_path: Path) -> Path:
    """Create an empty output directory."""
    output_dir = tmp_path / "public"
    output_dir.mkdir(parents=True)
    return output_dir


@pytest.fixture
def mock_cache() -> Mock:
    """Create a mock BuildCache."""
    cache = Mock(spec=BuildCache)
    cache.is_changed = Mock(return_value=False)
    cache.get_all_tags = Mock(return_value=[])
    cache.autodoc_dependencies = {}
    return cache


@pytest.fixture
def mock_pages(tmp_path: Path) -> list[Page]:
    """Create mock pages for testing."""
    content_dir = tmp_path / "content"
    content_dir.mkdir(parents=True)
    
    pages = []
    for i in range(5):
        source_path = content_dir / f"page{i}.md"
        source_path.write_text(f"# Page {i}")
        pages.append(
            Page(
                source_path=source_path,
                _raw_content=f"# Page {i}",
                metadata={"title": f"Page {i}"},
            )
        )
    return pages


@pytest.fixture
def mock_assets(tmp_path: Path) -> list[Asset]:
    """Create mock assets for testing."""
    assets_dir = tmp_path / "assets"
    assets_dir.mkdir(parents=True)
    
    assets = []
    for suffix in [".css", ".js", ".png"]:
        source_path = assets_dir / f"asset{suffix}"
        source_path.write_text(f"/* {suffix} */")
        assets.append(Asset(source_path=source_path))
    return assets


@pytest.fixture
def engine_with_output(
    mock_cache: Mock, tmp_output_dir: Path
) -> IncrementalFilterEngine:
    """Create filter engine with existing output directory."""
    return IncrementalFilterEngine(
        cache=mock_cache,
        output_dir=tmp_output_dir,
    )


@pytest.fixture
def engine_empty_output(
    mock_cache: Mock, empty_output_dir: Path
) -> IncrementalFilterEngine:
    """Create filter engine with empty output directory."""
    return IncrementalFilterEngine(
        cache=mock_cache,
        output_dir=empty_output_dir,
    )


# =============================================================================
# DefaultOutputChecker Tests
# =============================================================================


class TestDefaultOutputChecker:
    """Tests for DefaultOutputChecker."""

    def test_check_output_exists(self, tmp_output_dir: Path) -> None:
        """Test checker when output exists with assets."""
        checker = DefaultOutputChecker()
        result = checker.check(tmp_output_dir)
        
        assert result.is_present is True
        assert result.reason is None

    def test_check_output_dir_not_exists(self, tmp_path: Path) -> None:
        """Test checker when output directory doesn't exist."""
        checker = DefaultOutputChecker()
        result = checker.check(tmp_path / "nonexistent")
        
        assert result.is_present is False
        assert result.reason == "output_dir_not_exists"

    def test_check_output_dir_empty(self, empty_output_dir: Path) -> None:
        """Test checker when output directory is empty."""
        checker = DefaultOutputChecker()
        result = checker.check(empty_output_dir)
        
        assert result.is_present is False
        assert result.reason == "output_dir_empty"

    def test_check_assets_dir_missing(self, empty_output_dir: Path) -> None:
        """Test checker when assets directory is missing."""
        # Add some content but no assets dir
        (empty_output_dir / "index.html").write_text("<html></html>")
        
        checker = DefaultOutputChecker()
        result = checker.check(empty_output_dir)
        
        assert result.is_present is False
        assert result.reason == "assets_dir_not_exists"

    def test_check_insufficient_assets(self, empty_output_dir: Path) -> None:
        """Test checker when assets directory has insufficient files."""
        (empty_output_dir / "index.html").write_text("<html></html>")
        assets_dir = empty_output_dir / "assets"
        assets_dir.mkdir()
        (assets_dir / "main.css").write_text("/* css */")
        # Only 1 asset, need MIN_ASSET_FILES (3)
        
        checker = DefaultOutputChecker()
        result = checker.check(empty_output_dir)
        
        assert result.is_present is False
        assert "assets_insufficient" in result.reason


# =============================================================================
# FilterDecisionLog Tests
# =============================================================================


class TestFilterDecisionLog:
    """Tests for FilterDecisionLog dataclass."""

    def test_to_dict(self) -> None:
        """Test conversion to dictionary."""
        log = FilterDecisionLog(
            incremental_enabled=True,
            output_present=True,
            pages_with_changes=5,
            decision_type=FilterDecisionType.INCREMENTAL,
        )
        
        result = log.to_dict()
        
        assert result["incremental_enabled"] is True
        assert result["output_present"] is True
        assert result["pages_with_changes"] == 5
        assert result["decision_type"] == "incremental"
        assert result["full_rebuild_trigger"] is None

    def test_to_dict_with_trigger(self) -> None:
        """Test conversion with full rebuild trigger."""
        log = FilterDecisionLog(
            decision_type=FilterDecisionType.FULL,
            full_rebuild_trigger=FullRebuildTrigger.OUTPUT_DIR_EMPTY,
        )
        
        result = log.to_dict()
        
        assert result["decision_type"] == "full"
        assert result["full_rebuild_trigger"] == "output_dir_empty"

    def test_to_dict_includes_layer_trace(self) -> None:
        """Test that to_dict includes layer_trace field (RFC: rfc-incremental-build-observability)."""
        log = FilterDecisionLog(
            incremental_enabled=True,
            decision_type=FilterDecisionType.INCREMENTAL,
            # Layer 1: Data files
            data_files_checked=5,
            data_files_changed=2,
            data_file_fingerprints_available=True,
            # Layer 2: Autodoc
            autodoc_sources_total=10,
            autodoc_sources_stale=1,
            autodoc_metadata_available=True,
            autodoc_stale_method="metadata",
            # Layer 3: Sections
            sections_total=3,
            sections_marked_changed=["docs"],
            section_change_reasons={"docs": "content_changed"},
            # Layer 4: Page filtering
            pages_in_changed_sections=15,
            pages_filtered_by_section=85,
        )
        
        result = log.to_dict()
        
        # Verify layer_trace structure
        assert "layer_trace" in result
        trace = result["layer_trace"]
        
        # Layer 1
        assert trace["data_files"]["checked"] == 5
        assert trace["data_files"]["changed"] == 2
        assert trace["data_files"]["fingerprints_available"] is True
        
        # Layer 2
        assert trace["autodoc"]["sources_total"] == 10
        assert trace["autodoc"]["sources_stale"] == 1
        assert trace["autodoc"]["metadata_available"] is True
        assert trace["autodoc"]["stale_method"] == "metadata"
        
        # Layer 3
        assert trace["sections"]["total"] == 3
        assert trace["sections"]["changed"] == ["docs"]
        assert trace["sections"]["change_reasons"] == {"docs": "content_changed"}
        
        # Layer 4
        assert trace["page_filtering"]["in_changed_sections"] == 15
        assert trace["page_filtering"]["filtered_out"] == 85

    def test_to_trace_output(self) -> None:
        """Test human-readable trace output (RFC: rfc-incremental-build-observability)."""
        log = FilterDecisionLog(
            decision_type=FilterDecisionType.INCREMENTAL,
            data_files_checked=3,
            data_files_changed=0,
            data_file_fingerprints_available=True,
            autodoc_sources_total=448,
            autodoc_sources_stale=0,
            autodoc_metadata_available=False,
            autodoc_fingerprint_fallback_used=True,
            autodoc_stale_method="fingerprint",
            sections_total=5,
            sections_marked_changed=["docs"],
            section_change_reasons={"docs": "subsection_changed:about/glossary.md"},
            pages_in_changed_sections=35,
            pages_filtered_by_section=1028,
        )
        
        output = log.to_trace_output()
        
        # Verify key sections are present
        assert "DECISION TRACE" in output
        assert "Decision: INCREMENTAL" in output
        
        # Layer 1
        assert "Layer 1: Data Files" in output
        assert "Checked:     3" in output
        assert "Changed:     0" in output
        assert "Fingerprints available: ✓" in output
        
        # Layer 2
        assert "Layer 2: Autodoc" in output
        assert "Sources tracked: 448" in output
        assert "⚠ Using fingerprint fallback" in output
        assert "Detection method: fingerprint" in output
        
        # Layer 3
        assert "Layer 3: Section Optimization" in output
        assert "Sections total:   5" in output
        assert "docs" in output
        
        # Layer 4
        assert "Layer 4: Page Filtering" in output
        assert "In changed sections: 35" in output
        assert "Filtered out:        1028" in output


# =============================================================================
# FilterDecision Tests
# =============================================================================


class TestFilterDecision:
    """Tests for FilterDecision dataclass."""

    def test_properties(self, mock_pages: list[Page]) -> None:
        """Test FilterDecision properties."""
        log = FilterDecisionLog(
            decision_type=FilterDecisionType.FULL,
            full_rebuild_trigger=FullRebuildTrigger.INCREMENTAL_DISABLED,
        )
        decision = FilterDecision(
            pages_to_build=mock_pages[:2],
            assets_to_process=[],
            affected_tags={"python"},
            affected_sections={"docs"},
            changed_page_paths=set(),
            decision_log=log,
        )
        
        assert decision.decision_type == FilterDecisionType.FULL
        assert decision.is_full_rebuild is True
        assert decision.is_skip is False
        assert decision.full_rebuild_reason == "incremental_disabled"

    def test_skip_decision(self) -> None:
        """Test skip decision properties."""
        log = FilterDecisionLog(decision_type=FilterDecisionType.SKIP)
        decision = FilterDecision(
            pages_to_build=[],
            assets_to_process=[],
            affected_tags=set(),
            affected_sections=set(),
            changed_page_paths=set(),
            decision_log=log,
        )
        
        assert decision.is_skip is True
        assert decision.is_full_rebuild is False
        assert decision.full_rebuild_reason is None

    def test_to_legacy_decision_full(self, mock_pages: list[Page]) -> None:
        """Test conversion to legacy IncrementalDecision for full rebuild."""
        log = FilterDecisionLog(
            decision_type=FilterDecisionType.FULL,
            full_rebuild_trigger=FullRebuildTrigger.OUTPUT_DIR_EMPTY,
            pages_skipped=0,
        )
        decision = FilterDecision(
            pages_to_build=mock_pages,
            assets_to_process=[],
            affected_tags=set(),
            affected_sections=set(),
            changed_page_paths=set(),
            decision_log=log,
        )
        
        legacy = decision.to_legacy_decision()
        
        assert len(legacy.pages_to_build) == len(mock_pages)
        assert legacy.pages_skipped_count == 0
        # All pages should have OUTPUT_MISSING reason
        for page in mock_pages:
            assert str(page.source_path) in legacy.rebuild_reasons

    def test_to_legacy_decision_fingerprint(self, mock_pages: list[Page]) -> None:
        """Test conversion preserves fingerprint change info."""
        log = FilterDecisionLog(
            decision_type=FilterDecisionType.INCREMENTAL,
            fingerprint_cascade_triggered=True,
            fingerprint_assets_changed=["main.css", "main.js"],
        )
        decision = FilterDecision(
            pages_to_build=mock_pages[:2],
            assets_to_process=[],
            affected_tags=set(),
            affected_sections=set(),
            changed_page_paths=set(),
            decision_log=log,
        )
        
        legacy = decision.to_legacy_decision()
        
        assert legacy.fingerprint_changes is True
        assert legacy.asset_changes == ["main.css", "main.js"]


# =============================================================================
# IncrementalFilterEngine Basic Tests
# =============================================================================


class TestIncrementalFilterEngineBasic:
    """Basic tests for IncrementalFilterEngine."""

    def test_full_rebuild_when_incremental_disabled(
        self,
        engine_with_output: IncrementalFilterEngine,
        mock_pages: list[Page],
        mock_assets: list[Asset],
    ) -> None:
        """Test that incremental=False triggers full rebuild."""
        decision = engine_with_output.decide(
            pages=mock_pages,
            assets=mock_assets,
            incremental=False,
        )
        
        assert decision.is_full_rebuild
        assert decision.decision_log.full_rebuild_trigger == FullRebuildTrigger.INCREMENTAL_DISABLED
        assert len(decision.pages_to_build) == len(mock_pages)
        assert len(decision.assets_to_process) == len(mock_assets)

    def test_full_rebuild_when_output_missing(
        self,
        engine_empty_output: IncrementalFilterEngine,
        mock_pages: list[Page],
        mock_assets: list[Asset],
    ) -> None:
        """Test that empty output triggers full rebuild."""
        decision = engine_empty_output.decide(
            pages=mock_pages,
            assets=mock_assets,
            incremental=True,
        )
        
        assert decision.is_full_rebuild
        assert decision.decision_log.full_rebuild_trigger == FullRebuildTrigger.OUTPUT_DIR_EMPTY
        assert not decision.decision_log.output_present

    def test_skip_when_no_changes(
        self,
        engine_with_output: IncrementalFilterEngine,
        mock_pages: list[Page],
        mock_assets: list[Asset],
    ) -> None:
        """Test that no changes triggers skip decision."""
        decision = engine_with_output.decide(
            pages=mock_pages,
            assets=mock_assets,
            incremental=True,
        )
        
        assert decision.is_skip
        assert decision.decision_log.decision_type == FilterDecisionType.SKIP
        assert len(decision.pages_to_build) == 0
        assert len(decision.assets_to_process) == 0

    def test_incremental_when_pages_changed(
        self,
        mock_cache: Mock,
        tmp_output_dir: Path,
        mock_pages: list[Page],
        mock_assets: list[Asset],
    ) -> None:
        """Test incremental decision when some pages changed."""
        # Mark first two pages as changed
        def is_changed(path: Path) -> bool:
            return "page0" in str(path) or "page1" in str(path)
        mock_cache.is_changed.side_effect = is_changed
        
        engine = IncrementalFilterEngine(
            cache=mock_cache,
            output_dir=tmp_output_dir,
        )
        
        decision = engine.decide(
            pages=mock_pages,
            assets=mock_assets,
            incremental=True,
        )
        
        assert not decision.is_full_rebuild
        assert not decision.is_skip
        assert decision.decision_type == FilterDecisionType.INCREMENTAL
        assert len(decision.pages_to_build) == 2


# =============================================================================
# Fingerprint Cascade Tests
# =============================================================================


class TestFingerprintCascade:
    """Tests for CSS/JS fingerprint cascade behavior."""

    def test_css_change_forces_all_pages(
        self,
        mock_cache: Mock,
        tmp_output_dir: Path,
        mock_pages: list[Page],
        mock_assets: list[Asset],
    ) -> None:
        """Test that CSS asset change triggers all pages to rebuild."""
        # Mark only the CSS asset as changed
        def is_changed(path: Path) -> bool:
            return path.suffix == ".css"
        mock_cache.is_changed.side_effect = is_changed
        
        engine = IncrementalFilterEngine(
            cache=mock_cache,
            output_dir=tmp_output_dir,
        )
        
        decision = engine.decide(
            pages=mock_pages,
            assets=mock_assets,
            incremental=True,
        )
        
        assert decision.decision_log.fingerprint_cascade_triggered
        assert "asset.css" in decision.decision_log.fingerprint_assets_changed
        # All pages should be rebuilt when fingerprint changes
        assert len(decision.pages_to_build) == len(mock_pages)

    def test_js_change_forces_all_pages(
        self,
        mock_cache: Mock,
        tmp_output_dir: Path,
        mock_pages: list[Page],
        mock_assets: list[Asset],
    ) -> None:
        """Test that JS asset change triggers all pages to rebuild."""
        def is_changed(path: Path) -> bool:
            return path.suffix == ".js"
        mock_cache.is_changed.side_effect = is_changed
        
        engine = IncrementalFilterEngine(
            cache=mock_cache,
            output_dir=tmp_output_dir,
        )
        
        decision = engine.decide(
            pages=mock_pages,
            assets=mock_assets,
            incremental=True,
        )
        
        assert decision.decision_log.fingerprint_cascade_triggered
        assert len(decision.pages_to_build) == len(mock_pages)

    def test_non_fingerprint_asset_no_cascade(
        self,
        mock_cache: Mock,
        tmp_output_dir: Path,
        mock_pages: list[Page],
        mock_assets: list[Asset],
    ) -> None:
        """Test that PNG change doesn't trigger cascade."""
        def is_changed(path: Path) -> bool:
            return path.suffix == ".png"
        mock_cache.is_changed.side_effect = is_changed
        
        engine = IncrementalFilterEngine(
            cache=mock_cache,
            output_dir=tmp_output_dir,
        )
        
        decision = engine.decide(
            pages=mock_pages,
            assets=mock_assets,
            incremental=True,
        )
        
        assert not decision.decision_log.fingerprint_cascade_triggered
        # Only the asset should be processed, not all pages
        assert len(decision.assets_to_process) == 1
        assert len(decision.pages_to_build) == 0


# =============================================================================
# Taxonomy and Special Pages Tests
# =============================================================================


class TestTaxonomyAndSpecialPages:
    """Tests for taxonomy regeneration and special pages behavior."""

    def test_taxonomy_regen_prevents_skip(
        self,
        engine_with_output: IncrementalFilterEngine,
        mock_pages: list[Page],
        mock_assets: list[Asset],
    ) -> None:
        """Test that needs_taxonomy_regen prevents skip decision."""
        decision = engine_with_output.decide(
            pages=mock_pages,
            assets=mock_assets,
            incremental=True,
            needs_taxonomy_regen=True,
        )
        
        # Should NOT skip even though no content changes
        assert not decision.is_skip
        assert decision.decision_log.taxonomy_regen_needed is True

    def test_special_pages_missing_prevents_skip(
        self,
        mock_cache: Mock,
        tmp_output_dir: Path,
        mock_pages: list[Page],
        mock_assets: list[Asset],
    ) -> None:
        """Test that missing special pages prevents skip decision."""
        # Mock special pages checker that returns True (missing)
        special_pages_checker = Mock()
        special_pages_checker.check.return_value = True
        
        engine = IncrementalFilterEngine(
            cache=mock_cache,
            output_dir=tmp_output_dir,
            special_pages_checker=special_pages_checker,
        )
        
        decision = engine.decide(
            pages=mock_pages,
            assets=mock_assets,
            incremental=True,
        )
        
        assert not decision.is_skip
        assert decision.decision_log.special_pages_missing is True


# =============================================================================
# Autodoc Output Tests
# =============================================================================


class TestAutodocOutput:
    """Tests for autodoc output checking."""

    def test_autodoc_missing_forces_full_rebuild(
        self,
        mock_cache: Mock,
        tmp_output_dir: Path,
        mock_pages: list[Page],
        mock_assets: list[Asset],
    ) -> None:
        """Test that missing autodoc output forces full rebuild."""
        # Mock autodoc checker that returns True (missing)
        autodoc_checker = Mock()
        autodoc_checker.check.return_value = True
        
        engine = IncrementalFilterEngine(
            cache=mock_cache,
            output_dir=tmp_output_dir,
            autodoc_checker=autodoc_checker,
        )
        
        decision = engine.decide(
            pages=mock_pages,
            assets=mock_assets,
            incremental=True,
        )
        
        assert decision.is_full_rebuild
        assert decision.decision_log.full_rebuild_trigger == FullRebuildTrigger.AUTODOC_OUTPUT_MISSING
        assert decision.decision_log.autodoc_output_missing is True


# =============================================================================
# Regress-to-Bug Tests (RFC: rfc-rebuild-decision-hardening)
# =============================================================================


class TestRegressToBugB1:
    """Regression tests for Bug 1: output_html_missing check.
    
    Bug: output_html_missing assumed root index.html existed, causing
    false full rebuilds for sites without a home page.
    
    Fix: Check if output_dir has ANY content instead of checking for index.html.
    """

    def test_output_dir_with_content_no_index_html(
        self,
        mock_cache: Mock,
        tmp_path: Path,
        mock_pages: list[Page],
    ) -> None:
        """Test that output with content but no index.html is INCREMENTAL, not FULL."""
        # Create output dir with content but NO index.html at root
        output_dir = tmp_path / "public"
        output_dir.mkdir()
        (output_dir / "docs").mkdir()
        (output_dir / "docs" / "index.html").write_text("<html>docs</html>")
        # Create minimal assets
        assets_dir = output_dir / "assets"
        assets_dir.mkdir()
        (assets_dir / "main.css").write_text("/* css */")
        (assets_dir / "main.js").write_text("// js")
        (assets_dir / "icons.svg").write_text("<svg></svg>")
        
        engine = IncrementalFilterEngine(
            cache=mock_cache,
            output_dir=output_dir,
        )
        
        # No changes, should SKIP (not FULL rebuild)
        decision = engine.decide(
            pages=mock_pages,
            assets=[],
            incremental=True,
        )
        
        # Key assertion: should be SKIP or INCREMENTAL, NOT FULL
        assert not decision.is_full_rebuild, (
            "Bug B1 regression: Should not force full rebuild when output has content but no root index.html"
        )

    def test_truly_empty_output_forces_full(
        self,
        mock_cache: Mock,
        tmp_path: Path,
        mock_pages: list[Page],
    ) -> None:
        """Test that truly empty output dir forces full rebuild (expected behavior)."""
        output_dir = tmp_path / "public"
        output_dir.mkdir()
        # Empty directory
        
        engine = IncrementalFilterEngine(
            cache=mock_cache,
            output_dir=output_dir,
        )
        
        decision = engine.decide(
            pages=mock_pages,
            assets=[],
            incremental=True,
        )
        
        assert decision.is_full_rebuild
        assert decision.decision_log.full_rebuild_trigger == FullRebuildTrigger.OUTPUT_DIR_EMPTY


class TestRegressToBugB2:
    """Regression tests for Bug 2: stale _change_detector reference.
    
    Bug: ChangeDetector kept reference to old cache after cache reinitialization,
    causing incorrect change detection.
    
    Fix: IncrementalOrchestrator.initialize() resets _change_detector to None.
    
    Note: This test validates the engine's behavior when detector is swapped,
    simulating the fix in orchestrator.py.
    """

    def test_engine_with_new_change_detector(
        self,
        mock_cache: Mock,
        tmp_output_dir: Path,
        mock_pages: list[Page],
    ) -> None:
        """Test that engine uses the change detector it was given, not a stale one."""
        # Create a change detector that says page0 changed
        change_detector_v1 = Mock()
        change_set_v1 = Mock()
        change_set_v1.pages_to_build = mock_pages[:1]  # Only page0
        change_set_v1.assets_to_process = []
        change_detector_v1.detect_changes.return_value = change_set_v1
        
        engine = IncrementalFilterEngine(
            cache=mock_cache,
            output_dir=tmp_output_dir,
            change_detector=change_detector_v1,
        )
        
        decision1 = engine.decide(
            pages=mock_pages,
            assets=[],
            incremental=True,
        )
        
        assert len(decision1.pages_to_build) == 1
        
        # Simulate cache reinit: create new detector that says ALL pages changed
        change_detector_v2 = Mock()
        change_set_v2 = Mock()
        change_set_v2.pages_to_build = mock_pages  # All pages
        change_set_v2.assets_to_process = []
        change_detector_v2.detect_changes.return_value = change_set_v2
        
        # Create new engine with new detector (simulates orchestrator reset)
        engine2 = IncrementalFilterEngine(
            cache=mock_cache,
            output_dir=tmp_output_dir,
            change_detector=change_detector_v2,
        )
        
        decision2 = engine2.decide(
            pages=mock_pages,
            assets=[],
            incremental=True,
        )
        
        # Key assertion: new engine should use new detector's results
        assert len(decision2.pages_to_build) == len(mock_pages), (
            "Bug B2 regression: Engine should use the provided change detector, not a stale one"
        )


# =============================================================================
# Integration Tests (with mock ChangeDetector)
# =============================================================================


class TestChangeDetectorIntegration:
    """Tests for integration with ChangeDetector."""

    def test_uses_change_detector_when_provided(
        self,
        mock_cache: Mock,
        tmp_output_dir: Path,
        mock_pages: list[Page],
        mock_assets: list[Asset],
    ) -> None:
        """Test that engine delegates to ChangeDetector when provided."""
        change_detector = Mock()
        change_set = Mock()
        change_set.pages_to_build = mock_pages[:2]
        change_set.assets_to_process = []
        change_detector.detect_changes.return_value = change_set
        
        engine = IncrementalFilterEngine(
            cache=mock_cache,
            output_dir=tmp_output_dir,
            change_detector=change_detector,
        )
        
        decision = engine.decide(
            pages=mock_pages,
            assets=mock_assets,
            incremental=True,
        )
        
        # Verify ChangeDetector was called with correct phase
        change_detector.detect_changes.assert_called_once()
        call_kwargs = change_detector.detect_changes.call_args[1]
        assert call_kwargs.get("phase") == "early"
        
        # Verify results
        assert len(decision.pages_to_build) == 2

    def test_falls_back_to_cache_when_no_detector(
        self,
        mock_cache: Mock,
        tmp_output_dir: Path,
        mock_pages: list[Page],
        mock_assets: list[Asset],
    ) -> None:
        """Test fallback to cache.is_changed() when no ChangeDetector."""
        def is_changed(path: Path) -> bool:
            return "page0" in str(path)
        mock_cache.is_changed.side_effect = is_changed
        
        engine = IncrementalFilterEngine(
            cache=mock_cache,
            output_dir=tmp_output_dir,
            change_detector=None,  # No detector
        )
        
        decision = engine.decide(
            pages=mock_pages,
            assets=mock_assets,
            incremental=True,
        )
        
        # Should have called cache.is_changed for each page/asset
        assert mock_cache.is_changed.call_count > 0
        assert len(decision.pages_to_build) == 1


# =============================================================================
# Decision Log Completeness Tests
# =============================================================================


class TestDecisionLogCompleteness:
    """Tests to verify decision log captures all decision points."""

    def test_log_captures_all_checks_incremental(
        self,
        engine_with_output: IncrementalFilterEngine,
        mock_pages: list[Page],
        mock_assets: list[Asset],
    ) -> None:
        """Test that decision log captures all checks for incremental build."""
        decision = engine_with_output.decide(
            pages=mock_pages,
            assets=mock_assets,
            incremental=True,
        )
        
        log = decision.decision_log
        
        # Verify all key fields are populated
        assert log.incremental_enabled is True
        assert log.output_present is True
        assert log.pages_with_changes == 0
        assert log.assets_with_changes == 0
        assert log.fingerprint_cascade_triggered is False
        assert log.decision_type == FilterDecisionType.SKIP

    def test_log_captures_full_rebuild_details(
        self,
        engine_empty_output: IncrementalFilterEngine,
        mock_pages: list[Page],
        mock_assets: list[Asset],
    ) -> None:
        """Test that decision log captures full rebuild trigger details."""
        decision = engine_empty_output.decide(
            pages=mock_pages,
            assets=mock_assets,
            incremental=True,
        )
        
        log = decision.decision_log
        
        assert log.decision_type == FilterDecisionType.FULL
        assert log.full_rebuild_trigger == FullRebuildTrigger.OUTPUT_DIR_EMPTY
        assert log.output_present is False
        assert log.output_presence_reason == "output_dir_empty"
