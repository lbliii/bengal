# Plan: Parallelize Asset Tracking Phase

**RFC**: [rfc-parallelize-asset-tracking.md](rfc-parallelize-asset-tracking.md)
**Status**: Ready
**Estimated Effort**: 30 minutes
**Confidence**: 95% 🟢

---

## Summary

Parallelize the "Track Assets" build phase (Phase 16) to reduce tracking time by 3-4x on multi-core systems. Uses the same `ThreadPoolExecutor` pattern as the rendering phase.

---

## Tasks

### Phase 1: Core Implementation

#### Task 1.1: Add parallel asset extraction to `phase_track_assets`

**File**: `bengal/orchestration/build/rendering.py`

**Changes**:
1. Add `ThreadPoolExecutor` import
2. Define `PARALLEL_THRESHOLD = 5` constant
3. Extract `_extract_page_assets()` helper function
4. Add conditional parallel/sequential execution

**Implementation**:
```python
def phase_track_assets(
    orchestrator: BuildOrchestrator, pages_to_build: list[Any], cli: CLIOutput | None = None
) -> None:
    """
    Phase 16: Track Asset Dependencies (Parallel).

    Extracts and caches which assets each rendered page references.
    Used for incremental builds to invalidate pages when assets change.

    Performance:
        Uses parallel extraction for sites with >5 pages. On 8-core systems,
        this provides ~3-4x speedup for large sites (100+ pages).

    Args:
        orchestrator: Build orchestrator instance
        pages_to_build: List of rendered pages
        cli: Optional CLI output handler
    """
    from concurrent.futures import ThreadPoolExecutor, as_completed

    PARALLEL_THRESHOLD = 5

    def extract_page_assets(page):
        """Extract assets from a single page (thread-safe)."""
        if not page.rendered_html:
            return None
        assets = extract_assets_from_html(page.rendered_html)
        return (page.source_path, assets) if assets else None

    with orchestrator.logger.phase("track_assets", enabled=True):
        # ... existing setup code ...

        if len(pages_to_build) < PARALLEL_THRESHOLD:
            # Sequential for small workloads (avoid thread overhead)
            for page in pages_to_build:
                result = extract_page_assets(page)
                if result:
                    asset_map.track_page_assets(*result)
        else:
            # Parallel extraction
            max_workers = getattr(orchestrator, 'max_workers', None)
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                futures = [executor.submit(extract_page_assets, p) for p in pages_to_build]
                for future in as_completed(futures):
                    result = future.result()
                    if result:
                        source_path, assets = result
                        asset_map.track_page_assets(source_path, assets)
```

**Pre-drafted commit**:
```bash
git add -A && git commit -m "orchestration: parallelize phase_track_assets for 3-4x speedup on multi-core systems"
```

---

### Phase 2: Tests

#### Task 2.1: Add unit tests for parallel asset tracking

**File**: `tests/unit/orchestration/build/test_rendering.py`

**Tests to add**:

1. **`test_phase_track_assets_parallel_produces_same_results`**
   - Create mock pages with rendered HTML containing assets
   - Verify parallel extraction produces identical asset map as sequential

2. **`test_phase_track_assets_below_threshold_runs_sequential`**
   - Create 3 pages (below PARALLEL_THRESHOLD)
   - Verify ThreadPoolExecutor is not used

3. **`test_phase_track_assets_above_threshold_runs_parallel`**
   - Create 10 pages (above PARALLEL_THRESHOLD)
   - Verify ThreadPoolExecutor is used

4. **`test_phase_track_assets_handles_empty_html`**
   - Pages with `rendered_html = None` should be skipped gracefully

5. **`test_phase_track_assets_handles_no_assets`**
   - Pages with no asset references should not error

