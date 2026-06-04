REST autodoc schema pages now render advanced OpenAPI constructs as structured
model documentation instead of dropping or flattening them (#285). `oneOf`,
`anyOf`, and `allOf` render as labeled composition blocks; polymorphic schemas
show their `discriminator` property and `value → schema` mapping; per-property
validation constraints (`format`, `pattern`, numeric `min`/`max`/`multipleOf`,
string `minLength`/`maxLength`, and array `minItems`/`maxItems`/`uniqueItems`)
render as chips; and `nullable`, `readOnly`, `writeOnly`, and `deprecated`
render as badges. Open and typed maps (`additionalProperties`) get their own
section, primitive schemas surface their constraints and example, and a
self-referential schema renders a bounded, readable "circular reference"
indicator rather than an empty box or runaway recursion. Schema catalog tiles
gained composition/discriminator/deprecated summary chips. Examples normalize a
singular `example`, a 3.1 `examples` list, and a named `examples` map into a
uniform rendering. The work is driven by additive normalization filters in
`bengal/rendering/template_functions/openapi.py`
(`schema_composition`/`schema_constraints`/`schema_flags`/
`schema_additional_properties`/`schema_examples`/`schema_ref`), so simple schemas
render byte-identically. The demo commerce spec marks server-assigned fields
`readOnly` and credentials `writeOnly` to exercise the new rendering. Covered by
unit tests for the normalization helpers (including circular-ref bounding and
malformed-input robustness), template/CSS contract tests, and an end-to-end
build of a fixture exercising every construct.
