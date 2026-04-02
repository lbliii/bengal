"""
Content file parsing for content discovery.

This module handles parsing content files including frontmatter extraction,
YAML error recovery, and collection schema validation. Extracted from
content_discovery.py per RFC: rfc-modularize-large-files.

Classes:
ContentParser: Parses content files with frontmatter.

"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import patitas

from bengal.utils.observability.logger import get_logger

if TYPE_CHECKING:
    from pathlib import Path

    from bengal.collections import CollectionConfig
    from bengal.orchestration.build_context import BuildContext

logger = get_logger(__name__)


class ContentParser:
    """
    Parses content files with frontmatter and optional validation.

    Handles:
    - Valid frontmatter
    - Invalid YAML in frontmatter (graceful degradation)
    - Missing frontmatter
    - File encoding issues
    - Collection schema validation (when collections defined)

    Attributes:
        content_dir: Root content directory
        collections: Optional dict of collection configs for validation
        strict_validation: Whether to raise on validation failure
        build_context: Optional BuildContext for content caching

    Example:
            >>> parser = ContentParser(Path("content"), collections=collections)
            >>> content, metadata = parser.parse_file(Path("content/post.md"))

    """

    def __init__(
        self,
        content_dir: Path,
        collections: dict[str, CollectionConfig[Any]] | None = None,
        strict_validation: bool = True,
        build_context: BuildContext | None = None,
    ):
        """
        Initialize the content parser.

        Args:
            content_dir: Root content directory
            collections: Optional dict of collection configs for schema validation
            strict_validation: If True, raise errors on validation failure
            build_context: Optional BuildContext for caching content
        """
        self.content_dir = content_dir
        self._collections = collections or {}
        self._strict_validation = strict_validation
        self._build_context = build_context
        self._validation_errors: list[tuple[Path, str, list[Any]]] = []

    @property
    def validation_errors(self) -> list[tuple[Path, str, list[Any]]]:
        """Get validation errors accumulated during parsing."""
        return self._validation_errors

    def parse_file(self, file_path: Path) -> tuple[str, dict[str, Any]]:
        """
        Parse a content file with robust error handling.

        Caches raw content in BuildContext for later use by validators,
        eliminating redundant disk I/O during health checks.

        Args:
            file_path: Path to content file

        Returns:
            Tuple of (content, metadata)

        Raises:
            IOError: If file cannot be read
        """
        # Notebook files use a different parser
        if file_path.suffix.lower() == ".ipynb":
            return self._parse_notebook(file_path)

        # Read file once using file_io utility for robust encoding handling
        from bengal.utils.io.file_io import read_text_file

        file_content = read_text_file(
            file_path, fallback_encoding="latin-1", on_error="raise", caller="content_discovery"
        )

        # Cache raw content for validators (build-integrated validation)
        if self._build_context is not None and file_content is not None:
            self._build_context.cache_content(file_path, file_content)

        # Parse frontmatter (patitas handles YAML errors gracefully)
        metadata, content = patitas.parse_frontmatter(file_content)
        return content, metadata

    def _parse_notebook(self, file_path: Path) -> tuple[str, dict[str, Any]]:
        """Parse a Jupyter notebook (.ipynb) file."""
        from bengal.utils.io.file_io import read_text_file

        file_content = read_text_file(
            file_path, fallback_encoding="utf-8", on_error="raise", caller="content_discovery"
        )

        if self._build_context is not None and file_content is not None:
            self._build_context.cache_content(file_path, file_content)

        parse_notebook = getattr(patitas, "parse_notebook", None)
        if parse_notebook is None:
            content, metadata = self._parse_notebook_with_stdlib(file_content, file_path)
        else:
            content, metadata = parse_notebook(file_content, file_path)

        if "type" not in metadata:
            metadata["type"] = "notebook"

        return content, metadata

    def _parse_notebook_with_stdlib(
        self, file_content: str, source_path: Path
    ) -> tuple[str, dict[str, Any]]:
        """Parse .ipynb without patitas notebook API (compatibility fallback)."""
        import json

        payload = json.loads(file_content)
        raw_cells = payload.get("cells", [])

        blocks: list[str] = []
        for cell in raw_cells:
            if not isinstance(cell, dict):
                continue

            source = cell.get("source", "")
            if isinstance(source, list):
                text = "".join(str(part) for part in source)
            else:
                text = str(source)

            text = text.strip()
            if not text:
                continue

            cell_type = str(cell.get("cell_type", "")).lower()
            if cell_type == "code":
                blocks.append(f"```python\n{text}\n```")
            else:
                blocks.append(text)

        content = "\n\n".join(blocks)
        metadata = {"notebook": source_path.stem}
        return content, metadata

    def validate_against_collection(
        self, file_path: Path, metadata: dict[str, Any]
    ) -> dict[str, Any]:
        """
        Validate frontmatter against collection schema if applicable.

        Args:
            file_path: Path to content file
            metadata: Parsed frontmatter metadata

        Returns:
            Validated metadata (possibly with schema-enforced defaults)

        Raises:
            ContentValidationError: If strict_validation=True and validation fails
        """
        if not self._collections:
            return metadata

        collection_name, config = self._get_collection_for_file(file_path)

        if config is None:
            return metadata

        from bengal.collections import ContentValidationError, SchemaValidator

        # Validate
        validator = SchemaValidator(config.schema, strict=config.strict)
        result = validator.validate(metadata, source_file=file_path)

        if not result.valid:
            from bengal.errors import ErrorCode, record_error

            error_summary = result.error_summary
            self._validation_errors.append((file_path, collection_name or "", result.errors))

            error = ContentValidationError(
                message=f"Validation failed for {file_path}",
                path=file_path,
                errors=result.errors,
                collection_name=collection_name,
                code=ErrorCode.N011,
            )

            # Record for session aggregation
            record_error(error, file_path=str(file_path))

            if self._strict_validation:
                raise error
            logger.warning(
                "collection_validation_failed",
                path=str(file_path),
                collection=collection_name,
                errors=error_summary,
                action="continuing_with_original_metadata",
                code="N011",
            )
            return metadata

        # Return validated data as dict (from schema instance)
        if result.data is not None:
            from bengal.utils.serialization import to_jsonable

            if not isinstance(result.data, type):
                return dict(to_jsonable(result.data))
            if hasattr(result.data, "model_dump"):
                return dict(result.data.model_dump())

        return metadata

    def _get_collection_for_file(
        self, file_path: Path
    ) -> tuple[str | None, CollectionConfig[Any] | None]:
        """
        Find which collection a file belongs to based on its path.

        Args:
            file_path: Path to content file

        Returns:
            Tuple of (collection_name, CollectionConfig) or (None, None)
        """
        try:
            rel_path = file_path.relative_to(self.content_dir)
        except ValueError:
            return None, None

        for name, config in self._collections.items():
            try:
                if config.directory is not None:
                    rel_path.relative_to(config.directory)
                    return name, config
            except ValueError:
                continue

        return None, None
