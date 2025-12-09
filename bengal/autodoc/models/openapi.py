"""
OpenAPI-specific metadata dataclasses for autodoc system.

Provides typed metadata for:
- API Overview (OpenAPIOverviewMetadata)
- Endpoints (OpenAPIEndpointMetadata)
- Schemas (OpenAPISchemaMetadata)
- Parameters (OpenAPIParameterMetadata)
- Request bodies (OpenAPIRequestBodyMetadata)
- Responses (OpenAPIResponseMetadata)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

type HTTPMethod = Literal["GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"]


@dataclass(frozen=True, slots=True)
class OpenAPIParameterMetadata:
    """
    Metadata for OpenAPI parameter.

    Attributes:
        name: Parameter name
        location: Where parameter is located (path, query, header, cookie)
        required: Whether parameter is required
        schema_type: Type of parameter
        description: Parameter description

    Example:
        >>> meta = OpenAPIParameterMetadata(
        ...     name="user_id",
        ...     location="path",
        ...     required=True,
        ...     schema_type="string",
        ... )
        >>> meta.location
        'path'
    """

    name: str
    location: Literal["path", "query", "header", "cookie"]
    required: bool = False
    schema_type: str = "string"
    description: str = ""


@dataclass(frozen=True, slots=True)
class OpenAPIRequestBodyMetadata:
    """
    Metadata for OpenAPI request body.

    Attributes:
        content_type: Media type (e.g., "application/json")
        schema_ref: Reference to schema
        required: Whether request body is required
        description: Request body description

    Example:
        >>> meta = OpenAPIRequestBodyMetadata(
        ...     content_type="application/json",
        ...     schema_ref="#/components/schemas/User",
        ...     required=True,
        ... )
        >>> meta.required
        True
    """

    content_type: str = "application/json"
    schema_ref: str | None = None
    required: bool = False
    description: str = ""


@dataclass(frozen=True, slots=True)
class OpenAPIResponseMetadata:
    """
    Metadata for OpenAPI response.

    Attributes:
        status_code: HTTP status code (e.g., "200", "404", "default")
        description: Response description
        content_type: Media type
        schema_ref: Reference to response schema

    Example:
        >>> meta = OpenAPIResponseMetadata(
        ...     status_code="200",
        ...     description="Successful response",
        ...     content_type="application/json",
        ... )
        >>> meta.status_code
        '200'
    """

    status_code: str
    description: str = ""
    content_type: str | None = None
    schema_ref: str | None = None


@dataclass(frozen=True, slots=True)
class OpenAPIEndpointMetadata:
    """
    Metadata specific to OpenAPI endpoints.

    Attributes:
        method: HTTP method (GET, POST, PUT, DELETE, etc.)
        path: URL path
        operation_id: Unique operation identifier
        summary: Short summary
        tags: Endpoint tags for grouping
        parameters: Request parameters
        request_body: Request body metadata
        responses: Response metadata
        security: Security requirements
        deprecated: Whether endpoint is deprecated

    Example:
        >>> meta = OpenAPIEndpointMetadata(
        ...     method="GET",
        ...     path="/users/{id}",
        ...     operation_id="getUser",
        ...     tags=("users",),
        ... )
        >>> meta.method
        'GET'
    """

    method: HTTPMethod
    path: str
    operation_id: str | None = None
    summary: str | None = None
    tags: tuple[str, ...] = ()
    parameters: tuple[OpenAPIParameterMetadata, ...] = ()
    request_body: OpenAPIRequestBodyMetadata | None = None
    responses: tuple[OpenAPIResponseMetadata, ...] = ()
    security: tuple[str, ...] = ()
    deprecated: bool = False


@dataclass(frozen=True, slots=True)
class OpenAPIOverviewMetadata:
    """
    Metadata for OpenAPI spec overview.

    Attributes:
        version: API version
        servers: Server URLs
        security_schemes: Available security schemes
        tags: API tags with descriptions

    Example:
        >>> meta = OpenAPIOverviewMetadata(
        ...     version="1.0.0",
        ...     servers=("https://api.example.com",),
        ... )
        >>> meta.version
        '1.0.0'
    """

    version: str | None = None
    servers: tuple[str, ...] = ()
    security_schemes: dict[str, Any] = field(default_factory=dict)
    tags: tuple[dict[str, Any], ...] = ()

    def __hash__(self) -> int:
        """Hash based on immutable fields only."""
        return hash(
            (
                self.version,
                self.servers,
                tuple(self.security_schemes.keys()),
                len(self.tags),
            )
        )


@dataclass(frozen=True, slots=True)
class OpenAPISchemaMetadata:
    """
    Metadata for OpenAPI schema/model.

    Attributes:
        schema_type: Type of schema (object, array, string, etc.)
        properties: Schema properties
        required: Required property names
        enum: Enum values if applicable
        example: Example value

    Example:
        >>> meta = OpenAPISchemaMetadata(
        ...     schema_type="object",
        ...     required=("id", "name"),
        ... )
        >>> meta.schema_type
        'object'
    """

    schema_type: str | None = None
    properties: dict[str, Any] = field(default_factory=dict)
    required: tuple[str, ...] = ()
    enum: tuple[Any, ...] | None = None
    example: Any = None

    def __hash__(self) -> int:
        """Hash based on immutable fields only."""
        return hash(
            (
                self.schema_type,
                tuple(self.properties.keys()),
                self.required,
                self.enum,
            )
        )
