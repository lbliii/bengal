"""
HTTP error handling utilities for remote content sources.

Provides consistent error handling for GitHub, Notion, and REST sources.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from bengal.errors import BengalDiscoveryError, ErrorCode, record_error

if TYPE_CHECKING:
    from aiohttp import ClientResponse


async def check_http_response(
    response: ClientResponse,
    resource_type: str,
    resource_id: str,
    *,
    error_suggestions: dict[int, str] | None = None,
) -> None:
    """
    Check HTTP response and raise appropriate error for non-success status codes.

    Handles common HTTP errors (401, 403, 404) with consistent error messages
    and records them for aggregation. Does nothing if response is successful.

    Args:
        response: aiohttp ClientResponse to check
        resource_type: Type of resource being fetched (e.g., "GitHub repository",
            "Notion database", "REST API endpoint")
        resource_id: Identifier for the resource (e.g., repo name, database ID, URL)
        error_suggestions: Optional mapping of status codes to custom suggestions.
            Defaults are provided for 401, 403, 404.

    Raises:
        BengalDiscoveryError: If response status indicates an error

    Example:
        >>> async with session.get(url) as resp:
        ...     await check_http_response(
        ...         resp,
        ...         resource_type="GitHub repository",
        ...         resource_id="myorg/api-docs",
        ...     )
        ...     # Process successful response
        ...     data = await resp.json()

    """
    if response.ok:
        return

    status = response.status

    # Default suggestions by status code
    default_suggestions = {
        401: f"Check authentication credentials for {resource_type}",
        403: f"Check access permissions for {resource_type}",
        404: f"Verify {resource_type} exists and is accessible: {resource_id}",
    }

    # Merge with custom suggestions
    suggestions = {**default_suggestions, **(error_suggestions or {})}
    suggestion = suggestions.get(status, f"Check {resource_type} configuration")

    # Default error codes by status
    error_codes = {
        401: ErrorCode.D010,  # Auth failed
        403: ErrorCode.D010,  # Access denied
        404: ErrorCode.D011,  # Not found
    }
    code = error_codes.get(status, ErrorCode.D008)  # Generic fetch error

    # Build error message
    status_messages = {
        401: "Authentication failed",
        403: "Access denied",
        404: "Not found",
    }
    status_msg = status_messages.get(status, f"HTTP {status}")

    error = BengalDiscoveryError(
        f"{status_msg} for {resource_type}: {resource_id}",
        code=code,
        suggestion=suggestion,
    )
    record_error(error)
    raise error


def raise_http_error(
    status: int,
    resource_type: str,
    resource_id: str,
    *,
    suggestion: str | None = None,
) -> None:
    """
    Raise an HTTP error without an aiohttp response object.

    Useful when you've already checked the status and want to raise
    an appropriate error.

    Args:
        status: HTTP status code
        resource_type: Type of resource
        resource_id: Resource identifier
        suggestion: Optional custom suggestion

    Raises:
        BengalDiscoveryError: Always raises

    """
    # Default suggestions
    default_suggestions = {
        401: f"Check authentication credentials for {resource_type}",
        403: f"Check access permissions for {resource_type}",
        404: f"Verify {resource_type} exists: {resource_id}",
    }

    # Error codes
    error_codes = {
        401: ErrorCode.D010,
        403: ErrorCode.D010,
        404: ErrorCode.D011,
    }

    # Status messages
    status_messages = {
        401: "Authentication failed",
        403: "Access denied",
        404: "Not found",
    }

    code = error_codes.get(status, ErrorCode.D008)
    msg = status_messages.get(status, f"HTTP {status}")
    sugg = suggestion or default_suggestions.get(status, f"Check {resource_type} configuration")

    error = BengalDiscoveryError(
        f"{msg} for {resource_type}: {resource_id}",
        code=code,
        suggestion=sugg,
    )
    record_error(error)
    raise error
