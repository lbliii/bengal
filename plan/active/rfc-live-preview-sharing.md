# RFC: Live Collaboration Preview

**Status**: Draft  
**Created**: 2025-12-08  
**Author**: AI Assistant  
**Confidence**: 65% 🟡

---

## Executive Summary

Enable sharing temporary preview URLs from the local dev server without deployment. Run `bengal serve --share` to get a public URL like `https://preview.bengal.dev/abc123` that teammates or stakeholders can access.

---

## Problem Statement

### Current State

To share a preview of documentation changes:
1. Commit changes
2. Push to branch
3. Wait for CI/CD
4. Share staging URL

Or use external tools:
- ngrok (separate install, configuration)
- localtunnel (unreliable)
- Cloudflare Tunnels (complex setup)

**Evidence**:
- `bengal/server/`: No tunneling or sharing capability
- No integration with external tunnel services

### Pain Points

1. **Slow feedback loop**: 5-10 minutes to share a change
2. **Context switching**: Leave Bengal workflow to use ngrok
3. **Stakeholder friction**: Non-technical reviewers can't run Bengal locally
4. **Branch pollution**: Creating PR branches just for previews

### User Impact

Writers avoid getting early feedback because it's too much work. Stakeholders review in large batches instead of incrementally. Quality suffers.

---

## Goals & Non-Goals

**Goals**:
- One-command preview sharing: `bengal serve --share`
- Shareable URL accessible from anywhere
- Optional authentication (password, single-use links)
- No external account required for basic use
- Automatic cleanup when server stops

**Non-Goals**:
- Persistent hosting (use `bengal deploy` for that)
- Custom domains (not for previews)
- High traffic support (preview, not production)
- Real-time collaboration editing (just viewing)

---

## Architecture Impact

**Affected Subsystems**:
- **Server** (`bengal/server/`): Tunnel integration
- **CLI** (`bengal/cli/`): Share flags and status

**New Components**:
- `bengal/server/tunnel.py` - Tunnel provider abstraction
- `bengal/server/auth.py` - Preview authentication

---

## Design Options

### Option A: Self-Hosted Tunnel Relay (Recommended)

**Concept**: Bengal project runs a relay server. Local dev servers connect via WebSocket. Public URLs proxy through the relay.

```
┌─────────────────┐     WebSocket      ┌─────────────────┐
│  Local Bengal   │◀─────────────────▶│  Bengal Relay   │
│  Dev Server     │                    │  (preview.      │
│  :8000          │                    │   bengal.dev)   │
└─────────────────┘                    └────────┬────────┘
                                                │
                                                │ HTTPS
                                                ▼
                                       ┌─────────────────┐
                                       │    Reviewer     │
                                       │    Browser      │
                                       └─────────────────┘
```

**How it works**:
1. `bengal serve --share` connects to `preview.bengal.dev` via WebSocket
2. Relay assigns unique subdomain: `abc123.preview.bengal.dev`
3. Requests to subdomain are forwarded through WebSocket to local server
4. Responses streamed back through relay

**Implementation**:
```python
# bengal/server/tunnel.py
import websockets
import asyncio
from dataclasses import dataclass

@dataclass
class TunnelConfig:
    relay_url: str = "wss://preview.bengal.dev/tunnel"
    auth_token: str | None = None  # Optional for rate limiting

class TunnelClient:
    def __init__(self, local_port: int, config: TunnelConfig):
        self.local_port = local_port
        self.config = config
        self.public_url: str | None = None
    
    async def connect(self) -> str:
        """Connect to relay and get public URL."""
        async with websockets.connect(self.config.relay_url) as ws:
            # Register with relay
            await ws.send(json.dumps({
                "type": "register",
                "token": self.config.auth_token,
            }))
            
            # Receive assigned URL
            response = json.loads(await ws.recv())
            self.public_url = response["url"]
            
            # Handle incoming requests
            await self._handle_requests(ws)
        
        return self.public_url
    
    async def _handle_requests(self, ws):
        """Forward requests from relay to local server."""
        async for message in ws:
            request = json.loads(message)
            
            # Forward to local server
            async with aiohttp.ClientSession() as session:
                async with session.request(
                    method=request["method"],
                    url=f"http://localhost:{self.local_port}{request['path']}",
                    headers=request["headers"],
                    data=request.get("body"),
                ) as resp:
                    # Send response back through relay
                    await ws.send(json.dumps({
                        "request_id": request["id"],
                        "status": resp.status,
                        "headers": dict(resp.headers),
                        "body": await resp.text(),
                    }))
```

