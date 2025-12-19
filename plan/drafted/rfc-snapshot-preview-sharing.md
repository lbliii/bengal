# RFC: Snapshot Preview Sharing

**Status**: Draft  
**Created**: 2025-12-19  
**Author**: AI Assistant  
**Confidence**: 78% 🟢  
**Priority**: P2 (Medium)  
**Supersedes**: rfc-live-preview-sharing.md

---

## Executive Summary

Share documentation previews by building static snapshots and uploading to temporary hosting. Run `bengal share` to get a public URL like `https://abc123.surge.sh` that anyone can access—no tunnel binaries, no persistent connections, laptop can be off after upload.

**Paid tier opportunity**: Bengal-hosted preview service with stable URLs, password protection, view analytics, and team features.

---

## Problem Statement

### Current State

To share a preview of documentation changes:
1. Commit changes
2. Push to branch
3. Wait for CI/CD (2-10 minutes)
4. Share staging URL

Or manually deploy somewhere, which requires setup and context switching.

### Why Not Tunnels?

The [previous RFC](rfc-live-preview-sharing.md) proposed tunneling (Cloudflare, ngrok). Issues:

| Problem | Impact |
|---------|--------|
| Requires binary install (`cloudflared`) | Friction for users |
| Laptop must stay on | Not always practical |
| Corporate firewalls block tunnels | Enterprise unfriendly |
| Complex persistent connections | More to go wrong |

### Key Insight

**Users don't need a live server. They need to share files.**

Documentation is static. Build it, upload it, share the URL. Simple.

---

## Goals & Non-Goals

**Goals**:
- One-command preview sharing: `bengal share`
- Shareable URL accessible from anywhere
- Laptop can be off after sharing
- No external binary installation required
- Works in corporate environments (just HTTPS)
- Path to paid service with premium features

**Non-Goals**:
- Live reload in preview (use `bengal serve` locally for that)
- Real-time collaboration editing
- Production hosting (use `bengal deploy` for that)

---

## Design: Snapshot Sharing

### Core Flow

```
┌─────────────────────────────────────────────────────────────────┐
│  bengal share                                                    │
│                                                                  │
│  1. Build site to temp directory                                │
│  2. Upload static files to preview host                         │
│  3. Return public URL                                           │
│  4. Done (laptop can close)                                     │
└─────────────────────────────────────────────────────────────────┘

User's Laptop                    Preview Host                 Reviewer
┌─────────────┐    upload       ┌─────────────┐              ┌─────────────┐
│ bengal share│ ──────────────▶ │ Static CDN  │ ◀─────────── │ Browser     │
│             │   (HTTPS POST)  │             │   (HTTPS GET)│             │
└─────────────┘                 └─────────────┘              └─────────────┘
      │
      │ (can close after upload)
      ▼
    💤 Done
```

### CLI Interface

```bash
# Basic sharing
bengal share

# Output:
# 📤 Building site...
# 📤 Uploading 42 files (1.2 MB)...
#
# 🔗 https://abc123.surge.sh
#
# Share this URL. Preview available until manually deleted.


# With expiration
bengal share --expires 24h

# Output:
# 🔗 https://abc123.surge.sh
# ⏰ Expires in 24 hours


# With password (paid tier)
bengal share --password

# Output:
# 🔗 https://myproject.preview.bengal.dev
# 🔐 Password: xK9mP2nQ


# Using specific provider
bengal share --provider surge
bengal share --provider netlify
bengal share --provider bengal  # Paid tier
```

---

## Provider Options

### Free Tier: Third-Party Hosts

#### Option 1: Surge.sh (Recommended Default)

**Why**: No account required for basic use, instant, free.

```python
# bengal/share/surge.py
import subprocess
import secrets

def share_surge(build_dir: Path) -> str:
    """Upload to Surge.sh and return URL."""
    subdomain = f"bengal-{secrets.token_hex(4)}"
    domain = f"{subdomain}.surge.sh"

    result = subprocess.run(
        ["npx", "surge", str(build_dir), "--domain", domain],
        capture_output=True,
        text=True,
    )

    if result.returncode != 0:
        raise ShareError(f"Surge upload failed: {result.stderr}")

    return f"https://{domain}"
```

**Pros**:
- No account for throwaway previews
- Instant
- Free
- Reliable (Zeit/Vercel heritage)

**Cons**:
- Requires Node.js (`npx surge`)
- No built-in expiration
- No password protection

#### Option 2: Netlify CLI

```python
# bengal/share/netlify.py
import subprocess
import json

def share_netlify(build_dir: Path) -> str:
    """Deploy draft to Netlify."""
    result = subprocess.run(
        ["netlify", "deploy", "--dir", str(build_dir), "--json"],
        capture_output=True,
        text=True,
    )

    data = json.loads(result.stdout)
    return data["deploy_url"]  # Draft URL, not production
```

