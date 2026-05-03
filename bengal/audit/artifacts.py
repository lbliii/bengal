"""Post-build artifact audit for generated output directories."""

from __future__ import annotations

from dataclasses import dataclass
from html.parser import HTMLParser
from typing import TYPE_CHECKING, Any
from urllib.parse import urlparse

if TYPE_CHECKING:
    from pathlib import Path


@dataclass(frozen=True, slots=True)
class ArtifactFinding:
    """A generated artifact problem found during audit."""

    severity: str
    message: str
    artifact: str
    reference: str
    code: str = "A101"
    recommendation: str = "Regenerate the site or fix the broken generated reference."

    def to_dict(self) -> dict[str, Any]:
        """Serialize finding for Kida/JSON contexts."""
        return {
            "severity": self.severity,
            "code": self.code,
            "message": self.message,
            "artifact": self.artifact,
            "reference": self.reference,
            "recommendation": self.recommendation,
            "details": [f"{self.artifact}: {self.reference}"],
            "metadata": None,
        }


@dataclass(frozen=True, slots=True)
class ArtifactAuditSummary:
    """Counts from an artifact audit run."""

    files_checked: int
    references_checked: int
    broken_references: int

    def to_dict(self) -> dict[str, int]:
        """Serialize summary for Kida/JSON contexts."""
        return {
            "files_checked": self.files_checked,
            "references_checked": self.references_checked,
            "broken_references": self.broken_references,
            "errors": self.broken_references,
            "warnings": 0,
            "passed": 1 if self.broken_references == 0 else 0,
        }


@dataclass(frozen=True, slots=True)
class ArtifactAuditReport:
    """Result of scanning generated artifacts."""

    output_dir: Path
    summary: ArtifactAuditSummary
    findings: tuple[ArtifactFinding, ...]

    @property
    def passed(self) -> bool:
        """Return whether the audit found no broken references."""
        return self.summary.broken_references == 0

    def to_envelope(self, *, command: str = "audit") -> dict[str, Any]:
        """Return a versioned, presentation-neutral audit envelope."""
        status = "passed" if self.passed else "failed"
        return {
            "schema_version": "bengal.audit.v1",
            "command": command,
            "status": status,
            "policy": {"errors_fail": True, "warnings_fail": False},
            "summary": self.summary.to_dict(),
            "findings": [finding.to_dict() for finding in self.findings],
            "metadata": {"output_dir": str(self.output_dir)},
        }

    def format_validation_report(self) -> dict[str, Any]:
        """Return Kida context compatible with ``validation_report.kida``."""
        envelope = self.to_envelope()
        issues = [
            {
                "level": "error",
                "message": finding.message,
                "detail": f"{finding.artifact}: {finding.reference}",
            }
            for finding in self.findings[:10]
        ]
        if len(self.findings) > 10:
            issues.append(
                {
                    "level": "info",
                    "message": f"{len(self.findings) - 10} more broken reference(s)",
                    "detail": "Use --json for the complete audit result.",
                }
            )
        if not issues:
            issues.append(
                {
                    "level": "success",
                    "message": "Artifact audit passed",
                    "detail": f"{self.summary.files_checked} file(s) checked",
                }
            )

        return {
            **envelope,
            "title": "Artifact Audit",
            "issues": issues,
            "summary": {
                "errors": self.summary.broken_references,
                "warnings": 0,
                "passed": 1 if self.passed else 0,
            },
            "report": envelope,
        }


def audit_output_dir(output_dir: Path, *, baseurl: str = "") -> ArtifactAuditReport:
    """Audit generated HTML artifacts for broken internal file references."""
    output_dir = output_dir.resolve()
    html_files = sorted(output_dir.rglob("*.html")) if output_dir.exists() else []
    findings: list[ArtifactFinding] = []
    references_checked = 0
    baseurl_path = urlparse(baseurl).path.rstrip("/") if baseurl else ""

    for html_file in html_files:
        parser = _ReferenceExtractor()
        parser.feed(html_file.read_text(encoding="utf-8", errors="ignore"))
        artifact = _posix_relative(html_file, output_dir)
        for reference in parser.references:
            target = _target_for_reference(
                reference,
                source_file=html_file,
                output_dir=output_dir,
                baseurl_path=baseurl_path,
            )
            if target is None:
                continue
            references_checked += 1
            if not _target_exists(target):
                findings.append(
                    ArtifactFinding(
                        severity="error",
                        message="Generated artifact references a missing file",
                        artifact=artifact,
                        reference=reference,
                    )
                )

    return ArtifactAuditReport(
        output_dir=output_dir,
        summary=ArtifactAuditSummary(
            files_checked=len(html_files),
            references_checked=references_checked,
            broken_references=len(findings),
        ),
        findings=tuple(findings),
    )


class _ReferenceExtractor(HTMLParser):
    """Extract generated href/src references from HTML."""

    def __init__(self) -> None:
        super().__init__()
        self.references: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        for name, value in attrs:
            if name in {"href", "src"} and value:
                self.references.append(value)


def _target_for_reference(
    reference: str,
    *,
    source_file: Path,
    output_dir: Path,
    baseurl_path: str,
) -> Path | None:
    """Map an HTML reference to an expected local artifact path."""
    parsed = urlparse(reference)
    if parsed.scheme or parsed.netloc or reference.startswith(("#", "mailto:", "tel:", "data:")):
        return None

    path = parsed.path
    if not path:
        return None

    if path.startswith("/"):
        if baseurl_path and (path == baseurl_path or path.startswith(baseurl_path + "/")):
            path = path[len(baseurl_path) :] or "/"
        return output_dir / path.lstrip("/")
    return (source_file.parent / path).resolve()


def _target_exists(path: Path) -> bool:
    """Return whether a reference target exists as a file or clean URL artifact."""
    if path.exists():
        return True
    if path.suffix:
        return False
    return (path / "index.html").exists() or path.with_suffix(".html").exists()


def _posix_relative(path: Path, root: Path) -> str:
    """Return a POSIX relative path for stable diagnostics."""
    return path.relative_to(root).as_posix()
