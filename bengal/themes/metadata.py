"""Internal theme metadata parsing and validation."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Literal

if TYPE_CHECKING:
    from pathlib import Path

METADATA_FILENAMES = ("theme.toml", "theme.yaml")

IssueLevel = Literal["error", "warning"]


@dataclass(frozen=True, slots=True)
class ThemeMetadataIssue:
    """A validation issue found while parsing theme metadata."""

    level: IssueLevel
    message: str
    suggestion: str | None = None


@dataclass(frozen=True, slots=True)
class ThemeMetadata:
    """Normalized internal view of a theme metadata file."""

    name: str | None = None
    version: str | None = None
    description: str | None = None
    author: str | None = None
    license: str | None = None
    extends: str | None = None
    parent: str | None = None
    libraries: tuple[str, ...] = ()
    raw: dict[str, Any] = field(default_factory=dict)

    @property
    def parent_slug(self) -> str | None:
        return self.extends or self.parent

    @classmethod
    def from_mapping(cls, data: dict[str, Any]) -> tuple[ThemeMetadata, list[ThemeMetadataIssue]]:
        issues: list[ThemeMetadataIssue] = []

        name = _optional_scalar(data, "name", issues)
        version = _optional_scalar(data, "version", issues)
        description = _optional_scalar(data, "description", issues)
        author = _optional_scalar(data, "author", issues)
        license_name = _optional_scalar(data, "license", issues)
        extends = _optional_scalar(data, "extends", issues)
        parent = _optional_scalar(data, "parent", issues)
        libraries = _optional_string_list(data, "libraries", issues)

        if not name:
            issues.append(
                ThemeMetadataIssue(
                    "warning",
                    "Theme metadata should define a name",
                    'Add `name = "your-theme"` to theme.toml.',
                )
            )

        return (
            cls(
                name=name,
                version=version,
                description=description,
                author=author,
                license=license_name,
                extends=extends,
                parent=parent,
                libraries=libraries,
                raw=data,
            ),
            issues,
        )


@dataclass(frozen=True, slots=True)
class ThemeMetadataResult:
    """Parsed metadata and issues for a theme directory."""

    metadata: ThemeMetadata
    path: Path | None
    issues: list[ThemeMetadataIssue]

    @property
    def errors(self) -> list[ThemeMetadataIssue]:
        return [issue for issue in self.issues if issue.level == "error"]

    @property
    def warnings(self) -> list[ThemeMetadataIssue]:
        return [issue for issue in self.issues if issue.level == "warning"]


def load_theme_metadata(theme_path: Path) -> ThemeMetadataResult:
    """Load and validate theme metadata from a theme directory."""
    manifest = _metadata_path(theme_path)
    if manifest is None:
        return ThemeMetadataResult(
            metadata=ThemeMetadata(),
            path=None,
            issues=[
                ThemeMetadataIssue(
                    "error",
                    "Missing theme.toml or theme.yaml",
                    "Add a theme metadata file at the theme root.",
                )
            ],
        )

    data, issues = _read_metadata_file(manifest)
    if issues:
        return ThemeMetadataResult(metadata=ThemeMetadata(), path=manifest, issues=issues)

    metadata, validation_issues = ThemeMetadata.from_mapping(data)
    return ThemeMetadataResult(metadata=metadata, path=manifest, issues=validation_issues)


def _metadata_path(theme_path: Path) -> Path | None:
    for filename in METADATA_FILENAMES:
        candidate = theme_path / filename
        if candidate.is_file():
            return candidate
    return None


def _read_metadata_file(path: Path) -> tuple[dict[str, Any], list[ThemeMetadataIssue]]:
    if path.name == "theme.toml":
        import tomllib

        try:
            with path.open("rb") as handle:
                data = tomllib.load(handle)
        except (OSError, tomllib.TOMLDecodeError) as exc:
            return {}, [ThemeMetadataIssue("error", f"Invalid theme.toml: {exc}")]
    else:
        try:
            import yaml

            data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        except (OSError, yaml.YAMLError) as exc:
            return {}, [ThemeMetadataIssue("error", f"Invalid theme.yaml: {exc}")]

    if not isinstance(data, dict):
        return {}, [ThemeMetadataIssue("error", "Theme metadata must be a mapping")]
    return data, []


def _optional_scalar(
    data: dict[str, Any],
    field_name: str,
    issues: list[ThemeMetadataIssue],
) -> str | None:
    value = data.get(field_name)
    if value is None:
        return None
    if isinstance(value, str):
        return value
    if isinstance(value, int | float | bool):
        return str(value)
    issues.append(
        ThemeMetadataIssue(
            "error",
            f"Theme metadata field `{field_name}` must be a scalar value",
            f"Set `{field_name}` to a string value.",
        )
    )
    return None


def _optional_string_list(
    data: dict[str, Any],
    field_name: str,
    issues: list[ThemeMetadataIssue],
) -> tuple[str, ...]:
    value = data.get(field_name)
    if value is None:
        return ()
    if isinstance(value, list) and all(isinstance(item, str) for item in value):
        return tuple(value)
    issues.append(
        ThemeMetadataIssue(
            "error",
            f"Theme metadata field `{field_name}` must be a list of strings",
            f'Set `{field_name}` to strings such as `["chirp_ui"]`.',
        )
    )
    return ()
