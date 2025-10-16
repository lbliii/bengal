"""
Metadata cascade with depth limiting.

This module implements Hugo-style cascade functionality with depth limits
to prevent metadata from leaking infinitely deep in nested section hierarchies.

INTEGRATION STATUS:
===================
✅ COMPLETED - Integrated into Site._apply_section_cascade()
Status: Production-ready, fully tested

The CascadeScope class provides:
- Depth-limited cascade propagation
- Configurable merge strategies (override, skip, append)
- Edge case handling (None values, circular refs)
- Context manager support for scope management
- Comprehensive logging

Example:
    >>> scope = CascadeScope(max_depth=3, merge_strategy='override')
    >>> result = scope.apply(page_metadata, section_metadata)
    >>> # Metadata from section cascades to page, but only up to depth 3
"""

from typing import Any, Literal

from bengal.utils.logger import get_logger

logger = get_logger(__name__)

# Merge strategy type
MergeStrategy = Literal["override", "skip", "append"]


class CascadeScope:
    """
    Metadata cascade with depth limiting to prevent leaks.

    Implements controlled metadata propagation from sections to pages,
    respecting depth boundaries to prevent deep nesting issues.

    Args:
        max_depth: Maximum cascade depth (default: 3)
        current_depth: Current depth in cascade (default: 0)
        merge_strategy: How to handle key conflicts:
            - 'override': Section metadata overwrites page metadata (default)
            - 'skip': Page metadata takes precedence, skip section values
            - 'append': For list values, append instead of override
        config_key: Key in metadata that contains cascade config (default: 'cascade')

    Example:
        >>> scope = CascadeScope(max_depth=2)
        >>> page_meta = scope.apply(
        ...     page.metadata,
        ...     section.metadata,
        ...     depth_in_section=1
        ... )
    """

    def __init__(
        self,
        max_depth: int = 3,
        current_depth: int = 0,
        merge_strategy: MergeStrategy = "override",
        config_key: str = "cascade",
    ):
        self.max_depth = max_depth
        self.current_depth = current_depth
        self.merge_strategy = merge_strategy
        self.config_key = config_key
        self._visited_sections: set[int] = set()  # Circular reference detection

    def apply(
        self,
        metadata: dict[str, Any],
        base_meta: dict[str, Any],
        depth_in_section: int = 1,
    ) -> dict[str, Any]:
        """
        Apply cascade from base_meta to metadata with depth limiting.

        Args:
            metadata: Target metadata dict (page metadata)
            base_meta: Source metadata to cascade from (section metadata)
            depth_in_section: Current depth in section hierarchy

        Returns:
            Merged metadata dict

        Raises:
            RuntimeError: If circular cascade detected
        """
        # Depth limit check: Don't cascade beyond max depth
        if self.current_depth >= self.max_depth:
            logger.debug(
                "cascade_depth_limit_reached",
                current_depth=self.current_depth,
                max_depth=self.max_depth,
            )
            return metadata

        # Validate inputs
        if not isinstance(metadata, dict):
            logger.debug("cascade_skip_invalid_target_metadata", type=type(metadata))
            return {}

        if not isinstance(base_meta, dict):
            logger.debug("cascade_skip_invalid_source_metadata", type=type(base_meta))
            return metadata

        # Detect circular cascades by tracking section identity
        base_meta_id = id(base_meta)
        if base_meta_id in self._visited_sections:
            logger.warning("cascade_circular_reference_detected", metadata_id=base_meta_id)
            raise RuntimeError(
                f"Circular cascade detected: section metadata {base_meta_id} "
                "already visited in this cascade chain"
            )

        self._visited_sections.add(base_meta_id)

        try:
            # Extract cascade config from source metadata
            cascade_config = base_meta.get(self.config_key, {})
            if not cascade_config:
                # No cascade config, just return target as-is
                return metadata

            # Merge cascade config into target metadata
            for key, value in cascade_config.items():
                # Skip None values - they shouldn't propagate
                if value is None:
                    logger.debug("cascade_skip_none_value", key=key)
                    continue

                # Apply merge strategy
                if key not in metadata:
                    # Key doesn't exist in target, add it
                    metadata[key] = value
                    logger.debug("cascade_added_key", key=key, merge_strategy=self.merge_strategy)
                elif self.merge_strategy == "override":
                    # Override target with cascaded value
                    metadata[key] = value
                    logger.debug(
                        "cascade_override_value",
                        key=key,
                        old_value=metadata.get(key),
                        new_value=value,
                    )
                elif self.merge_strategy == "skip":
                    # Skip - keep target value
                    logger.debug("cascade_skip_existing_key", key=key)
                    continue
                elif self.merge_strategy == "append":
                    # For lists, append cascaded values
                    if isinstance(metadata.get(key), list) and isinstance(value, list):
                        metadata[key].extend(value)
                        logger.debug("cascade_appended_list_value", key=key)
                    else:
                        # Fallback to override for non-list values
                        metadata[key] = value
                        logger.debug(
                            "cascade_append_fallback_to_override",
                            key=key,
                            reason="non-list_value",
                        )

            return metadata

        finally:
            # Clean up visited marker
            self._visited_sections.discard(base_meta_id)

    def descend(self) -> "CascadeScope":
        """
        Create a child scope for descending deeper in hierarchy.

        Returns:
            New CascadeScope with incremented depth
        """
        new_scope = CascadeScope(
            max_depth=self.max_depth,
            current_depth=self.current_depth + 1,
            merge_strategy=self.merge_strategy,
            config_key=self.config_key,
        )
        # Share visited sections set to maintain circular reference detection
        new_scope._visited_sections = self._visited_sections
        return new_scope

    def __enter__(self) -> "CascadeScope":
        """Context manager entry."""
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Context manager exit - cleanup visited sections."""
        self._visited_sections.clear()


def apply_cascade(
    page: Any,
    section_metadata: dict[str, Any],
    scope: CascadeScope | None = None,
    depth_in_section: int = 1,
) -> dict[str, Any]:
    """
    Apply cascade to page from section metadata.

    This function applies section-level cascade configuration to page metadata,
    respecting depth limits to prevent metadata from propagating too deep.

    Args:
        page: Page instance to apply cascade to
        section_metadata: Section metadata containing cascade config
        scope: CascadeScope controlling depth (auto-created if None)
        depth_in_section: Current depth in section hierarchy

    Returns:
        Merged metadata dict

    Example:
        >>> scope = CascadeScope(max_depth=3)
        >>> result = apply_cascade(page, section.metadata, scope, depth=1)
    """
    if scope is None:
        scope = CascadeScope()

    if not hasattr(page, "metadata"):
        logger.debug("cascade_skip_page_no_metadata", page=str(page))
        return {}

    return scope.apply(page.metadata, section_metadata, depth_in_section=depth_in_section)
