The shared test suite no longer leaks the active plugin registry between tests.
A build sets the `_active_registry` contextvar (`set_active_registry()`) but
never resets it, so any test that ran a build leaked its `FrozenPluginRegistry`
into the contextvar for every later test sharing the same `pytest-xdist` worker.
Under random test ordering this caused intermittent failures in
`test_active_plugin_registry_is_context_scoped` (which expects `None`) and, via
patitas' `get_active_registry()` read during parsing, in
`test_parse_shard_matches_in_process_parse` (in-process parses diverging from
fresh-subprocess shard parses). The autouse `reset_bengal_state` fixture now
clears the contextvar before and after each test.
