"""
Regression tests for the unified RebuildReason / RebuildReasonCode vocabulary (#445).

Two diverged definitions used to exist:
- bengal/build/contracts/results.py  (auto()-int codes, RebuildReason.trigger:str)
- bengal/orchestration/build/results.py  (string codes, RebuildReason.details:dict)

These tests pin the contract that there is now exactly ONE definition: the
contracts copy is canonical (string values + details:dict + trigger compat),
and the orchestration module re-exports it. Importing either path must yield
the identical object.
"""

from __future__ import annotations

import bengal.build.contracts.results as contracts_results
import bengal.orchestration.build.results as orchestration_results


class TestUnifiedIdentity:
    """The two import paths must resolve to the SAME class object."""

    def test_rebuild_reason_code_is_same_object(self) -> None:
        assert orchestration_results.RebuildReasonCode is contracts_results.RebuildReasonCode

    def test_rebuild_reason_is_same_object(self) -> None:
        assert orchestration_results.RebuildReason is contracts_results.RebuildReason

    def test_change_detection_result_full_rebuild_uses_reason(self) -> None:
        """full_rebuild(reason=...) must populate, not discard, its reason."""
        result = contracts_results.ChangeDetectionResult.full_rebuild(reason="config edit")
        assert result.force_full_rebuild is True
        # The reason must surface somewhere observable, not be silently dropped.
        assert any(
            "config edit" in str(r) or r.trigger == "config edit"
            for r in result.rebuild_reasons.values()
        ), "full_rebuild(reason=...) discarded its reason"


class TestUnionMembers:
    """The canonical enum must carry the UNION of both legacy vocabularies."""

    def test_string_valued_codes(self) -> None:
        """Codes must serialize as strings (observability/JSON), not auto() ints."""
        code = contracts_results.RebuildReasonCode
        assert code.CONTENT_CHANGED.value == "content_changed"
        assert code.TEMPLATE_CHANGED.value == "template_changed"
        assert code.DATA_FILE_CHANGED.value == "data_file_changed"
        assert code.TAXONOMY_CASCADE.value == "taxonomy_cascade"
        assert code.ASSET_FINGERPRINT_CHANGED.value == "asset_fingerprint_changed"
        assert code.CROSS_VERSION_DEPENDENCY.value == "cross_version_dependency"
        assert code.ADJACENT_NAV_CHANGED.value == "adjacent_nav_changed"
        assert code.FORCED.value == "forced"
        assert code.FULL_REBUILD.value == "full_rebuild"
        assert code.OUTPUT_MISSING.value == "output_missing"

    def test_orchestration_only_members_present(self) -> None:
        code = contracts_results.RebuildReasonCode
        assert code.CASCADE_DEPENDENCY.value == "cascade_dependency"
        assert code.NAV_CHANGED.value == "nav_changed"

    def test_contracts_only_members_present(self) -> None:
        code = contracts_results.RebuildReasonCode
        assert code.CONFIG_CHANGED.value == "config_changed"
        # CASCADE is the contracts-side spelling for the orchestration
        # CASCADE_DEPENDENCY concept: they must alias to one another.
        assert code.CASCADE is code.CASCADE_DEPENDENCY


class TestRebuildReasonCompat:
    """RebuildReason carries details (primary) + trigger (backward-compat)."""

    def test_details_default_empty(self) -> None:
        reason = contracts_results.RebuildReason(
            code=contracts_results.RebuildReasonCode.CONTENT_CHANGED
        )
        assert reason.details == {}

    def test_trigger_backward_compat(self) -> None:
        reason = contracts_results.RebuildReason(
            code=contracts_results.RebuildReasonCode.DATA_FILE_CHANGED,
            trigger="data/team.yaml",
        )
        assert reason.trigger == "data/team.yaml"

    def test_str_uses_code_value_for_observability(self) -> None:
        reason = contracts_results.RebuildReason(
            code=contracts_results.RebuildReasonCode.CONTENT_CHANGED
        )
        assert str(reason) == "content_changed"


class TestFilterEmitsCanonicalCodes:
    """provenance_filter must construct reasons from the canonical enum."""

    def test_filter_imports_canonical_code(self) -> None:
        from bengal.orchestration.build import provenance_filter

        assert provenance_filter.RebuildReasonCode is contracts_results.RebuildReasonCode

    def test_add_rebuild_reason_records_canonical_code(self) -> None:
        decision = orchestration_results.IncrementalDecision(
            pages_to_build=[],
            pages_skipped_count=0,
        )
        decision.add_rebuild_reason(
            "content/index.md",
            contracts_results.RebuildReasonCode.FULL_REBUILD,
            {"cold_build": True},
        )
        reason = decision.rebuild_reasons["content/index.md"]
        assert reason.code is contracts_results.RebuildReasonCode.FULL_REBUILD
        assert reason.code.value == "full_rebuild"