**Relay Server** (hosted by Bengal project):
```python
# Separate service: preview-relay
from fastapi import FastAPI, WebSocket
import uuid

app = FastAPI()
tunnels: dict[str, WebSocket] = {}

@app.websocket("/tunnel")
async def tunnel_endpoint(ws: WebSocket):
    await ws.accept()
    
    # Assign unique subdomain
    tunnel_id = uuid.uuid4().hex[:8]
    tunnels[tunnel_id] = ws
    
    await ws.send_json({
        "type": "registered",
        "url": f"https://{tunnel_id}.preview.bengal.dev",
    })
    
    try:
        await ws.receive()  # Keep connection open
    finally:
        del tunnels[tunnel_id]

@app.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def proxy(request: Request):
    # Extract tunnel ID from subdomain
    host = request.headers.get("host", "")
    tunnel_id = host.split(".")[0]
    
    if tunnel_id not in tunnels:
        raise HTTPException(404, "Preview not found")
    
    ws = tunnels[tunnel_id]
    request_id = uuid.uuid4().hex
    
    # Forward to local server via WebSocket
    await ws.send_json({
        "id": request_id,
        "method": request.method,
        "path": request.url.path,
        "headers": dict(request.headers),
        "body": await request.body(),
    })
    
    # Wait for response (with timeout)
    response = await asyncio.wait_for(
        receive_response(ws, request_id),
        timeout=30
    )
    
    return Response(
        content=response["body"],
        status_code=response["status"],
        headers=response["headers"],
    )
```

**Pros**:
- No external account needed
- Bengal controls the experience
- Can add features (auth, analytics)

**Cons**:
- Requires Bengal project to run relay
- Infrastructure cost
- Single point of failure

---

### Option B: Cloudflare Tunnels Integration

**Concept**: Use Cloudflare's free tunnel service (cloudflared).

```python
# bengal/server/tunnel_cloudflare.py
import subprocess
import re

class CloudflareTunnel:
    def __init__(self, local_port: int):
        self.local_port = local_port
        self.process: subprocess.Popen | None = None
    
    async def start(self) -> str:
        """Start cloudflared tunnel and return URL."""
        self.process = subprocess.Popen(
            ["cloudflared", "tunnel", "--url", f"http://localhost:{self.local_port}"],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )
        
        # Parse URL from output
        for line in self.process.stdout:
            match = re.search(r'https://[a-z0-9-]+\.trycloudflare\.com', line.decode())
            if match:
                return match.group(0)
        
        raise RuntimeError("Failed to get tunnel URL")
    
    def stop(self):
        if self.process:
            self.process.terminate()
```

