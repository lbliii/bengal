"""
Content file parsing for content discovery.

This module handles parsing content files including frontmatter extraction,
YAML error recovery, and collection schema validation. Extracted from
content_discovery.py per RFC: rfc-modularize-large-files.

Classes:
ContentParser: Parses content files with frontmatter.

"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any

import frontmatter

from bengal.content.utils.frontmatter import extract_content_skip_frontmatter
from bengal.utils.observability.logger import get_logger

if TYPE_CHECKING:
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
        import yaml

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

        # Parse frontmatter
        try:
            post = frontmatter.loads(file_content)
            content = post.content
            metadata = dict(post.metadata)
            return content, metadata

        except yaml.YAMLError as e:
            return self._handle_yaml_error(file_path, file_content or "", e)

        except Exception as e:
            return self._handle_parse_error(file_path, file_content or "", e)

    def _parse_notebook(self, file_path: Path) -> tuple[str, dict[str, Any]]:
        """Parse a Jupyter notebook (.ipynb) file."""
        from bengal.content.notebook.converter import NotebookConverter
        from bengal.utils.io.file_io import read_text_file

        file_content = read_text_file(
            file_path, fallback_encoding="utf-8", on_error="raise", caller="content_discovery"
        )

        if self._build_context is not None and file_content is not None:
            self._build_context.cache_content(file_path, file_content)

        content, metadata = NotebookConverter.convert(file_path, file_content)

        if "type" not in metadata:
            metadata["type"] = "notebook"

        return content, metadata

    def _handle_yaml_error(
        self, file_path: Path, file_content: str, error: Exception
    ) -> tuple[str, dict[str, Any]]:
        """Handle YAML syntax error in frontmatter."""
        from bengal.errors import BengalDiscoveryError, ErrorContext, enrich_error

        context = ErrorContext(
            file_path=file_path,
            operation="parsing frontmatter",
            suggestion="Fix frontmatter YAML syntax",
            original_error=error,
        )
        enrich_error(error, context, BengalDiscoveryError)

        logger.debug(
            "frontmatter_parse_failed",
            file_path=str(file_path),
            error=str(error),
            error_type="yaml_syntax",
            action="processing_without_metadata",
            suggestion="Fix frontmatter YAML syntax",
        )

        content = extract_content_skip_frontmatter(file_content)

        from bengal.utils.primitives.text import humanize_slug

        metadata = {
            "_parse_error": str(error),
            "_parse_error_type": "yaml",
            "_source_file": str(file_path),
            "title": humanize_slug(file_path.stem),
        }

        return content, metadata

    def _handle_parse_error(
        self, file_path: Path, file_content: str, error: Exception
    ) -> tuple[str, dict[str, Any]]:
        """Handle unexpected parse error."""
        from bengal.errors import BengalDiscoveryError, ErrorContext, enrich_error

        context = ErrorContext(
            file_path=file_path,
            operation="parsing content file",
            suggestion="Check file encoding and format",
            original_error=error,
        )
        enriched_error = enrich_error(error, context, BengalDiscoveryError)

        if self._build_context and hasattr(self._build_context, "build_stats"):
            build_stats = self._build_context.build_stats
            if build_stats:
                build_stats.add_error(enriched_error, category="discovery")

        logger.warning(
            "content_parse_unexpected_error",
            file_path=str(file_path),
            error=str(error),
            error_type=type(error).__name__,
            action="using_full_file_as_content",
        )

        from bengal.utils.primitives.text import humanize_slug

        metadata = {
            "_parse_error": str(error),
            "_parse_error_type": "unknown",
            "_source_file": str(file_path),
            "title": humanize_slug(file_path.stem),
        }

        return file_content, metadata

    def _extract_content_skip_frontmatter(self, file_content: str) -> str:
        """
        Extract content, skipping broken frontmatter section.

        .. deprecated::
            Use ``bengal.content.utils.frontmatter.extract_content_skip_frontmatter``
            directly for new code.

        Args:
            file_content: Full file content

        Returns:
            Content without frontmatter section
        """
        return extract_content_skip_frontmatter(file_content)

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
            else:
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
            elif hasattr(result.data, "model_dump"):
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
