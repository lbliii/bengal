# RFC: API Docs from Running Server

**Status**: Draft  
**Created**: 2025-12-08  
**Author**: AI Assistant  
**Confidence**: 75% 🟡
**Priority**: P2 (Medium)  

---

## Executive Summary

Generate interactive API documentation by introspecting a running server's OpenAPI spec. Point Bengal at `http://localhost:8000`, and it generates endpoint documentation with live "Try It" functionality, auto-generated examples, and response schema docs.

---

## Problem Statement

### Current State

Bengal's autodoc generates documentation from Python source code:
- Extracts docstrings, type hints, signatures
- Works great for libraries and CLIs

**Evidence**:
- `bengal/autodoc/`: Comprehensive Python introspection
- No OpenAPI/REST API support

For REST APIs, users must:
1. Write documentation manually
2. Keep it in sync with actual endpoints
3. Create examples by hand
4. Hope nothing drifts

### Pain Points

1. **Manual sync**: API changes → docs get stale
2. **No "Try It"**: Users can't test endpoints from docs
3. **Missing examples**: Request/response examples are tedious to maintain
4. **Schema drift**: Docs say one thing, API does another
5. **Boilerplate**: Lots of repetitive endpoint documentation

### User Impact

API documentation is often wrong. Users learn to distrust it and go straight to the code or trial-and-error. This wastes time and creates frustration.

---

## Goals & Non-Goals

**Goals**:
- Generate docs from OpenAPI spec (local or remote)
- Interactive "Try It" functionality
- Auto-generated request/response examples
- Live validation against running server
- Support OpenAPI 3.0/3.1

**Non-Goals**:
- GraphQL support (separate RFC)
- gRPC support (separate RFC)
- API mocking (use Prism or similar)
- Replacing dedicated API doc tools (Swagger UI, Redoc)

---

## Architecture Impact

**Affected Subsystems**:
- **Autodoc** (`bengal/autodoc/`): New OpenAPI module
- **Rendering** (`bengal/rendering/`): API endpoint templates
- **CLI** (`bengal/cli/`): New autodoc subcommand

**New Components**:
- `bengal/autodoc/openapi/` - OpenAPI processing
- `bengal/autodoc/openapi/parser.py` - Spec parsing
- `bengal/autodoc/openapi/generator.py` - Doc generation
- `bengal/autodoc/openapi/live.py` - Live server introspection

---

## Proposed CLI Interface

### From Running Server

```bash
# Introspect running server
bengal autodoc api http://localhost:8000

# With custom OpenAPI endpoint
bengal autodoc api http://localhost:8000 --spec-path /openapi.json

# Output to specific directory
bengal autodoc api http://localhost:8000 --output content/api/
```

### From Spec File

```bash
# From local file
bengal autodoc api --spec openapi.yaml

# From remote URL
bengal autodoc api --spec https://api.example.com/openapi.json
```

### With Live Testing

```bash
# Enable "Try It" with actual server
bengal autodoc api http://localhost:8000 --live

# Output:
# Generated API documentation in content/api/
# ├─ _index.md (API overview)
# ├─ authentication.md
# ├─ endpoints/
# │   ├─ users/
# │   │   ├─ list.md (GET /users)
# │   │   ├─ create.md (POST /users)
# │   │   └─ get.md (GET /users/{id})
# │   └─ products/
# │       └─ ...
# └─ schemas/
#     ├─ User.md
#     └─ Product.md
#
# Live testing enabled: http://localhost:8000
```

---

## Detailed Design

### OpenAPI Parser

