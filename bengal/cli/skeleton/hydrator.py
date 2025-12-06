"""
Skeleton Hydrator.

This module implements the logic to turn a Skeleton schema into actual files on disk.
It handles:
1. Traversing the component tree
2. Merging cascades (parent -> child)
3. Generating frontmatter (mapping Component Model -> YAML)
4. Writing files (atomic writes)
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from bengal.cli.skeleton.schema import Component, Skeleton
from bengal.utils.atomic_write import atomic_write_text
from bengal.utils.logger import get_logger

logger = get_logger(__name__)


class Hydrator:
    """
    Hydrates a Skeleton into a file structure.
    """

    def __init__(self, root_path: Path, dry_run: bool = False, force: bool = False):
        self.root_path = root_path
        self.dry_run = dry_run
        self.force = force
        self.created_files: list[Path] = []
        self.skipped_files: list[Path] = []

    def apply(self, skeleton: Skeleton) -> None:
        """Apply the skeleton to the root path."""
        # Start with global cascade
        self._process_components(skeleton.structure, self.root_path, skeleton.cascade)

    def _process_components(
        self,
        components: list[Component],
        parent_path: Path,
        cascade: dict[str, Any],
    ) -> None:
        """Process a list of components recursively."""
        for comp in components:
            # 1. Merge Cascade
            # Parent cascade + Component fields -> Component effective state
            # Note: We don't modify the component in place, we just use the merged values
            # for creating children context.
            
            effective_type = comp.type or cascade.get("type")
            effective_variant = comp.variant or cascade.get("variant")
            
            # Prepare next cascade context (merge current component's cascade into parent's)
            next_cascade = cascade.copy()
            next_cascade.update(comp.cascade)

            # 2. Determine Output Path
            # If it's a section (has pages), it becomes a directory
            # If it's a page, it becomes a file
            if comp.is_section():
                current_path = parent_path / comp.path
                output_file = current_path / "_index.md"
            else:
                # Ensure .md extension
                filename = comp.path if comp.path.endswith(".md") else f"{comp.path}.md"
                output_file = parent_path / filename
                current_path = parent_path  # For children (though pages shouldn't have children)

            # 3. Generate Content
            file_content = self._generate_file_content(comp, effective_type, effective_variant)

            # 4. Write File
            self._write_file(output_file, file_content)

            # 5. Recurse
            if comp.pages:
                self._process_components(comp.pages, current_path, next_cascade)

    def _generate_file_content(
        self, comp: Component, effective_type: str | None, effective_variant: str | None
    ) -> str:
        """Generate the full markdown file content with frontmatter."""
        # 1. Build Frontmatter Dict
        frontmatter = {}

        # Identity & Mode (Explicitly set if present on component, ignoring cascade for local file)
        # We write what is explicitly defined on THIS component.
        # However, for the 'cascade' key in frontmatter, we write comp.cascade.
        
        if comp.type:
            frontmatter["type"] = comp.type
        if comp.variant:
            frontmatter["variant"] = comp.variant

        # Props (Data)
        # Flatten props into root for ergonomic markdown (hybrid approach)
        # But we can also support 'props' dict if user prefers strictness.
        # For now, let's flatten to keep it idiomatic Bengal/Hugo style.
        frontmatter.update(comp.props)

        # Cascade (Forwarding instructions to children)
        if comp.cascade:
            frontmatter["cascade"] = comp.cascade

        # 2. Serialize to YAML
        yaml_str = yaml.dump(frontmatter, sort_keys=False, default_flow_style=False).strip()
        
        # 3. Append Content
        body = comp.content or ""
        if not body and "title" in comp.props:
             body = f"# {comp.props['title']}\n\nAdd content here."
        
        return f"---\n{yaml_str}\n---\n\n{body}\n"

    def _write_file(self, path: Path, content: str) -> None:
        """Write file to disk (handling dry-run and force)."""
        if path.exists() and not self.force:
            logger.debug("skipping_existing_file", path=str(path))
            self.skipped_files.append(path)
            return

        if self.dry_run:
            logger.info("dry_run_write", path=str(path))
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            atomic_write_text(path, content)
        
        self.created_files.append(path)