**Pros**:
- Professional, reliable
- Draft URLs don't affect production
- Good CLI

**Cons**:
- Requires Netlify account
- Requires `netlify` CLI installed

#### Option 3: Direct S3/R2 Upload

```python
# bengal/share/s3.py
import boto3

def share_s3(build_dir: Path, bucket: str) -> str:
    """Upload to S3 with public-read."""
    s3 = boto3.client("s3")
    prefix = f"previews/{secrets.token_hex(8)}"

    for file in build_dir.rglob("*"):
        if file.is_file():
            key = f"{prefix}/{file.relative_to(build_dir)}"
            s3.upload_file(
                str(file), bucket, key,
                ExtraArgs={"ACL": "public-read"}
            )

    return f"https://{bucket}.s3.amazonaws.com/{prefix}/index.html"
```

**Pros**:
- User controls hosting
- No third-party dependency
- Cheap at scale

**Cons**:
- Requires AWS setup
- User manages cleanup

### Provider Abstraction

```python
# bengal/share/provider.py
from abc import ABC, abstractmethod

class ShareProvider(ABC):
    @abstractmethod
    def upload(self, build_dir: Path) -> ShareResult:
        """Upload build directory and return result."""
        pass

    @abstractmethod
    def delete(self, share_id: str) -> None:
        """Delete a shared preview."""
        pass

@dataclass
class ShareResult:
    url: str
    share_id: str
    expires_at: datetime | None = None
    password: str | None = None

def get_provider(name: str = "auto") -> ShareProvider:
    if name == "bengal":
        return BengalShareProvider()  # Paid tier
    elif name == "surge" or (name == "auto" and _has_npx()):
        return SurgeProvider()
    elif name == "netlify":
        return NetlifyProvider()
    elif name == "s3":
        return S3Provider()
    else:
        raise ValueError(f"Unknown provider: {name}")
```

---

## Paid Tier: Bengal Preview Service

### Value Proposition

| Feature | Free (Surge/Netlify) | Paid (Bengal) |
|---------|---------------------|---------------|
| URL | `random-abc123.surge.sh` | `yourproject.preview.bengal.dev` |
| Stable URL | ❌ Random each time | ✅ Same URL for project |
| Password protection | ❌ No | ✅ Built-in |
| Expiration control | ❌ Manual delete | ✅ Auto-expire (1h, 24h, 7d) |
| View analytics | ❌ No | ✅ "5 people viewed" |
| Team sharing | ❌ No | ✅ Share with team members |
| Custom branding | ❌ No | ✅ Remove "Powered by Bengal" |
| Bandwidth | Subject to Surge limits | Generous limits |
| Support | None | Email support |

### Pricing Ideas

```yaml
# Option A: Simple subscription
free:
  - Use Surge/Netlify (no Bengal cost)

pro: $8/month per user
  - preview.bengal.dev hosting
  - Stable project URLs
  - Password protection
  - View analytics
  - 10 active previews
  - 7-day max retention

team: $20/month (up to 5 users)
  - Everything in Pro
  - Team member access
  - Shared preview library
  - 30-day max retention
  - Custom subdomain (yourcompany.preview.bengal.dev)

# Option B: Usage-based
free:
  - 3 previews/month on Bengal
  - 24h expiration

pay_as_you_go:
  - $0.10 per preview-day
  - Password protection included
  - Analytics included
```

### Technical Implementation

**Backend Service** (simple Flask/FastAPI app):