```python
# bengal/autodoc/openapi/parser.py
from dataclasses import dataclass
import yaml
import httpx

@dataclass
class OpenAPISpec:
    title: str
    version: str
    description: str
    servers: list[Server]
    paths: dict[str, PathItem]
    schemas: dict[str, Schema]
    security_schemes: dict[str, SecurityScheme]

@dataclass
class Endpoint:
    method: str
    path: str
    operation_id: str
    summary: str
    description: str
    parameters: list[Parameter]
    request_body: RequestBody | None
    responses: dict[str, Response]
    security: list[SecurityRequirement]
    tags: list[str]

class OpenAPIParser:
    """Parse OpenAPI specs from various sources."""

    @classmethod
    async def from_server(cls, base_url: str, spec_path: str = "/openapi.json") -> OpenAPISpec:
        """Fetch and parse spec from running server."""
        async with httpx.AsyncClient() as client:
            # Try common spec paths
            paths_to_try = [spec_path, "/openapi.json", "/swagger.json", "/api/openapi.json"]

            for path in paths_to_try:
                try:
                    resp = await client.get(f"{base_url}{path}")
                    if resp.status_code == 200:
                        return cls.parse(resp.json())
                except:
                    continue

            raise ValueError(f"Could not find OpenAPI spec at {base_url}")

    @classmethod
    def from_file(cls, path: Path) -> OpenAPISpec:
        """Parse spec from local file."""
        content = path.read_text()
        if path.suffix in (".yaml", ".yml"):
            data = yaml.safe_load(content)
        else:
            data = json.loads(content)
        return cls.parse(data)

    @classmethod
    def parse(cls, data: dict) -> OpenAPISpec:
        """Parse OpenAPI spec dictionary."""
        return OpenAPISpec(
            title=data.get("info", {}).get("title", "API"),
            version=data.get("info", {}).get("version", "1.0"),
            description=data.get("info", {}).get("description", ""),
            servers=[Server(**s) for s in data.get("servers", [])],
            paths=cls._parse_paths(data.get("paths", {})),
            schemas=cls._parse_schemas(data.get("components", {}).get("schemas", {})),
            security_schemes=cls._parse_security(data.get("components", {}).get("securitySchemes", {})),
        )

    @classmethod
    def _parse_paths(cls, paths: dict) -> dict[str, PathItem]:
        """Parse path items into endpoints."""
        result = {}
        for path, item in paths.items():
            for method in ["get", "post", "put", "patch", "delete"]:
                if method in item:
                    op = item[method]
                    endpoint = Endpoint(
                        method=method.upper(),
                        path=path,
                        operation_id=op.get("operationId", f"{method}_{path}"),
                        summary=op.get("summary", ""),
                        description=op.get("description", ""),
                        parameters=cls._parse_parameters(op.get("parameters", [])),
                        request_body=cls._parse_request_body(op.get("requestBody")),
                        responses=cls._parse_responses(op.get("responses", {})),
                        security=op.get("security", []),
                        tags=op.get("tags", []),
                    )
                    result[f"{method}:{path}"] = endpoint
        return result
```

### Documentation Generator

```python
# bengal/autodoc/openapi/generator.py

class APIDocGenerator:
    """Generate markdown documentation from OpenAPI spec."""

    def __init__(self, spec: OpenAPISpec, options: GeneratorOptions):
        self.spec = spec
        self.options = options

    def generate(self, output_dir: Path) -> list[Path]:
        """Generate all documentation files."""
        files = []

        # Generate index
        files.append(self._generate_index(output_dir))

        # Generate endpoint pages
        for endpoint in self.spec.endpoints:
            files.append(self._generate_endpoint(endpoint, output_dir))

        # Generate schema pages
        for name, schema in self.spec.schemas.items():
            files.append(self._generate_schema(name, schema, output_dir))

        return files

    def _generate_endpoint(self, endpoint: Endpoint, output_dir: Path) -> Path:
        """Generate documentation for a single endpoint."""

        # Determine output path from tags/path
        if endpoint.tags:
            section = endpoint.tags[0].lower().replace(" ", "-")
        else:
            section = "endpoints"

        filename = self._endpoint_to_filename(endpoint)
        path = output_dir / section / filename
        path.parent.mkdir(parents=True, exist_ok=True)

        content = self._render_endpoint(endpoint)
        path.write_text(content)

        return path

    def _render_endpoint(self, endpoint: Endpoint) -> str:
        """Render endpoint to markdown."""

        lines = [
            "---",
            f"title: \"{endpoint.summary or endpoint.operation_id}\"",
            f"method: {endpoint.method}",
            f"path: {endpoint.path}",
            "template: api-endpoint",
            "---",
            "",
            f"# {endpoint.method} {endpoint.path}",
            "",
        ]

        if endpoint.description:
            lines.extend([endpoint.description, ""])

        # Parameters
        if endpoint.parameters:
            lines.extend(self._render_parameters(endpoint.parameters))

        # Request body
        if endpoint.request_body:
            lines.extend(self._render_request_body(endpoint.request_body))

        # Responses
        lines.extend(self._render_responses(endpoint.responses))

        # Example
        lines.extend(self._render_example(endpoint))

        # Try It (if live mode)
        if self.options.live_server:
            lines.extend(self._render_try_it(endpoint))

        return "\n".join(lines)

    def _render_example(self, endpoint: Endpoint) -> list[str]:
        """Generate example request/response."""
        lines = ["## Example", ""]

        # Generate curl example
        curl = self._generate_curl(endpoint)
        lines.extend([
            "### Request",
            "",
            "```bash",
            curl,
            "```",
            "",
        ])

        # Generate example response
        if "200" in endpoint.responses:
            response = endpoint.responses["200"]
            example = self._generate_response_example(response)
            lines.extend([
                "### Response",
                "",
                "```json",
                json.dumps(example, indent=2),
                "```",
                "",
            ])

        return lines

    def _generate_curl(self, endpoint: Endpoint) -> str:
        """Generate curl command for endpoint."""
        parts = [f"curl -X {endpoint.method}"]

        url = f"{self.options.base_url}{endpoint.path}"

        # Add path parameters as placeholders
        for param in endpoint.parameters:
            if param.location == "path":
                url = url.replace(f"{{{param.name}}}", f"<{param.name}>")

        parts.append(f'  "{url}"')

        # Add headers
        if endpoint.request_body:
            parts.append('  -H "Content-Type: application/json"')

        # Add body
        if endpoint.request_body:
            example = self._generate_request_example(endpoint.request_body)
            parts.append(f"  -d '{json.dumps(example)}'")

        return " \\\n".join(parts)

    def _render_try_it(self, endpoint: Endpoint) -> list[str]:
        """Render interactive Try It section."""
        return [
            "## Try It",
            "",
            f":::{{api-tester endpoint=\"{endpoint.method} {endpoint.path}\"}}",
            ":::",
            "",
        ]
