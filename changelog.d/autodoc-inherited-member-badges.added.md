Autodoc now surfaces inherited members in the rendered output (#329). When
`include_inherited` is enabled, members synthesized from base classes already
carried `inherited_from`/`synthetic` metadata but it was never shown. `MemberView`
now exposes `is_inherited` and `inherited_from`, and the default theme renders an
"inherited from X" attribution badge that is visually distinct from native
members. The `include_inherited` default is unchanged (stays opt-in/off).
