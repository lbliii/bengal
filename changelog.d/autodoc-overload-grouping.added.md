Autodoc now groups `@overload` definitions (#328). Multiple `typing.overload`
stubs plus the concrete implementation of a callable are collapsed into a single
documented member that lists every signature variant in source order, instead of
N+1 duplicate peers that all collide on one `#name` anchor. The implementation's
docstring is kept as the canonical description; an `overload` badge marks the
member and each signature variant is rendered. Grouping runs before member-order
sorting (so ordering stays stable and byte-reproducible) and applies to both class
methods and module-level functions. The grouped metadata round-trips through
`DocElement.to_dict`/`from_dict` and the content-hash stays stable.