```

### Live Testing Component

```python
# bengal/autodoc/openapi/live.py

class APITester:
    """Execute live API requests from documentation."""

    def __init__(self, base_url: str, auth_token: str | None = None):
        self.base_url = base_url
        self.auth_token = auth_token

    async def execute(
        self,
        method: str,
        path: str,
        params: dict | None = None,
        body: dict | None = None,
        headers: dict | None = None,
    ) -> APIResponse:
        """Execute API request and return response."""

        url = f"{self.base_url}{path}"

        # Replace path parameters
        if params:
            for key, value in params.items():
                url = url.replace(f"{{{key}}}", str(value))

        request_headers = headers or {}
        if self.auth_token:
            request_headers["Authorization"] = f"Bearer {self.auth_token}"

        async with httpx.AsyncClient() as client:
            start = time.perf_counter()

            response = await client.request(
                method=method,
                url=url,
                json=body,
                headers=request_headers,
                timeout=30,
            )

            duration = time.perf_counter() - start

        return APIResponse(
            status_code=response.status_code,
            headers=dict(response.headers),
            body=response.json() if response.headers.get("content-type", "").startswith("application/json") else response.text,
            duration_ms=duration * 1000,
        )
```

### Try It Shortcode

```python
# bengal/rendering/shortcodes/api_tester.py

