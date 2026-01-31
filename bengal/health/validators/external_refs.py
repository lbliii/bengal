"""
External reference validator.

Reports unresolved [[ext:project:target]] references captured during rendering.
Uses resolver.unresolved populated by CrossReferencePlugin/ExternalRefResolver.
"""

from __future__ import annotations

from typing import Any

from bengal.health.base import BaseValidator
from bengal.health.report import CheckResult, CheckStatus


class ExternalRefValidator(BaseValidator):
    """
    Validate external references resolved during rendering.

    Emits warnings for unresolved [[ext:project:target]] so builds can surface
    missing templates or indexes without failing.

    """

    name = "external_references"
    description = "Reports unresolved external references"
    enabled_by_default = True

    def validate(self, site: Any, build_context: Any | None = None) -> list[CheckResult]:
        results: list[CheckResult] = []

        external_refs_config = getattr(site, "config", {}).get("external_refs", {})
        if isinstance(external_refs_config, bool) and not external_refs_config:
            return results
        if isinstance(external_refs_config, dict) and not external_refs_config.get("enabled", True):
            return results

        resolver = getattr(site, "external_ref_resolver", None)
        unresolved = getattr(resolver, "unresolved", []) if resolver else []

        for ref in unresolved:
            details = []
            if getattr(ref, "source_file", None):
                detail = str(ref.source_file)
                if getattr(ref, "line", None):
                    detail = f"{detail}:{ref.line}"
                details.append(detail)

            results.append(
                CheckResult(
                    status=CheckStatus.WARNING,
                    message=f"Unresolved external reference: [[ext:{ref.project}:{ref.target}]]",
                    code="H710",
                    recommendation="Add template or index entry in external_refs config",
                    details=details or None,
                    validator=self.name,
                    metadata={
                        "project": ref.project,
                        "target": ref.target,
                    },
                )
            )

        return results
