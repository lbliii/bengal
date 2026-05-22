Fixed a dev-server watcher shutdown race when the background event loop closes before `stop()` posts its final stop callback.
