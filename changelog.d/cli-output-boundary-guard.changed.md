Add a unit-test guard that blocks direct terminal writes in CLI-facing Bengal
packages so output continues to route through the shared CLI renderer.
