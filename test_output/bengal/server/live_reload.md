# live_reload

```{warning}
Template Variable Error: python/module.md.jinja2
Undefined variable: 'config' is undefined
```

## Basic Information

**Type:** module
**Source:** bengal/server/live_reload.py

Live reload functionality for the dev server.

Provides Server-Sent Events (SSE) endpoint and HTML injection for hot reload.

Architecture:
- SSE Endpoint (/__bengal_reload__): Maintains persistent connections to clients
- Live Reload Script: Injected into HTML pages to connect to SSE endpoint
- Reload Notifications: Broadcast to all clients when build completes using a
  global generation counter and condition variable (no per-client queues)

SSE Protocol:
    Client: EventSource('/__bengal_reload__')
    Server (init): retry: 2000

  (client waits 2s before reconnect after disconnect)
    Server (events): data: {json payload}|reload

  (triggers reload/css update)
    Server (idle): : keepalive

  (sent on interval; ignored by client)

Dev behavior:
- Keepalive interval is configurable via env BENGAL_SSE_KEEPALIVE_SECS (default 15s).
- On new connections/reconnects, last_seen_generation is initialized to the current
  generation so we do not replay the last reload event to the client.

*Note: Template has undefined variables. This is fallback content.*
