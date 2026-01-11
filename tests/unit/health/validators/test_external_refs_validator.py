from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from bengal.health.report import CheckStatus
from bengal.health.validators.external_refs import ExternalRefValidator
from bengal.rendering.external_refs.resolver import UnresolvedRef


def test_external_refs_empty_resolves_to_no_results() -> None:
    site = SimpleNamespace(config={"external_refs": {"enabled": True}}, external_ref_resolver=None)
    validator = ExternalRefValidator()

    assert validator.validate(site) == []


def test_external_refs_unresolved_warning() -> None:
    unresolved = [
        UnresolvedRef(project="p", target="Missing", source_file=Path("docs/page.md"), line=10)
    ]
    site = SimpleNamespace(
        config={"external_refs": {"enabled": True}},
        external_ref_resolver=SimpleNamespace(unresolved=unresolved),
    )
    validator = ExternalRefValidator()

    results = validator.validate(site)

    assert len(results) == 1
    assert results[0].status == CheckStatus.WARNING
    assert "ext:p:Missing" in results[0].message
    assert results[0].details == ["docs/page.md:10"]
