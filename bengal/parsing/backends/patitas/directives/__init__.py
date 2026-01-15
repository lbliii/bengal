"""Directive system for Patitas.

Provides extensible block-level markup through the directive syntax:

:::{directive-name} optional title
:option-key: option value

Content goes here.
:::

Key components:
- DirectiveHandler: Protocol for custom directive implementations
- DirectiveOptions: Base class for typed option parsing
- DirectiveContract: Nesting validation rules
- DirectiveRegistry: Handler lookup and registration

Thread Safety:
All components are designed for thread-safety:
- Options are frozen dataclasses
- Contracts are frozen dataclasses
- Registry is immutable after creation
- Handlers must be stateless

Example:
    >>> from patitas.directives import DirectiveHandler, DirectiveOptions
    >>>
    >>> @dataclass(frozen=True, slots=True)
    ... class VideoOptions(DirectiveOptions):
    ...     width: int | None = None
    ...     autoplay: bool = False
    ...
    >>> class VideoDirective:
    ...     names = ("video",)
    ...     token_type = "video"
    ...     options_class = VideoOptions
    ...
    ...     def parse(self, name, title, options, content, children, location):
    ...         return Directive(location, name, title, options, children)
    ...
    ...     def render(self, node, rendered_children, sb):
    ...         sb.append(f'<video src="{node.title}"></video>')

"""

from __future__ import annotations

from bengal.parsing.backends.patitas.directives.contracts import (
    DEFINITION_CONTRACT,
    DEFINITION_LIST_CONTRACT,
    DROPDOWN_CONTRACT,
    GRID_CONTRACT,
    GRID_ITEM_CONTRACT,
    STEP_CONTRACT,
    STEPS_CONTRACT,
    TAB_ITEM_CONTRACT,
    TAB_SET_CONTRACT,
    ContractViolation,
    DirectiveContract,
)
from bengal.parsing.backends.patitas.directives.options import (
    AdmonitionOptions,
    CodeBlockOptions,
    DirectiveOptions,
    FigureOptions,
    ImageOptions,
    StyledOptions,
    TabItemOptions,
    TabSetOptions,
)
from bengal.parsing.backends.patitas.directives.protocol import (
    DirectiveHandler,
    DirectiveParseOnly,
    DirectiveRenderOnly,
)
from bengal.parsing.backends.patitas.directives.registry import (
    DirectiveRegistry,
    DirectiveRegistryBuilder,
    create_default_registry,
)

__all__ = [
    # Protocol
    "DirectiveHandler",
    "DirectiveParseOnly",
    "DirectiveRenderOnly",
    # Options
    "DirectiveOptions",
    "StyledOptions",
    "AdmonitionOptions",
    "CodeBlockOptions",
    "ImageOptions",
    "FigureOptions",
    "TabSetOptions",
    "TabItemOptions",
    # Contracts
    "DirectiveContract",
    "ContractViolation",
    # Pre-defined contracts
    "STEPS_CONTRACT",
    "STEP_CONTRACT",
    "TAB_SET_CONTRACT",
    "TAB_ITEM_CONTRACT",
    "DROPDOWN_CONTRACT",
    "GRID_CONTRACT",
    "GRID_ITEM_CONTRACT",
    "DEFINITION_LIST_CONTRACT",
    "DEFINITION_CONTRACT",
    # Registry
    "DirectiveRegistry",
    "DirectiveRegistryBuilder",
    "create_default_registry",
]
