"""Metadata accumulator using ContextVar pattern.

Collects extended page metadata during rendering in a single pass.
Complements existing HtmlRenderer._headings for TOC.

Thread Safety:
    ContextVars are thread-local by design (PEP 567).
    Each thread has independent storage - no locks needed.

Usage:
    with metadata_context() as meta:
        html = renderer.render(ast)
        if meta.has_math:
            include_mathjax()
        print(f"Word count: {meta.word_count}")

RFC: rfc-contextvar-downstream-patterns.md

"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import Token
from dataclasses import dataclass, field

from bengal.parsing.backends.patitas.utils.contextvar import ContextVarManager

__all__ = [
    "RenderMetadata",
    "get_metadata",
    "metadata_context",
    "reset_metadata",
    "set_metadata",
]


@dataclass
class RenderMetadata:
    """Extended metadata accumulated during rendering.

    Complements existing HtmlRenderer._headings for TOC.
    Collected during single render pass—no post-processing needed.

    Attributes:
        has_math: Whether inline or block math was rendered
        has_code_blocks: Whether any fenced/indented code was rendered
        has_mermaid: Whether mermaid diagrams were detected
        has_tables: Whether any tables were rendered
        word_count: Accumulated word count from text content
        code_languages: Set of programming languages in code blocks
        internal_links: List of internal link targets
        external_links: List of external link URLs
        image_refs: List of image source URLs
    """

    # Content features (for asset loading decisions)
    has_math: bool = False
    has_code_blocks: bool = False
    has_mermaid: bool = False
    has_tables: bool = False

    # Statistics
    word_count: int = 0
    code_languages: set[str] = field(default_factory=set)

    # Cross-references (for dependency tracking)
    internal_links: list[str] = field(default_factory=list)
    external_links: list[str] = field(default_factory=list)
    image_refs: list[str] = field(default_factory=list)

    def add_words(self, text: str) -> None:
        """Accumulate word count from text content.

        Args:
            text: Text content to count words from
        """
        self.word_count += len(text.split())

    def add_code_block(self, language: str | None) -> None:
        """Record a code block.

        Args:
            language: Programming language (None for unspecified)
        """
        self.has_code_blocks = True
        if language:
            self.code_languages.add(language)
            if language == "mermaid":
                self.has_mermaid = True

    def add_internal_link(self, target: str) -> None:
        """Record an internal link target.

        Args:
            target: Internal link target (relative path)
        """
        self.internal_links.append(target)

    def add_external_link(self, url: str) -> None:
        """Record an external link URL.

        Args:
            url: External link URL
        """
        self.external_links.append(url)

    def add_image(self, src: str) -> None:
        """Record an image source.

        Args:
            src: Image source URL
        """
        self.image_refs.append(src)

    def to_dict(self) -> dict:
        """Convert to dictionary for page metadata.

        Returns:
            Dictionary with all metadata fields
        """
        return {
            "has_math": self.has_math,
            "has_code_blocks": self.has_code_blocks,
            "has_mermaid": self.has_mermaid,
            "has_tables": self.has_tables,
            "word_count": self.word_count,
            "code_languages": list(self.code_languages),
            "internal_links": self.internal_links,
            "external_links": self.external_links,
            "image_refs": self.image_refs,
        }


# Thread-local metadata using ContextVarManager (default None for optional usage)
_manager: ContextVarManager[RenderMetadata] = ContextVarManager("render_metadata")


def get_metadata() -> RenderMetadata | None:
    """Get current metadata accumulator (None if not in context).

    Returns:
        Current RenderMetadata or None if not within metadata_context()
    """
    return _manager.get()


def set_metadata(meta: RenderMetadata) -> Token[RenderMetadata | None]:
    """Set metadata accumulator for current context.

    Returns a token that can be used to restore the previous value.

    Args:
        meta: The RenderMetadata to set for the current context.

    Returns:
        Token for reset_metadata()
    """
    return _manager.set(meta)


def reset_metadata(token: Token[RenderMetadata | None] | None = None) -> None:
    """Reset metadata accumulator.

    If token is provided, restores to the previous value.
    Otherwise, resets to None.

    Args:
        token: Optional token from set_metadata()
    """
    _manager.reset(token)


@contextmanager
def metadata_context() -> Iterator[RenderMetadata]:
    """Context manager for metadata accumulation.

    Creates a fresh RenderMetadata and sets it as the current accumulator.
    Properly restores previous state on exit (supports nesting).

    Yields:
        RenderMetadata instance that will be populated during rendering

    Usage:
        with metadata_context() as meta:
            html = renderer.render(ast)
            if meta.has_math:
                include_mathjax()
    """
    meta = RenderMetadata()
    with _manager.context(meta):
        yield meta