```python
# preview-service/app.py
from fastapi import FastAPI, UploadFile, HTTPException
from fastapi.responses import FileResponse
import secrets
import shutil

app = FastAPI()

# Storage: S3, R2, or local disk
STORAGE_PATH = Path("/var/previews")

@app.post("/api/upload")
async def upload_preview(
    files: list[UploadFile],
    api_key: str,
    project_slug: str | None = None,
    password: str | None = None,
    expires_hours: int = 24,
):
    """Upload preview files."""
    # Validate API key, check quota
    user = validate_api_key(api_key)
    check_quota(user)

    # Generate or use stable preview ID
    if project_slug and user.plan == "pro":
        preview_id = f"{user.username}-{project_slug}"
    else:
        preview_id = secrets.token_hex(8)

    # Save files
    preview_dir = STORAGE_PATH / preview_id
    preview_dir.mkdir(parents=True, exist_ok=True)

    for file in files:
        dest = preview_dir / file.filename
        dest.parent.mkdir(parents=True, exist_ok=True)
        with open(dest, "wb") as f:
            shutil.copyfileobj(file.file, f)

    # Save metadata
    save_metadata(preview_id, {
        "user": user.id,
        "password_hash": hash_password(password) if password else None,
        "expires_at": datetime.now() + timedelta(hours=expires_hours),
        "created_at": datetime.now(),
        "view_count": 0,
    })

    return {
        "url": f"https://{preview_id}.preview.bengal.dev",
        "preview_id": preview_id,
        "expires_at": metadata["expires_at"].isoformat(),
    }

@app.get("/{preview_id}/{path:path}")
async def serve_preview(preview_id: str, path: str, password: str | None = None):
    """Serve preview files with optional password check."""
    metadata = get_metadata(preview_id)

    if not metadata:
        raise HTTPException(404, "Preview not found")

    if metadata["expires_at"] < datetime.now():
        raise HTTPException(410, "Preview expired")

    if metadata["password_hash"]:
        if not password or not verify_password(password, metadata["password_hash"]):
            return HTMLResponse(password_form_html())

    # Increment view count
    increment_view_count(preview_id)

    # Serve file
    file_path = STORAGE_PATH / preview_id / (path or "index.html")
    if not file_path.exists():
        file_path = STORAGE_PATH / preview_id / "index.html"

    return FileResponse(file_path)

@app.get("/api/analytics/{preview_id}")
async def get_analytics(preview_id: str, api_key: str):
    """Get view analytics for a preview."""
    user = validate_api_key(api_key)
    metadata = get_metadata(preview_id)

    if metadata["user"] != user.id:
        raise HTTPException(403, "Not your preview")

    return {
        "view_count": metadata["view_count"],
        "created_at": metadata["created_at"],
        "expires_at": metadata["expires_at"],
    }
```

**Client Integration**:

```python
# bengal/share/bengal_provider.py
import httpx
from pathlib import Path

class BengalShareProvider(ShareProvider):
    API_URL = "https://api.bengal.dev"

    def __init__(self):
        self.api_key = self._get_api_key()

    def upload(self, build_dir: Path, **options) -> ShareResult:
        files = []
        for file in build_dir.rglob("*"):
            if file.is_file():
                rel_path = file.relative_to(build_dir)
                files.append(("files", (str(rel_path), open(file, "rb"))))

        response = httpx.post(
            f"{self.API_URL}/api/upload",
            files=files,
            data={
                "api_key": self.api_key,
                "project_slug": options.get("project"),
                "password": options.get("password"),
                "expires_hours": options.get("expires_hours", 24),
            },
        )
        response.raise_for_status()
        data = response.json()

        return ShareResult(
            url=data["url"],
            share_id=data["preview_id"],
            expires_at=datetime.fromisoformat(data["expires_at"]),
            password=options.get("password"),
        )

    def _get_api_key(self) -> str:
        # Check env var, then config file
        if key := os.environ.get("BENGAL_API_KEY"):
            return key

        config_path = Path.home() / ".config" / "bengal" / "credentials"
        if config_path.exists():
            return config_path.read_text().strip()

        raise ShareError(
            "Bengal API key not found. Get one at https://bengal.dev/account\n"
            "Set BENGAL_API_KEY or run: bengal auth login"
        )
```

### Infrastructure (Minimal)

```yaml
# What Bengal needs to run the paid service

Option A: Simple VPS ($10-20/month)
  - Nginx serving static files
  - FastAPI for upload API
  - SQLite for metadata
  - Cron job for expiration cleanup
  - Good for: 0-1000 users

Option B: Cloudflare Stack ($5-50/month)
  - Cloudflare R2 for storage (cheap)
  - Cloudflare Workers for API
  - Cloudflare Pages for dashboard
  - D1 or KV for metadata
  - Good for: Scaling without ops burden

Option C: AWS Serverless (usage-based)
  - S3 for storage
  - Lambda + API Gateway
  - DynamoDB for metadata
  - CloudFront for CDN
  - Good for: Variable load, pay-per-use
```

---

## Configuration

```toml
# bengal.toml
[share]
# Default provider
provider = "auto"  # auto, surge, netlify, bengal, s3

# Default expiration
default_expires = "24h"

# Project slug for stable URLs (paid tier)
project = "my-docs"

# Bengal paid tier settings
[share.bengal]
# api_key = "..."  # Or BENGAL_API_KEY env var

# S3 settings (if using S3)
[share.s3]
bucket = "my-preview-bucket"
region = "us-east-1"
```

---

## Implementation Plan

### Phase 1: Free Tier MVP (1 week)
- [ ] `bengal share` command
- [ ] Surge.sh provider (default)
- [ ] Basic CLI output