class APITesterShortcode(Shortcode):
    """Interactive API testing component."""

    name = "api-tester"

    def render(self, endpoint: str, **kwargs) -> str:
        method, path = endpoint.split(" ", 1)

        return f'''
<div class="api-tester" data-method="{method}" data-path="{path}">
    <div class="api-tester-params">
        <!-- Parameter inputs generated from schema -->
    </div>

    <div class="api-tester-body">
        <label>Request Body</label>
        <textarea class="api-tester-body-input" placeholder="{{}}"></textarea>
    </div>

    <button class="api-tester-send">Send Request</button>

    <div class="api-tester-response" style="display: none;">
        <div class="api-tester-status"></div>
        <div class="api-tester-time"></div>
        <pre class="api-tester-output"></pre>
    </div>
</div>

<script>
(function() {{
    const tester = document.currentScript.previousElementSibling;
    const sendBtn = tester.querySelector('.api-tester-send');
    const responseDiv = tester.querySelector('.api-tester-response');

    sendBtn.addEventListener('click', async () => {{
        const body = tester.querySelector('.api-tester-body-input').value;

        try {{
            const resp = await fetch('/_bengal/api-test', {{
                method: 'POST',
                headers: {{ 'Content-Type': 'application/json' }},
                body: JSON.stringify({{
                    method: '{method}',
                    path: '{path}',
                    body: body ? JSON.parse(body) : null,
                }}),
            }});

            const result = await resp.json();

            responseDiv.style.display = 'block';
            tester.querySelector('.api-tester-status').textContent = `Status: ${{result.status_code}}`;
            tester.querySelector('.api-tester-time').textContent = `Time: ${{result.duration_ms.toFixed(0)}}ms`;
            tester.querySelector('.api-tester-output').textContent = JSON.stringify(result.body, null, 2);
        }} catch (e) {{
            responseDiv.style.display = 'block';
            tester.querySelector('.api-tester-output').textContent = `Error: ${{e.message}}`;
        }}
    }});
}})();
</script>
'''
```

---

## Generated Documentation Structure

```
content/api/
├─ _index.md                    # API Overview
│   - Title, version, description
│   - Authentication overview
│   - Base URL configuration
│   - Quick links to sections
│
├─ authentication.md            # Auth documentation
│   - Available auth methods
│   - How to get tokens
│   - Example authenticated request
│
├─ users/                       # Grouped by tag
│   ├─ _index.md               # Users overview
│   ├─ list-users.md           # GET /users
│   ├─ create-user.md          # POST /users
│   ├─ get-user.md             # GET /users/{id}
│   ├─ update-user.md          # PUT /users/{id}
│   └─ delete-user.md          # DELETE /users/{id}
│
├─ products/
│   └─ ...
│
└─ schemas/                     # Data models
    ├─ _index.md               # Schema overview
    ├─ User.md                 # User schema
    ├─ Product.md              # Product schema
    └─ Error.md                # Error response schema
```

---

## Configuration

```toml
# bengal.toml
[autodoc.openapi]
# Default output directory
output_dir = "content/api"

# Template for endpoint pages
endpoint_template = "api-endpoint"

# Template for schema pages
schema_template = "api-schema"

# Group endpoints by
group_by = "tags"  # or "path"

# Generate Try It components
live_testing = true

# Base URL for examples (overrides spec)
# base_url = "https://api.example.com"

# Include deprecated endpoints
include_deprecated = false

# Example generation
[autodoc.openapi.examples]
# Use examples from spec when available
prefer_spec_examples = true

# Generate fake data for missing examples
generate_fake_data = true
```

---

## Implementation Plan

### Phase 1: Core Parser (2 weeks)
- [ ] OpenAPI 3.0/3.1 parsing
- [ ] Spec fetching from server
- [ ] Spec loading from file

### Phase 2: Doc Generation (2 weeks)
- [ ] Endpoint documentation
- [ ] Schema documentation
- [ ] Example generation

### Phase 3: Live Testing (2 weeks)
- [ ] API tester shortcode
- [ ] Server-side proxy endpoint
- [ ] Response formatting

### Phase 4: Polish (1 week)
- [ ] Authentication handling
- [ ] Error documentation
- [ ] Multiple server support

---

## Risks & Mitigations

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| OpenAPI spec incomplete | High | Medium | Warn on missing info, generate placeholders |
| Live server unavailable | Medium | Medium | Graceful degradation, cached examples |
| Security (exposing internal APIs) | High | Low | Auth required for Try It, configurable |
| Large specs (100s of endpoints) | Medium | Low | Pagination, lazy loading |

---

## Open Questions

1. **Should Try It work in production?**
   - Risk: Exposing test functionality
   - Proposal: Dev mode only by default

2. **How to handle authentication in Try It?**
   - Options: Token input, env var, skip auth endpoints
   - Proposal: Configurable per-endpoint

3. **Support for multiple API versions?**
   - Relates to versioned documentation RFC
   - Proposal: One spec per version, versioning handles the rest

---

## Success Criteria

- [ ] Generate docs from valid OpenAPI 3.x spec
- [ ] Try It functionality works for simple endpoints
- [ ] Examples auto-generated from schema
- [ ] <30s generation for 100-endpoint spec
- [ ] No manual sync needed when API changes

---

## References

- [OpenAPI Specification](https://spec.openapis.org/oas/latest.html)
- [Swagger UI](https://swagger.io/tools/swagger-ui/)
- [Redoc](https://redocly.com/redoc/)
- [Stoplight Elements](https://stoplight.io/open-source/elements)
