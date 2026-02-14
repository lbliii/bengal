# RFC: Pipeline Input/Output Contracts

## Status: Draft
## Created: 2026-02-14
## Related: rfc-incremental-build-contracts, rfc-bengal-v2-architecture

---

## Summary

**Problem**: Bengal's build pipeline has opaque inputs (BuildOptions incomplete, BuildRequest loses fields in subprocess), horizontal coupling (phase functions take full BuildOrchestrator), and output tracking gaps (some writes not recorded for hot reload).

**Solution**: Formalize BuildInput, PhaseInput, and PhaseOutput as contracts. Implement BuildInput consolidation, output tracking audit, Discovery PhaseInput extraction, and reload hint from build.

---

## Contracts

### BuildInput

**Location**: `bengal/orchestration/build/inputs.py`

Single frozen record of all build inputs. BuildRequest is a serialized view for process-isolated builds.

```python
@dataclass(frozen=True)
class BuildInput:
    options: BuildOptions
    site_root: Path
    config_hash: str = ""
    changed_sources: frozenset[Path] = frozenset()
    nav_changed_sources: frozenset[Path] = frozenset()
    structural_changed: bool = False
    event_types: frozenset[str] = frozenset()
```

- `from_options(options, site_root, **overrides) -> BuildInput`
- `from_build_request(request, site_root) -> BuildInput`
- `to_build_request() -> BuildRequest`

### PhaseInput / PhaseOutput

**Location**: `bengal/orchestration/build/results.py`

Phases receive only what they need; return structured output.

#### Discovery Phase (Implemented)

```python
@dataclass
class DiscoveryPhaseInput:
    site: Site
    cache: BuildCache | None
    incremental: bool
    build_context: BuildContext | None

@dataclass
class DiscoveryPhaseOutput:
    pages: list[Page]
    sections: list[Section]
    assets: list[Asset]
```

- `run_discovery_phase(input: DiscoveryPhaseInput) -> DiscoveryPhaseOutput`
- `phase_discovery(orchestrator, ...)` is a thin wrapper that builds input, calls `run_discovery_phase`, applies output to orchestrator.site

#### Future Phases (Migration Path)

- AssetsPhaseInput / AssetsPhaseOutput
- RenderPhaseInput / RenderPhaseOutput
- PostprocessPhaseInput / PostprocessPhaseOutput
- FinalizationPhaseInput / FinalizationPhaseOutput

---

## Output Tracking

Every write to the output directory must be recorded in BuildOutputCollector for reliable hot reload.

| Location | Write Type | Recorded |
|----------|------------|----------|
| rendering/pipeline/output.py | HTML | Yes |
| orchestration/asset.py | Assets | Yes |
| postprocess/sitemap.py | Sitemap XML | Yes |
| postprocess/rss.py | RSS XML | Yes |
| build/initialization.py | fonts.css | Yes |
| postprocess/special_pages.py | 404, search, graph | Yes |
| postprocess/redirects.py | Redirect HTML, _redirects | Yes |
| postprocess/social_cards.py | OG images | Yes |
| postprocess/xref_index.py | xref.json | Yes |

---

## Reload Hint

**Location**: `bengal/orchestration/stats/models.py` (BuildStats), `bengal/server/reload_controller.py`

Build declares reload hint for smarter dev server decisions:

- `"css-only"`: All changed_outputs are CSS; prefer CSS hot reload
- `"full"`: Any HTML changed
- `"none"`: dry_run or no outputs

Computed after phase_postprocess. Passed via BuildResult to ReloadController.decide_from_outputs(). When `reload_hint == "none"`, controller returns action="none".

---

## Migration Path

1. **Discovery phase** — Done. `run_discovery_phase` extracted; `phase_discovery` is thin wrapper.
2. **Remaining phases** — Apply same pattern: define PhaseInput/PhaseOutput, extract `run_*_phase()`, keep `phase_*()` as wrapper.
3. **Detector consolidation** — See rfc-incremental-build-contracts for provenance filter unification.
4. **Composition** — See rfc-bengal-v2-architecture for longer-term coordinator decomposition.

---

## References

- `plan/analysis-pipeline-inputs-and-vertical-stacks.md` — Analysis and input map
- `plan/rfc-incremental-build-contracts.md` — Detector consolidation
- `plan/rfc-bengal-v2-architecture.md` — Composition and coordinator design
