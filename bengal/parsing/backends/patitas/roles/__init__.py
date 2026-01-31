"""Role system for Patitas.

Provides extensible inline markup through the role syntax:

{role}`content`

Roles are the inline equivalent of directives, providing
custom inline markup capabilities.

Key components:
- RoleHandler: Protocol for custom role implementations
- RoleRegistry: Handler lookup and registration

Thread Safety:
All components are designed for thread-safety:
- Handlers must be stateless
- Registry is immutable after creation

Example:
    >>> from patitas.roles import RoleHandler
    >>>
    >>> class EmojiRole:
    ...     names = ("emoji",)
    ...     token_type = "emoji"
    ...
    ...     def parse(self, name, content, location):
    ...         return Role(location, name, content)
    ...
    ...     def render(self, node, sb):
    ...         sb.append(f'<span class="emoji">{EMOJI_MAP.get(node.content, node.content)}</span>')

"""

from __future__ import annotations

from bengal.parsing.backends.patitas.roles.protocol import (
    RoleHandler,
    RoleParseOnly,
    RoleRenderOnly,
)
from bengal.parsing.backends.patitas.roles.registry import (
    RoleRegistry,
    RoleRegistryBuilder,
    create_default_registry,
)

__all__ = [
    # Protocol
    "RoleHandler",
    "RoleParseOnly",
    # Registry
    "RoleRegistry",
    "RoleRegistryBuilder",
    "RoleRenderOnly",
    "create_default_registry",
]
