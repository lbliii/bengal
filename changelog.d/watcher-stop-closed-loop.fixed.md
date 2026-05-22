Hardened dev-server watcher shutdown with explicit lifecycle states, including the race where the background event loop closes before `stop()` posts its final stop callback.