### Phase 2: Provider Abstraction (1 week)
- [ ] Provider interface
- [ ] Netlify provider
- [ ] S3 provider
- [ ] Provider auto-detection

### Phase 3: Bengal Paid Service (2-3 weeks)
- [ ] Upload API
- [ ] File serving with subdomain routing
- [ ] Password protection
- [ ] Expiration handling
- [ ] Basic analytics

### Phase 4: Polish (1 week)
- [ ] `bengal share --list` (show active previews)
- [ ] `bengal share --delete <id>`
- [ ] View count display
- [ ] Dashboard (web UI)

---

## Business Model Analysis

### Revenue Potential

```
Conservative estimate (Year 1):
- 50 Pro subscribers × $8/mo = $400/mo = $4,800/year
- Infrastructure cost: ~$50/mo = $600/year
- Net: $4,200/year (not life-changing, but covers costs)

Optimistic estimate (Year 2):
- 200 Pro subscribers × $8/mo = $1,600/mo
- 20 Team subscribers × $20/mo = $400/mo
- Total: $2,000/mo = $24,000/year
- Infrastructure: ~$200/mo = $2,400/year
- Net: $21,600/year
```

### Customer Acquisition

The free tier (Surge/Netlify) serves as funnel:
1. User discovers `bengal share` (free)
2. Loves it, uses it regularly
3. Hits friction: random URLs, no password, wants analytics
4. Converts to paid tier

### Competitive Landscape

| Product | Preview Sharing | Pricing |
|---------|-----------------|---------|
| Netlify | Built into platform | Free tier, then $19+/mo |
| Vercel | Built into platform | Free tier, then $20+/mo |
| Surge | Standalone | Free |
| ReadMe | API docs | $99+/mo |
| GitBook | Docs platform | $8+/user/mo |
| **Bengal** | SSG + share feature | Free + $8/mo optional |

Bengal's angle: You're not locked into a platform. Use any hosting for production, use Bengal Share for previews.

---

## Risks & Mitigations

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| Surge changes terms | Medium | Low | Multiple providers, own paid tier |
| Low paid tier adoption | Medium | Medium | Keep free tier great, paid as bonus |
| Abuse (spam, illegal content) | High | Medium | Rate limits, ToS, content scanning |
| Infrastructure costs spike | Medium | Low | Usage-based pricing, caps |
| Support burden | Medium | Medium | Good docs, community support for free tier |

---

## Open Questions

1. **Should free tier use Bengal infrastructure?**
   - Pro: Consistent experience, upsell path
   - Con: Cost, abuse potential
   - Proposal: No, use third-party for free tier

2. **What about image-heavy sites?**
   - Large uploads = bandwidth cost
   - Proposal: Size limits (50MB free, 500MB paid)

3. **How long should previews live?**
   - Free: Provider's policy (Surge = forever until deleted)
   - Paid: User-controlled, max 30 days

4. **Team features scope?**
   - Shared preview library
   - Access controls
   - Proposal: Keep simple initially, add based on demand

---

## Success Criteria

### Phase 1 (Free Tier)
- [ ] `bengal share` produces working URL
- [ ] < 30 seconds to upload average site
- [ ] Works on Mac/Linux/Windows
- [ ] Clear error messages for missing dependencies

### Phase 3 (Paid Tier)
- [ ] Stable URLs work
- [ ] Password protection works
- [ ] View analytics accurate
- [ ] 10+ paying customers in first 3 months

### Business
- [ ] Positive unit economics (revenue > infrastructure)
- [ ] < 1 hour/week support burden
- [ ] NPS > 40 from paid users

---

## Comparison: Tunnel vs Snapshot

| Factor | Tunnel (Old RFC) | Snapshot (This RFC) |
|--------|------------------|---------------------|
| User experience | Run command, keep laptop on | Run command, done |
| Binary dependencies | cloudflared/ngrok | npx surge (or none for paid) |
| Corporate friendly | 🟡 Tunnels often blocked | ✅ Just HTTPS |
| Live updates | ✅ Yes | ❌ Re-share needed |
| Laptop can sleep | ❌ No | ✅ Yes |
| Paid tier opportunity | Weak (relay hosting) | Strong (simple file hosting) |
| Implementation complexity | Medium (WebSocket relay) | Low (HTTP upload) |

**Verdict**: Snapshot approach is simpler, more reliable, and has better business potential.

---

## References

- [Surge.sh](https://surge.sh/) - Static web publishing
- [Netlify CLI](https://docs.netlify.com/cli/get-started/) - Deploy from command line
- [Cloudflare R2](https://developers.cloudflare.com/r2/) - S3-compatible object storage
- [Vercel CLI](https://vercel.com/docs/cli) - Instant deployments
