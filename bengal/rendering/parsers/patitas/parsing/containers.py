"""Container Stack Architecture for CommonMark Parsing.

This module implements a Container Stack for managing nested block-level
containers during Markdown parsing. The stack provides:

1. Explicit indent ownership - Each container "claims" an indent range
2. Automatic state propagation - Looseness propagates upward on pop
3. Centralized indent queries - find_owner() replaces scattered logic

Usage:
    stack = ContainerStack()  # Initializes with DOCUMENT frame

    # Push a list container
    stack.push(ContainerFrame(
        container_type=ContainerType.LIST,
        start_indent=0,
        content_indent=2,
    ))

    # Find owner for a given indent
    owner, depth = stack.find_owner(4)

    # Pop and propagate state
    frame = stack.pop()
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto


class ContainerType(Enum):
    """Types of block-level containers in CommonMark."""

    DOCUMENT = auto()  # Root container
    LIST = auto()  # List (ordered or unordered)
    LIST_ITEM = auto()  # Individual list item
    BLOCK_QUOTE = auto()  # Block quote (> prefix)
    FENCED_CODE = auto()  # Fenced code block (leaf, no nesting)


@dataclass(slots=True)
class ContainerFrame:
    """A frame on the container stack representing a parsing context.

    Each container "claims" an indent range. Tokens are routed to
    the deepest container that claims their indent.

    Attributes:
        container_type: The type of container (LIST, LIST_ITEM, etc.)
        start_indent: Where this container started (marker position)
        content_indent: Minimum indent for content continuation
        marker_width: Width of the marker (e.g., 2 for "- ")
        max_sibling_indent: For lists, marker siblings can appear at
            start_indent to start_indent+3
        is_loose: Whether the container has blank lines between content
        saw_blank_line: Whether a blank line was seen in this container
        ordered: For lists, whether the list is ordered
        bullet_char: For unordered lists, the bullet character
        start_number: For ordered lists, the starting number
    """

    container_type: ContainerType

    # Indent boundaries
    start_indent: int  # Where this container started (marker position)
    content_indent: int  # Minimum indent for content continuation
    marker_width: int = 0  # Width of the marker (e.g., 2 for "- ")

    # For lists: marker siblings can appear at start_indent to start_indent+3
    max_sibling_indent: int = field(default=-1)

    # State that propagates upward on pop
    is_loose: bool = False
    saw_blank_line: bool = False

    # For lists: tracking
    ordered: bool = False
    bullet_char: str = ""
    start_number: int = 1

    def __post_init__(self) -> None:
        """Set default max_sibling_indent if not provided."""
        if self.max_sibling_indent == -1:
            self.max_sibling_indent = self.start_indent

    def owns_content(self, indent: int) -> bool:
        """Does this container own content at this indent level?

        Args:
            indent: The indent level to check

        Returns:
            True if content at this indent belongs to this container
        """
        return indent >= self.content_indent

    def owns_marker(self, indent: int) -> bool:
        """Could a list marker at this indent be a sibling in this container?

        Only valid for LIST containers.

        Args:
            indent: The indent level of the marker

        Returns:
            True if a marker at this indent is a sibling item
        """
        if self.container_type != ContainerType.LIST:
            return False
        return self.start_indent <= indent <= self.max_sibling_indent

    def is_nested_marker(self, indent: int) -> bool:
        """Would a marker at this indent start a nested list?

        Args:
            indent: The indent level of the marker

        Returns:
            True if a marker at this indent starts a nested list
        """
        return indent >= self.content_indent


@dataclass
class ContainerStack:
    """Manages the stack of active containers during parsing.

    Invariant: stack[0] is always DOCUMENT, stack[-1] is innermost container.

    Usage:
        stack = ContainerStack()  # Initializes with DOCUMENT frame
        stack.push(frame)         # Push new container
        stack.pop()               # Pop and propagate state
        stack.find_owner(indent)  # Find container owning this indent
    """

    _stack: list[ContainerFrame] = field(default_factory=list)

    def __post_init__(self) -> None:
        """Initialize with DOCUMENT frame."""
        self._stack = [
            ContainerFrame(
                container_type=ContainerType.DOCUMENT,
                start_indent=0,
                content_indent=0,
            )
        ]

    def push(self, frame: ContainerFrame) -> None:
        """Push a new container onto the stack.

        Args:
            frame: The container frame to push

        Raises:
            AssertionError: If stack is empty (should never happen)
        """
        assert len(self._stack) > 0, "Cannot push to empty stack"
        self._stack.append(frame)

    def pop(self) -> ContainerFrame:
        """Pop the innermost container.

        Propagates state (looseness, blank lines) to parent if applicable.
        - When popping a LIST_ITEM with blank lines, propagates to parent LIST

        Note: For blank lines BETWEEN items (sibling separation), use
        mark_parent_list_loose() directly instead of relying on propagation.
        This propagation handles blank lines WITHIN item content.

        Note: Nested LIST does NOT propagate to parent LIST_ITEM, as nested
        list looseness should not affect the outer list's tightness.

        Returns:
            The popped container frame

        Raises:
            ValueError: If attempting to pop the document frame
        """
        if len(self._stack) <= 1:
            raise ValueError("Cannot pop document frame")

        frame = self._stack.pop()

        # Propagate looseness to parent container
        if frame.saw_blank_line or frame.is_loose:
            parent = self._stack[-1]
            # LIST_ITEM -> propagate to parent LIST
            # This handles blank lines within item content
            if (
                frame.container_type == ContainerType.LIST_ITEM
                and parent.container_type == ContainerType.LIST
            ):
                parent.is_loose = True
                parent.saw_blank_line = True
            # Note: We do NOT propagate nested LIST -> parent LIST_ITEM
            # because nested list looseness should not affect outer list

        return frame

    def current(self) -> ContainerFrame:
        """Get the innermost container.

        Returns:
            The current (innermost) container frame
        """
        return self._stack[-1]

    def depth(self) -> int:
        """Current nesting depth (document = 0).

        Returns:
            The number of containers above DOCUMENT
        """
        return len(self._stack) - 1

    def find_owner(self, indent: int) -> tuple[ContainerFrame, int]:
        """Find which container owns content at this indent.

        Walks from innermost to outermost, returns first container
        that claims the indent.

        Args:
            indent: The indent level to check

        Returns:
            (owner_frame, stack_index) - the frame and its position in stack
        """
        for i in range(len(self._stack) - 1, -1, -1):
            frame = self._stack[i]
            if frame.owns_content(indent):
                return (frame, i)
        return (self._stack[0], 0)

    def find_sibling_list(self, marker_indent: int) -> tuple[ContainerFrame, int] | None:
        """Find a list container where a marker at this indent would be a sibling.

        Args:
            marker_indent: The indent level of the marker

        Returns:
            (frame, index) if found, None if marker starts new list at document level
        """
        for i in range(len(self._stack) - 1, -1, -1):
            frame = self._stack[i]
            if frame.container_type == ContainerType.LIST and frame.owns_marker(marker_indent):
                return (frame, i)
        return None

    def pop_until(self, target_index: int) -> list[ContainerFrame]:
        """Pop containers until stack has target_index + 1 elements.

        Args:
            target_index: The index to stop at (inclusive)

        Returns:
            List of popped frames (innermost first)
        """
        popped = []
        while len(self._stack) > target_index + 1:
            popped.append(self.pop())
        return popped

    def mark_loose(self) -> None:
        """Mark current container as loose (saw blank line with content after)."""
        self._stack[-1].is_loose = True
        self._stack[-1].saw_blank_line = True

    def mark_blank_line(self) -> None:
        """Mark that a blank line was seen in current container."""
        self._stack[-1].saw_blank_line = True

    def mark_parent_list_loose(self) -> None:
        """Mark the parent LIST container as loose.

        Called when a blank line between sibling items is detected.
        The current frame is LIST_ITEM, and the parent should be LIST.
        """
        if len(self._stack) >= 2:
            parent = self._stack[-2]
            if parent.container_type == ContainerType.LIST:
                parent.is_loose = True
                parent.saw_blank_line = True

    def update_content_indent(self, actual_content_indent: int) -> None:
        """Update the current container's content_indent to the actual value.

        Called when the first content line is parsed and we know the actual
        column position where content starts. This allows find_owner() to
        use the correct indent for subsequent content.

        Args:
            actual_content_indent: The actual content indent from first line
        """
        self._stack[-1].content_indent = actual_content_indent
