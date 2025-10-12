Title: Dev server freezes on rapid navigation - diagnosis and fixes

Summary
- Increased HTTP server backlog to 128 to absorb bursty connections
- Added thread-safe HTML injection cache with locking and safe clearing after rebuilds
- Reduced SSE keepalive interval from 30s to 10s; close EventSource on page unload/pagehide
- Minor client init adjustment to avoid double-init via once: true

Hypothesis
- Thread pool saturation from lingering SSE connections and slow keepalive cycle
- Race conditions and lock contention around HTML injection cache
- Request queue overflow under rapid navigation causing perceived freeze

Changes
- dev_server.py: custom ThreadingTCPServer class with request_queue_size=128
- request_handler.py: add _html_cache_lock for thread-safe access
- build_handler.py: clear HTML cache under lock after rebuild
- live_reload.py: close EventSource on unload/pagehide; keepalive every 10s
- interactive.js: DOMContentLoaded listener set with { once: true }

Follow-ups
- Add optional diagnostics: per-request timing, open thread counts, SSE client count
- Consider HTTP keep-alive timeouts and max connections if freezes persist
- Expose env flags to tune request_queue_size and cache size

Validation Plan
- Stress test: open 10 tabs, rapidly click 5–10 links per tab
- Observe server responsiveness and absence of backlog stalls
- Verify no thread leakage (counts stabilize) and quick recovery
