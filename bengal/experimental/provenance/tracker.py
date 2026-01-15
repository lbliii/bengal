"""
Provenance tracker for automatic dependency capture.

Usage:
    tracker = ProvenanceTracker(store, site_root)
    
    with tracker.track("content/about.md") as ctx:
        # Read files - automatically tracked
        content = ctx.read_file(Path("content/about.md"))
        template = ctx.read_file(Path("templates/page.html"))
        data = ctx.read_data("team.yaml")
        
        # Render...
        html = render(content, template, data)
        
        # Record output
        ctx.set_output(html)
    
    # Provenance automatically saved
    print(ctx.provenance.summary())
"""

from __future__ import annotations

import contextvars
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Generator

from bengal.experimental.provenance.store import ProvenanceStore
from bengal.experimental.provenance.core_types import (
    ContentHash,
    Provenance,
    ProvenanceRecord,
    hash_content,
    hash_dict,
    hash_file,
)

# Context variable for current tracking context
_current_ctx: contextvars.ContextVar[TrackingContext | None] = contextvars.ContextVar(
    "provenance_ctx", default=None
)


def is_tracking() -> bool:
    """Check if provenance tracking is active."""
    return _current_ctx.get() is not None


def record_input(input_type: str, path: str, content_hash: ContentHash) -> None:
    """Record an input (if tracking is active)."""
    ctx = _current_ctx.get()
    if ctx is not None:
        ctx._record_input(input_type, path, content_hash)


@dataclass
class TrackingContext:
    """
    Context for tracking provenance during page rendering.
    
    Captures all inputs accessed during the context and
    builds a complete Provenance record.
    """
    
    page_path: str
    site_root: Path
    store: ProvenanceStore
    
    # Accumulated provenance
    _provenance: Provenance = field(default_factory=Provenance)
    _output_hash: ContentHash = field(default=ContentHash(""))
    
    def _record_input(self, input_type: str, path: str, content_hash: ContentHash) -> None:
        """Record an input (internal)."""
        self._provenance = self._provenance.with_input(input_type, path, content_hash)
    
    def read_file(self, path: Path, input_type: str = "content") -> str:
        """Read a file and record it as an input."""
        full_path = path if path.is_absolute() else self.site_root / path
        content = full_path.read_text()
        
        # Compute hash and record
        content_hash = hash_content(content)
        rel_path = str(path.relative_to(self.site_root) if path.is_absolute() else path)
        self._record_input(input_type, rel_path, content_hash)
        
        return content
    
    def read_file_bytes(self, path: Path, input_type: str = "asset") -> bytes:
        """Read a binary file and record it as an input."""
        full_path = path if path.is_absolute() else self.site_root / path
        content = full_path.read_bytes()
        
        content_hash = hash_content(content)
        rel_path = str(path.relative_to(self.site_root) if path.is_absolute() else path)
        self._record_input(input_type, rel_path, content_hash)
        
        return content
    
    def read_template(self, template_path: Path) -> str:
        """Read a template and record it."""
        return self.read_file(template_path, input_type="template")
    
    def read_partial(self, partial_path: Path) -> str:
        """Read a partial/include and record it."""
        return self.read_file(partial_path, input_type="partial")
    
    def read_data(self, data_path: str | Path) -> Any:
        """Read a data file and record it."""
        import json
        
        path = Path(data_path) if isinstance(data_path, str) else data_path
        full_path = self.site_root / "data" / path if not path.is_absolute() else path
        
        content = full_path.read_text()
        content_hash = hash_content(content)
        
        rel_path = f"data/{path}" if not str(path).startswith("data/") else str(path)
        self._record_input("data", rel_path, content_hash)
        
        # Parse based on extension
        if path.suffix in (".yaml", ".yml"):
            try:
                import yaml
                return yaml.safe_load(content)
            except ImportError:
                # Fallback: return raw content
                return content
        elif path.suffix == ".json":
            return json.loads(content)
        elif path.suffix == ".toml":
            import tomllib
            return tomllib.loads(content)
        else:
            return content
    
    def record_config(self, config: dict[str, Any], key: str = "site_config") -> None:
        """Record configuration as an input."""
        config_hash = hash_dict(config)
        self._record_input("config", key, config_hash)
    
    def record_metadata(self, metadata: dict[str, Any]) -> None:
        """Record page metadata as input (for frontmatter tracking)."""
        meta_hash = hash_dict(metadata)
        self._record_input("metadata", self.page_path, meta_hash)
    
    def set_output(self, output: str | bytes) -> None:
        """Set the output content (for integrity verification)."""
        self._output_hash = hash_content(output if isinstance(output, bytes) else output.encode())
    
    @property
    def provenance(self) -> Provenance:
        """Get the accumulated provenance."""
        return self._provenance
    
    def _finalize(self, build_id: str = "") -> ProvenanceRecord:
        """Create and store the final provenance record."""
        record = ProvenanceRecord(
            page_path=self.page_path,
            provenance=self._provenance,
            output_hash=self._output_hash,
            build_id=build_id,
        )
        self.store.store(record)
        return record


