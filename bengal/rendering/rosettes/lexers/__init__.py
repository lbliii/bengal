"""Rosettes lexers package.

All lexers are hand-written state machines with O(n) guaranteed performance
and zero ReDoS vulnerability. Lexers are loaded lazily via the registry.
"""

from bengal.rendering.rosettes.lexers._state_machine import StateMachineLexer

__all__ = ["StateMachineLexer"]