**Implementation sketch**:
```python
class TestPhaseTrackAssetsParallel:
    """Tests for parallel asset tracking."""

    def test_parallel_produces_same_results(self, tmp_path):
        """Parallel extraction produces identical results to sequential."""
        orchestrator = MockPhaseContext.create_orchestrator(tmp_path)

        # Create mock pages with assets
        pages = []
        for i in range(10):
            page = MagicMock()
            page.source_path = Path(f"page{i}.md")
            page.rendered_html = f'<img src="/assets/img{i}.png">'
            pages.append(page)

        # Mock the AssetDependencyMap
        with patch('bengal.orchestration.build.rendering.AssetDependencyMap') as mock_map:
            mock_instance = MagicMock()
            mock_map.return_value = mock_instance

            phase_track_assets(orchestrator, pages)

            # Verify all 10 pages were tracked
            assert mock_instance.track_page_assets.call_count == 10
            mock_instance.save_to_disk.assert_called_once()

    def test_below_threshold_runs_sequential(self, tmp_path):
        """Small workloads run sequentially."""
        orchestrator = MockPhaseContext.create_orchestrator(tmp_path)

        pages = [MagicMock(rendered_html='<img src="/a.png">', source_path=Path("p.md"))]

        with patch('bengal.orchestration.build.rendering.ThreadPoolExecutor') as mock_executor:
            with patch('bengal.orchestration.build.rendering.AssetDependencyMap'):
                phase_track_assets(orchestrator, pages)

                # ThreadPoolExecutor should NOT be called for <5 pages
                mock_executor.assert_not_called()

    def test_above_threshold_runs_parallel(self, tmp_path):
        """Large workloads run in parallel."""
        orchestrator = MockPhaseContext.create_orchestrator(tmp_path)

        pages = [
            MagicMock(rendered_html=f'<img src="/{i}.png">', source_path=Path(f"{i}.md"))
            for i in range(10)
        ]

        with patch('bengal.orchestration.build.rendering.AssetDependencyMap'):
            with patch('bengal.orchestration.build.rendering.ThreadPoolExecutor') as mock_executor:
                mock_executor.return_value.__enter__ = MagicMock(return_value=MagicMock())
                mock_executor.return_value.__exit__ = MagicMock(return_value=False)

                phase_track_assets(orchestrator, pages)

                # ThreadPoolExecutor SHOULD be called for >=5 pages
                mock_executor.assert_called_once()

    def test_handles_empty_rendered_html(self, tmp_path):
        """Pages with no rendered HTML are skipped."""
        orchestrator = MockPhaseContext.create_orchestrator(tmp_path)

        pages = [MagicMock(rendered_html=None, source_path=Path("p.md"))]

        with patch('bengal.orchestration.build.rendering.AssetDependencyMap') as mock_map:
            mock_instance = MagicMock()
            mock_map.return_value = mock_instance

            phase_track_assets(orchestrator, pages)

            # No assets tracked for empty HTML
            mock_instance.track_page_assets.assert_not_called()

    def test_handles_no_assets_in_html(self, tmp_path):
        """Pages with no assets are handled gracefully."""
        orchestrator = MockPhaseContext.create_orchestrator(tmp_path)

        pages = [MagicMock(rendered_html='<p>No assets here</p>', source_path=Path("p.md"))]

        with patch('bengal.orchestration.build.rendering.AssetDependencyMap') as mock_map:
            mock_instance = MagicMock()
            mock_map.return_value = mock_instance

            phase_track_assets(orchestrator, pages)

            # No assets tracked when HTML has no asset references
            mock_instance.track_page_assets.assert_not_called()
```

**Pre-drafted commit**:
```bash
git add -A && git commit -m "tests: add unit tests for parallel asset tracking in phase_track_assets"
```

---

### Phase 3: Verification

#### Task 3.1: Run tests and lint

**Commands**:
```bash
# Run specific tests
pytest tests/unit/orchestration/build/test_rendering.py -v

# Run full test suite
pytest tests/unit/ -n auto

# Lint
ruff check bengal/orchestration/build/rendering.py
ruff format bengal/orchestration/build/rendering.py
```

#### Task 3.2: Manual performance verification (optional)

**Command**:
```bash
# Build a medium-sized site and observe timing
cd site && bengal site build --verbose
```

**Expected**: "Track assets" phase timing should be 3-4x faster on sites with 50+ pages.

---

## Checklist

- [ ] Task 1.1: Implement parallel asset extraction
- [ ] Task 2.1: Add unit tests
- [ ] Task 3.1: Tests pass, lint clean
- [ ] Task 3.2: Manual verification (optional)

---

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Race condition in dict writes | Python dict simple assignment is atomic; `track_page_assets` uses simple assignment |
| Thread overhead on small sites | `PARALLEL_THRESHOLD = 5` gates usage |
| Exception in thread lost | `future.result()` surfaces exceptions |

---

## Architecture Impact

| Subsystem | Impact |
|-----------|--------|
| Orchestration | Modified: `build/rendering.py` - `phase_track_assets` |
| Cache | None - `AssetDependencyMap` already thread-safe |
| Rendering | None - `extract_assets_from_html` is stateless |
| Core | None |

---

## Post-Implementation

After completing all tasks:

1. Delete this plan file
2. Delete the RFC file
3. Add changelog entry:

```markdown
### Performance

- **Parallel asset tracking**: 3-4x speedup for "Track Assets" phase on multi-core systems
```