@dataclass
class ProvenanceTracker:
    """
    Main tracker for provenance-based incremental builds.
    
    Usage:
        tracker = ProvenanceTracker(store, site_root)
        
        # Check if rebuild needed
        if tracker.needs_rebuild("content/about.md"):
            with tracker.track("content/about.md") as ctx:
                html = render_with_tracking(ctx)
                ctx.set_output(html)
        
        tracker.save()
    """
    
    store: ProvenanceStore
    site_root: Path
    build_id: str = ""
    
    def __post_init__(self) -> None:
        self.site_root = Path(self.site_root)
    
    @contextmanager
    def track(self, page_path: str) -> Generator[TrackingContext, None, None]:
        """
        Context manager for tracking provenance.
        
        All file reads within this context are automatically recorded.
        """
        ctx = TrackingContext(
            page_path=page_path,
            site_root=self.site_root,
            store=self.store,
        )
        
        token = _current_ctx.set(ctx)
        try:
            yield ctx
        finally:
            _current_ctx.reset(token)
            ctx._finalize(self.build_id)
    
    def is_fresh(self, page_path: str) -> bool:
        """
        Quick check if a page's cached output is still valid.
        
        This probes the current inputs and compares with stored hash.
        Does NOT do full tracking - just checks key inputs.
        """
        # Get stored record
        record = self.store.get(page_path)
        if record is None:
            return False  # Never built
        
        # Quick probe: check if main content file changed
        content_path = self.site_root / page_path
        if content_path.exists():
            current_hash = hash_file(content_path)
            
            # Find the content input in stored provenance
            for inp in record.provenance.inputs:
                if inp.input_type == "content" and inp.path == page_path:
                    if inp.hash != current_hash:
                        return False  # Content changed
                    break
        
        # For full validation, we'd check all inputs
        # But for quick probe, content change is the most common case
        return True
    
    def needs_rebuild(self, page_path: str) -> bool:
        """Inverse of is_fresh (for readability)."""
        return not self.is_fresh(page_path)
    
    def get_affected_pages(self, changed_path: str) -> set[str]:
        """
        Find all pages affected by a file change.
        
        This is the SUBVENANCE query - critical for incremental builds.
        """
        full_path = self.site_root / changed_path
        current_hash = hash_file(full_path)
        
        return self.store.get_affected_by(current_hash)
    
    def get_lineage(self, page_path: str) -> list[str]:
        """Get human-readable lineage for debugging."""
        record = self.store.get(page_path)
        if record is None:
            return [f"No provenance for {page_path}"]
        
        lines = [f"Provenance for {page_path}:"]
        lines.append(f"  Combined hash: {record.provenance.combined_hash}")
        lines.append(f"  Output hash: {record.output_hash}")
        lines.append(f"  Inputs ({record.provenance.input_count}):")
        
        for inp in sorted(record.provenance.inputs, key=lambda x: (x.input_type, x.path)):
            lines.append(f"    [{inp.input_type}] {inp.path} = {inp.hash}")
        
        return lines
    
    def save(self) -> None:
        """Persist all provenance data."""
        self.store.save()
    
    def stats(self) -> dict[str, Any]:
        """Get tracker statistics."""
        return self.store.stats()