**Pros**:
- Free and reliable
- No infrastructure to maintain
- Fast (Cloudflare's network)

**Cons**:
- Requires cloudflared binary install
- URL changes on each restart
- Cloudflare's terms of service

---

### Option C: ngrok Integration

**Concept**: Built-in integration with ngrok.

```python
# bengal/server/tunnel_ngrok.py
from pyngrok import ngrok

class NgrokTunnel:
    def __init__(self, local_port: int, auth_token: str | None = None):
        self.local_port = local_port
        if auth_token:
            ngrok.set_auth_token(auth_token)
    
    def start(self) -> str:
        """Start ngrok tunnel and return URL."""
        tunnel = ngrok.connect(self.local_port, "http")
        return tunnel.public_url
    
    def stop(self):
        ngrok.kill()
```

**Pros**:
- Well-known, reliable
- Python SDK available
- Paid tiers have stable URLs

**Cons**:
- Free tier has limitations
- Requires ngrok account for best experience
- External dependency

---

## Recommended Approach: Hybrid

Start with **Option B** (Cloudflare) for zero-infrastructure launch, with abstraction layer to support Option A (self-hosted) later.

```python
# bengal/server/tunnel.py
from abc import ABC, abstractmethod

class TunnelProvider(ABC):
    @abstractmethod
    async def start(self) -> str:
        """Start tunnel and return public URL."""
        pass
    
    @abstractmethod
    def stop(self):
        """Stop tunnel."""
        pass

def get_tunnel_provider(
    local_port: int,
    provider: str = "auto",
) -> TunnelProvider:
    """Get appropriate tunnel provider."""
    
    if provider == "cloudflare" or (provider == "auto" and _has_cloudflared()):
        return CloudflareTunnel(local_port)
    elif provider == "ngrok":
        return NgrokTunnel(local_port)
    elif provider == "bengal":
        return BengalRelayTunnel(local_port)
    else:
        raise ValueError(f"Unknown tunnel provider: {provider}")
```

---

## CLI Interface

### Basic Sharing

```bash
# Start server with sharing enabled
bengal serve --share

# Output:
# 🌐 Local:  http://localhost:8000
# 🔗 Share:  https://abc123.trycloudflare.com
# 
# Share this URL with reviewers. Press Ctrl+C to stop.
```

### With Authentication

```bash
# Password-protected preview
bengal serve --share --password

# Output:
# 🌐 Local:  http://localhost:8000
# 🔗 Share:  https://abc123.trycloudflare.com
# 🔐 Password: xK9mP2nQ (auto-generated)

# Custom password
bengal serve --share --password=secretreview
```

### Single-Use Links

```bash
# Generate one-time link
bengal serve --share --single-use

# Output:
# 🔗 Share:  https://abc123.trycloudflare.com?token=xyz789
# ⚠️  This link expires after first use
```

### Expiring Links

```bash
# Link expires after 1 hour
bengal serve --share --expires=1h

# Output:
# 🔗 Share:  https://abc123.trycloudflare.com
# ⏰ Expires in 1 hour
```

---

## Authentication Implementation

```python
# bengal/server/auth.py
from dataclasses import dataclass
from datetime import datetime, timedelta
import secrets
import hashlib

@dataclass
class PreviewAuth:
    password: str | None = None
    single_use_tokens: set[str] = field(default_factory=set)
    expires_at: datetime | None = None

class PreviewAuthMiddleware:
    def __init__(self, auth: PreviewAuth):
        self.auth = auth
        self.used_tokens: set[str] = set()
    
    async def __call__(self, request, call_next):
        # Check expiration
        if self.auth.expires_at and datetime.now() > self.auth.expires_at:
            return Response("Preview expired", status_code=410)
        
        # Check single-use token
        token = request.query_params.get("token")
        if self.auth.single_use_tokens:
            if not token or token not in self.auth.single_use_tokens:
                return Response("Invalid or expired token", status_code=401)
            if token in self.used_tokens:
                return Response("Token already used", status_code=401)
            self.used_tokens.add(token)
        
        # Check password
        if self.auth.password:
            # Check cookie first
            if request.cookies.get("preview_auth") == self._hash_password():
                return await call_next(request)
            
            # Check form submission
            if request.method == "POST" and request.url.path == "/_auth":
                form = await request.form()
                if form.get("password") == self.auth.password:
                    response = RedirectResponse("/")
                    response.set_cookie("preview_auth", self._hash_password())
                    return response
            
            # Show login form
            return HTMLResponse(self._login_form())
        
        return await call_next(request)
    
    def _hash_password(self) -> str:
        return hashlib.sha256(self.auth.password.encode()).hexdigest()
    
    def _login_form(self) -> str:
        return """
        <!DOCTYPE html>
        <html>
        <head><title>Preview Access</title></head>
        <body style="font-family: system-ui; max-width: 300px; margin: 100px auto; text-align: center;">
            <h2>🔐 Preview Access</h2>
            <form method="POST" action="/_auth">
                <input type="password" name="password" placeholder="Password" style="padding: 10px; width: 100%;">
                <button type="submit" style="margin-top: 10px; padding: 10px 20px;">Access Preview</button>
            </form>
        </body>
        </html>
        """
```

---

## Configuration

```toml
# bengal.toml
[server.share]
# Default tunnel provider
provider = "auto"  # or "cloudflare", "ngrok", "bengal"

# ngrok settings (if using ngrok)
# ngrok_token = "..."  # or BENGAL_NGROK_TOKEN env var

# Bengal relay settings (if using bengal relay)
# relay_url = "wss://preview.bengal.dev/tunnel"

# Default authentication
default_password = false
default_expiry = "24h"
```

---

## Implementation Plan

### Phase 1: Basic Sharing (2 weeks)
- [ ] Cloudflare tunnel integration
- [ ] `--share` flag
- [ ] URL display and status

### Phase 2: Authentication (1 week)
- [ ] Password protection
- [ ] Single-use tokens
- [ ] Expiration

### Phase 3: Multi-Provider (2 weeks)
- [ ] Provider abstraction
- [ ] ngrok support
- [ ] Auto-detection

### Phase 4: Bengal Relay (Future)
- [ ] Design relay architecture
- [ ] Deploy relay service
- [ ] Client integration

---

## Risks & Mitigations

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| Cloudflare changes terms | High | Low | Provider abstraction, multiple options |
| Security exposure | High | Medium | Auth options, expiring links, clear warnings |
| Relay infrastructure cost | Medium | Medium | Start with Cloudflare, add relay later |
| Complex setup for auth | Low | Low | Sensible defaults, clear docs |

---

## Open Questions

1. **Should Bengal run its own relay?**
   - Pro: Better UX, more features
   - Con: Infrastructure cost, maintenance
   - Decision: Start without, add if demand exists

2. **How to handle large assets?**
   - Tunnels may be slow for images/videos
   - Proposal: Warning for large sites, suggest deployment

3. **Should preview access be logged?**
   - Useful for knowing who viewed
   - Privacy concerns
   - Proposal: Opt-in access logging

---

## Success Criteria

- [ ] `bengal serve --share` produces working public URL
- [ ] URL accessible from external network
- [ ] Password protection works
- [ ] Clean shutdown removes tunnel
- [ ] <5s to establish tunnel

---

## References

- [Cloudflare Tunnels](https://developers.cloudflare.com/cloudflare-one/connections/connect-apps/)
- [ngrok](https://ngrok.com/)
- [localtunnel](https://github.com/localtunnel/localtunnel)
- [Vercel Preview Deployments](https://vercel.com/docs/concepts/deployments/preview-deployments)



